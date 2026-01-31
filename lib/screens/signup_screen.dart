import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import '/reusable_widgets/reusable_widget.dart';

class SignUpPage extends StatefulWidget {
  const SignUpPage({super.key});

  @override
  _SignUpPageState createState() => _SignUpPageState();
}

class _SignUpPageState extends State<SignUpPage> {
  final TextEditingController _passwordTextController = TextEditingController();
  final TextEditingController _emailTextController = TextEditingController();
  final TextEditingController _userNameTextController = TextEditingController();
  String? _errorMessage;

  Future<void> _signUp() async {
    try {
      await FirebaseAuth.instance.createUserWithEmailAndPassword(
        email: _emailTextController.text.trim(),
        password: _passwordTextController.text.trim(),
      );
      print("Created New Account");

      // Navigate to calibration screen for new users
      if (mounted) {
        Navigator.pushReplacementNamed(context, '/calibration');
      }
    } on FirebaseAuthException catch (e) {
      setState(() {
        _errorMessage = e.message ?? "An unexpected error occurred.";
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Text(
          "Sign Up",
          style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
        ),
      ),
      body: Container(
        width: MediaQuery.of(context).size.width,
        height: MediaQuery.of(context).size.height,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              Colors.blue,
              const Color.fromARGB(255, 46, 16, 165),
              const Color.fromARGB(255, 12, 0, 14),
            ],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 120, 20, 0),
            child: Column(
              children: <Widget>[
                const SizedBox(height: 20),
                reusableTextField(
                  "Enter UserName",
                  Icons.person_outline,
                  false,
                  _userNameTextController,
                ),
                const SizedBox(height: 20),
                reusableTextField(
                  "Enter Email Id",
                  Icons.email,
                  false,
                  _emailTextController,
                ),
                const SizedBox(height: 20),
                reusableTextField(
                  "Enter Password",
                  Icons.lock_outlined,
                  true,
                  _passwordTextController,
                ),
                const SizedBox(height: 20),
                if (_errorMessage != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 20),
                    child: Text(
                      _errorMessage!,
                      style: const TextStyle(color: Colors.red),
                    ),
                  ),
                firebaseUIButton(context, "Sign Up", _signUp),
              ],
            ),
          ),
        ),
      ),
    );
  }
}




//
// // ============= previous version ==============
//
// import 'package:firebase_auth/firebase_auth.dart';
// import 'package:flutter/material.dart';
// import 'package:wave_flight_app/screens/home_screen.dart';
// import '/reusable_widgets/reusable_widget.dart';
//
// class SignUpPage extends StatefulWidget {
//   const SignUpPage({super.key});
//
//   @override
//   // ignore: library_private_types_in_public_api
//   _SignUpPageState createState() => _SignUpPageState();
// }
//
// class _SignUpPageState extends State<SignUpPage> {
//   final TextEditingController _passwordTextController = TextEditingController();
//   final TextEditingController _emailTextController = TextEditingController();
//   final TextEditingController _userNameTextController = TextEditingController();
//   String?
//       _errorMessage; // The error message will be held here acoording to the error
//
//   Future<void> _signUp() async {
//     try {
//       await FirebaseAuth.instance.createUserWithEmailAndPassword(
//         email: _emailTextController.text.trim(),
//         password: _passwordTextController.text.trim(),
//       );
//       print("Created New Account");
//       Navigator.pushReplacement(
//         context,
//         MaterialPageRoute(builder: (context) => HomeScreen()),
//       );
//     } on FirebaseAuthException catch (e) {
//       setState(() {
//         _errorMessage = e.message ?? "An unexpected error occurred.";
//       });
//     }
//   }
//
//   @override
//   Widget build(BuildContext context) {
//     return Scaffold(
//       extendBodyBehindAppBar: true,
//       appBar: AppBar(
//         backgroundColor: Colors.transparent,
//         elevation: 0,
//         title: const Text(
//           "Sign Up",
//           style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
//         ),
//       ),
//       body: Container(
//           width: MediaQuery.of(context).size.width,
//           height: MediaQuery.of(context).size.height,
//           decoration: BoxDecoration(
//             gradient: LinearGradient(
//               colors: [
//                 Colors.blue,
//                 const Color.fromARGB(255, 46, 16, 165),
//                 const Color.fromARGB(255, 12, 0, 14),
//               ],
//               begin: Alignment.topCenter,
//               end: Alignment.bottomCenter,
//             ),
//           ),
//           child: SingleChildScrollView(
//               child: Padding(
//             padding: const EdgeInsets.fromLTRB(20, 120, 20, 0),
//             child: Column(
//               children: <Widget>[
//                 const SizedBox(
//                   height: 20,
//                 ),
//                 reusableTextField("Enter UserName", Icons.person_outline, false,
//                     _userNameTextController),
//                 const SizedBox(
//                   height: 20,
//                 ),
//                 reusableTextField(
//                     "Enter Email Id", Icons.email, false, _emailTextController),
//                 const SizedBox(
//                   height: 20,
//                 ),
//                 reusableTextField("Enter Password", Icons.lock_outlined, true,
//                     _passwordTextController),
//                 const SizedBox(
//                   height: 20,
//                 ),
//                 firebaseUIButton(context, "Sign Up", () {
//                   FirebaseAuth.instance
//                       .createUserWithEmailAndPassword(
//                           email: _emailTextController.text,
//                           password: _passwordTextController.text)
//                       .then((value) {
//                     print("Created New Account");
//                     Navigator.push(context,
//                         MaterialPageRoute(builder: (context) => HomeScreen()));
//                   }).onError((error, stackTrace) {
//                     print("Error ${error.toString()}");
//                   });
//                 })
//               ],
//             ),
//           ))),
//     );
//   }
// }
