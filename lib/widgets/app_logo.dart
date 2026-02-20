import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'dart:math' as math;
import '../theme/app_theme.dart';

class AppLogo extends StatelessWidget {
  final double size;
  final bool showText;
  final bool isLarge;

  const AppLogo({
    super.key,
    this.size = 32,
    this.showText = true,
    this.isLarge = false,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Stack(
          alignment: Alignment.center,
          children: [
            // Outer Glow
            Container(
              height: size * 1.2,
              width: size * 1.2,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: AppTheme.glassBlue.withOpacity(0.2),
                    blurRadius: size / 2,
                    spreadRadius: 2,
                  )
                ],
              ),
            ),
            // Hexagon Container
            Transform.rotate(
              angle: math.pi / 2,
              child: CustomPaint(
                size: Size(size, size),
                painter: HexagonPainter(
                  gradient: const LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [AppTheme.glassBlue, Color(0xFF1E40AF)],
                  ),
                ),
              ),
            ),
            // Minimalist Bolt
            Icon(
              Icons.bolt_rounded,
              color: Colors.white,
              size: size * 0.6,
            ),
          ],
        ),
        if (showText) ...[
          SizedBox(width: isLarge ? 20 : 12),
          RichText(
            text: TextSpan(
              style: GoogleFonts.outfit(
                fontSize: isLarge ? 28 : 20,
                fontWeight: FontWeight.bold,
                letterSpacing: 1.5,
                color: Colors.white,
              ),
              children: const [
                TextSpan(text: 'ALPHA'),
                TextSpan(
                  text: ' IMPACT',
                  style: TextStyle(color: AppTheme.glassBlue),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

class HexagonPainter extends CustomPainter {
  final Gradient gradient;

  HexagonPainter({required this.gradient});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..shader = gradient.createShader(Rect.fromLTWH(0, 0, size.width, size.height))
      ..style = PaintingStyle.fill;

    final path = Path();
    final centerX = size.width / 2;
    final centerY = size.height / 2;
    final radius = size.width / 2;

    for (int i = 0; i < 6; i++) {
      double angle = (math.pi / 3.0) * i;
      double x = centerX + radius * math.cos(angle);
      double y = centerY + radius * math.sin(angle);
      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }
    path.close();
    canvas.drawPath(path, paint);
    
    // Inner border
    final borderPaint = Paint()
      ..color = Colors.white.withOpacity(0.2)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;
    canvas.drawPath(path, borderPaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
