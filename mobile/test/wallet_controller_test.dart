import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/testing.dart';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'package:bigcoin_mobile/services/chain_service.dart';
import 'package:bigcoin_mobile/wallet/bigcoin_network.dart';
import 'package:bigcoin_mobile/wallet/secure_key_store.dart';
import 'package:bigcoin_mobile/wallet/wallet_controller.dart';

const _mnemonic =
    'abandon abandon abandon abandon abandon abandon '
    'abandon abandon abandon abandon abandon about';
// index-0 testnet address for the vector above, and its scriptPubKey.
const _addr0 = 'tbig1q6rz28mcfaxtmd6v789l9rrlrusdprr9pdc24tr';
const _spk0 = '0014d0c4a3ef09e997b6e99e397e518fe3e41a118ca1';
const _dest = 'tbig1qd7spv5q28348xl4myc8zmh983w5jx32clha2cz';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late String? lastBroadcastHex;

  http.Client fakeHttp() => MockClient((req) async {
        final path = req.url.path;
        if (path.endsWith('/api/status')) {
          return http.Response(
              jsonEncode({
                'chain': 'test',
                'blocks': 50,
                'headers': 50,
                'bestblockhash': 'abc',
                'difficulty': 1.0,
                'verificationprogress': 1.0,
                'mempool_txs': 0,
                'connections': 3,
                'subversion': '/BigCoin:2.5.0/',
                'demo': false,
              }),
              200);
        }
        if (path.contains('/balance')) {
          return http.Response(
              jsonEncode({
                'address': _addr0,
                'confirmed': 50.0,
                'unconfirmed': 0.0,
                'total': 50.0,
                'utxo_count': 1,
                'demo': false,
              }),
              200);
        }
        if (path.contains('/utxos')) {
          return http.Response(
              jsonEncode({
                'address': _addr0,
                'utxos': [
                  {
                    'txid':
                        '1111111111111111111111111111111111111111111111111111111111111111',
                    'vout': 0,
                    'amount': 50.0,
                    'scriptPubKey': _spk0,
                    'height': 10,
                    'confirmations': 120,
                  }
                ],
                'scan_height': 130,
                'demo': false,
              }),
              200);
        }
        if (path.endsWith('/api/fee')) {
          return http.Response(
              jsonEncode({'feerate': 0.00001, 'blocks': 6, 'source': 'x'}),
              200);
        }
        if (path.endsWith('/api/tx/broadcast')) {
          lastBroadcastHex =
              (jsonDecode(req.body) as Map<String, dynamic>)['rawtx'] as String;
          return http.Response(jsonEncode({'txid': 'deadbeef'}), 200);
        }
        return http.Response('{"error":"unexpected ${req.url}"}', 404);
      });

  WalletController makeController() => WalletController(
        chain: ChainService(baseUrl: 'https://x', httpClient: fakeHttp()),
        store: SecureKeyStore(),
      );

  setUp(() {
    lastBroadcastHex = null;
    FlutterSecureStorage.setMockInitialValues({});
  });

  test('imports a wallet and derives the index-0 address', () async {
    final c = makeController();
    await c.importExisting(_mnemonic, network: BigCoinNetwork.testnet);
    expect(c.hasWallet, isTrue);
    expect(c.receiveAddress, _addr0);
    expect(await c.store.hasWallet(), isTrue);
  });

  test('createNew persists and produces a tbig1 address', () async {
    final c = makeController();
    final phrase = await c.createNew(network: BigCoinNetwork.testnet);
    expect(phrase.split(' ').length, 12);
    expect(c.receiveAddress.startsWith('tbig1'), isTrue);

    // A fresh controller should load the same wallet back from storage.
    final c2 = makeController();
    expect(await c2.loadExisting(), isTrue);
    expect(c2.receiveAddress, c.receiveAddress);
  });

  test('refresh loads status and balance', () async {
    final c = makeController();
    await c.importExisting(_mnemonic, network: BigCoinNetwork.testnet);
    await c.refresh();
    expect(c.status?.chain, 'test');
    expect(c.balance?.total, 50.0);
    expect(c.error, isNull);
  });

  test('send builds, signs, and broadcasts a tx', () async {
    final c = makeController();
    await c.importExisting(_mnemonic, network: BigCoinNetwork.testnet);
    final txid = await c.send(toAddress: _dest, amountSats: 100000000);
    expect(txid, 'deadbeef');
    // The broadcast payload must be a real signed tx hex (segwit marker 0001).
    expect(lastBroadcastHex, isNotNull);
    expect(lastBroadcastHex!.startsWith('02000000'), isTrue);
    expect(lastBroadcastHex!.contains('0001'), isTrue);
  });

  test('rejects an invalid mnemonic import', () async {
    final c = makeController();
    expect(
      () => c.importExisting('not a valid phrase'),
      throwsArgumentError,
    );
  });
}
