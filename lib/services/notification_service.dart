import 'package:onesignal_flutter/onesignal_flutter.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'api_service.dart';
import '../main.dart';
import '../screens/alert_details_screen.dart';
import '../models/event_alert.dart';

class NotificationService {
  static Future<void> init() async {
    // Enable verbose logging for debugging in dev
    if (kDebugMode) {
      OneSignal.Debug.setLogLevel(OSLogLevel.verbose);
    }
    
    // Initialize with OneSignal App ID
    OneSignal.initialize("7087a2bc-e285-49a9-a404-15be244a893f");
    
    // Setup listener for notification clicks (Dailyhunt-style)
    OneSignal.Notifications.addClickListener((event) {
      final data = event.notification.additionalData;
      if (data != null && data.containsKey('alert_id')) {
        final alertId = data['alert_id'] as String;
        _navigateToAlert(alertId);
      }
    });
    
    // Setup observer for player_id changes
    OneSignal.User.pushSubscription.addObserver((state) {
      if (state.current.id != null && state.current.id!.isNotEmpty) {
        ApiService().registerDevice(state.current.id!);
      }
    });
  }

  static void _navigateToAlert(String alertId) async {
    // 1. Get the navigator context
    final context = MarketImpactApp.navigatorKey.currentContext;
    if (context == null) return;

    // 2. Fetch latest alerts to find the one we need
    // (In a more complex app, we'd fetch a single alert by ID)
    final alerts = await ApiService().fetchAlerts();
    final alert = alerts.firstWhere(
      (a) => a.id == alertId,
      orElse: () => EventAlert(
        id: alertId,
        event: "New Market Alert",
        company: "Market",
        sector: "Market",
        stocks: [],
        impactDirection: "NEUTRAL",
        impactDescription: "Fetch failed or alert not found. Please refresh the app.",
        eventDate: "",
        impactDateEst: "",
        probability: 0,
        reason: "",
        timestamp: DateTime.now().toIso8601String(),
      ),
    );

    // 3. Navigate to the detail screen
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => AlertDetailsScreen(alert: alert)),
    );
  }

  static Future<void> requestPermissions() async {
    // Prompt for push notifications
    await OneSignal.Notifications.requestPermission(true);
    
    // Attempt immediate registration if id is already available
    final playerId = OneSignal.User.pushSubscription.id;
    if (playerId != null && playerId.isNotEmpty) {
      await ApiService().registerDevice(playerId);
    }
  }
}
