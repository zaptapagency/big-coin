import 'dart:typed_data';

import 'package:bip39/bip39.dart' as bip39;
import 'package:coinslib/coinslib.dart';

import 'bigcoin_network.dart';

/// A single derived Big Coin key/address, ready to show, receive to, or spend.
class BigCoinAccount {
  final int index;
  final String derivationPath;

  /// Native SegWit (bech32) address — the primary receive address ("big1…").
  final String bech32Address;

  /// Legacy P2PKH address (starts with the pubKeyHash version byte).
  final String legacyAddress;

  /// Compressed public key (hex) — safe to share.
  final String publicKeyHex;

  /// WIF-encoded private key — SECRET. Only used locally for signing.
  final String wif;

  const BigCoinAccount({
    required this.index,
    required this.derivationPath,
    required this.bech32Address,
    required this.legacyAddress,
    required this.publicKeyHex,
    required this.wif,
  });
}

/// Non-custodial, on-device HD wallet for Big Coin.
///
/// All key material is derived locally from a BIP39 mnemonic; nothing leaves
/// the device. Addresses follow BIP84 (native SegWit, `big1…`) using Big Coin's
/// own network parameters ([BigCoinNetwork]).
///
/// Derivation path: `m/84'/<coinType>'/0'/0/<index>`
///   - mainnet coinType 2 (Litecoin-lineage fork)
///   - testnet coinType 1 (BIP44 test convention)
class HdWalletService {
  final BigCoinNetwork network;

  HdWalletService(this.network);

  static const int _mainnetCoinType = 2;
  static const int _testnetCoinType = 1;

  int get _coinType =>
      network.isTestnet ? _testnetCoinType : _mainnetCoinType;

  /// BIP84 account-level path prefix for this network.
  String get accountPath => "m/84'/$_coinType'/0'/0";

  /// Full external-chain path for a receive [index].
  String derivationPathForIndex(int index) => "$accountPath/$index";

  // --- Mnemonic helpers -------------------------------------------------

  /// Generates a fresh BIP39 mnemonic. 128 bits => 12 words, 256 => 24 words.
  String generateMnemonic({int strengthBits = 128}) =>
      bip39.generateMnemonic(strength: strengthBits);

  /// True if [mnemonic] is a valid BIP39 phrase (words + checksum).
  bool validateMnemonic(String mnemonic) =>
      bip39.validateMnemonic(mnemonic.trim());

  // --- Derivation -------------------------------------------------------

  /// Root HD node for a mnemonic on this network.
  HDWallet _root(String mnemonic, {String passphrase = ''}) {
    final normalized = mnemonic.trim();
    if (!bip39.validateMnemonic(normalized)) {
      throw ArgumentError('Invalid BIP39 mnemonic');
    }
    final Uint8List seed =
        bip39.mnemonicToSeed(normalized, passphrase: passphrase);
    return HDWallet.fromSeed(seed, network: network.coins);
  }

  /// Derives the receive account at [index] (default 0) from [mnemonic].
  BigCoinAccount deriveAccount(
    String mnemonic, {
    int index = 0,
    String passphrase = '',
  }) {
    final path = derivationPathForIndex(index);
    final node = _root(mnemonic, passphrase: passphrase).derivePath(path);

    final bech32 =
        P2WPKH.fromPublicKey(node.pubKeyBytes).address(network.coins);

    return BigCoinAccount(
      index: index,
      derivationPath: path,
      bech32Address: bech32,
      legacyAddress: node.address,
      publicKeyHex: node.pubKey,
      wif: node.wif!,
    );
  }

  /// Derives a contiguous range of accounts `[start, start+count)`.
  List<BigCoinAccount> deriveAccounts(
    String mnemonic, {
    int start = 0,
    int count = 1,
    String passphrase = '',
  }) {
    final normalized = mnemonic.trim();
    if (!bip39.validateMnemonic(normalized)) {
      throw ArgumentError('Invalid BIP39 mnemonic');
    }
    final seed = bip39.mnemonicToSeed(normalized, passphrase: passphrase);
    final root = HDWallet.fromSeed(seed, network: network.coins);

    return List<BigCoinAccount>.generate(count, (i) {
      final index = start + i;
      final path = derivationPathForIndex(index);
      final node = root.derivePath(path);
      final bech32 =
          P2WPKH.fromPublicKey(node.pubKeyBytes).address(network.coins);
      return BigCoinAccount(
        index: index,
        derivationPath: path,
        bech32Address: bech32,
        legacyAddress: node.address,
        publicKeyHex: node.pubKey,
        wif: node.wif!,
      );
    });
  }
}
