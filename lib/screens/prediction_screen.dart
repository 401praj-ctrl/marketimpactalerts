import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class PredictionScreen extends StatefulWidget {
  const PredictionScreen({super.key});

  @override
  State<PredictionScreen> createState() => _PredictionScreenState();
}

class _PredictionScreenState extends State<PredictionScreen> {
  final ApiService _apiService = ApiService();
  Map<String, dynamic>? _stats;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _fetchStats();
  }

  Future<void> _fetchStats() async {
    try {
      final stats = await _apiService.getPredictionStats();
      setState(() {
        _stats = stats;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Alpha Accuracy Dashboard'),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _stats == null
              ? const Center(child: Text('No performance data available yet.'))
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildSummaryGrid(),
                      const SizedBox(height: 30),
                      _buildTierAccuracySection(),
                      const SizedBox(height: 30),
                      _buildPerformanceNote(),
                    ],
                  ),
                ),
    );
  }

  Widget _buildSummaryGrid() {
    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 15,
      crossAxisSpacing: 15,
      childAspectRatio: 1.5,
      children: [
        _buildStatCard('Total Predictions', (_stats?['total_predictions'] ?? 0).toString(), Icons.analytics_rounded),
        _buildStatCard('Accuracy %', '${_stats?['avg_accuracy'] ?? 0.0}%', Icons.check_circle_rounded),
        _buildStatCard('Correct Moves', (_stats?['correct_predictions'] ?? 0).toString(), Icons.trending_up_rounded),
        _buildStatCard('Wrong Moves', (_stats?['false_signals'] ?? 0).toString(), Icons.trending_down_rounded, color: Colors.redAccent),
        _buildStatCard('Profit Sim', '${_stats?['profit_simulation_pct'] ?? 0.0}%', Icons.account_balance_wallet_rounded),
      ],
    );
  }

  Widget _buildStatCard(String label, String value, IconData icon, {Color color = AppTheme.glassBlue}) {
    return Container(
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      padding: const EdgeInsets.all(15),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, color: color, size: 24),
          const SizedBox(height: 8),
          Text(value, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white)),
          Text(label, style: TextStyle(fontSize: 12, color: AppTheme.silver.withOpacity(0.7))),
        ],
      ),
    );
  }

  Widget _buildTierAccuracySection() {
    final tierAcc = (_stats!['tier_accuracy'] as Map?) ?? {};
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Accuracy by Impact Tier', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
        const SizedBox(height: 15),
        _buildTierBar('Tier-1 (Direct)', tierAcc['Tier-1'] ?? 0, Colors.greenAccent),
        _buildTierBar('Tier-2 (Sector)', tierAcc['Tier-2'] ?? 0, Colors.orangeAccent),
        _buildTierBar('Tier-3 (Macro)', tierAcc['Tier-3'] ?? 0, Colors.blueAccent),
      ],
    );
  }

  Widget _buildTierBar(String label, int value, Color color) {
    // Value represents the accuracy percentage from 0 to 100
    double progressValue = (value / 100.0).clamp(0.0, 1.0);
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(label, style: const TextStyle(color: Colors.white, fontSize: 14)),
              Text('$value% accuracy', style: TextStyle(color: AppTheme.silver, fontSize: 12)),
            ],
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(10),
            child: LinearProgressIndicator(
              value: progressValue,
              backgroundColor: color.withOpacity(0.1),
              valueColor: AlwaysStoppedAnimation<Color>(color),
              minHeight: 8,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPerformanceNote() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(15),
      ),
      child: Row(
        children: [
          const Icon(Icons.info_outline, color: Colors.blueAccent, size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              'Predictions are verified against next-day market moves. Tier-3 news is capped at 35% probability to reduce noise.',
              style: TextStyle(color: AppTheme.silver, fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }
}
