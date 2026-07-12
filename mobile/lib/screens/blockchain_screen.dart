import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import '../models/wallet_model.dart';

class BlockchainScreen extends StatefulWidget {
  const BlockchainScreen({Key? key}) : super(key: key);

  @override
  State<BlockchainScreen> createState() => _BlockchainScreenState();
}

class _BlockchainScreenState extends State<BlockchainScreen> {
  BlockchainInfo? blockchainInfo;
  bool isLoading = false;
  String? errorMessage;

  @override
  void initState() {
    super.initState();
    _loadBlockchainInfo();
  }

  Future<void> _loadBlockchainInfo() async {
    setState(() {
      isLoading = true;
      errorMessage = null;
    });

    try {
      final apiService = context.read<ApiService>();
      final info = await apiService.getBlockchainInfo();
      setState(() {
        blockchainInfo = info;
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Blockchain Info'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: isLoading ? null : _loadBlockchainInfo,
          ),
        ],
      ),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (blockchainInfo != null) ...[
                    _buildInfoCard(
                      icon: Icons.layers,
                      title: 'Chain Height',
                      value: blockchainInfo!.height.toString(),
                      subtitle: 'blocks',
                    ),
                    const SizedBox(height: 12),
                    _buildInfoCard(
                      icon: Icons.fingerprint,
                      title: 'Tip Hash',
                      value: blockchainInfo!.tipHash,
                      subtitle: 'current block hash',
                      isTruncated: true,
                    ),
                    const SizedBox(height: 12),
                    _buildInfoCard(
                      icon: Icons.monetization_on,
                      title: 'Total Money Supply',
                      value:
                          '${blockchainInfo!.totalMoneyCoins.toStringAsFixed(8)} BIG',
                      subtitle: '${blockchainInfo!.totalMoneyCents} cents',
                    ),
                    const SizedBox(height: 12),
                    _buildInfoCard(
                      icon: Icons.receipt_long,
                      title: 'Transaction Count',
                      value: blockchainInfo!.txCount.toString(),
                      subtitle: 'confirmed transactions',
                    ),
                  ] else if (errorMessage != null)
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Colors.red[900],
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Column(
                        children: [
                          const Icon(
                            Icons.error_outline,
                            color: Colors.white,
                            size: 48,
                          ),
                          const SizedBox(height: 12),
                          Text(
                            'Error Loading Data',
                            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              color: Colors.white,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            errorMessage ?? 'Unknown error',
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              color: Colors.white70,
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    )
                  else
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: const Color(0xFF1F1F1F),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Text(
                        'No data available',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Color(0xFF999999)),
                      ),
                    ),
                  const SizedBox(height: 24),
                  SizedBox(
                    child: ElevatedButton.icon(
                      icon: const Icon(Icons.refresh),
                      label: const Text('Refresh'),
                      onPressed: isLoading ? null : _loadBlockchainInfo,
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        backgroundColor: const Color(0xFF1F6FD9),
                        foregroundColor: Colors.white,
                      ),
                    ),
                  ),
                ],
              ),
            ),
    );
  }

  Widget _buildInfoCard({
    required IconData icon,
    required String title,
    required String value,
    required String subtitle,
    bool isTruncated = false,
  }) {
    return Card(
      color: const Color(0xFF1F1F1F),
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  icon,
                  color: const Color(0xFF1F6FD9),
                  size: 24,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: const TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          color: Color(0xFF999999),
                        ),
                      ),
                      const SizedBox(height: 4),
                      SelectableText(
                        isTruncated ? value.substring(0, 32) + '...' : value,
                        style: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF1F6FD9),
                          fontFamily: 'Courier',
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerRight,
              child: Text(
                subtitle,
                style: const TextStyle(
                  fontSize: 11,
                  color: Color(0xFF666666),
                  fontStyle: FontStyle.italic,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
