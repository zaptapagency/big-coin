import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../wallet/wallet_controller.dart';

/// Chain tab: shows node/chain status (height, tip hash, difficulty, peers,
/// mempool) from the explorer API via [WalletController].
class BlockchainScreen extends StatelessWidget {
  const BlockchainScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final wallet = context.watch<WalletController>();
    final status = wallet.status;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Chain'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: wallet.busy ? null : () => wallet.refresh(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => wallet.refresh(),
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (status == null) ...[
              const SizedBox(height: 80),
              Center(
                child: wallet.busy
                    ? const CircularProgressIndicator()
                    : const Text(
                        'No chain data yet. Pull to refresh.',
                        style: TextStyle(color: Colors.white38),
                      ),
              ),
            ] else ...[
              if (status.demo) const _DemoBanner(),
              _StatusCard(
                icon: Icons.layers,
                title: 'Block height',
                value: status.blocks.toString(),
                subtitle: status.isSynced
                    ? 'synced'
                    : 'syncing — ${status.headers} headers',
              ),
              const SizedBox(height: 12),
              _StatusCard(
                icon: Icons.link,
                title: 'Chain',
                value: status.chain,
                subtitle: 'network: ${wallet.network.id}',
              ),
              const SizedBox(height: 12),
              _StatusCard(
                icon: Icons.fingerprint,
                title: 'Best block hash',
                value: status.bestBlockHash.isEmpty
                    ? '—'
                    : status.bestBlockHash,
                subtitle: 'chain tip',
                monospace: true,
              ),
              const SizedBox(height: 12),
              _StatusCard(
                icon: Icons.speed,
                title: 'Difficulty',
                value: status.difficulty.toStringAsFixed(4),
                subtitle:
                    'verification ${(status.verificationProgress * 100).toStringAsFixed(2)}%',
              ),
              const SizedBox(height: 12),
              _StatusCard(
                icon: Icons.people,
                title: 'Connections',
                value: status.connections.toString(),
                subtitle: 'peers',
              ),
              const SizedBox(height: 12),
              _StatusCard(
                icon: Icons.pending_actions,
                title: 'Mempool',
                value: status.mempoolTxs.toString(),
                subtitle: 'unconfirmed transactions',
              ),
              if (status.subversion.isNotEmpty) ...[
                const SizedBox(height: 12),
                _StatusCard(
                  icon: Icons.dns,
                  title: 'Node',
                  value: status.subversion,
                  subtitle: 'user agent',
                ),
              ],
            ],
            if (wallet.error != null) ...[
              const SizedBox(height: 16),
              Text(wallet.error!,
                  style: const TextStyle(color: Colors.redAccent)),
            ],
          ],
        ),
      ),
    );
  }
}

class _StatusCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String value;
  final String subtitle;
  final bool monospace;

  const _StatusCard({
    required this.icon,
    required this.title,
    required this.value,
    required this.subtitle,
    this.monospace = false,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: const Color(0xFF1F6FD9), size: 24),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                        fontSize: 12, color: Colors.white54),
                  ),
                  const SizedBox(height: 4),
                  SelectableText(
                    value,
                    style: TextStyle(
                      fontSize: monospace ? 12 : 16,
                      fontWeight: FontWeight.bold,
                      fontFamily: monospace ? 'monospace' : null,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    subtitle,
                    style: const TextStyle(
                        fontSize: 11, color: Colors.white38),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _DemoBanner extends StatelessWidget {
  const _DemoBanner();

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.amber.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(8),
      ),
      child: const Row(
        children: [
          Icon(Icons.info_outline, color: Colors.amber, size: 20),
          SizedBox(width: 8),
          Expanded(
            child: Text(
              'Explorer is in demo mode — chain data is not live yet.',
              style: TextStyle(color: Colors.amber, fontSize: 12),
            ),
          ),
        ],
      ),
    );
  }
}
