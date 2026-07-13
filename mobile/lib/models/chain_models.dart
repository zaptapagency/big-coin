/// Plain data models for the Big Coin explorer JSON API (`/api/*`).
///
/// Hand-written (no codegen) to keep the build simple. Shapes mirror the
/// Flask blueprint in `explorer/api.py`.
library;

/// Chain tip + node summary from `GET /api/status`.
class ChainStatus {
  final String chain;
  final int blocks;
  final int headers;
  final String bestBlockHash;
  final double difficulty;
  final double verificationProgress;
  final int mempoolTxs;
  final int connections;
  final String subversion;
  final bool demo;

  const ChainStatus({
    required this.chain,
    required this.blocks,
    required this.headers,
    required this.bestBlockHash,
    required this.difficulty,
    required this.verificationProgress,
    required this.mempoolTxs,
    required this.connections,
    required this.subversion,
    required this.demo,
  });

  bool get isSynced => headers == 0 || blocks >= headers;

  factory ChainStatus.fromJson(Map<String, dynamic> j) => ChainStatus(
        chain: (j['chain'] ?? '?').toString(),
        blocks: (j['blocks'] ?? 0) as int,
        headers: (j['headers'] ?? j['blocks'] ?? 0) as int,
        bestBlockHash: (j['bestblockhash'] ?? '').toString(),
        difficulty: (j['difficulty'] ?? 0).toDouble(),
        verificationProgress: (j['verificationprogress'] ?? 1.0).toDouble(),
        mempoolTxs: (j['mempool_txs'] ?? 0) as int,
        connections: (j['connections'] ?? 0) as int,
        subversion: (j['subversion'] ?? '').toString(),
        demo: (j['demo'] ?? false) as bool,
      );
}

/// One spendable output from `GET /api/address/<a>/utxos`.
class Utxo {
  final String txid;
  final int vout;
  final double amount; // BIG
  final String scriptPubKey; // hex
  final int? height;
  final int confirmations;

  const Utxo({
    required this.txid,
    required this.vout,
    required this.amount,
    required this.scriptPubKey,
    required this.height,
    required this.confirmations,
  });

  /// Amount in satoshi-equivalent (1 BIG = 1e8) for coin-selection math.
  int get amountSats => (amount * 1e8).round();

  factory Utxo.fromJson(Map<String, dynamic> j) => Utxo(
        txid: (j['txid'] ?? '').toString(),
        vout: (j['vout'] ?? 0) as int,
        amount: (j['amount'] ?? 0).toDouble(),
        scriptPubKey: (j['scriptPubKey'] ?? '').toString(),
        height: j['height'] as int?,
        confirmations: (j['confirmations'] ?? 0) as int,
      );
}

/// Aggregated balance from `GET /api/address/<a>/balance`.
class WalletBalance {
  final String address;
  final double confirmed;
  final double unconfirmed;
  final double total;
  final int utxoCount;
  final bool demo;

  const WalletBalance({
    required this.address,
    required this.confirmed,
    required this.unconfirmed,
    required this.total,
    required this.utxoCount,
    required this.demo,
  });

  factory WalletBalance.fromJson(Map<String, dynamic> j) => WalletBalance(
        address: (j['address'] ?? '').toString(),
        confirmed: (j['confirmed'] ?? 0).toDouble(),
        unconfirmed: (j['unconfirmed'] ?? 0).toDouble(),
        total: (j['total'] ?? 0).toDouble(),
        utxoCount: (j['utxo_count'] ?? 0) as int,
        demo: (j['demo'] ?? false) as bool,
      );
}
