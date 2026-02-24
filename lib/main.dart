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
        _appVersion = packageInfo.version;
      });
    }

    // 2. Always request/verify permissions and register with OneSignal on startup
    await NotificationService.requestPermissions();
    
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('is_first_launch', false);

    // 3. Check for Update
    await _performVersionCheck(packageInfo.version);
    
    // 4. If no update, proceed to home after delay
    if (!_showUpdateUI) {
      _navigateToHome();
    }
  }

  Future<void> _performVersionCheck(String currentVersion) async {
    print('Splash: Current App Version: $currentVersion');
    try {
      final updateInfo = await _apiService.getLatestAppVersion();
      if (updateInfo != null) {
        final String latestVersion = updateInfo['latest_version'] ?? '1.2.0';
        print('Splash: Latest Server Version: $latestVersion');
        
        bool isNewer = _isVersionNewer(currentVersion, latestVersion);
        print('Splash: Is newer version available? $isNewer');

        if (isNewer) {
          if (mounted) {
            setState(() {
              _updateInfo = updateInfo;
              _showUpdateUI = true;
              _isCheckingUpdate = false;
            });
          }
          return;
        }
      } else {
        print('Splash: No update info received from server (null)');
      }
    } catch (e) {
      print('Splash: Update check failed with error: $e');
    }
    
    if (mounted) {
      setState(() {
        _isCheckingUpdate = false;
      });
    }
  }

  bool _isVersionNewer(String current, String latest) {
    try {
      List<int> currentParts = current.split('+')[0].split('.').map(int.parse).toList();
      List<int> latestParts = latest.split('+')[0].split('.').map(int.parse).toList();

      for (int i = 0; i < 3; i++) {
        int c = i < currentParts.length ? currentParts[i] : 0;
        int l = i < latestParts.length ? latestParts[i] : 0;
        if (l > c) return true;
        if (l < c) return false;
      }
    } catch (e) {
      print('Version Comparison Error: $e');
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
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const AppLogo(size: 80, showText: false),
        const SizedBox(height: 40),
        const AppLogo(showText: true, isLarge: true, size: 40),
        const SizedBox(height: 60),
        if (_isCheckingUpdate)
          const SizedBox(
            width: 160,
            child: LinearProgressIndicator(
              backgroundColor: Colors.white10,
              valueColor: AlwaysStoppedAnimation<Color>(AppTheme.glassBlue),
              minHeight: 2,
            ),
          ),
        const SizedBox(height: 20),
        Text(
          'POWERING ALPHA ENGINE v$_appVersion',
          style: GoogleFonts.inter(
            color: AppTheme.silver.withOpacity(0.5),
            fontSize: 10,
            letterSpacing: 3,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }

  Widget _buildUpdateUI() {
    final version = _updateInfo?['latest_version'] ?? 'Latest';
    final notes = _updateInfo?['release_notes'] ?? 'Improvements and bug fixes.';
    final url = _updateInfo?['download_url'] ?? '';

    return Padding(
      key: const ValueKey('update'),
      padding: const EdgeInsets.symmetric(horizontal: 40),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: AppTheme.glassBlue.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.system_update_rounded, color: AppTheme.glassBlue, size: 48),
          ),
          const SizedBox(height: 32),
          Text(
            'NEW ENGINE READY',
            style: GoogleFonts.outfit(
              color: Colors.white,
              fontSize: 24,
              fontWeight: FontWeight.bold,
              letterSpacing: 1,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Version $version is available',
            style: TextStyle(color: AppTheme.silver, fontSize: 14),
          ),
          const SizedBox(height: 40),
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: AppTheme.cardDark.withOpacity(0.5),
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: AppTheme.white05),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'RELEASE NOTES',
                  style: GoogleFonts.inter(
                    color: AppTheme.glassBlue,
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 2,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  notes,
                  style: const TextStyle(color: Colors.white, fontSize: 13, height: 1.5),
                ),
              ],
            ),
          ),
          const SizedBox(height: 60),
          SizedBox(
            width: double.infinity,
            height: 56,
            child: ElevatedButton(
              onPressed: () => _startInAppUpdate(url, version),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.glassBlue,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              ),
              child: const Text(
                'UPDATE NOW',
                style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
              ),
            ),
          ),
          const SizedBox(height: 16),
          TextButton(
            onPressed: () => _navigateToHome(),
            child: Text(
              'LATER',
              style: TextStyle(color: AppTheme.silver.withOpacity(0.7), letterSpacing: 1),
            ),
          ),
        ],
      ),
    );
  }

  void _startInAppUpdate(String url, String version) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => _UpdateProgressDialog(url: url, version: version),
    );
  }
}

class _UpdateProgressDialog extends StatefulWidget {
  final String url;
  final String version;

  const _UpdateProgressDialog({required this.url, required this.version});

  @override
  State<_UpdateProgressDialog> createState() => _UpdateProgressDialogState();
}

class _UpdateProgressDialogState extends State<_UpdateProgressDialog> {
  String _status = 'Initializing...';
  double _progress = 0;
  String _mbDownloaded = '0';
  String _totalMb = '...';
  bool _isDone = false;
  bool _isError = false;
  CancelToken _cancelToken = CancelToken();

  @override
  void initState() {
    super.initState();
    _executeUpgrade();
  }

  @override
  void dispose() {
    _cancelToken.cancel();
    super.dispose();
  }

  Future<void> _executeUpgrade() async {
    try {
      final Directory docsDir = await getApplicationDocumentsDirectory();
      final String savePath = "${docsDir.path}/market_impact_${widget.version}.apk";

      final dio = Dio();
      await dio.download(
        widget.url,
        savePath,
        cancelToken: _cancelToken,
        onReceiveProgress: (received, total) {
          if (total != -1) {
            if (mounted) {
              setState(() {
                _status = 'Downloading update...';
                _progress = (received / total * 100);
                _totalMb = (total / (1024 * 1024)).toStringAsFixed(1);
                _mbDownloaded = (received / (1024 * 1024)).toStringAsFixed(1);
              });
            }
          }
        },
      );

      if (mounted) {
        setState(() {
          _status = 'Download complete! Checking permissions...';
        });
      }

      if (Platform.isAndroid) {
        var status = await Permission.requestInstallPackages.status;
        if (status.isDenied || status.isPermanentlyDenied) {
          status = await Permission.requestInstallPackages.request();
        }

        if (!status.isGranted) {
          if (mounted) {
            setState(() {
              _status = "Install permission required.";
              _isError = true;
            });
          }
          return;
        }
      }

      final result = await OpenFile.open(savePath);
      if (result.type != ResultType.done) {
        if (mounted) {
          setState(() {
            _status = "Error opening APK";
            _isError = true;
          });
        }
      } else {
        if (mounted) {
          setState(() {
            _status = 'Installer launched!';
            _isDone = true;
          });
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _status = 'Update failed.';
          _isError = true;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: AppTheme.cardDark,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      title: Row(
        children: [
          const Icon(Icons.cloud_download_rounded, color: AppTheme.glassBlue),
          const SizedBox(width: 12),
          Text('Downloading Update', style: GoogleFonts.outfit(fontWeight: FontWeight.bold, fontSize: 18)),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(_status, style: const TextStyle(color: Colors.white, fontSize: 14)),
          const SizedBox(height: 24),
          if (!_isError && !_isDone) ...[
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: LinearProgressIndicator(
                value: _progress / 100,
                backgroundColor: Colors.white.withOpacity(0.05),
                valueColor: const AlwaysStoppedAnimation<Color>(AppTheme.glassBlue),
                minHeight: 10,
              ),
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('${_mbDownloaded}MB / ${_totalMb}MB', style: const TextStyle(color: AppTheme.silver, fontSize: 12)),
                Text('${_progress.toInt()}%', style: const TextStyle(color: AppTheme.glassBlue, fontWeight: FontWeight.bold)),
              ],
            ),
          ],
          if (_isError) ...[
            const Icon(Icons.error_outline_rounded, color: Colors.redAccent, size: 48),
            const SizedBox(height: 12),
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('CLOSE', style: TextStyle(color: AppTheme.silver)),
            ),
          ],
          if (_isDone) ...[
            const Icon(Icons.check_circle_outline_rounded, color: Colors.greenAccent, size: 48),
            const SizedBox(height: 12),
            ElevatedButton(
              onPressed: () => Navigator.pop(context),
              style: ElevatedButton.styleFrom(backgroundColor: AppTheme.glassBlue),
              child: const Text('OK', style: TextStyle(color: Colors.white)),
            ),
          ],
        ],
      ),
    );
  }
}

