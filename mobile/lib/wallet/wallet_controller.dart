import 'package:flutter/foundation.dart';

import '../models/chain_models.dart';
import '../services/chain_service.dart';
import 'bigcoin_network.dart';
import 'hd_wallet_service.dart';
import 'secure_key_store.dart';
import 'tx_builder.dart';

/// Orchestrates the non-custodial wallet: key storage, derivation, balance
/// refresh, and on-device signing + broadcast. UI observes this via Provider.
///
/// A single external receive address (BIP84 index 0) is used; change returns
/// to the same address. Keys never leave the device — [ChainService] only
/// fetches chain state and relays already-signed transactions.
class WalletController extends ChangeNotifier {
  final ChainService chain;
  final SecureKeyStore store;

  WalletController({
    required this.chain,
    SecureKeyStore? store,
  }) : store = store ?? SecureKeyStore();

  BigCoinNetwork _network = BigCoinNetwork.testnet;
  String? _mnemonic;
  BigCoinAccount? _account;
  WalletBalance? _balance;
  ChainStatus? _status;
  bool _busy = false;
  String? _error;

  BigCoinNetwork get network => _network;
  BigCoinAccount? get account => _account;
  WalletBalance? get balance => _balance;
  ChainStatus? get status => _status;
  bool get busy => _busy;
  String? get error => _error;
  bool get hasWallet => _account != null;

  String get receiveAddress => _account?.bech32Address ?? '';

  HdWalletService get _hd => HdWalletService(_network);

  void _set({bool? busy, String? error, bool clearError = false}) {
    if (busy != null) _busy = busy;
    if (clearError) _error = null;
    if (error != null) _error = error;
    notifyListeners();
  }

  /// Loads a previously-created wallet from secure storage, if any.
  Future<bool> loadExisting() async {
    if (!await store.hasWallet()) return false;
    final mnemonic = await store.readMnemonic();
    final netId = await store.readNetworkId();
    if (mnemonic == null) return false;
    _network = BigCoinNetwork.byId(netId);
    _mnemonic = mnemonic;
    _account = _hd.deriveAccount(mnemonic, index: 0);
    notifyListeners();
    return true;
  }

  /// Creates a brand-new wallet on [network] and persists it.
  Future<String> createNew({
    BigCoinNetwork? network,
    int strengthBits = 128,
  }) async {
    _network = network ?? _network;
    final mnemonic = _hd.generateMnemonic(strengthBits: strengthBits);
    await _persistAndDerive(mnemonic);
    return mnemonic;
  }

  /// Imports an existing BIP39 mnemonic. Throws [ArgumentError] if invalid.
  Future<void> importExisting(String mnemonic, {BigCoinNetwork? network}) async {
    _network = network ?? _network;
    final normalized = mnemonic.trim();
    if (!_hd.validateMnemonic(normalized)) {
      throw ArgumentError('Invalid recovery phrase');
    }
    await _persistAndDerive(normalized);
  }

  Future<void> _persistAndDerive(String mnemonic) async {
    await store.saveWallet(mnemonic: mnemonic, networkId: _network.id);
    _mnemonic = mnemonic;
    _account = _hd.deriveAccount(mnemonic, index: 0);
    notifyListeners();
  }

  /// Refreshes chain status and this wallet's balance.
  Future<void> refresh() async {
    if (_account == null) return;
    _set(busy: true, clearError: true);
    try {
      final results = await Future.wait([
        chain.getStatus(),
        chain.getBalance(_account!.bech32Address),
      ]);
      _status = results[0] as ChainStatus;
      _balance = results[1] as WalletBalance;
    } catch (e) {
      _error = e.toString();
    } finally {
      _set(busy: false);
    }
  }

  /// Builds, signs (on-device), and broadcasts a payment of [amountSats] sats
  /// (1 BIG = 1e8 sats) to [toAddress]. Returns the accepted txid.
  Future<String> send({
    required String toAddress,
    required int amountSats,
  }) async {
    final account = _account;
    final mnemonic = _mnemonic;
    if (account == null || mnemonic == null) {
      throw StateError('No wallet loaded');
    }
    _set(busy: true, clearError: true);
    try {
      final utxos = await chain.getUtxos(account.bech32Address);
      final feeBigPerKb = await chain.getFeeRate();
      final feeSatPerVByte = feeBigPerKb * 1e8 / 1000;

      final signed = TxBuilder(_network).buildSpend(
        utxos: utxos,
        toAddress: toAddress,
        amountSats: amountSats,
        changeAddress: account.bech32Address,
        wif: account.wif,
        feeRateSatPerVByte: feeSatPerVByte,
      );

      final txid = await chain.broadcast(signed.rawHex);
      await refresh();
      return txid;
    } finally {
      _set(busy: false);
    }
  }

  /// Permanently removes the wallet from the device.
  Future<void> wipe() async {
    await store.wipe();
    _mnemonic = null;
    _account = null;
    _balance = null;
    _status = null;
    notifyListeners();
  }
}
