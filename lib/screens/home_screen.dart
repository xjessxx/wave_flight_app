import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';


//placeholder page for getting baseline

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('BCI For Accessibility'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            ElevatedButton(
              child: const Text("Calibration"),
              onPressed: () {
                Navigator.pushNamed(context, '/calibration');
              },
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              child: const Text("Training"),
              onPressed: () {
                Navigator.pushNamed(context, '/training');
              },
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              child: const Text("Logout"),
              onPressed: () {
                FirebaseAuth.instance.signOut().then((value) {
                  Navigator.pushNamedAndRemoveUntil(context, '/', (route) => false);
                });
              },
            ),
          ],
        ),
      ),
    );
  }
}