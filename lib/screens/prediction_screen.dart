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

  Future<void> _triggerManualAnalysis() async {
    setState(() => _isLoading = true);
    await _apiService.triggerManualVerification();
    // Wait a bit for the backend to process
    await Future.delayed(const Duration(seconds: 3));
    await _fetchStats();
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Manual analysis triggered. Results updated.')),
      );
    }
  }

  String _formatDateTime(String? isoString) {
    if (isoString == null || isoString.isEmpty) return 'Never';
    try {
      final dt = DateTime.parse(isoString).toLocal();
      return '${dt.day}/${dt.month} ${dt.hour}:${dt.minute.toString().padLeft(2, '0')}';
    } catch (e) {
      return 'Unknown';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Alpha Accuracy Dashboard'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              setState(() => _isLoading = true);
              _fetchStats();
            },
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _stats == null
              ? const Center(child: Text('No performance data available yet.'))
              : RefreshIndicator(
                  onRefresh: _fetchStats,
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(20),
                    physics: const AlwaysScrollableScrollPhysics(),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildManualAnalysisButton(),
                        const SizedBox(height: 10),
                        _buildAnalysisStatusInfo(),
                        const SizedBox(height: 25),
                        _buildSummaryGrid(),
                        const SizedBox(height: 30),
                        _buildTierAccuracySection(),
                        const SizedBox(height: 30),
                        _buildPerformanceNote(),
                      ],
                    ),
                  ),
                ),
    );
  }

  Widget _buildManualAnalysisButton() {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton.icon(
        onPressed: _triggerManualAnalysis,
        icon: const Icon(Icons.bolt_rounded),
        label: const Text('START MANUAL ANALYSIS'),
        style: ElevatedButton.styleFrom(
          backgroundColor: AppTheme.glassBlue,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(vertical: 15),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
          elevation: 5,
        ),
      ),
    );
  }

  Widget _buildAnalysisStatusInfo() {
    final lastAuto = _stats?['last_auto_verification'];
    final lastManual = _stats?['last_manual_verification'];
    
    DateTime? nextAuto;
    if (lastAuto != null) {
      final now = DateTime.now();
      nextAuto = DateTime(now.year, now.month, now.day + 1, 0, 0);
    }

    bool recentlyDone = false;
    if (lastAuto != null) {
      final lastAutoDate = DateTime.parse(lastAuto);
      recentlyDone = DateTime.now().difference(lastAutoDate).inMinutes < 60;
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withOpacity(0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (recentlyDone) ...[
            const Row(
              children: [
                Icon(Icons.verified_rounded, color: Colors.greenAccent, size: 16),
                SizedBox(width: 8),
                Text('AUTO ANALYSIS IS DONE', 
                  style: TextStyle(color: Colors.greenAccent, fontWeight: FontWeight.bold, fontSize: 13)),
              ],
            ),
            const SizedBox(height: 6),
          ],
          Text('Last Auto Analysis: ${_formatDateTime(lastAuto)}', 
            style: TextStyle(color: AppTheme.silver, fontSize: 12)),
          if (nextAuto != null)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text('Next Scheduled Auto Analysis: ${_formatDateTime(nextAuto.toIso8601String())}', 
                style: const TextStyle(color: Colors.orangeAccent, fontSize: 12, fontWeight: FontWeight.w500)),
            ),
          if (lastManual != null)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text('Last Manual Analysis: ${_formatDateTime(lastManual)}', 
                style: TextStyle(color: AppTheme.silver, fontSize: 12)),
            ),
        ],
      ),
    );
  }

  Widget _buildSummaryGrid() {
    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 12,
      crossAxisSpacing: 12,
      childAspectRatio: 1.6, // Adjusted for slightly taller cards
      children: [
        _buildStatCard(
            'Total Predictions',
            (_stats?['total_predictions'] ?? 0).toString(),
            Icons.analytics_rounded,
            onTap: () => _showPredictionsList('all', 'Total Predictions')),
        _buildStatCard(
            'Accuracy %',
            '${_stats?['avg_accuracy'] ?? 0.0}%',
            Icons.check_circle_rounded,
            onTap: () => _showPredictionsList('all', 'Total Predictions')), // Also maps to all for now
        _buildStatCard(
            'Correct Moves',
            (_stats?['correct_predictions'] ?? 0).toString(),
            Icons.trending_up_rounded,
            onTap: () => _showPredictionsList('correct', 'Correct Moves')),
        _buildStatCard(
            'Wrong Moves',
            (_stats?['false_signals'] ?? 0).toString(),
            Icons.trending_down_rounded,
            color: Colors.redAccent,
            onTap: () => _showPredictionsList('wrong', 'Wrong Moves')),
      ],
    );
  }

  Widget _buildStatCard(String label, String value, IconData icon, {Color color = AppTheme.glassBlue, VoidCallback? onTap}) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: Container(
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
              'Predictions are verified against next-day market moves. Tap on the cards above to see the specific alerts.',
              style: TextStyle(color: AppTheme.silver, fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }

  void _showPredictionsList(String status, String title) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return DraggableScrollableSheet(
          initialChildSize: 0.8,
          minChildSize: 0.5,
          maxChildSize: 0.95,
          builder: (_, controller) {
            return Container(
              decoration: BoxDecoration(
                color: AppTheme.spaceDark,
                borderRadius: const BorderRadius.vertical(top: Radius.circular(25)),
              ),
              child: FutureBuilder<List<dynamic>>(
                future: _apiService.fetchPredictionHistory(status: status),
                builder: (context, snapshot) {
                  return Column(
                    children: [
                      Container(
                        margin: const EdgeInsets.symmetric(vertical: 12),
                        height: 5,
                        width: 50,
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.3),
                          borderRadius: BorderRadius.circular(10),
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                        child: Text(
                          title,
                          style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
                        ),
                      ),
                      Expanded(
                        child: _buildListContent(snapshot, controller),
                      ),
                    ],
                  );
                },
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildListContent(AsyncSnapshot<List<dynamic>> snapshot, ScrollController controller) {
    if (snapshot.connectionState == ConnectionState.waiting) {
      return const Center(child: CircularProgressIndicator());
    }
    if (snapshot.hasError) {
      return Center(child: Text('Error loading data', style: TextStyle(color: Colors.redAccent)));
    }
    
    final items = snapshot.data ?? [];
    if (items.isEmpty) {
      return const Center(
        child: Text('No predictions found for this category.', style: TextStyle(color: Colors.white54)),
      );
    }

    return ListView.builder(
      controller: controller,
      itemCount: items.length,
      padding: const EdgeInsets.all(15),
      itemBuilder: (context, index) {
        final pred = items[index];
        final isVerified = pred['verified'] == true;
        final isCorrect = pred['is_correct'] == true;
        final actualMove = pred['actual_move'];
        
        String moveText = '';
        if (isVerified && actualMove != null) {
          final movePct = (actualMove * 100).toStringAsFixed(2);
          moveText = actualMove > 0 ? '+$movePct%' : '$movePct%';
        } else {
          moveText = 'Pending';
        }

        return Card(
          color: Colors.white.withOpacity(0.05),
          margin: const EdgeInsets.only(bottom: 12),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          child: ListTile(
            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            title: Text(
              pred['event'] ?? 'Unknown Event',
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 14),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            subtitle: Padding(
              padding: const EdgeInsets.only(top: 8.0),
              child: Row(
                children: [
                  Icon(
                    pred['direction'] == 'UP' ? Icons.arrow_upward : (pred['direction'] == 'DOWN' ? Icons.arrow_downward : Icons.remove),
                    size: 14,
                    color: pred['direction'] == 'UP' ? Colors.greenAccent : (pred['direction'] == 'DOWN' ? Colors.redAccent : Colors.orangeAccent),
                  ),
                  const SizedBox(width: 4),
                  Text(
                    pred['stocks']?.isNotEmpty == true ? pred['stocks'][0] : (pred['company'] ?? 'Market'),
                    style: TextStyle(color: AppTheme.silver, fontSize: 12),
                  ),
                  const Spacer(),
                  Text(
                    moveText,
                    style: TextStyle(
                      color: isVerified ? (isCorrect ? Colors.greenAccent : Colors.redAccent) : Colors.orangeAccent,
                      fontWeight: FontWeight.bold,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}
