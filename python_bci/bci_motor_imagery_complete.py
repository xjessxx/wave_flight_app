"""
Motor Imagery BCI classification System - Complete Implementation
===================================================
Hardware-ready version with proper ML training and real time classification

Author: Lily Farr (Based on Chapter 3 Methods)
Hardware: OpenBCI Cyton / NeuroPawn EEG Headset 
Features: Baseline calibration, ML training, real-time ERD detection, smart home control

BEFORE RUNNING:
1. Install dependencies: pip install -r requirements.txt
2. Configure hardware settings in Config class
3. Ensure EEG headset is properly connected
4. Pair Android device via Bluetooth
"""

import numpy as np
import pandas as pd
from scipy.signal import welch, butter, sosfiltfilt
import matplotlib.pyplot as plt
import time
from collections import deque
import json
import pickle
from datetime import datetime
import os
import warnings
warnings.filterwarnings('ignore')

# BrainFlow for OpenBCI/Neuropawn
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
from brainflow.data_filter import DataFilter, FilterTypes, DetrendOperations

# MNE-Python for EEG processing
import mne
from mne.preprocessing import ICA

# Machine Learning
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score
from sklearn.metrics import classification_report, confusion_matrix

# Bluetooth communication 
try:
    import bluetooth
    BLUETOOTH_AVAILABLE = True
except ImportError:
    print("Warning: PyBluez not installed. Bluetooth triggers disabled.")
    print("Install with: pip install pybluez")
    BLUETOOTH_AVAILABLE = False


# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """System configuration - ADJUST THESE FOR YOUR HARDWARE"""
    
    # === Hardware Selection ===
    # Options: BoardIds.CYTON_BOARD, BoardIds.SYNTHETIC_BOARD
    BOARD_ID = BoardIds.NEUROPAWN_KNIGHT_BOARD # Change when hardware arrives
    SERIAL_PORT = 'COM5' # '/dev/ttyUSB0'  # Windows: 'COM3', Mac: '/dev/cu.usbserial-*'
    NUM_CHANNELS = 8 

    # === EEG Channels ===
    C3_CHANNEL = 3  # Left motor cortex (right hand imagery) - 1-indexed
    C4_CHANNEL = 4  # Right motor cortex (left hand imagery)
    SAMPLING_RATE = 125  # Hz (OpenBCI default) CHANGE (neuropawn i think 125hz)
    
    # === Signal Processing ===
    BANDPASS_LOW = 1.0   # Hz - remove DC drift
    BANDPASS_HIGH = 50.0  # Hz - remove high-freq noise
    NOTCH_FREQ = 60.0     # Hz - power line noise (50 Hz in Europe)
    
    MU_BAND = (8, 12)     # Hz - sensorimotor rhythm
    BETA_BAND = (13, 30)  # Hz - motor-related beta
    WELCH_NPERSEG = 250   # 2 seconds at 125 Hz
    
    # === Baseline Calibration ===
    BASELINE_DURATION = 60  # seconds (30-60 recommended)
    
    # === Training Protocol ===
    TRAINING_TRIALS = 20     # trials per class (20-40 recommended)
    TRIAL_DURATION = 4.0     # seconds per trial
    REST_DURATION = 3.0      # seconds between trials
    CUE_DELAY = 1.0          # seconds before motor imagery starts
    
    # === Real-Time Detection ===
    WINDOW_DURATION = 2.0    # seconds
    STEP_SIZE = 0.5          # seconds (overlap)
    CONFIDENCE_WINDOWS = 3   # consecutive detections required
    TRIGGER_COOLDOWN = 2.0   # seconds between triggers
    
    # === Machine Learning ===
    CLASSIFIER = 'LDA'       # Options: 'LDA', 'SVM'
    USE_ERD_FEATURES = True  # Use ERD% as features
    USE_PSD_FEATURES = False # Use raw PSD as features
    
    # === Bluetooth ===
    ANDROID_MAC = 'XX:XX:XX:XX:XX:XX'  # Update with the Android MAC
    BT_PORT = 1
    
    # === Logging ===
    LOG_DIR = './eeg_logs'
    SAVE_RAW_DATA = True
    SAVE_MODELS = True


# ============================================================================
# HARDWARE INTERFACE
# ============================================================================

class EEGStream:
    """Manages EEG hardware connection and data streaming"""
    
    def __init__(self, board_id, serial_port=None):
        self.board_id = board_id
        self.params = BrainFlowInputParams()
        
        if serial_port:
            self.params.serial_port = serial_port
        
        self.board = BoardShim(board_id, self.params)
        self.is_streaming = False
        
        # Get board info
        self.eeg_channels = BoardShim.get_eeg_channels(board_id)
        self.sampling_rate = BoardShim.get_sampling_rate(board_id)
        self.timestamp_channel = BoardShim.get_timestamp_channel(board_id)
        
        print(f"\n{'='*60}")
        print(f"EEG Hardware Initialized")
        print(f"{'='*60}")
        print(f"Board: {board_id}")
        print(f"EEG Channels: {self.eeg_channels}")
        print(f"Sampling Rate: {self.sampling_rate} Hz")
        print(f"{'='*60}\n")
    
    def start(self):
        """Start EEG data streaming"""
        try:
            self.board.prepare_session()
            self.board.start_stream(450000) # buffer
            self.is_streaming = True
            print("EEG stream started")
            time.sleep(2)  # Stabilization

            if self.board_id == BoardIds.NEUROPAWN_KNIGHT_BOARD.value:
                self.configure_neuropawn(Config.NUM_CHANNELS)

        except Exception as e:
            print(f"Failed to start stream: {e}")
            raise
    
    def configure_neuropawn(self, num_channels=8):
        """
        Configure Neuropawn Knight Board channels
        Enables each channel with gain=12 and RLD for noise reduction
        """
        if self.board_id != BoardIds.NEUROPAWN_KNIGHT_BOARD.value:
            return  
        
        print("\nConfiguring Neuropawn Knight Board...")
        
        for channel in range(1, num_channels + 1):
            # Enable channel with gain=12 - could be changed later
            cmd_on = f"chon_{channel}_12"
            self.board.config_board(cmd_on)
            time.sleep(0.5)
            
            # Enable RLD for noise reduction
            cmd_rld = f"rldadd_{channel}"
            self.board.config_board(cmd_rld)
            time.sleep(0.5)
        
        print("Neuropawn configuration complete\n")
    
    def stop(self):
        """Stop streaming and release hardware"""
        if self.is_streaming:
            self.board.stop_stream()
            self.board.release_session()
            self.is_streaming = False
            print("EEG stream stopped")
    
    def get_data(self, num_samples=None):
        """
        Get EEG data from buffer
        Returns: numpy array [channels x samples]
        """
        if num_samples:
            data = self.board.get_current_board_data(num_samples)
        else:
            data = self.board.get_board_data()
        return data
    
    def clear_buffer(self):
        """Clear the data buffer"""
        _ = self.board.get_board_data()


# ============================================================================
# SIGNAL PROCESSING
# ============================================================================

class SignalProcessor:
    """Handles filtering, artifact removal, and feature extraction"""
    
    def __init__(self, sampling_rate=250):
        self.fs = sampling_rate
        
    def bandpass_filter(self, data, low=1.0, high=50.0):
        """Apply Butterworth bandpass filter"""
        sos = butter(4, [low, high], btype='band', fs=self.fs, output='sos')
        return sosfiltfilt(sos, data)
    
    def notch_filter(self, data, freq=60.0, quality=30.0):
        """Remove power line noise using scipy instead of BrainFlow"""
        from scipy.signal import iirnotch, filtfilt
        
        # Design notch filter
        b, a = iirnotch(freq, quality, self.fs)
        
        # Apply filter
        filtered = filtfilt(b, a, data)
        return filtered
    
    def preprocess(self, data, apply_notch=True):
        """
        Apply standard preprocessing pipeline
        Args:
            data: 1D array of EEG samples
        Returns:
            Filtered data
        """
        # Convert to numpy array and ensure float type
        data = np.array(data, dtype=np.float64)
        
        # Bandpass filter
        filtered = self.bandpass_filter(data, Config.BANDPASS_LOW, Config.BANDPASS_HIGH)
        
        # Notch filter for power line noise (optional)
        if apply_notch:
            try:
                filtered = self.notch_filter(filtered, Config.NOTCH_FREQ)
            except Exception as e:
                print(f"Warning: Notch filter failed ({e}), continuing without it...")
        
        return filtered
    
    def compute_psd(self, data, band=None):
        """
        Compute Power Spectral Density using Welch's method
        Args:
            data: 1D array of EEG samples
            band: tuple (low, high) to extract specific band power
        Returns:
            If band specified: band power (scalar)
            If no band: (frequencies, psd) arrays
        """
        freqs, psd = welch(data, fs=self.fs, nperseg=Config.WELCH_NPERSEG)
        
        if band:
            # Extract specific band power
            band_idx = np.logical_and(freqs >= band[0], freqs <= band[1])
            # Use trapezoid for numpy 2.0+, fallback to trapz for older versions
            try:
                band_power = np.trapezoid(psd[band_idx], freqs[band_idx])
            except AttributeError:
                band_power = np.trapz(psd[band_idx], freqs[band_idx])
            return band_power
        else:
            return freqs, psd
    
    def compute_erd(self, activation_power, baseline_power):
        """
        Calculate Event-Related Desynchronization
        ERD% = (P_activation - P_baseline) / P_baseline × 100
        
        Negative values indicate desynchronization (expected during MI)
        """
        return ((activation_power - baseline_power) / baseline_power) * 100


# ============================================================================
# BASELINE CALIBRATION
# ============================================================================

class BaselineCalibrator:
    """Collects resting state baseline for ERD calculation"""
    
    def __init__(self, stream, processor):
        self.stream = stream
        self.processor = processor
        self.baseline = None
    
    def collect(self, duration=60):
        """
        Collect baseline resting data
        
        Returns:
            dict with baseline power for C3/C4 mu/beta bands
        """
        print(f"\n{'='*60}")
        print("BASELINE CALIBRATION")
        print(f"{'='*60}")
        print(f"Duration: {duration} seconds")
        print("\nInstructions:")
        print("  • Sit comfortably and RELAX")
        print("  • Do NOT imagine any movements")
        print("  • Keep eyes open, focused on a fixed point")
        print("  • Minimize eye movements, jaw tension, and body movement")
        print("\nThis establishes your resting brain state.")
        print("Motor imagery will be compared against this baseline.")
        
        input("\nPress ENTER when ready...")
        print("\nStarting in 3...")
        time.sleep(1)
        print("2...")
        time.sleep(1)
        print("1...")
        time.sleep(1)
        print("\n>>> COLLECTING BASELINE - STAY RELAXED <<<")
        
        # Clear buffer and collect fresh data
        self.stream.clear_buffer()
        time.sleep(duration)
        
        # Get data
        data = self.stream.get_data()
        c3_data = data[Config.C3_CHANNEL]
        c4_data = data[Config.C4_CHANNEL]
        
        # Preprocess
        c3_clean = self.processor.preprocess(c3_data)
        c4_clean = self.processor.preprocess(c4_data)
        
        # Calculate baseline power
        baseline = {
            'c3_mu': self.processor.compute_psd(c3_clean, Config.MU_BAND),
            'c3_beta': self.processor.compute_psd(c3_clean, Config.BETA_BAND),
            'c4_mu': self.processor.compute_psd(c4_clean, Config.MU_BAND),
            'c4_beta': self.processor.compute_psd(c4_clean, Config.BETA_BAND),
        }
        
        self.baseline = baseline
        
        print("\nBASELINE COMPLETE")
        print(f"  C3 - Mu: {baseline['c3_mu']:.2f} µV²/Hz, Beta: {baseline['c3_beta']:.2f} µV²/Hz")
        print(f"  C4 - Mu: {baseline['c4_mu']:.2f} µV²/Hz, Beta: {baseline['c4_beta']:.2f} µV²/Hz")
        
        # Save baseline
        if Config.SAVE_RAW_DATA:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"{Config.LOG_DIR}/baseline_{timestamp}.json"
            with open(filepath, 'w') as f:
                json.dump(baseline, f, indent=2)
            print(f"  Saved to: {filepath}")
        
        return baseline


# ============================================================================
# TRAINING DATA COLLECTION
# ============================================================================

class TrainingCollector:
    """Collects labeled motor imagery training data"""
    
    def __init__(self, stream, processor, baseline):
        self.stream = stream
        self.processor = processor
        self.baseline = baseline
        self.training_data = []
    
    def collect_trial(self, label, trial_num, total_trials):
        """
        Collect a single motor imagery trial
        
        Args:
            label: 0 (rest) or 1 (motor imagery)
            trial_num: current trial number
            total_trials: total number of trials
        """
        print(f"\nTrial {trial_num}/{total_trials} - ", end='')
        
        if label == 0:
            print("REST (do nothing)")
            print("  - Just relax, no movement or imagery")
        else:
            print("MOTOR IMAGERY (imagine thumb swiping)")
            print("  - Vividly imagine swiping your thumb")
            print("  - Feel the movement without actually moving")
        
        # Countdown
        print("\nStarting in: ", end='', flush=True)
        for i in range(3, 0, -1):
            print(f"{i}... ", end='', flush=True)
            time.sleep(1)
        print("GO!\n")
        
        # Collect data
        self.stream.clear_buffer()
        time.sleep(Config.TRIAL_DURATION)
        
        data = self.stream.get_data()
        c3_data = data[Config.C3_CHANNEL]
        c4_data = data[Config.C4_CHANNEL]
        
        # Preprocess
        c3_clean = self.processor.preprocess(c3_data)
        c4_clean = self.processor.preprocess(c4_data)
        
        # Extract features
        features = self._extract_features(c3_clean, c4_clean)
        
        # Store trial
        self.training_data.append({
            'features': features,
            'label': label,
            'trial_num': trial_num,
            'timestamp': time.time()
        })
        
        print(" Trial complete")
        
        # Rest between trials
        if trial_num < total_trials:
            print(f"\nRest for {Config.REST_DURATION} seconds...")
            time.sleep(Config.REST_DURATION)
    
    def _extract_features(self, c3_data, c4_data):
        """
        Extract features for classification
        
        Current implementation: ERD values for mu/beta bands
        Returns: 4-element feature vector [C3_mu_ERD, C3_beta_ERD, C4_mu_ERD, C4_beta_ERD]
        """
        # Compute current band powers
        c3_mu_power = self.processor.compute_psd(c3_data, Config.MU_BAND)
        c3_beta_power = self.processor.compute_psd(c3_data, Config.BETA_BAND)
        c4_mu_power = self.processor.compute_psd(c4_data, Config.MU_BAND)
        c4_beta_power = self.processor.compute_psd(c4_data, Config.BETA_BAND)
        
        # Calculate ERD
        c3_mu_erd = self.processor.compute_erd(c3_mu_power, self.baseline['c3_mu'])
        c3_beta_erd = self.processor.compute_erd(c3_beta_power, self.baseline['c3_beta'])
        c4_mu_erd = self.processor.compute_erd(c4_mu_power, self.baseline['c4_mu'])
        c4_beta_erd = self.processor.compute_erd(c4_beta_power, self.baseline['c4_beta'])
        
        return np.array([c3_mu_erd, c3_beta_erd, c4_mu_erd, c4_beta_erd])
    
    def collect_full_training_set(self):
        """
        Collect complete training dataset with both classes
        """
        print(f"\n{'='*60}")
        print("TRAINING DATA COLLECTION")
        print(f"{'='*60}")
        print(f"Total trials: {Config.TRAINING_TRIALS * 2}")
        print(f"  • {Config.TRAINING_TRIALS} REST trials")
        print(f"  • {Config.TRAINING_TRIALS} MOTOR IMAGERY trials")
        print(f"Trial duration: {Config.TRIAL_DURATION} seconds")
        print(f"Rest between trials: {Config.REST_DURATION} seconds")
        print("\nThis will take approximately {:.1f} minutes".format(
            (Config.TRAINING_TRIALS * 2 * (Config.TRIAL_DURATION + Config.REST_DURATION)) / 60
        ))
        
        input("\nPress ENTER to begin training...")
        
        # Collect REST trials
        print(f"\n{'='*60}")
        print("Phase 1: REST TRIALS")
        print(f"{'='*60}")
        for i in range(Config.TRAINING_TRIALS):
            self.collect_trial(label=0, trial_num=i+1, total_trials=Config.TRAINING_TRIALS)
        
        print(f"\n{'='*60}")
        print("Phase 1 complete! Take a 30 second break...")
        print(f"{'='*60}")
        time.sleep(30)
        
        # Collect MOTOR IMAGERY trials
        print(f"\n{'='*60}")
        print("Phase 2: MOTOR IMAGERY TRIALS")
        print(f"{'='*60}")
        print("\nRemember: VIVIDLY imagine swiping your thumb")
        print("The more focused your imagery, the better the classifier will work!")
        input("\nPress ENTER to begin motor imagery trials...")
        
        for i in range(Config.TRAINING_TRIALS):
            self.collect_trial(label=1, trial_num=i+1, total_trials=Config.TRAINING_TRIALS)
        
        print(f"\n{'='*60}")
        print("✓ TRAINING DATA COLLECTION COMPLETE!")
        print(f"{'='*60}")
        print(f"Collected {len(self.training_data)} trials")
        
        return self.training_data


# ============================================================================
# MACHINE LEARNING CLASSIFIER
# ============================================================================

class MIClassifier:
    """Trains and applies ML classifier for motor imagery detection"""
    
    def __init__(self):
        self.classifier = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names = ['C3_mu_ERD', 'C3_beta_ERD', 'C4_mu_ERD', 'C4_beta_ERD']
    
    def train(self, training_data):
        """
        Train classifier on collected data
        
        Args:
            training_data: list of dicts with 'features' and 'label'
        """
        print(f"\n{'='*60}")
        print("TRAINING CLASSIFIER")
        print(f"{'='*60}")
        
        # Prepare data
        X = np.array([trial['features'] for trial in training_data])
        y = np.array([trial['label'] for trial in training_data])
        
        print(f"Training samples: {len(X)}")
        print(f"  REST (class 0): {np.sum(y == 0)}")
        print(f"  MOTOR IMAGERY (class 1): {np.sum(y == 1)}")
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Initialize classifier
        if Config.CLASSIFIER == 'LDA':
            self.classifier = LinearDiscriminantAnalysis()
            print("\nUsing: Linear Discriminant Analysis (LDA)")
        elif Config.CLASSIFIER == 'SVM':
            self.classifier = SVC(kernel='rbf', C=1.0, gamma='scale', probability=True)
            print("\nUsing: Support Vector Machine (SVM)")
        
        # Cross-validation
        print("\nPerforming 5-fold cross-validation...")
        cv_scores = cross_val_score(self.classifier, X_scaled, y, cv=5, scoring='accuracy')
        print(f"CV Accuracy: {cv_scores.mean():.2%} ± {cv_scores.std():.2%}")
        
        # Train on full dataset
        self.classifier.fit(X_scaled, y)
        train_acc = self.classifier.score(X_scaled, y)
        print(f"Training Accuracy: {train_acc:.2%}")
        
        # Feature importance (for LDA)
        if Config.CLASSIFIER == 'LDA' and hasattr(self.classifier, 'coef_'):
            print("\nFeature Importance (absolute coefficients):")
            importance = np.abs(self.classifier.coef_[0])
            for name, imp in sorted(zip(self.feature_names, importance), key=lambda x: x[1], reverse=True):
                print(f"  {name}: {imp:.3f}")
        
        self.is_trained = True
        print("\nClassifier trained successfully!")
        
        # Save model
        if Config.SAVE_MODELS:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_path = f"{Config.LOG_DIR}/classifier_{timestamp}.pkl"
            with open(model_path, 'wb') as f:
                pickle.dump({
                    'classifier': self.classifier,
                    'scaler': self.scaler,
                    'feature_names': self.feature_names,
                    'cv_scores': cv_scores
                }, f)
            print(f"  Model saved to: {model_path}")
    
    def predict(self, features):
        """
        Classify a single sample
        
        Args:
            features: 1D array of features
        
        Returns:
            prediction (0 or 1), confidence (0-1)
        """
        if not self.is_trained:
            raise ValueError("Classifier not trained yet!")
        
        # Scale features
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        
        # Predict
        prediction = self.classifier.predict(features_scaled)[0]
        
        # Get confidence
        if hasattr(self.classifier, 'predict_proba'):
            proba = self.classifier.predict_proba(features_scaled)[0]
            confidence = proba[prediction]
        elif hasattr(self.classifier, 'decision_function'):
            decision = self.classifier.decision_function(features_scaled)[0]
            confidence = 1 / (1 + np.exp(-decision))  # Sigmoid
            if prediction == 0:
                confidence = 1 - confidence
        else:
            confidence = 1.0
        
        return prediction, confidence
    
    def load_model(self, filepath):
        """Load pre-trained model"""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        self.classifier = data['classifier']
        self.scaler = data['scaler']
        self.feature_names = data['feature_names']
        self.is_trained = True
        print(f"Model loaded from {filepath}")


# ============================================================================
# REAL-TIME DETECTION
# ============================================================================

class RealTimeDetector:
    """Sliding window motor imagery detection with ML classification"""
    
    def __init__(self, stream, processor, baseline, classifier):
        self.stream = stream
        self.processor = processor
        self.baseline = baseline
        self.classifier = classifier
        
        # Sliding window buffers
        self.window_size = int(Config.WINDOW_DURATION * Config.SAMPLING_RATE)
        self.step_size = int(Config.STEP_SIZE * Config.SAMPLING_RATE)
        
        self.c3_buffer = deque(maxlen=self.window_size)
        self.c4_buffer = deque(maxlen=self.window_size)
        
        # Detection state
        self.detection_history = deque(maxlen=Config.CONFIDENCE_WINDOWS)
        self.last_trigger_time = 0
        self.is_mi_active = False
    
    def add_sample(self, c3_sample, c4_sample):
        """Add new sample to sliding window buffers"""
        self.c3_buffer.append(c3_sample)
        self.c4_buffer.append(c4_sample)
    
    def process_window(self):
        """
        Process current window and detect motor imagery
        
        Returns:
            trigger (bool), prediction (0/1), confidence (0-1), erd_values (dict)
        """
        if len(self.c3_buffer) < self.window_size:
            return False, 0, 0.0, {}
        
        # Get window data
        c3_data = np.array(self.c3_buffer)
        c4_data = np.array(self.c4_buffer)
        
        # Preprocess
        c3_clean = self.processor.preprocess(c3_data)
        c4_clean = self.processor.preprocess(c4_data)
        
        # Extract features (same as training)
        c3_mu_power = self.processor.compute_psd(c3_clean, Config.MU_BAND)
        c3_beta_power = self.processor.compute_psd(c3_clean, Config.BETA_BAND)
        c4_mu_power = self.processor.compute_psd(c4_clean, Config.MU_BAND)
        c4_beta_power = self.processor.compute_psd(c4_clean, Config.BETA_BAND)
        
        c3_mu_erd = self.processor.compute_erd(c3_mu_power, self.baseline['c3_mu'])
        c3_beta_erd = self.processor.compute_erd(c3_beta_power, self.baseline['c3_beta'])
        c4_mu_erd = self.processor.compute_erd(c4_mu_power, self.baseline['c4_mu'])
        c4_beta_erd = self.processor.compute_erd(c4_beta_power, self.baseline['c4_beta'])
        
        features = np.array([c3_mu_erd, c3_beta_erd, c4_mu_erd, c4_beta_erd])
        
        # Classify
        prediction, confidence = self.classifier.predict(features)
        
        # Update detection history
        self.detection_history.append(prediction == 1)
        
        # Check for trigger
        trigger = False
        confidence_met = (len(self.detection_history) == Config.CONFIDENCE_WINDOWS and
                         sum(self.detection_history) == Config.CONFIDENCE_WINDOWS)
        
        if confidence_met and not self.is_mi_active:
            current_time = time.time()
            if current_time - self.last_trigger_time > Config.TRIGGER_COOLDOWN:
                trigger = True
                self.is_mi_active = True
                self.last_trigger_time = current_time
        
        # Reset state when MI no longer detected
        if prediction == 0:
            self.is_mi_active = False
        
        erd_values = {
            'c3_mu': c3_mu_erd,
            'c3_beta': c3_beta_erd,
            'c4_mu': c4_mu_erd,
            'c4_beta': c4_beta_erd
        }
        
        return trigger, prediction, confidence, erd_values
    
    def run(self, bt_controller=None):
        """
        Main real-time detection loop
        """
        print(f"\n{'='*60}")
        print("REAL-TIME MOTOR IMAGERY DETECTION")
        print(f"{'='*60}")
        print("Status: ACTIVE")
        print("\nInstructions:")
        print("  - Imagine swiping your thumb to trigger device")
        print("  - Keep imagery consistent and focused")
        print("  - Detection requires sustained MI (not just a quick thought)")
        print(f"  - Cooldown: {Config.TRIGGER_COOLDOWN}s between triggers")
        print("\nPress Ctrl+C to stop\n")
        
        # Logging setup
        log_data = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"{Config.LOG_DIR}/realtime_{timestamp}.csv"
        
        sample_count = 0
        window_count = 0
        
        try:
            while True:
                # Get latest sample
                data = self.stream.get_data(1)
                
                if data.shape[1] > 0:
                    c3_sample = data[Config.C3_CHANNEL][0]
                    c4_sample = data[Config.C4_CHANNEL][0]
                    
                    self.add_sample(c3_sample, c4_sample)
                    sample_count += 1
                    
                    # Process at step intervals
                    if sample_count % self.step_size == 0 and len(self.c3_buffer) == self.window_size:
                        trigger, prediction, confidence, erd = self.process_window()
                        window_count += 1
                        
                        # Display
                        status = "MI DETECTED!" if trigger else "MONITORING  "
                        pred_symbol = "✓" if prediction == 1 else "o"
                        conf_bars = "█" * int(confidence * 10)
                        
                        print(f"\r{status} | {pred_symbol} Conf: {conf_bars:<10} {confidence:.0%} | "
                              f"C3μ: {erd['c3_mu']:6.1f}% | C4μ: {erd['c4_mu']:6.1f}%",
                              end='', flush=True)
                        
                        # Log
                        log_data.append({
                            'window': window_count,
                            'timestamp': time.time(),
                            'prediction': prediction,
                            'confidence': confidence,
                            'trigger': trigger,
                            **erd
                        })
                        
                        # Send trigger
                        if trigger and bt_controller:
                            print(f"\n{'='*60}")
                            print("TRIGGER ACTIVATED - Sending to device...")
                            print(f"{'='*60}\n")
                            bt_controller.send_trigger()
                
                time.sleep(1 / Config.SAMPLING_RATE)
        
        except KeyboardInterrupt:
            print("\n\n Detection stopped by user")
            
            # Save log
            if log_data:
                df = pd.DataFrame(log_data)
                df.to_csv(log_file, index=False)
                print(f"Session log saved: {log_file}")
                
                # Print summary
                print(f"\nSession Summary:")
                print(f"  Windows processed: {window_count}")
                print(f"  MI detections: {df['prediction'].sum()}")
                print(f"  Triggers sent: {df['trigger'].sum()}")
                print(f"  Avg confidence: {df['confidence'].mean():.1%}")


# ============================================================================
# BLUETOOTH CONTROLLER
# ============================================================================

class BluetoothController:
    """Sends trigger commands to Android app"""
    
    def __init__(self, mac_address, port=1):
        self.mac = mac_address
        self.port = port
        self.socket = None
        self.connected = False
    
    def connect(self):
        """Establish Bluetooth connection"""
        if not BLUETOOTH_AVAILABLE:
            print(" Bluetooth not available (PyBluez not installed)")
            return False
        
        try:
            print(f"Connecting to {self.mac}...")
            self.socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            self.socket.connect((self.mac, self.port))
            self.connected = True
            print(f"Bluetooth connected")
            return True
        except Exception as e:
            print(f"Bluetooth connection failed: {e}")
            return False
    
    def send_trigger(self):
        """Send trigger command to toggle device"""
        if not self.connected:
            print("Bluetooth not connected - trigger not sent")
            return False
        
        try:
            message = json.dumps({
                "command": "TOGGLE_DEVICE",
                "timestamp": time.time()
            })
            self.socket.send(message.encode())
            print("Trigger sent to Android app")
            return True
        except Exception as e:
            print(f"Failed to send trigger: {e}")
            return False
    
    def disconnect(self):
        """Close connection"""
        if self.socket:
            self.socket.close()
            self.connected = False
            print("Bluetooth disconnected")


# ============================================================================
# MAIN WORKFLOW
# ============================================================================

def main():
    """Complete BCI workflow: calibrate → train → detect"""
    
    print("\n" + "="*70)
    print(" " * 15 + "MOTOR IMAGERY BCI SYSTEM")
    print(" " * 10 + "Smart Home Control via Brain Signals")
    print("="*70)
    
    # Create log directory
    os.makedirs(Config.LOG_DIR, exist_ok=True)
    
    # Initialize hardware
    print("\n[1/6] Initializing EEG Hardware...")
    stream = EEGStream(Config.BOARD_ID, Config.SERIAL_PORT)
    processor = SignalProcessor(Config.SAMPLING_RATE)
    
    try:
        stream.start()
        
        # Baseline calibration
        print("\n[2/6] Baseline Calibration...")
        calibrator = BaselineCalibrator(stream, processor)
        baseline = calibrator.collect(Config.BASELINE_DURATION)
        
        # Training data collection
        print("\n[3/6] Training Data Collection...")
        trainer = TrainingCollector(stream, processor, baseline)
        training_data = trainer.collect_full_training_set()
        
        # Train classifier
        print("\n[4/6] Training Classifier...")
        classifier = MIClassifier()
        classifier.train(training_data)
        
        # Bluetooth setup
        print("\n[5/6] Bluetooth Connection...")
        bt_controller = BluetoothController(Config.ANDROID_MAC)
        
        if not bt_controller.connect():
            print("Continuing without Bluetooth (simulation mode)")
            bt_controller = None
        
        # Real-time detection
        print("\n[6/6] Starting Real-Time Detection...")
        detector = RealTimeDetector(stream, processor, baseline, classifier)
        detector.run(bt_controller)
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        print("\n\nShutting down...")
        stream.stop()
        if 'bt_controller' in locals() and bt_controller:
            bt_controller.disconnect()
        print(" System shutdown complete")


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()