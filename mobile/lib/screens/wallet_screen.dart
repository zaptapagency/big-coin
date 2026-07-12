import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:qr_flutter/qr_flutter.dart';
import '../services/api_service.dart';
import '../models/wallet_model.dart';

class WalletScreen extends StatefulWidget {
  const WalletScreen({Key? key}) : super(key: key);

  @override
  State<WalletScreen> createState() => _WalletScreenState();
}

class _WalletScreenState extends State<WalletScreen> {
  Address? currentAddress;
  Balance? currentBalance;
  bool isLoading = false;
  String? errorMessage;

  @override
  void initState() {
    super.initState();
    _loadBalance();
  }

  Future<void> _generateNewKey() async {
    setState(() {
      isLoading = true;
      errorMessage = null;
    });

    try {
      final apiService = context.read<ApiService>();
      final address = await apiService.newKey();
      setState(() {
        currentAddress = address;
        isLoading = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('New key generated successfully')),
      );
    } catch (e) {
      setState(() {
        errorMessage = e.toString();
        isLoading = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red),
      );
    }
  }

  Future<void> _loadBalance() async {
    setState(() {
      isLoading = true;
      errorMessage = null;
    });

    try {
      final apiService = context.read<ApiService>();
      final balance = await apiService.getBalance();
      setState(() {
        currentBalance = balance;
        isLoading = false;
      });
    } catch (e) {
      setState(() {
        errorMessage = e.toString();
        isLoading = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red),
      );
    }
  }

  Future<void> _checkBalance() async {
    setState(() {
      isLoading = true;
      errorMessage = null;
    });

    try {
      final apiService = context.read<ApiService>();
      final balance = await apiService.getBalance();
      setState(() {
        currentBalance = balance;
        isLoading = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Balance updated')),
      );
    } catch (e) {
      setState(() {
        errorMessage = e.toString();
        isLoading = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Wallet'),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // Address Display Section
            Card(
              color: const Color(0xFF1F1F1F),
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    const Text(
                      'Wallet Address',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w500,
                        color: Color(0xFF999999),
                      ),
                    ),
                    const SizedBox(height: 16),
                    if (currentAddress != null)
                      Column(
                        children: [
                          QrImageView(
                            data: currentAddress!.address,
                            version: QrVersions.auto,
                            size: 200.0,
                            backgroundColor: Colors.white,
                          ),
                          const SizedBox(height: 16),
                          SelectableText(
                            currentAddress!.address,
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              fontSize: 12,
                              fontFamily: 'Courier',
                              color: Color(0xFF1F6FD9),
                            ),
                          ),
                        ],
                      )
                    else
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 32.0),
                        child: Text(
                          'No address generated yet',
                          style: TextStyle(
                            fontSize: 14,
                            color: Colors.grey[600],
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

            // Balance Display Section
            if (currentBalance != null)
              Card(
                color: const Color(0xFF1F1F1F),
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    children: [
                      const Text(
                        'Balance',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w500,
                          color: Color(0xFF999999),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        '${currentBalance!.balanceCoins.toStringAsFixed(8)} BigCoin',
                        style: const TextStyle(
                          fontSize: 28,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF1F6FD9),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        '${currentBalance!.balanceCents} cents',
                        style: const TextStyle(
                          fontSize: 12,
                          color: Color(0xFF999999),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            const SizedBox(height: 24),

            // Action Buttons
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                icon: const Icon(Icons.vpn_key),
                label: const Text('Generate New Key'),
                onPressed: isLoading ? null : _generateNewKey,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  backgroundColor: const Color(0xFF1F6FD9),
                  foregroundColor: Colors.white,
                ),
              ),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                icon: const Icon(Icons.refresh),
                label: const Text('Check Balance'),
                onPressed: isLoading ? null : _checkBalance,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  backgroundColor: const Color(0xFF1F6FD9),
                  foregroundColor: Colors.white,
                ),
              ),
            ),
            const SizedBox(height: 24),

            // Error Display
            if (errorMessage != null)
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.red[900],
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  errorMessage!,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
