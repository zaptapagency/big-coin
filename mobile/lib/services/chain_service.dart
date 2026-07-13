import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/chain_models.dart';

/// Read/relay client for the Big Coin explorer JSON API.
///
/// This service NEVER sees private keys. The wallet derives keys and signs
/// transactions on-device (see `wallet/`); this class only fetches chain state
/// and relays already-signed raw transactions.
class ChainService {
  /// Live explorer (demo data until a real bigcoind backend is wired up).
  static const String defaultBaseUrl =
      'https://big-coin-production.up.railway.app';

  String baseUrl;
  final http.Client _http;
  final Duration timeout;

  ChainService({
    String? baseUrl,
    http.Client? httpClient,
    this.timeout = const Duration(seconds: 15),
  })  : baseUrl = (baseUrl ?? defaultBaseUrl).replaceAll(RegExp(r'/+$'), ''),
        _http = httpClient ?? http.Client();

  void setBaseUrl(String url) =>
      baseUrl = url.replaceAll(RegExp(r'/+$'), '');

  Uri _u(String path) => Uri.parse('$baseUrl$path');

  Map<String, dynamic> _decode(http.Response r) {
    final body = r.body.isEmpty ? '{}' : r.body;
    final Map<String, dynamic> json = jsonDecode(body) as Map<String, dynamic>;
    if (r.statusCode >= 400) {
      throw ChainApiException(
        (json['error'] ?? 'HTTP ${r.statusCode}').toString(),
        r.statusCode,
      );
    }
    return json;
  }

  /// Chain tip + node summary.
  Future<ChainStatus> getStatus() async {
    final r = await _http.get(_u('/api/status')).timeout(timeout);
    return ChainStatus.fromJson(_decode(r));
  }

  /// Spendable outputs for [address] (via server-side scantxoutset).
  Future<List<Utxo>> getUtxos(String address) async {
    final r =
        await _http.get(_u('/api/address/$address/utxos')).timeout(timeout);
    final json = _decode(r);
    final list = (json['utxos'] as List?) ?? const [];
    return list
        .map((e) => Utxo.fromJson(e as Map<String, dynamic>))
        .toList(growable: false);
  }

  /// Confirmed / unconfirmed / total balance for [address].
  Future<WalletBalance> getBalance(String address) async {
    final r =
        await _http.get(_u('/api/address/$address/balance')).timeout(timeout);
    return WalletBalance.fromJson(_decode(r));
  }

  /// Suggested fee rate in BIG per kB.
  Future<double> getFeeRate() async {
    final r = await _http.get(_u('/api/fee')).timeout(timeout);
    final json = _decode(r);
    return (json['feerate'] ?? 0.00001).toDouble();
  }

  /// Relays a fully-signed raw transaction; returns the accepted txid.
  Future<String> broadcast(String rawTxHex) async {
    final r = await _http
        .post(
          _u('/api/tx/broadcast'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'rawtx': rawTxHex}),
        )
        .timeout(timeout);
    final json = _decode(r);
    return (json['txid'] ?? '').toString();
  }

  /// Decoded transaction JSON as returned by the node.
  Future<Map<String, dynamic>> getTransaction(String txid) async {
    final r = await _http.get(_u('/api/tx/$txid')).timeout(timeout);
    return _decode(r);
  }
}

class ChainApiException implements Exception {
  final String message;
  final int statusCode;
  ChainApiException(this.message, this.statusCode);
  @override
  String toString() => 'ChainApiException($statusCode): $message';
}
