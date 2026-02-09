"""
BCI Flutter Bridge Server
=========================
HTTP server that connects the BCI Python system with Flutter app

The server will run on http://localhost:5000
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
import time
import json
from datetime import datetime
import queue
import numpy as np

from bci_motor_imagery_complete import (
    EEGStream, SignalProcessor, BaselineCalibrator, 
    TrainingCollector, MIClassifier, RealTimeDetector, Config
)

app = Flask(__name__)
CORS(app)  # Allow Flutter to make requests

# Global state
bci_state = {
    'status': 'idle',  # idle, calibrating, training, detecting
    'baseline_progress': 0,
    'training_progress': 0,
    'current_trial': 0,
    'total_trials': 0,
    'trigger_detected': False,
    'last_trigger_time': None,
    'confidence': 0.0,
    'erd_values': {},
    'calibration_complete': False, 
    'hardware_initialized': False,
}

# Communication queues
command_queue = queue.Queue()
event_queue = queue.Queue()

# BCI components (global references)
stream = None
processor = None
baseline = None
classifier = None
detector = None


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/status', methods=['GET'])
def get_status():
    """Get current BCI system status"""
    return jsonify(bci_state)


@app.route('/calibration/start', methods=['POST'])
def start_calibration():
    """Start baseline calibration (60 seconds)"""
    global bci_state
    
    if bci_state['status'] != 'idle':
        return jsonify({'error': 'System busy'}), 400
    
    bci_state['status'] = 'calibrating'
    bci_state['baseline_progress'] = 0
    
    # Start calibration in background thread
    threading.Thread(target=run_calibration, daemon=True).start()
    
    return jsonify({'message': 'Calibration started', 'duration': Config.BASELINE_DURATION})


@app.route('/calibration/progress', methods=['GET'])
def get_calibration_progress():
    """Get calibration progress (0-100%)"""
    return jsonify({
        'progress': bci_state['baseline_progress'],
        'status': bci_state['status']
    })

@app.route('/calibration/status', methods=['GET'])
def calibration_status():
    return jsonify({
        'complete': bci_state.get('calibration_complete', False),
        'status': bci_state.get('status'),
        'progress': bci_state.get('baseline_progress', 0)
    })


@app.route('/training/start', methods=['POST'])
def start_training():
    """Start training session"""
    global bci_state, baseline
    
    if not bci_state.get('calibration_complete', False):
        return jsonify({'error': 'Calibration failed or not completed'}), 400

    
    if bci_state['status'] != 'idle':
        return jsonify({'error': f'System busy (status: {bci_state["status"]})'}), 400
    
    print("\n" + "="*60)
    print("TRAINING SESSION STARTING")
    print("="*60)
    
    bci_state['status'] = 'training'
    bci_state['current_trial'] = 0
    bci_state['total_trials'] = Config.TRAINING_TRIALS
    
    # Start training in background thread
    threading.Thread(target=run_training, daemon=True).start()
    
    return jsonify({
        'message': 'Training started',
        'total_trials': Config.TRAINING_TRIALS,
        'trial_duration': Config.TRIAL_DURATION
    })

@app.route('/training/trial_start', methods=['POST'])
def trial_start():
    """Signal that Flutter animation has started - begin collecting data"""
    global bci_state
    
    current_status = bci_state['status']
    
    if current_status == 'training':
        bci_state['status'] = 'collecting_trial'
        print("Trial collection triggered by Flutter")
        return jsonify({'message': 'Trial data collection started'})
    else:
        return jsonify({
            'error': f'Not ready for trial (current status: {current_status})'
        }), 400


@app.route('/training/trigger', methods=['POST'])
def manual_trigger():
    """Manual trigger for training (when button is pressed)"""
    command_queue.put('trigger')
    return jsonify({'message': 'Trigger received'})


@app.route('/training/progress', methods=['GET'])
def get_training_progress():
    """Get training progress"""
    return jsonify({
        'current_trial': bci_state['current_trial'],
        'total_trials': bci_state['total_trials'],
        'status': bci_state['status']
    })


@app.route('/detection/start', methods=['POST'])
def start_detection():
    """Start real-time motor imagery detection"""
    global bci_state, detector
    
    if classifier is None:
        return jsonify({'error': 'Training must be completed first'}), 400
    
    bci_state['status'] = 'detecting'
    
    # Start detector in background thread
    threading.Thread(target=run_detection, daemon=True).start()
    
    return jsonify({'message': 'Detection started'})


@app.route('/detection/stop', methods=['POST'])
def stop_detection():
    """Stop real-time detection"""
    global bci_state
    bci_state['status'] = 'idle'
    return jsonify({'message': 'Detection stopped'})


@app.route('/detection/poll', methods=['GET'])
def poll_detection():
    """Poll for motor imagery detection (call this repeatedly from Flutter)"""
    trigger = bci_state['trigger_detected']
    
    # Reset trigger after reading
    if trigger:
        bci_state['trigger_detected'] = False
    
    return jsonify({
        'trigger': trigger,
        'confidence': bci_state['confidence'],
        'erd_values': bci_state['erd_values'],
        'timestamp': bci_state['last_trigger_time']
    })

@app.route('/system/initialize', methods=['POST']) # ONLY INITIALIZE ONCE IN MAIN
def initialize_system():
    global stream, processor, bci_state

    if bci_state['hardware_initialized']:
        print("Initialize called again — ignored")
        return jsonify({'message': 'Already initialized'})

    print("Initializing EEG Hardware...")

    stream = EEGStream(Config.BOARD_ID, Config.SERIAL_PORT)
    processor = SignalProcessor(Config.SAMPLING_RATE)
    stream.start()

    bci_state['hardware_initialized'] = True
    bci_state['status'] = 'idle'

    return jsonify({'message': 'System initialized successfully'})



@app.route('/system/shutdown', methods=['POST'])
def shutdown_system():
    """Shutdown EEG hardware"""
    global stream, bci_state
    
    if stream:
        stream.stop()
    
    bci_state['status'] = 'idle'
    
    return jsonify({'message': 'System shutdown'})


# ============================================================================
# BACKGROUND WORKER FUNCTIONS
# ============================================================================

def run_calibration():
    """Run baseline calibration in background"""
    global baseline, bci_state, stream, processor
    
    print("\n" + "="*60)
    print("BASELINE CALIBRATION STARTING")
    print("="*60)
    
    # Safety checks
    if stream is None:
        print("Error: EEG stream not initialized!")
        bci_state['status'] = 'idle'
        return
    
    if processor is None:
        print("Error: Signal processor not initialized!")
        bci_state['status'] = 'idle'
        return
    
    try:
        duration = Config.BASELINE_DURATION
        start_time = time.time()
        
        # Progress updater
        def update_progress():
            while bci_state['status'] == 'calibrating':
                elapsed = time.time() - start_time
                progress = min(99, int((elapsed / duration) * 100)) # clamping at 99
                bci_state['baseline_progress'] = progress
                if progress % 20 == 0:  # Print every 20%
                    print(f"Progress: {progress}%")
                time.sleep(1)
        
        threading.Thread(target=update_progress, daemon=True).start()
        
       
        print(f"Collecting {duration}s of baseline data...")
        
        # Clear buffer
        stream.clear_buffer()
        time.sleep(1)  # Small delay
        
        # Wait for duration while collecting
        print(">>> COLLECTING BASELINE <<<")

        samples_needed = int(Config.BASELINE_DURATION * Config.SAMPLING_RATE)
        all_data = []

        start_time = time.time()

        while time.time() - start_time < Config.BASELINE_DURATION:
            chunk = stream.get_data(1)  # actively pull samples
            if chunk.shape[1] > 0:
                all_data.append(chunk)
            time.sleep(0.01)  # prevent CPU burn

        if not all_data:
            raise RuntimeError("No EEG data collected during calibration")

        # Concatenate collected chunks
        data = np.hstack(all_data)

        print(f"Collected {data.shape[1]} samples")

        
        if data.shape[1] == 0:
            raise Exception("No data collected!")
        
        print(f"Got {data.shape[1]} samples")
        
        # Extract C3 and C4 channels
        c3_idx = Config.C3_CHANNEL - 1
        c4_idx = Config.C4_CHANNEL - 1

        c3_data = data[c3_idx]  
        c4_data = data[c4_idx]
        
        # Preprocess
        print("Processing signals...")
        c3_clean = processor.preprocess(c3_data)
        c4_clean = processor.preprocess(c4_data)
        
        # Calculate baseline power
        print("Computing baseline power...")
        baseline = {
            'c3_mu_power': processor.compute_psd(c3_clean, Config.MU_BAND),
            'c3_beta_power': processor.compute_psd(c3_clean, Config.BETA_BAND),
            'c4_mu_power': processor.compute_psd(c4_clean, Config.MU_BAND),
            'c4_beta_power': processor.compute_psd(c4_clean, Config.BETA_BAND),
        }

        bci_state['calibration_complete'] = True

        print("\n" + "="*60)
        print("BASELINE CALIBRATION COMPLETE")
        print("="*60)
        print(f"C3 - Mu: {baseline['c3_mu_power']:.2f}, Beta: {baseline['c3_beta_power']:.2f}")
        print(f"C4 - Mu: {baseline['c4_mu_power']:.2f}, Beta: {baseline['c4_beta_power']:.2f}")
        print("="*60 + "\n")
        
        bci_state['status'] = 'idle'
        bci_state['baseline_progress'] = 100
        
    except Exception as e:
        print("\n" + "="*60)
        print("CALIBRATION FAILED")
        print("="*60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print("="*60 + "\n")
        bci_state['status'] = 'idle'
        bci_state['calibration_complete'] = False
        baseline = None


def run_training():
    """Run training data collection in background"""
    global classifier, bci_state, baseline, stream, processor
    
    if baseline is None: # make sure we have baseline first - home screen will be removed later so this shoujldnt be a problem
        print("Error: Baseline not collected")
        bci_state['status'] = 'idle'
        return
    
    print("\n" + "="*60)
    print("TRAINING DATA COLLECTION")
    print("="*60)
    print(f"Collecting {Config.TRAINING_TRIALS} trials")
    print("Waiting for Flutter to trigger animations...")
    print("="*60 + "\n")
    
    all_trials = []
    
    for trial_num in range(Config.TRAINING_TRIALS):
        bci_state['current_trial'] = trial_num
        
        print(f"\n[Trial {trial_num + 1}/{Config.TRAINING_TRIALS}]")
        print("Waiting for Flutter animation to start...")
        
        # Wait for Flutter to signal trial start
        wait_start = time.time()
        while bci_state['status'] == 'training':
            time.sleep(0.1)
            
            # Check if we've been waiting too long
            if time.time() - wait_start > 30:
                print("Timeout waiting for trial - skipping")
                break
        
        if bci_state['status'] == 'collecting_trial':
            print("Animation started - collecting EEG data...")
            
            # Collect data during the animation (4 seconds)
            try:
                trial_data = collect_trial_data(stream, processor, baseline)
                all_trials.append(trial_data)
                
                print(f"Trial {trial_num + 1} complete!")
                print(f"  ERD values: C3μ={trial_data['c3_mu_erd']:.1f}%, C4μ={trial_data['c4_mu_erd']:.1f}%")
                
            except Exception as e:
                print(f"Error collecting trial: {e}")
                import traceback
                traceback.print_exc()
            
            # Reset status for next trial
            bci_state['status'] = 'training'
        else:
            # Training was stopped
            print("Training interrupted by user")
            break
    
    # Update final trial count
    bci_state['current_trial'] = len(all_trials)
    
    # Now train the classifier if we have enough trials
    if len(all_trials) >= 10:  # Need at least 10 trials
        print("\n" + "="*60)
        print("TRAINING CLASSIFIER")
        print("="*60)
        print(f"Using {len(all_trials)} trials")
        
        try:
            classifier = MIClassifier()
            training_data = prepare_training_data(all_trials)
            
            print("Training model...")
            classifier.train(training_data)
            
            print("Classifier trained successfully!")
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"Classifier training failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"\nNot enough trials collected ({len(all_trials)}/{Config.TRAINING_TRIALS})")
        print("Classifier not trained - need at least 10 trials")
    
    bci_state['status'] = 'idle'
    print("\n Training session complete\n")


def collect_trial_data(stream, processor, baseline):
    """Collect EEG data for one trial (1.8 seconds during animation)"""
    import time
    
    # Clear buffer
    stream.clear_buffer()
    
    # Collect for trial duration
    duration = 1.8  # shooting phase seconds
    samples_needed = int(duration * Config.SAMPLING_RATE)
    
    print(f"  Collecting {samples_needed} samples ({duration}s)...")
    
    c3_data = []
    c4_data = []
    
    start_time = time.time()
    sample_count = 0
    
    while sample_count < samples_needed:
        data = stream.get_data(1)
        
        if data.shape[1] > 0:
            c3_data.append(data[Config.C3_CHANNEL - 1][0])
            c4_data.append(data[Config.C4_CHANNEL - 1][0])
            sample_count += 1
        
        time.sleep(1 / Config.SAMPLING_RATE)
        
        # Timeout safety
        if time.time() - start_time > duration + 2:
            print(f"Collection timeout - got {sample_count}/{samples_needed} samples")
            break
    
    print(f"Collected {sample_count} samples")
    
    # Convert to numpy arrays
    c3_signal = np.array(c3_data)
    c4_signal = np.array(c4_data)
    
    # Bandpass filter
    c3_filtered = processor.bandpass_filter(c3_signal)
    c4_filtered = processor.bandpass_filter(c4_signal)
    
    # Compute psd in mu and beta bands
    c3_mu_power = processor.compute_psd(c3_filtered, Config.MU_BAND)
    c3_beta_power = processor.compute_psd(c3_filtered, Config.BETA_BAND)
    c4_mu_power = processor.compute_psd(c4_filtered, Config.MU_BAND)
    c4_beta_power = processor.compute_psd(c4_filtered, Config.BETA_BAND)
    
    # Compute ERD 
    c3_mu_erd = processor.compute_erd(c3_mu_power, baseline['c3_mu_power'])
    c3_beta_erd = processor.compute_erd(c3_beta_power, baseline['c3_beta_power'])
    c4_mu_erd = processor.compute_erd(c4_mu_power, baseline['c4_mu_power'])
    c4_beta_erd = processor.compute_erd(c4_beta_power, baseline['c4_beta_power'])
    
    return {
        'c3_mu_erd': c3_mu_erd,
        'c3_beta_erd': c3_beta_erd,
        'c4_mu_erd': c4_mu_erd,
        'c4_beta_erd': c4_beta_erd,
        'label': 1  # Motor imagery
    }

def prepare_training_data(trials):
    """Convert trial data to format for classifier"""
    training_data = []
    
    for trial in trials:
        # Create feature vector from ERD values
        feature_vector = [
            trial['c3_mu_erd'],
            trial['c3_beta_erd'],
            trial['c4_mu_erd'],
            trial['c4_beta_erd']
        ]
        
        # Add to training data with proper format
        training_data.append({
            'features': feature_vector,
            'label': trial['label']  # Should be 1 for motor imagery
        })
    
    return training_data


def run_detection():
    """Run real-time detection in background"""
    global detector, bci_state, baseline, classifier
    
    detector = RealTimeDetector(stream, processor, baseline, classifier)
    
    print("\nStarting real-time detection...")
    
    # Modified detection loop that updates bci_state
    while bci_state['status'] == 'detecting':
        data = stream.get_data(1)
        
        if data.shape[1] > 0:
            c3_sample = data[Config.C3_CHANNEL - 1][0]
            c4_sample = data[Config.C4_CHANNEL - 1][0]
            
            detector.add_sample(c3_sample, c4_sample)
            
            # Process window
            if len(detector.c3_buffer) == detector.window_size:
                trigger, prediction, confidence, erd = detector.process_window()
                
                # Update state
                bci_state['confidence'] = confidence
                bci_state['erd_values'] = erd
                
                if trigger:
                    bci_state['trigger_detected'] = True
                    bci_state['last_trigger_time'] = time.time()
                    print(f"\nTRIGGER DETECTED - Confidence: {confidence:.0%}")
        
        time.sleep(1 / Config.SAMPLING_RATE)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*60)
    print(" " * 15 + "BCI FLUTTER BRIDGE SERVER")
    print("="*60)
    print("\nServer starting on http://localhost:5000")
    print("\nAvailable endpoints:")
    print("  POST /system/initialize     - Initialize EEG hardware")
    print("  POST /calibration/start     - Start 60s baseline")
    print("  GET  /calibration/progress  - Get calibration progress")
    print("  POST /training/start        - Start training trials")
    print("  GET  /training/progress     - Get training progress")
    print("  POST /detection/start       - Start MI detection")
    print("  GET  /detection/poll        - Check for triggers")
    print("  POST /system/shutdown       - Shutdown system")
    print("\n" + "="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)