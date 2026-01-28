import 'package:flutter/material.dart';
import '/reusable_widgets/reusable_widget.dart';

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

  // Static idle position
  static const double idleBallBottom = 100.0;
  static const double idleShadowBottom = 100.0;

  @override
  void initState() {
    super.initState();

    _controller = AnimationController(
      duration: Duration(
          milliseconds:
              3000), //can be increased to allow more time between ball reload
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
    });
  }

  void _showInstructionsPopup() {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        // go away after 10 seconds
        Future.delayed(Duration(seconds: 15), () {
          if (Navigator.canPop(context)) {
            Navigator.of(context).pop();
          }
        });

        return InstructionsDialog(
          title: 'Thumb Movement Detection',
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Welcome to Training Mode!',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              SizedBox(height: 12),
              Text('• Make sure you are in a calm and quiet environment'),
              SizedBox(height: 8),
              Text(
                  '• After the countdown, Imagine moving your thumb once to swipe the ball'),
              SizedBox(height: 8),
              Text(
                  '• After the task is detected, you will be asked to repeat it on a count of 3'),
              SizedBox(height: 12),
              Text(
                'This message will close in 10 seconds',
                style: TextStyle(
                  fontSize: 12,
                  fontStyle: FontStyle.italic,
                  color: Colors.grey[600],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  @override
  void dispose() {
    _controller.dispose();
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
      backgroundColor: Colors.white,
      body: Stack(
        children: [
          Column(
            children: [
              // Top target area
              Container(
                height: 150,
                width: double.infinity,
                decoration: BoxDecoration(
                  color: Colors.grey[300],
                  border: Border(
                    bottom: BorderSide(color: Colors.black, width: 3),
                  ),
                ),
                child: Center(
                  child: Text(
                    'swipe the ball over here',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w500,
                      color: Colors.black87,
                    ),
                  ),
                ),
              ),

              Expanded(
                child: Container(
                  color: Colors.white,
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
                              color: Colors.black.withOpacity(0.5),
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
                              color: Colors.black26,
                              blurRadius: 15,
                              offset: Offset(5, 5),
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
                            color: const Color.fromARGB(255, 22, 210, 8),
                            shadows: [
                              Shadow(
                                color: Colors.black26,
                                blurRadius: 10,
                                offset: Offset(2, 2),
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

              if (animationProgress <= 0.33) {
                // SHOOTING PHASE
                final shootProgress = animationProgress / 0.33;

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
              } else if (animationProgress <= 0.66) {
                // PAUSE PHASE - ball is behind wall
                ballBottom = screenHeight + 100;
                ballScale = 0.5;
                shadowOpacity = 0.1;
                shadowSize = 40.0;
                shadowBlur = 10.0;
              } else {
                // FALLING PHASE
                final fallProgress = (animationProgress - 0.66) / 0.34;

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
                  if (animationProgress <= 0.6 || animationProgress > 0.65)
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
                              color: Colors.black.withOpacity(shadowOpacity),
                              blurRadius: shadowBlur,
                              spreadRadius: 5,
                            ),
                          ],
                        ),
                      ),
                    ),

                  // Ball
                  if (animationProgress <= 0.6 || animationProgress > 0.65)
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
                                color: Colors.black26,
                                blurRadius: 15,
                                offset: Offset(5, 5),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  if (animationProgress > 0.66 || _showGo)
                    Positioned(
                      left: screenWidth / 2 - 25,
                      bottom: _showGo ? idleBallBottom + 120 : ballBottom + 120,
                      child: () {
                        String text;

                        if (_showGo) {
                          text = 'GO!';
                        } else {
                          final fallProgress =
                              (animationProgress - 0.66) / 0.34;

                          if (fallProgress < 0.40) {
                            text = '3';
                          } else if (fallProgress < 0.7) {
                            text = '2';
                          } else if (fallProgress < 0.99) {
                            text = '1';
                          } else {
                            text = 'GO!';
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
                            color: const Color.fromARGB(255, 28, 61, 88),
                            shadows: [
                              Shadow(
                                color: Colors.black26,
                                blurRadius: 10,
                                offset: Offset(2, 2),
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

          // Trigger button )
          Positioned(
            bottom: 30,
            right: 30,
            child: ElevatedButton(
              onPressed: _triggerJump,
              style: ElevatedButton.styleFrom(
                padding: EdgeInsets.symmetric(horizontal: 30, vertical: 15),
                backgroundColor: Colors.blue,
                foregroundColor: Colors.white,
                elevation: 5,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(30),
                ),
              ),
              child: Text(
                'TRIGGER',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
