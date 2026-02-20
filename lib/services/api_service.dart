import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/event_alert.dart';

class ApiService {
  // 1. LOCAL (Testing - Physical Device Native IP)
  // static const String baseUrl = 'http://192.168.1.7:8000'; 
  
  // 2. LIVE (Render) 
  static const String baseUrl = 'https://market-impact-backend.onrender.com';

  Future<List<EventAlert>> fetchAlerts() async {
    print('ApiService: Fetching alerts from $baseUrl/alerts...');
    try {
      final response = await http.get(Uri.parse('$baseUrl/alerts')).timeout(const Duration(seconds: 60));
      print('ApiService: Status code: ${response.statusCode}');
      if (response.statusCode == 200) {
        print('ApiService: Response body: ${response.body}');
        List jsonResponse = json.decode(response.body);
        return jsonResponse.map((data) => EventAlert.fromJson(data)).toList();
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
}
