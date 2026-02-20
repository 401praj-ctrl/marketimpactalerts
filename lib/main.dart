import 'package:flutter/material.dart';
import 'package:market_impact_alerts/theme/app_theme.dart';
import 'package:market_impact_alerts/screens/home_screen.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:market_impact_alerts/widgets/app_logo.dart';
import 'package:market_impact_alerts/services/notification_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

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

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
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
  @override
  void initState() {
    super.initState();
    _checkFirstLaunch();
    _navigateToHome();
  }

  Future<void> _checkFirstLaunch() async {
    final prefs = await SharedPreferences.getInstance();
    final isFirstLaunch = prefs.getBool('is_first_launch') ?? true;
    
    if (isFirstLaunch) {
      await NotificationService.requestPermissions();
      await prefs.setBool('is_first_launch', false);
    }
  }

  Future<void> _navigateToHome() async {
    await Future.delayed(const Duration(seconds: 3));
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
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const AppLogo(size: 80, showText: false),
            const SizedBox(height: 40),
            const AppLogo(showText: true, isLarge: true, size: 0), // Use 0 size to just show high-res text part
            const SizedBox(height: 60),
            const SizedBox(
              width: 160,
              child: LinearProgressIndicator(
                backgroundColor: Colors.white10,
                color: AppTheme.glassBlue,
                minHeight: 2,
              ),
            ),
            const SizedBox(height: 20),
            Text(
              'POWERING ALPHA ENGINE v1.0.5',
              style: GoogleFonts.inter(
                color: AppTheme.silver.withOpacity(0.5),
                fontSize: 10,
                letterSpacing: 3,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
