import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'services/chain_service.dart';
import 'screens/home_screen.dart';
import 'screens/onboarding_screen.dart';
import 'wallet/local_auth_service.dart';
import 'wallet/wallet_controller.dart';

void main() {
  runApp(const BigCoinApp());
}

class BigCoinApp extends StatelessWidget {
  const BigCoinApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        Provider<ChainService>(create: (_) => ChainService()),
        Provider<LocalAuthService>(create: (_) => LocalAuthService()),
        ChangeNotifierProvider<WalletController>(
          create: (ctx) =>
              WalletController(chain: ctx.read<ChainService>()),
        ),
      ],
      child: MaterialApp(
        title: 'Big Coin Wallet',
        debugShowCheckedModeBanner: false,
        theme: ThemeData.dark(useMaterial3: true).copyWith(
          scaffoldBackgroundColor: const Color(0xFF121212),
          colorScheme: const ColorScheme.dark(
            primary: Color(0xFF1F6FD9),
            secondary: Color(0xFF1F6FD9),
          ),
          appBarTheme: const AppBarTheme(
            backgroundColor: Color(0xFF1F1F1F),
            elevation: 0,
          ),
          bottomNavigationBarTheme: const BottomNavigationBarThemeData(
            backgroundColor: Color(0xFF1F1F1F),
            selectedItemColor: Color(0xFF1F6FD9),
            unselectedItemColor: Color(0xFF666666),
          ),
        ),
        home: const _Root(),
      ),
    );
  }
}

/// Decides between onboarding and the main app depending on whether a wallet
/// already exists on the device.
class _Root extends StatefulWidget {
  const _Root();

  @override
  State<_Root> createState() => _RootState();
}

class _RootState extends State<_Root> {
  late final Future<bool> _loaded;

  @override
  void initState() {
    super.initState();
    _loaded = context.read<WalletController>().loadExisting();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<bool>(
      future: _loaded,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }
        final controller = context.watch<WalletController>();
        return controller.hasWallet
            ? const HomeScreen()
            : const OnboardingScreen();
      },
    );
  }
}
