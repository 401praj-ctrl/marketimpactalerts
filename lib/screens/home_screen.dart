import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/event_alert.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import 'alert_details_screen.dart';
import 'watchlist_screen.dart';
import 'settings_screen.dart';
import 'package:google_fonts/google_fonts.dart';
import '../widgets/app_logo.dart';
import '../services/notification_service.dart';
import 'dart:async';
import 'dart:convert';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final ApiService _apiService = ApiService();
  List<EventAlert> _alerts = [];
  Set<String> _hiddenAlertIds = {};
  bool _isLoading = true;
  String? _errorMessage;
  bool _isAutoDeleteEnabled = true;
  bool _notificationsEnabled = true;
  bool _isRefreshing = false;
  Set<String> _previousAlertIds = {};
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _initializeApp();
  }

  @override
  void dispose() {
    super.dispose();
  }

  Future<void> _initializeApp() async {
    await _loadSettings();
    await _loadCachedAlerts();
    await _loadAlerts();
  }

  Future<void> _loadCachedAlerts() async {
    final prefs = await SharedPreferences.getInstance();
    final cachedStr = prefs.getString('cached_alerts');
    if (cachedStr != null) {
      try {
        List jsonResponse = json.decode(cachedStr);
        final alerts = jsonResponse.map((data) => EventAlert.fromJson(data)).toList();
        final filteredAlerts = _filterAlerts(alerts);
        setState(() {
          _alerts = filteredAlerts;
          _isLoading = false; // Stop loading spinner immediately
          _previousAlertIds = filteredAlerts.map((a) => a.id).toSet();
        });
      } catch (e) {
        // Ignore cache parsing errors
      }
    }
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _hiddenAlertIds = prefs.getStringList('hidden_alerts')?.toSet() ?? {};
      _isAutoDeleteEnabled = prefs.getBool('auto_delete_enabled') ?? true;
      _notificationsEnabled = prefs.getBool('notifications_enabled') ?? true;
    });
  }

  Future<void> _loadAlerts() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    
    try {
      final alerts = await _apiService.fetchAlerts();
      final filteredAlerts = _filterAlerts(alerts);
      
      if (_previousAlertIds.isNotEmpty && _notificationsEnabled) {
        _checkAndNotifyNewAlerts(filteredAlerts);
      }

      setState(() {
        _alerts = filteredAlerts;
        _isLoading = false;
        _previousAlertIds = filteredAlerts.map((a) => a.id).toSet();
        if (_alerts.isEmpty) {
          _errorMessage = "No alerts found for the current filter.";
        }
      });
      
      // Cache the result
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('cached_alerts', json.encode(alerts.map((a) => a.toJson()).toList()));
      
    } catch (e) {
      setState(() {
        _isLoading = false;
        if (_alerts.isEmpty) {
          _errorMessage = "Connection error: $e";
        }
      });
    }
  }

  List<EventAlert> _filterAlerts(List<EventAlert> alerts) {
    DateTime now = DateTime.now();
    return alerts.where((alert) {
      // 1. Filter out manually hidden alerts
      if (_hiddenAlertIds.contains(alert.id)) return false;

      // 2. Filter out alerts older than 7 days if enabled
      if (_isAutoDeleteEnabled) {
        try {
          DateTime alertDate = DateFormat("yyyy-MM-dd").parse(alert.eventDate);
          if (now.difference(alertDate).inDays > 7) return false;
        } catch (e) {
          // If date parsing fails, keep it
        }
      }
      return true;
    }).toList();
  }

  void _checkAndNotifyNewAlerts(List<EventAlert> currentAlerts) {
    for (var alert in currentAlerts) {
      if (!_previousAlertIds.contains(alert.id)) {
        // This is a new alert!
        if (alert.probability >= 70) {
          // Local notifications are no longer used since migrating to OneSignal.
          // In a real scenario, the backend that generated this alert
          // should send a push notification via OneSignal API.
          print('New high probability alert: ${alert.event}');
        }
      }
    }
  }

  Future<void> _hideAlert(String id) async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _hiddenAlertIds.add(id);
      _alerts.removeWhere((a) => a.id == id);
    });
    await prefs.setStringList('hidden_alerts', _hiddenAlertIds.toList());
  }

  Map<String, List<EventAlert>> _groupAlerts() {
    Map<String, List<EventAlert>> groups = {};
    for (var alert in _alerts) {
      String dateStr = alert.eventDate;
      if (!groups.containsKey(dateStr)) {
        groups[dateStr] = [];
      }
      groups[dateStr]!.add(alert);
    }
    
    // Sort keys (dates) in descending order
    var sortedKeys = groups.keys.toList()..sort((a, b) => b.compareTo(a));
    return {for (var k in sortedKeys) k: groups[k]!};
  }

  @override
  Widget build(BuildContext context) {
    final groupedAlerts = _groupAlerts();

    return Scaffold(
      appBar: AppBar(
        title: _buildAppLogoTitle(),
        actions: [
          IconButton(
            icon: Icon(Icons.refresh_rounded, color: _isRefreshing ? AppTheme.silver : AppTheme.glassBlue),
            onPressed: () async {
              if (_isRefreshing) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Analysis already in progress. Please wait.')),
                );
                return;
              }
              setState(() {
                _isLoading = true;
                _isRefreshing = true;
              });
              
              try {
                await _apiService.refreshAlerts();
                await _loadAlerts();
              } finally {
                setState(() => _isRefreshing = false);
              }
            },
          ),
        ],
      ),
      drawer: _buildDrawer(),
      body: _isLoading && _alerts.isEmpty
          ? const Center(child: CircularProgressIndicator(color: AppTheme.glassBlue))
          : _errorMessage != null && _alerts.isEmpty
              ? _buildErrorPlaceholder()
              : RefreshIndicator(
                  onRefresh: _loadAlerts,
                  color: AppTheme.glassBlue,
                  backgroundColor: AppTheme.cardDark,
                  child: _buildGroupedList(groupedAlerts),
                ),
    );
  }

  Widget _buildAppLogoTitle() {
    return const AppLogo();
  }

  Widget _buildGroupedList(Map<String, List<EventAlert>> groups) {
    return RefreshIndicator(
      onRefresh: _loadAlerts,
      color: AppTheme.glassBlue,
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
        itemCount: groups.length,
        itemBuilder: (context, index) {
          String date = groups.keys.elementAt(index);
          List<EventAlert> dayAlerts = groups[date]!;

          return Column(
            children: [
              _buildDateSectionHeader(date),
              ...dayAlerts.map((alert) => _buildAlertCard(alert)).toList(),
              const SizedBox(height: 20),
            ],
          );
        },
      ),
    );
  }

  Widget _buildDateSectionHeader(String date) {
    String formattedDate;
    try {
      DateTime dt = DateFormat("yyyy-MM-dd").parse(date);
      formattedDate = DateFormat("MMMM dd, yyyy").format(dt).toUpperCase();
    } catch (e) {
      formattedDate = date.toUpperCase();
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Row(
        children: [
          const Expanded(child: Divider(color: AppTheme.white10)),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Text(
              formattedDate,
              style: TextStyle(
                color: AppTheme.silver,
                fontWeight: FontWeight.bold,
                fontSize: 12,
                letterSpacing: 2,
              ),
            ),
          ),
          const Expanded(child: Divider(color: AppTheme.white10)),
        ],
      ),
    );
  }

  Widget _buildAlertCard(EventAlert alert) {
    final impactColor = AppTheme.getImpactColor(alert.impactDirection);
    
    return Container(
      margin: const EdgeInsets.only(bottom: 24),
      decoration: BoxDecoration(
        color: AppTheme.cardDark.withOpacity(0.4),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: AppTheme.white05, width: 1),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.2),
            blurRadius: 10,
            offset: const Offset(0, 4),
          )
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (context) => AlertDetailsScreen(alert: alert)),
            ),
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      _buildImpactBadge(alert.impactDirection, impactColor),
                      IconButton(
                        icon: const Icon(Icons.close_rounded, color: Colors.white24, size: 22),
                        onPressed: () => _showDeleteConfirmation(alert),
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  Text(
                    alert.event,
                    style: GoogleFonts.outfit(
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                      height: 1.3,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Icon(Icons.layers_rounded, size: 16, color: AppTheme.silver),
                      const SizedBox(width: 8),
                      Flexible(
                        child: Text(
                          alert.sector.toUpperCase(),
                          style: GoogleFonts.inter(
                            color: AppTheme.silver,
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            letterSpacing: 0.5,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      const Spacer(),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: AppTheme.glassBlue.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          '${alert.probability}% CONFIDENCE',
                          style: GoogleFonts.inter(
                            color: AppTheme.glassBlue,
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  _buildStockChips(alert.stocks),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildImpactBadge(String direction, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(30),
        border: Border.all(color: color.withOpacity(0.3), width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            direction.toLowerCase() == 'up' ? Icons.trending_up_rounded : Icons.trending_down_rounded,
            size: 14,
            color: color,
          ),
          const SizedBox(width: 6),
          Text(
            direction.toUpperCase(),
            style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 11, letterSpacing: 1),
          ),
        ],
      ),
    );
  }

  Widget _buildStockChips(List<String> stocks) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: stocks.map((stock) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: AppTheme.glassBlue.withOpacity(0.05),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: AppTheme.glassBlue.withOpacity(0.1)),
        ),
        child: Text(
          stock,
          style: const TextStyle(color: AppTheme.glassBlue, fontSize: 11, fontWeight: FontWeight.bold),
        ),
      )).toList(),
    );
  }

  void _showDeleteConfirmation(EventAlert alert) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppTheme.cardDark,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Text('Remove Alert?'),
        content: const Text('This alert will be hidden from your feed.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('CANCEL', style: TextStyle(color: AppTheme.silver)),
          ),
          TextButton(
            onPressed: () {
              _hideAlert(alert.id);
              Navigator.pop(context);
            },
            child: const Text('REMOVE', style: TextStyle(color: Colors.redAccent, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  Widget _buildDrawer() {
    return Drawer(
      backgroundColor: AppTheme.spaceDark,
      child: Column(
        children: [
          _buildDrawerHeader(),
          _buildDrawerItem(Icons.home_filled, 'Dashboard', () => Navigator.pop(context), active: true),
          _buildDrawerItem(Icons.bookmark_rounded, 'Watchlist', () {
            Navigator.pop(context);
            Navigator.push(context, MaterialPageRoute(builder: (context) => const WatchlistScreen()));
          }),
          const Spacer(),
          _buildDrawerItem(Icons.settings_suggest_rounded, 'Settings', () {
            Navigator.pop(context);
            Navigator.push(context, MaterialPageRoute(builder: (context) => const SettingsScreen()));
          }),
          const SizedBox(height: 20),
        ],
      ),
    );
  }

  Widget _buildDrawerHeader() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(24, 64, 24, 32),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppTheme.spaceDark, AppTheme.cardDark.withOpacity(0.8)],
        ),
        border: const Border(bottom: BorderSide(color: AppTheme.white05)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const AppLogo(size: 48, showText: false),
          const SizedBox(height: 24),
          Text(
            'ALPHA IMPACT',
            style: GoogleFonts.outfit(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              letterSpacing: 1,
              color: Colors.white,
            ),
          ),
          const Text(
            'Alpha Engine v1.0.5',
            style: TextStyle(color: AppTheme.silver, fontSize: 13, letterSpacing: 1),
          ),
        ],
      ),
    );
  }

  Widget _buildDrawerItem(IconData icon, String title, VoidCallback onTap, {bool active = false}) {
    return ListTile(
      leading: Icon(icon, color: active ? AppTheme.glassBlue : AppTheme.silver, size: 24),
      title: Text(
        title,
        style: TextStyle(
          color: active ? Colors.white : AppTheme.silver,
          fontWeight: active ? FontWeight.bold : FontWeight.normal,
          fontSize: 16,
        ),
      ),
      onTap: onTap,
      contentPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 4),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    );
  }

  Widget _buildErrorPlaceholder() {
    bool isInitialSync = _alerts.isEmpty && (_errorMessage == null || _errorMessage!.contains("No alerts"));
    
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(40),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (isInitialSync) ...[
              const AppLogo(size: 80, showText: false),
              const SizedBox(height: 32),
              Text(
                'SYNCHRONIZING...',
                style: GoogleFonts.outfit(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 2,
                  color: Colors.white,
                ),
              ),
              const SizedBox(height: 16),
              const Text(
                'Please wait for a minute.\nAlpha Engine is loading market data...',
                textAlign: TextAlign.center,
                style: TextStyle(color: AppTheme.silver, height: 1.5),
              ),
              const SizedBox(height: 48),
              const SizedBox(
                width: 200,
                child: LinearProgressIndicator(
                  backgroundColor: Colors.white10,
                  color: AppTheme.glassBlue,
                  minHeight: 2,
                ),
              ),
            ] else ...[
              Icon(Icons.cloud_off_rounded, size: 80, color: Colors.redAccent.withOpacity(0.3)),
              const SizedBox(height: 24),
              Text(
                'NETWORK SYNC FAILED',
                style: GoogleFonts.outfit(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white70),
              ),
              const SizedBox(height: 12),
              Text(
                _errorMessage ?? 'Unknown error occurred.',
                textAlign: TextAlign.center,
                style: const TextStyle(color: AppTheme.silver),
              ),
              const SizedBox(height: 30),
              ElevatedButton.icon(
                onPressed: _loadAlerts,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('RETRY CONNECTION'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.glassBlue,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 15),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
