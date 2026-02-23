import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:package_info_plus/package_info_plus.dart';
import '../theme/app_theme.dart';
import '../models/event_alert.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool _notificationsEnabled = true;
  bool _autoDeleteEnabled = true;
  List<EventAlert> _hiddenAlerts = [];
  bool _isLoadingHidden = true;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    final hiddenIds = prefs.getStringList('hidden_alerts') ?? [];
    final cachedStr = prefs.getString('cached_alerts');
    
    List<EventAlert> hiddenItems = [];
    if (cachedStr != null && hiddenIds.isNotEmpty) {
      try {
        List jsonResponse = json.decode(cachedStr);
        final allAlerts = jsonResponse.map((data) => EventAlert.fromJson(data)).toList();
        hiddenItems = allAlerts.where((a) => hiddenIds.contains(a.id)).toList();
      } catch (e) {
        print('Settings: Error parsing cached alerts: $e');
      }
    }

    setState(() {
      _autoDeleteEnabled = prefs.getBool('auto_delete_enabled') ?? true;
      _notificationsEnabled = prefs.getBool('notifications_enabled') ?? true;
      _hiddenAlerts = hiddenItems;
      _isLoadingHidden = false;
    });
  }

  Future<void> _saveSetting(String key, bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(key, value);
  }

  Future<void> _restoreAlert(EventAlert alert) async {
    final prefs = await SharedPreferences.getInstance();
    final hiddenIds = prefs.getStringList('hidden_alerts') ?? [];
    hiddenIds.remove(alert.id);
    await prefs.setStringList('hidden_alerts', hiddenIds);
    
    setState(() {
      _hiddenAlerts.removeWhere((a) => a.id == alert.id);
    });

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Restored: ${alert.event}')),
      );
    }
  }

  Future<void> _resetHiddenAlerts() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('hidden_alerts');
    setState(() {
      _hiddenAlerts = [];
    });
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('All hidden alerts have been restored.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('SETTINGS')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _buildSectionHeader('ALERTS & NOTIFICATIONS'),
          _buildSettingTile(
            title: 'Push Notifications',
            subtitle: 'Get real-time market impact alerts',
            icon: Icons.notifications_active_rounded,
            value: _notificationsEnabled,
            onChanged: (val) {
              setState(() => _notificationsEnabled = val);
              _saveSetting('notifications_enabled', val);
            },
          ),
          const SizedBox(height: 24),
          _buildSectionHeader('DATA MANAGEMENT'),
          _buildSettingTile(
            title: 'Auto-Clean Feed',
            subtitle: 'Delete alerts older than 7 days',
            icon: Icons.auto_delete_rounded,
            value: _autoDeleteEnabled,
            onChanged: (val) {
              setState(() => _autoDeleteEnabled = val);
              _saveSetting('auto_delete_enabled', val);
            },
          ),
          const SizedBox(height: 24),
          _buildSectionHeader('RESTORE DELETED ALERTS'),
          if (_isLoadingHidden)
            const Center(child: Padding(padding: EdgeInsets.all(20), child: CircularProgressIndicator()))
          else if (_hiddenAlerts.isEmpty)
            _buildEmptyHiddenPlaceholder()
          else
            ..._hiddenAlerts.map((alert) => _buildHiddenAlertTile(alert)).toList(),
          
          if (_hiddenAlerts.isNotEmpty) ...[
            const SizedBox(height: 8),
            TextButton.icon(
              onPressed: _resetHiddenAlerts,
              icon: const Icon(Icons.restore_rounded, size: 18),
              label: const Text('RESTORE ALL'),
              style: TextButton.styleFrom(foregroundColor: AppTheme.silver),
            ),
          ],
          const SizedBox(height: 32),
          _buildSectionHeader('SYSTEM'),
          FutureBuilder<String>(
            future: _getAppVersion(),
            builder: (context, snapshot) {
              return ListTile(
                leading: const Icon(Icons.info_outline, color: AppTheme.silver),
                title: const Text('Engine Version'),
                subtitle: Text('Alpha Engine v${snapshot.data ?? '...'}'),
                trailing: const Text('STABLE', style: TextStyle(color: AppTheme.glassBlue, fontWeight: FontWeight.bold, fontSize: 10)),
              );
            },
          ),
        ],
      ),
    );
  }

  Future<String> _getAppVersion() async {
    try {
      final info = await PackageInfo.fromPlatform();
      return info.version;
    } catch (e) {
      return '1.1.0';
    }
  }

  Widget _buildEmptyHiddenPlaceholder() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: AppTheme.glassDecoration(),
      child: Column(
        children: [
          Icon(Icons.check_circle_outline_rounded, color: AppTheme.silver.withOpacity(0.3), size: 48),
          const SizedBox(height: 12),
          Text(
            'No hidden alerts',
            style: TextStyle(color: AppTheme.silver.withOpacity(0.5), fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }

  Widget _buildHiddenAlertTile(EventAlert alert) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: AppTheme.glassDecoration(),
      child: ListTile(
        title: Text(
          alert.event,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
        ),
        subtitle: Text(
          alert.company.isNotEmpty ? alert.company : alert.sector,
          style: const TextStyle(color: AppTheme.silver, fontSize: 12),
        ),
        trailing: IconButton(
          icon: const Icon(Icons.restore_rounded, color: AppTheme.glassBlue),
          onPressed: () => _restoreAlert(alert),
        ),
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.only(left: 16, bottom: 8),
      child: Text(
        title,
        style: const TextStyle(
          color: AppTheme.glassBlue,
          fontSize: 12,
          fontWeight: FontWeight.bold,
          letterSpacing: 1.5,
        ),
      ),
    );
  }

  Widget _buildSettingTile({
    required String title,
    required String subtitle,
    required IconData icon,
    required bool value,
    required ValueChanged<bool> onChanged,
  }) {
    return Container(
      decoration: AppTheme.glassDecoration(),
      child: SwitchListTile(
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(subtitle, style: const TextStyle(color: AppTheme.silver, fontSize: 12)),
        secondary: Icon(icon, color: AppTheme.accentCyan),
        value: value,
        onChanged: onChanged,
        activeColor: AppTheme.glassBlue,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      ),
    );
  }
}
