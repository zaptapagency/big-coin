import 'package:flutter_test/flutter_test.dart';

import 'package:bigcoin_mobile/wallet/amount.dart';

void main() {
  group('Amount.tryParseBigToSats', () {
    test('parses whole and fractional BIG exactly', () {
      expect(Amount.tryParseBigToSats('1'), 100000000);
      expect(Amount.tryParseBigToSats('0.5'), 50000000);
      expect(Amount.tryParseBigToSats('1.23456789'), 123456789);
      expect(Amount.tryParseBigToSats('0.00000001'), 1);
      expect(Amount.tryParseBigToSats('.5'), 50000000);
      expect(Amount.tryParseBigToSats('21000000'), 2100000000000000);
    });

    test('is exact where a double would drift', () {
      // 0.1 + 0.2 in floating point != 0.3; integer parsing must be exact.
      expect(Amount.tryParseBigToSats('0.1'), 10000000);
      expect(Amount.tryParseBigToSats('0.2'), 20000000);
      expect(Amount.tryParseBigToSats('0.3'), 30000000);
      // A value that (x * 1e8).round() historically mishandled.
      expect(Amount.tryParseBigToSats('4.20'), 420000000);
    });

    test('trims surrounding whitespace', () {
      expect(Amount.tryParseBigToSats('  2.5  '), 250000000);
    });

    test('rejects more than 8 decimal places', () {
      expect(Amount.tryParseBigToSats('0.000000001'), isNull);
    });

    test('rejects malformed input', () {
      expect(Amount.tryParseBigToSats(''), isNull);
      expect(Amount.tryParseBigToSats('  '), isNull);
      expect(Amount.tryParseBigToSats('abc'), isNull);
      expect(Amount.tryParseBigToSats('1.2.3'), isNull);
      expect(Amount.tryParseBigToSats('-1'), isNull);
      expect(Amount.tryParseBigToSats('1e8'), isNull);
      expect(Amount.tryParseBigToSats('1,5'), isNull);
      expect(Amount.tryParseBigToSats('.'), isNull);
    });
  });

  group('Amount.satsToBigString', () {
    test('formats with 8 decimals', () {
      expect(Amount.satsToBigString(100000000), '1.00000000');
      expect(Amount.satsToBigString(1), '0.00000001');
      expect(Amount.satsToBigString(123456789), '1.23456789');
    });
  });
}
