import 'dart:convert';
import 'dart:async';
import 'package:http/http.dart' as http;

/// Service to communicate with Python BCI server
///
/// Usage:
/// 1. Start Python server: python bci_flutter_bridge.py
/// 2. Initialize: await BCIService.instance.initialize()
/// 3. Use in the calibration/training screens
class BCIService {
  // Singleton pattern
  static final BCIService instance = BCIService._internal();
  factory BCIService() => instance;
  BCIService._internal();

  // Server configuration
  static const String baseUrl =
      'http://10.0.2.2:5000'; // <- this is android emulator ip can be changed tro real phone // locally hosted for privacy

  //  timer for detection
  Timer? _pollTimer;

  Function(bool trigger, double confidence)? onTriggerDetected;
  Function(int progress)? onCalibrationProgress;
  Function(int current, int total)? onTrainingProgress;

  // ========== SYSTEM MANAGEMENT ==========

  /// Initialize EEG hardware
  Future<bool> initialize() async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/system/initialize'),
      );

      if (response.statusCode == 200) {
        print('BCI System initialized');
        return true;
      } else {
        print('Failed to initialize: ${response.body}');
        return false;
      }
    } catch (e) {
      print('Connection error: $e');
      print('Make sure Python server is running: python bci_flutter_bridge.py');
      return false;
    }
  }

  /// Shutdown EEG hardware
  Future<void> shutdown() async {
    stopDetectionPolling();

    try {
      await http.post(Uri.parse('$baseUrl/system/shutdown'));
      print('BCI System shutdown');
    } catch (e) {
      print('Shutdown error: $e');
    }
  }

  // ========== CALIBRATION ==========

  /// Start baseline calibration (60 seconds)
  Future<bool> startCalibration() async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/calibration/start'),
      );

      if (response.statusCode == 200) {
        print('Calibration started');
        _startCalibrationPolling();
        return true;
      } else {
        print('Failed to start calibration: ${response.body}');
        return false;
      }
    } catch (e) {
      print('Calibration error: $e');
      return false;
    }
  }

  // Poll calibration progress
  void _startCalibrationPolling() {
  _pollTimer?.cancel();

  _pollTimer = Timer.periodic(
    const Duration(milliseconds: 500),
    (timer) async {
      try {
        final response = await http.get(
          Uri.parse('$baseUrl/calibration/progress'),
        );

        if (response.statusCode != 200) return;

        final data = json.decode(response.body);
        final progress = data['progress'] as int;
        final status = data['status'] as String;

        onCalibrationProgress?.call(progress);

        // STOP polling unless actively calibrating
        if (status != 'calibrating') {
          timer.cancel();
          _pollTimer = null;
        }
      } catch (_) {
        timer.cancel();
        _pollTimer = null;
      }
    },
  );
}


  Future<Map<String, dynamic>> getCalibrationStatus() async {
    final response = await http.get(
      Uri.parse('$baseUrl/calibration/status'),
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to get calibration status');
    }

    return jsonDecode(response.body);
  }

  // ========== TRAINING ==========

  /// Start training session
  Future<bool> startTraining() async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/training/start'),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        print('Training started - ${data['total_trials']} trials');
        _startTrainingPolling();
        return true;
      } else {
        print('Failed to start training: ${response.body}');
        return false;
      }
    } catch (e) {
      print('Training error: $e');
      return false;
    }
  }

  /*Send manual trigger (when user presses button during training)
  Future<void> sendTrainingTrigger() async {
    try {
      await http.post(Uri.parse('$baseUrl/training/trigger'));
      print('Training trigger sent');
    } catch (e) {
      print('Trigger error: $e');
    }
  }*/

  /// Poll training progress
  void _startTrainingPolling() {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(Duration(seconds: 1), (timer) async {
      try {
        final response = await http.get(
          Uri.parse('$baseUrl/training/progress'),
        );

        if (response.statusCode == 200) {
          final data = json.decode(response.body);
          final current = data['current_trial'] as int;
          final total = data['total_trials'] as int;

          onTrainingProgress?.call(current, total);

          // Stop polling when complete
          if (current >= total) {
            timer.cancel();
          }
        }
      } catch (e) {
        print('Progress poll error: $e');
      }
    });
  }

  // ========== REAL-TIME DETECTION ==========

  /// Start motor imagery detection
  Future<bool> startDetection() async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/detection/start'),
      );

      if (response.statusCode == 200) {
        print('Detection started');
        _startDetectionPolling();
        return true;
      } else {
        print('Failed to start detection: ${response.body}');
        return false;
      }
    } catch (e) {
      print('Detection error: $e');
      return false;
    }
  }

  /// Stop motor imagery detection
  Future<void> stopDetection() async {
    stopDetectionPolling();

    try {
      await http.post(Uri.parse('$baseUrl/detection/stop'));
      print('Detection stopped');
    } catch (e) {
      print('Stop detection error: $e');
    }
  }

  /// Poll for motor imagery triggers
  void _startDetectionPolling() {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(Duration(milliseconds: 200), (timer) async {
      try {
        final response = await http.get(
          Uri.parse('$baseUrl/detection/poll'),
        );

        if (response.statusCode == 200) {
          final data = json.decode(response.body);
          final trigger = data['trigger'] as bool;
          final confidence = (data['confidence'] as num).toDouble();

          if (trigger) {
            print(
                'TRIGGER DETECTED! Confidence: ${(confidence * 100).toStringAsFixed(0)}%');
            onTriggerDetected?.call(trigger, confidence);
          }
        }
      } catch (e) {
        // Silent fail for polling
      }
    });
  }

  /// Stop polling
  void stopDetectionPolling() {
    _pollTimer?.cancel();
    _pollTimer = null;
  }

  // ========== STATUS ==========

  /// Get current system status
  Future<Map<String, dynamic>?> getStatus() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/status'));

      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
    } catch (e) {
      print('Status error: $e');
    }
    return null;
  }
}
