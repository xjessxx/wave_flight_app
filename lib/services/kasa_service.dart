// // import 'dart:convert';
// // import 'package:http/http.dart' as http;

// // class BridgeConfigStatus {
// //   final bool credentialsConfigured;
// //   final bool hasStoredUsername;
// //   final String bridgeUrlHint;
// //   final int deviceCount;

// //   BridgeConfigStatus({
// //     required this.credentialsConfigured,
// //     required this.hasStoredUsername,
// //     required this.bridgeUrlHint,
// //     required this.deviceCount,
// //   });

// //   factory BridgeConfigStatus.fromJson(Map<String, dynamic> json) {
// //     return BridgeConfigStatus(
// //       credentialsConfigured: json['credentialsConfigured'] == true,
// //       hasStoredUsername: json['hasStoredUsername'] == true,
// //       bridgeUrlHint: (json['bridgeUrlHint'] ?? '').toString(),
// //       deviceCount: (json['deviceCount'] ?? 0) as int,
// //     );
// //   }
// // }

// // class KasaDevice {
// //   final String id;
// //   String name;
// //   final String ip;
// //   final String model;
// //   bool state;
// //   final int? port;

// //   KasaDevice({
// //     required this.id,
// //     required this.name,
// //     required this.ip,
// //     required this.model,
// //     required this.state,
// //     this.port,
// //   });

// //   factory KasaDevice.fromJson(Map<String, dynamic> json) {
// //     return KasaDevice(
// //       id: json['id'].toString(),
// //       name: (json['name'] ?? 'Kasa Device').toString(),
// //       ip: json['ip'].toString(),
// //       model: (json['model'] ?? 'Unknown').toString(),
// //       state: json['state'] == true,
// //       port: json['port'] is int ? json['port'] as int : int.tryParse('${json['port']}'),
// //     );
// //   }

// //   Map<String, dynamic> toJson() {
// //     return {
// //       'id': id,
// //       'name': name,
// //       'ip': ip,
// //       'model': model,
// //       'state': state,
// //       'port': port,
// //     };
// //   }
// // }

// // class KasaSmartPlugService {
// //   KasaSmartPlugService({String? baseUrl})
// //       : _baseUrl = baseUrl ??
// //             const String.fromEnvironment(
// //               'KASA_BRIDGE_URL',
// //               defaultValue: 'http://127.0.0.1:5273',
// //             );

// //   final String _baseUrl;

// //   Uri _uri(String path) => Uri.parse('$_baseUrl$path');

// //   Map<String, dynamic> _decode(http.Response response) {
// //     if (response.body.isEmpty) return {};
// //     return jsonDecode(response.body) as Map<String, dynamic>;
// //   }

// //   Future<bool> bridgeAvailable() async {
// //     try {
// //       final response = await http.get(_uri('/health')).timeout(const Duration(seconds: 3));
// //       return response.statusCode == 200;
// //     } catch (_) {
// //       return false;
// //     }
// //   }

// //   Future<Map<String, dynamic>> getHealth() async {
// //     final response = await http.get(_uri('/health')).timeout(const Duration(seconds: 5));
// //     return _decode(response);
// //   }

// //   Future<BridgeConfigStatus> getConfigStatus() async {
// //     final response = await http.get(_uri('/config/status')).timeout(const Duration(seconds: 5));
// //     final data = _decode(response);
// //     if (response.statusCode >= 400 || data['ok'] != true) {
// //       throw Exception(data['error'] ?? 'Failed to fetch config status');
// //     }
// //     return BridgeConfigStatus.fromJson(data);
// //   }

// //   Future<void> saveCredentials({
// //     required String username,
// //     required String password,
// //   }) async {
// //     final response = await http.post(
// //       _uri('/config/credentials'),
// //       headers: {'Content-Type': 'application/json'},
// //       body: jsonEncode({
// //         'username': username,
// //         'password': password,
// //       }),
// //     ).timeout(const Duration(seconds: 10));

// //     final data = _decode(response);
// //     if (response.statusCode >= 400 || data['ok'] != true) {
// //       throw Exception(data['error'] ?? 'Failed to save credentials');
// //     }
// //   }

// //   Future<KasaDevice> testCredentials(String ip) async {
// //     final response = await http.post(
// //       _uri('/config/test'),
// //       headers: {'Content-Type': 'application/json'},
// //       body: jsonEncode({'ip': ip}),
// //     ).timeout(const Duration(seconds: 15));

// //     final data = _decode(response);
// //     if (response.statusCode >= 400 || data['ok'] != true) {
// //       throw Exception(data['error'] ?? 'Failed to test credentials');
// //     }
// //     return KasaDevice.fromJson(Map<String, dynamic>.from(data['device']));
// //   }

// //   Future<void> clearCredentials() async {
// //     final response = await http.post(_uri('/config/clear')).timeout(const Duration(seconds: 5));
// //     final data = _decode(response);
// //     if (response.statusCode >= 400 || data['ok'] != true) {
// //       throw Exception(data['error'] ?? 'Failed to clear credentials');
// //     }
// //   }

// //   Future<List<KasaDevice>> discoverDevices() async {
// //     final response = await http.get(_uri('/devices')).timeout(const Duration(seconds: 5));
// //     final data = _decode(response);
// //     final rawDevices = (data['devices'] as List?) ?? const [];
// //     return rawDevices
// //         .whereType<Map>()
// //         .map((e) => KasaDevice.fromJson(Map<String, dynamic>.from(e)))
// //         .toList();
// //   }

// //   Future<KasaDevice> registerDevice(String ip, {String? name}) async {
// //     final response = await http.post(
// //       _uri('/devices/register'),
// //       headers: {'Content-Type': 'application/json'},
// //       body: jsonEncode({'ip': ip, 'name': name}),
// //     ).timeout(const Duration(seconds: 15));

// //     final data = _decode(response);
// //     if (response.statusCode >= 400 || data['ok'] != true) {
// //       throw Exception(data['error'] ?? 'Failed to register device');
// //     }
// //     return KasaDevice.fromJson(Map<String, dynamic>.from(data['device']));
// //   }

// //   Future<KasaDevice> getDeviceInfo(String deviceId) async {
// //     final response = await http.get(_uri('/devices/$deviceId/state')).timeout(
// //           const Duration(seconds: 10),
// //         );
// //     final data = _decode(response);
// //     if (response.statusCode >= 400 || data['ok'] != true) {
// //       throw Exception(data['error'] ?? 'Failed to fetch device state');
// //     }
// //     return KasaDevice.fromJson(Map<String, dynamic>.from(data['device']));
// //   }

// //   Future<bool> toggleDevice(String deviceId) async {
// //     final response = await http.post(_uri('/devices/$deviceId/toggle')).timeout(
// //           const Duration(seconds: 10),
// //         );
// //     final data = _decode(response);
// //     if (response.statusCode >= 400 || data['ok'] != true) {
// //       throw Exception(data['error'] ?? 'Failed to toggle device');
// //     }
// //     return true;
// //   }

// //   Future<bool> removeDevice(String deviceId) async {
// //     final response = await http.delete(_uri('/devices/$deviceId')).timeout(
// //           const Duration(seconds: 10),
// //         );
// //     final data = _decode(response);
// //     if (response.statusCode >= 400 || data['ok'] != true) {
// //       throw Exception(data['error'] ?? 'Failed to remove device');
// //     }
// //     return true;
// //   }

// //   String get baseUrl => _baseUrl;
// // }


// // export 'kasa_service_stub.dart'
// //     if (dart.library.io) 'kasa_service_io.dart';
// import 'dart:convert';
// import 'package:http/http.dart' as http;

// class KasaSmartPlugService {
//   KasaSmartPlugService({String? baseUrl})
//       : _baseUrl = baseUrl ?? const String.fromEnvironment(
//           'KASA_BRIDGE_URL',
//           defaultValue: 'http://127.0.0.1:5273',
//         );

//   final String _baseUrl;

//   Uri _uri(String path) => Uri.parse('$_baseUrl$path');

//   Future<bool> bridgeAvailable() async {
//     try {
//       final response = await http.get(_uri('/health')).timeout(
//             const Duration(seconds: 3),
//           );
//       return response.statusCode == 200;
//     } catch (_) {
//       return false;
//     }
//   }

//   Future<List<Map<String, dynamic>>> discoverDevices({String subnet = ''}) async {
//     final response = await http.get(_uri('/devices')).timeout(
//           const Duration(seconds: 5),
//         );

//     final data = _decode(response);
//     final rawDevices = (data['devices'] as List?) ?? const [];
//     return rawDevices
//         .whereType<Map>()
//         .map((e) => Map<String, dynamic>.from(e))
//         .toList();
//   }

//   Future<Map<String, dynamic>?> registerDevice(String ip, {String? name}) async {
//     final response = await http.post(
//       _uri('/devices/register'),
//       headers: {'Content-Type': 'application/json'},
//       body: jsonEncode({'ip': ip, 'name': name}),
//     ).timeout(const Duration(seconds: 15));

//     final data = _decode(response);
//     if (response.statusCode >= 400 || data['ok'] != true) {
//       throw Exception(data['error'] ?? 'Failed to register device');
//     }
//     return Map<String, dynamic>.from(data['device']);
//   }

//   Future<Map<String, dynamic>?> getDeviceInfo(String deviceId) async {
//     final response = await http.get(_uri('/devices/$deviceId/state')).timeout(
//           const Duration(seconds: 10),
//         );
//     final data = _decode(response);
//     if (response.statusCode >= 400 || data['ok'] != true) {
//       throw Exception(data['error'] ?? 'Failed to fetch device state');
//     }
//     return Map<String, dynamic>.from(data['device']);
//   }

//   Future<bool?> getDeviceState(String deviceId) async {
//     final device = await getDeviceInfo(deviceId);
//     return device?['state'] as bool?;
//   }

//   Future<bool> toggleDevice(String deviceId) async {
//     final response = await http.post(_uri('/devices/$deviceId/toggle')).timeout(
//           const Duration(seconds: 10),
//         );
//     final data = _decode(response);
//     if (response.statusCode >= 400 || data['ok'] != true) {
//       throw Exception(data['error'] ?? 'Failed to toggle device');
//     }
//     return true;
//   }

//   Future<bool> turnOn(String deviceId) async {
//     final response = await http.post(_uri('/devices/$deviceId/on')).timeout(
//           const Duration(seconds: 10),
//         );
//     final data = _decode(response);
//     if (response.statusCode >= 400 || data['ok'] != true) {
//       throw Exception(data['error'] ?? 'Failed to turn on device');
//     }
//     return true;
//   }

//   Future<bool> turnOff(String deviceId) async {
//     final response = await http.post(_uri('/devices/$deviceId/off')).timeout(
//           const Duration(seconds: 10),
//         );
//     final data = _decode(response);
//     if (response.statusCode >= 400 || data['ok'] != true) {
//       throw Exception(data['error'] ?? 'Failed to turn off device');
//     }
//     return true;
//   }

//   Future<void> removeDevice(String deviceId) async {
//     final response = await http.delete(_uri('/devices/$deviceId')).timeout(
//           const Duration(seconds: 5),
//         );
//     final data = _decode(response);
//     if (response.statusCode >= 400 || data['ok'] != true) {
//       throw Exception(data['error'] ?? 'Failed to remove device');
//     }
//   }

//   Map<String, dynamic> _decode(http.Response response) {
//     if (response.body.isEmpty) return <String, dynamic>{};
//     final decoded = jsonDecode(response.body);
//     if (decoded is Map<String, dynamic>) return decoded;
//     return <String, dynamic>{'data': decoded};
//   }
// }


import 'dart:convert';
import 'package:http/http.dart' as http;

// ============================================================================
// DATA MODELS
// ============================================================================

class KasaDevice {
  final String id;
  String name;
  final String ip;
  String model;
  bool state;

  KasaDevice({
    required this.id,
    required this.name,
    required this.ip,
    required this.model,
    required this.state,
  });

  factory KasaDevice.fromJson(Map<String, dynamic> json) {
    return KasaDevice(
      id: (json['id'] as String?) ?? '',
      name: (json['name'] as String?) ?? 'Kasa Plug',
      ip: (json['ip'] as String?) ?? '',
      model: (json['model'] as String?) ?? 'Kasa Plug',
      state: (json['state'] as bool?) ?? false,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'ip': ip,
        'model': model,
        'state': state,
      };

  @override
  String toString() => 'KasaDevice($name @ $ip, ${state ? "ON" : "OFF"})';
}

class BridgeConfigStatus {
  final bool credentialsConfigured;
  final int deviceCount;

  BridgeConfigStatus({
    required this.credentialsConfigured,
    required this.deviceCount,
  });

  factory BridgeConfigStatus.fromJson(Map<String, dynamic> json) {
    return BridgeConfigStatus(
      credentialsConfigured: (json['credentials_configured'] as bool?) ?? false,
      deviceCount: (json['device_count'] as int?) ?? 0,
    );
  }
}

// ============================================================================
// SERVICE
// ============================================================================

/// Flutter client for the Python Kasa bridge server (kasa_bridge.py).
///
/// The bridge runs locally and handles all python-kasa calls.
/// Credentials are held in the bridge's process memory only —
/// they are never written to disk or sent anywhere other than
/// your own Kasa account servers.
class KasaSmartPlugService {
  final String baseUrl;

  KasaSmartPlugService({required this.baseUrl});

  Uri _uri(String path) => Uri.parse('$baseUrl$path');

  Map<String, dynamic> _decodeBody(http.Response response) {
    if (response.body.isEmpty) return {};
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  void _assertOk(http.Response response) {
    if (response.statusCode < 200 || response.statusCode >= 300) {
      Map<String, dynamic> body = {};
      try {
        body = _decodeBody(response);
      } catch (_) {}
      final msg = (body['error'] as String?) ?? response.body;
      throw Exception(msg.isNotEmpty ? msg : 'HTTP ${response.statusCode}');
    }
  }

  // ──────────────────────────────────────────────────────────────────────────
  // HEALTH
  // ──────────────────────────────────────────────────────────────────────────

  /// Returns true if the bridge server is reachable.
  Future<bool> bridgeAvailable() async {
    try {
      final response = await http
          .get(_uri('/status'))
          .timeout(const Duration(seconds: 3));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  /// Returns credentials + device count from the bridge.
  Future<BridgeConfigStatus> getConfigStatus() async {
    final response = await http
        .get(_uri('/config/status'))
        .timeout(const Duration(seconds: 5));
    _assertOk(response);
    return BridgeConfigStatus.fromJson(_decodeBody(response));
  }

  // ──────────────────────────────────────────────────────────────────────────
  // CREDENTIALS
  // ──────────────────────────────────────────────────────────────────────────

  /// Send Kasa account credentials to the bridge (held in memory only).
  Future<void> saveCredentials({
    required String username,
    required String password,
  }) async {
    final response = await http
        .post(
          _uri('/credentials/save'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'username': username, 'password': password}),
        )
        .timeout(const Duration(seconds: 10));
    _assertOk(response);
  }

  /// Test saved credentials against a known plug IP.
  /// Returns the device if successful, throws on failure.
  Future<KasaDevice> testCredentials(String ip) async {
    final response = await http
        .post(
          _uri('/credentials/test'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'ip': ip}),
        )
        .timeout(const Duration(seconds: 15));
    _assertOk(response);
    return KasaDevice.fromJson(_decodeBody(response));
  }

  /// Clear credentials from the bridge's memory.
  Future<void> clearCredentials() async {
    final response = await http
        .post(_uri('/credentials/clear'))
        .timeout(const Duration(seconds: 5));
    _assertOk(response);
  }

  // ──────────────────────────────────────────────────────────────────────────
  // DEVICE MANAGEMENT
  // ──────────────────────────────────────────────────────────────────────────

  /// List all registered devices (with live state if bridge can reach them).
  Future<List<KasaDevice>> discoverDevices() async {
    final response = await http
        .get(_uri('/devices'))
        .timeout(const Duration(seconds: 15));
    _assertOk(response);
    final list = jsonDecode(response.body) as List<dynamic>;
    return list
        .map((e) => KasaDevice.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Register a new plug by IP address.
  /// The bridge will verify credentials + connectivity before persisting.
  Future<KasaDevice> registerDevice(String ip, {String? name}) async {
    final response = await http
        .post(
          _uri('/devices/register'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'ip': ip, 'name': name ?? ''}),
        )
        .timeout(const Duration(seconds: 20));
    _assertOk(response);
    return KasaDevice.fromJson(_decodeBody(response));
  }

  /// Get live state for one device.
  Future<KasaDevice> getDeviceInfo(String deviceId) async {
    final response = await http
        .get(_uri('/devices/$deviceId'))
        .timeout(const Duration(seconds: 10));
    _assertOk(response);
    return KasaDevice.fromJson(_decodeBody(response));
  }

  /// Toggle a device on/off. Returns the updated device state.
  Future<KasaDevice> toggleDevice(String deviceId) async {
    final response = await http
        .post(_uri('/devices/$deviceId/toggle'))
        .timeout(const Duration(seconds: 10));
    _assertOk(response);
    return KasaDevice.fromJson(_decodeBody(response));
  }

  /// Remove a device from the registry.
  Future<void> removeDevice(String deviceId) async {
    final response = await http
        .delete(_uri('/devices/$deviceId'))
        .timeout(const Duration(seconds: 10));
    _assertOk(response);
  }
}