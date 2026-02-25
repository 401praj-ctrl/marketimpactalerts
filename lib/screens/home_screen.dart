import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/event_alert.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import 'alert_details_screen.dart';
import 'watchlist_screen.dart';
import 'settings_screen.dart';
import 'prediction_screen.dart';
import 'package:google_fonts/google_fonts.dart';
import '../widgets/app_logo.dart';
import '../services/notification_service.dart';
import 'dart:async';
import 'dart:convert';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:dio/dio.dart';
import 'package:path_provider/path_provider.dart';
import 'package:open_file/open_file.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:market_impact_alerts/widgets/update_dialog.dart';
import 'dart:io';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final ApiService _apiService = ApiService();
  List<EventAlert> _allAlerts = [];
  Set<String> _hiddenAlertIds = {};
  bool _isLoading = true;
  String? _errorMessage;
  bool _isAutoDeleteEnabled = true;
  bool _notificationsEnabled = true;
  String _selectedSector = 'All';
  Set<String> _userWatchlist = {};
  bool _isRefreshing = false;
  bool _isAnalyzing = true; // Assume true on boot until confirmed false
  Set<String> _previousAlertIds = {};
  Timer? _refreshTimer;
  Timer? _statusTimer;

  // Search state
  bool _isSearchActive = false;
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';
  String _appVersion = '1.0.0';

  @override
  void initState() {
    super.initState();
    _initializeApp();
    _startRefreshTimer();
    _startStatusTimer();
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    _statusTimer?.cancel();
    super.dispose();
  }

  void _startStatusTimer() {
    _statusTimer?.cancel();
    // Poll every 5 seconds for backend analysis status
    _statusTimer = Timer.periodic(const Duration(seconds: 5), (timer) async {
      if (!mounted) return;
      
      bool currentlyAnalyzing = await _apiService.checkAnalysisStatus();
      
      if (!mounted) return;
      
      // Transition from TRUE to FALSE means cycle just completed
      if (_isAnalyzing && !currentlyAnalyzing) {
        print('HomeScreen: Analysis cycle completed. Fetching latest alerts...');
        _loadAlerts();
      }
      
      if (_isAnalyzing != currentlyAnalyzing) {
        setState(() {
          _isAnalyzing = currentlyAnalyzing;
        });
      }
    });
  }

  void _startRefreshTimer() {
    _refreshTimer?.cancel();
    _refreshTimer = Timer.periodic(const Duration(minutes: 10), (timer) {
      if (mounted && !_isLoading && !_isRefreshing) {
        print('HomeScreen: Auto-refreshing alerts...');
        _loadAlerts();
      }
    });
  }

  Future<void> _initializeApp() async {
    await _loadSettings();
    await _loadCachedAlerts();
    await _loadAlerts();
    PackageInfo packageInfo = await PackageInfo.fromPlatform();
    if (mounted) {
      setState(() {
        _appVersion = "${packageInfo.version}+${packageInfo.buildNumber}";
      });
    }
    
    // Check for updates in background to ensure users don't miss them
    _checkUpdateInBackground(_appVersion);
  }

  Future<void> _loadCachedAlerts() async {
    final prefs = await SharedPreferences.getInstance();
    final cachedStr = prefs.getString('cached_alerts');
    if (cachedStr != null) {
      try {
        List jsonResponse = json.decode(cachedStr);
        final alerts = jsonResponse.map((data) => EventAlert.fromJson(data)).toList();
        setState(() {
          _allAlerts = alerts;
          _isLoading = false; // Stop loading spinner immediately
          _previousAlertIds = alerts.map((a) => a.id).toSet();
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
      // Load watchlist for highlighting
      _userWatchlist = ['HDFC Bank', 'Reliance', 'Nvidia', 'TCS'].toSet(); // Default for now, ideally from shared_prefs
    });
  }

  // Helper method for dynamic filtering inside build method or when state changes
  List<EventAlert> _getFilteredAlerts() {
    return _filterAlerts(_allAlerts);
  }

  Future<void> _loadAlerts() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    
    try {
      final serverAlerts = await _apiService.fetchAlerts();
      
      if (_previousAlertIds.isNotEmpty && _notificationsEnabled) {
        _checkAndNotifyNewAlerts(serverAlerts);
      }

      setState(() {
        // Create a map for fast lookup of existing alerts by ID
        final Map<String, EventAlert> alertMap = {
          for (var a in _allAlerts) a.id: a
        };
        
        // Merge server alerts (overwrite older versions with same ID if needed)
        for (var sa in serverAlerts) {
          alertMap[sa.id] = sa;
        }
        
        // Update the master list with all unique alerts
        _allAlerts = alertMap.values.toList();
        
        // Sort by date/timestamp descending to keep newest at top
        _allAlerts.sort((a, b) => b.timestamp.compareTo(a.timestamp));
        
        _isLoading = false;
        _previousAlertIds = _allAlerts.map((a) => a.id).toSet();
        if (_allAlerts.isEmpty) {
          _errorMessage = "No alerts found.";
        }
      });
      
      // Cache the merged list to SharedPreferences
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('cached_alerts', json.encode(_allAlerts.map((a) => a.toJson()).toList()));
      
    } catch (e) {
      setState(() {
        _isLoading = false;
        if (_allAlerts.isEmpty) {
          _errorMessage = "Connection error: $e";
        }
      });
    }
  }

  Future<void> _handleManualRefresh() async {
    if (_isRefreshing) return;
    
    setState(() {
      _isRefreshing = true;
      _isAnalyzing = true; // Show synchronizing UI immediately
    });
    
    try {
      await _apiService.refreshAlerts();
      await _loadAlerts();
    } finally {
      setState(() => _isRefreshing = false);
    }
  }

  List<EventAlert> _filterAlerts(List<EventAlert> alerts) {
    return alerts.where((alert) {
      // 1. Filter out manually hidden alerts
      if (_hiddenAlertIds.contains(alert.id)) return false;

      // 2. Filter out alerts older than 7 days if auto-delete is enabled
      if (_isAutoDeleteEnabled) {
        final now = DateTime.now();
        final alertDate = DateTime.tryParse(alert.timestamp) ?? now; // safely parse
        final difference = now.difference(alertDate);
        if (difference.inDays >= 7) return false;
      }

      // 3. Filter by selected sector
      if (_selectedSector != 'All' && alert.sector != _selectedSector) return false;

      // 3. Filter by search query (Stock Names or Event content)
      if (_searchQuery.isNotEmpty) {
        final query = _searchQuery.toLowerCase();
        final matchesEvent = alert.event.toLowerCase().contains(query);
        final matchesSector = alert.sector.toLowerCase().contains(query);
        final matchesStocks = alert.stocks.any((stock) => stock.toLowerCase().contains(query));
        
        if (!matchesEvent && !matchesSector && !matchesStocks) return false;
      }

      return true;
    }).toList();
  }

  Future<void> _checkUpdateInBackground(String current) async {
    print('HomeScreen: Background update check... Current: $current');
    try {
      final updateInfo = await _apiService.getLatestAppVersion();
      if (updateInfo != null) {
        final String latest = updateInfo['latest_version'] ?? '';
        if (_isVersionNewer(current, latest)) {
          print('HomeScreen: New version detected in background: $latest');
          if (mounted) {
            _showUpdateDialog(updateInfo);
          }
        }
      }
    } catch (e) {
      print('HomeScreen: Background update check error: $e');
    }
  }

  bool _isVersionNewer(String current, String latest) {
    try {
      String currentVer = current.split('+')[0].trim();
      String latestVer = latest.split('+')[0].trim();
      List<int> currentParts = currentVer.split('.').map((e) => int.tryParse(e) ?? 0).toList();
      List<int> latestParts = latestVer.split('.').map((e) => int.tryParse(e) ?? 0).toList();
      for (int i = 0; i < 3; i++) {
        int c = i < currentParts.length ? currentParts[i] : 0;
        int l = i < latestParts.length ? latestParts[i] : 0;
        if (l > c) return true;
        if (l < c) return false;
      }
      int currentBuild = 0;
      int latestBuild = 0;
      if (current.contains('+')) currentBuild = int.tryParse(current.split('+')[1].trim()) ?? 0;
      if (latest.contains('+')) latestBuild = int.tryParse(latest.split('+')[1].trim()) ?? 0;
      if (latestBuild > currentBuild) return true;
    } catch (e) {}
    return false;
  }

  void _showUpdateDialog(Map<String, dynamic> updateInfo) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        backgroundColor: AppTheme.spaceDark,
        title: const Text('New Update Available', style: TextStyle(color: Colors.white)),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Version: ${updateInfo['latest_version']}', 
                   style: const TextStyle(color: AppTheme.glassBlue, fontWeight: FontWeight.bold)),
              const SizedBox(height: 10),
              Text(updateInfo['release_notes'] ?? 'New features and improvements.', 
                   style: const TextStyle(color: Colors.white70)),
            ],
          ),
        ),
        actions: [
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.glassBlue),
            onPressed: () {
              Navigator.pop(context);
              // Show the shared mandatory update dialog instead of launching URL
              showDialog(
                context: context,
                barrierDismissible: false,
                builder: (context) => UpdateProgressDialog(
                  url: updateInfo['download_url'] ?? '',
                  version: updateInfo['latest_version'] ?? 'Latest',
                ),
              );
            },
            child: const Text('UPDATE NOW', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  // Helper removed as we now use UpdateProgressDialog
  /* 
  void _launchUpdate(String? url) async { ... }
  */

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
      _allAlerts.removeWhere((a) => a.id == id);
    });
    await prefs.setStringList('hidden_alerts', _hiddenAlertIds.toList());
  }

  Map<String, List<EventAlert>> _groupAlerts() {
    Map<String, List<EventAlert>> groups = {};
    final filtered = _getFilteredAlerts();
    for (var alert in filtered) {
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
        title: _isSearchActive ? _buildSearchField() : _buildAppLogoTitle(),
        actions: [
          IconButton(
            icon: Icon(_isSearchActive ? Icons.close_rounded : Icons.search_rounded, color: AppTheme.glassBlue),
            onPressed: () {
              setState(() {
                if (_isSearchActive) {
                  _isSearchActive = false;
                  _searchController.clear();
                  _searchQuery = '';
                } else {
                  _isSearchActive = true;
                }
              });
            },
          ),
          IconButton(
            icon: Icon(Icons.analytics_outlined, color: AppTheme.glassBlue),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const PredictionScreen()),
              );
            },
          ),
          IconButton(
            icon: Icon(Icons.refresh_rounded, color: _isRefreshing ? AppTheme.silver : AppTheme.glassBlue),
            onPressed: _handleManualRefresh,
          ),
        ],
      ),
      drawer: _buildDrawer(),
      body: _isLoading && _allAlerts.isEmpty
          ? const Center(child: CircularProgressIndicator(color: AppTheme.glassBlue))
          : Column(
              children: [
                if (_errorMessage != null && _allAlerts.isEmpty)
                  Expanded(child: Center(child: _buildErrorPlaceholder()))
                else ...[
                  _buildMarketPulseDashboard(),
                  _buildSectorFilter(),
                  Expanded(
                    child: RefreshIndicator(
                      onRefresh: _handleManualRefresh,
                      color: AppTheme.glassBlue,
                      backgroundColor: AppTheme.cardDark,
                      child: _buildGroupedList(groupedAlerts),
                    ),
                  ),
                ],
              ],
            ),
    );
  }

  Widget _buildMarketPulseDashboard() {
    final currentAlerts = _getFilteredAlerts();
    if (currentAlerts.isEmpty) return const SizedBox.shrink();

    int bullish = currentAlerts.where((a) => a.impactDirection.toLowerCase() == 'up').length;
    int bearish = currentAlerts.where((a) => a.impactDirection.toLowerCase() == 'down').length;
    int total = currentAlerts.length;
    int bullishPercent = total > 0 ? ((bullish / total) * 100).round() : 0;

    return Container(
      margin: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [AppTheme.glassBlue.withOpacity(0.15), AppTheme.accentCyan.withOpacity(0.05)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: AppTheme.glassBlue.withOpacity(0.2)),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'MARKET PULSE',
                  style: GoogleFonts.inter(
                    color: AppTheme.glassBlue,
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 2,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  bullishPercent >= 50 ? 'BULLISH SENTIMENT' : 'CAUTIOUS SENTIMENT',
                  style: GoogleFonts.outfit(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  '$bullish Altas Up | $bearish Down | $total Total Events',
                  style: TextStyle(color: AppTheme.silver, fontSize: 12),
                ),
              ],
            ),
          ),
          Stack(
            alignment: Alignment.center,
            children: [
              SizedBox(
                width: 60,
                height: 60,
                child: CircularProgressIndicator(
                  value: bullishPercent / 100,
                  backgroundColor: AppTheme.white10,
                  color: AppTheme.getImpactColor('up'),
                  strokeWidth: 6,
                ),
              ),
              Text(
                '$bullishPercent%',
                style: GoogleFonts.outfit(
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                  color: Colors.white,
                ),
              ),
            ],
          )
        ],
      ),
    );
  }

  Widget _buildSectorFilter() {
    Set<String> sectors = {'All'};
    for (var alert in _allAlerts) {
      sectors.add(alert.sector);
    }
    List<String> sortedSectors = sectors.toList()..sort();

    return Container(
      height: 50,
      margin: const EdgeInsets.symmetric(vertical: 8),
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        itemCount: sortedSectors.length,
        itemBuilder: (context, index) {
          String sector = sortedSectors[index];
          bool isSelected = _selectedSector == sector;
          return Padding(
            padding: const EdgeInsets.only(right: 8),
            child: ChoiceChip(
              label: Text(sector.toUpperCase()),
              selected: isSelected,
              onSelected: (selected) {
                setState(() {
                  _selectedSector = sector;
                });
              },
              backgroundColor: Colors.transparent,
              selectedColor: AppTheme.glassBlue.withOpacity(0.2),
              labelStyle: GoogleFonts.inter(
                color: isSelected ? AppTheme.glassBlue : AppTheme.silver,
                fontSize: 10,
                fontWeight: FontWeight.bold,
                letterSpacing: 1,
              ),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
                side: BorderSide(
                  color: isSelected ? AppTheme.glassBlue : AppTheme.white10,
                ),
              ),
              showCheckmark: false,
            ),
          );
        },
      ),
    );
  }

  Widget _buildAppLogoTitle() {
    return LayoutBuilder(
      builder: (context, constraints) {
        return AppLogo(showText: MediaQuery.of(context).size.width > 400);
      },
    );
  }

  Widget _buildSearchField() {
    return TextField(
      controller: _searchController,
      autofocus: true,
      decoration: InputDecoration(
        hintText: 'Search stocks or events...',
        hintStyle: TextStyle(color: AppTheme.silver.withOpacity(0.5), fontSize: 16),
        border: InputBorder.none,
      ),
      style: const TextStyle(color: Colors.white, fontSize: 16),
      onChanged: (value) {
        setState(() {
          _searchQuery = value;
        });
      },
    );
  }

  Widget _buildGroupedList(Map<String, List<EventAlert>> groups) {
    return RefreshIndicator(
      onRefresh: _handleManualRefresh,
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
    bool isInWatchlist = alert.stocks.any((s) => _userWatchlist.contains(s));
    
    return Container(
      margin: const EdgeInsets.only(bottom: 24),
      decoration: BoxDecoration(
        color: AppTheme.cardDark.withOpacity(0.4),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: isInWatchlist ? AppTheme.glassBlue.withOpacity(0.3) : AppTheme.white05, 
          width: isInWatchlist ? 2 : 1
        ),
        boxShadow: [
          BoxShadow(
            color: isInWatchlist ? AppTheme.glassBlue.withOpacity(0.1) : Colors.black.withOpacity(0.2),
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
                      Row(
                        children: [
                          _buildImpactBadge(alert.impactDirection, impactColor),
                          if (isInWatchlist) ...[
                            const SizedBox(width: 8),
                            _buildWatchlistBadge(),
                          ],
                        ],
                      ),
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
                  _buildStockChips(alert),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      Icon(Icons.access_time_rounded, size: 10, color: AppTheme.silver.withOpacity(0.3)),
                      const SizedBox(width: 4),
                      Text(
                        _formatAlertTime(alert.timestamp),
                        style: GoogleFonts.inter(
                          color: AppTheme.silver.withOpacity(0.4),
                          fontSize: 10,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
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

  Widget _buildStockChips(EventAlert alert) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: alert.stocks.map((stock) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: AppTheme.glassBlue.withOpacity(0.05),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppTheme.glassBlue.withOpacity(0.1)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              stock,
              style: const TextStyle(color: AppTheme.glassBlue, fontSize: 13, fontWeight: FontWeight.bold),
            ),
            if (alert.livePrice != null) ...[
              const SizedBox(height: 4),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    _formatPrice(alert.livePrice, alert.currency),
                    style: TextStyle(color: AppTheme.silver, fontSize: 11, fontWeight: FontWeight.w500),
                  ),
                  if (alert.predictedPrice != null) ...[
                    const SizedBox(width: 4),
                    const Icon(Icons.arrow_forward_rounded, size: 10, color: Colors.white24),
                    const SizedBox(width: 4),
                    Text(
                      _formatPrice(alert.predictedPrice, alert.currency),
                      style: GoogleFonts.inter(
                        color: alert.impactDirection.toLowerCase() == 'up' ? AppTheme.getImpactColor('up') : AppTheme.getImpactColor('down'),
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ],
              ),
            ],
          ],
        ),
      )).toList(),
    );
  }

  Widget _buildWatchlistBadge() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: AppTheme.glassBlue.withOpacity(0.1),
        borderRadius: BorderRadius.circular(30),
        border: Border.all(color: AppTheme.glassBlue.withOpacity(0.3), width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.star_rounded, size: 14, color: AppTheme.glassBlue),
          const SizedBox(width: 4),
          Text(
            'WATCHLIST',
            style: GoogleFonts.inter(color: AppTheme.glassBlue, fontWeight: FontWeight.bold, fontSize: 10, letterSpacing: 1),
          ),
        ],
      ),
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
            Navigator.push(context, MaterialPageRoute(builder: (context) => const SettingsScreen())).then((_) => _initializeApp());
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
          Text(
            'Alpha Engine v$_appVersion',
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
    bool isEmptyNoError = _allAlerts.isEmpty && (_errorMessage == null || _errorMessage!.contains("No alerts"));
    
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(40),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (isEmptyNoError && _isAnalyzing) ...[
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
            ] else if (isEmptyNoError && !_isAnalyzing) ...[
              Icon(Icons.check_circle_outline_rounded, size: 80, color: AppTheme.silver.withOpacity(0.5)),
              const SizedBox(height: 24),
              Text(
                'NO NEW ALERTS',
                style: GoogleFonts.outfit(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white70),
              ),
              const SizedBox(height: 12),
              const Text(
                'Alpha Engine has completed its analysis cycle.\nNo high impact events detected.',
                textAlign: TextAlign.center,
                style: TextStyle(color: AppTheme.silver, height: 1.5),
              ),
              const SizedBox(height: 30),
              ElevatedButton.icon(
                onPressed: _handleManualRefresh,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('REFRESH NOW'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.glassBlue.withOpacity(0.2),
                  foregroundColor: AppTheme.glassBlue,
                  padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 15),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
                  elevation: 0,
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

  String _formatAlertTime(String? timestamp) {
    if (timestamp == null || timestamp.isEmpty) return "--:-- --";
    try {
      // 1. Standard ISO Parse
      DateTime dt = DateTime.parse(timestamp);
      return _formatRelative(dt);
    } catch (e) {
      // 2. Regex Fallback for "Tue, 21 Feb 2026..." common in feeds
      try {
        // Look for DD Mon YYYY
        final regex = RegExp(r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})');
        final match = regex.firstMatch(timestamp);
        if (match != null) {
          final day = int.parse(match.group(1)!);
          final monthStr = match.group(2)!;
          final year = int.parse(match.group(3)!);
          
          final months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
          final month = months.indexOf(monthStr) + 1;
          
          DateTime dt = DateTime(year, month, day);
          return _formatRelative(dt);
        }
      } catch (re) {}
      
      // 3. Simple split fallback
      return timestamp.contains(',') ? timestamp.split(',')[0] : timestamp;
    }
  }

  String _formatRelative(DateTime dt) {
    final now = DateTime.now();
    // Convert to local if naive/UTC (frontend assumption)
    dt = dt.isUtc ? dt.toLocal() : dt;
    
    final difference = now.difference(dt);

    if (difference.inMinutes < 60 && difference.inMinutes >= 0) {
      return "${difference.inMinutes}m ago";
    } else if (difference.inHours < 24 && difference.inHours >= 0) {
      return "${difference.inHours}h ago";
    } else if (difference.inHours < 48 && difference.inHours >= 0) {
      return "Yesterday";
    } else {
      return "${dt.day} ${_getMonth(dt.month)}";
    }
  }

  String _getMonth(int month) {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return months[month - 1];
  }

  String _formatPrice(double? price, String? currency) {
    if (price == null) return '...';
    final symbol = currency == "USD" ? "\$" : "₹";
    return "$symbol${price.toStringAsFixed(2)}";
  }
}
