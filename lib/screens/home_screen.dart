import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:wave_flight_app/screens/device_control_screen.dart';
import 'package:wave_flight_app/services/bci_service.dart';
import 'package:wave_flight_app/services/kasa_service.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  static const String _selectedDeviceKey = 'selected_device_id_v2';
  static const String _kasaBridgeUrlKey = 'kasa_bridge_url_v2';
  static const String _bciBridgeUrlKey = 'bci_bridge_url_v1';

  final BCIService _bci = BCIService.instance;
  final TextEditingController _bciUrlController = TextEditingController();

  KasaSmartPlugService? _kasa;

  KasaDevice? _selectedDevice;
  String? _selectedDeviceId;

  bool _bciBridgeAvailable = false;
  bool _bciInitialized = false;
  bool _bciDetecting = false;
  bool _bciArmed = false;
  bool _isTogglingFromBci = false;

  double _lastConfidence = 0.0;
  String _lastEvent = 'Idle';

  DateTime? _lastDeviceActionAt;

  static const double _confidenceThreshold = 0.80;
  static const Duration _deviceCooldown = Duration(seconds: 4);

  @override
  void initState() {
    super.initState();
    _initialize();
    _bci.onTriggerDetected = _handleBciTrigger;
  }

  @override
  void dispose() {
    _bci.onTriggerDetected = null;
    _bciUrlController.dispose();
    super.dispose();
  }

  Future<void> _initialize() async {
    final prefs = await SharedPreferences.getInstance();

    final kasaBridgeUrl = prefs.getString(_kasaBridgeUrlKey) ??
        const String.fromEnvironment(
          'KASA_BRIDGE_URL',
          defaultValue: 'http://localhost:5273',
        );
    final bciBridgeUrl = prefs.getString(_bciBridgeUrlKey) ??
        const String.fromEnvironment(
          'BCI_BRIDGE_URL',
          defaultValue: 'http://localhost:5000',
        );

    _selectedDeviceId = prefs.getString(_selectedDeviceKey);
    _kasa = KasaSmartPlugService(baseUrl: kasaBridgeUrl);

    _bciUrlController.text = bciBridgeUrl;
    _bci.updateBaseUrl(bciBridgeUrl);

    await _refreshHomeStatus();
  }

  Future<void> _refreshHomeStatus() async {
    await _refreshSelectedDevice();
    await _refreshBciStatus();
  }

  Future<void> _refreshSelectedDevice() async {
    if (_selectedDeviceId == null) {
      if (!mounted) return;
      setState(() {
        _selectedDevice = null;
      });
      return;
    }

    // Try live bridge first
    if (_kasa != null) {
      try {
        final devices = await _kasa!.discoverDevices();
        final match = devices.where((d) => d.id == _selectedDeviceId).cast<KasaDevice?>().firstWhere(
              (d) => d != null,
              orElse: () => null,
            );

        if (match != null) {
          final prefs = await SharedPreferences.getInstance();
          await prefs.setString('selected_device_name', match.name);
          await prefs.setString('selected_device_ip', match.ip);
          await prefs.setString('selected_device_model', match.model);
          await prefs.setBool('selected_device_state', match.state);

          if (!mounted) return;
          setState(() {
            _selectedDevice = match;
          });
          return;
        }
      } catch (e) {
        // Fall through to cached data
      }
    }

    // Fall back to cached data
    final prefs = await SharedPreferences.getInstance();
    final name = prefs.getString('selected_device_name');
    final ip = prefs.getString('selected_device_ip');
    final model = prefs.getString('selected_device_model');
    final state = prefs.getBool('selected_device_state') ?? false;

    if (!mounted) return;
    setState(() {
      _selectedDevice = (name != null && ip != null)
          ? KasaDevice(
              id: _selectedDeviceId!,
              name: name,
              ip: ip,
              model: model ?? 'Kasa Plug',
              state: state,
            )
          : null;
    });
  }

  Future<void> _refreshBciStatus() async {
    final available = await _bci.bridgeAvailable();
    final status = available ? await _bci.getStatus() : null;

    if (!mounted) return;
    setState(() {
      _bciBridgeAvailable = available;
      _bciInitialized = status?.initialized ?? false;
      _bciDetecting = status?.detecting ?? false;
      _lastConfidence = status?.lastConfidence ?? _lastConfidence;
    });
  }

  Future<void> _applyBciUrl() async {
    final prefs = await SharedPreferences.getInstance();
    final url = _bciUrlController.text.trim();
    if (url.isEmpty) return;

    await prefs.setString(_bciBridgeUrlKey, url);
    _bci.updateBaseUrl(url);
    await _refreshBciStatus();
  }

  Future<void> _initializeBci() async {
    final ok = await _bci.initialize();
    if (!mounted) return;

    if (!ok) {
      setState(() => _lastEvent = 'BCI initialization failed');
      return;
    }

    setState(() => _lastEvent = 'Initializing BCI hardware (this takes ~30-40s)...');

    // stream.start() takes ~15s on the Neuropawn (config + settle).
    // Poll /status until hardware_initialized = true, up to 60s.
    const maxWait = Duration(seconds: 120); // Neuropawn config takes ~30-40s
    const pollInterval = Duration(seconds: 2);
    final deadline = DateTime.now().add(maxWait);

    while (DateTime.now().isBefore(deadline)) {
      await Future.delayed(pollInterval);
      if (!mounted) return;

      await _refreshBciStatus();

      if (_bciInitialized) {
        setState(() => _lastEvent = 'BCI initialized successfully');
        return;
      }
    }

    if (mounted) {
      setState(() => _lastEvent = 'BCI initialization timed out — check terminal');
    }
  }

  Future<void> _startDetection() async {
    final ok = await _bci.startDetection();
    if (!mounted) return;

    setState(() {
      _lastEvent = ok ? 'Detection started' : 'Detection failed to start';
    });

    await _refreshBciStatus();
  }

  Future<void> _stopDetection() async {
    await _bci.stopDetection();
    if (!mounted) return;

    setState(() {
      _bciArmed = false;
      _lastEvent = 'Detection stopped';
    });

    await _refreshBciStatus();
  }

  Future<void> _handleBciTrigger(bool trigger, double confidence) async {
    if (!mounted || !trigger) return;

    setState(() {
      _lastConfidence = confidence;
      _lastEvent = 'Trigger detected (${(confidence * 100).toStringAsFixed(0)}%)';
    });

    if (!_bciArmed) {
      setState(() {
        _lastEvent = 'Trigger ignored: BCI not armed';
      });
      return;
    }

    if (!_bciDetecting) {
      setState(() {
        _lastEvent = 'Trigger ignored: detection not active';
      });
      return;
    }

    if (_selectedDevice == null || _kasa == null) {
      setState(() {
        _lastEvent = 'Trigger ignored: no selected smart plug';
      });
      return;
    }

    if (confidence < _confidenceThreshold) {
      setState(() {
        _lastEvent =
            'Trigger ignored: confidence ${(confidence * 100).toStringAsFixed(0)}% below threshold';
      });
      return;
    }

    final now = DateTime.now();
    if (_lastDeviceActionAt != null &&
        now.difference(_lastDeviceActionAt!) < _deviceCooldown) {
      setState(() {
        _lastEvent = 'Trigger ignored: cooldown active';
      });
      return;
    }

    if (_isTogglingFromBci) return;

    setState(() {
      _isTogglingFromBci = true;
      _lastEvent = 'Executing safe toggle on ${_selectedDevice!.name}';
    });

    try {
      await _kasa!.toggleDevice(_selectedDevice!.id);
      final fresh = await _kasa!.getDeviceInfo(_selectedDevice!.id);

      _lastDeviceActionAt = DateTime.now();

      if (!mounted) return;
      setState(() {
        _selectedDevice = fresh;
        _lastEvent = 'BCI toggled ${fresh.name}';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _lastEvent = 'BCI toggle failed: $e';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isTogglingFromBci = false;
        });
      }
    }
  }

  Widget _statusChip(String label, bool ok) {
    return Chip(
      label: Text(label),
      backgroundColor: ok ? Colors.green.shade100 : Colors.orange.shade100,
      side: BorderSide(color: ok ? Colors.green : Colors.orange),
    );
  }

  @override
  Widget build(BuildContext context) {
    final selectedText = _selectedDevice == null
        ? 'No device selected'
        : '${_selectedDevice!.name} • ${_selectedDevice!.ip} • ${_selectedDevice!.state ? "ON" : "OFF"}';

    return Scaffold(
      appBar: AppBar(
        title: const Text('BCI For Accessibility'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () {
              Navigator.pushNamedAndRemoveUntil(context, '/signin', (route) => false);
            },
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Icon(Icons.psychology, size: 90, color: Colors.blue),
          const SizedBox(height: 16),
          const Center(
            child: Text(
              'Brain-Computer Interface',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
          ),
          const SizedBox(height: 6),
          const Center(
            child: Text(
              'Control one selected smart plug with safe BCI gating',
              style: TextStyle(fontSize: 16, color: Colors.grey),
            ),
          ),
          const SizedBox(height: 24),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'BCI Bridge',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _bciUrlController,
                    decoration: const InputDecoration(
                      labelText: 'BCI bridge URL',
                      hintText: 'http://localhost:5000',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(child: _statusChip('Bridge', _bciBridgeAvailable)),
                      const SizedBox(width: 8),
                      Expanded(child: _statusChip('Initialized', _bciInitialized)),
                      const SizedBox(width: 8),
                      Expanded(child: _statusChip('Detecting', _bciDetecting)),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: [
                      FilledButton(
                        onPressed: _applyBciUrl,
                        child: const Text('Apply URL'),
                      ),
                      OutlinedButton(
                        onPressed: _initializeBci,
                        child: const Text('Initialize BCI'),
                      ),
                      OutlinedButton(
                        onPressed: _startDetection,
                        child: const Text('Start Detection'),
                      ),
                      OutlinedButton(
                        onPressed: _stopDetection,
                        child: const Text('Stop Detection'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Selected Device',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  Text(selectedText),
                  const SizedBox(height: 12),
                  FilledButton.icon(
                    onPressed: () async {
                      await Navigator.push(
                        context,
                        MaterialPageRoute(builder: (_) => const DeviceControlScreen()),
                      );
                      await _refreshSelectedDevice();
                    },
                    icon: const Icon(Icons.home),
                    label: const Text('Open Devices'),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: SwitchListTile(
              title: const Text('Arm BCI Device Control'),
              subtitle: const Text(
                'Requires initialized detection, one selected plug, confidence threshold, and cooldown.',
              ),
              value: _bciArmed,
              onChanged: (_selectedDevice == null || !_bciDetecting)
                  ? null
                  : (value) {
                      setState(() {
                        _bciArmed = value;
                        _lastEvent = value ? 'BCI armed' : 'BCI disarmed';
                      });
                    },
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: ListTile(
              title: const Text('Last confidence'),
              subtitle: Text('${(_lastConfidence * 100).toStringAsFixed(0)}%'),
            ),
          ),
          Card(
            child: ListTile(
              title: const Text('Last event'),
              subtitle: Text(_lastEvent),
            ),
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              icon: const Icon(Icons.tune),
              label: const Text('Calibration'),
              onPressed: () {
                Navigator.pushNamed(context, '/calibration');
              },
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              icon: const Icon(Icons.fitness_center),
              label: const Text('Training'),
              onPressed: () {
                Navigator.pushNamed(context, '/training');
              },
            ),
          ),
        ],
      ),
    );
  }
}
