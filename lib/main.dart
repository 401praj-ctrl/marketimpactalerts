import 'package:flutter/material.dart';
import 'package:market_impact_alerts/theme/app_theme.dart';
import 'package:market_impact_alerts/screens/home_screen.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:market_impact_alerts/widgets/app_logo.dart';
import 'package:market_impact_alerts/services/notification_service.dart';
import 'package:market_impact_alerts/services/api_service.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:dio/dio.dart';
import 'package:path_provider/path_provider.dart';
import 'package:open_file/open_file.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:market_impact_alerts/widgets/update_dialog.dart';
import 'dart:io';

void main() async {
  try {
    WidgetsFlutterBinding.ensureInitialized();
    await NotificationService.init();
    runApp(const MarketImpactApp());
  } catch (e, stackTrace) {
    print('Initialization Error: $e');
    runApp(ErrorApp(error: e.toString(), stackTrace: stackTrace));
  }
}

class ErrorApp extends StatelessWidget {
  final String error;
  final StackTrace? stackTrace;
  const ErrorApp({super.key, required this.error, this.stackTrace});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: Scaffold(
        backgroundColor: Colors.black,
        body: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, color: Colors.red, size: 50),
              const SizedBox(height: 20),
              const Text('Startup Error', style: TextStyle(color: Colors.white, fontSize: 20)),
              const SizedBox(height: 10),
              Text(error, style: const TextStyle(color: Colors.white70)),
              const SizedBox(height: 10),
              if (stackTrace != null)
                Text(stackTrace.toString(), style: const TextStyle(color: Colors.white30, fontSize: 10)),
            ],
          ),
        ),
      ),
    );
  }
}

class MarketImpactApp extends StatelessWidget {
  const MarketImpactApp({super.key});

  static final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      navigatorKey: navigatorKey,
      title: 'Market Impact Alerts',
      theme: AppTheme.darkTheme,
      home: const SplashScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  final ApiService _apiService = ApiService();
  String _appVersion = '1.0.0';
  bool _showUpdateUI = false;
  Map<String, dynamic>? _updateInfo;
  bool _isCheckingUpdate = true;
  String _statusMessage = 'Initializing...';
  bool _showRetryButton = false;

  @override
  void initState() {
    super.initState();
    _initializeApp();
  }

  Future<void> _initializeApp() async {
    // 1. Fetch dynamic version
    final packageInfo = await PackageInfo.fromPlatform();
    if (mounted) {
      setState(() {
        _appVersion = "${packageInfo.version}+${packageInfo.buildNumber}";
        _statusMessage = 'Checking for critical updates...';
      });
    }

    // 3. Check for Update (Wait up to 30 seconds for cold starts)
    final String currentFullVersion = "${packageInfo.version}+${packageInfo.buildNumber}";
    try {
      if (mounted) {
        setState(() => _statusMessage = 'Initializing secure connection...');
      }
      
      // Delay slightly to let the UI breathe
      await Future.delayed(const Duration(milliseconds: 500));
      
      if (mounted) {
        setState(() => _statusMessage = 'Optimizing for peak performance...');
      }

      await _performVersionCheck(currentFullVersion).timeout(const Duration(seconds: 30));
    } catch (e) {
      print('Splash: Update check timed out or failed: $e');
      if (mounted) {
        setState(() {
           _isCheckingUpdate = false;
        });
      }
    }
    
    // 4. Register and request permissions (DON'T AWAIT - avoids blocking the app start)
    NotificationService.requestPermissions().catchError((e) {
      print('Splash: Permission request failed: $e');
    });
    
    // 5. If no update, proceed to home
    if (!_showUpdateUI) {
      if (!_showRetryButton) {
        _navigateToHome();
      } else {
         print('Splash: Update check failed. Waiting for user to RETRY.');
      }
    }
  }

  Future<void> _performVersionCheck(String currentVersion) async {
    print('Splash: Checking for update... Current: $currentVersion');
    try {
      final updateInfo = await _apiService.getLatestAppVersion();
      if (updateInfo != null) {
        final String latestVersion = updateInfo['latest_version'] ?? '';
        print('Splash: Server reports latest: $latestVersion');
        
        bool isNewer = _isVersionNewer(currentVersion, latestVersion);
        if (isNewer) {
          /* 
          // REMOVED SUPPRESSION LOGIC TO ENSURE IMMEDIATE PROMPT
          final prefs = await SharedPreferences.getInstance();
          final String? lastPromptedVersion = prefs.getString('last_prompted_version');
          final int? lastPromptedTime = prefs.getInt('last_prompted_time');
          
          if (lastPromptedVersion == latestVersion && lastPromptedTime != null) {
            final lastTime = DateTime.fromMillisecondsSinceEpoch(lastPromptedTime);
            if (DateTime.now().difference(lastTime).inHours < 2) {
              print('Splash: Update suppressed for $latestVersion (Last prompt: $lastTime)');
              return;
            }
          }
          */

          print('Splash: New version available. Showing update UI.');
          if (mounted) {
            setState(() {
              _updateInfo = updateInfo;
              _showUpdateUI = true;
              _isCheckingUpdate = false;
            });
            // Mark as prompted
            final prefs = await SharedPreferences.getInstance();
            await prefs.setString('last_prompted_version', latestVersion);
            await prefs.setInt('last_prompted_time', DateTime.now().millisecondsSinceEpoch);
          }
          return;
        } else {
          print('Splash: App is up to date.');
        }
      } else {
        print('Splash: Could not reach update server.');
      }
    } catch (e) {
      print('Splash: Error during update check: $e');
      if (mounted) {
        setState(() {
          _statusMessage = 'Update check failed. Continuing...';
          _showRetryButton = true;
        });
      }
    }
    
    if (mounted) {
      setState(() {
        _isCheckingUpdate = false;
      });
    }
  }

  bool _isVersionNewer(String current, String latest) {
    print('Splash: Comparing Current($current) vs Latest($latest)');
    try {
      // 1. Compare main version (X.Y.Z)
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

      // 2. Compare build numbers (after the +)
      int currentBuild = 0;
      int latestBuild = 0;
      
      if (current.contains('+')) {
        String b = current.split('+')[1].trim();
        currentBuild = int.tryParse(b) ?? 0;
      }
      if (latest.contains('+')) {
        String b = latest.split('+')[1].trim();
        latestBuild = int.tryParse(b) ?? 0;
      }

      print('Splash: Build Comparison - Current: $currentBuild, Latest: $latestBuild');
      if (latestBuild > currentBuild) return true;
      
    } catch (e) {
      print('Splash: Version Comparison Error: $e');
    }
    return false;
  }

  Future<void> _navigateToHome() async {
    await Future.delayed(const Duration(seconds: 2));
    if (mounted) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (context) => const HomeScreen()),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.spaceDark,
      body: Container(
        width: double.infinity,
        decoration: BoxDecoration(
          gradient: RadialGradient(
            center: Alignment.center,
            radius: 1.5,
            colors: [
              AppTheme.glassBlue.withOpacity(0.05),
              AppTheme.spaceDark,
            ],
          ),
        ),
        child: AnimatedSwitcher(
          duration: const Duration(milliseconds: 500),
          child: _showUpdateUI ? _buildUpdateUI() : _buildSplashScreenUI(),
        ),
      ),
    );
  }

  Widget _buildSplashScreenUI() {
    return Column(
      key: const ValueKey('splash'),
      children: [
        const Spacer(flex: 3),
        // Central Large Logo
        const AppLogo(size: 140, showText: false),
        const Spacer(flex: 1),
        // Secondary Title Row
        const AppLogo(size: 32, showText: true, isLarge: true),
        const Spacer(flex: 2),
        // Progress Section
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 60),
          child: Column(
            children: [
              if (_isCheckingUpdate) ...[
                ClipRRect(
                  borderRadius: BorderRadius.circular(2),
                  child: const LinearProgressIndicator(
                    backgroundColor: Colors.white10,
                    valueColor: AlwaysStoppedAnimation<Color>(AppTheme.glassBlue),
                    minHeight: 2,
                  ),
                ),
                const SizedBox(height: 20),
                Text(
                  _statusMessage,
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.white30, fontSize: 13),
                ),
              ] else if (_showRetryButton) ...[
                Text(
                  _statusMessage,
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.white30, fontSize: 13),
                ),
                const SizedBox(height: 15),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    TextButton(
                      onPressed: () => _initializeApp(),
                      child: const Text('RETRY', style: TextStyle(color: AppTheme.glassBlue)),
                    ),
                    const SizedBox(width: 20),
                    TextButton(
                      onPressed: () => _navigateToHome(),
                      child: const Text('BYPASS', style: TextStyle(color: Colors.white24)),
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),
        const Spacer(flex: 2),
        // Footer
        Opacity(
          opacity: 0.3,
          child: Column(
            children: [
              Text(
                'POWERING ALPHA ENGINE',
                style: GoogleFonts.outfit(
                  fontSize: 10,
                  letterSpacing: 2,
                  color: Colors.white,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'v$_appVersion',
                style: GoogleFonts.outfit(
                  fontSize: 10,
                  color: Colors.white,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 50),
      ],
    );
  }
  Widget _buildUpdateUI() {
    final version = _updateInfo?['latest_version'] ?? 'Latest';
    final notes = _updateInfo?['release_notes'] ?? 'Improvements and bug fixes.';
    final url = _updateInfo?['download_url'] ?? '';

    return Container(
      key: const ValueKey('update'),
      width: double.infinity,
      child: Column(
        children: [
          const Spacer(flex: 2),
          // Unify with Splash
          const AppLogo(size: 100, showText: false),
          const SizedBox(height: 24),
          const AppLogo(size: 24, showText: true, isLarge: true),
          const Spacer(flex: 1),
          
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 40),
            child: Column(
              children: [
                Text(
                  'ENGINE UPGRADE READY',
                  style: GoogleFonts.outfit(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'v$version is now available',
                  style: const TextStyle(color: AppTheme.glassBlue, fontSize: 13, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 32),
                
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: AppTheme.cardDark.withOpacity(0.5),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: AppTheme.white05),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.auto_awesome, color: AppTheme.glassBlue, size: 14),
                          const SizedBox(width: 8),
                          Text(
                            'WHAT\'S NEW',
                            style: GoogleFonts.inter(
                              color: AppTheme.glassBlue,
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                              letterSpacing: 2,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Text(
                        notes,
                        style: const TextStyle(color: Colors.white70, fontSize: 12, height: 1.6),
                      ),
                    ],
                  ),
                ),
                
                const SizedBox(height: 48),
                
                SizedBox(
                  width: double.infinity,
                  height: 54,
                  child: ElevatedButton(
                    onPressed: () => _startInAppUpdate(url, version),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.glassBlue,
                      foregroundColor: Colors.white,
                      elevation: 0,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    child: const Text(
                      'ACTIVATE UPGRADE',
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, letterSpacing: 1),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                const Text(
                  'MANDATORY FOR PERFORMANCE',
                  style: TextStyle(color: Colors.white24, fontSize: 9, letterSpacing: 1),
                ),
              ],
            ),
          ),
          const Spacer(flex: 2),
        ],
      ),
    );
  }

  void _startInAppUpdate(String url, String version) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => UpdateProgressDialog(url: url, version: version),
    );
  }
}

// End of SplashScreen

