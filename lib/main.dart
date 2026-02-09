import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'screens/signin_screen.dart';
import 'screens/calibration_screen.dart';
import 'screens/home_screen.dart';
import 'screens/training_screen.dart';
import 'services/bci_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  runApp(const MyApp());
}

class MyApp extends StatefulWidget {
  const MyApp({super.key});

   

  @override
  State<MyApp> createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {

    @override
  void initState() {
    super.initState();
    // Initialize BCI when app starts
    _initializeBCI();
  }

  Future<void> _initializeBCI() async {
    print('🧠 Initializing BCI system...');
    
    // Wait a moment for the app to fully load
    await Future.delayed(Duration(seconds: 1));
    
    final success = await BCIService.instance.initialize();
    
    if (success) {
      print('BCI system initialized successfully'); //this nbeeds to eb the only place this is happening
    } else {
      print('BCI initialization failed - check Python server');
      print('   Run: python bci_flutter_bridge.py');
    }
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'BCI for Accessibility',
      debugShowCheckedModeBanner: false,

      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.blue,
          brightness: Brightness.light,
        ),
      ),

      darkTheme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.blue,
          brightness: Brightness.dark,
        ),
      ),

      themeMode: ThemeMode.system, // or ThemeMode.dark
      initialRoute: '/',
      routes: {
        '/': (context) => const SigninScreen(),
        '/calibration': (context) => const CalibrationScreen(),
        '/home': (context) => const HomeScreen(),
        '/training': (context) => const TrainingScreen(),
      },
    );
  }
}



// // ============= previos version ==============
//
// import 'package:firebase_core/firebase_core.dart';
// import 'package:flutter/material.dart';
// import 'screens/signin_screen.dart';
//
// void main() async {
//   WidgetsFlutterBinding.ensureInitialized();
//   await Firebase.initializeApp();
//   runApp(const MyApp());
// }
//
// class MyApp extends StatelessWidget {
//   const MyApp({super.key});
//
//   // This widget is the root of your application.
//   @override
//   Widget build(BuildContext context) {
//     return MaterialApp(
//       title: 'Flutter Demo',
//       theme: ThemeData(
//         // This is the theme of your application.
//         //
//         // TRY THIS: Try running your application with "flutter run". You'll see
//         // the application has a purple toolbar. Then, without quitting the app,
//         // try changing the seedColor in the colorScheme below to Colors.green
//         // and then invoke "hot reload" (save your changes or press the "hot
//         // reload" button in a Flutter-supported IDE, or press "r" if you used
//         // the command line to start the app).
//         //
//         // Notice that the counter didn't reset back to zero; the application
//         // state is not lost during the reload. To reset the state, use hot
//         // restart instead.
//         //
//         // This works for code too, not just values: Most code changes can be
//         // tested with just a hot reload.
//         colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
//         useMaterial3: true,
//       ),
//       home: const SigninScreen(),
//     );
//   }
// }
