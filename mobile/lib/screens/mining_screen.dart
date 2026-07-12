import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:async';
import '../services/api_service.dart';
import '../models/wallet_model.dart';

class MiningScreen extends StatefulWidget {
  const MiningScreen({Key? key}) : super(key: key);

  @override
  State<MiningScreen> createState() => _MiningScreenState();
}

class _MiningScreenState extends State<MiningScreen> {
  final TextEditingController _blocksController = TextEditingController(text: '1');
  final TextEditingController _addressController = TextEditingController();

  bool isMining = false;
  MiningStatus? miningStatus;
  String? errorMessage;
  Timer? statusPoller;

  @override
  void initState() {
    super.initState();
    _checkMiningStatus();
  }

  @override
  void dispose() {
    _blocksController.dispose();
    _addressController.dispose();
    statusPoller?.cancel();
    super.dispose();
  }

  Future<void> _checkMiningStatus() async {
    try {
      final apiService = context.read<ApiService>();
      final status = await apiService.getMiningStatus();
      setState(() {
        miningStatus = status;
        isMining = status.isMining;
        if (isMining) {
          _startStatusPolling();
        }
      });
    } catch (e) {
      // Silent fail on startup
    }
  }

  void _startStatusPolling() {
    statusPoller = Timer.periodic(const Duration(seconds: 2), (_) async {
      try {
        final apiService = context.read<ApiService>();
        final status = await apiService.getMiningStatus();
        setState(() {
          miningStatus = status;
          isMining = status.isMining;
          if (!isMining) {
            statusPoller?.cancel();
            statusPoller = null;
          }
        });
      } catch (e) {
        // Ignore polling errors
      }
    });
  }

  bool _isValidAddress(String address) {
    // Basic validation: address should not be empty and should be hex-like
    return address.isNotEmpty && address.length > 20;
  }

  Future<void> _startMining() async {
    final blocks = int.tryParse(_blocksController.text);
    final address = _addressController.text;

    if (blocks == null || blocks <= 0) {
      setState(() {
        errorMessage = 'Blocks must be a positive number';
      });
      return;
    }

    if (!_isValidAddress(address)) {
      setState(() {
        errorMessage = 'Please enter a valid miner address';
      });
      return;
    }

    setState(() {
      errorMessage = null;
      isMining = true;
    });

    try {
      final apiService = context.read<ApiService>();
      await apiService.startMining(blocks, address);

      _startStatusPolling();

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Mining started')),
      );
    } catch (e) {
      setState(() {
        errorMessage = e.toString();
        isMining = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red),
      );
    }
  }

  Future<void> _stopMining() async {
    try {
      final apiService = context.read<ApiService>();
      await apiService.stopMining();

      setState(() {
        isMining = false;
      });
      statusPoller?.cancel();
      statusPoller = null;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Mining stopped')),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mining'),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Input Section
            if (!isMining) ...[
              const Text(
                'Number of Blocks',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _blocksController,
                keyboardType: TextInputType.number,
                enabled: !isMining,
                decoration: InputDecoration(
                  hintText: '1',
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 12,
                  ),
                ),
              ),
              const SizedBox(height: 24),
              const Text(
                'Miner Address',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _addressController,
                enabled: !isMining,
                decoration: InputDecoration(
                  hintText: 'Enter your wallet address',
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 12,
                  ),
                ),
              ),
              const SizedBox(height: 24),
              if (errorMessage != null)
                Container(
                  padding: const EdgeInsets.all(12),
                  margin: const EdgeInsets.only(bottom: 16),
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
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  icon: const Icon(Icons.play_arrow),
                  label: const Text('Start Mining'),
                  onPressed: _startMining,
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    backgroundColor: const Color(0xFF1F6FD9),
                    foregroundColor: Colors.white,
                  ),
                ),
              ),
            ] else ...[
              // Mining Status Display
              Card(
                color: const Color(0xFF1F1F1F),
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Mining in Progress',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF1F6FD9),
                        ),
                      ),
                      const SizedBox(height: 16),
                      Center(
                        child: Column(
                          children: [
                            if (miningStatus != null)
                              CircularProgressIndicator(
                                value: miningStatus!.blocksToMine > 0
                                    ? miningStatus!.blocksMined /
                                        miningStatus!.blocksToMine
                                    : 0,
                                strokeWidth: 6,
                                valueColor: const AlwaysStoppedAnimation<Color>(
                                  Color(0xFF1F6FD9),
                                ),
                              ),
                            const SizedBox(height: 16),
                            if (miningStatus != null)
                              Text(
                                '${miningStatus!.blocksMined}/${miningStatus!.blocksToMine} blocks',
                                style: const TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 24),
                      _buildStatusRow(
                        'Height:',
                        miningStatus?.currentHeight.toString() ?? '-',
                      ),
                      _buildStatusRow(
                        'Blocks mined:',
                        miningStatus?.blocksMined.toString() ?? '-',
                      ),
                      _buildStatusRow(
                        'Blocks target:',
                        miningStatus?.blocksToMine.toString() ?? '-',
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  icon: const Icon(Icons.stop),
                  label: const Text('Stop Mining'),
                  onPressed: _stopMining,
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    backgroundColor: Colors.red[700],
                    foregroundColor: Colors.white,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildStatusRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(
              fontSize: 12,
              color: Color(0xFF999999),
            ),
          ),
          Flexible(
            child: SelectableText(
              value,
              textAlign: TextAlign.end,
              style: const TextStyle(
                fontSize: 12,
                fontFamily: 'Courier',
                color: Color(0xFF1F6FD9),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
