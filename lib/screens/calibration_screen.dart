import 'package:flutter/material.dart';
import 'dart:async';

/// Simplified Calibration Screen - Baseline Only
///
/// This screen collects the user's baseline brain state (60s of relaxed focus).
/// Motor imagery training happens on the separate training_screen.dart
class CalibrationScreen extends StatefulWidget {
  const CalibrationScreen({super.key});

  @override
  State<CalibrationScreen> createState() => _CalibrationScreenState();
}

class _CalibrationScreenState extends State<CalibrationScreen>
    with SingleTickerProviderStateMixin {
  // Calibration state
  CalibrationPhase _currentPhase = CalibrationPhase.introduction;

  // Timer
  Timer? _phaseTimer;
  int _secondsRemaining = 0;
  bool _isCollecting = false;

  // Animation for focus dot
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();

    // Setup pulse animation for focus dot
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    );

    _pulseAnimation = Tween<double>(begin: 0.8, end: 1.2).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    _pulseController.repeat(reverse: true);
  }

  @override
  void dispose() {
    _phaseTimer?.cancel();
    _pulseController.dispose();
    super.dispose();
  }

  // ========== CALIBRATION CONTROL ==========

  void _startBaseline() {
    setState(() {
      _currentPhase = CalibrationPhase.baseline;
      _secondsRemaining = 60; // 60 second baseline
      _isCollecting = true;
    });

    // Start countdown
    _phaseTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      setState(() {
        _secondsRemaining--;

        if (_secondsRemaining <= 0) {
          timer.cancel();
          _onBaselineComplete();
        }
      });
    });

    // TODO: Call BCI service to start baseline collection
    // Example: bciBluetooth.startBaseline();
  }

  void _onBaselineComplete() {
    setState(() {
      _isCollecting = false;
      _currentPhase = CalibrationPhase.complete;
    });

    // Show completion dialog
    _showCompletionDialog();
  }

  void _showCompletionDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        title: const Text(
          '✓ Baseline Complete!',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.check_circle, color: Colors.green, size: 80),
            const SizedBox(height: 16),
            const Text(
              'Great job! Your baseline has been recorded.\n\n'
              'Now you can start training with motor imagery.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 16),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              // Navigate to home screen
              Navigator.pushReplacementNamed(context, '/home');
            },
            child: const Text(
              'Continue to Home',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
          ),
        ],
      ),
    );
  }

  // ========== UI BUILDERS ==========

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: _buildPhaseContent(),
      ),
    );
  }

  Widget _buildPhaseContent() {
    switch (_currentPhase) {
      case CalibrationPhase.introduction:
        return _buildIntroduction();
      case CalibrationPhase.baseline:
        return _buildBaselineView();
      case CalibrationPhase.complete:
        return _buildCompletionView();
    }
  }

  Widget _buildIntroduction() {
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.psychology, size: 80, color: Color(0xFF4A90E2)),
          const SizedBox(height: 24),
          const Text(
            'Baseline Calibration',
            style: TextStyle(
              color: Colors.white,
              fontSize: 32,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          const Text(
            'We need to measure your resting brain state.\nThis takes 60 seconds.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white70, fontSize: 16),
          ),
          const SizedBox(height: 40),

          // Instructions card
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: Colors.grey[900],
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFF4A90E2), width: 2),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.info_outline, color: Color(0xFF4A90E2)),
                    SizedBox(width: 12),
                    Text(
                      'What to do:',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                _buildInstructionItem(
                  icon: Icons.visibility,
                  text: 'Keep your eyes open and focused on the blue dot',
                ),
                const SizedBox(height: 12),
                _buildInstructionItem(
                  icon: Icons.self_improvement,
                  text: 'Sit comfortably and stay relaxed',
                ),
                const SizedBox(height: 12),
                _buildInstructionItem(
                  icon: Icons.air,
                  text: 'Breathe normally and naturally',
                ),
                const SizedBox(height: 12),
                _buildInstructionItem(
                  icon: Icons.block,
                  text: 'Don\'t think about moving or imagine any movements',
                ),
                const SizedBox(height: 12),
                _buildInstructionItem(
                  icon: Icons.camera,
                  text: 'Minimize eye blinks, jaw clenching, and body movement',
                ),
              ],
            ),
          ),

          const Spacer(),

          // Start button
          SizedBox(
            width: double.infinity,
            height: 56,
            child: ElevatedButton(
              onPressed: () => _startBaseline(),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF4A90E2),
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              child: const Text(
                'Start Baseline Collection',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
            ),
          ),
          const SizedBox(height: 16),
          const Text(
            'Make sure you\'re in a quiet place before starting',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white60, fontSize: 14),
          ),
        ],
      ),
    );
  }

  Widget _buildInstructionItem({required IconData icon, required String text}) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: const Color(0xFF4A90E2), size: 20),
        const SizedBox(width: 12),
        Expanded(
          child: Text(
            text,
            style: const TextStyle(color: Colors.white70, fontSize: 16),
          ),
        ),
      ],
    );
  }

  Widget _buildBaselineView() {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const Text(
          'Collecting Baseline',
          style: TextStyle(
            color: Colors.white,
            fontSize: 28,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 16),
        Text(
          '${_secondsRemaining}s',
          style: const TextStyle(
            color: Color(0xFF4A90E2),
            fontSize: 64,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 40),

        // Focus dot with pulse animation
        AnimatedBuilder(
          animation: _pulseAnimation,
          builder: (context, child) {
            return Transform.scale(
              scale: _pulseAnimation.value,
              child: Container(
                width: 80,
                height: 80,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: const Color(0xFF4A90E2),
                  boxShadow: [
                    BoxShadow(
                      color: const Color(0xFF4A90E2).withValues(blue: 0.6),
                      blurRadius: 30,
                      spreadRadius: 10,
                    ),
                  ],
                ),
              ),
            );
          },
        ),

        const SizedBox(height: 60),

        // Reminder card
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 32),
          child: Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.grey[900],
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.grey[800]!),
            ),
            child: const Column(
              children: [
                Icon(Icons.spa, color: Color(0xFF4A90E2), size: 32),
                SizedBox(height: 12),
                Text(
                  'Stay Focused & Relaxed',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                SizedBox(height: 8),
                Text(
                  'Keep your eyes on the blue dot\nStay still and breathe normally',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.white70, fontSize: 14),
                ),
              ],
            ),
          ),
        ),

        const SizedBox(height: 40),

        // Progress bar
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 40),
          child: Column(
            children: [
              LinearProgressIndicator(
                value: 1 - (_secondsRemaining / 60),
                backgroundColor: Colors.grey[800],
                color: const Color(0xFF4A90E2),
                minHeight: 8,
              ),
              const SizedBox(height: 8),
              Text(
                '${(((60 - _secondsRemaining) / 60) * 100).toStringAsFixed(0)}% Complete',
                style: const TextStyle(color: Colors.white60, fontSize: 14),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildCompletionView() {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const Icon(
          Icons.check_circle,
          color: Colors.green,
          size: 100,
        ),
        const SizedBox(height: 24),
        const Text(
          'Baseline Collected!',
          style: TextStyle(
            color: Colors.white,
            fontSize: 32,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 16),
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 40),
          child: Text(
            'Your resting brain state has been recorded.\nYou can now proceed to motor imagery training.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white70, fontSize: 16),
          ),
        ),
      ],
    );
  }
}

// ========== ENUMS ==========

enum CalibrationPhase {
  introduction,
  baseline,
  complete,
}
