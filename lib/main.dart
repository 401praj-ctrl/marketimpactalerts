import 'package:flutter/material.dart';
import 'package:market_impact_alerts/theme/app_theme.dart';
import 'package:market_impact_alerts/screens/home_screen.dart';

void main() {
  runApp(const MarketImpactApp());
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
    Future.delayed(const Duration(seconds: 3), () {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (context) => const HomeScreen()),
      );
    });
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
            Container(
              height: 100,
              width: 100,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: const LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [AppTheme.glassBlue, Color(0xFF1E40AF)],
                ),
                boxShadow: [
                  BoxShadow(
                    color: AppTheme.glassBlue.withOpacity(0.4),
                    blurRadius: 30,
                    spreadRadius: 5,
                  )
                ],
              ),
              child: const Icon(Icons.analytics_rounded, size: 50, color: Colors.white),
            ),
            const SizedBox(height: 40),
            RichText(
              textAlign: TextAlign.center,
              text: TextSpan(
                style: GoogleFonts.outfit(
                  fontSize: 36,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 2,
                  color: Colors.white,
                ),
                children: const [
                  TextSpan(text: 'IMPACT'),
                  TextSpan(
                    text: '\nALERTS',
                    style: TextStyle(color: AppTheme.glassBlue),
                  ),
                ],
              ),
            ),
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
              'POWERING ALPHA ENGINE v1.0.4',
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
