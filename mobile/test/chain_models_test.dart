import 'package:flutter_test/flutter_test.dart';

import 'package:bigcoin_mobile/models/chain_models.dart';

void main() {
  group('ChainStatus', () {
    test('parses a demo /api/status payload', () {
      final s = ChainStatus.fromJson({
        'chain': 'main',
        'blocks': 11,
        'headers': 11,
        'bestblockhash': 'd9cb...22fb',
        'difficulty': 1.0033,
        'verificationprogress': 1.0,
        'mempool_txs': 2,
        'connections': 8,
        'subversion': '/BigCoin:2.5.0/',
        'demo': true,
      });
      expect(s.chain, 'main');
      expect(s.blocks, 11);
      expect(s.demo, isTrue);
      expect(s.isSynced, isTrue);
    });

    test('reports not-synced while headers exceed blocks', () {
      final s = ChainStatus.fromJson({'blocks': 100, 'headers': 500});
      expect(s.isSynced, isFalse);
    });
  });

  group('Utxo', () {
    test('parses and converts amount to sats', () {
      final u = Utxo.fromJson({
        'txid': 'aa',
        'vout': 1,
        'amount': 12.5,
        'scriptPubKey': '0014abcd',
        'height': 90,
        'confirmations': 12,
      });
      expect(u.vout, 1);
      expect(u.amountSats, 1250000000);
      expect(u.confirmations, 12);
    });
  });

  group('WalletBalance', () {
    test('parses a zero demo balance', () {
      final b = WalletBalance.fromJson({
        'address': 'tbig1qxyz',
        'confirmed': 0,
        'unconfirmed': 0,
        'total': 0,
        'utxo_count': 0,
        'demo': true,
      });
      expect(b.total, 0);
      expect(b.utxoCount, 0);
      expect(b.demo, isTrue);
    });
  });
}
