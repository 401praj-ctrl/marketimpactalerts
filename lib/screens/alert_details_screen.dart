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
      appBar: AppBar(title: const Text('Impact Analysis')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: impactColor.withOpacity(0.1),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: impactColor.withOpacity(0.3)),
              ),
              child: Column(
                children: [
                  Text(
                    alert.impactDirection.toUpperCase(),
                    style: TextStyle(color: impactColor, fontSize: 32, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.bolt, color: Colors.amber, size: 20),
                      const SizedBox(width: 8),
                      Text(
                        '${alert.probability}% Probability',
                        style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            _buildInfoRow(Icons.event, "Event Date", alert.eventDate),
            const SizedBox(height: 12),
            _buildInfoRow(Icons.trending_up, "Estimated Impact", alert.impactDateEst),
            const SizedBox(height: 32),
            const Text('The Event', style: TextStyle(color: Colors.grey, fontSize: 14, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text(alert.event, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
            const SizedBox(height: 24),
            const Text('Market Impact Analysis', style: TextStyle(color: Colors.grey, fontSize: 14, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text(alert.impactDescription, style: const TextStyle(fontSize: 16, height: 1.6, color: Colors.white)),
            const SizedBox(height: 24),
            const Text('AI Reasoning', style: TextStyle(color: Colors.grey, fontSize: 14, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text(alert.reason, style: const TextStyle(fontSize: 15, height: 1.5, color: Colors.white70)),
            const SizedBox(height: 32),
            const Text('Target Stocks', style: TextStyle(color: Colors.grey, fontSize: 14, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: alert.stocks.map((stock) => Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                  color: Colors.blueAccent.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.blueAccent.withOpacity(0.3)),
                ),
                child: Text(stock, style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.blueAccent)),
              )).toList(),
            ),
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(IconData icon, String label, String value) {
    return Row(
      children: [
        Icon(icon, size: 20, color: Colors.grey),
        const SizedBox(width: 12),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(color: Colors.grey, fontSize: 12)),
            Text(value.isEmpty ? "TBD" : value, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          ],
        ),
      ],
    );
  }
}
