import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  // Premium Color Palette
  static const Color spaceDark = Color(0xFF0F172A);
  static const Color cardDark = Color(0xFF1E293B);
  static const Color glassBlue = Color(0xFF38BDF8);
  static const Color accentCyan = Color(0xFF22D3EE);
  static const Color silver = Color(0xFF94A3B8);
  static const Color white05 = Color(0x0DFFFFFF);
  static const Color white10 = Color(0x1AFFFFFF);
  
  static ThemeData darkTheme = ThemeData(
    brightness: Brightness.dark,
    primaryColor: glassBlue,
    scaffoldBackgroundColor: spaceDark,
    cardColor: cardDark,
    
    // Premium Typography
    textTheme: GoogleFonts.outfitTextTheme(ThemeData.dark().textTheme).copyWith(
      displayLarge: GoogleFonts.outfit(fontWeight: FontWeight.bold, color: Colors.white),
      titleLarge: GoogleFonts.outfit(fontWeight: FontWeight.w600, color: Colors.white),
      bodyLarge: GoogleFonts.inter(color: silver, fontSize: 16),
      bodyMedium: GoogleFonts.inter(color: silver, fontSize: 14),
    ),
    
    colorScheme: const ColorScheme.dark(
      primary: glassBlue,
      secondary: accentCyan,
      surface: cardDark,
      background: spaceDark,
    ),
    
    appBarTheme: const AppBarTheme(
      backgroundColor: spaceDark,
      elevation: 0,
      centerTitle: true,
      titleTextStyle: TextStyle(
        fontSize: 20,
        fontWeight: FontWeight.bold,
        letterSpacing: 0.5,
      ),
    ),
    
    cardTheme: CardThemeData(
      color: cardDark,
      elevation: 8,
      shadowColor: Colors.black45,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
    ),
  );

  static Color getImpactColor(String direction) {
    switch (direction.toLowerCase()) {
      case 'up':
        return const Color(0xFF4ADE80); // Success Green
      case 'down':
        return const Color(0xFFF87171); // Danger Red
      default:
        return const Color(0xFFFBBF24); // Alert Amber
    }
  }

  // Glassmorphic Decoration Utility
  static BoxDecoration glassDecoration() {
    return BoxDecoration(
      color: Colors.white.withOpacity(0.05),
      borderRadius: BorderRadius.circular(20),
      border: Border.all(color: Colors.white.withOpacity(0.1)),
    );
  }
}
