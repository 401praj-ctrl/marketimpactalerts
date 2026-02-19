import 'package:flutter/material.dart';
import '../models/event_alert.dart';
import '../theme/app_theme.dart';

class AlertDetailsScreen extends StatelessWidget {
  final EventAlert alert;

  const AlertDetailsScreen({super.key, required this.alert});

  @override
  Widget build(BuildContext context) {
    final impactColor = AppTheme.getImpactColor(alert.impactDirection);

    return Scaffold(
      backgroundColor: AppTheme.spaceDark,
      appBar: AppBar(
        title: Text('IMPACT ANALYSIS', style: GoogleFonts.outfit(fontWeight: FontWeight.bold, letterSpacing: 1)),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: impactColor.withOpacity(0.05),
                borderRadius: BorderRadius.circular(24),
                border: Border.all(color: impactColor.withOpacity(0.2)),
                boxShadow: [
                  BoxShadow(
                    color: impactColor.withOpacity(0.05),
                    blurRadius: 20,
                    spreadRadius: 2,
                  )
                ],
              ),
              child: Column(
                children: [
                  Text(
                    alert.impactDirection.toUpperCase(),
                    style: GoogleFonts.outfit(
                      color: impactColor,
                      fontSize: 36,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 2,
                    ),
                  ),
                  const SizedBox(height: 16),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.05),
                      borderRadius: BorderRadius.circular(30),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.bolt_rounded, color: Colors.amber, size: 20),
                        const SizedBox(width: 8),
                        Text(
                          '${alert.probability}% PROBABILITY',
                          style: GoogleFonts.inter(
                            color: Colors.white,
                            fontSize: 14,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 1,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 32),
            Row(
              children: [
                Expanded(child: _buildInfoRow(Icons.calendar_today_rounded, "EVENT DATE", alert.eventDate)),
                const SizedBox(width: 16),
                Expanded(child: _buildInfoRow(Icons.speed_rounded, "EST. IMPACT", alert.impactDateEst)),
              ],
            ),
            const SizedBox(height: 40),
            _buildSectionHeader('THE EVENT'),
            const SizedBox(height: 12),
            Text(
              alert.event,
              style: GoogleFonts.outfit(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white),
            ),
            const SizedBox(height: 32),
            _buildSectionHeader('MARKET IMPACT ANALYSIS'),
            const SizedBox(height: 12),
            Text(
              alert.impactDescription,
              style: GoogleFonts.inter(fontSize: 16, height: 1.7, color: Colors.white.withOpacity(0.9)),
            ),
            const SizedBox(height: 32),
            _buildSectionHeader('AI REASONING'),
            const SizedBox(height: 12),
            Text(
              alert.reason,
              style: GoogleFonts.inter(fontSize: 15, height: 1.6, color: AppTheme.silver),
            ),
            const SizedBox(height: 40),
            _buildSectionHeader('TARGET STOCKS'),
            const SizedBox(height: 16),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: alert.stocks.map((stock) => Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                decoration: BoxDecoration(
                  color: AppTheme.glassBlue.withOpacity(0.05),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppTheme.glassBlue.withOpacity(0.2)),
                ),
                child: Text(
                  stock,
                  style: GoogleFonts.inter(fontWeight: FontWeight.bold, color: AppTheme.glassBlue, letterSpacing: 0.5),
                ),
              )).toList(),
            ),
            const SizedBox(height: 60),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Text(
      title,
      style: GoogleFonts.inter(
        color: AppTheme.glassBlue,
        fontSize: 12,
        fontWeight: FontWeight.bold,
        letterSpacing: 2,
      ),
    );
  }

  Widget _buildInfoRow(IconData icon, String label, String value) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.03),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.white05),
      ),
      child: Row(
        children: [
          Icon(icon, size: 20, color: AppTheme.silver),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: GoogleFonts.inter(color: AppTheme.silver.withOpacity(0.5), fontSize: 10, letterSpacing: 1)),
              const SizedBox(height: 4),
              Text(
                value.isEmpty ? "TBD" : value,
                style: GoogleFonts.outfit(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
