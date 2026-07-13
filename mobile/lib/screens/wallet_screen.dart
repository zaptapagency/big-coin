import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../wallet/wallet_controller.dart';

/// Receive tab: shows balance, the receive address + QR, and a refresh action.
class WalletScreen extends StatelessWidget {
  const WalletScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final wallet = context.watch<WalletController>();
    final balance = wallet.balance;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Wallet'),
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
          padding: const EdgeInsets.all(20),
          children: [
            if (wallet.status?.demo ?? false) const _DemoBanner(),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  children: [
                    const Text('Balance',
                        style: TextStyle(color: Colors.white54)),
                    const SizedBox(height: 8),
                    Text(
                      balance == null
                          ? '—'
                          : '${balance.total.toStringAsFixed(8)} BIG',
                      style: const TextStyle(
                          fontSize: 28, fontWeight: FontWeight.bold),
                    ),
                    if (balance != null && balance.unconfirmed != 0) ...[
                      const SizedBox(height: 4),
                      Text(
                        '${balance.unconfirmed.toStringAsFixed(8)} unconfirmed',
                        style: const TextStyle(
                            color: Colors.amber, fontSize: 12),
                      ),
                    ],
                    const SizedBox(height: 4),
                    Text(
                      'Network: ${wallet.network.id}',
                      style: const TextStyle(
                          color: Colors.white38, fontSize: 12),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),
            const Text('Receive address',
                style: TextStyle(color: Colors.white54)),
            const SizedBox(height: 12),
            Center(
              child: Container(
                padding: const EdgeInsets.all(12),
                color: Colors.white,
                child: QrImageView(
                  data: wallet.receiveAddress,
                  size: 200,
                  backgroundColor: Colors.white,
                ),
              ),
            ),
            const SizedBox(height: 16),
            SelectableText(
              wallet.receiveAddress,
              textAlign: TextAlign.center,
              style: const TextStyle(fontFamily: 'monospace', fontSize: 13),
            ),
            const SizedBox(height: 8),
            Center(
              child: TextButton.icon(
                icon: const Icon(Icons.copy, size: 18),
                label: const Text('Copy address'),
                onPressed: () {
                  Clipboard.setData(
                      ClipboardData(text: wallet.receiveAddress));
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Address copied')),
                  );
                },
              ),
            ),
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
              'Explorer is in demo mode — balances are not live yet.',
              style: TextStyle(color: Colors.amber, fontSize: 12),
            ),
          ),
        ],
      ),
    );
  }
}
