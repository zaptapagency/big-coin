import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../wallet/bigcoin_network.dart';
import '../wallet/local_auth_service.dart';
import '../wallet/wallet_controller.dart';

/// First-run flow: create a new wallet (shows the recovery phrase to back up)
/// or import an existing BIP39 phrase. Defaults to testnet for safety.
class OnboardingScreen extends StatelessWidget {
  const OnboardingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Big Coin Wallet')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Spacer(),
            const Icon(Icons.account_balance_wallet,
                size: 72, color: Color(0xFF1F6FD9)),
            const SizedBox(height: 16),
            const Text(
              'A non-custodial wallet.\nYour keys stay on this device.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 16, color: Colors.white70),
            ),
            const Spacer(),
            FilledButton.icon(
              icon: const Icon(Icons.add),
              label: const Text('Create new wallet'),
              onPressed: () => _createWallet(context),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              icon: const Icon(Icons.download),
              label: const Text('Import recovery phrase'),
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const _ImportScreen()),
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              'Network: testnet (safe mode)',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 12, color: Colors.white38),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _createWallet(BuildContext context) async {
    final controller = context.read<WalletController>();
    final auth = context.read<LocalAuthService>();

    // Gate revealing the recovery phrase behind device auth when available.
    if (await auth.isAvailable()) {
      final ok = await auth.authenticate('Authenticate to reveal your recovery phrase');
      if (!ok) return;
    }

    final phrase =
        await controller.createNew(network: BigCoinNetwork.testnet);
    if (!context.mounted) return;
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => _BackupDialog(phrase: phrase),
    );
  }
}

class _BackupDialog extends StatelessWidget {
  final String phrase;
  const _BackupDialog({required this.phrase});

  @override
  Widget build(BuildContext context) {
    final words = phrase.split(' ');
    return AlertDialog(
      title: const Text('Back up your recovery phrase'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Write these 12 words down in order. Anyone with them controls '
              'your coins. They are never sent anywhere.\n\n'
              'For your safety this phrase cannot be copied — write it down '
              'by hand and store it offline.',
              style: TextStyle(color: Colors.white70, fontSize: 13),
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (var i = 0; i < words.length; i++)
                  Chip(label: Text('${i + 1}. ${words[i]}')),
              ],
            ),
          ],
        ),
      ),
      actions: [
        FilledButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text("I've saved it"),
        ),
      ],
    );
  }
}

class _ImportScreen extends StatefulWidget {
  const _ImportScreen();

  @override
  State<_ImportScreen> createState() => _ImportScreenState();
}

class _ImportScreenState extends State<_ImportScreen> {
  final _controller = TextEditingController();
  String? _error;
  bool _busy = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _import() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await context
          .read<WalletController>()
          .importExisting(_controller.text, network: BigCoinNetwork.testnet);
      if (mounted) {
        Navigator.of(context)
          ..pop()
          ..pop();
      }
    } catch (e) {
      setState(() => _error = 'Invalid recovery phrase');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Import wallet')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('Enter your 12 or 24-word recovery phrase.',
                style: TextStyle(color: Colors.white70)),
            const SizedBox(height: 16),
            TextField(
              controller: _controller,
              maxLines: 4,
              autocorrect: false,
              enableSuggestions: false,
              decoration: InputDecoration(
                border: const OutlineInputBorder(),
                hintText: 'word1 word2 word3 ...',
                errorText: _error,
              ),
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: _busy ? null : _import,
              child: _busy
                  ? const SizedBox(
                      height: 18,
                      width: 18,
                      child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text('Import'),
            ),
          ],
        ),
      ),
    );
  }
}
