import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  static ThemeData darkTheme = ThemeData(
    brightness: Brightness.dark,
    primaryColor: Colors.blueAccent,
    scaffoldBackgroundColor: const Color(0xFF0F172A),
    cardColor: const Color(0xFF1E293B),
    textTheme: GoogleFonts.outfitTextTheme(ThemeData.dark().textTheme),
    colorScheme: const ColorScheme.dark(
      primary: Colors.blueAccent,
      secondary: Colors.cyanAccent,
      surface: Color(0xFF1E293B),
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: Color(0xFF0F172A),
      elevation: 0,
      centerTitle: true,
    ),
  );

  static Color getImpactColor(String direction) {
    switch (direction.toLowerCase()) {
      case 'up':
        return Colors.greenAccent;
      case 'down':
        return Colors.redAccent;
      default:
        return Colors.amberAccent;
    }
  }
}
