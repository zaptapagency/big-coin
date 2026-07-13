import 'package:flutter_test/flutter_test.dart';

import 'package:bigcoin_mobile/wallet/bigcoin_network.dart';
import 'package:bigcoin_mobile/wallet/hd_wallet_service.dart';

/// Standard BIP39 test vector mnemonic (all-zero entropy). Deterministic, so
/// the derived addresses below are fixed for a given set of network params.
const _testVectorMnemonic =
    'abandon abandon abandon abandon abandon abandon '
    'abandon abandon abandon abandon abandon about';

void main() {
  group('BigCoinNetwork params', () {
    test('mainnet uses big bech32 + Litecoin-fork version bytes', () {
      final n = BigCoinNetwork.mainnet.coins;
      expect(n.bech32, 'big');
      expect(n.pubKeyHash, 25);
      expect(n.scriptHash, 5);
      expect(n.wif, 176);
      expect(n.bip32.public, 0x0488b21e);
      expect(n.bip32.private, 0x0488ade4);
    });

    test('testnet uses tbig bech32 + testnet version bytes', () {
      final n = BigCoinNetwork.testnet.coins;
      expect(n.bech32, 'tbig');
      expect(n.pubKeyHash, 111);
      expect(n.scriptHash, 196);
      expect(n.wif, 239);
      expect(n.bip32.public, 0x043587cf);
      expect(n.bip32.private, 0x04358394);
    });

    test('byId round-trips and defaults to mainnet', () {
      expect(BigCoinNetwork.byId('testnet').isTestnet, isTrue);
      expect(BigCoinNetwork.byId('mainnet').isTestnet, isFalse);
      expect(BigCoinNetwork.byId('anything-else').id, 'mainnet');
    });
  });

  group('Mnemonic', () {
    final svc = HdWalletService(BigCoinNetwork.testnet);

    test('generates a valid 12-word phrase by default', () {
      final m = svc.generateMnemonic();
      expect(m.split(' ').length, 12);
      expect(svc.validateMnemonic(m), isTrue);
    });

    test('generates a valid 24-word phrase at 256 bits', () {
      final m = svc.generateMnemonic(strengthBits: 256);
      expect(m.split(' ').length, 24);
      expect(svc.validateMnemonic(m), isTrue);
    });

    test('rejects a tampered phrase', () {
      expect(svc.validateMnemonic('not a real mnemonic phrase at all'),
          isFalse);
    });

    test('tolerates surrounding whitespace', () {
      expect(svc.validateMnemonic('  $_testVectorMnemonic  '), isTrue);
    });
  });

  group('Derivation — testnet', () {
    final svc = HdWalletService(BigCoinNetwork.testnet);

    test('uses BIP84 path with testnet coin type 1', () {
      expect(svc.accountPath, "m/84'/1'/0'/0");
      expect(svc.derivationPathForIndex(3), "m/84'/1'/0'/0/3");
    });

    test('produces a tbig1 bech32 receive address', () {
      final acct = svc.deriveAccount(_testVectorMnemonic);
      expect(acct.bech32Address.startsWith('tbig1'), isTrue,
          reason: 'got ${acct.bech32Address}');
      expect(acct.publicKeyHex.length, 66); // 33-byte compressed pubkey
      expect(acct.wif, isNotEmpty);
      expect(acct.derivationPath, "m/84'/1'/0'/0/0");
    });

    test('is deterministic for the same mnemonic + index', () {
      final a = svc.deriveAccount(_testVectorMnemonic);
      final b = svc.deriveAccount(_testVectorMnemonic);
      expect(a.bech32Address, b.bech32Address);
      expect(a.wif, b.wif);
      expect(a.publicKeyHex, b.publicKeyHex);
    });

    test('different indexes yield different addresses', () {
      final a0 = svc.deriveAccount(_testVectorMnemonic, index: 0);
      final a1 = svc.deriveAccount(_testVectorMnemonic, index: 1);
      expect(a0.bech32Address, isNot(a1.bech32Address));
      expect(a0.wif, isNot(a1.wif));
    });

    test('deriveAccounts range matches single derivations', () {
      final batch = svc.deriveAccounts(_testVectorMnemonic, count: 3);
      expect(batch.length, 3);
      for (var i = 0; i < 3; i++) {
        final single = svc.deriveAccount(_testVectorMnemonic, index: i);
        expect(batch[i].bech32Address, single.bech32Address);
        expect(batch[i].index, i);
      }
    });

    test('rejects an invalid mnemonic on derive', () {
      expect(() => svc.deriveAccount('totally invalid words'),
          throwsArgumentError);
    });
  });

  group('Derivation — mainnet', () {
    final svc = HdWalletService(BigCoinNetwork.mainnet);

    test('uses BIP84 path with mainnet coin type 2', () {
      expect(svc.accountPath, "m/84'/2'/0'/0");
    });

    test('produces a big1 bech32 receive address', () {
      final acct = svc.deriveAccount(_testVectorMnemonic);
      expect(acct.bech32Address.startsWith('big1'), isTrue,
          reason: 'got ${acct.bech32Address}');
    });

    test('mainnet and testnet derive different addresses from same seed', () {
      final mainAddr = svc.deriveAccount(_testVectorMnemonic).bech32Address;
      final testAddr = HdWalletService(BigCoinNetwork.testnet)
          .deriveAccount(_testVectorMnemonic)
          .bech32Address;
      expect(mainAddr, isNot(testAddr));
    });
  });
}
