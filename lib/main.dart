import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'firebase_options.dart';
import 'screens/calibration_screen.dart';
import 'screens/device_control_screen.dart';
import 'screens/home_screen.dart';
import 'screens/reset_password.dart';
import 'screens/signin_screen.dart';
import 'screens/signup_screen.dart';
import 'screens/training_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  bool firebaseAvailable = false;

  // Only init Firebase on Android — skip on Windows and web for dev convenience.
  // Set this to true once you're ready to test auth on a real Android device.
  const bool enableFirebaseAuth = false; //  flip to true for real device auth testing

  if (!kIsWeb &&
      defaultTargetPlatform == TargetPlatform.android &&
      enableFirebaseAuth) {
    try {
      final opts = DefaultFirebaseOptions.currentPlatformOrNull;
      if (opts != null) {
        await Firebase.initializeApp(options: opts);
        firebaseAvailable = true;
      }
    } catch (e) {
      debugPrint('Firebase init failed: $e');
    }
  }

  runApp(WaveFlightApp(firebaseAvailable: firebaseAvailable));
}

class WaveFlightApp extends StatelessWidget {
  final bool firebaseAvailable;
  const WaveFlightApp({super.key, required this.firebaseAvailable});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'WaveFlight',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF3A86FF),
          brightness: Brightness.light,
        ),
      ),
      darkTheme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF3A86FF),
          brightness: Brightness.dark,
        ),
      ),
      themeMode: ThemeMode.system,
      // Skip auth screens during development — go straight to home.
      // When enableFirebaseAuth is true, shows sign-in screen instead.
      initialRoute: firebaseAvailable ? '/signin' : '/home',
      routes: {
        '/signin':      (context) => const SigninScreen(),
        '/signup':      (context) => const SignUpPage(),
        '/reset':       (context) => const ResetPasswordScreen(),
        '/home':        (context) => const HomeScreen(),
        '/devices':     (context) => const DeviceControlScreen(),
        '/calibration': (context) => const CalibrationScreen(),
        '/training':    (context) => const TrainingScreen(),
      },
    );
  }
}