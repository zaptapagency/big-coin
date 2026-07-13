import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../wallet/address_script.dart';
import '../wallet/amount.dart';
import '../wallet/local_auth_service.dart';
import '../wallet/tx_builder.dart';
import '../wallet/wallet_controller.dart';

/// Send tab: enter a destination address + amount, then build, sign (on-device)
/// and broadcast. Validates the address against the current network before
/// enabling send.
class SendScreen extends StatefulWidget {
  const SendScreen({super.key});

  @override
  State<SendScreen> createState() => _SendScreenState();
}

class _SendScreenState extends State<SendScreen> {
  final _addressController = TextEditingController();
  final _amountController = TextEditingController();
  String? _addressError;
  String? _amountError;

  @override
  void dispose() {
    _addressController.dispose();
    _amountController.dispose();
    super.dispose();
  }

  int? _validate(WalletController wallet) {
    String? addrErr;
    String? amtErr;

    final addr = _addressController.text.trim();
    if (addr.isEmpty) {
      addrErr = 'Enter a destination address';
    } else {
      try {
        AddressScript.forAddress(addr, wallet.network);
      } catch (_) {
        addrErr = 'Not a valid ${wallet.network.id} address';
      }
    }

    final sats = Amount.tryParseBigToSats(_amountController.text);
    if (sats == null || sats <= 0) {
      amtErr = 'Enter a positive amount (max 8 decimals)';
    } else {
      // Client-side balance check so we fail fast without a round-trip.
      final availableSats = wallet.balance == null
          ? null
          : (wallet.balance!.total * Amount.satsPerBig).round();
      if (availableSats != null && sats > availableSats) {
        amtErr = 'Amount exceeds available balance';
      }
    }

    setState(() {
      _addressError = addrErr;
      _amountError = amtErr;
    });
    return (addrErr == null && amtErr == null) ? sats : null;
  }

  Future<void> _send(WalletController wallet) async {
    final sats = _validate(wallet);
    if (sats == null) return;
    final to = _addressController.text.trim();

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Confirm send'),
        content: Text(
            'Send ${Amount.satsToBigString(sats)} BIG to:\n\n$to\n\nOn ${wallet.network.id}.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Send'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    // Require device authentication (biometric / PIN) before spending.
    if (!mounted) return;
    final auth = context.read<LocalAuthService>();
    if (await auth.isAvailable()) {
      final ok = await auth.authenticate('Authenticate to authorize this payment');
      if (!ok) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Authentication required to send')),
        );
        return;
      }
    }

    try {
      final txid = await wallet.send(toAddress: to, amountSats: sats);
      if (!mounted) return;
      _addressController.clear();
      _amountController.clear();
      showDialog<void>(
        context: context,
        builder: (_) => AlertDialog(
          title: const Text('Sent'),
          content: SelectableText('Transaction broadcast:\n\n$txid'),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('OK'),
            ),
          ],
        ),
      );
    } catch (e) {
      if (!mounted) return;
      final message = e is InsufficientFundsException
          ? 'Insufficient funds for this amount + fee.'
          : e.toString();
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final wallet = context.watch<WalletController>();
    final available = wallet.balance?.total;

    return Scaffold(
      appBar: AppBar(title: const Text('Send')),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (available != null)
              Text('Available: ${available.toStringAsFixed(8)} BIG',
                  style: const TextStyle(color: Colors.white54)),
            const SizedBox(height: 16),
            TextField(
              controller: _addressController,
              autocorrect: false,
              enableSuggestions: false,
              decoration: InputDecoration(
                labelText: 'Destination address',
                hintText: wallet.network.addressPrefixHint,
                border: const OutlineInputBorder(),
                errorText: _addressError,
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _amountController,
              keyboardType:
                  const TextInputType.numberWithOptions(decimal: true),
              decoration: InputDecoration(
                labelText: 'Amount (BIG)',
                border: const OutlineInputBorder(),
                errorText: _amountError,
              ),
            ),
            const SizedBox(height: 24),
            FilledButton.icon(
              icon: wallet.busy
                  ? const SizedBox(
                      height: 18,
                      width: 18,
                      child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.send),
              label: Text(wallet.busy ? 'Sending…' : 'Send'),
              onPressed: wallet.busy ? null : () => _send(wallet),
            ),
            const SizedBox(height: 16),
            const Text(
              'The transaction is built and signed on this device. Only the '
              'signed result is sent to the network.',
              style: TextStyle(color: Colors.white38, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }
}
