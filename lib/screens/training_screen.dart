import 'package:flutter/material.dart';
import 'package:wave_flight_app/services/bci_service.dart';

class TrainingScreen extends StatefulWidget {
  const TrainingScreen({super.key});

  @override
  State<TrainingScreen> createState() => _TrainingScreenState();
}

class _TrainingScreenState extends State<TrainingScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  bool _hasAnimated = false;
  bool _showGo = false;
  final BCIService _bciService = BCIService.instance;
  bool _bciEnabled = false;

  // Static idle position
  static const double idleBallBottom = 100.0;
  static const double idleShadowBottom = 100.0;

  @override
  void initState() {
    super.initState();

    _controller = AnimationController(
      duration: Duration(
          milliseconds:
              4500), //can be increased to allow more time between ball reload
      vsync: this,
    );

    // Reset flag when animation completes
    _controller.addStatusListener((status) {
      if (status == AnimationStatus.completed) {
        setState(() {
          _hasAnimated = false;
        });
      }
    });

    WidgetsBinding.instance.addPostFrameCallback((_) {
      //pop up on screen load
      _showInstructionsPopup();
       _setupBCIDetection();
    });
  }

  
  void _showInstructionsPopup() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (BuildContext context) {
        // Auto-dismiss after 15 seconds
        Future.delayed(Duration(seconds: 15), () {
          if (Navigator.canPop(context)) {
            Navigator.of(context).pop();
          }
        });

        return Dialog(
          backgroundColor: Colors.black,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          child: Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.psychology,
                    size: 60, color: Color(0xFF4A90E2)),
                const SizedBox(height: 16),
                const Text(
                  'Thumb Movement Detection',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 24),

                // Instructions container
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: Colors.grey[900],
                    borderRadius: BorderRadius.circular(12),
                    border:
                        Border.all(color: const Color(0xFF4A90E2), width: 2),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildInstructionItem(
                        icon: Icons.self_improvement,
                        text:
                            'Make sure you are in a calm and quiet environment',
                      ),
                      const SizedBox(height: 12),
                      _buildInstructionItem(
                        icon: Icons.timer,
                        text:
                            'After the countdown, imagine moving your thumb once to swipe the ball',
                      ),
                      const SizedBox(height: 12),
                      _buildInstructionItem(
                        icon: Icons.repeat,
                        text:
                            'After the task is detected, you will be asked to repeat it on a count of 3',
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 20),

                // Timer countdown text
                Text(
                  'This message will close in 15 seconds',
                  style: TextStyle(
                    fontSize: 14,
                    fontStyle: FontStyle.italic,
                    color: Colors.grey[500],
                  ),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        );
      },
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
            style: const TextStyle(color: Colors.white70, fontSize: 15),
          ),
        ),
      ],
    );
  }

  void _setupBCIDetection() async {
    // Setup trigger callback
    _bciService.onTriggerDetected = (trigger, confidence) {
      if (trigger && !_hasAnimated && mounted) {
        print('BCI Trigger detected! Confidence: ${(confidence * 100).toStringAsFixed(0)}%');
        _triggerJump(); // Automatically trigger the ball animation
      }
    };
    
    // Start BCI detection
    final success = await _bciService.startDetection();
    
    if (mounted) {
      setState(() {
        _bciEnabled = success;
      });
      
      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(' BCI Detection Active - Imagine thumb movement to trigger'),
            backgroundColor: Color(0xFF4A90E2),
            duration: Duration(seconds: 3),
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('⚠️ BCI not connected - Using manual trigger'),
            backgroundColor: Colors.orange,
            duration: Duration(seconds: 3),
          ),
        );
      }
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    _bciService.stopDetection();
    super.dispose();
  }

  void _triggerJump() {
    setState(() {
      _hasAnimated = true;
      _showGo = false;
    });
    _controller.reset();
    _controller.forward();
  }

  double _calculateArcHeight(double progress) {
    return -4 * (progress - 0.5) * (progress - 0.5) + 1;
  }

  @override
  Widget build(BuildContext context) {
    final screenHeight = MediaQuery.of(context).size.height;
    final screenWidth = MediaQuery.of(context).size.width;

    return Scaffold(
      backgroundColor: Color(0xFF1a1a1a),
      body: Stack(
        children: [
          Column(
            children: [
              // Top target area - Tunnel Effect
              Container(
                height: 150,
                width: double.infinity,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      Color(0xFF1a1a2e),
                      Color(0xFF16213e),
                    ],
                  ),
                  border: Border(
                    bottom: BorderSide(color: Color(0xFF4A90E2), width: 3),
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Color(0xFF4A90E2).withValues(alpha: 0.3),
                      blurRadius: 20,
                      offset: Offset(0, 5),
                    ),
                  ],
                ),
                child: Stack(
                  children: [
                    // Tunnel circle
                    Align(
                      alignment: Alignment.bottomCenter,
                      child: Container(
                        width: 160,
                        height: 160,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: RadialGradient(
                            colors: [
                              Color(0xFF0a0a0a),
                              Color(0xFF16213e),
                            ],
                            stops: [0.5, 1.0],
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: Color(0xFF4A90E2).withValues(alpha: 0.4),
                              blurRadius: 30,
                              spreadRadius: -5,
                            ),
                          ],
                        ),
                      ),
                    ),
                    // Arched text above tunnel
                    Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.arrow_downward_rounded,
                            color: Color(0xFF4A90E2),
                            size: 32,
                          ),
                          SizedBox(height: 4),
                          Text(
                            'swipe the ball',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w600,
                              color: Colors.white,
                              letterSpacing: 0.5,
                            ),
                          ),
                          Text(
                            'through here',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w600,
                              color: Color(0xFF4A90E2),
                              letterSpacing: 0.5,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),

              Expanded(
                child: Container(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [
                        Color(0xFF1a1a1a),
                        Color(0xFF0f0f0f),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),

          // Animated ball and shadow
          AnimatedBuilder(
            animation: _controller,
            builder: (context, child) {
              // If animation hasn't been triggered, show idle state
              if (!_hasAnimated) {
                return Stack(
                  children: [
                    // Idle Shadow
                    Positioned(
                      left: screenWidth / 2 - 50,
                      bottom: idleShadowBottom,
                      child: Container(
                        width: 100.0,
                        height: 15,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(100),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withValues(alpha: 0.5),
                              blurRadius: 25.0,
                              spreadRadius: 5,
                            ),
                          ],
                        ),
                      ),
                    ),
                    // Idle Ball
                    Positioned(
                      left: screenWidth / 2 - 50,
                      bottom: idleBallBottom,
                      child: Container(
                        width: 100,
                        height: 100,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: RadialGradient(
                            center: Alignment(-0.4, -0.4),
                            radius: 0.6,
                            colors: [
                              Color(0xFF87CEEB),
                              Color(0xFF4A90E2),
                              Color(0xFF2E5C8A),
                            ],
                            stops: [0.0, 0.6, 1.0],
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: Color(0xFF4A90E2).withValues(alpha: 0.5),
                              blurRadius: 25,
                              offset: Offset(0, 10),
                            ),
                          ],
                        ),
                      ),
                    ),
                    if (_showGo)
                      Positioned(
                        left: screenWidth / 2 - 45,
                        bottom: idleBallBottom + 120,
                        child: Text(
                          'GO!',
                          style: TextStyle(
                            fontSize: 48,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF4A90E2),
                            shadows: [
                              Shadow(
                                color: Color(0xFF4A90E2).withValues(alpha: 0.8),
                                blurRadius: 20,
                                offset: Offset(0, 0),
                              ),
                            ],
                          ),
                        ),
                      ),
                  ],
                );
              }

              // Animation is running - calculate animated positions
              final animationProgress = _controller.value;
              double ballBottom;
              double shadowOpacity;
              double shadowSize;
              double shadowBlur;
              double ballScale;

              if (animationProgress <= 0.40) {
                // SHOOTING PHASE
                final shootProgress = animationProgress / 0.40;

                final t = shootProgress;
                final forwardProgress = t;
                final arcProgress = t;

                final arcHeight = _calculateArcHeight(arcProgress);
                final distanceToTravel = screenHeight - 300;
                final forwardMovement = forwardProgress * distanceToTravel;
                final maxArcHeight = 300.0;
                final arcOffset = arcHeight * maxArcHeight;

                // Start from idle position
                ballBottom = idleBallBottom + forwardMovement + arcOffset;

                final easedProgress = Curves.easeOut.transform(shootProgress);
                ballScale = 1.0 - (easedProgress * 0.5);

                shadowOpacity = 0.5 - (shootProgress * 0.4);
                shadowSize = 100.0 - (shootProgress * 60);
                shadowBlur = 25.0 - (shootProgress * 15);
              } else if (animationProgress <= 0.55) {
                // PAUSE PHASE - ball is behind wall
                ballBottom = screenHeight + 100;
                ballScale = 0.5;
                shadowOpacity = 0.1;
                shadowSize = 40.0;
                shadowBlur = 10.0;
              } else {
                // FALLING PHASE
                final fallProgress = (animationProgress - 0.55) / 0.45;

                // Calculate where the ball was at the top
                final topPosition = screenHeight - 50;

                // Fall back down to idle position
                ballBottom = topPosition -
                    (fallProgress * (topPosition - idleBallBottom));
                ballScale = 1.0;

                shadowOpacity = 0.1 + (fallProgress * 0.4);
                shadowSize = 40.0 + (fallProgress * 60);
                shadowBlur = 10.0 + (fallProgress * 15);
              }

              return Stack(
                children: [
                  // Shadow
                  if (animationProgress <= 0.40 || animationProgress > 0.55)
                    Positioned(
                      left: screenWidth / 2 - (shadowSize / 2),
                      bottom: idleShadowBottom,
                      child: Container(
                        width: shadowSize,
                        height: 15,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(100),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withValues(alpha: shadowOpacity),
                              blurRadius: shadowBlur,
                              spreadRadius: 5,
                            ),
                          ],
                        ),
                      ),
                    ),

                  // Ball
                  if (animationProgress <= 0.40 || animationProgress > 0.55)
                    Positioned(
                      left: screenWidth / 2 - 50,
                      bottom: ballBottom,
                      child: Transform.scale(
                        scale: ballScale,
                        child: Container(
                          width: 100,
                          height: 100,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            gradient: RadialGradient(
                              center: Alignment(-0.4, -0.4),
                              radius: 0.6,
                              colors: [
                                Color(0xFF87CEEB),
                                Color(0xFF4A90E2),
                                Color(0xFF2E5C8A),
                              ],
                              stops: [0.0, 0.6, 1.0],
                            ),
                            boxShadow: [
                              BoxShadow(
                                color: Color(0xFF4A90E2).withValues(alpha: 0.4),
                                blurRadius: 20,
                                offset: Offset(0, 8),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  if (animationProgress > 0.55 || _showGo)
                    Positioned(
                      left: screenWidth / 2 - 25,
                      bottom: _showGo ? idleBallBottom + 120 : ballBottom + 120,
                      child: () {
                        String text;
                        Color textColor;

                        if (_showGo) {
                          text = 'GO!';
                          textColor = Color(0xFF4A90E2);
                        } else {
                          final fallProgress =
                              (animationProgress - 0.55) / 0.45;

                          if (fallProgress < 0.40) {
                            text = '3';
                            textColor = Colors.white70;
                          } else if (fallProgress < 0.7) {
                            text = '2';
                            textColor = Colors.white70;
                          } else if (fallProgress < 0.99) {
                            text = '1';
                            textColor = Colors.white70;
                          } else {
                            text = 'GO!';
                            textColor = Color(0xFF4A90E2);
                            // Set flag when we reach GO!
                            WidgetsBinding.instance.addPostFrameCallback((_) {
                              if (mounted) {
                                setState(() {
                                  _showGo = true;
                                });
                              }
                            });
                          }
                        }

                        return Text(
                          text,
                          style: TextStyle(
                            fontSize: 48,
                            fontWeight: FontWeight.bold,
                            color: textColor,
                            shadows: [
                              Shadow(
                                color: textColor.withValues(alpha: 0.6),
                                blurRadius: 15,
                                offset: Offset(0, 0),
                              ),
                            ],
                          ),
                        );
                      }(),
                    ),
                ],
              );
            },
          ),

          // Trigger button - only if bci not attached
          if (!_bciEnabled)
            Positioned(
              bottom: 30,
              right: 30,
              child: Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(30),
                  boxShadow: [
                    BoxShadow(
                      color: Color(0xFF4A90E2).withValues(alpha: 0.5),
                      blurRadius: 20,
                      offset: Offset(0, 5),
                    ),
                  ],
                ),
                child: ElevatedButton(
                  onPressed: _triggerJump,
                  style: ElevatedButton.styleFrom(
                    padding: EdgeInsets.symmetric(horizontal: 30, vertical: 15),
                    backgroundColor: Color(0xFF4A90E2),
                    foregroundColor: Colors.white,
                    elevation: 0,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(30),
                    ),
                  ),
                  child: Text(
                    'MANUAL TRIGGER',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 1.2,
                    ),
                  ),
                ),
              ),
            ),
          
          // BCI Status Indicator 
          if (_bciEnabled)
            Positioned(
              bottom: 30,
              right: 30,
              child: Container(
                padding: EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                decoration: BoxDecoration(
                  color: Colors.black.withValues(alpha: 0.8),
                  borderRadius: BorderRadius.circular(30),
                  border: Border.all(color: Color(0xFF4A90E2), width: 2),
                  boxShadow: [
                    BoxShadow(
                      color: Color(0xFF4A90E2).withValues(alpha: 0.5),
                      blurRadius: 20,
                      offset: Offset(0, 5),
                    ),
                  ],
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.psychology,
                      color: Color(0xFF4A90E2),
                      size: 20,
                    ),
                    SizedBox(width: 8),
                    Text(
                      'BCI ACTIVE',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 1.2,
                      ),
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
