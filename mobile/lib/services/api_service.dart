import 'package:http/http.dart' as http;
import 'dart:convert';
import '../models/wallet_model.dart';

class ApiService {
  static const String defaultBaseUrl = 'http://localhost:5002';

  late String baseUrl;
  late http.Client httpClient;

  ApiService({String? baseUrl, http.Client? httpClient}) {
    this.baseUrl = baseUrl ?? defaultBaseUrl;
    this.httpClient = httpClient ?? http.Client();
  }

  void setBaseUrl(String newUrl) {
    baseUrl = newUrl;
  }

  Future<Address> newKey() async {
    try {
      final response = await httpClient.get(
        Uri.parse('$baseUrl/api/wallet/new'),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final jsonData = jsonDecode(response.body);
        return Address.fromJson(jsonData);
      } else {
        throw Exception('Failed to generate new key: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error generating new key: $e');
    }
  }

  Future<Balance> getBalance({String? address}) async {
    try {
      final uri = address != null
          ? Uri.parse('$baseUrl/api/wallet/balance').replace(
              queryParameters: {'address': address},
            )
          : Uri.parse('$baseUrl/api/wallet/balance');

      final response = await httpClient.get(uri).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final jsonData = jsonDecode(response.body);
        return Balance.fromJson(jsonData);
      } else {
        throw Exception('Failed to fetch balance: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error fetching balance: $e');
    }
  }

  Future<Map<String, dynamic>> startMining(int blocks, String address) async {
    try {
      if (blocks <= 0) {
        throw Exception('Blocks must be greater than 0');
      }
      if (address.isEmpty) {
        throw Exception('Miner address is required');
      }

      final response = await httpClient.post(
        Uri.parse('$baseUrl/api/mining/start'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'blocks': blocks,
          'address': address,
        }),
      ).timeout(const Duration(seconds: 30));

      if (response.statusCode == 200 || response.statusCode == 202) {
        return jsonDecode(response.body);
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['error'] ?? 'Failed to start mining');
      }
    } catch (e) {
      throw Exception('Error starting mining: $e');
    }
  }

  Future<MiningStatus> getMiningStatus() async {
    try {
      final response = await httpClient.get(
        Uri.parse('$baseUrl/api/mining/status'),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final jsonData = jsonDecode(response.body);
        return MiningStatus.fromJson(jsonData);
      } else {
        throw Exception('Failed to fetch mining status: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error fetching mining status: $e');
    }
  }

  Future<Map<String, dynamic>> stopMining() async {
    try {
      final response = await httpClient.get(
        Uri.parse('$baseUrl/api/mining/stop'),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Failed to stop mining: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error stopping mining: $e');
    }
  }

  Future<BlockchainInfo> getBlockchainInfo() async {
    try {
      final response = await httpClient.get(
        Uri.parse('$baseUrl/api/blockchain/info'),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final jsonData = jsonDecode(response.body);
        return BlockchainInfo.fromJson(jsonData);
      } else {
        throw Exception('Failed to fetch blockchain info: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error fetching blockchain info: $e');
    }
  }
}
