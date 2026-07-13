import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../wallet/wallet_controller.dart';
import 'blockchain_screen.dart';
import 'send_screen.dart';
import 'wallet_screen.dart';

/// Main shell once a wallet exists. Three tabs: receive (Wallet), Send, and
/// chain status (Chain). Mining was removed — a phone can't meaningfully do
/// scrypt PoW, and the wallet is non-custodial.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _index = 0;

  static const _tabs = [WalletScreen(), SendScreen(), BlockchainScreen()];

  @override
  void initState() {
    super.initState();
    // Kick off an initial balance/status load.
    WidgetsBinding.instance.addPostFrameCallback(
      (_) => context.read<WalletController>().refresh(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(index: _index, children: _tabs),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _index,
        onTap: (i) => setState(() => _index = i),
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.account_balance_wallet),
            label: 'Wallet',
          ),
          BottomNavigationBarItem(icon: Icon(Icons.send), label: 'Send'),
          BottomNavigationBarItem(icon: Icon(Icons.link), label: 'Chain'),
        ],
      ),
    );
  }
}
