/// Precise conversion between a human BIG amount string and integer satoshis
/// (1 BIG = 1e8 sats). Avoids floating-point: the amount is parsed digit-by-digit
/// so values like `0.1 + 0.2` or `21000000.00000001` are exact.
class Amount {
  static const int satsPerBig = 100000000; // 1e8
  static const int _decimals = 8;

  /// Parses a decimal BIG string into integer sats.
  ///
  /// Returns null if the string is not a well-formed non-negative decimal or
  /// has more than 8 fractional digits (which sats can't represent).
  static int? tryParseBigToSats(String input) {
    final s = input.trim();
    if (s.isEmpty) return null;

    final parts = s.split('.');
    if (parts.length > 2) return null;

    final intPart = parts[0];
    final fracPart = parts.length == 2 ? parts[1] : '';

    // Only digits allowed in each part (no sign, no separators).
    if (!_isDigits(intPart) && intPart.isNotEmpty) return null;
    if (!_isDigits(fracPart) && fracPart.isNotEmpty) return null;
    if (intPart.isEmpty && fracPart.isEmpty) return null;
    if (fracPart.length > _decimals) return null;

    final whole = intPart.isEmpty ? 0 : int.tryParse(intPart);
    if (whole == null) return null;

    final paddedFrac = fracPart.padRight(_decimals, '0');
    final frac = paddedFrac.isEmpty ? 0 : int.tryParse(paddedFrac);
    if (frac == null) return null;

    return whole * satsPerBig + frac;
  }

  /// Formats integer [sats] as a fixed 8-decimal BIG string.
  static String satsToBigString(int sats) =>
      (sats / satsPerBig).toStringAsFixed(_decimals);

  static bool _isDigits(String s) {
    for (final code in s.codeUnits) {
      if (code < 0x30 || code > 0x39) return false;
    }
    return true;
  }
}
