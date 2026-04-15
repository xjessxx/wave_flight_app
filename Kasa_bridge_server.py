"""
Kasa Smart Plug Bridge Server
==============================
Compatible with python-kasa 0.7+ (including 0.10.x)
Uses Discover.discover_single() — the correct modern API.

    pip install flask flask-cors python-kasa
    python kasa_bridge.py

Port: 5273
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import asyncio
import json
import os
import hashlib
import sys

try:
    from kasa import Discover, Credentials
    import kasa as _kasa_module
    KASA_AVAILABLE = True
    print(f"[kasa_bridge] python-kasa {_kasa_module.__version__} loaded OK")
except ImportError:
    KASA_AVAILABLE = False
    _kasa_module = None
    print("WARNING: python-kasa not installed. Run: pip install python-kasa")

app = Flask(__name__)
CORS(app)

# ============================================================================
# STATE
# ============================================================================

_credentials = None        # {'username': str, 'password': str} — RAM only, never persisted
_registered_devices = {}   # device_id -> {id, name, ip, model, state}

DEVICES_FILE = os.path.join(os.path.dirname(__file__), '.kasa_devices.json')


def _load_devices():
    global _registered_devices
    if os.path.exists(DEVICES_FILE):
        try:
            with open(DEVICES_FILE) as f:
                data = json.load(f)
            # Scrub any accidentally-saved credential fields
            for v in data.values():
                for key in ('password', 'kasa_password', 'username', 'kasa_username', 'token'):
                    v.pop(key, None)
            _registered_devices = data
            print(f"[kasa_bridge] Loaded {len(_registered_devices)} device(s) from registry")
        except Exception as e:
            print(f"[kasa_bridge] Could not load devices file: {e}")
            _registered_devices = {}


def _save_devices():
    """Persist IPs and names only — credentials are never written to disk."""
    safe = {
        k: {fk: v.get(fk, '') for fk in ('id', 'ip', 'name', 'model', 'state')}
        for k, v in _registered_devices.items()
    }
    try:
        with open(DEVICES_FILE, 'w') as f:
            json.dump(safe, f, indent=2)
    except Exception as e:
        print(f"[kasa_bridge] Could not save devices: {e}")


def _make_id(ip: str) -> str:
    return hashlib.md5(ip.encode()).hexdigest()[:12]


def _run(coro):
    """Run an async coroutine synchronously (Flask is sync)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _connect(ip: str):
    """
    Connect to a plug using the modern Discover.discover_single() API.
    Works with python-kasa 0.7+ including 0.10.x.
    Credentials are optional for older IOT devices that don't require auth.
    """
    if _credentials:
        device = await Discover.discover_single(
            ip,
            username=_credentials['username'],
            password=_credentials['password'],
        )
    else:
        # Try without credentials for older legacy devices
        device = await Discover.discover_single(ip)
    await device.update()
    return device


def _serialize(device_id: str, device=None) -> dict:
    reg = _registered_devices[device_id]
    result = {
        'id': device_id,
        'name': reg.get('name') or reg['ip'],
        'ip': reg['ip'],
        'model': reg.get('model', 'Kasa Plug'),
        'state': reg.get('state', False),
    }
    if device is not None:
        result['state'] = device.is_on
        result['model'] = getattr(device, 'model', None) or 'Kasa Plug'
        result['name'] = reg.get('name') or getattr(device, 'alias', None) or reg['ip']
    return result


def _friendly(exc: Exception) -> str:
    msg = str(exc)
    if 'authentication' in msg.lower() or 'login' in msg.lower() or '1003' in msg:
        return "Authentication failed — check your Kasa email and password"
    if 'timed out' in msg.lower() or 'timeout' in msg.lower():
        return f"Timed out reaching plug — check IP and that it's on the same Wi-Fi network"
    if 'connection refused' in msg.lower():
        return f"Connection refused at that IP — is the plug powered on and on this network?"
    if 'no devices found' in msg.lower():
        return f"No Kasa device responded at that IP address"
    return msg


# ============================================================================
# HEALTH
# ============================================================================

@app.route('/health', methods=['GET'])
@app.route('/status', methods=['GET'])
def status():
    ver = getattr(_kasa_module, '__version__', 'unknown') if KASA_AVAILABLE else 'not installed'
    return jsonify({
        'ok': True,
        'kasa_available': KASA_AVAILABLE,
        'kasa_version': ver,
        'credentials_configured': _credentials is not None,
        'registered_device_count': len(_registered_devices),
    })


@app.route('/config/status', methods=['GET'])
def config_status():
    return jsonify({
        'credentials_configured': _credentials is not None,
        'device_count': len(_registered_devices),
    })


# ============================================================================
# CREDENTIALS  (RAM only — never written to disk)
# ============================================================================

@app.route('/credentials/save', methods=['POST'])
def save_credentials():
    global _credentials
    body = request.get_json(force=True, silent=True) or {}
    username = (body.get('username') or '').strip()
    password = body.get('password') or ''
    if not username or not password:
        return jsonify({'error': 'username and password are required'}), 400
    _credentials = {'username': username, 'password': password}
    print(f"[kasa_bridge] Credentials saved for '{username}' (password NOT logged)")
    return jsonify({'message': 'Credentials saved in memory only'})


@app.route('/credentials/test', methods=['POST'])
def test_credentials():
    if not _credentials:
        return jsonify({'error': 'Save credentials first'}), 400
    if not KASA_AVAILABLE:
        return jsonify({'error': 'python-kasa not installed'}), 500

    body = request.get_json(force=True, silent=True) or {}
    ip = (body.get('ip') or '').strip()
    if not ip:
        return jsonify({'error': 'ip is required'}), 400

    try:
        device = _run(_connect(ip))
    except Exception as e:
        return jsonify({'error': _friendly(e)}), 400

    # Auto-register on successful test
    device_id = _make_id(ip)
    if device_id not in _registered_devices:
        _registered_devices[device_id] = {
            'id': device_id,
            'ip': ip,
            'name': getattr(device, 'alias', None) or ip,
            'model': getattr(device, 'model', None) or 'Kasa Plug',
            'state': device.is_on,
        }
        _save_devices()

    return jsonify(_serialize(device_id, device))


@app.route('/credentials/clear', methods=['POST'])
def clear_credentials():
    global _credentials
    _credentials = None
    print("[kasa_bridge] Credentials cleared from memory")
    return jsonify({'message': 'Credentials cleared'})


# ============================================================================
# DEVICES
# ============================================================================

@app.route('/devices', methods=['GET'])
def list_devices():
    result = []
    for device_id, reg in list(_registered_devices.items()):
        entry = _serialize(device_id)
        if KASA_AVAILABLE and _credentials:
            try:
                device = _run(_connect(reg['ip']))
                entry = _serialize(device_id, device)
                _registered_devices[device_id]['state'] = device.is_on
            except Exception:
                pass  # Serve cached state on failure
        result.append(entry)
    return jsonify(result)


@app.route('/devices/register', methods=['POST'])
def register_device():
    if not _credentials:
        return jsonify({'error': 'Save credentials before adding a device'}), 400
    if not KASA_AVAILABLE:
        return jsonify({'error': 'python-kasa not installed'}), 500

    body = request.get_json(force=True, silent=True) or {}
    ip = (body.get('ip') or '').strip()
    custom_name = (body.get('name') or '').strip() or None
    if not ip:
        return jsonify({'error': 'ip is required'}), 400

    try:
        device = _run(_connect(ip))
    except Exception as e:
        return jsonify({'error': _friendly(e)}), 400

    device_id = _make_id(ip)
    _registered_devices[device_id] = {
        'id': device_id,
        'ip': ip,
        'name': custom_name or getattr(device, 'alias', None) or ip,
        'model': getattr(device, 'model', None) or 'Kasa Plug',
        'state': device.is_on,
    }
    _save_devices()
    print(f"[kasa_bridge] Registered '{_registered_devices[device_id]['name']}' at {ip}")
    return jsonify(_serialize(device_id, device))


@app.route('/devices/<device_id>', methods=['GET'])
def get_device(device_id):
    if device_id not in _registered_devices:
        return jsonify({'error': 'Device not found'}), 404
    if KASA_AVAILABLE and _credentials:
        try:
            device = _run(_connect(_registered_devices[device_id]['ip']))
            _registered_devices[device_id]['state'] = device.is_on
            _save_devices()
            return jsonify(_serialize(device_id, device))
        except Exception as e:
            return jsonify({'error': _friendly(e)}), 400
    return jsonify(_serialize(device_id))


@app.route('/devices/<device_id>/toggle', methods=['POST'])
def toggle_device(device_id):
    if device_id not in _registered_devices:
        return jsonify({'error': 'Device not found'}), 404
    if not KASA_AVAILABLE:
        return jsonify({'error': 'python-kasa not installed'}), 500
    if not _credentials:
        return jsonify({'error': 'No credentials saved'}), 400

    reg = _registered_devices[device_id]

    async def _toggle():
        device = await _connect(reg['ip'])
        if device.is_on:
            await device.turn_off()
        else:
            await device.turn_on()
        await device.update()
        return device

    try:
        device = _run(_toggle())
        _registered_devices[device_id]['state'] = device.is_on
        _save_devices()
        state_str = 'ON' if device.is_on else 'OFF'
        print(f"[kasa_bridge] Toggled '{reg['name']}' -> {state_str}")
        return jsonify(_serialize(device_id, device))
    except Exception as e:
        return jsonify({'error': _friendly(e)}), 400


@app.route('/devices/<device_id>', methods=['DELETE'])
def remove_device(device_id):
    if device_id not in _registered_devices:
        return jsonify({'error': 'Device not found'}), 404
    name = _registered_devices.pop(device_id).get('name', device_id)
    _save_devices()
    print(f"[kasa_bridge] Removed '{name}'")
    return jsonify({'message': f'Removed {name}'})


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    _load_devices()

    # Warn if kasa_config.json with a plaintext password exists nearby
    cfg_path = os.path.join(os.path.dirname(__file__), 'kasa_config.json')
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path) as f:
                cfg = json.load(f)
            if cfg.get('kasa_password') or cfg.get('password'):
                print("\n" + "!" * 60)
                print("SECURITY WARNING: kasa_config.json has a plaintext password.")
                print("Delete it — credentials should only live in process memory.")
                print(f"Path: {cfg_path}")
                print("!" * 60 + "\n")
        except Exception:
            pass

    ver = getattr(_kasa_module, '__version__', '?') if KASA_AVAILABLE else 'not installed'
    print("\n" + "=" * 60)
    print("     KASA SMART PLUG BRIDGE  (port 5273)")
    print(f"     python-kasa version: {ver}")
    print("=" * 60)
    print("Endpoints:")
    print("  GET    /status                  Health + version")
    print("  GET    /config/status           Credential + device count")
    print("  POST   /credentials/save        Save Kasa credentials (RAM only)")
    print("  POST   /credentials/test        Test against a plug IP")
    print("  POST   /credentials/clear       Wipe credentials")
    print("  GET    /devices                 List registered devices")
    print("  POST   /devices/register        Add plug by IP")
    print("  GET    /devices/<id>            Get single device state")
    print("  POST   /devices/<id>/toggle     Toggle plug on/off")
    print("  DELETE /devices/<id>            Remove plug")
    print("=" * 60 + "\n")

    app.run(host='0.0.0.0', port=5273, debug=False, threaded=True)
