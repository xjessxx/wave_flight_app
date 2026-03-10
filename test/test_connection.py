from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
import time

# Configure for your headset
SERIAL_PORT = 'COM5'  # Change this to your port
BOARD_ID = BoardIds.NEUROPAWN_KNIGHT_BOARD

print(f"Testing connection to NeuroPawn on {SERIAL_PORT}...")

params = BrainFlowInputParams()
params.serial_port = SERIAL_PORT

try:
    board = BoardShim(BOARD_ID, params)
    print("Preparing session...")
    board.prepare_session()
    
    print("Starting stream...")
    board.start_stream()
    
    time.sleep(2)
    
    print("Getting data...")
    data = board.get_current_board_data(10)
    print(f"✓ Success! Got data shape: {data.shape}")
    
    board.stop_stream()
    board.release_session()
    print("✓ Connection test passed!")
    
except Exception as e:
    print(f"✗ Connection failed: {e}")
    print("\nTroubleshooting:")
    print("1. Check serial port in Device Manager")
    print("2. Make sure headset is powered on")
    print("3. Try unplugging and replugging USB")
    print("4. Close any other programs using the headset")