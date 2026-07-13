import 'package:local_auth/local_auth.dart';

/// Device-level authentication gate (biometrics or device PIN/passcode).
///
/// Used to protect sensitive actions — revealing the recovery phrase and
/// authorizing a spend. If the device has no biometrics or lock screen
/// configured, [authenticate] returns `false` so callers can decide how to
/// proceed (we fail closed for spends).
class LocalAuthService {
  final LocalAuthentication _auth;

  LocalAuthService([LocalAuthentication? auth])
      : _auth = auth ?? LocalAuthentication();

  /// True if the device can perform biometric or device-credential auth.
  Future<bool> isAvailable() async {
    try {
      final supported = await _auth.isDeviceSupported();
      final canCheck = await _auth.canCheckBiometrics;
      return supported || canCheck;
    } catch (_) {
      return false;
    }
  }

  /// Prompts the user to authenticate for [reason]. Returns true only on a
  /// successful biometric/PIN confirmation. Any error or cancellation → false.
  Future<bool> authenticate(String reason) async {
    try {
      return await _auth.authenticate(
        localizedReason: reason,
        options: const AuthenticationOptions(
          biometricOnly: false,
          stickyAuth: true,
          useErrorDialogs: true,
        ),
      );
    } catch (_) {
      return false;
    }
  }
}
