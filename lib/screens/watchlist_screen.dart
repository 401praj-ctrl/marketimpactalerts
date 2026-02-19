import 'package:flutter/material.dart';

class WatchlistScreen extends StatefulWidget {
  const WatchlistScreen({super.key});

  @override
  State<WatchlistScreen> createState() => _WatchlistScreenState();
}

class _WatchlistScreenState extends State<WatchlistScreen> {
  final List<String> _watchlist = ['HDFC Bank', 'Reliance', 'Nvidia', 'TCS'];
  final TextEditingController _controller = TextEditingController();

  void _addStock() {
    if (_controller.text.isNotEmpty) {
      setState(() {
        _watchlist.add(_controller.text);
        _controller.clear();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My Watchlist')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _controller,
                    decoration: const InputDecoration(
                      hintText: 'Add stock symbol (e.g. AAPL)',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                ElevatedButton(
                  onPressed: _addStock,
                  child: const Icon(Icons.add),
                ),
              ],
            ),
          ),
          Expanded(
            child: ListView.builder(
              itemCount: _watchlist.length,
              itemBuilder: (context, index) {
                return ListTile(
                  leading: const Icon(Icons.show_chart, color: Colors.blueAccent),
                  title: Text(_watchlist[index], style: const TextStyle(fontWeight: FontWeight.bold)),
                  trailing: IconButton(
                    icon: const Icon(Icons.delete_outline, color: Colors.grey),
                    onPressed: () => setState(() => _watchlist.removeAt(index)),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
