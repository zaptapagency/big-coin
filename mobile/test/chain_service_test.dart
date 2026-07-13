import 'package:flutter_test/flutter_test.dart';
import 'package:http/testing.dart';
import 'package:http/http.dart' as http;

import 'package:bigcoin_mobile/services/chain_service.dart';

void main() {
  group('ChainService base URL scheme', () {
    test('accepts https and strips trailing slashes', () {
      final c = ChainService(baseUrl: 'https://explorer.example/');
      expect(c.baseUrl, 'https://explorer.example');
    });

    test('allows http only for loopback hosts', () {
      final c = ChainService(baseUrl: 'http://127.0.0.1:5055');
      expect(c.baseUrl, 'http://127.0.0.1:5055');
      expect(() => ChainService(baseUrl: 'http://localhost:5055'),
          returnsNormally);
    });

    test('rejects insecure http for a remote host', () {
      expect(() => ChainService(baseUrl: 'http://explorer.example'),
          throwsArgumentError);
    });

    test('rejects an unsupported scheme', () {
      expect(() => ChainService(baseUrl: 'ftp://explorer.example'),
          throwsArgumentError);
    });

    test('setBaseUrl enforces the same rules', () {
      final c = ChainService(baseUrl: 'https://ok.example');
      expect(() => c.setBaseUrl('http://evil.example'), throwsArgumentError);
    });
  });

  group('ChainService response decoding', () {
    ChainService withResponse(http.Response Function() build) => ChainService(
          baseUrl: 'https://x',
          httpClient: MockClient((_) async => build()),
        );

    test('surfaces a non-JSON gateway error as ChainApiException', () async {
      final c = withResponse(
          () => http.Response('<html>502 Bad Gateway</html>', 502));
      expect(
        () => c.getStatus(),
        throwsA(isA<ChainApiException>()
            .having((e) => e.statusCode, 'statusCode', 502)),
      );
    });

    test('rejects a JSON body that is not an object', () async {
      final c = withResponse(() => http.Response('[1,2,3]', 200));
      expect(() => c.getStatus(), throwsA(isA<ChainApiException>()));
    });
  });
}
