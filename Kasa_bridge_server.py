# """
# Kasa Bridge Server
# ==================
# HTTP bridge between the Flutter app and TP-Link Kasa smart plugs.

# Handles all known python-kasa API variants automatically by inspecting
# the installed library's signatures at startup.

# Requirements:  pip install flask kasa
# Run:           python Kasa_bridge_server.py   (default port 5273)
# """

# from __future__ import annotations

# import asyncio
# import inspect
# import json
# import os
# import re
# import subprocess
# from ipaddress import ip_address
# from pathlib import Path
# from typing import Any, Dict

# from flask import Flask, jsonify, request

# app      = Flask(__name__)
# PORT     = int(os.environ.get("KASA_BRIDGE_PORT", "5273"))
# KASA_CMD = os.environ.get("KASA_CLI", "kasa")

# BASE_DIR     = Path(__file__).resolve().parent
# DEVICES_FILE = BASE_DIR / "kasa_devices.json"
# CONFIG_FILE  = BASE_DIR / "kasa_config.json"


# # ---------------------------------------------------------------------------
# # Detect exact python-kasa API once at startup
# # ---------------------------------------------------------------------------

# def _detect_kasa_api() -> str:
#     """
#     Inspects the installed kasa library to pick the right connection method.
#     Prints diagnostic info so you can see exactly what was detected.
#     """
#     try:
#         import kasa
#         print(f"[kasa-bridge] kasa version      : {kasa.__version__}")
#         print(f"[kasa-bridge] Has Device        : {hasattr(kasa, 'Device')}")
#         print(f"[kasa-bridge] Has DeviceConfig  : {hasattr(kasa, 'DeviceConfig')}")
#         print(f"[kasa-bridge] Has Credentials   : {hasattr(kasa, 'Credentials')}")
#         print(f"[kasa-bridge] Has SmartPlug     : {hasattr(kasa, 'SmartPlug')}")

#         # kasa >= 0.7: Device.connect() is the primary entrypoint
#         if hasattr(kasa, "Device") and hasattr(kasa.Device, "connect"):
#             sig    = inspect.signature(kasa.Device.connect)
#             params = list(sig.parameters.keys())
#             print(f"[kasa-bridge] Device.connect params: {params}")

#             if "config" in params and hasattr(kasa, "DeviceConfig"):
#                 return "device_config"   # kasa 0.7.x latest
#             if "credentials" in params:
#                 return "device_creds"    # kasa 0.7.x early
#             # connect exists but signature unknown — try DeviceConfig
#             if hasattr(kasa, "DeviceConfig"):
#                 return "device_config"
#             return "device_creds"

#         # kasa 0.5-0.6: SmartPlug constructor
#         if hasattr(kasa, "SmartPlug"):
#             sig    = inspect.signature(kasa.SmartPlug.__init__)
#             params = list(sig.parameters.keys())
#             print(f"[kasa-bridge] SmartPlug.__init__ params: {params}")
#             if "credentials" in params:
#                 return "smartplug_new"
#             return "smartplug_old"

#         return "cli"

#     except ImportError:
#         print("[kasa-bridge] kasa library not found — falling back to CLI")
#         return "cli"
#     except Exception as exc:
#         print(f"[kasa-bridge] API detection error: {exc} — falling back to CLI")
#         return "cli"


# KASA_API = _detect_kasa_api()
# print(f"[kasa-bridge] *** Using API mode: {KASA_API} ***")


# # ---------------------------------------------------------------------------
# # Persistence helpers
# # ---------------------------------------------------------------------------

# def _read_json(path: Path, default: Any) -> Any:
#     if not path.exists():
#         return default
#     try:
#         return json.loads(path.read_text(encoding="utf-8"))
#     except Exception:
#         return default


# def _write_json(path: Path, data: Any) -> None:
#     path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# def _load_devices() -> Dict[str, Dict[str, Any]]:
#     data = _read_json(DEVICES_FILE, {})
#     return data if isinstance(data, dict) else {}


# def _load_config() -> Dict[str, Any]:
#     defaults: Dict[str, Any] = {"kasa_username": "", "kasa_password": ""}
#     data = _read_json(CONFIG_FILE, defaults)
#     return data if isinstance(data, dict) else defaults


# CONFIG:  Dict[str, Any]            = _load_config()
# DEVICES: Dict[str, Dict[str, Any]] = _load_devices()


# def _save_devices() -> None:
#     _write_json(DEVICES_FILE, DEVICES)


# def _save_config() -> None:
#     _write_json(CONFIG_FILE, CONFIG)


# # ---------------------------------------------------------------------------
# # Credential helpers
# # ---------------------------------------------------------------------------

# def _get_username() -> str:
#     return (str(CONFIG.get("kasa_username", "")).strip() or
#             str(os.environ.get("KASA_USERNAME", "")).strip())


# def _get_password() -> str:
#     return (str(CONFIG.get("kasa_password", "")).strip() or
#             str(os.environ.get("KASA_PASSWORD", "")).strip())


# def _credentials_configured() -> bool:
#     return bool(_get_username() and _get_password())


# def _device_id(ip: str) -> str:
#     return f"kasa_{ip.replace('.', '_')}"


# def _is_private_ip(value: str) -> bool:
#     try:
#         return ip_address(value).is_private
#     except ValueError:
#         return False


# # ---------------------------------------------------------------------------
# # Async device helpers — all API variants
# # ---------------------------------------------------------------------------

# async def _connect_and_get_info(ip: str) -> Dict[str, Any]:
#     """
#     Connect to a device, read its state, disconnect cleanly, return info dict.
#     Handles all API variants. Raises on failure with a descriptive message.
#     """
#     username = _get_username()
#     password = _get_password()

#     print(f"[kasa-bridge] Connecting to {ip} via mode={KASA_API}")

#     try:
#         if KASA_API == "device_config":
#             import kasa
#             creds  = kasa.Credentials(username=username, password=password)
#             config = kasa.DeviceConfig(host=ip, credentials=creds)
#             # Device.connect returns an already-updated device
#             device = await kasa.Device.connect(config=config)
#             try:
#                 info = _extract_info(device, ip)
#             finally:
#                 try:
#                     await device.disconnect()
#                 except Exception:
#                     pass
#             return info

#         elif KASA_API == "device_creds":
#             import kasa
#             creds  = kasa.Credentials(username=username, password=password)
#             device = await kasa.Device.connect(host=ip, credentials=creds)
#             try:
#                 info = _extract_info(device, ip)
#             finally:
#                 try:
#                     await device.disconnect()
#                 except Exception:
#                     pass
#             return info

#         elif KASA_API == "smartplug_new":
#             from kasa import SmartPlug, Credentials
#             plug = SmartPlug(ip,
#                              credentials=Credentials(username=username,
#                                                      password=password))
#             await plug.update()
#             return _extract_info(plug, ip)

#         elif KASA_API == "smartplug_old":
#             from kasa import SmartPlug
#             plug = SmartPlug(ip)
#             await plug.update()
#             return _extract_info(plug, ip)

#         else:
#             # CLI fallback
#             return _cli_get_device_info(ip)

#     except Exception as exc:
#         # Re-raise with the IP included so error messages are clear
#         raise RuntimeError(f"Could not reach {ip}: {exc}") from exc


# async def _connect_and_set_state(ip: str, turn_on: bool) -> bool:
#     """Connect, set relay state, return new state."""
#     username = _get_username()
#     password = _get_password()

#     if KASA_API == "cli":
#         _cli_run(ip, "on" if turn_on else "off")
#         return turn_on

#     try:
#         if KASA_API == "device_config":
#             import kasa
#             creds  = kasa.Credentials(username=username, password=password)
#             config = kasa.DeviceConfig(host=ip, credentials=creds)
#             device = await kasa.Device.connect(config=config)
#             try:
#                 if turn_on:
#                     await device.turn_on()
#                 else:
#                     await device.turn_off()
#                 await device.update()
#                 return device.is_on
#             finally:
#                 try:
#                     await device.disconnect()
#                 except Exception:
#                     pass

#         elif KASA_API == "device_creds":
#             import kasa
#             creds  = kasa.Credentials(username=username, password=password)
#             device = await kasa.Device.connect(host=ip, credentials=creds)
#             try:
#                 if turn_on:
#                     await device.turn_on()
#                 else:
#                     await device.turn_off()
#                 await device.update()
#                 return device.is_on
#             finally:
#                 try:
#                     await device.disconnect()
#                 except Exception:
#                     pass

#         else:
#             from kasa import SmartPlug
#             kwargs = {}
#             if KASA_API == "smartplug_new":
#                 from kasa import Credentials
#                 kwargs["credentials"] = Credentials(username=username,
#                                                     password=password)
#             plug = SmartPlug(ip, **kwargs)
#             await plug.update()
#             if turn_on:
#                 await plug.turn_on()
#             else:
#                 await plug.turn_off()
#             await plug.update()
#             return plug.is_on

#     except Exception as exc:
#         raise RuntimeError(f"Could not control {ip}: {exc}") from exc


# async def _connect_and_toggle(ip: str, current_state: bool) -> bool:
#     return await _connect_and_set_state(ip, not current_state)


# def _extract_info(device: Any, ip: str) -> Dict[str, Any]:
#     return {
#         "id":    _device_id(ip),
#         "name":  getattr(device, "alias", None) or ip,
#         "ip":    ip,
#         "model": getattr(device, "model", None) or "Kasa Plug",
#         "state": bool(getattr(device, "is_on", False)),
#         "port":  80,
#     }


# def _run(coro):
#     """Run an async coroutine from synchronous Flask context."""
#     return asyncio.run(coro)


# # ---------------------------------------------------------------------------
# # CLI fallback helpers
# # ---------------------------------------------------------------------------

# _DEVICE_HEADER_RE = re.compile(
#     r"^==\s*(?P<n>.+?)\s*-\s*(?P<model>[^=]+?)\s*==$", re.MULTILINE)
# _HOST_RE  = re.compile(r"^Host:\s*(?P<host>.+)$",               re.MULTILINE)
# _STATE_RE = re.compile(r"^Device state:\s*(?P<s>True|False)$",  re.MULTILINE)


# def _cli_run(ip: str, command: str) -> str:
#     args = [KASA_CMD, "--host", ip]
#     if _get_username():
#         args += ["--username", _get_username()]
#     if _get_password():
#         args += ["--password", _get_password()]
#     args.append(command)
#     result = subprocess.run(args, capture_output=True, text=True, timeout=30)
#     if result.returncode != 0:
#         detail = (result.stderr or result.stdout or
#                   f"kasa CLI exited {result.returncode}").strip()
#         raise RuntimeError(detail)
#     return result.stdout


# def _cli_get_device_info(ip: str) -> Dict[str, Any]:
#     output = _cli_run(ip, "state")
#     header = _DEVICE_HEADER_RE.search(output)
#     host   = _HOST_RE.search(output)
#     state  = _STATE_RE.search(output)
#     return {
#         "id":    _device_id(ip),
#         "name":  header.group("n").strip() if header else ip,
#         "ip":    host.group("host").strip() if host else ip,
#         "model": header.group("model").strip() if header else "Kasa Plug",
#         "state": state.group("s") == "True" if state else False,
#         "port":  80,
#     }


# # ---------------------------------------------------------------------------
# # Routes — health & config
# # ---------------------------------------------------------------------------

# @app.get("/health")
# def health() -> Any:
#     return jsonify({
#         "ok":                    True,
#         "bridge":                "kasa-python-bridge",
#         "api_mode":              KASA_API,
#         "credentialsConfigured": _credentials_configured(),
#         "deviceCount":           len(DEVICES),
#     })


# @app.get("/config/status")
# def config_status() -> Any:
#     return jsonify({
#         "ok":                    True,
#         "credentialsConfigured": _credentials_configured(),
#         "hasStoredUsername":     bool(str(CONFIG.get("kasa_username", "")).strip()),
#         "bridgeUrlHint":         f"http://localhost:{PORT}",
#         "deviceCount":           len(DEVICES),
#     })


# @app.post("/config/credentials")
# def save_credentials() -> Any:
#     body     = request.get_json(silent=True) or {}
#     username = str(body.get("username", "")).strip()
#     password = str(body.get("password", "")).strip()
#     if not username or not password:
#         return jsonify({"ok": False,
#                         "error": "Username and password are required."}), 400
#     CONFIG["kasa_username"] = username
#     CONFIG["kasa_password"] = password
#     _save_config()
#     return jsonify({"ok": True, "credentialsConfigured": True})


# @app.post("/config/test")
# def test_credentials() -> Any:
#     body = request.get_json(silent=True) or {}
#     ip   = str(body.get("ip", "")).strip()
#     if not ip:
#         return jsonify({"ok": False, "error": "A device IP is required."}), 400
#     if not _is_private_ip(ip):
#         return jsonify({"ok": False,
#                         "error": "Please provide a valid private LAN IP."}), 400
#     if not _credentials_configured():
#         return jsonify({"ok": False,
#                         "error": "Save Kasa credentials first."}), 400
#     try:
#         device = _run(_connect_and_get_info(ip))
#         return jsonify({"ok": True, "device": device})
#     except Exception as exc:
#         return jsonify({"ok": False, "error": str(exc)}), 502


# @app.post("/config/clear")
# def clear_credentials() -> Any:
#     CONFIG["kasa_username"] = ""
#     CONFIG["kasa_password"] = ""
#     _save_config()
#     return jsonify({"ok": True, "credentialsConfigured": False})


# # ---------------------------------------------------------------------------
# # Routes — devices
# # ---------------------------------------------------------------------------

# @app.get("/devices")
# def list_devices() -> Any:
#     return jsonify({"devices": list(DEVICES.values())})


# @app.post("/devices/register")
# def register_device() -> Any:
#     body = request.get_json(silent=True) or {}
#     ip   = str(body.get("ip", "")).strip()
#     name = str(body.get("name", "")).strip() or None
#     if not ip:
#         return jsonify({"ok": False, "error": "IP address is required."}), 400
#     if not _is_private_ip(ip):
#         return jsonify({"ok": False,
#                         "error": "Please provide a valid private LAN IP."}), 400
#     if not _credentials_configured():
#         return jsonify({"ok": False,
#                         "error": "Save Kasa credentials first."}), 400
#     try:
#         device = _run(_connect_and_get_info(ip))
#         if name:
#             device["name"] = name
#         DEVICES[device["id"]] = device
#         _save_devices()
#         return jsonify({"ok": True, "device": device})
#     except Exception as exc:
#         return jsonify({"ok": False, "error": str(exc)}), 502


# @app.get("/devices/<device_id>/state")
# def get_device_state(device_id: str) -> Any:
#     device = DEVICES.get(device_id)
#     if not device:
#         return jsonify({"ok": False, "error": "Device not found."}), 404
#     try:
#         fresh = _run(_connect_and_get_info(device["ip"]))
#         fresh["name"] = device.get("name", fresh["name"])
#         DEVICES[device_id] = fresh
#         _save_devices()
#         return jsonify({"ok": True, "device": fresh})
#     except Exception as exc:
#         return jsonify({"ok": False, "error": str(exc)}), 502


# @app.post("/devices/<device_id>/toggle")
# def toggle(device_id: str) -> Any:
#     device = DEVICES.get(device_id)
#     if not device:
#         return jsonify({"ok": False, "error": "Device not found."}), 404
#     try:
#         new_state = _run(_connect_and_toggle(device["ip"],
#                                              device.get("state", False)))
#         device["state"] = new_state
#         DEVICES[device_id] = device
#         _save_devices()
#         return jsonify({"ok": True, "device": device})
#     except Exception as exc:
#         return jsonify({"ok": False, "error": str(exc)}), 502


# @app.post("/devices/<device_id>/on")
# def turn_on(device_id: str) -> Any:
#     return _set_device_state(device_id, True)


# @app.post("/devices/<device_id>/off")
# def turn_off(device_id: str) -> Any:
#     return _set_device_state(device_id, False)


# def _set_device_state(device_id: str, turn_on: bool) -> Any:
#     device = DEVICES.get(device_id)
#     if not device:
#         return jsonify({"ok": False, "error": "Device not found."}), 404
#     try:
#         new_state = _run(_connect_and_set_state(device["ip"], turn_on))
#         device["state"] = new_state
#         DEVICES[device_id] = device
#         _save_devices()
#         return jsonify({"ok": True, "device": device})
#     except Exception as exc:
#         return jsonify({"ok": False, "error": str(exc)}), 502


# @app.delete("/devices/<device_id>")
# def remove_device(device_id: str) -> Any:
#     DEVICES.pop(device_id, None)
#     _save_devices()
#     return jsonify({"ok": True})


# # ---------------------------------------------------------------------------
# # Entry point
# # ---------------------------------------------------------------------------

# if __name__ == "__main__":
#     print(f"Kasa Bridge  : http://localhost:{PORT}")
#     print(f"API mode     : {KASA_API}")
#     print(f"Credentials  : {'configured' if _credentials_configured() else 'NOT set'}")
#     print(f"Devices      : {len(DEVICES)} registered")
#     app.run(host="localhost", port=PORT, debug=False)


#==========================================================

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
