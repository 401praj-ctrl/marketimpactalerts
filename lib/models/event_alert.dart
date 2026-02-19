class EventAlert {
  final String id;
  final String event;
  final String company;
  final String sector;
  final List<String> stocks;
  final String impactDirection;
  final String impactDescription;
  final String eventDate;
  final String impactDateEst;
  final int probability;
  final String reason;
  final String timestamp;
  final String? articleSummary;

  EventAlert({
    required this.id,
    required this.event,
    required this.company,
    required this.sector,
    required this.stocks,
    required this.impactDirection,
    required this.impactDescription,
    required this.eventDate,
    required this.impactDateEst,
    required this.probability,
    required this.reason,
    required this.timestamp,
    this.articleSummary,
  });

  factory EventAlert.fromJson(Map<String, dynamic> json) {
    return EventAlert(
      id: json['id'] ?? '',
      event: json['event'] ?? '',
      company: json['company'] ?? '',
      sector: json['sector'] ?? '',
      stocks: List<String>.from(json['stocks'] ?? []),
      impactDirection: json['impact_direction'] ?? 'NEUTRAL',
      impactDescription: json['impact_description'] ?? '',
      eventDate: json['event_date'] ?? '',
      impactDateEst: json['impact_date_est'] ?? '',
      probability: json['probability'] ?? 0,
      reason: json['reason'] ?? '',
      timestamp: json['timestamp'] ?? DateTime.now().toIso8601String(),
      articleSummary: json['article_summary'],
    );
  }
}
