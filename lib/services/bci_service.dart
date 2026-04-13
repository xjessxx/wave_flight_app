import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;

class BCIStatus {
  final bool initialized;
  final bool calibrated;
  final bool trained;
  final bool detecting;
  final String mode;
  final double lastConfidence;

  BCIStatus({
    required this.initialized,
    required this.calibrated,
    required this.trained,
    required this.detecting,
    required this.mode,
    required this.lastConfidence,
  });

  factory BCIStatus.fromJson(Map<String, dynamic> json) {
    return BCIStatus(
      initialized: json['initialized'] == true,
      calibrated: json['calibrated'] == true,
      trained: json['trained'] == true,
      detecting: json['detecting'] == true,
      mode: (json['mode'] ?? 'unknown').toString(),
      lastConfidence: (json['last_confidence'] ?? 0).toDouble(),
    );
  }
}

class BCIService {
  static final BCIService instance = BCIService._internal();
  factory BCIService() => instance;
  BCIService._internal();

  String _baseUrl = const String.fromEnvironment(
    'BCI_BRIDGE_URL',
    defaultValue: 'http://localhost:5000',
  );

  Timer? _pollTimer;

  Function(bool trigger, double confidence)? onTriggerDetected;
  Function(int progress)? onCalibrationProgress;
  Function(int current, int total)? onTrainingProgress;

  String get baseUrl => _baseUrl;

  void updateBaseUrl(String url) {
    _baseUrl = url.trim();
  }

  Uri _uri(String path) => Uri.parse('$_baseUrl$path');

  Map<String, dynamic> _decode(http.Response response) {
    if (response.body.isEmpty) return {};
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<bool> bridgeAvailable() async {
    try {
      final response = await http.get(_uri('/status')).timeout(const Duration(seconds: 3));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<bool> initialize() async {
    try {
      final response = await http.post(_uri('/system/initialize')).timeout(
            const Duration(seconds: 10),
          );
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<void> shutdown() async {
    stopPolling();
    try {
      await http.post(_uri('/system/shutdown')).timeout(const Duration(seconds: 5));
    } catch (_) {}
  }

  Future<bool> startCalibration() async {
    try {
      final response = await http.post(_uri('/calibration/start')).timeout(
            const Duration(seconds: 10),
          );
      if (response.statusCode == 200) {
        _startCalibrationPolling();
        return true;
      }
      return false;
    } catch (_) {
      return false;
    }
  }

  Future<Map<String, dynamic>> getCalibrationStatus() async {
    final response = await http.get(_uri('/calibration/status')).timeout(
          const Duration(seconds: 5),
        );
    if (response.statusCode != 200) {
      throw Exception('Failed to get calibration status');
    }
    return _decode(response);
  }

  void _startCalibrationPolling() {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(milliseconds: 500), (timer) async {
      try {
        final response = await http.get(_uri('/calibration/progress'));
        if (response.statusCode != 200) return;

        final data = _decode(response);
        final progress = (data['progress'] ?? 0) as int;
        final status = (data['status'] ?? '').toString();

        onCalibrationProgress?.call(progress);

        if (status != 'calibrating') {
          timer.cancel();
          _pollTimer = null;
        }
      } catch (_) {
        timer.cancel();
        _pollTimer = null;
      }
    });
  }
//   // ========== CALIBRATION ==========

//   /// Start baseline calibration (60 seconds)
//   Future<bool> startCalibration() async {
//     try {
//       final response = await http.post(
//         Uri.parse('$baseUrl/calibration/start'),
//       );

//       if (response.statusCode == 200) {
//         print('Calibration started');
//         _startCalibrationPolling();
//         return true;
//       } else {
//         print('Failed to start calibration: ${response.body}');
//         return false;
//       }
//     } catch (e) {
//       print('Calibration error: $e');
//       return false;
//     }
//   }

//   // Poll calibration progress
//   void _startCalibrationPolling() {
//   _pollTimer?.cancel();

//   _pollTimer = Timer.periodic(
//     const Duration(milliseconds: 500),
//     (timer) async {
//       try {
//         final response = await http.get(
//           Uri.parse('$baseUrl/calibration/progress'),
//         );

//         if (response.statusCode != 200) return;

//         final data = json.decode(response.body);
//         final progress = data['progress'] as int;
//         final status = data['status'] as String;

//         onCalibrationProgress?.call(progress);

//         // STOP polling unless actively calibrating
//         if (status != 'calibrating') {
//           timer.cancel();
//           _pollTimer = null;
//         }
//       } catch (_) {
//         timer.cancel();
//         _pollTimer = null;
//       }
//     },
//   );
// }


//   Future<Map<String, dynamic>> getCalibrationStatus() async {
//     final response = await http.get(
//       Uri.parse('$baseUrl/calibration/status'),
//     );

//     if (response.statusCode != 200) {
//       throw Exception('Failed to get calibration status');
//     }

//     return jsonDecode(response.body);
//   }
  Future<bool> startTraining() async {
    try {
      final response = await http.post(_uri('/training/start')).timeout(
            const Duration(seconds: 10),
          );
      if (response.statusCode == 200) {
        _startTrainingPolling();
        return true;
      }
      return false;
    } catch (_) {
      return false;
    }
  }

  Future<bool> trainingTrialStart() async {
    try {
      final response = await http.post(_uri('/training/trial_start')).timeout(
            const Duration(seconds: 5),
          );
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  void _startTrainingPolling() {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(seconds: 1), (timer) async {
      try {
        final response = await http.get(_uri('/training/progress'));
        if (response.statusCode != 200) return;

        final data = _decode(response);
        final current = (data['current_trial'] ?? 0) as int;
        final total = (data['total_trials'] ?? 0) as int;

        onTrainingProgress?.call(current, total);

        if (current >= total && total > 0) {
          timer.cancel();
          _pollTimer = null;
        }
      } catch (_) {
        timer.cancel();
        _pollTimer = null;
      }
    });
  }

  Future<bool> startDetection() async {
    try {
      final response = await http.post(_uri('/detection/start')).timeout(
            const Duration(seconds: 10),
          );
      if (response.statusCode == 200) {
        _startDetectionPolling();
        return true;
      }
      return false;
    } catch (_) {
      return false;
    }
  }

  Future<void> stopDetection() async {
    stopPolling();
    try {
      await http.post(_uri('/detection/stop')).timeout(const Duration(seconds: 5));
    } catch (_) {}
  }

  void _startDetectionPolling() {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(milliseconds: 200), (timer) async {
      try {
        final response = await http.get(_uri('/detection/poll'));
        if (response.statusCode != 200) return;

        final data = _decode(response);
        final trigger = data['trigger'] == true;
        final confidence = (data['confidence'] ?? 0).toDouble();

        if (trigger) {
          onTriggerDetected?.call(true, confidence);
        }
      } catch (_) {
        // keep polling quietly
      }
    });
  }

  void stopPolling() {
    _pollTimer?.cancel();
    _pollTimer = null;
  }

  Future<BCIStatus?> getStatus() async {
    try {
      final response = await http.get(_uri('/status')).timeout(
            const Duration(seconds: 5),
          );
      if (response.statusCode == 200) {
        return BCIStatus.fromJson(_decode(response));
      }
    } catch (_) {}
    return null;
  }
}
