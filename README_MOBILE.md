# MyCoin Mobile App - Flutter

This is a cross-platform mobile application for MyCoin, an educational blockchain project. The app provides wallet management, mining capabilities, and blockchain information viewing on iOS and Android.

**EDUCATIONAL USE ONLY** - This app never holds real funds and is intended for learning purposes only.

## Features

- **Wallet Management**: Generate new addresses, display QR codes, check balance
- **Mining Interface**: Start/stop mining operations, monitor progress, view real-time status
- **Blockchain Info**: View chain height, tip hash, money supply, transaction count
- **Real-time Updates**: Polling-based status updates during mining operations
- **Dark Theme**: Professional UI with dark mode optimized for blockchain apps

## Prerequisites

### Required Software

1. **Flutter SDK** (version 3.0.0 or later)
   - Download from: https://flutter.dev/docs/get-started/install
   - Ensure Flutter is added to your PATH

2. **Platform-Specific Requirements**:
   - **Android**: Android SDK, Android emulator or physical device
   - **iOS**: Xcode (macOS only), iPhone simulator or physical device

3. **Backend**: MyCoin web app must be running
   - Default expected at: `http://localhost:5000`
   - See main README for web_app.py setup

## Installation

### 1. Install Flutter

Follow the official Flutter installation guide for your operating system:
https://flutter.dev/docs/get-started/install

Verify installation:
```bash
flutter --version
flutter doctor
```

### 2. Clone/Navigate to Project

```bash
cd C:/Users/usman/Desktop/BigCoinBB/mobile
```

### 3. Install Dependencies

```bash
flutter pub get
```

This installs all Dart/Flutter dependencies defined in `pubspec.yaml`:
- `http`: HTTP client for API calls
- `provider`: State management
- `qr_flutter`: QR code generation
- `json_annotation` & `json_serializable`: JSON parsing

## Building JSON Models

If you modify the model classes in `lib/models/wallet_model.dart`, regenerate the JSON serialization code:

```bash
flutter pub run build_runner build
```

Or with delete-conflicting-outputs:
```bash
flutter pub run build_runner build --delete-conflicting-outputs
```

## Running the App

### Android

**Using Emulator:**
```bash
flutter run
```

**Using Physical Device:**
- Enable USB debugging on your Android device
- Connect via USB
- Run: `flutter run`

**Build APK:**
```bash
flutter build apk
flutter build apk --release  # for release build
```

Output: `build/app/outputs/flutter-apk/app-release.apk`

### iOS

**Using Simulator:**
```bash
flutter run
```

**Using Physical Device:**
- Connect via Xcode or USB
- Provisioning profile must be configured in Xcode
- Run: `flutter run`

**Build iOS App:**
```bash
flutter build ios
flutter build ios --release
```

## Configuration

### Backend URL

By default, the app connects to `http://localhost:5000`. To change this:

**Option 1: Edit at Build Time**
Edit `lib/services/api_service.dart`:
```dart
static const String defaultBaseUrl = 'http://your-server:5000';
```

**Option 2: Runtime Configuration (Future)**
Currently the base URL is fixed at initialization. To add runtime configuration, add a Settings screen that calls:
```dart
apiService.setBaseUrl('http://new-url:5000');
```

## Project Structure

```
mobile/
├── pubspec.yaml                    # Flutter project manifest
├── lib/
│   ├── main.dart                   # App entry point, BottomNavigationBar
│   ├── services/
│   │   └── api_service.dart        # HTTP client, all API calls
│   ├── models/
│   │   └── wallet_model.dart       # Data models (Address, Balance, etc.)
│   └── screens/
│       ├── wallet_screen.dart      # Wallet UI (address, balance, QR)
│       ├── mining_screen.dart      # Mining UI (input, progress, status)
│       └── blockchain_screen.dart  # Blockchain info UI (chain stats)
├── android/                         # Android native project
└── ios/                             # iOS native project
```

## API Endpoints

The app communicates with these backend endpoints:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/wallet/new` | Generate new wallet address |
| GET | `/api/wallet/balance` | Get current balance |
| POST | `/api/mining/start` | Start mining blocks |
| GET | `/api/mining/status` | Check mining progress |
| GET | `/api/mining/stop` | Stop active mining |
| GET | `/api/blockchain/info` | Get blockchain statistics |

Ensure your `web_app.py` backend implements these endpoints and is running before using the app.

## Troubleshooting

### App won't connect to backend
- **Check backend is running**: Verify `web_app.py` is running on `localhost:5000`
- **Check firewall**: Ensure port 5000 is accessible
- **On mobile device**: If using physical device, ensure it's on the same network and use device's IP instead of localhost
- **Edit API URL**: Update `defaultBaseUrl` in `api_service.dart`

### Flutter doctor shows issues
```bash
flutter doctor
```
Follow the instructions to resolve any missing dependencies.

### App crashes on startup
- Check that all dependencies installed: `flutter pub get`
- Rebuild: `flutter clean && flutter pub get && flutter run`
- Check Logcat (Android) or Xcode console (iOS) for error details

### Mining doesn't start
- Verify miner address is provided and valid (not empty)
- Check blocks count is a positive number
- Verify backend is running and accessible

## Development Notes

- **State Management**: Uses Provider for state management across the app
- **API Calls**: All HTTP requests are in `api_service.dart` for easy refactoring
- **Models**: JSON serialization via `json_annotation` - regenerate models after changes
- **Dark Theme**: Configured in `main.dart` with custom colors
- **Error Handling**: All API calls include try-catch with user-friendly error messages

## Testing

Unit and widget tests can be run with:
```bash
flutter test
```

Integration tests (requires running app):
```bash
flutter drive --target=test_driver/app.dart
```

## Future Enhancements

Potential features to add:
- Transaction broadcasting UI
- Wallet import/export
- Settings screen with base URL configuration
- Local notification support for mining completion
- Biometric authentication for wallet security
- Persistent wallet storage (SharedPreferences)
- Network switching (testnet/mainnet)

## License

Educational use only. Not intended for production blockchain applications.

## Support

For issues with the Flutter app, check:
1. Flutter installation: `flutter doctor`
2. Backend connectivity: Verify web_app.py is running
3. Dependencies: `flutter pub get && flutter pub upgrade`
4. Clean rebuild: `flutter clean && flutter pub get && flutter run`
