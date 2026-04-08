# # """
# # BCI Flutter Bridge Server
# # =========================
# # HTTP server that connects the BCI Python system with Flutter app

# # The server will run on http://localhost:5000
# # """

# # from flask import Flask, jsonify, request
# # from flask_cors import CORS
# # import threading
# # import time
# # import json
# # from datetime import datetime
# # import queue
# # import numpy as np

# # from bci_motor_imagery_complete import (
# #     EEGStream, SignalProcessor, BaselineCalibrator, 
# #     TrainingCollector, MIClassifier, RealTimeDetector, Config
# # )

# # app = Flask(__name__)
# # CORS(app)  # Allow Flutter to make requests

# # # Global state
# # bci_state = {
# #     'status': 'idle',  # idle, calibrating, training, detecting
# #     'baseline_progress': 0,
# #     'training_progress': 0,
# #     'current_trial': 0,
# #     'total_trials': 0,
# #     'trigger_detected': False,
# #     'last_trigger_time': None,
# #     'confidence': 0.0,
# #     'erd_values': {},
# #     'calibration_complete': False, 
# #     'hardware_initialized': False,
# # }

# # # Communication queues
# # command_queue = queue.Queue()
# # event_queue = queue.Queue()

# # # BCI components (global references)
# # stream = None
# # processor = None
# # baseline = None
# # classifier = None
# # detector = None


# # # ============================================================================
# # # API ENDPOINTS
# # # ============================================================================

# # @app.route('/status', methods=['GET'])
# # def get_status():
# #     """Get current BCI system status"""
# #     return jsonify(bci_state)


# # @app.route('/calibration/start', methods=['POST'])
# # def start_calibration():
# #     """Start baseline calibration (60 seconds)"""
# #     global bci_state
    
# #     if bci_state['status'] != 'idle':
# #         return jsonify({'error': 'System busy'}), 400
    
# #     bci_state['status'] = 'calibrating'
# #     bci_state['baseline_progress'] = 0
    
# #     # Start calibration in background thread
# #     threading.Thread(target=run_calibration, daemon=True).start()
    
# #     return jsonify({'message': 'Calibration started', 'duration': Config.BASELINE_DURATION})


# # @app.route('/calibration/progress', methods=['GET'])
# # def get_calibration_progress():
# #     """Get calibration progress (0-100%)"""
# #     return jsonify({
# #         'progress': bci_state['baseline_progress'],
# #         'status': bci_state['status']
# #     })

# # @app.route('/calibration/status', methods=['GET'])
# # def calibration_status():
# #     return jsonify({
# #         'complete': bci_state.get('calibration_complete', False),
# #         'status': bci_state.get('status'),
# #         'progress': bci_state.get('baseline_progress', 0)
# #     })


# # @app.route('/training/start', methods=['POST'])
# # def start_training():
# #     """Start training session"""
# #     global bci_state, baseline
    
# #     if not bci_state.get('calibration_complete', False):
# #         return jsonify({'error': 'Calibration failed or not completed'}), 400

    
# #     if bci_state['status'] != 'idle':
# #         return jsonify({'error': f'System busy (status: {bci_state["status"]})'}), 400
    
# #     print("\n" + "="*60)
# #     print("TRAINING SESSION STARTING")
# #     print("="*60)
    
# #     bci_state['status'] = 'training'
# #     bci_state['current_trial'] = 0
# #     bci_state['total_trials'] = Config.TRAINING_TRIALS
    
# #     # Start training in background thread
# #     threading.Thread(target=run_training, daemon=True).start()
    
# #     return jsonify({
# #         'message': 'Training started',
# #         'total_trials': Config.TRAINING_TRIALS,
# #         'trial_duration': Config.TRIAL_DURATION
# #     })

# # @app.route('/training/trial_start', methods=['POST'])
# # def trial_start():
# #     """Signal that Flutter animation has started - begin collecting data"""
# #     global bci_state
    
# #     current_status = bci_state['status']
    
# #     if current_status == 'training':
# #         bci_state['status'] = 'collecting_trial'
# #         print("Trial collection triggered by Flutter")
# #         return jsonify({'message': 'Trial data collection started'})
# #     else:
# #         return jsonify({
# #             'error': f'Not ready for trial (current status: {current_status})'
# #         }), 400


# # @app.route('/training/trigger', methods=['POST'])
# # def manual_trigger():
# #     """Manual trigger for training (when button is pressed)"""
# #     command_queue.put('trigger')
# #     return jsonify({'message': 'Trigger received'})


# # @app.route('/training/progress', methods=['GET'])
# # def get_training_progress():
# #     """Get training progress"""
# #     return jsonify({
# #         'current_trial': bci_state['current_trial'],
# #         'total_trials': bci_state['total_trials'],
# #         'status': bci_state['status']
# #     })


# # @app.route('/detection/start', methods=['POST'])
# # def start_detection():
# #     """Start real-time motor imagery detection"""
# #     global bci_state, detector
    
# #     if classifier is None:
# #         return jsonify({'error': 'Training must be completed first'}), 400
    
# #     bci_state['status'] = 'detecting'
    
# #     # Start detector in background thread
# #     threading.Thread(target=run_detection, daemon=True).start()
    
# #     return jsonify({'message': 'Detection started'})


# # @app.route('/detection/stop', methods=['POST'])
# # def stop_detection():
# #     """Stop real-time detection"""
# #     global bci_state
# #     bci_state['status'] = 'idle'
# #     return jsonify({'message': 'Detection stopped'})


# # @app.route('/detection/poll', methods=['GET'])
# # def poll_detection():
# #     """Poll for motor imagery detection (call this repeatedly from Flutter)"""
# #     trigger = bci_state['trigger_detected']
    
# #     # Reset trigger after reading
# #     if trigger:
# #         bci_state['trigger_detected'] = False
    
# #     return jsonify({
# #         'trigger': trigger,
# #         'confidence': bci_state['confidence'],
# #         'erd_values': bci_state['erd_values'],
# #         'timestamp': bci_state['last_trigger_time']
# #     })

# # @app.route('/system/initialize', methods=['POST']) # ONLY INITIALIZE ONCE IN MAIN
# # def initialize_system():
# #     global stream, processor, bci_state

# #     if bci_state['hardware_initialized']:
# #         print("Initialize called again — ignored")
# #         return jsonify({'message': 'Already initialized'})

# #     print("Initializing EEG Hardware...")

# #     stream = EEGStream(Config.BOARD_ID, Config.SERIAL_PORT)
# #     processor = SignalProcessor(Config.SAMPLING_RATE)
# #     stream.start()

# #     bci_state['hardware_initialized'] = True
# #     bci_state['status'] = 'idle'

# #     return jsonify({'message': 'System initialized successfully'})



# # @app.route('/system/shutdown', methods=['POST'])
# # def shutdown_system():
# #     """Shutdown EEG hardware"""
# #     global stream, bci_state
    
# #     if stream:
# #         stream.stop()
    
# #     bci_state['status'] = 'idle'
    
# #     return jsonify({'message': 'System shutdown'})


# # # ============================================================================
# # # BACKGROUND WORKER FUNCTIONS
# # # ============================================================================

# # def run_calibration():
# #     """Run baseline calibration in background."""
# #     global baseline, bci_state, stream, processor

# #     print("\n" + "="*60)
# #     print("BASELINE CALIBRATION STARTING")
# #     print("="*60)

# #     if stream is None:
# #         print("Error: EEG stream not initialized!")
# #         bci_state['status'] = 'idle'
# #         return

# #     if processor is None:
# #         print("Error: Signal processor not initialized!")
# #         bci_state['status'] = 'idle'
# #         return

# #     try:
# #         duration   = Config.BASELINE_DURATION
# #         start_time = time.time()

# #         # ── Progress updater thread ──────────────────────────────────────────
# #         def update_progress():
# #             while bci_state['status'] == 'calibrating':
# #                 elapsed  = time.time() - start_time
# #                 progress = min(99, int((elapsed / duration) * 100))
# #                 bci_state['baseline_progress'] = progress
# #                 time.sleep(1)

# #         threading.Thread(target=update_progress, daemon=True).start()

# #         # ── Wait for channel config to finish ────────────────────────────────
# #         # The Neuropawn config_board calls take ~8 s (8 channels × 2 cmds × 0.5 s).
# #         # We wait an extra buffer so no config warnings pollute calibration data.
# #         config_settle = 12   # seconds — increase if you still see sync warnings
# #         print(f"Waiting {config_settle}s for channel configuration to settle...")
# #         time.sleep(config_settle)

# #         # Clear whatever landed in the buffer during config
# #         print("Clearing config-phase buffer...")
# #         _ = stream.board.get_board_data()          # drains and discards
# #         time.sleep(1)                               # brief settle

# #         # ── Collect ──────────────────────────────────────────────────────────
# #         # Simply sleep for the baseline duration.  BrainFlow's acquisition
# #         # thread silently fills its ring buffer the whole time.
# #         # One get_board_data() call at the end drains everything reliably.
# #         print(f">>> COLLECTING BASELINE ({duration}s) <<<")
# #         start_time = time.time()                    # reset for progress calc
# #         time.sleep(duration)

# #         data = stream.board.get_board_data()        # drain entire ring buffer

# #         if data is None or data.shape[1] == 0:
# #             raise RuntimeError(
# #                 f"No EEG data in buffer after {duration}s.\n"
# #                 "Possible causes:\n"
# #                 "  1. Channel config is still running — increase config_settle above\n"
# #                 "  2. Board lost connection during baseline\n"
# #                 "  3. BrainFlow ring buffer was cleared elsewhere"
# #             )

# #         print(f"Collected {data.shape[1]} samples "
# #               f"({data.shape[1]/Config.SAMPLING_RATE:.1f}s at {Config.SAMPLING_RATE}Hz)")

# #         # ── Channel indexing ─────────────────────────────────────────────────
# #         # stream.eeg_channels = [1,2,3,4,5,6,7,8] — these are the ROW indices
# #         # in BrainFlow's data matrix (not 0-based EEG positions).
# #         # Config.C3_CHANNEL = 3  means the 3rd EEG electrode.
# #         # eeg_channels[C3_CHANNEL - 1] = eeg_channels[2] = 3 → data row 3.
# #         eeg_ch = stream.eeg_channels
# #         c3_row = eeg_ch[Config.C3_CHANNEL - 1]   # correct BrainFlow row index
# #         c4_row = eeg_ch[Config.C4_CHANNEL - 1]

# #         print(f"Using BrainFlow rows: C3={c3_row}, C4={c4_row}")

# #         c3_data = data[c3_row]
# #         c4_data = data[c4_row]

# #         print(f"C3 samples: {len(c3_data)}, C4 samples: {len(c4_data)}")

# #         # ── Signal processing ────────────────────────────────────────────────
# #         print("Processing signals...")
# #         c3_clean = processor.preprocess(c3_data)
# #         c4_clean = processor.preprocess(c4_data)

# #         print("Computing baseline power...")
# #         baseline = {
# #             'c3_mu_power':   processor.compute_psd(c3_clean, Config.MU_BAND),
# #             'c3_beta_power': processor.compute_psd(c3_clean, Config.BETA_BAND),
# #             'c4_mu_power':   processor.compute_psd(c4_clean, Config.MU_BAND),
# #             'c4_beta_power': processor.compute_psd(c4_clean, Config.BETA_BAND),
# #         }

# #         bci_state['calibration_complete'] = True
# #         bci_state['status']               = 'idle'
# #         bci_state['baseline_progress']    = 100

# #         print("\n" + "="*60)
# #         print("BASELINE CALIBRATION COMPLETE")
# #         print("="*60)
# #         print(f"C3 - Mu: {baseline['c3_mu_power']:.4f}  Beta: {baseline['c3_beta_power']:.4f}")
# #         print(f"C4 - Mu: {baseline['c4_mu_power']:.4f}  Beta: {baseline['c4_beta_power']:.4f}")
# #         print("="*60 + "\n")

# #     except Exception as e:
# #         print("\n" + "="*60)
# #         print("CALIBRATION FAILED")
# #         print("="*60)
# #         print(f"Error: {e}")
# #         import traceback
# #         traceback.print_exc()
# #         print("="*60 + "\n")
# #         bci_state['status']               = 'idle'
# #         bci_state['calibration_complete'] = False
# #         baseline                          = None


# # def run_training():
# #     """Run training data collection in background"""
# #     global classifier, bci_state, baseline, stream, processor
    
# #     if baseline is None: # make sure we have baseline first - home screen will be removed later so this shoujldnt be a problem
# #         print("Error: Baseline not collected")
# #         bci_state['status'] = 'idle'
# #         return
    
# #     print("\n" + "="*60)
# #     print("TRAINING DATA COLLECTION")
# #     print("="*60)
# #     print(f"Collecting {Config.TRAINING_TRIALS} trials")
# #     print("Waiting for Flutter to trigger animations...")
# #     print("="*60 + "\n")
    
# #     all_trials = []
    
# #     for trial_num in range(Config.TRAINING_TRIALS):
# #         bci_state['current_trial'] = trial_num
        
# #         print(f"\n[Trial {trial_num + 1}/{Config.TRAINING_TRIALS}]")
# #         print("Waiting for Flutter animation to start...")
        
# #         # Wait for Flutter to signal trial start
# #         wait_start = time.time()
# #         while bci_state['status'] == 'training':
# #             time.sleep(0.1)
            
# #             # Check if we've been waiting too long
# #             if time.time() - wait_start > 30:
# #                 print("Timeout waiting for trial - skipping")
# #                 break
        
# #         if bci_state['status'] == 'collecting_trial':
# #             print("Animation started - collecting EEG data...")
            
# #             # Collect data during the animation (4 seconds)
# #             try:
# #                 trial_data = collect_trial_data(stream, processor, baseline)
# #                 all_trials.append(trial_data)
                
# #                 print(f"Trial {trial_num + 1} complete!")
# #                 print(f"  ERD values: C3μ={trial_data['c3_mu_erd']:.1f}%, C4μ={trial_data['c4_mu_erd']:.1f}%")
                
# #             except Exception as e:
# #                 print(f"Error collecting trial: {e}")
# #                 import traceback
# #                 traceback.print_exc()
            
# #             # Reset status for next trial
# #             bci_state['status'] = 'training'
# #         else:
# #             # Training was stopped
# #             print("Training interrupted by user")
# #             break
    
# #     # Update final trial count
# #     bci_state['current_trial'] = len(all_trials)
    
# #     # Now train the classifier if we have enough trials
# #     if len(all_trials) >= 10:  # Need at least 10 trials
# #         print("\n" + "="*60)
# #         print("TRAINING CLASSIFIER")
# #         print("="*60)
# #         print(f"Using {len(all_trials)} trials")
        
# #         try:
# #             classifier = MIClassifier()
# #             training_data = prepare_training_data(all_trials)
            
# #             print("Training model...")
# #             classifier.train(training_data)
            
# #             print("Classifier trained successfully!")
# #             print("="*60 + "\n")
            
# #         except Exception as e:
# #             print(f"Classifier training failed: {e}")
# #             import traceback
# #             traceback.print_exc()
# #     else:
# #         print(f"\nNot enough trials collected ({len(all_trials)}/{Config.TRAINING_TRIALS})")
# #         print("Classifier not trained - need at least 10 trials")
    
# #     bci_state['status'] = 'idle'
# #     print("\n Training session complete\n")


# # def collect_trial_data(stream, processor, baseline):
# #     """Collect EEG data for one trial (1.8 seconds during animation)"""
# #     import time
    
# #     # Clear buffer
# #     stream.clear_buffer()
    
# #     # Collect for trial duration
# #     duration = 1.8  # shooting phase seconds
# #     samples_needed = int(duration * Config.SAMPLING_RATE)
    
# #     print(f"  Collecting {samples_needed} samples ({duration}s)...")
    
# #     c3_data = []
# #     c4_data = []
    
# #     start_time = time.time()
# #     sample_count = 0
    
# #     while sample_count < samples_needed:
# #         data = stream.get_data(1)
        
# #         if data.shape[1] > 0:
# #             eeg_ch = stream.eeg_channels
# #             c3_data.append(data[eeg_ch[Config.C3_CHANNEL - 1]][0])
# #             c4_data.append(data[eeg_ch[Config.C4_CHANNEL - 1]][0])
# #             sample_count += 1
        
# #         time.sleep(1 / Config.SAMPLING_RATE)
        
# #         # Timeout safety
# #         if time.time() - start_time > duration + 2:
# #             print(f"Collection timeout - got {sample_count}/{samples_needed} samples")
# #             break
    
# #     print(f"Collected {sample_count} samples")
    
# #     # Convert to numpy arrays
# #     c3_signal = np.array(c3_data)
# #     c4_signal = np.array(c4_data)
    
# #     # Bandpass filter
# #     c3_filtered = processor.bandpass_filter(c3_signal)
# #     c4_filtered = processor.bandpass_filter(c4_signal)
    
# #     # Compute psd in mu and beta bands
# #     c3_mu_power = processor.compute_psd(c3_filtered, Config.MU_BAND)
# #     c3_beta_power = processor.compute_psd(c3_filtered, Config.BETA_BAND)
# #     c4_mu_power = processor.compute_psd(c4_filtered, Config.MU_BAND)
# #     c4_beta_power = processor.compute_psd(c4_filtered, Config.BETA_BAND)
    
# #     # Compute ERD 
# #     c3_mu_erd = processor.compute_erd(c3_mu_power, baseline['c3_mu_power'])
# #     c3_beta_erd = processor.compute_erd(c3_beta_power, baseline['c3_beta_power'])
# #     c4_mu_erd = processor.compute_erd(c4_mu_power, baseline['c4_mu_power'])
# #     c4_beta_erd = processor.compute_erd(c4_beta_power, baseline['c4_beta_power'])
    
# #     return {
# #         'c3_mu_erd': c3_mu_erd,
# #         'c3_beta_erd': c3_beta_erd,
# #         'c4_mu_erd': c4_mu_erd,
# #         'c4_beta_erd': c4_beta_erd,
# #         'label': 1  # Motor imagery
# #     }

# # def prepare_training_data(trials):
# #     """Convert trial data to format for classifier"""
# #     training_data = []
    
# #     for trial in trials:
# #         # Create feature vector from ERD values
# #         feature_vector = [
# #             trial['c3_mu_erd'],
# #             trial['c3_beta_erd'],
# #             trial['c4_mu_erd'],
# #             trial['c4_beta_erd']
# #         ]
        
# #         # Add to training data with proper format
# #         training_data.append({
# #             'features': feature_vector,
# #             'label': trial['label']  # Should be 1 for motor imagery
# #         })
    
# #     return training_data


# # def run_detection():
# #     """Run real-time detection in background"""
# #     global detector, bci_state, baseline, classifier
    
# #     detector = RealTimeDetector(stream, processor, baseline, classifier)
    
# #     print("\nStarting real-time detection...")
    
# #     # Modified detection loop that updates bci_state
# #     while bci_state['status'] == 'detecting':
# #         data = stream.get_data(1)
        
# #         if data.shape[1] > 0:
# #             eeg_ch    = stream.eeg_channels
# #             c3_sample = data[eeg_ch[Config.C3_CHANNEL - 1]][0]
# #             c4_sample = data[eeg_ch[Config.C4_CHANNEL - 1]][0]
            
# #             detector.add_sample(c3_sample, c4_sample)
            
# #             # Process window
# #             if len(detector.c3_buffer) == detector.window_size:
# #                 trigger, prediction, confidence, erd = detector.process_window()
                
# #                 # Update state
# #                 bci_state['confidence'] = confidence
# #                 bci_state['erd_values'] = erd
                
# #                 if trigger:
# #                     bci_state['trigger_detected'] = True
# #                     bci_state['last_trigger_time'] = time.time()
# #                     print(f"\nTRIGGER DETECTED - Confidence: {confidence:.0%}")
        
# #         time.sleep(1 / Config.SAMPLING_RATE)


# # # ============================================================================
# # # MAIN
# # # ============================================================================

# # if __name__ == '__main__':
# #     print("\n" + "="*60)
# #     print(" " * 15 + "BCI FLUTTER BRIDGE SERVER")
# #     print("="*60)
# #     print("\nServer starting on http://localhost:5000")
# #     print("\nAvailable endpoints:")
# #     print("  POST /system/initialize     - Initialize EEG hardware")
# #     print("  POST /calibration/start     - Start 60s baseline")
# #     print("  GET  /calibration/progress  - Get calibration progress")
# #     print("  POST /training/start        - Start training trials")
# #     print("  GET  /training/progress     - Get training progress")
# #     print("  POST /detection/start       - Start MI detection")
# #     print("  GET  /detection/poll        - Check for triggers")
# #     print("  POST /system/shutdown       - Shutdown system")
# #     print("\n" + "="*60 + "\n")
    
# #     app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)





























# # """
# # BCI Flutter Bridge Server
# # =========================
# # HTTP server that connects the BCI Python system with Flutter app

# # The server will run on http://localhost:5000
# # """

# # from flask import Flask, jsonify, request
# # from flask_cors import CORS
# # import threading
# # import time
# # import json
# # from datetime import datetime
# # import queue
# # import numpy as np

# # from bci_motor_imagery_complete import (
# #     EEGStream, SignalProcessor, BaselineCalibrator, 
# #     TrainingCollector, MIClassifier, RealTimeDetector, Config
# # )

# # app = Flask(__name__)
# # CORS(app)  # Allow Flutter to make requests

# # # Global state
# # bci_state = {
# #     'status': 'idle',  # idle, calibrating, training, detecting
# #     'baseline_progress': 0,
# #     'training_progress': 0,
# #     'current_trial': 0,
# #     'total_trials': 0,
# #     'trigger_detected': False,
# #     'last_trigger_time': None,
# #     'confidence': 0.0,
# #     'erd_values': {},
# #     'calibration_complete': False, 
# #     'hardware_initialized': False,
# # }

# # # Communication queues
# # command_queue = queue.Queue()
# # event_queue = queue.Queue()

# # # BCI components (global references)
# # stream = None
# # processor = None
# # baseline = None
# # classifier = None
# # detector = None


# # # ============================================================================
# # # API ENDPOINTS
# # # ============================================================================

# # @app.route('/status', methods=['GET'])
# # def get_status():
# #     """Get current BCI system status"""
# #     return jsonify(bci_state)


# # @app.route('/calibration/start', methods=['POST'])
# # def start_calibration():
# #     """Start baseline calibration (60 seconds)"""
# #     global bci_state
    
# #     if bci_state['status'] != 'idle':
# #         return jsonify({'error': 'System busy'}), 400
    
# #     bci_state['status'] = 'calibrating'
# #     bci_state['baseline_progress'] = 0
    
# #     # Start calibration in background thread
# #     threading.Thread(target=run_calibration, daemon=True).start()
    
# #     return jsonify({'message': 'Calibration started', 'duration': Config.BASELINE_DURATION})


# # @app.route('/calibration/progress', methods=['GET'])
# # def get_calibration_progress():
# #     """Get calibration progress (0-100%)"""
# #     return jsonify({
# #         'progress': bci_state['baseline_progress'],
# #         'status': bci_state['status']
# #     })

# # @app.route('/calibration/status', methods=['GET'])
# # def calibration_status():
# #     return jsonify({
# #         'complete': bci_state.get('calibration_complete', False),
# #         'status': bci_state.get('status'),
# #         'progress': bci_state.get('baseline_progress', 0)
# #     })


# # @app.route('/training/start', methods=['POST'])
# # def start_training():
# #     """Start training session"""
# #     global bci_state, baseline
    
# #     if not bci_state.get('calibration_complete', False):
# #         return jsonify({'error': 'Calibration failed or not completed'}), 400

    
# #     if bci_state['status'] != 'idle':
# #         return jsonify({'error': f'System busy (status: {bci_state["status"]})'}), 400
    
# #     print("\n" + "="*60)
# #     print("TRAINING SESSION STARTING")
# #     print("="*60)
    
# #     bci_state['status'] = 'training'
# #     bci_state['current_trial'] = 0
# #     bci_state['total_trials'] = Config.TRAINING_TRIALS
    
# #     # Start training in background thread
# #     threading.Thread(target=run_training, daemon=True).start()
    
# #     return jsonify({
# #         'message': 'Training started',
# #         'total_trials': Config.TRAINING_TRIALS,
# #         'trial_duration': Config.TRIAL_DURATION
# #     })

# # @app.route('/training/trial_start', methods=['POST'])
# # def trial_start():
# #     """Signal that Flutter animation has started - begin collecting data"""
# #     global bci_state
    
# #     current_status = bci_state['status']
    
# #     if current_status == 'training':
# #         bci_state['status'] = 'collecting_trial'
# #         print("Trial collection triggered by Flutter")
# #         return jsonify({'message': 'Trial data collection started'})
# #     else:
# #         return jsonify({
# #             'error': f'Not ready for trial (current status: {current_status})'
# #         }), 400


# # @app.route('/training/trigger', methods=['POST'])
# # def manual_trigger():
# #     """Manual trigger for training (when button is pressed)"""
# #     command_queue.put('trigger')
# #     return jsonify({'message': 'Trigger received'})


# # @app.route('/training/progress', methods=['GET'])
# # def get_training_progress():
# #     """Get training progress"""
# #     return jsonify({
# #         'current_trial': bci_state['current_trial'],
# #         'total_trials': bci_state['total_trials'],
# #         'status': bci_state['status']
# #     })


# # @app.route('/detection/start', methods=['POST'])
# # def start_detection():
# #     """Start real-time motor imagery detection"""
# #     global bci_state, detector
    
# #     if classifier is None:
# #         return jsonify({'error': 'Training must be completed first'}), 400
    
# #     bci_state['status'] = 'detecting'
    
# #     # Start detector in background thread
# #     threading.Thread(target=run_detection, daemon=True).start()
    
# #     return jsonify({'message': 'Detection started'})


# # @app.route('/detection/stop', methods=['POST'])
# # def stop_detection():
# #     """Stop real-time detection"""
# #     global bci_state
# #     bci_state['status'] = 'idle'
# #     return jsonify({'message': 'Detection stopped'})


# # @app.route('/detection/poll', methods=['GET'])
# # def poll_detection():
# #     """Poll for motor imagery detection (call this repeatedly from Flutter)"""
# #     trigger = bci_state['trigger_detected']
    
# #     # Reset trigger after reading
# #     if trigger:
# #         bci_state['trigger_detected'] = False
    
# #     return jsonify({
# #         'trigger': trigger,
# #         'confidence': bci_state['confidence'],
# #         'erd_values': bci_state['erd_values'],
# #         'timestamp': bci_state['last_trigger_time']
# #     })

# # @app.route('/system/initialize', methods=['POST']) # ONLY INITIALIZE ONCE IN MAIN
# # def initialize_system():
# #     global stream, processor, bci_state

# #     if bci_state['hardware_initialized']:
# #         print("Initialize called again — ignored")
# #         return jsonify({'message': 'Already initialized'})

# #     print("Initializing EEG Hardware...")

# #     stream = EEGStream(Config.BOARD_ID, Config.SERIAL_PORT)
# #     processor = SignalProcessor(Config.SAMPLING_RATE)
# #     stream.start()

# #     bci_state['hardware_initialized'] = True
# #     bci_state['status'] = 'idle'

# #     return jsonify({'message': 'System initialized successfully'})



# # @app.route('/system/shutdown', methods=['POST'])
# # def shutdown_system():
# #     """Shutdown EEG hardware"""
# #     global stream, bci_state
    
# #     if stream:
# #         stream.stop()
    
# #     bci_state['status'] = 'idle'
    
# #     return jsonify({'message': 'System shutdown'})


# # # ============================================================================
# # # BACKGROUND WORKER FUNCTIONS
# # # ============================================================================

# # def run_calibration():
# #     """Run baseline calibration in background."""
# #     global baseline, bci_state, stream, processor

# #     print("\n" + "="*60)
# #     print("BASELINE CALIBRATION STARTING")
# #     print("="*60)

# #     if stream is None:
# #         print("Error: EEG stream not initialized!")
# #         bci_state['status'] = 'idle'
# #         return

# #     if processor is None:
# #         print("Error: Signal processor not initialized!")
# #         bci_state['status'] = 'idle'
# #         return

# #     try:
# #         duration   = Config.BASELINE_DURATION
# #         start_time = time.time()

# #         # ── Progress updater thread ──────────────────────────────────────────
# #         def update_progress():
# #             while bci_state['status'] == 'calibrating':
# #                 elapsed  = time.time() - start_time
# #                 progress = min(99, int((elapsed / duration) * 100))
# #                 bci_state['baseline_progress'] = progress
# #                 time.sleep(1)

# #         threading.Thread(target=update_progress, daemon=True).start()

# #         # ── Wait for channel config to finish ────────────────────────────────
# #         # The Neuropawn config_board calls take ~8 s (8 channels × 2 cmds × 0.5 s).
# #         # We wait an extra buffer so no config warnings pollute calibration data.
# #         config_settle = 12   # seconds — increase if you still see sync warnings
# #         print(f"Waiting {config_settle}s for channel configuration to settle...")
# #         time.sleep(config_settle)

# #         # Clear whatever landed in the buffer during config
# #         print("Clearing config-phase buffer...")
# #         _ = stream.board.get_board_data()          # drains and discards
# #         time.sleep(1)                               # brief settle

# #         # ── Collect ──────────────────────────────────────────────────────────
# #         # Simply sleep for the baseline duration.  BrainFlow's acquisition
# #         # thread silently fills its ring buffer the whole time.
# #         # One get_board_data() call at the end drains everything reliably.
# #         print(f">>> COLLECTING BASELINE ({duration}s) <<<")
# #         start_time = time.time()                    # reset for progress calc
# #         time.sleep(duration)

# #         data = stream.board.get_board_data()        # drain entire ring buffer

# #         if data is None or data.shape[1] == 0:
# #             raise RuntimeError(
# #                 f"No EEG data in buffer after {duration}s.\n"
# #                 "Possible causes:\n"
# #                 "  1. Channel config is still running — increase config_settle above\n"
# #                 "  2. Board lost connection during baseline\n"
# #                 "  3. BrainFlow ring buffer was cleared elsewhere"
# #             )

# #         print(f"Collected {data.shape[1]} samples "
# #               f"({data.shape[1]/Config.SAMPLING_RATE:.1f}s at {Config.SAMPLING_RATE}Hz)")

# #         # ── Channel indexing ─────────────────────────────────────────────────
# #         # stream.eeg_channels = [1,2,3,4,5,6,7,8] — these are the ROW indices
# #         # in BrainFlow's data matrix (not 0-based EEG positions).
# #         # Config.C3_CHANNEL = 3  means the 3rd EEG electrode.
# #         # eeg_channels[C3_CHANNEL - 1] = eeg_channels[2] = 3 → data row 3.
# #         eeg_ch = stream.eeg_channels
# #         c3_row = eeg_ch[Config.C3_CHANNEL - 1]   # correct BrainFlow row index
# #         c4_row = eeg_ch[Config.C4_CHANNEL - 1]

# #         print(f"Using BrainFlow rows: C3={c3_row}, C4={c4_row}")

# #         c3_data = data[c3_row]
# #         c4_data = data[c4_row]

# #         print(f"C3 samples: {len(c3_data)}, C4 samples: {len(c4_data)}")

# #         # ── Signal processing ────────────────────────────────────────────────
# #         print("Processing signals...")
# #         c3_clean = processor.preprocess(c3_data)
# #         c4_clean = processor.preprocess(c4_data)

# #         print("Computing baseline power...")
# #         baseline = {
# #             'c3_mu_power':   processor.compute_psd(c3_clean, Config.MU_BAND),
# #             'c3_beta_power': processor.compute_psd(c3_clean, Config.BETA_BAND),
# #             'c4_mu_power':   processor.compute_psd(c4_clean, Config.MU_BAND),
# #             'c4_beta_power': processor.compute_psd(c4_clean, Config.BETA_BAND),
# #         }

# #         bci_state['calibration_complete'] = True
# #         bci_state['status']               = 'idle'
# #         bci_state['baseline_progress']    = 100

# #         print("\n" + "="*60)
# #         print("BASELINE CALIBRATION COMPLETE")
# #         print("="*60)
# #         print(f"C3 - Mu: {baseline['c3_mu_power']:.4f}  Beta: {baseline['c3_beta_power']:.4f}")
# #         print(f"C4 - Mu: {baseline['c4_mu_power']:.4f}  Beta: {baseline['c4_beta_power']:.4f}")
# #         print("="*60 + "\n")

# #     except Exception as e:
# #         print("\n" + "="*60)
# #         print("CALIBRATION FAILED")
# #         print("="*60)
# #         print(f"Error: {e}")
# #         import traceback
# #         traceback.print_exc()
# #         print("="*60 + "\n")
# #         bci_state['status']               = 'idle'
# #         bci_state['calibration_complete'] = False
# #         baseline                          = None


# # def run_training():
# #     """Run training with paired REST + MOTOR IMAGERY trials.

# #     For each of the 20 trials the bridge:
# #       1. Immediately collects a 1.8 s REST window (no Flutter trigger needed)
# #       2. Waits for Flutter to signal the animation start
# #       3. Collects a 1.8 s MOTOR IMAGERY window during the animation

# #     This gives the LDA classifier both classes to discriminate between.
# #     """
# #     global classifier, bci_state, baseline, stream, processor

# #     if baseline is None:
# #         print("Error: Baseline not collected — run calibration first")
# #         bci_state['status'] = 'idle'
# #         return

# #     print("\n" + "="*60)
# #     print("TRAINING DATA COLLECTION")
# #     print("="*60)
# #     print(f"Collecting {Config.TRAINING_TRIALS} paired REST + IMAGERY trials")
# #     print("="*60 + "\n")

# #     rest_trials    = []
# #     imagery_trials = []

# #     for trial_num in range(Config.TRAINING_TRIALS):
# #         bci_state['current_trial'] = trial_num + 1

# #         print(f"\n[Trial {trial_num + 1}/{Config.TRAINING_TRIALS}]")

# #         # ── Step 1: collect REST window immediately ──────────────────────────
# #         try:
# #             print("  Collecting REST window...")
# #             rest_trial = collect_rest_trial_data(stream, processor, baseline)
# #             rest_trials.append(rest_trial)
# #             print(f"  REST complete: C3μ={rest_trial['c3_mu_erd']:.1f}%, "
# #                   f"C4μ={rest_trial['c4_mu_erd']:.1f}%")
# #         except Exception as e:
# #             print(f"  Error collecting REST trial: {e}")
# #             import traceback; traceback.print_exc()
# #             continue

# #         # ── Step 2: wait for Flutter animation trigger ───────────────────────
# #         print("  Waiting for Flutter animation...")
# #         wait_start = time.time()
# #         while bci_state['status'] == 'training':
# #             time.sleep(0.1)
# #             if time.time() - wait_start > 30:
# #                 print("  Timeout waiting for trial trigger — skipping")
# #                 break

# #         # ── Step 3: collect IMAGERY window ───────────────────────────────────
# #         if bci_state['status'] == 'collecting_trial':
# #             print("  Animation started — collecting MOTOR IMAGERY window...")
# #             try:
# #                 imagery_trial = collect_trial_data(stream, processor, baseline)
# #                 imagery_trials.append(imagery_trial)
# #                 print(f"  IMAGERY complete: C3μ={imagery_trial['c3_mu_erd']:.1f}%, "
# #                       f"C4μ={imagery_trial['c4_mu_erd']:.1f}%")
# #             except Exception as e:
# #                 print(f"  Error collecting imagery trial: {e}")
# #                 import traceback; traceback.print_exc()

# #             bci_state['status'] = 'training'
# #         else:
# #             print("  Training interrupted")
# #             break

# #     # ── Train classifier ─────────────────────────────────────────────────────
# #     paired_count   = min(len(rest_trials), len(imagery_trials))
# #     rest_trials    = rest_trials[:paired_count]
# #     imagery_trials = imagery_trials[:paired_count]
# #     bci_state['current_trial'] = paired_count

# #     if paired_count >= 10:
# #         print("\n" + "="*60)
# #         print("TRAINING CLASSIFIER")
# #         print("="*60)
# #         print(f"Using {paired_count} REST + {paired_count} IMAGERY trials")

# #         try:
# #             import os
# #             os.makedirs(Config.LOG_DIR, exist_ok=True)   # ensure dir exists

# #             classifier    = MIClassifier()
# #             training_data = prepare_training_data(rest_trials, imagery_trials)
# #             classifier.train(training_data)
# #             print("Classifier trained successfully!")
# #             print("="*60 + "\n")
# #         except Exception as e:
# #             print(f"Classifier training failed: {e}")
# #             import traceback; traceback.print_exc()
# #             classifier = None
# #     else:
# #         print(f"\nNot enough paired trials ({paired_count}/{Config.TRAINING_TRIALS})")
# #         classifier = None

# #     bci_state['status'] = 'idle'
# #     print("\nTraining session complete\n")


# # def collect_trial_data(stream, processor, baseline):
# #     """Collect EEG data for one trial (1.8 seconds during animation)"""
# #     import time
    
# #     # Clear buffer
# #     stream.clear_buffer()
    
# #     # Collect for trial duration
# #     duration = 1.8  # shooting phase seconds
# #     samples_needed = int(duration * Config.SAMPLING_RATE)
    
# #     print(f"  Collecting {samples_needed} samples ({duration}s)...")
    
# #     c3_data = []
# #     c4_data = []
    
# #     start_time = time.time()
# #     sample_count = 0
    
# #     while sample_count < samples_needed:
# #         data = stream.get_data(1)
        
# #         if data.shape[1] > 0:
# #             eeg_ch = stream.eeg_channels
# #             c3_data.append(data[eeg_ch[Config.C3_CHANNEL - 1]][0])
# #             c4_data.append(data[eeg_ch[Config.C4_CHANNEL - 1]][0])
# #             sample_count += 1
        
# #         time.sleep(1 / Config.SAMPLING_RATE)
        
# #         # Timeout safety
# #         if time.time() - start_time > duration + 2:
# #             print(f"Collection timeout - got {sample_count}/{samples_needed} samples")
# #             break
    
# #     print(f"Collected {sample_count} samples")
    
# #     # Convert to numpy arrays
# #     c3_signal = np.array(c3_data)
# #     c4_signal = np.array(c4_data)
    
# #     # Bandpass filter
# #     c3_filtered = processor.bandpass_filter(c3_signal)
# #     c4_filtered = processor.bandpass_filter(c4_signal)
    
# #     # Compute psd in mu and beta bands
# #     c3_mu_power = processor.compute_psd(c3_filtered, Config.MU_BAND)
# #     c3_beta_power = processor.compute_psd(c3_filtered, Config.BETA_BAND)
# #     c4_mu_power = processor.compute_psd(c4_filtered, Config.MU_BAND)
# #     c4_beta_power = processor.compute_psd(c4_filtered, Config.BETA_BAND)
    
# #     # Compute ERD 
# #     c3_mu_erd = processor.compute_erd(c3_mu_power, baseline['c3_mu_power'])
# #     c3_beta_erd = processor.compute_erd(c3_beta_power, baseline['c3_beta_power'])
# #     c4_mu_erd = processor.compute_erd(c4_mu_power, baseline['c4_mu_power'])
# #     c4_beta_erd = processor.compute_erd(c4_beta_power, baseline['c4_beta_power'])
    
# #     return {
# #         'c3_mu_erd': c3_mu_erd,
# #         'c3_beta_erd': c3_beta_erd,
# #         'c4_mu_erd': c4_mu_erd,
# #         'c4_beta_erd': c4_beta_erd,
# #         'label': 1  # Motor imagery
# #     }

# # def collect_rest_trial_data(stream, processor, baseline):
# #     """Collect 1.8 s of REST EEG (no motor imagery)."""
# #     stream.clear_buffer()

# #     duration       = 1.8
# #     samples_needed = int(duration * Config.SAMPLING_RATE)
# #     eeg_ch         = stream.eeg_channels

# #     c3_data, c4_data = [], []
# #     start_time       = time.time()
# #     sample_count     = 0

# #     while sample_count < samples_needed:
# #         data = stream.get_data(1)
# #         if data.shape[1] > 0:
# #             c3_data.append(data[eeg_ch[Config.C3_CHANNEL - 1]][0])
# #             c4_data.append(data[eeg_ch[Config.C4_CHANNEL - 1]][0])
# #             sample_count += 1
# #         time.sleep(1 / Config.SAMPLING_RATE)
# #         if time.time() - start_time > duration + 2:
# #             break

# #     c3_signal = np.array(c3_data)
# #     c4_signal = np.array(c4_data)

# #     c3_f = processor.bandpass_filter(c3_signal)
# #     c4_f = processor.bandpass_filter(c4_signal)

# #     return {
# #         'c3_mu_erd':   processor.compute_erd(processor.compute_psd(c3_f, Config.MU_BAND),   baseline['c3_mu_power']),
# #         'c3_beta_erd': processor.compute_erd(processor.compute_psd(c3_f, Config.BETA_BAND), baseline['c3_beta_power']),
# #         'c4_mu_erd':   processor.compute_erd(processor.compute_psd(c4_f, Config.MU_BAND),   baseline['c4_mu_power']),
# #         'c4_beta_erd': processor.compute_erd(processor.compute_psd(c4_f, Config.BETA_BAND), baseline['c4_beta_power']),
# #         'label': 0,
# #     }


# # def prepare_training_data(rest_trials, imagery_trials):
# #     """Build classifier training set from paired REST + IMAGERY trials."""
# #     training_data = []
# #     for trial in rest_trials:
# #         training_data.append({
# #             'features': [trial['c3_mu_erd'], trial['c3_beta_erd'],
# #                          trial['c4_mu_erd'], trial['c4_beta_erd']],
# #             'label': 0,
# #         })
# #     for trial in imagery_trials:
# #         training_data.append({
# #             'features': [trial['c3_mu_erd'], trial['c3_beta_erd'],
# #                          trial['c4_mu_erd'], trial['c4_beta_erd']],
# #             'label': 1,
# #         })
# #     return training_data


# # def run_detection():
# #     """Run real-time detection in background"""
# #     global detector, bci_state, baseline, classifier
    
# #     detector = RealTimeDetector(stream, processor, baseline, classifier)
    
# #     print("\nStarting real-time detection...")
    
# #     # Modified detection loop that updates bci_state
# #     while bci_state['status'] == 'detecting':
# #         data = stream.get_data(1)
        
# #         if data.shape[1] > 0:
# #             eeg_ch    = stream.eeg_channels
# #             c3_sample = data[eeg_ch[Config.C3_CHANNEL - 1]][0]
# #             c4_sample = data[eeg_ch[Config.C4_CHANNEL - 1]][0]
            
# #             detector.add_sample(c3_sample, c4_sample)
            
# #             # Process window
# #             if len(detector.c3_buffer) == detector.window_size:
# #                 trigger, prediction, confidence, erd = detector.process_window()
                
# #                 # Update state
# #                 bci_state['confidence'] = confidence
# #                 bci_state['erd_values'] = erd
                
# #                 if trigger:
# #                     bci_state['trigger_detected'] = True
# #                     bci_state['last_trigger_time'] = time.time()
# #                     print(f"\nTRIGGER DETECTED - Confidence: {confidence:.0%}")
        
# #         time.sleep(1 / Config.SAMPLING_RATE)


# # # ============================================================================
# # # MAIN
# # # ============================================================================

# # if __name__ == '__main__':
# #     print("\n" + "="*60)
# #     print(" " * 15 + "BCI FLUTTER BRIDGE SERVER")
# #     print("="*60)
# #     print("\nServer starting on http://localhost:5000")
# #     print("\nAvailable endpoints:")
# #     print("  POST /system/initialize     - Initialize EEG hardware")
# #     print("  POST /calibration/start     - Start 60s baseline")
# #     print("  GET  /calibration/progress  - Get calibration progress")
# #     print("  POST /training/start        - Start training trials")
# #     print("  GET  /training/progress     - Get training progress")
# #     print("  POST /detection/start       - Start MI detection")
# #     print("  GET  /detection/poll        - Check for triggers")
# #     print("  POST /system/shutdown       - Shutdown system")
# #     print("\n" + "="*60 + "\n")
    
# #     app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)










# """
# VERSION FOR THE FIXED INIT BCI
# BCI Flutter Bridge Server
# =========================
# HTTP server that connects the BCI Python system with Flutter app

# The server will run on http://localhost:5000
# """

# from flask import Flask, jsonify, request
# from flask_cors import CORS
# import threading
# import time
# import json
# from datetime import datetime
# import queue
# import numpy as np

# from bci_motor_imagery_complete import (
#     EEGStream, SignalProcessor, BaselineCalibrator,
#     TrainingCollector, MIClassifier, RealTimeDetector, Config
# )
# from brainflow.board_shim import BoardIds

# app = Flask(__name__)
# CORS(app)  # Allow Flutter to make requests

# # Global state
# bci_state = {
#     'status': 'idle',  # idle, calibrating, training, detecting
#     'baseline_progress': 0,
#     'training_progress': 0,
#     'current_trial': 0,
#     'total_trials': 0,
#     'trigger_detected': False,
#     'last_trigger_time': None,
#     'confidence': 0.0,
#     'erd_values': {},
#     'calibration_complete': False, 
#     'hardware_initialized': False,
# }

# # Communication queues
# command_queue = queue.Queue()
# event_queue = queue.Queue()

# # BCI components (global references)
# stream = None
# processor = None
# baseline = None
# classifier = None
# detector = None


# # ============================================================================
# # API ENDPOINTS
# # ============================================================================

# @app.route('/status', methods=['GET'])
# def get_status():
#     """Get current BCI system status.

#     Returns keys matching BCIStatus.fromJson() in bci_service.dart.
#     """
#     return jsonify({
#         # Flutter-facing keys
#         'initialized':      bci_state['hardware_initialized'],
#         'calibrated':       bci_state.get('calibration_complete', False),
#         'trained':          classifier is not None,
#         'detecting':        bci_state['status'] == 'detecting',
#         'mode':             bci_state['status'],
#         'last_confidence':  bci_state.get('confidence', 0.0),
#         # Extra detail
#         'baseline_progress': bci_state.get('baseline_progress', 0),
#         'current_trial':     bci_state.get('current_trial', 0),
#         'total_trials':      bci_state.get('total_trials', 0),
#     })


# @app.route('/calibration/start', methods=['POST'])
# def start_calibration():
#     """Start baseline calibration (60 seconds)"""
#     global bci_state
    
#     if bci_state['status'] != 'idle':
#         return jsonify({'error': 'System busy'}), 400
    
#     bci_state['status'] = 'calibrating'
#     bci_state['baseline_progress'] = 0
    
#     # Start calibration in background thread
#     threading.Thread(target=run_calibration, daemon=True).start()
    
#     return jsonify({'message': 'Calibration started', 'duration': Config.BASELINE_DURATION})


# @app.route('/calibration/progress', methods=['GET'])
# def get_calibration_progress():
#     """Get calibration progress (0-100%)"""
#     return jsonify({
#         'progress': bci_state['baseline_progress'],
#         'status': bci_state['status']
#     })

# @app.route('/calibration/status', methods=['GET'])
# def calibration_status():
#     return jsonify({
#         'complete': bci_state.get('calibration_complete', False),
#         'status': bci_state.get('status'),
#         'progress': bci_state.get('baseline_progress', 0)
#     })


# @app.route('/training/start', methods=['POST'])
# def start_training():
#     """Start training session"""
#     global bci_state, baseline
    
#     if not bci_state.get('calibration_complete', False):
#         return jsonify({'error': 'Calibration failed or not completed'}), 400

    
#     if bci_state['status'] != 'idle':
#         return jsonify({'error': f'System busy (status: {bci_state["status"]})'}), 400
    
#     print("\n" + "="*60)
#     print("TRAINING SESSION STARTING")
#     print("="*60)
    
#     bci_state['status'] = 'training'
#     bci_state['current_trial'] = 0
#     bci_state['total_trials'] = Config.TRAINING_TRIALS
    
#     # Start training in background thread
#     threading.Thread(target=run_training, daemon=True).start()
    
#     return jsonify({
#         'message': 'Training started',
#         'total_trials': Config.TRAINING_TRIALS,
#         'trial_duration': Config.TRIAL_DURATION
#     })

# @app.route('/training/trial_start', methods=['POST'])
# def trial_start():
#     """Signal that Flutter animation has started - begin collecting data"""
#     global bci_state
    
#     current_status = bci_state['status']
    
#     if current_status == 'training':
#         bci_state['status'] = 'collecting_trial'
#         print("Trial collection triggered by Flutter")
#         return jsonify({'message': 'Trial data collection started'})
#     else:
#         return jsonify({
#             'error': f'Not ready for trial (current status: {current_status})'
#         }), 400


# @app.route('/training/trigger', methods=['POST'])
# def manual_trigger():
#     """Manual trigger for training (when button is pressed)"""
#     command_queue.put('trigger')
#     return jsonify({'message': 'Trigger received'})


# @app.route('/training/progress', methods=['GET'])
# def get_training_progress():
#     """Get training progress"""
#     return jsonify({
#         'current_trial': bci_state['current_trial'],
#         'total_trials': bci_state['total_trials'],
#         'status': bci_state['status']
#     })


# @app.route('/detection/start', methods=['POST'])
# def start_detection():
#     """Start real-time motor imagery detection"""
#     global bci_state, detector
    
#     if classifier is None:
#         return jsonify({'error': 'Training must be completed first'}), 400
    
#     bci_state['status'] = 'detecting'
    
#     # Start detector in background thread
#     threading.Thread(target=run_detection, daemon=True).start()
    
#     return jsonify({'message': 'Detection started'})


# @app.route('/detection/stop', methods=['POST'])
# def stop_detection():
#     """Stop real-time detection"""
#     global bci_state
#     bci_state['status'] = 'idle'
#     return jsonify({'message': 'Detection stopped'})


# @app.route('/detection/poll', methods=['GET'])
# def poll_detection():
#     """Poll for motor imagery detection (call this repeatedly from Flutter)"""
#     trigger = bci_state['trigger_detected']
    
#     # Reset trigger after reading
#     if trigger:
#         bci_state['trigger_detected'] = False
    
#     return jsonify({
#         'trigger': trigger,
#         'confidence': bci_state['confidence'],
#         'erd_values': bci_state['erd_values'],
#         'timestamp': bci_state['last_trigger_time']
#     })

# @app.route('/system/initialize', methods=['POST']) # ONLY INITIALIZE ONCE IN MAIN
# def initialize_system():
#     global stream, processor, bci_state

#     if bci_state['hardware_initialized']:
#         print("Initialize called again — ignored")
#         return jsonify({'message': 'Already initialized',
#                         'hardware_initialized': True})

#     # Block re-init if a calibration/training/detection is in progress
#     if bci_state['status'] not in ('idle', ''):
#         msg = f"Cannot initialize while status is '{bci_state['status']}'"
#         print(f"Initialize blocked: {msg}")
#         return jsonify({'error': msg}), 400

#     print("Initializing EEG Hardware...")

#     # Run the slow stream.start() (Neuropawn config takes ~15s) in a
#     # background thread so the HTTP response returns immediately.
#     # Flutter polls /status to know when initialization is complete.
#     bci_state['status'] = 'initializing'

#     def _do_init():
#         global stream, processor
#         try:
#             print("[init] Creating EEGStream...")
#             stream    = EEGStream(Config.BOARD_ID, Config.SERIAL_PORT)
#             processor = SignalProcessor(Config.SAMPLING_RATE)

#             print("[init] Preparing session and starting stream...")
#             stream.board.prepare_session()
#             stream.board.start_stream(450000)
#             stream.is_streaming = True
#             print("[init] Stream started. Skipping channel config for fast init.")
#             print("[init] You can recalibrate after init if signal quality is poor.")

#             # Mark as initialized BEFORE the slow channel config
#             # so Flutter sees it immediately. Config runs in background.
#             bci_state['hardware_initialized'] = True
#             bci_state['status']               = 'idle'
#             print("=" * 60)
#             print("EEG HARDWARE INITIALIZATION COMPLETE")
#             print("Flutter will now see initialized=True on next /status poll")
#             print("=" * 60)

#             # Now run channel config in background — won't block Flutter
#             import time as _time
#             _time.sleep(2)   # brief stabilization
#             # Run Neuropawn config — compare by board ID int value to be safe
#             neuropawn_val = BoardIds.NEUROPAWN_KNIGHT_BOARD.value
#             board_val = (stream.board_id.value
#                          if hasattr(stream.board_id, 'value')
#                          else int(stream.board_id))
#             if board_val == neuropawn_val:
#                 print("[init] Running Neuropawn channel configuration in background...")
#                 stream.configure_neuropawn(Config.NUM_CHANNELS)
#                 _ = stream.board.get_board_data()  # clear config-phase data
#                 _time.sleep(3)
#                 print("[init] Neuropawn configuration complete. Ready for calibration.")

#         except Exception as exc:
#             print(f"[init] INITIALIZATION FAILED: {exc}")
#             import traceback; traceback.print_exc()
#             bci_state['hardware_initialized'] = False
#             bci_state['status'] = 'idle'

#     threading.Thread(target=_do_init, daemon=True).start()

#     return jsonify({'message': 'Initialization started — poll /status for completion'})



# @app.route('/system/shutdown', methods=['POST'])
# def shutdown_system():
#     """Shutdown EEG hardware"""
#     global stream, bci_state
    
#     if stream:
#         stream.stop()
    
#     bci_state['status'] = 'idle'
    
#     return jsonify({'message': 'System shutdown'})


# # ============================================================================
# # BACKGROUND WORKER FUNCTIONS
# # ============================================================================

# def run_calibration():
#     """Run baseline calibration in background."""
#     global baseline, bci_state, stream, processor

#     print("\n" + "="*60)
#     print("BASELINE CALIBRATION STARTING")
#     print("="*60)

#     if stream is None:
#         print("Error: EEG stream not initialized!")
#         bci_state['status'] = 'idle'
#         return

#     if processor is None:
#         print("Error: Signal processor not initialized!")
#         bci_state['status'] = 'idle'
#         return

#     try:
#         duration   = Config.BASELINE_DURATION
#         start_time = time.time()

#         # ── Progress updater thread ──────────────────────────────────────────
#         def update_progress():
#             while bci_state['status'] == 'calibrating':
#                 elapsed  = time.time() - start_time
#                 progress = min(99, int((elapsed / duration) * 100))
#                 bci_state['baseline_progress'] = progress
#                 time.sleep(1)

#         threading.Thread(target=update_progress, daemon=True).start()

#         # ── Wait for channel config to finish ────────────────────────────────
#         # The Neuropawn config_board calls take ~8 s (8 channels × 2 cmds × 0.5 s).
#         # We wait an extra buffer so no config warnings pollute calibration data.
#         config_settle = 12   # seconds — increase if you still see sync warnings
#         print(f"Waiting {config_settle}s for channel configuration to settle...")
#         time.sleep(config_settle)

#         # Clear whatever landed in the buffer during config
#         print("Clearing config-phase buffer...")
#         _ = stream.board.get_board_data()          # drains and discards
#         time.sleep(1)                               # brief settle

#         # ── Collect ──────────────────────────────────────────────────────────
#         # Simply sleep for the baseline duration.  BrainFlow's acquisition
#         # thread silently fills its ring buffer the whole time.
#         # One get_board_data() call at the end drains everything reliably.
#         print(f">>> COLLECTING BASELINE ({duration}s) <<<")
#         start_time = time.time()                    # reset for progress calc
#         time.sleep(duration)

#         data = stream.board.get_board_data()        # drain entire ring buffer

#         if data is None or data.shape[1] == 0:
#             raise RuntimeError(
#                 f"No EEG data in buffer after {duration}s.\n"
#                 "Possible causes:\n"
#                 "  1. Channel config is still running — increase config_settle above\n"
#                 "  2. Board lost connection during baseline\n"
#                 "  3. BrainFlow ring buffer was cleared elsewhere"
#             )

#         print(f"Collected {data.shape[1]} samples "
#               f"({data.shape[1]/Config.SAMPLING_RATE:.1f}s at {Config.SAMPLING_RATE}Hz)")

#         # ── Channel indexing ─────────────────────────────────────────────────
#         # stream.eeg_channels = [1,2,3,4,5,6,7,8] — these are the ROW indices
#         # in BrainFlow's data matrix (not 0-based EEG positions).
#         # Config.C3_CHANNEL = 3  means the 3rd EEG electrode.
#         # eeg_channels[C3_CHANNEL - 1] = eeg_channels[2] = 3 → data row 3.
#         eeg_ch = stream.eeg_channels
#         c3_row = eeg_ch[Config.C3_CHANNEL - 1]   # correct BrainFlow row index
#         c4_row = eeg_ch[Config.C4_CHANNEL - 1]

#         print(f"Using BrainFlow rows: C3={c3_row}, C4={c4_row}")

#         c3_data = data[c3_row]
#         c4_data = data[c4_row]

#         print(f"C3 samples: {len(c3_data)}, C4 samples: {len(c4_data)}")

#         # ── Signal processing ────────────────────────────────────────────────
#         print("Processing signals...")
#         c3_clean = processor.preprocess(c3_data)
#         c4_clean = processor.preprocess(c4_data)

#         print("Computing baseline power...")
#         baseline = {
#             'c3_mu_power':   processor.compute_psd(c3_clean, Config.MU_BAND),
#             'c3_beta_power': processor.compute_psd(c3_clean, Config.BETA_BAND),
#             'c4_mu_power':   processor.compute_psd(c4_clean, Config.MU_BAND),
#             'c4_beta_power': processor.compute_psd(c4_clean, Config.BETA_BAND),
#         }

#         bci_state['calibration_complete'] = True
#         bci_state['status']               = 'idle'
#         bci_state['baseline_progress']    = 100

#         print("\n" + "="*60)
#         print("BASELINE CALIBRATION COMPLETE")
#         print("="*60)
#         print(f"C3 - Mu: {baseline['c3_mu_power']:.4f}  Beta: {baseline['c3_beta_power']:.4f}")
#         print(f"C4 - Mu: {baseline['c4_mu_power']:.4f}  Beta: {baseline['c4_beta_power']:.4f}")
#         print("="*60 + "\n")

#     except Exception as e:
#         print("\n" + "="*60)
#         print("CALIBRATION FAILED")
#         print("="*60)
#         print(f"Error: {e}")
#         import traceback
#         traceback.print_exc()
#         print("="*60 + "\n")
#         bci_state['status']               = 'idle'
#         bci_state['calibration_complete'] = False
#         baseline                          = None


# def run_training():
#     """Run training with paired REST + MOTOR IMAGERY trials.

#     For each of the 20 trials the bridge:
#       1. Immediately collects a 1.8 s REST window (no Flutter trigger needed)
#       2. Waits for Flutter to signal the animation start
#       3. Collects a 1.8 s MOTOR IMAGERY window during the animation

#     This gives the LDA classifier both classes to discriminate between.
#     """
#     global classifier, bci_state, baseline, stream, processor

#     if baseline is None:
#         print("Error: Baseline not collected — run calibration first")
#         bci_state['status'] = 'idle'
#         return

#     print("\n" + "="*60)
#     print("TRAINING DATA COLLECTION")
#     print("="*60)
#     print(f"Collecting {Config.TRAINING_TRIALS} paired REST + IMAGERY trials")
#     print("="*60 + "\n")

#     rest_trials    = []
#     imagery_trials = []

#     for trial_num in range(Config.TRAINING_TRIALS):
#         bci_state['current_trial'] = trial_num + 1

#         print(f"\n[Trial {trial_num + 1}/{Config.TRAINING_TRIALS}]")

#         # ── Step 1: collect REST window immediately ──────────────────────────
#         try:
#             print("  Collecting REST window...")
#             rest_trial = collect_rest_trial_data(stream, processor, baseline)
#             rest_trials.append(rest_trial)
#             print(f"  REST complete: C3μ={rest_trial['c3_mu_erd']:.1f}%, "
#                   f"C4μ={rest_trial['c4_mu_erd']:.1f}%")
#         except Exception as e:
#             print(f"  Error collecting REST trial: {e}")
#             import traceback; traceback.print_exc()
#             continue

#         # ── Step 2: wait for Flutter animation trigger ───────────────────────
#         print("  Waiting for Flutter animation...")
#         wait_start = time.time()
#         while bci_state['status'] == 'training':
#             time.sleep(0.1)
#             if time.time() - wait_start > 30:
#                 print("  Timeout waiting for trial trigger — skipping")
#                 break

#         # ── Step 3: collect IMAGERY window ───────────────────────────────────
#         if bci_state['status'] == 'collecting_trial':
#             print("  Animation started — collecting MOTOR IMAGERY window...")
#             try:
#                 imagery_trial = collect_trial_data(stream, processor, baseline)
#                 imagery_trials.append(imagery_trial)
#                 print(f"  IMAGERY complete: C3μ={imagery_trial['c3_mu_erd']:.1f}%, "
#                       f"C4μ={imagery_trial['c4_mu_erd']:.1f}%")
#             except Exception as e:
#                 print(f"  Error collecting imagery trial: {e}")
#                 import traceback; traceback.print_exc()

#             bci_state['status'] = 'training'
#         else:
#             print("  Training interrupted")
#             break

#     # ── Train classifier ─────────────────────────────────────────────────────
#     paired_count   = min(len(rest_trials), len(imagery_trials))
#     rest_trials    = rest_trials[:paired_count]
#     imagery_trials = imagery_trials[:paired_count]
#     bci_state['current_trial'] = paired_count

#     if paired_count >= 10:
#         print("\n" + "="*60)
#         print("TRAINING CLASSIFIER")
#         print("="*60)
#         print(f"Using {paired_count} REST + {paired_count} IMAGERY trials")

#         try:
#             import os
#             os.makedirs(Config.LOG_DIR, exist_ok=True)   # ensure dir exists

#             classifier    = MIClassifier()
#             training_data = prepare_training_data(rest_trials, imagery_trials)
#             classifier.train(training_data)
#             print("Classifier trained successfully!")
#             print("="*60 + "\n")
#         except Exception as e:
#             print(f"Classifier training failed: {e}")
#             import traceback; traceback.print_exc()
#             classifier = None
#     else:
#         print(f"\nNot enough paired trials ({paired_count}/{Config.TRAINING_TRIALS})")
#         classifier = None

#     bci_state['status'] = 'idle'
#     print("\nTraining session complete\n")


# def collect_trial_data(stream, processor, baseline):
#     """Collect EEG data for one trial (1.8 seconds during animation)"""
#     import time
    
#     # Clear buffer
#     stream.clear_buffer()
    
#     # Collect for trial duration
#     duration = 1.8  # shooting phase seconds
#     samples_needed = int(duration * Config.SAMPLING_RATE)
    
#     print(f"  Collecting {samples_needed} samples ({duration}s)...")
    
#     c3_data = []
#     c4_data = []
    
#     start_time = time.time()
#     sample_count = 0
    
#     while sample_count < samples_needed:
#         data = stream.get_data(1)
        
#         if data.shape[1] > 0:
#             eeg_ch = stream.eeg_channels
#             c3_data.append(data[eeg_ch[Config.C3_CHANNEL - 1]][0])
#             c4_data.append(data[eeg_ch[Config.C4_CHANNEL - 1]][0])
#             sample_count += 1
        
#         time.sleep(1 / Config.SAMPLING_RATE)
        
#         # Timeout safety
#         if time.time() - start_time > duration + 2:
#             print(f"Collection timeout - got {sample_count}/{samples_needed} samples")
#             break
    
#     print(f"Collected {sample_count} samples")
    
#     # Convert to numpy arrays
#     c3_signal = np.array(c3_data)
#     c4_signal = np.array(c4_data)
    
#     # Bandpass filter
#     c3_filtered = processor.bandpass_filter(c3_signal)
#     c4_filtered = processor.bandpass_filter(c4_signal)
    
#     # Compute psd in mu and beta bands
#     c3_mu_power = processor.compute_psd(c3_filtered, Config.MU_BAND)
#     c3_beta_power = processor.compute_psd(c3_filtered, Config.BETA_BAND)
#     c4_mu_power = processor.compute_psd(c4_filtered, Config.MU_BAND)
#     c4_beta_power = processor.compute_psd(c4_filtered, Config.BETA_BAND)
    
#     # Compute ERD 
#     c3_mu_erd = processor.compute_erd(c3_mu_power, baseline['c3_mu_power'])
#     c3_beta_erd = processor.compute_erd(c3_beta_power, baseline['c3_beta_power'])
#     c4_mu_erd = processor.compute_erd(c4_mu_power, baseline['c4_mu_power'])
#     c4_beta_erd = processor.compute_erd(c4_beta_power, baseline['c4_beta_power'])
    
#     return {
#         'c3_mu_erd': c3_mu_erd,
#         'c3_beta_erd': c3_beta_erd,
#         'c4_mu_erd': c4_mu_erd,
#         'c4_beta_erd': c4_beta_erd,
#         'label': 1  # Motor imagery
#     }

# def collect_rest_trial_data(stream, processor, baseline):
#     """Collect 1.8 s of REST EEG (no motor imagery)."""
#     stream.clear_buffer()

#     duration       = 1.8
#     samples_needed = int(duration * Config.SAMPLING_RATE)
#     eeg_ch         = stream.eeg_channels

#     c3_data, c4_data = [], []
#     start_time       = time.time()
#     sample_count     = 0

#     while sample_count < samples_needed:
#         data = stream.get_data(1)
#         if data.shape[1] > 0:
#             c3_data.append(data[eeg_ch[Config.C3_CHANNEL - 1]][0])
#             c4_data.append(data[eeg_ch[Config.C4_CHANNEL - 1]][0])
#             sample_count += 1
#         time.sleep(1 / Config.SAMPLING_RATE)
#         if time.time() - start_time > duration + 2:
#             break

#     c3_signal = np.array(c3_data)
#     c4_signal = np.array(c4_data)

#     c3_f = processor.bandpass_filter(c3_signal)
#     c4_f = processor.bandpass_filter(c4_signal)

#     return {
#         'c3_mu_erd':   processor.compute_erd(processor.compute_psd(c3_f, Config.MU_BAND),   baseline['c3_mu_power']),
#         'c3_beta_erd': processor.compute_erd(processor.compute_psd(c3_f, Config.BETA_BAND), baseline['c3_beta_power']),
#         'c4_mu_erd':   processor.compute_erd(processor.compute_psd(c4_f, Config.MU_BAND),   baseline['c4_mu_power']),
#         'c4_beta_erd': processor.compute_erd(processor.compute_psd(c4_f, Config.BETA_BAND), baseline['c4_beta_power']),
#         'label': 0,
#     }


# def prepare_training_data(rest_trials, imagery_trials):
#     """Build classifier training set from paired REST + IMAGERY trials."""
#     training_data = []
#     for trial in rest_trials:
#         training_data.append({
#             'features': [trial['c3_mu_erd'], trial['c3_beta_erd'],
#                          trial['c4_mu_erd'], trial['c4_beta_erd']],
#             'label': 0,
#         })
#     for trial in imagery_trials:
#         training_data.append({
#             'features': [trial['c3_mu_erd'], trial['c3_beta_erd'],
#                          trial['c4_mu_erd'], trial['c4_beta_erd']],
#             'label': 1,
#         })
#     return training_data


# def run_detection():
#     """Run real-time detection in background"""
#     global detector, bci_state, baseline, classifier
    
#     detector = RealTimeDetector(stream, processor, baseline, classifier)
    
#     print("\nStarting real-time detection...")
    
#     # Modified detection loop that updates bci_state
#     while bci_state['status'] == 'detecting':
#         data = stream.get_data(1)
        
#         if data.shape[1] > 0:
#             eeg_ch    = stream.eeg_channels
#             c3_sample = data[eeg_ch[Config.C3_CHANNEL - 1]][0]
#             c4_sample = data[eeg_ch[Config.C4_CHANNEL - 1]][0]
            
#             detector.add_sample(c3_sample, c4_sample)
            
#             # Process window
#             if len(detector.c3_buffer) == detector.window_size:
#                 trigger, prediction, confidence, erd = detector.process_window()
                
#                 # Update state
#                 bci_state['confidence'] = confidence
#                 bci_state['erd_values'] = erd
                
#                 if trigger:
#                     bci_state['trigger_detected'] = True
#                     bci_state['last_trigger_time'] = time.time()
#                     print(f"\nTRIGGER DETECTED - Confidence: {confidence:.0%}")
        
#         time.sleep(1 / Config.SAMPLING_RATE)


# # ============================================================================
# # MAIN
# # ============================================================================

# if __name__ == '__main__':
#     print("\n" + "="*60)
#     print(" " * 15 + "BCI FLUTTER BRIDGE SERVER")
#     print("="*60)
#     print("\nServer starting on http://localhost:5000")
#     print("\nAvailable endpoints:")
#     print("  POST /system/initialize     - Initialize EEG hardware")
#     print("  POST /calibration/start     - Start 60s baseline")
#     print("  GET  /calibration/progress  - Get calibration progress")
#     print("  POST /training/start        - Start training trials")
#     print("  GET  /training/progress     - Get training progress")
#     print("  POST /detection/start       - Start MI detection")
#     print("  GET  /detection/poll        - Check for triggers")
#     print("  POST /system/shutdown       - Shutdown system")
#     print("\n" + "="*60 + "\n")
    
#     app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)




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
from brainflow.board_shim import BoardIds

app = Flask(__name__)
CORS(app)  # Allow Flutter to make requests

# Global state
bci_state = {
    'status': 'idle',  # idle, calibrating, training, detecting
    'channel_config_complete': False,  # True once Neuropawn config finishes
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
    """Get current BCI system status.

    Returns keys matching BCIStatus.fromJson() in bci_service.dart.
    """
    return jsonify({
        # Flutter-facing keys
        'initialized':      bci_state['hardware_initialized'],
        'calibrated':       bci_state.get('calibration_complete', False),
        'trained':          classifier is not None,
        'detecting':        bci_state['status'] == 'detecting',
        'mode':             bci_state['status'],
        'last_confidence':  bci_state.get('confidence', 0.0),
        # Extra detail
        'baseline_progress': bci_state.get('baseline_progress', 0),
        'current_trial':     bci_state.get('current_trial', 0),
        'total_trials':      bci_state.get('total_trials', 0),
    })


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
        return jsonify({'message': 'Already initialized',
                        'hardware_initialized': True})

    # Block re-init if a calibration/training/detection is in progress
    if bci_state['status'] not in ('idle', ''):
        msg = f"Cannot initialize while status is '{bci_state['status']}'"
        print(f"Initialize blocked: {msg}")
        return jsonify({'error': msg}), 400

    print("Initializing EEG Hardware...")

    # Run the slow stream.start() (Neuropawn config takes ~15s) in a
    # background thread so the HTTP response returns immediately.
    # Flutter polls /status to know when initialization is complete.
    bci_state['status'] = 'initializing'

    def _do_init():
        global stream, processor
        try:
            print("[init] Creating EEGStream...")
            stream    = EEGStream(Config.BOARD_ID, Config.SERIAL_PORT)
            processor = SignalProcessor(Config.SAMPLING_RATE)

            print("[init] Preparing session and starting stream...")
            stream.board.prepare_session()
            stream.board.start_stream(450000)
            stream.is_streaming = True
            print("[init] Stream started. Skipping channel config for fast init.")
            print("[init] You can recalibrate after init if signal quality is poor.")

            # Mark as initialized BEFORE the slow channel config
            # so Flutter sees it immediately. Config runs in background.
            bci_state['hardware_initialized'] = True
            bci_state['status']               = 'idle'
            print("=" * 60)
            print("EEG HARDWARE INITIALIZATION COMPLETE")
            print("Flutter will now see initialized=True on next /status poll")
            print("=" * 60)

            # Now run channel config in background — won't block Flutter
            import time as _time
            _time.sleep(2)   # brief stabilization
            # Run Neuropawn config — compare by board ID int value to be safe
            neuropawn_val = BoardIds.NEUROPAWN_KNIGHT_BOARD.value
            board_val = (stream.board_id.value
                         if hasattr(stream.board_id, 'value')
                         else int(stream.board_id))
            if board_val == neuropawn_val:
                print("[init] Running Neuropawn channel configuration in background...")
                stream.configure_neuropawn(Config.NUM_CHANNELS)
                _ = stream.board.get_board_data()  # clear config-phase data
                _time.sleep(3)
                print("[init] Neuropawn configuration complete. Ready for calibration.")
                bci_state['channel_config_complete'] = True
            else:
                bci_state['channel_config_complete'] = True

        except Exception as exc:
            print(f"[init] INITIALIZATION FAILED: {exc}")
            import traceback; traceback.print_exc()
            bci_state['hardware_initialized'] = False
            bci_state['status'] = 'idle'

    threading.Thread(target=_do_init, daemon=True).start()

    return jsonify({'message': 'Initialization started — poll /status for completion'})



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
    """Run baseline calibration in background."""
    global baseline, bci_state, stream, processor

    print("\n" + "="*60)
    print("BASELINE CALIBRATION STARTING")
    print("="*60)

    if stream is None:
        print("Error: EEG stream not initialized!")
        bci_state['status'] = 'idle'
        return

    if processor is None:
        print("Error: Signal processor not initialized!")
        bci_state['status'] = 'idle'
        return

    try:
        duration   = Config.BASELINE_DURATION
        start_time = time.time()

        # ── Progress updater thread ──────────────────────────────────────────
        def update_progress():
            while bci_state['status'] == 'calibrating':
                elapsed  = time.time() - start_time
                progress = min(99, int((elapsed / duration) * 100))
                bci_state['baseline_progress'] = progress
                time.sleep(1)

        threading.Thread(target=update_progress, daemon=True).start()

        # ── Wait for channel config to finish ────────────────────────────────
        # The background _do_init thread sets channel_config_complete=True when
        # configure_neuropawn() finishes. Poll until that flag is set, then
        # drain the buffer and settle. Max wait 90s.
        print("Waiting for Neuropawn channel configuration to complete...")
        wait_start = time.time()
        while not bci_state.get('channel_config_complete', False):
            time.sleep(1)
            elapsed = int(time.time() - wait_start)
            if elapsed % 5 == 0 and elapsed > 0:
                print(f"  Still waiting for config... ({elapsed}s elapsed)")
            if elapsed > 90:
                print("  Config wait timed out — proceeding anyway")
                break

        print("Channel config done. Clearing buffer and settling 3s...")
        _ = stream.board.get_board_data()          # drain all config-phase data
        time.sleep(3)                               # extra settle for clean signal

        # ── Collect ──────────────────────────────────────────────────────────
        # Simply sleep for the baseline duration.  BrainFlow's acquisition
        # thread silently fills its ring buffer the whole time.
        # One get_board_data() call at the end drains everything reliably.
        print(f">>> COLLECTING BASELINE ({duration}s) <<<")
        start_time = time.time()                    # reset for progress calc
        time.sleep(duration)

        data = stream.board.get_board_data()        # drain entire ring buffer

        if data is None or data.shape[1] == 0:
            raise RuntimeError(
                f"No EEG data in buffer after {duration}s.\n"
                "Possible causes:\n"
                "  1. Channel config is still running — increase config_settle above\n"
                "  2. Board lost connection during baseline\n"
                "  3. BrainFlow ring buffer was cleared elsewhere"
            )

        print(f"Collected {data.shape[1]} samples "
              f"({data.shape[1]/Config.SAMPLING_RATE:.1f}s at {Config.SAMPLING_RATE}Hz)")

        # ── Channel indexing ─────────────────────────────────────────────────
        # stream.eeg_channels = [1,2,3,4,5,6,7,8] — these are the ROW indices
        # in BrainFlow's data matrix (not 0-based EEG positions).
        # Config.C3_CHANNEL = 3  means the 3rd EEG electrode.
        # eeg_channels[C3_CHANNEL - 1] = eeg_channels[2] = 3 → data row 3.
        eeg_ch = stream.eeg_channels
        c3_row = eeg_ch[Config.C3_CHANNEL - 1]   # correct BrainFlow row index
        c4_row = eeg_ch[Config.C4_CHANNEL - 1]

        print(f"Using BrainFlow rows: C3={c3_row}, C4={c4_row}")

        c3_data = data[c3_row]
        c4_data = data[c4_row]

        print(f"C3 samples: {len(c3_data)}, C4 samples: {len(c4_data)}")

        # ── Signal processing ────────────────────────────────────────────────
        print("Processing signals...")
        c3_clean = processor.preprocess(c3_data)
        c4_clean = processor.preprocess(c4_data)

        print("Computing baseline power...")
        baseline = {
            'c3_mu_power':   processor.compute_psd(c3_clean, Config.MU_BAND),
            'c3_beta_power': processor.compute_psd(c3_clean, Config.BETA_BAND),
            'c4_mu_power':   processor.compute_psd(c4_clean, Config.MU_BAND),
            'c4_beta_power': processor.compute_psd(c4_clean, Config.BETA_BAND),
        }

        bci_state['calibration_complete'] = True
        bci_state['status']               = 'idle'
        bci_state['baseline_progress']    = 100

        print("\n" + "="*60)
        print("BASELINE CALIBRATION COMPLETE")
        print("="*60)
        print(f"C3 - Mu: {baseline['c3_mu_power']:.4f}  Beta: {baseline['c3_beta_power']:.4f}")
        print(f"C4 - Mu: {baseline['c4_mu_power']:.4f}  Beta: {baseline['c4_beta_power']:.4f}")
        print("="*60 + "\n")

    except Exception as e:
        print("\n" + "="*60)
        print("CALIBRATION FAILED")
        print("="*60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print("="*60 + "\n")
        bci_state['status']               = 'idle'
        bci_state['calibration_complete'] = False
        baseline                          = None


def run_training():
    """Run training with paired REST + MOTOR IMAGERY trials.
 
    For each of the 20 trials the bridge:
      1. Immediately collects a 1.8 s REST window (no Flutter trigger needed)
      2. Waits for Flutter to signal the animation start
      3. Collects a 1.8 s MOTOR IMAGERY window during the animation
 
    This gives the LDA classifier both classes to discriminate between.
    """
    global classifier, bci_state, baseline, stream, processor
 
    if baseline is None:
        print("Error: Baseline not collected — run calibration first")
        bci_state['status'] = 'idle'
        return
 
    print("\n" + "="*60)
    print("TRAINING DATA COLLECTION")
    print("="*60)
    print(f"Collecting {Config.TRAINING_TRIALS} paired REST + IMAGERY trials")
    print(f"(2 sets of {Config.TRAINING_TRIALS // 2} with a 60-second break in between)")
    print("="*60 + "\n")
 
    rest_trials    = []
    imagery_trials = []
 
    HALF = Config.TRAINING_TRIALS // 2  # = 20 for 40-trial sessions
 
    for trial_num in range(Config.TRAINING_TRIALS):
        bci_state['current_trial'] = trial_num + 1
 
        # ── Mid-session break ────────────────────────────────────────────────
        if trial_num == HALF:
            print("\n" + "="*60)
            print("MID-SESSION BREAK")
            print("="*60)
            print(f"Completed {HALF}/{Config.TRAINING_TRIALS} trials.")
            print("Take a 60-second break — relax, blink, stretch.")
            print("Training will resume automatically.")
            print("="*60)
            bci_state['status'] = 'break'
            time.sleep(60)
            bci_state['status'] = 'training'
            print("Break over — resuming training.\n")
 
        print(f"\n[Trial {trial_num + 1}/{Config.TRAINING_TRIALS}]")
 
        # ── Step 1: collect REST window immediately ──────────────────────────
        try:
            print("  Collecting REST window...")
            rest_trial = collect_rest_trial_data(stream, processor, baseline)
            rest_trials.append(rest_trial)
            print(f"  REST complete: C3μ={rest_trial['c3_mu_erd']:.1f}%, "
                  f"C4μ={rest_trial['c4_mu_erd']:.1f}%")
        except Exception as e:
            print(f"  Error collecting REST trial: {e}")
            import traceback; traceback.print_exc()
            continue
 
        # ── Step 2: wait for Flutter animation trigger ───────────────────────
        print("  Waiting for Flutter animation...")
        wait_start = time.time()
        while bci_state['status'] == 'training':
            time.sleep(0.1)
            if time.time() - wait_start > 30:
                print("  Timeout waiting for trial trigger — skipping")
                break
 
        # ── Step 3: collect IMAGERY window ───────────────────────────────────
        if bci_state['status'] == 'collecting_trial':
            print("  Animation started — collecting MOTOR IMAGERY window...")
            try:
                imagery_trial = collect_trial_data(stream, processor, baseline)
                imagery_trials.append(imagery_trial)
                print(f"  IMAGERY complete: C3μ={imagery_trial['c3_mu_erd']:.1f}%, "
                      f"C4μ={imagery_trial['c4_mu_erd']:.1f}%")
            except Exception as e:
                print(f"  Error collecting imagery trial: {e}")
                import traceback; traceback.print_exc()
 
            bci_state['status'] = 'training'
        else:
            print("  Training interrupted")
            break
 
    # ── Train classifier ─────────────────────────────────────────────────────
    paired_count   = min(len(rest_trials), len(imagery_trials))
    rest_trials    = rest_trials[:paired_count]
    imagery_trials = imagery_trials[:paired_count]
    bci_state['current_trial'] = paired_count
 
    if paired_count >= 10:
        print("\n" + "="*60)
        print("TRAINING CLASSIFIER")
        print("="*60)
        print(f"Using {paired_count} REST + {paired_count} IMAGERY trials")
 
        try:
            import os
            os.makedirs(Config.LOG_DIR, exist_ok=True)   # ensure dir exists
 
            classifier    = MIClassifier()
            training_data = prepare_training_data(rest_trials, imagery_trials)
            classifier.train(training_data)
            print("Classifier trained successfully!")
            print("="*60 + "\n")
        except Exception as e:
            print(f"Classifier training failed: {e}")
            import traceback; traceback.print_exc()
            classifier = None
    else:
        print(f"\nNot enough paired trials ({paired_count}/{Config.TRAINING_TRIALS})")
        classifier = None
 
    bci_state['status'] = 'idle'
    print("\nTraining session complete\n")
 
 
def collect_trial_data(stream, processor, baseline):
    """Collect EEG data for one IMAGERY trial (1.8s)."""
    import time

    stream.clear_buffer()
    time.sleep(0.2)

    duration       = 1.8
    samples_needed = int(duration * Config.SAMPLING_RATE)
    print(f"  Collecting {samples_needed} samples ({duration}s)...")

    time.sleep(duration)

    data      = stream.board.get_board_data()
    eeg_ch    = stream.eeg_channels
    c3_signal = data[eeg_ch[Config.C3_CHANNEL - 1]][-samples_needed:]
    c4_signal = data[eeg_ch[Config.C4_CHANNEL - 1]][-samples_needed:]
    sample_count = len(c3_signal)

    print(f"  Collected {sample_count} samples")

    # Raw signal diagnostics
    c3_zeros = np.sum(c3_signal == 0)
    c4_zeros = np.sum(c4_signal == 0)
    print(f"  [DEBUG IMAGERY] C3 raw  mean: {c3_signal.mean():.2f}  std: {c3_signal.std():.2f}  zeros: {c3_zeros}/{sample_count}")
    print(f"  [DEBUG IMAGERY] C4 raw  mean: {c4_signal.mean():.2f}  std: {c4_signal.std():.2f}  zeros: {c4_zeros}/{sample_count}")
    if c3_zeros > sample_count * 0.2 or c4_zeros > sample_count * 0.2:
        print("  WARNING: >20% zero samples - possible electrode dropout or buffer underrun")
    if c3_signal.std() < 0.5 or c4_signal.std() < 0.5:
        print("  WARNING: Signal std very low - possible flat/saturated signal")

    c3_filtered = processor.preprocess(c3_signal)
    c4_filtered = processor.preprocess(c4_signal)

    c3_mu_power   = processor.compute_psd(c3_filtered, Config.MU_BAND)
    c3_beta_power = processor.compute_psd(c3_filtered, Config.BETA_BAND)
    c4_mu_power   = processor.compute_psd(c4_filtered, Config.MU_BAND)
    c4_beta_power = processor.compute_psd(c4_filtered, Config.BETA_BAND)

    c3_mu_erd   = processor.compute_erd(c3_mu_power,   baseline['c3_mu_power'])
    c3_beta_erd = processor.compute_erd(c3_beta_power, baseline['c3_beta_power'])
    c4_mu_erd   = processor.compute_erd(c4_mu_power,   baseline['c4_mu_power'])
    c4_beta_erd = processor.compute_erd(c4_beta_power, baseline['c4_beta_power'])

    print(f"  [DEBUG IMAGERY] C3  mu_pwr: {c3_mu_power:.2f}  beta_pwr: {c3_beta_power:.2f}"
          f"  (baseline  mu: {baseline['c3_mu_power']:.2f}  beta: {baseline['c3_beta_power']:.2f})")
    print(f"  [DEBUG IMAGERY] C4  mu_pwr: {c4_mu_power:.2f}  beta_pwr: {c4_beta_power:.2f}"
          f"  (baseline  mu: {baseline['c4_mu_power']:.2f}  beta: {baseline['c4_beta_power']:.2f})")

    return {
        'c3_mu_erd':   c3_mu_erd,
        'c3_beta_erd': c3_beta_erd,
        'c4_mu_erd':   c4_mu_erd,
        'c4_beta_erd': c4_beta_erd,
        'label': 1,
    }

def collect_rest_trial_data(stream, processor, baseline):
    """Collect 1.8s of REST EEG (no motor imagery)."""
    import time

    stream.clear_buffer()
    time.sleep(0.2)

    duration       = 1.8
    samples_needed = int(duration * Config.SAMPLING_RATE)
    print(f"  Collecting {samples_needed} samples ({duration}s)...")

    time.sleep(duration)

    data      = stream.board.get_board_data()
    eeg_ch    = stream.eeg_channels
    c3_signal = data[eeg_ch[Config.C3_CHANNEL - 1]][-samples_needed:]
    c4_signal = data[eeg_ch[Config.C4_CHANNEL - 1]][-samples_needed:]
    sample_count = len(c3_signal)

    print(f"  Collected {sample_count} samples")

    # Raw signal diagnostics
    c3_zeros = np.sum(c3_signal == 0)
    c4_zeros = np.sum(c4_signal == 0)
    print(f"  [DEBUG REST]    C3 raw  mean: {c3_signal.mean():.2f}  std: {c3_signal.std():.2f}  zeros: {c3_zeros}/{sample_count}")
    print(f"  [DEBUG REST]    C4 raw  mean: {c4_signal.mean():.2f}  std: {c4_signal.std():.2f}  zeros: {c4_zeros}/{sample_count}")
    if c3_zeros > sample_count * 0.2 or c4_zeros > sample_count * 0.2:
        print("  WARNING: >20% zero samples - possible electrode dropout or buffer underrun")
    if c3_signal.std() < 0.5 or c4_signal.std() < 0.5:
        print("  WARNING: Signal std very low - possible flat/saturated signal")

    c3_f = processor.preprocess(c3_signal)
    c4_f = processor.preprocess(c4_signal)

    c3_mu_erd   = processor.compute_erd(processor.compute_psd(c3_f, Config.MU_BAND),   baseline['c3_mu_power'])
    c3_beta_erd = processor.compute_erd(processor.compute_psd(c3_f, Config.BETA_BAND), baseline['c3_beta_power'])
    c4_mu_erd   = processor.compute_erd(processor.compute_psd(c4_f, Config.MU_BAND),   baseline['c4_mu_power'])
    c4_beta_erd = processor.compute_erd(processor.compute_psd(c4_f, Config.BETA_BAND), baseline['c4_beta_power'])

    print(f"  [DEBUG REST]    C3  mu_pwr: {processor.compute_psd(c3_f, Config.MU_BAND):.2f}  beta_pwr: {processor.compute_psd(c3_f, Config.BETA_BAND):.2f}"
          f"  (baseline  mu: {baseline['c3_mu_power']:.2f}  beta: {baseline['c3_beta_power']:.2f})")

    return {
        'c3_mu_erd':   c3_mu_erd,
        'c3_beta_erd': c3_beta_erd,
        'c4_mu_erd':   c4_mu_erd,
        'c4_beta_erd': c4_beta_erd,
        'label': 0,
    }


def prepare_training_data(rest_trials, imagery_trials):
    """Build classifier training set from paired REST + IMAGERY trials."""
    training_data = []
    for trial in rest_trials:
        training_data.append({
            'features': [trial['c3_mu_erd'], trial['c3_beta_erd'],
                         trial['c4_mu_erd'], trial['c4_beta_erd']],
            'label': 0,
        })
    for trial in imagery_trials:
        training_data.append({
            'features': [trial['c3_mu_erd'], trial['c3_beta_erd'],
                         trial['c4_mu_erd'], trial['c4_beta_erd']],
            'label': 1,
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
            eeg_ch    = stream.eeg_channels
            c3_sample = data[eeg_ch[Config.C3_CHANNEL - 1]][0]
            c4_sample = data[eeg_ch[Config.C4_CHANNEL - 1]][0]
            
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