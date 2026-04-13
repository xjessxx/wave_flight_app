import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:wave_flight_app/services/kasa_service.dart';

class DeviceControlScreen extends StatefulWidget {
  const DeviceControlScreen({super.key});

  @override
  State<DeviceControlScreen> createState() => _DeviceControlScreenState();
}

class _DeviceControlScreenState extends State<DeviceControlScreen> {
  static const String _selectedDeviceKey = 'selected_device_id_v2';
  static const String _bridgeUrlKey = 'kasa_bridge_url_v2';

  late KasaSmartPlugService _kasa;

  final TextEditingController _bridgeUrlController = TextEditingController();
  final TextEditingController _usernameController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();

  List<KasaDevice> _devices = [];
  String? _selectedDeviceId;

  final bool _useRealDevices = true;
  bool _isLoading = false;
  bool _isSavingCredentials = false;
  bool _isTestingCredentials = false;
  bool _isRefreshingDevices = false;
  bool _isTogglingSelected = false;

  bool _bridgeAvailable = false;
  BridgeConfigStatus? _configStatus;
  String? _statusMessage;

  KasaDevice? get _selectedDevice {
    for (final device in _devices) {
      if (device.id == _selectedDeviceId) return device;
    }
    return null;
  }

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  @override
  void dispose() {
    _bridgeUrlController.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _initialize() async {
    final prefs = await SharedPreferences.getInstance();
    final savedBridgeUrl = prefs.getString(_bridgeUrlKey) ??
        const String.fromEnvironment(
          'KASA_BRIDGE_URL',
          defaultValue: 'http://localhost:5273',
        );
    final savedSelectedDeviceId = prefs.getString(_selectedDeviceKey);

    _bridgeUrlController.text = savedBridgeUrl;
    _selectedDeviceId = savedSelectedDeviceId;
    // Persist the URL immediately so it survives restarts even if the user
    // never presses Apply.
    await prefs.setString(_bridgeUrlKey, savedBridgeUrl);
    _rebuildService();

    await _refreshAll();
  }

  void _rebuildService() {
    _kasa = KasaSmartPlugService(baseUrl: _bridgeUrlController.text.trim());
  }

  Future<void> _saveBridgeUrl() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_bridgeUrlKey, _bridgeUrlController.text.trim());
  }

  /*Future<void> _saveSelectedDevice(String? deviceId) async {
    final prefs = await SharedPreferences.getInstance();
    if (deviceId == null) {
      await prefs.remove(_selectedDeviceKey);
    } else {
      await prefs.setString(_selectedDeviceKey, deviceId);
    }

    if (!mounted) return;
    setState(() {
      _selectedDeviceId = deviceId;
    });
  }*/

  Future<void> _saveSelectedDevice(String? deviceId) async {
    final prefs = await SharedPreferences.getInstance();
    if (deviceId == null) {
      await prefs.remove(_selectedDeviceKey);
      await prefs.remove('selected_device_name');
      await prefs.remove('selected_device_ip');
      await prefs.remove('selected_device_model');
      await prefs.remove('selected_device_state');
    } else {
      await prefs.setString(_selectedDeviceKey, deviceId);
      // Cache full device details so home screen works without live bridge
      final device = _devices.where((d) => d.id == deviceId).firstOrNull;
      if (device != null) {
        await prefs.setString('selected_device_name', device.name);
        await prefs.setString('selected_device_ip', device.ip);
        await prefs.setString('selected_device_model', device.model);
        await prefs.setBool('selected_device_state', device.state);
      }
    }

    if (!mounted) return;
    setState(() {
      _selectedDeviceId = deviceId;
    });
  }

  Future<void> _refreshAll() async {
    setState(() {
      _isLoading = true;
      _statusMessage = 'Connecting to bridge...';
    });

    try {
      await _refreshBridgeStatus();
      if (_bridgeAvailable && _useRealDevices) {
        await _refreshDevices();
      } else if (!_useRealDevices) {
        setState(() {
          _devices = [
            KasaDevice(
              id: 'mock_device',
              name: 'Mock Lamp',
              ip: 'localhost',
              model: 'Mock Plug',
              state: false,
            ),
          ];
          _statusMessage = 'Mock mode is active.';
        });
      }
    } catch (e) {
      _setStatus('Failed to initialize device page: $e', isError: true);
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _refreshBridgeStatus() async {
    _rebuildService();

    try {
      final available = await _kasa.bridgeAvailable();
      if (!mounted) return;

      setState(() {
        _bridgeAvailable = available;
      });

      if (!available) {
        setState(() {
          _configStatus = null;
          _devices = _useRealDevices ? [] : _devices;
          _statusMessage =
              'Bridge not reachable. Check the server URL and make sure the bridge is running.';
        });
        return;
      }

      final config = await _kasa.getConfigStatus();
      if (!mounted) return;

      setState(() {
        _configStatus = config;
        _statusMessage = config.credentialsConfigured
            ? 'Bridge connected. Kasa credentials are configured.'
            : 'Bridge connected. Save your Kasa credentials to continue.';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _bridgeAvailable = false;
        _configStatus = null;
        _statusMessage = 'Bridge error: $e';
      });
    }
  }

  Future<void> _refreshDevices() async {
    if (!_useRealDevices) return;
    if (!_bridgeAvailable) {
      _setStatus('Bridge is not connected.', isError: true);
      return;
    }

    setState(() {
      _isRefreshingDevices = true;
    });

    try {
      final devices = await _kasa.discoverDevices();
      if (!mounted) return;

      setState(() {
        _devices = devices;
        final selectedStillExists =
            _devices.any((d) => d.id == _selectedDeviceId);
        if (!selectedStillExists && _devices.isNotEmpty) {
          _selectedDeviceId = null;
        }

        _statusMessage = devices.isEmpty
            ? 'No registered devices yet. Add a plug by IP after saving credentials.'
            : 'Loaded ${devices.length} registered device(s).';
      });

      if (_selectedDeviceId == null && _devices.isNotEmpty) {
        final prefs = await SharedPreferences.getInstance();
        await prefs.remove(_selectedDeviceKey);
      }
    } catch (e) {
      _setStatus('Failed to load devices: $e', isError: true);
    } finally {
      if (mounted) {
        setState(() {
          _isRefreshingDevices = false;
        });
      }
    }
  }

  Future<void> _saveCredentials() async {
    final username = _usernameController.text.trim();
    final password = _passwordController.text;

    if (username.isEmpty || password.isEmpty) {
      _setStatus('Enter both Kasa username/email and password.', isError: true);
      return;
    }

    if (!_bridgeAvailable) {
      _setStatus('Bridge is not connected.', isError: true);
      return;
    }

    setState(() {
      _isSavingCredentials = true;
    });

    try {
      await _kasa.saveCredentials(username: username, password: password);
      await _refreshBridgeStatus();
      _setStatus('Kasa credentials saved to the bridge.');
      _passwordController.clear();
    } catch (e) {
      _setStatus('Failed to save credentials: $e', isError: true);
    } finally {
      if (mounted) {
        setState(() {
          _isSavingCredentials = false;
        });
      }
    }
  }

  Future<void> _testCredentials() async {
    final ip = await _showSingleIpPrompt(
      title: 'Test Kasa Credentials',
      description:
          'Enter the IP address of one known Kasa plug. The bridge will verify your saved credentials against that device.',
      confirmLabel: 'Test',
    );

    if (ip == null || ip.isEmpty) return;

    setState(() {
      _isTestingCredentials = true;
    });

    try {
      final device = await _kasa.testCredentials(ip);
      await _refreshBridgeStatus();
      _setStatus(
        'Credentials worked. Verified ${device.name} at ${device.ip}.',
      );
    } catch (e) {
      _setStatus('Credential test failed: $e', isError: true);
    } finally {
      if (mounted) {
        setState(() {
          _isTestingCredentials = false;
        });
      }
    }
  }

  Future<void> _clearCredentials() async {
    try {
      await _kasa.clearCredentials();
      _usernameController.clear();
      _passwordController.clear();
      await _refreshBridgeStatus();
      _setStatus('Stored Kasa credentials were cleared.');
    } catch (e) {
      _setStatus('Could not clear credentials: $e', isError: true);
    }
  }

  Future<void> _toggleSelected() async {
    final selected = _selectedDevice;
    if (selected == null) {
      _setStatus('Select a device first.', isError: true);
      return;
    }

    setState(() {
      _isTogglingSelected = true;
    });

    try {
      if (_useRealDevices) {
        await _kasa.toggleDevice(selected.id);
        final fresh = await _kasa.getDeviceInfo(selected.id);
        final index = _devices.indexWhere((d) => d.id == selected.id);
        if (index != -1) {
          _devices[index] = fresh;
        }
        if (!mounted) return;
        setState(() {
          _statusMessage = 'Toggled ${fresh.name}.';
        });
      } else {
        final index = _devices.indexWhere((d) => d.id == selected.id);
        if (index != -1) {
          setState(() {
            _devices[index].state = !_devices[index].state;
            _statusMessage = 'Toggled ${_devices[index].name}.';
          });
        }
      }
    } catch (e) {
      _setStatus('Toggle failed: $e', isError: true);
    } finally {
      if (mounted) {
        setState(() {
          _isTogglingSelected = false;
        });
      }
    }
  }

  Future<void> _refreshSelected() async {
    final selected = _selectedDevice;
    if (selected == null) {
      _setStatus('Select a device first.', isError: true);
      return;
    }

    if (!_useRealDevices) {
      _setStatus('Refresh is only needed in real mode.');
      return;
    }

    try {
      final fresh = await _kasa.getDeviceInfo(selected.id);
      final index = _devices.indexWhere((d) => d.id == selected.id);
      if (index != -1) {
        setState(() {
          _devices[index] = fresh;
          _statusMessage = 'Refreshed ${fresh.name}.';
        });
      }
    } catch (e) {
      _setStatus('Refresh failed: $e', isError: true);
    }
  }

  Future<void> _removeDevice(KasaDevice device) async {
    try {
      if (_useRealDevices) {
        await _kasa.removeDevice(device.id);
      }

      setState(() {
        _devices.removeWhere((d) => d.id == device.id);
        if (_selectedDeviceId == device.id) {
          _selectedDeviceId = null;
        }
        _statusMessage = 'Removed ${device.name}.';
      });

      await _saveSelectedDevice(_selectedDeviceId);
    } catch (e) {
      _setStatus('Remove failed: $e', isError: true);
    }
  }

  Future<void> _addDeviceByIp() async {
    final result = await _showAddDeviceDialog();
    if (result == null) return;

    try {
      final device = await _kasa.registerDevice(
        result.ip,
        name: result.name.isEmpty ? null : result.name,
      );

      await _refreshDevices();
      await _saveSelectedDevice(device.id);

      _setStatus('Added ${device.name}.');
    } catch (e) {
      _setStatus('Could not add device: $e', isError: true);
    }
  }

  Future<_AddDeviceResult?> _showAddDeviceDialog() async {
    final nameController = TextEditingController();
    final ipController = TextEditingController();
    bool saving = false;

    return showDialog<_AddDeviceResult>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            Future<void> submit() async {
              final ip = ipController.text.trim();
              final name = nameController.text.trim();

              if (ip.isEmpty) return;

              setDialogState(() {
                saving = true;
              });

              Navigator.of(context).pop(_AddDeviceResult(name: name, ip: ip));
            }

            return AlertDialog(
              title: const Text('Add Kasa Plug by IP'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: nameController,
                    decoration: const InputDecoration(
                      labelText: 'Display name (optional)',
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: ipController,
                    decoration: const InputDecoration(
                      labelText: 'IP address',
                      hintText: '<device-ip>',
                    ),
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'This registers the plug through the bridge using your saved Kasa credentials.',
                    style: TextStyle(fontSize: 12, color: Colors.grey),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: saving ? null : () => Navigator.of(context).pop(),
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  onPressed: saving ? null : submit,
                  child: const Text('Add'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  Future<String?> _showSingleIpPrompt({
    required String title,
    required String description,
    required String confirmLabel,
  }) async {
    final controller = TextEditingController();

    return showDialog<String>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text(title),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(description),
              const SizedBox(height: 12),
              TextField(
                controller: controller,
                decoration: const InputDecoration(
                  labelText: 'Device IP',
                  hintText: '<device-ip>',
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () =>
                  Navigator.of(context).pop(controller.text.trim()),
              child: Text(confirmLabel),
            ),
          ],
        );
      },
    );
  }

  void _applyBridgeUrl() async {
    final rawUrl = _bridgeUrlController.text.trim();
    if (rawUrl.isEmpty) {
      _setStatus('Enter a bridge URL first.', isError: true);
      return;
    }

    await _saveBridgeUrl();
    _rebuildService();
    await _refreshAll();
  }

  void _setStatus(String message, {bool isError = false}) {
    if (!mounted) return;

    setState(() {
      _statusMessage = message;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError ? Colors.red : Colors.green,
      ),
    );
  }

  Widget _buildBridgeCard() {
    final credentialsConfigured = _configStatus?.credentialsConfigured ?? false;

    return Card(
      margin: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Bridge Connection',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _bridgeUrlController,
              decoration: const InputDecoration(
                labelText: 'Bridge URL',
                hintText: 'http://localhost:5273',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Icon(
                  _bridgeAvailable ? Icons.check_circle : Icons.error_outline,
                  color: _bridgeAvailable ? Colors.green : Colors.red,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    _bridgeAvailable
                        ? 'Bridge connected'
                        : 'Bridge not connected',
                  ),
                ),
                FilledButton(
                  onPressed: _applyBridgeUrl,
                  child: const Text('Apply'),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              credentialsConfigured
                  ? 'Kasa credentials are configured on the bridge.'
                  : 'Kasa credentials are not configured yet.',
              style: TextStyle(
                color: credentialsConfigured ? Colors.green : Colors.orange,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'For desktop testing use localhost. For phone testing on the same Wi-Fi, use your computer\'s LAN address and port 5273.',
              style: TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCredentialsCard() {
    final credentialsConfigured = _configStatus?.credentialsConfigured ?? false;

    return Card(
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Kasa Account',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _usernameController,
              decoration: const InputDecoration(
                labelText: 'Kasa email / username',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _passwordController,
              obscureText: true,
              decoration: const InputDecoration(
                labelText: 'Kasa password',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                FilledButton.icon(
                  onPressed: !_bridgeAvailable || _isSavingCredentials
                      ? null
                      : _saveCredentials,
                  icon: _isSavingCredentials
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.save),
                  label: const Text('Save Credentials'),
                ),
                OutlinedButton.icon(
                  onPressed: !_bridgeAvailable || _isTestingCredentials
                      ? null
                      : _testCredentials,
                  icon: _isTestingCredentials
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.verified_user),
                  label: const Text('Test Credentials'),
                ),
                TextButton(
                  onPressed: !_bridgeAvailable ? null : _clearCredentials,
                  child: const Text('Clear'),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              credentialsConfigured
                  ? 'Credentials are saved on the bridge machine.'
                  : 'Save credentials once before adding Kasa plugs.',
              style: const TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ],
        ),
      ),
    );
  }

  /// Shown inside SliverFillRemaining when the device list is empty.
  Widget _buildEmptyDeviceState(bool credentialsConfigured) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.power, size: 72, color: Colors.grey),
            const SizedBox(height: 16),
            const Text(
              'No plugs added yet',
              style: TextStyle(fontSize: 20, color: Colors.grey),
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: !_bridgeAvailable || !credentialsConfigured
                  ? null
                  : _addDeviceByIp,
              icon: const Icon(Icons.add),
              label: const Text('Add by IP'),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: _isRefreshingDevices ? null : _refreshDevices,
              icon: _isRefreshingDevices
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.refresh),
              label: const Text('Refresh Registered Devices'),
            ),
          ],
        ),
      ),
    );
  }

  /// Single device tile used by the SliverList.
  Widget _buildDeviceTile(KasaDevice device) {
    final isSelected = device.id == _selectedDeviceId;

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
      child: Card(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(
            color: isSelected ? Colors.blue : Colors.transparent,
            width: 2,
          ),
        ),
        child: ListTile(
          leading: Icon(
            Icons.power,
            color: device.state ? Colors.green : Colors.grey,
            size: 36,
          ),
          title: Text(device.name),
          subtitle: Text('${device.model} • ${device.ip}'),
          trailing: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(device.state ? 'ON' : 'OFF'),
              const SizedBox(width: 8),
              Switch(
                value: device.state,
                onChanged: _isTogglingSelected
                    ? null
                    : (_) async {
                        await _saveSelectedDevice(device.id);
                        await _toggleSelected();
                      },
              ),
              PopupMenuButton<String>(
                onSelected: (value) async {
                  if (value == 'remove') {
                    await _removeDevice(device);
                  } else if (value == 'select') {
                    await _saveSelectedDevice(device.id);
                    _setStatus(
                        '${device.name} selected for later BCI control.');
                  }
                },
                itemBuilder: (_) => const [
                  PopupMenuItem(value: 'select', child: Text('Use for BCI')),
                  PopupMenuItem(value: 'remove', child: Text('Remove')),
                ],
              ),
            ],
          ),
          onTap: () => _saveSelectedDevice(device.id),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final credentialsConfigured = _configStatus?.credentialsConfigured ?? false;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Devices & Smart Home'),
      ),
      // Use a CustomScrollView so the bridge/credential cards can scroll on
      // small windows without causing "BOTTOM OVERFLOWED BY X PIXELS" errors.
      body: CustomScrollView(
        slivers: [
          // ── Status banner ──────────────────────────────────────────────
          SliverToBoxAdapter(
            child: Container(
              width: double.infinity,
              color: Colors.black87,
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Safe testing flow',
                    style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    _useRealDevices
                        ? 'First save credentials, then add one harmless plug by IP, select it, and verify manual toggling works before connecting BCI control.'
                        : 'Mock mode is active for UI testing only.',
                    style: const TextStyle(color: Colors.white70),
                  ),
                  if (_statusMessage != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      _statusMessage!,
                      style: const TextStyle(color: Colors.white70),
                    ),
                  ],
                ],
              ),
            ),
          ),

          // ── Bridge + credentials cards ─────────────────────────────────
          SliverToBoxAdapter(child: _buildBridgeCard()),
          SliverToBoxAdapter(child: _buildCredentialsCard()),

          // ── Device list ────────────────────────────────────────────────
          _isLoading
              ? const SliverFillRemaining(
                  child: Center(child: CircularProgressIndicator()),
                )
              : _devices.isEmpty
                  ? SliverFillRemaining(
                      hasScrollBody: false,
                      child: _buildEmptyDeviceState(credentialsConfigured),
                    )
                  : SliverList(
                      delegate: SliverChildBuilderDelegate(
                        (context, index) => _buildDeviceTile(_devices[index]),
                        childCount: _devices.length,
                      ),
                    ),

          // ── Bottom action buttons ──────────────────────────────────────
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
              child: Column(
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: !_bridgeAvailable ||
                                  !credentialsConfigured ||
                                  _isRefreshingDevices
                              ? null
                              : _refreshDevices,
                          icon: const Icon(Icons.search),
                          label: const Text('Refresh Devices'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: !_bridgeAvailable || !credentialsConfigured
                              ? null
                              : _addDeviceByIp,
                          icon: const Icon(Icons.add),
                          label: const Text('Add by IP'),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed:
                              _selectedDevice == null ? null : _refreshSelected,
                          icon: const Icon(Icons.refresh),
                          label: const Text('Refresh Selected'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: FilledButton.icon(
                          onPressed:
                              _selectedDevice == null || _isTogglingSelected
                                  ? null
                                  : _toggleSelected,
                          icon: _isTogglingSelected
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child:
                                      CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.bolt),
                          label: const Text('Test Selected'),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    _selectedDevice == null
                        ? 'Select one plug to make it the only BCI target later.'
                        : 'Selected for BCI: ${_selectedDevice!.name}',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Helper class ────────────────────────────────────────────────────────────

class _AddDeviceResult {
  final String name;
  final String ip;

  _AddDeviceResult({
    required this.name,
    required this.ip,
  });
}

// //===================================================================================

// import 'package:flutter/material.dart';
// import 'package:shared_preferences/shared_preferences.dart';
// import 'package:wave_flight_app/services/kasa_service.dart';

// class DeviceControlScreen extends StatefulWidget {
//   const DeviceControlScreen({super.key});

//   @override
//   State<DeviceControlScreen> createState() => _DeviceControlScreenState();
// }

// class _DeviceControlScreenState extends State<DeviceControlScreen> {
//   final KasaSmartPlugService _kasa = KasaSmartPlugService();

//   List<KasaDevice> _availableDevices = [];
//   String? _selectedDeviceId;
//   bool _useRealDevices = true;
//   bool _isBusy = false;
//   String? _statusMessage;

//   static const _selectedDeviceKey = 'selected_device_id';

//   @override
//   void initState() {
//     super.initState();
//     _loadSelectedDevice();
//     _refreshDevices();
//   }

//   Future<void> _loadSelectedDevice() async {
//     final prefs = await SharedPreferences.getInstance();
//     if (!mounted) return;
//     setState(() {
//       _selectedDeviceId = prefs.getString(_selectedDeviceKey);
//     });
//   }

//   Future<void> _saveSelectedDevice(String? deviceId) async {
//     final prefs = await SharedPreferences.getInstance();
//     if (deviceId == null) {
//       await prefs.remove(_selectedDeviceKey);
//     } else {
//       await prefs.setString(_selectedDeviceKey, deviceId);
//     }
//     if (!mounted) return;
//     setState(() {
//       _selectedDeviceId = deviceId;
//     });
//   }

//   Future<void> _refreshDevices() async {
//     if (!_useRealDevices) {
//       setState(() {
//         _availableDevices = [
//           KasaDevice(
//             id: 'mock_plug',
//             name: 'Mock Desk Lamp',
//             ip: 'localhost',
//             model: 'Mock Plug',
//             state: false,
//           ),
//         ];
//         _statusMessage = 'Mock mode is active.';
//       });
//       return;
//     }

//     setState(() {
//       _isBusy = true;
//       _statusMessage = 'Checking local Kasa bridge...';
//     });

//     try {
//       final available = await _kasa.bridgeAvailable();
//       if (!available) {
//         throw Exception('Local Kasa bridge is not running on http://localhost:5273');
//       }

//       final devices = await _kasa.discoverDevices();
//       if (!mounted) return;
//       setState(() {
//         _availableDevices = devices.map(KasaDevice.fromJson).toList();
//         _statusMessage = devices.isEmpty
//             ? 'Bridge is running. Add your plug by IP to register it.'
//             : 'Loaded ${devices.length} registered device(s).';
//       });
//     } catch (e) {
//       if (!mounted) return;
//       setState(() {
//         _statusMessage = 'Could not reach local bridge: $e';
//       });
//     } finally {
//       if (mounted) {
//         setState(() {
//           _isBusy = false;
//         });
//       }
//     }
//   }

//   Future<void> _toggleDevice(KasaDevice device) async {
//     setState(() => _isBusy = true);
//     try {
//       if (_useRealDevices) {
//         await _kasa.toggleDevice(device.id);
//         final fresh = await _kasa.getDeviceInfo(device.id);
//         if (fresh != null) {
//           final updated = KasaDevice.fromJson(fresh);
//           final index = _availableDevices.indexWhere((d) => d.id == device.id);
//           if (index != -1) {
//             _availableDevices[index] = updated;
//           }
//         }
//       } else {
//         final index = _availableDevices.indexWhere((d) => d.id == device.id);
//         if (index != -1) {
//           _availableDevices[index].state = !_availableDevices[index].state;
//         }
//       }

//       if (!mounted) return;
//       setState(() {
//         _statusMessage = 'Toggled ${device.name}.';
//       });
//     } catch (e) {
//       _showError('Toggle failed: $e');
//     } finally {
//       if (mounted) setState(() => _isBusy = false);
//     }
//   }

//   Future<void> _refreshSelected() async {
//     final selected = _selectedDevice;
//     if (selected == null) {
//       _showError('Select a device first.');
//       return;
//     }

//     setState(() => _isBusy = true);
//     try {
//       final fresh = await _kasa.getDeviceInfo(selected.id);
//       if (fresh != null && mounted) {
//         final updated = KasaDevice.fromJson(fresh);
//         final index = _availableDevices.indexWhere((d) => d.id == selected.id);
//         if (index != -1) {
//           setState(() {
//             _availableDevices[index] = updated;
//             _statusMessage = 'Refreshed ${updated.name}.';
//           });
//         }
//       }
//     } catch (e) {
//       _showError('Refresh failed: $e');
//     } finally {
//       if (mounted) setState(() => _isBusy = false);
//     }
//   }

//   Future<void> _testSelected() async {
//     final selected = _selectedDevice;
//     if (selected == null) {
//       _showError('Select a device first.');
//       return;
//     }
//     await _toggleDevice(selected);
//   }

//   Future<void> _removeDevice(KasaDevice device) async {
//     try {
//       if (_useRealDevices) {
//         await _kasa.removeDevice(device.id);
//       }
//       if (!mounted) return;
//       setState(() {
//         _availableDevices.removeWhere((d) => d.id == device.id);
//         if (_selectedDeviceId == device.id) {
//           _selectedDeviceId = null;
//         }
//         _statusMessage = 'Removed ${device.name}.';
//       });
//       await _saveSelectedDevice(_selectedDeviceId);
//     } catch (e) {
//       _showError('Remove failed: $e');
//     }
//   }

//   KasaDevice? get _selectedDevice {
//     try {
//       return _availableDevices.firstWhere((d) => d.id == _selectedDeviceId);
//     } catch (_) {
//       return null;
//     }
//   }

//   void _showAddDeviceDialog() {
//     final nameController = TextEditingController();
//     final ipController = TextEditingController();
//     bool saving = false;

//     showDialog<void>(
//       context: context,
//       barrierDismissible: !saving,
//       builder: (context) {
//         return StatefulBuilder(
//           builder: (context, setDialogState) {
//             Future<void> addDevice() async {
//               final ip = ipController.text.trim();
//               final name = nameController.text.trim();
//               if (ip.isEmpty) return;

//               setDialogState(() => saving = true);
//               try {
//                 if (_useRealDevices) {
//                   await _kasa.registerDevice(ip, name: name.isEmpty ? null : name);
//                   if (!mounted) return;
//                   Navigator.of(context).pop();
//                   await _refreshDevices();
//                 } else {
//                   final mock = KasaDevice(
//                     id: 'mock_${DateTime.now().millisecondsSinceEpoch}',
//                     name: name.isEmpty ? 'Mock Plug' : name,
//                     ip: ip,
//                     model: 'Mock Plug',
//                     state: false,
//                   );
//                   if (!mounted) return;
//                   setState(() {
//                     _availableDevices.add(mock);
//                     _statusMessage = 'Added mock device.';
//                   });
//                   Navigator.of(context).pop();
//                 }
//               } catch (e) {
//                 if (!mounted) return;
//                 setDialogState(() => saving = false);
//                 ScaffoldMessenger.of(context).showSnackBar(
//                   SnackBar(content: Text('Could not add device: $e')),
//                 );
//               }
//             }

//             return AlertDialog(
//               title: const Text('Add Kasa Plug by IP'),
//               content: Column(
//                 mainAxisSize: MainAxisSize.min,
//                 children: [
//                   TextField(
//                     controller: nameController,
//                     decoration: const InputDecoration(
//                       labelText: 'Display name (optional)',
//                     ),
//                   ),
//                   const SizedBox(height: 12),
//                   TextField(
//                     controller: ipController,
//                     decoration: const InputDecoration(
//                       labelText: 'IP address',
//                       hintText: '<device-ip>',
//                     ),
//                   ),
//                   const SizedBox(height: 12),
//                   Text(
//                     _useRealDevices
//                         ? 'This verifies the plug through the local Python Kasa bridge before saving it.'
//                         : 'This adds a mock plug only inside Flutter.',
//                     style: Theme.of(context).textTheme.bodySmall,
//                   ),
//                 ],
//               ),
//               actions: [
//                 TextButton(
//                   onPressed: saving ? null : () => Navigator.of(context).pop(),
//                   child: const Text('Cancel'),
//                 ),
//                 FilledButton(
//                   onPressed: saving ? null : addDevice,
//                   child: saving
//                       ? const SizedBox(
//                           width: 18,
//                           height: 18,
//                           child: CircularProgressIndicator(strokeWidth: 2),
//                         )
//                       : const Text('Add'),
//                 ),
//               ],
//             );
//           },
//         );
//       },
//     );
//   }

//   void _showError(String message) {
//     if (!mounted) return;
//     ScaffoldMessenger.of(context).showSnackBar(
//       SnackBar(content: Text(message), backgroundColor: Colors.red),
//     );
//   }

//   @override
//   Widget build(BuildContext context) {
//     return Scaffold(
//       appBar: AppBar(
//         title: const Text('Kasa Device Control'),
//         actions: [
//           Row(
//             children: [
//               Text(
//                 _useRealDevices ? 'REAL' : 'MOCK',
//                 style: TextStyle(
//                   fontWeight: FontWeight.bold,
//                   color: _useRealDevices ? Colors.green[800] : Colors.orange[800],
//                 ),
//               ),
//               Switch(
//                 value: _useRealDevices,
//                 onChanged: (value) {
//                   setState(() {
//                     _useRealDevices = value;
//                     _availableDevices = [];
//                   });
//                   _refreshDevices();
//                 },
//               ),
//             ],
//           ),
//         ],
//       ),
//       body: Column(
//         children: [
//           Container(
//             width: double.infinity,
//             color: Colors.black87,
//             padding: const EdgeInsets.all(16),
//             child: Column(
//               crossAxisAlignment: CrossAxisAlignment.start,
//               children: [
//                 const Text(
//                   'Safe testing flow',
//                   style: TextStyle(
//                     color: Colors.white,
//                     fontWeight: FontWeight.bold,
//                     fontSize: 16,
//                   ),
//                 ),
//                 const SizedBox(height: 8),
//                 Text(
//                   _useRealDevices
//                       ? 'Use one harmless plug first. Keep headset control disconnected until manual add, refresh, and toggle all work reliably from this screen.'
//                       : 'Mock mode is for UI testing only.',
//                   style: const TextStyle(color: Colors.white70),
//                 ),
//                 if (_statusMessage != null) ...[
//                   const SizedBox(height: 8),
//                   Text(
//                     _statusMessage!,
//                     style: const TextStyle(color: Colors.white70),
//                   ),
//                 ],
//               ],
//             ),
//           ),
//           Expanded(
//             child: _availableDevices.isEmpty
//                 ? Center(
//                     child: Padding(
//                       padding: const EdgeInsets.all(24),
//                       child: Column(
//                         mainAxisAlignment: MainAxisAlignment.center,
//                         children: [
//                           const Icon(Icons.power, size: 72, color: Colors.grey),
//                           const SizedBox(height: 16),
//                           const Text(
//                             'No plugs added yet',
//                             style: TextStyle(fontSize: 20, color: Colors.grey),
//                           ),
//                           const SizedBox(height: 16),
//                           FilledButton.icon(
//                             onPressed: _showAddDeviceDialog,
//                             icon: const Icon(Icons.add),
//                             label: const Text('Add by IP'),
//                           ),
//                           const SizedBox(height: 12),
//                           OutlinedButton.icon(
//                             onPressed: _isBusy ? null : _refreshDevices,
//                             icon: _isBusy
//                                 ? const SizedBox(
//                                     width: 16,
//                                     height: 16,
//                                     child: CircularProgressIndicator(strokeWidth: 2),
//                                   )
//                                 : const Icon(Icons.refresh),
//                             label: const Text('Refresh Registered Devices'),
//                           ),
//                         ],
//                       ),
//                     ),
//                   )
//                 : ListView.builder(
//                     padding: const EdgeInsets.all(16),
//                     itemCount: _availableDevices.length,
//                     itemBuilder: (context, index) {
//                       final device = _availableDevices[index];
//                       final isSelected = device.id == _selectedDeviceId;
//                       return Card(
//                         shape: RoundedRectangleBorder(
//                           borderRadius: BorderRadius.circular(12),
//                           side: BorderSide(
//                             color: isSelected ? Colors.blue : Colors.transparent,
//                             width: 2,
//                           ),
//                         ),
//                         margin: const EdgeInsets.only(bottom: 12),
//                         child: ListTile(
//                           leading: Icon(
//                             Icons.power,
//                             color: device.state ? Colors.green : Colors.grey,
//                             size: 36,
//                           ),
//                           title: Text(device.name),
//                           subtitle: Text('${device.model} • ${device.ip}'),
//                           trailing: Row(
//                             mainAxisSize: MainAxisSize.min,
//                             children: [
//                               Text(device.state ? 'ON' : 'OFF'),
//                               const SizedBox(width: 8),
//                               Switch(
//                                 value: device.state,
//                                 onChanged: _isBusy ? null : (_) => _toggleDevice(device),
//                               ),
//                               PopupMenuButton<String>(
//                                 onSelected: (value) {
//                                   if (value == 'remove') _removeDevice(device);
//                                   if (value == 'select') _saveSelectedDevice(device.id);
//                                 },
//                                 itemBuilder: (_) => const [
//                                   PopupMenuItem(value: 'select', child: Text('Use for BCI')),
//                                   PopupMenuItem(value: 'remove', child: Text('Remove')),
//                                 ],
//                               ),
//                             ],
//                           ),
//                           onTap: () => _saveSelectedDevice(device.id),
//                         ),
//                       );
//                     },
//                   ),
//           ),
//           Padding(
//             padding: const EdgeInsets.all(16),
//             child: Column(
//               children: [
//                 Row(
//                   children: [
//                     Expanded(
//                       child: OutlinedButton.icon(
//                         onPressed: _isBusy ? null : _refreshDevices,
//                         icon: const Icon(Icons.search),
//                         label: const Text('Scan'),
//                       ),
//                     ),
//                     const SizedBox(width: 12),
//                     Expanded(
//                       child: OutlinedButton.icon(
//                         onPressed: _showAddDeviceDialog,
//                         icon: const Icon(Icons.add),
//                         label: const Text('Add by IP'),
//                       ),
//                     ),
//                   ],
//                 ),
//                 const SizedBox(height: 12),
//                 Row(
//                   children: [
//                     Expanded(
//                       child: OutlinedButton.icon(
//                         onPressed: _isBusy ? null : _refreshSelected,
//                         icon: const Icon(Icons.refresh),
//                         label: const Text('Refresh Selected'),
//                       ),
//                     ),
//                     const SizedBox(width: 12),
//                     Expanded(
//                       child: FilledButton.icon(
//                         onPressed: _isBusy ? null : _testSelected,
//                         icon: const Icon(Icons.bolt),
//                         label: const Text('Test Selected'),
//                       ),
//                     ),
//                   ],
//                 ),
//                 const SizedBox(height: 8),
//                 Text(
//                   _selectedDevice == null
//                       ? 'Select one plug to make it the only BCI target later.'
//                       : 'Selected for BCI: ${_selectedDevice!.name}',
//                   style: Theme.of(context).textTheme.bodySmall,
//                 ),
//               ],
//             ),
//           ),
//         ],
//       ),
//     );
//   }
// }

// class KasaDevice {
//   final String id;
//   final String name;
//   final String ip;
//   final String model;
//   bool state;

//   KasaDevice({
//     required this.id,
//     required this.name,
//     required this.ip,
//     required this.model,
//     required this.state,
//   });

//   factory KasaDevice.fromJson(Map<String, dynamic> json) {
//     return KasaDevice(
//       id: json['id'] as String,
//       name: (json['name'] as String?) ?? 'Kasa Plug',
//       ip: (json['ip'] as String?) ?? '',
//       model: (json['model'] as String?) ?? 'Unknown',
//       state: (json['state'] as bool?) ?? false,
//     );
//   }
// }
