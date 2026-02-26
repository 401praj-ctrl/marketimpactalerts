import 'package:flutter/material.dart';
import '../models/event_alert.dart';
import '../theme/app_theme.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AlertDetailsScreen extends StatefulWidget {
  final EventAlert alert;
  const AlertDetailsScreen({super.key, required this.alert});

  @override
  State<AlertDetailsScreen> createState() => _AlertDetailsScreenState();
}

class _AlertDetailsScreenState extends State<AlertDetailsScreen> {
  String? _userVerification; // 'correct', 'incorrect', or null

  @override
  void initState() {
    super.initState();
    _loadVerification();
  }

  Future<void> _loadVerification() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _userVerification = prefs.getString('verify_${widget.alert.id}');
    });
  }

  Future<void> _saveVerification(String status) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('verify_${widget.alert.id}', status);
    setState(() {
      _userVerification = status;
    });
  }

  @override
  Widget build(BuildContext context) {
    final alert = widget.alert;
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
            if (alert.isVerified) ...[
              const SizedBox(height: 32),
              _buildVerificationStatus(),
            ],
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
            _buildAIInsightButton(),
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
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                decoration: BoxDecoration(
                  color: AppTheme.glassBlue.withOpacity(0.05),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: AppTheme.glassBlue.withOpacity(0.2)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      stock,
                      style: GoogleFonts.inter(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.glassBlue, letterSpacing: 0.5),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('LIVE PRICE', style: GoogleFonts.inter(color: AppTheme.silver, fontSize: 10, letterSpacing: 1)),
                            const SizedBox(height: 4),
                            Text(
                              _formatPrice(alert.livePrice, alert.currency, alert.stocks), 
                              style: GoogleFonts.outfit(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)
                            ),
                          ],
                        ),
                        const SizedBox(width: 32),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('IMPACT PRICE', style: GoogleFonts.inter(color: AppTheme.silver, fontSize: 10, letterSpacing: 1)),
                            const SizedBox(height: 4),
                            Row(
                              children: [
                                 Text(
                                  _formatPrice(alert.predictedPrice, alert.currency, alert.stocks), 
                                  style: GoogleFonts.outfit(
                                    color: alert.impactDirection.toLowerCase() == 'up' ? AppTheme.getImpactColor('up') : 
                                           alert.impactDirection.toLowerCase() == 'down' ? AppTheme.getImpactColor('down') : 
                                           Colors.white, 
                                    fontSize: 18, 
                                    fontWeight: FontWeight.bold
                                  )
                                ),
                                if (alert.upsidePct != null) ...[
                                  const SizedBox(width: 8),
                                  Text('(${_cleanUpsidePct(alert.upsidePct!)})', 
                                    style: TextStyle(
                                      color: alert.impactDirection.toLowerCase() == 'up' ? AppTheme.getImpactColor('up') : 
                                             alert.impactDirection.toLowerCase() == 'down' ? AppTheme.getImpactColor('down') : 
                                             Colors.white,
                                      fontSize: 12,
                                      fontWeight: FontWeight.bold
                                    )
                                  ),
                                ],
                              ],
                            ),
                          ],
                        ),
                      ],
                    ),
                  ],
                ),
              )).toList(),
            ),
            const SizedBox(height: 48),
            _buildImpactSection(),
            const SizedBox(height: 60),
          ],
        ),
      ),
    );
  }

  Widget _buildVerificationStatus() {
    final alert = widget.alert;
    final bool isCorrect = alert.isCorrect == true;
    final Color statusColor = isCorrect ? Colors.greenAccent : Colors.redAccent;
    final Color bgColor = isCorrect ? Colors.green.withOpacity(0.1) : Colors.red.withOpacity(0.1);
    final String title = isCorrect ? 'TARGET ACHIEVED' : 'TARGET MISSED';
    final String impactPriceStr = _formatPrice(alert.predictedPrice, alert.currency, alert.stocks);
    final String subtitle = isCorrect 
        ? 'Impact price of $impactPriceStr was correctly achieved on the impact date (${alert.impactDateEst}).' 
        : 'Impact price of $impactPriceStr was not achieved on the impact date (${alert.impactDateEst}).';

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: statusColor.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(isCorrect ? Icons.check_circle_outline : Icons.cancel_outlined, color: statusColor, size: 28),
              const SizedBox(width: 12),
              Text(
                title,
                style: GoogleFonts.outfit(color: statusColor, fontSize: 18, fontWeight: FontWeight.bold, letterSpacing: 1),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            subtitle,
            style: GoogleFonts.inter(color: Colors.white.withOpacity(0.9), fontSize: 14),
          ),
          if (alert.actualMove != null) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.black26,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                'Actual Move Verified on Date: ${(alert.actualMove! * 100).toStringAsFixed(2)}%',
                style: GoogleFonts.inter(color: AppTheme.silver, fontSize: 12, fontWeight: FontWeight.bold),
              ),
            ),
          ]
        ],
      ),
    );
  }

  Widget _buildAIInsightButton() {
    return InkWell(
      onTap: () => _showAIInsightModal(),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: AppTheme.glassBlue.withOpacity(0.1),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: AppTheme.glassBlue.withOpacity(0.3)),
        ),
        child: Row(
          children: [
            const Icon(Icons.auto_awesome_rounded, color: AppTheme.glassBlue, size: 28),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'AI INSIGHTS',
                    style: GoogleFonts.inter(color: AppTheme.glassBlue, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 1.5),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Get executive summary',
                    style: GoogleFonts.outfit(color: Colors.white.withOpacity(1), fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
            ),
            const Icon(Icons.arrow_forward_ios_rounded, color: AppTheme.glassBlue, size: 16),
          ],
        ),
      ),
    );
  }

  void _showAIInsightModal() {
    showModalBottomSheet(
      context: context,
      backgroundColor: AppTheme.spaceDark,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(30))),
      isScrollControlled: true,
      builder: (context) => Container(
        padding: const EdgeInsets.fromLTRB(24, 40, 24, 40),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [AppTheme.glassBlue.withOpacity(0.1), AppTheme.spaceDark],
          ),
          borderRadius: const BorderRadius.vertical(top: Radius.circular(30)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.auto_awesome_rounded, color: AppTheme.glassBlue, size: 24),
                const SizedBox(width: 12),
                Text(
                  'EXECUTIVE SUMMARY',
                  style: GoogleFonts.outfit(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
                ),
              ],
            ),
            const SizedBox(height: 24),
            Text(
              widget.alert.articleSummary ?? widget.alert.reason,
              style: GoogleFonts.inter(fontSize: 16, height: 1.6, color: Colors.white.withOpacity(0.8)),
            ),
            const SizedBox(height: 40),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () => Navigator.pop(context),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.glassBlue,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                ),
                child: const Text('CLOSE INSIGHT', style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildImpactSection() {
    final alert = widget.alert;
    final isDirect = alert.impactType.toLowerCase() == 'direct';
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildSectionHeader('IMPACT CLASSIFICATION'),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: (isDirect ? Colors.orangeAccent : Colors.blueAccent).withOpacity(0.05),
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: (isDirect ? Colors.orangeAccent : Colors.blueAccent).withOpacity(0.2)),
          ),
          child: Row(
            children: [
              Icon(
                isDirect ? Icons.gps_fixed_rounded : Icons.bubble_chart_rounded,
                color: isDirect ? Colors.orangeAccent : Colors.blueAccent,
                size: 32,
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${alert.impactType.toUpperCase()} IMPACT',
                      style: GoogleFonts.outfit(
                        color: isDirect ? Colors.orangeAccent : Colors.blueAccent,
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 0.5,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      isDirect 
                        ? 'Directly affects company earnings and fundamentals.' 
                        : 'Broad market/sector sentiment shifting stock valuation.',
                      style: GoogleFonts.inter(color: AppTheme.silver.withOpacity(0.8), fontSize: 13),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
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
          Expanded(
            child: Column(
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
          ),
        ],
      ),
    );
  }

  String _formatPrice(double? price, String? currency, [List<String>? stocks]) {
    if (price == null) return '---';
    String finalCurrency = currency ?? 'INR';
    
    if (stocks != null && stocks.isNotEmpty) {
      final s = stocks[0].toUpperCase();
      final isIndian = s.contains('.NS') || s.contains('.BO') || s.contains('NSE:') || s.contains('BSE:');
      if (!isIndian) finalCurrency = 'USD';
    }
    
    final symbol = finalCurrency == "USD" ? "\$" : "₹";
    return "$symbol${price.toStringAsFixed(2)}";
  }

  String _cleanUpsidePct(String raw) {
    if (raw.startsWith('{') && raw.endsWith('}')) {
      // Basic extraction of the first value if it's a map string
      try {
        final parts = raw.split(':');
        if (parts.length > 1) {
          String val = parts.last.replaceAll('}', '').replaceAll('"', '').trim();
          if (!val.endsWith('%')) val += '%';
          return val;
        }
      } catch (e) {
        return raw;
      }
    }
    if (!raw.endsWith('%') && double.tryParse(raw.replaceAll('+', '').replaceAll('-', '')) != null) {
        return '$raw%';
    }
    return raw;
  }
}
