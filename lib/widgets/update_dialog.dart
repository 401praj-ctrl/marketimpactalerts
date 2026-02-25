import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import 'package:path_provider/path_provider.dart';
import 'package:open_file/open_file.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:market_impact_alerts/theme/app_theme.dart';
import 'dart:io';

class UpdateProgressDialog extends StatefulWidget {
  final String url;
  final String version;

  const UpdateProgressDialog({super.key, required this.url, required this.version});

  @override
  State<UpdateProgressDialog> createState() => _UpdateProgressDialogState();
}

class _UpdateProgressDialogState extends State<UpdateProgressDialog> {
  String _status = 'Initializing...';
  double _progress = 0;
  String _mbDownloaded = '0';
  String _totalMb = '...';
  bool _isDone = false;
  bool _isError = false;
  final CancelToken _cancelToken = CancelToken();

  @override
  void initState() {
    super.initState();
    _executeUpgrade();
  }

  @override
  void dispose() {
    _cancelToken.cancel();
    super.dispose();
  }

  Future<void> _executeUpgrade() async {
    try {
      final Directory docsDir = await getApplicationDocumentsDirectory();
      final String savePath = "${docsDir.path}/market_impact_${widget.version}.apk";

      final dio = Dio();
      await dio.download(
        widget.url,
        savePath,
        cancelToken: _cancelToken,
        onReceiveProgress: (received, total) {
          if (total != -1) {
            if (mounted) {
              setState(() {
                _status = 'Downloading update...';
                _progress = (received / total * 100);
                _totalMb = (total / (1024 * 1024)).toStringAsFixed(1);
                _mbDownloaded = (received / (1024 * 1024)).toStringAsFixed(1);
              });
            }
          }
        },
      );

      if (mounted) {
        setState(() {
          _status = 'Download complete! Checking permissions...';
        });
      }

      if (Platform.isAndroid) {
        var status = await Permission.requestInstallPackages.status;
        if (status.isDenied || status.isPermanentlyDenied) {
          status = await Permission.requestInstallPackages.request();
        }

        if (!status.isGranted) {
          if (mounted) {
            setState(() {
              _status = "Install permission required. Please enable it in settings to proceed.";
              _isError = true;
            });
          }
          return;
        }
      }

      final result = await OpenFile.open(savePath);
      print('UpdateDialog: OpenFile Result: ${result.type} - ${result.message}');
      
      if (result.type != ResultType.done) {
        if (mounted) {
          setState(() {
            _status = "Error opening APK: ${result.message}. Try manually installing from Downloads.";
            _isError = true;
          });
        }
      } else {
        if (mounted) {
          setState(() {
            _isDone = true;
            _status = "Update started. If nothing happens, open the APK manually from Downloads.";
          });
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _status = "Download error: $e";
          _isError = true;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: AppTheme.cardDark,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      title: Row(
        children: [
          Icon(
            _isError ? Icons.error_outline : (_isDone ? Icons.check_circle_outline : Icons.system_update_alt),
            color: _isError ? Colors.red : AppTheme.glassBlue,
          ),
          const SizedBox(width: 12),
          const Text('App Update', style: TextStyle(color: Colors.white)),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(_status, style: const TextStyle(color: Colors.white70, fontSize: 13)),
          const SizedBox(height: 20),
          if (!_isError && !_isDone) ...[
            ClipRRect(
              borderRadius: BorderRadius.circular(10),
              child: LinearProgressIndicator(
                value: _progress / 100,
                backgroundColor: Colors.white10,
                valueColor: const AlwaysStoppedAnimation<Color>(AppTheme.glassBlue),
                minHeight: 8,
              ),
            ),
            const SizedBox(height: 10),
            Text(
              "$_mbDownloaded MB / $_totalMb MB (${_progress.toStringAsFixed(0)}%)",
              style: const TextStyle(color: Colors.white30, fontSize: 11),
            ),
          ],
          if (_isError)
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: ElevatedButton(
                onPressed: () {
                  setState(() {
                    _isError = false;
                    _isDone = false;
                  });
                  _executeUpgrade();
                },
                style: ElevatedButton.styleFrom(backgroundColor: Colors.red.withOpacity(0.2)),
                child: const Text('RETRY DOWNLOAD', style: TextStyle(color: Colors.red)),
              ),
            ),
          if (_isDone)
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('CLOSE', style: TextStyle(color: AppTheme.glassBlue)),
              ),
            )
        ],
      ),
    );
  }
}
