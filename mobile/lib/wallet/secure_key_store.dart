import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Encrypted, on-device storage for the wallet's secret material.
///
/// Backed by the platform keystore (Android EncryptedSharedPreferences /
/// iOS Keychain). The BIP39 mnemonic is the ONLY secret persisted — every
/// address and private key is re-derived from it on demand, so nothing else
/// needs to touch disk.
class SecureKeyStore {
  static const _mnemonicKey = 'bigcoin.mnemonic';
  static const _networkKey = 'bigcoin.network'; // "mainnet" | "testnet"

  final FlutterSecureStorage _storage;

  SecureKeyStore([FlutterSecureStorage? storage])
      : _storage = storage ??
            const FlutterSecureStorage(
              aOptions: AndroidOptions(encryptedSharedPreferences: true),
              iOptions: IOSOptions(
                accessibility: KeychainAccessibility.first_unlock_this_device,
              ),
            );

  /// True once a wallet has been created/imported on this device.
  Future<bool> hasWallet() async =>
      (await _storage.read(key: _mnemonicKey)) != null;

  /// Persists the mnemonic and its network. Overwrites any existing wallet.
  Future<void> saveWallet({
    required String mnemonic,
    required String networkId,
  }) async {
    await _storage.write(key: _mnemonicKey, value: mnemonic.trim());
    await _storage.write(key: _networkKey, value: networkId);
  }

  /// Returns the stored mnemonic, or null if no wallet exists.
  Future<String?> readMnemonic() => _storage.read(key: _mnemonicKey);

  /// Returns the stored network id, defaulting to "testnet" for safety.
  Future<String> readNetworkId() async =>
      (await _storage.read(key: _networkKey)) ?? 'testnet';

  /// Permanently deletes all wallet secrets from the device.
  Future<void> wipe() async {
    await _storage.delete(key: _mnemonicKey);
    await _storage.delete(key: _networkKey);
  }
}
