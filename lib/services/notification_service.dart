import 'package:onesignal_flutter/onesignal_flutter.dart';
import 'package:flutter/foundation.dart';
import 'api_service.dart';

class NotificationService {
  static Future<void> init() async {
    // Enable verbose logging for debugging in dev
    if (kDebugMode) {
      OneSignal.Debug.setLogLevel(OSLogLevel.verbose);
    }
    
    // Initialize with OneSignal App ID
    OneSignal.initialize("7087a2bc-e285-49a9-a404-15be244a893f");
    
    // Setup observer for player_id changes
    OneSignal.User.pushSubscription.addObserver((state) {
      if (state.current.id != null && state.current.id!.isNotEmpty) {
        ApiService().registerDevice(state.current.id!);
      }
    });
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
