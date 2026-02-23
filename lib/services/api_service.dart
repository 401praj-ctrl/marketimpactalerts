import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/event_alert.dart';

class ApiService {
  // 1. LIVE (Render) - Recommended for Physical Devices
  static const String baseUrl = 'https://market-impact-backend.onrender.com';
  
  // 2. LOCAL (Emulator/Testing)
  // static const String baseUrl = 'http://10.0.2.2:8000';
  // static const String baseUrl = 'http://192.168.1.7:8000'; // Replace with your machine's local IP for physical phone testing

  Future<List<EventAlert>> fetchAlerts() async {
    print('ApiService: Fetching alerts from $baseUrl/alerts...');
    try {
      final response = await http.get(Uri.parse('$baseUrl/alerts')).timeout(const Duration(seconds: 60));
      print('ApiService: Status code: ${response.statusCode}');
      if (response.statusCode == 200) {
        print('ApiService: Response body: ${response.body}');
        List jsonResponse = json.decode(response.body);
        return jsonResponse
            .where((data) => data != null && data is Map<String, dynamic>)
            .map((data) => EventAlert.fromJson(data as Map<String, dynamic>))
            .toList();
      } else {
        print('ApiService: Error status code');
        throw Exception('Failed to load alerts');
      }
    } catch (e) {
      print('ApiService: Exception: $e');
      return [];
    }
  }

  Future<void> refreshAlerts() async {
    print('ApiService: Triggering manual refresh at $baseUrl/refresh...');
    try {
      final response = await http.post(Uri.parse('$baseUrl/refresh'));
      print('ApiService: Refresh response status: ${response.statusCode}');
    } catch (e) {
      print('ApiService: Refresh exception: $e');
    }
  }

  Future<bool> checkAnalysisStatus() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/status')).timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['is_analyzing'] ?? false;
      }
    } catch (e) {
      // Ignore network errors on polling to avoid spamming logs
    }
    return false;
  }

  Future<void> registerDevice(String playerId) async {
    print('ApiService: Registering device player_id: $playerId');
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/register_device'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'player_id': playerId}),
      );
      print('ApiService: Register response status: ${response.statusCode}');
    } catch (e) {
      print('ApiService: Register exception: $e');
    }
  }

  Future<Map<String, dynamic>> getPredictionStats() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/stats')).timeout(const Duration(seconds: 15));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data is Map<String, dynamic>) return data;
      }
    } catch (e) {
      print('ApiService: Stats exception: $e');
    }
    return {};
  }

  Future<Map<String, dynamic>?> getLatestAppVersion() async {
    print('ApiService: Checking for app update at $baseUrl/app/version...');
    try {
      final response = await http.get(Uri.parse('$baseUrl/app/version')).timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      print('ApiService: Update check exception: $e');
    }
    return null;
  }
}
