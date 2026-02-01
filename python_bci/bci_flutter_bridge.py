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
    'erd_values': {}
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


@app.route('/training/start', methods=['POST'])
def start_training():
    """Start training trial"""
    global bci_state
    
    if bci_state['status'] != 'idle' or baseline is None:
        return jsonify({'error': 'Calibration must be completed first'}), 400
    
    bci_state['status'] = 'training'
    bci_state['current_trial'] = 0
    bci_state['total_trials'] = Config.TRAINING_TRIALS
    
    # Start training in background thread
    threading.Thread(target=run_training, daemon=True).start()
    
    return jsonify({
        'message': 'Training started',
        'total_trials': Config.TRAINING_TRIALS
    })


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


@app.route('/system/initialize', methods=['POST'])
def initialize_system():
    """Initialize EEG hardware"""
    global stream, processor
    
    try:
        stream = EEGStream(Config.BOARD_ID, Config.SERIAL_PORT)
        processor = SignalProcessor(Config.SAMPLING_RATE)
        stream.start()
        
        bci_state['status'] = 'idle'
        
        return jsonify({'message': 'System initialized successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
    global baseline, bci_state
    
    calibrator = BaselineCalibrator(stream, processor)
    
    # Update progress during calibration
    duration = Config.BASELINE_DURATION
    start_time = time.time()
    
    def progress_callback():
        elapsed = time.time() - start_time
        bci_state['baseline_progress'] = min(100, int((elapsed / duration) * 100))
    
    # Start progress updater
    def update_progress():
        while bci_state['status'] == 'calibrating':
            progress_callback()
            time.sleep(0.5)
    
    threading.Thread(target=update_progress, daemon=True).start()
    
    # Run calibration
    baseline = calibrator.collect(duration)
    
    bci_state['status'] = 'idle'
    bci_state['baseline_progress'] = 100
    print("Calibration complete")


def run_training():
    """Run training data collection in background"""
    global classifier, bci_state, baseline
    
    trainer = TrainingCollector(stream, processor, baseline)
    
    # Collect training data trial by trial
    training_data = {
        'rest': {'features': [], 'labels': []},
        'mi': {'features': [], 'labels': []}
    }
    
    for trial in range(Config.TRAINING_TRIALS):
        bci_state['current_trial'] = trial + 1
        
        # Wait for Flutter to trigger animation
        print(f"\nTrial {trial + 1}/{Config.TRAINING_TRIALS} - Waiting for trigger...")
        
        # This would be called when animation starts in Flutter
        # For now, simulate with a delay
        time.sleep(Config.TRIAL_DURATION + Config.REST_DURATION)
        
        # Collect trial data (simplified)
        # trial_data = trainer.collect_single_trial()
        # training_data['mi']['features'].append(trial_data)
    
    # Train classifier
    print("\nTraining classifier...")
    classifier = MIClassifier()
    # classifier.train(training_data)
    
    bci_state['status'] = 'idle'
    print("✓ Training complete")


def run_detection():
    """Run real-time detection in background"""
    global detector, bci_state, baseline, classifier
    
    detector = RealTimeDetector(stream, processor, baseline, classifier)
    
    print("\nStarting real-time detection...")
    
    # Modified detection loop that updates bci_state
    while bci_state['status'] == 'detecting':
        data = stream.get_data(1)
        
        if data.shape[1] > 0:
            c3_sample = data[Config.C3_CHANNEL][0]
            c4_sample = data[Config.C4_CHANNEL][0]
            
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