import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../theme/app_theme.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool _notificationsEnabled = true;
  bool _autoDeleteEnabled = true;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _autoDeleteEnabled = prefs.getBool('auto_delete_enabled') ?? true;
      _notificationsEnabled = prefs.getBool('notifications_enabled') ?? true;
    });
  }

  Future<void> _saveSetting(String key, bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(key, value);
  }

  Future<void> _resetHiddenAlerts() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('hidden_alerts');
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
          const SizedBox(height: 12),
          ListTile(
            leading: const Icon(Icons.restore_rounded, color: AppTheme.silver),
            title: const Text('Restore Hidden Alerts'),
            subtitle: const Text('Bring back all manually deleted items'),
            onTap: _resetHiddenAlerts,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          ),
          const SizedBox(height: 24),
          _buildSectionHeader('SYSTEM'),
          ListTile(
            leading: const Icon(Icons.info_outline, color: AppTheme.silver),
            title: const Text('Engine Version'),
            subtitle: const Text('Alpha Engine v1.0.4'),
            trailing: const Text('STABLE', style: TextStyle(color: AppTheme.glassBlue, fontWeight: FontWeight.bold, fontSize: 10)),
          ),
        ],
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
