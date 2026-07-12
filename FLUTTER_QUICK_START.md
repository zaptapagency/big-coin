# MyCoin Flutter App - Quick Start

## 1. Prerequisites Check

Ensure you have Flutter installed:
```bash
flutter --version
flutter doctor
```

If Flutter is NOT installed, download from: https://flutter.dev/docs/get-started/install

## 2. Install Dependencies (One-time)

```bash
cd C:/Users/usman/Desktop/BigCoinBB/mobile
flutter pub get
```

## 3. Generate JSON Models (One-time, after model changes)

```bash
flutter pub run build_runner build
```

This generates `.g.dart` files for JSON serialization from `lib/models/wallet_model.dart`.

## 4. Start Backend Server

Ensure the MyCoin web app is running:
```bash
# In a separate terminal, from the project root
python web_app.py
```

The app expects the backend at: `http://localhost:5000`

## 5. Run the App

### Option A: Run on Android Emulator
```bash
flutter run
```

### Option B: Run on iOS Simulator (macOS only)
```bash
flutter run
```

### Option C: Run on Physical Device (Android/iOS)
1. Connect device via USB
2. Enable USB debugging (Android) or Trust computer (iOS)
3. Run: `flutter run`

## 6. Troubleshooting

### Backend URL not working?
Edit: `mobile/lib/services/api_service.dart` (line 12)
```dart
static const String defaultBaseUrl = 'http://your-machine-ip:5000';
```

### JSON models not generating?
```bash
flutter clean
flutter pub get
flutter pub run build_runner build --delete-conflicting-outputs
```

### Flutter not found?
Add Flutter to PATH or use full path:
```bash
/path/to/flutter/bin/flutter run
```

## App Screens

**Wallet Tab** - Manage addresses and balance
- Generate new address with QR code
- Check current balance
- View UTXO count

**Mining Tab** - Control mining operations
- Input blocks to mine and miner address
- Start/stop mining
- Real-time progress display
- Live status updates (height, hash, UTXOs)

**Blockchain Tab** - View chain statistics
- Chain height
- Tip hash
- Total money supply
- Transaction count
- Refresh button

## API Endpoints Used

All requests to: `http://localhost:5000/api/`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/wallet/new` | GET | Generate new address |
| `/wallet/balance` | GET | Get current balance |
| `/mining/start` | POST | Start mining |
| `/mining/status` | GET | Get mining progress |
| `/mining/stop` | GET | Stop mining |
| `/blockchain/info` | GET | Get chain info |

## Build for Release

### Android APK
```bash
flutter build apk --release
# Output: build/app/outputs/flutter-apk/app-release.apk
```

### iOS App Bundle
```bash
flutter build ios --release
# Output: build/ios/iphoneos/Runner.app
```

## Important Notes

- Educational project - never holds real funds
- Requires Flutter SDK 3.0.0 or later
- Backend must be running for full functionality
- JSON models use code generation - run build_runner after model changes
- Default backend URL is localhost:5000

## File Structure

```
mobile/
├── pubspec.yaml              # Project manifest & dependencies
├── lib/
│   ├── main.dart            # App entry & navigation
│   ├── services/
│   │   └── api_service.dart # HTTP client for backend
│   ├── models/
│   │   └── wallet_model.dart # Data models
│   └── screens/
│       ├── wallet_screen.dart
│       ├── mining_screen.dart
│       └── blockchain_screen.dart
└── android/ & ios/          # Native projects (auto-generated)
```

## Next Steps

1. Install Flutter SDK
2. Run `flutter pub get` in mobile directory
3. Start web_app.py backend
4. Run `flutter run` to launch app
5. Test wallet, mining, and blockchain features
