import 'package:flutter_test/flutter_test.dart';

import 'package:bigcoin_mobile/models/chain_models.dart';
import 'package:bigcoin_mobile/wallet/bigcoin_network.dart';
import 'package:bigcoin_mobile/wallet/hd_wallet_service.dart';
import 'package:bigcoin_mobile/wallet/tx_builder.dart';

const _mnemonic =
    'abandon abandon abandon abandon abandon abandon '
    'abandon abandon abandon abandon abandon about';

// Verified via `bigcoind -testnet validateaddress` for the index-0 test-vector
// key: tbig1q6rz28mcfaxtmd6v789l9rrlrusdprr9pdc24tr => this scriptPubKey.
const _spk0 = '0014d0c4a3ef09e997b6e99e397e518fe3e41a118ca1';
const _fakeTxid =
    '1111111111111111111111111111111111111111111111111111111111111111';

void main() {
  final net = BigCoinNetwork.testnet;
  final svc = HdWalletService(net);
  final builder = TxBuilder(net);

  final acct0 = svc.deriveAccount(_mnemonic, index: 0);
  final acct1 = svc.deriveAccount(_mnemonic, index: 1);

  Utxo utxo(double big, {int vout = 0}) => Utxo(
        txid: _fakeTxid,
        vout: vout,
        amount: big,
        scriptPubKey: _spk0,
        height: 100,
        confirmations: 120,
      );

  test('builds a signed spend with change', () {
    final signed = builder.buildSpend(
      utxos: [utxo(50.0)],
      toAddress: acct1.bech32Address,
      amountSats: 100000000, // 1 BIG
      changeAddress: acct0.bech32Address,
      wif: acct0.wif,
      feeRateSatPerVByte: 1.0,
    );

    expect(signed.rawHex, isNotEmpty);
    expect(signed.txid.length, 64);
    expect(signed.inputs.length, 1);
    expect(signed.feeSats, greaterThan(0));
    // one input, two outputs ~141 vbytes at 1 sat/vB
    expect(signed.feeSats, inInclusiveRange(120, 170));
    // change = 50 BIG - 1 BIG - fee
    expect(signed.changeSats, 5000000000 - 100000000 - signed.feeSats);
  });

  test('fee scales with fee rate', () {
    final low = builder.buildSpend(
      utxos: [utxo(50.0)],
      toAddress: acct1.bech32Address,
      amountSats: 100000000,
      changeAddress: acct0.bech32Address,
      wif: acct0.wif,
      feeRateSatPerVByte: 1.0,
    );
    final high = builder.buildSpend(
      utxos: [utxo(50.0)],
      toAddress: acct1.bech32Address,
      amountSats: 100000000,
      changeAddress: acct0.bech32Address,
      wif: acct0.wif,
      feeRateSatPerVByte: 10.0,
    );
    expect(high.feeSats, greaterThan(low.feeSats * 5));
  });

  test('selects multiple inputs when needed', () {
    final signed = builder.buildSpend(
      utxos: [utxo(1.0, vout: 0), utxo(1.0, vout: 1), utxo(1.0, vout: 2)],
      toAddress: acct1.bech32Address,
      amountSats: 250000000, // 2.5 BIG => needs 3 inputs
      changeAddress: acct0.bech32Address,
      wif: acct0.wif,
      feeRateSatPerVByte: 1.0,
    );
    expect(signed.inputs.length, 3);
  });

  test('throws on insufficient funds', () {
    expect(
      () => builder.buildSpend(
        utxos: [utxo(0.5)],
        toAddress: acct1.bech32Address,
        amountSats: 100000000, // want 1 BIG, only 0.5 available
        changeAddress: acct0.bech32Address,
        wif: acct0.wif,
        feeRateSatPerVByte: 1.0,
      ),
      throwsA(isA<InsufficientFundsException>()),
    );
  });

  test('drops dust change into the fee', () {
    // Pick an amount so the remainder after a normal fee is below dust.
    // 1 BIG utxo, send (1 BIG - 150 sats): change would be ~ (150 - fee) < dust.
    final signed = builder.buildSpend(
      utxos: [utxo(1.0)],
      toAddress: acct1.bech32Address,
      amountSats: 100000000 - 150,
      changeAddress: acct0.bech32Address,
      wif: acct0.wif,
      feeRateSatPerVByte: 1.0,
    );
    expect(signed.changeSats, 0);
    // Entire remainder becomes fee.
    expect(signed.feeSats, 150);
  });

  // Boundary: change output is created only once the leftover after the
  // 2-output fee (141 vB @ 1 sat/vB) is at least one dust (294). That happens
  // when remainder = amount leftover in the input >= 141 + 294 = 435 sats.
  test('keeps change exactly at the dust boundary (remainder 435)', () {
    final signed = builder.buildSpend(
      utxos: [utxo(1.0)],
      toAddress: acct1.bech32Address,
      amountSats: 100000000 - 435,
      changeAddress: acct0.bech32Address,
      wif: acct0.wif,
      feeRateSatPerVByte: 1.0,
    );
    expect(signed.feeSats, 141);
    expect(signed.changeSats, 294);
  });

  test('folds change into fee one sat below the boundary (remainder 434)', () {
    final signed = builder.buildSpend(
      utxos: [utxo(1.0)],
      toAddress: acct1.bech32Address,
      amountSats: 100000000 - 434,
      changeAddress: acct0.bech32Address,
      wif: acct0.wif,
      feeRateSatPerVByte: 1.0,
    );
    expect(signed.changeSats, 0);
    expect(signed.feeSats, 434);
  });

  test('sending the entire balance throws (cannot cover the fee)', () {
    expect(
      () => builder.buildSpend(
        utxos: [utxo(1.0)],
        toAddress: acct1.bech32Address,
        amountSats: 100000000, // no room left for any fee
        changeAddress: acct0.bech32Address,
        wif: acct0.wif,
        feeRateSatPerVByte: 1.0,
      ),
      throwsA(isA<InsufficientFundsException>()),
    );
  });
}
