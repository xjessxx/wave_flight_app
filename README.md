# WaveFlight: BCI for Accessibility

**Brain-Computer Interface (BCI) Motor Imagery system for smart home control via EEG signal processing.**

A research-based Flutter + Python application that enables users to control smart home devices (TP-Link Kasa plugs) using motor imagery—imagining left/right hand movement detected through EEG signals. Ideal for accessibility use cases where traditional interfaces are difficult or impossible to use.

---

## 🧠 Overview

WaveFlight implements real-time motor imagery classification on the NeuroPawn EEG headset. After a brief calibration and training phase, users can trigger smart home actions by imagining hand movements, detected with high confidence through event-related desynchronization (ERD) analysis.

**Based on:** Research in motor imagery BCI classification (see references)

### 🧠 Neuroethics & Responsible Innovation

This project emphasizes the critical importance of **neuroethics in neurotech development**. As brain-computer interfaces increasingly integrate with consumer applications, responsible design practices are essential. WaveFlight prioritizes user privacy (EEG data processed locally, never stored externally), informed consent, and individual autonomy in BCI interactions. We believe that accessibility technologies must be developed with careful consideration of cognitive rights, data protection, and equitable access—ensuring that motor imagery BCIs benefit all users, not just those with resources, while maintaining ethical standards that protect neurological data as the deeply personal information it represents.

---

## Features

- **User Authentication** — Firebase-based sign-in with Google OAuth (configurable)
- **EEG Baseline Calibration** — 60-second relaxed state recording for individual baseline
- **Motor Imagery Training** — 40-trial guided training session for right/left hand imagery
- **Real-Time Detection** — Live classification of motor imagery with confidence scoring
- **Smart Home Integration** — Control TP-Link Kasa smart plugs via motion intention
- **Development Mode** — Skip auth for desktop/emulator testing
- **Dark/Light Theme** — System-aware Material Design 3 UI

---

## Architecture

### Frontend (Flutter)
- **Authentication**: Firebase + Google Sign-In (optional for Android production)
- **Screens**:
  - `SigninScreen` — User authentication
  - `HomeScreen` — Device discovery & BCI control dashboard
  - `CalibrationScreen` — Baseline collection (60s)
  - `TrainingScreen` — Motor imagery training (40 trials)
  - `DeviceControlScreen` — Kasa smart plug interface
  - `ResetPasswordScreen` — Firebase password recovery

### Backend (Python)

#### BCI Motor Imagery System (`python_bci/bci_motor_imagery_complete.py`)
- **EEG Streaming** — BrainFlow integration for Neuropawn/OpenBCI hardware
- **Signal Processing** — Bandpass filtering (1-50 Hz), notch filtering (60 Hz)
- **Feature Extraction** — Power spectral density (PSD) in mu (8-12 Hz) and beta (13-30 Hz) bands
- **Baseline Calibration** — Individual resting-state EEG recording
- **Classifier Training** — Linear Discriminant Analysis (LDA) or SVM on motor imagery trials
- **Real-Time Detection** — Sliding window ERD classification with confidence thresholding
- **Bluetooth Triggers** — Optional Bluetooth connection to paired Android device

#### BCI Flask Bridge (`python_bci/bci_flutter_bridge.py`)
- HTTP server (`localhost:5000`) connecting Flutter app to BCI pipeline
- Endpoints:
  - `/status` — System health
  - `/system/initialize` — Initialize EEG hardware
  - `/calibration/start` — Begin baseline collection
  - `/training/start` — Begin motor imagery training
  - `/detection/start` — Enable real-time classification
  - `/detection/stop` — Disable classification
  - Polling-based progress updates for calibration/training

#### Kasa Smart Plug Bridge (`Kasa_bridge_server.py`)
- HTTP server (`localhost:5273`) for TP-Link Kasa device management
- Credentials stored in Python process (never transmitted externally)
- Endpoints for device discovery, state toggling, configuration

### Communication Flow
```
Flutter App → HTTP → BCI Bridge ← BrainFlow ← NeuroPawn EEG Headset
Flutter App → HTTP → Kasa Bridge → Kasa Cloud API → Smart Plugs
```

---

## Requirements

### Hardware
- **NeuroPawn Biopotential EEG Headset Kit** (8-channel)
  - Serial connection via USB or Bluetooth
  - Sampling rate: 125 Hz
  - Channels: 3 (C3), 4 (C4) for motor imagery

### Software
- **Flutter**: 3.6.2+
- **Dart**: 3.6.2+
- **Python**: 3.8+
- **Android SDK** (for device testing)

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
# Clone repository
git clone <repo-url>
cd wave_flight_app

# Install Flutter dependencies
flutter pub get

# Install Python dependencies
cd python_bci
pip install -r requirements.txt

# If planning real Kasa integration:
pip install flask flask-cors python-kasa
```

### 2. Update Configuration

Create `kasa_config.json` from the example:
```bash
cp kasa_config.json kasa_config.json.bak
# Edit kasa_config.json with your TP-Link Kasa account credentials
```

### 3. Run the BCI Bridge (Python Terminal)

```bash
cd python_bci
python bci_flutter_bridge.py
```

Expected output:
```
[bci_bridge] Initializing BCI system...
[bci_bridge] Listening on http://localhost:5000
```

### 4. Run Kasa Bridge (Optional, Python Terminal)

```bash
python ../Kasa_bridge_server.py
```

Expected output:
```
[kasa_bridge] Kasa version: 0.7.0+
[kasa_bridge] Listening on http://localhost:5273
```

### 5. Run Flutter App

```bash
# Desktop (Windows/Linux/Mac) - skips auth, goes to home screen
flutter run -d windows

# Android device/emulator - shows login screen (Firebase optional)
flutter run -d <device-id> \
  --dart-define KASA_BRIDGE_URL=http://<computer-ip>:5273 \
  --dart-define BCI_BRIDGE_URL=http://<computer-ip>:5000
```

---

## Project Structure

```
wave_flight_app/
├── lib/
│   ├── main.dart                      # Entry point, routing setup
│   ├── firebase_options.dart          # Firebase config (--dart-define)
│   ├── screens/
│   │   ├── signin_screen.dart         # Firebase authentication
│   │   ├── signup_screen.dart         # User registration
│   │   ├── reset_password.dart        # Password recovery
│   │   ├── home_screen.dart           # Dashboard, device selection, BCI status
│   │   ├── calibration_screen.dart    # 60s baseline collection UI
│   │   ├── training_screen.dart       # 40-trial motor imagery training UI
│   │   ├── device_control_screen.dart # Kasa smart plug UI
│   │   ├── auth_widgets.dart          # Reusable auth components
│   │   └── [...other screens]
│   ├── services/
│   │   ├── bci_service.dart           # HTTP client for BCI bridge
│   │   └── kasa_service.dart          # HTTP client for Kasa bridge
│   └── reusable_widgets/
│       └── reusable_widget.dart       # Shared UI components
├── python_bci/
│   ├── bci_motor_imagery_complete.py  # Core EEG processing & classification
│   ├── bci_flutter_bridge.py          # Flask HTTP server (→ Flutter)
│   ├── requirements.txt               # Python dependencies
│   └── eeg_logs/                      # Logged EEG data (for analysis)
├── Kasa_bridge_server.py              # Kasa smart plug bridge (optional)
├── kasa_config.json                   # Kasa credentials config (update with yours)
├── pubspec.yaml                       # Flutter dependencies
├── analysis_options.yaml              # Dart linting rules
└── README.md                          # This file
```

---

## Configuration

### Enable/Disable Features

**Development Mode** (skip Firebase auth):
```dart
// In lib/main.dart, set:
const bool enableFirebaseAuth = false;  // true for production
```

**BCI & Kasa URLs**:
```bash
# Desktop dev (hardcoded):
# BCI: http://localhost:5000
# Kasa: http://localhost:5273

# Android production (set via --dart-define):
flutter run -d <device> \
  --dart-define BCI_BRIDGE_URL=http://<ip>:5000 \
  --dart-define KASA_BRIDGE_URL=http://<ip>:5273
```

**Firebase** (optional for Android):
1. Create Firebase project at https://console.firebase.google.com
2. Download `google-services.json` for Android
3. Set environment variables:
   ```bash
   export FIREBASE_API_KEY="..."
   export FIREBASE_APP_ID="..."
   # ... other vars
   ```
4. Set `enableFirebaseAuth = true` in main.dart

### Hardware Configuration (`python_bci/bci_motor_imagery_complete.py`)

Adjust for your EEG setup:
```python
class Config:
    BOARD_ID = BoardIds.NEUROPAWN_KNIGHT_BOARD  # or SYNTHETIC_BOARD for testing
    SERIAL_PORT = 'COM5'                        # Windows: COM3, Mac: /dev/cu.usbserial-*
    NUM_CHANNELS = 8                            # Depends on your headset
    SAMPLING_RATE = 125                         # Hz
    BASELINE_DURATION = 60                      # seconds
    TRAINING_TRIALS = 40                        # trials per class
```

---

## Usage Workflow

### For New Users

1. **Launch App** → Home Screen
2. **Calibration** (5-10 min)
   - Enter Calibration Screen
   - Follow on-screen instructions
   - Relax for 60 seconds while baseline is recorded
3. **Training** (10-15 min)
   - Enter Training Screen
   - Imagine left/right hand movement on cue
   - 40 trials total (20 per imagery type)
   - Mid-session break at trial 20
4. **Detection Enabled** → Return to Home
   - Select a Kasa smart plug
   - Arm BCI detection
   - Imagine hand movement to trigger device

### For Developers

**Testing without Hardware**:
```bash
# Run BCI bridge in synthetic mode
# Edit bci_motor_imagery_complete.py:
# BOARD_ID = BoardIds.SYNTHETIC_BOARD
```

**Viewing EEG Data**:
```
Logged data saved to: python_bci/eeg_logs/
Analyze with: numpy, pandas, matplotlib
```

---

## Dependencies

### Flutter
- `firebase_core`, `firebase_auth` — User authentication
- `google_sign_in` — OAuth integration
- `http` — HTTP client for bridge communication
- `shared_preferences` — Local storage (URLs, device IDs)

### Python
- `brainflow>=5.0.0` — EEG hardware interface
- `flask` — HTTP server for mobile integration
- `flask-cors` — Cross-origin requests
- `mne>=1.0.0` — EEG signal processing
- `scikit-learn` — Machine learning (LDA, SVM)
- `numpy`, `scipy`, `pandas` — Scientific computing

---

## Security & Privacy

- **Credentials**: Kasa credentials stored in memory only, never persisted externally
- **EEG Data**: Processed locally on device/bridge, not sent to cloud storage
- **Firebase**: Optional; configure for production auth
- **API Keys**: Use `--dart-define` environment variables (never commit to repo)

---

## Development Notes

- **Windows/Desktop**: Runs in development mode without Firebase, skips auth
- **Android**: Requires physical or emulated device; can connect to local bridge IPs
- **Calibration/Training**: Logs to `eeg_logs/` for post-hoc analysis
- **Debugging**: Set `flutter run -v` for verbose output

---

## References

This project implements methods from **Chapter 3: Motor Imagery Classification** in the accompanying research paper. Key techniques:

- **Event-Related Desynchronization (ERD)** detection
- **Mu/Beta frequency band** analysis (8-30 Hz)
- **Linear Discriminant Analysis (LDA)** for real-time classification
- **Sliding window** approach for low-latency detection

---

## License

#TODO!
[Add license information here - MIT, GPL, etc.]

---

## Contributing

Contributions welcome! To contribute:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit changes (`git commit -m 'Add my feature'`)
4. Push to branch (`git push origin feature/my-feature`)
5. Open a Pull Request

---

## FAQ

**Q: Will this work without the NeuroPawn hardware?**  
A: Yes! Set `BOARD_ID = BoardIds.SYNTHETIC_BOARD` in `bci_motor_imagery_complete.py` for testing.

**Q: Do I need Firebase for the app to work?**  
A: No. Set `enableFirebaseAuth = false` in `lib/main.dart` for demo mode.

**Q: How accurate is the motor imagery classification?**  
A: With proper calibration and training, expects 70-85% accuracy after 40 trials. Individual variation is significant.

**Q: Can I use other EEG headsets?**  
A: Yes, if supported by BrainFlow (OpenBCI, Cyton, etc.). Update `Config.BOARD_ID` and adjust channel mappings.

**Q: How do I deploy this to production?**  
A: See Firebase deployment docs. Build release APK with: `flutter build apk --dart-define=...`

---

## Support

For issues, questions, or feedback, please open a GitHub issue or contact the maintainers.

---

**Made for accessibility research & Ethical NeuroTechnology**
