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
  })  : baseUrl = _sanitizeBaseUrl(baseUrl ?? defaultBaseUrl),
        _http = httpClient ?? http.Client();

  void setBaseUrl(String url) => baseUrl = _sanitizeBaseUrl(url);

  /// Normalizes a base URL and enforces HTTPS so wallet traffic (addresses,
  /// balances, signed transactions) is never sent in cleartext. Plain `http`
  /// is allowed only for loopback hosts, for local development against a node.
  static String _sanitizeBaseUrl(String url) {
    final trimmed = url.trim().replaceAll(RegExp(r'/+$'), '');
    final uri = Uri.tryParse(trimmed);
    if (uri == null || !uri.hasScheme || uri.host.isEmpty) {
      throw ArgumentError('Invalid explorer URL: $url');
    }
    final isLoopback =
        uri.host == 'localhost' || uri.host == '127.0.0.1' || uri.host == '::1';
    if (uri.scheme == 'http' && !isLoopback) {
      throw ArgumentError(
          'Refusing insecure http:// explorer URL (use https): $url');
    }
    if (uri.scheme != 'https' && uri.scheme != 'http') {
      throw ArgumentError('Unsupported explorer URL scheme: ${uri.scheme}');
    }
    return trimmed;
  }

  Uri _u(String path) => Uri.parse('$baseUrl$path');

  Map<String, dynamic> _decode(http.Response r) {
    final body = r.body.isEmpty ? '{}' : r.body;
    Object? parsed;
    try {
      parsed = jsonDecode(body);
    } catch (_) {
      // Non-JSON body (e.g. a gateway HTML error page). Surface a clean API
      // exception instead of leaking a raw FormatException.
      throw ChainApiException(
        r.statusCode >= 400
            ? 'HTTP ${r.statusCode}'
            : 'Malformed response from explorer',
        r.statusCode,
      );
    }
    if (parsed is! Map<String, dynamic>) {
      throw ChainApiException(
        'Unexpected response shape from explorer',
        r.statusCode,
      );
    }
    if (r.statusCode >= 400) {
      throw ChainApiException(
        (parsed['error'] ?? 'HTTP ${r.statusCode}').toString(),
        r.statusCode,
      );
    }
    return parsed;
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
