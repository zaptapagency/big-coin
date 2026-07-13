import 'package:flutter_test/flutter_test.dart';

import 'package:bigcoin_mobile/wallet/address_script.dart';
import 'package:bigcoin_mobile/wallet/bigcoin_network.dart';
import 'package:bigcoin_mobile/wallet/hd_wallet_service.dart';

const _mnemonic =
    'abandon abandon abandon abandon abandon abandon '
    'abandon abandon abandon abandon abandon about';

void main() {
  final mainnet = BigCoinNetwork.mainnet;
  final testnet = BigCoinNetwork.testnet;

  final mainAddr =
      HdWalletService(mainnet).deriveAccount(_mnemonic).bech32Address; // big1…
  final testAddr =
      HdWalletService(testnet).deriveAccount(_mnemonic).bech32Address; // tbig1…

  group('AddressScript.forAddress', () {
    test('accepts a same-network bech32 address and builds a P2WPKH script', () {
      final script = AddressScript.forAddress(mainAddr, mainnet);
      // OP_0 <20-byte program>
      expect(script.length, 22);
      expect(script[0], 0x00);
      expect(script[1], 20);
    });

    test('rejects a mainnet address on the testnet network (HRP mismatch)', () {
      expect(
        () => AddressScript.forAddress(mainAddr, testnet),
        throwsFormatException,
      );
    });

    test('rejects a testnet address on the mainnet network (HRP mismatch)', () {
      expect(
        () => AddressScript.forAddress(testAddr, mainnet),
        throwsFormatException,
      );
    });

    test('rejects garbage input', () {
      expect(
        () => AddressScript.forAddress('not-an-address', mainnet),
        throwsFormatException,
      );
    });
  });
}
