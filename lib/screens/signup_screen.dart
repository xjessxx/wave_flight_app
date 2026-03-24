// import 'package:firebase_auth/firebase_auth.dart';
// import 'package:flutter/material.dart';
// import '/reusable_widgets/reusable_widget.dart';

// class SignUpPage extends StatefulWidget {
//   const SignUpPage({super.key});

//   @override
//   SignUpPageState createState() => SignUpPageState();
// }

// class SignUpPageState extends State<SignUpPage> {
//   final TextEditingController _passwordTextController = TextEditingController();
//   final TextEditingController _emailTextController = TextEditingController();
//   final TextEditingController _userNameTextController = TextEditingController();
//   String? _errorMessage;

//   Future<void> _signUp() async {
//     try {
//       await FirebaseAuth.instance.createUserWithEmailAndPassword(
//         email: _emailTextController.text.trim(),
//         password: _passwordTextController.text.trim(),
//       );
//       print("Created New Account");

//       // Navigate to calibration screen for new users
//       if (mounted) {
//         Navigator.pushReplacementNamed(context, '/calibration');
//       }
//     } on FirebaseAuthException catch (e) {
//       setState(() {
//         _errorMessage = e.message ?? "An unexpected error occurred.";
//       });
//     }
//   }

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
//         width: MediaQuery.of(context).size.width,
//         height: MediaQuery.of(context).size.height,
//         decoration: BoxDecoration(
//           gradient: LinearGradient(
//             colors: [
//               Colors.blue,
//               const Color.fromARGB(255, 46, 16, 165),
//               const Color.fromARGB(255, 12, 0, 14),
//             ],
//             begin: Alignment.topCenter,
//             end: Alignment.bottomCenter,
//           ),
//         ),
//         child: SingleChildScrollView(
//           child: Padding(
//             padding: const EdgeInsets.fromLTRB(20, 120, 20, 0),
//             child: Column(
//               children: <Widget>[
//                 const SizedBox(height: 20),
//                 reusableTextField(
//                   "Enter UserName",
//                   Icons.person_outline,
//                   false,
//                   _userNameTextController,
//                 ),
//                 const SizedBox(height: 20),
//                 reusableTextField(
//                   "Enter Email Id",
//                   Icons.email,
//                   false,
//                   _emailTextController,
//                 ),
//                 const SizedBox(height: 20),
//                 reusableTextField(
//                   "Enter Password",
//                   Icons.lock_outlined,
//                   true,
//                   _passwordTextController,
//                 ),
//                 const SizedBox(height: 20),
//                 if (_errorMessage != null)
//                   Padding(
//                     padding: const EdgeInsets.only(bottom: 20),
//                     child: Text(
//                       _errorMessage!,
//                       style: const TextStyle(color: Colors.red),
//                     ),
//                   ),
//                 firebaseUIButton(context, "Sign Up", _signUp),
//               ],
//             ),
//           ),
//         ),
//       ),
//     );
//   }
// }


import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'auth_widgets.dart';

class SignUpPage extends StatefulWidget {
  const SignUpPage({super.key});

  @override
  State<SignUpPage> createState() => _SignUpPageState();
}

class _SignUpPageState extends State<SignUpPage> {
  final _emailController    = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmController  = TextEditingController();
  bool _isLoading     = false;
  bool _googleLoading = false;
  bool _obscure       = true;
  String? _errorMsg;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _confirmController.dispose();
    super.dispose();
  }

  // ── Email / password sign-up ──────────────────────────────────────────────

  Future<void> _signUp() async {
    final email    = _emailController.text.trim();
    final password = _passwordController.text;
    final confirm  = _confirmController.text;

    if (email.isEmpty || password.isEmpty || confirm.isEmpty) {
      _setError('Please fill in all fields.');
      return;
    }
    if (password != confirm) {
      _setError('Passwords do not match.');
      return;
    }
    if (password.length < 8) {
      _setError('Password must be at least 8 characters.');
      return;
    }

    setState(() { _isLoading = true; _errorMsg = null; });
    try {
      await FirebaseAuth.instance.createUserWithEmailAndPassword(
        email: email,
        password: password,
      );
      if (!mounted) return;
      // New users go to calibration so they can set up the headset first
      Navigator.pushReplacementNamed(context, '/calibration');
    } on FirebaseAuthException catch (e) {
      _setError(_authError(e));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  // ── Google sign-up ────────────────────────────────────────────────────────

  Future<void> _googleSignIn() async {
    setState(() => _googleLoading = true);
    try {
      final googleUser = await GoogleSignIn().signIn();
      if (googleUser == null) return;

      final googleAuth = await googleUser.authentication;
      final credential = GoogleAuthProvider.credential(
        accessToken: googleAuth.accessToken,
        idToken:     googleAuth.idToken,
      );

      final result = await FirebaseAuth.instance.signInWithCredential(credential);
      if (!mounted) return;

      // If this is a brand-new Google account, send them to calibration
      final isNew = result.additionalUserInfo?.isNewUser ?? false;
      Navigator.pushReplacementNamed(
          context, isNew ? '/calibration' : '/home');
    } on FirebaseAuthException catch (e) {
      _setError(_authError(e));
    } catch (_) {
      _setError('Google sign-in failed. Please try again.');
    } finally {
      if (mounted) setState(() => _googleLoading = false);
    }
  }

  String _authError(FirebaseAuthException e) {
    switch (e.code) {
      case 'email-already-in-use':
        return 'An account already exists for that email.';
      case 'invalid-email':
        return 'Please enter a valid email address.';
      case 'weak-password':
        return 'Password is too weak. Use at least 8 characters.';
      case 'operation-not-allowed':
        return 'Email sign-up is not enabled. Contact support.';
      default:
        return e.message ?? 'Sign-up failed. Please try again.';
    }
  }

  void _setError(String msg) {
    if (!mounted) return;
    setState(() => _errorMsg = msg);
  }

  // ── UI ────────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        iconTheme: const IconThemeData(color: Colors.white),
        title: const Text('Create account',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.w500)),
      ),
      body: Container(
        width: double.infinity,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [Color(0xFF3A86FF), Color(0xFF240046)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 16),

                const Icon(Icons.psychology, size: 72, color: Colors.white),
                const SizedBox(height: 8),
                const Text(
                  'Join WaveFlight',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 22,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                const Text(
                  'Control your world with your mind',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.white60, fontSize: 13),
                ),

                const SizedBox(height: 32),

                // Error banner
                if (_errorMsg != null) ...[
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.red.withValues(alpha: 0.25),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.red.shade300, width: 0.5),
                    ),
                    child: Text(
                      _errorMsg!,
                      style: const TextStyle(color: Colors.white),
                      textAlign: TextAlign.center,
                    ),
                  ),
                  const SizedBox(height: 16),
                ],

                AuthField(
                  controller: _emailController,
                  hint: 'Email address',
                  icon: Icons.email_outlined,
                  inputType: TextInputType.emailAddress,
                ),
                const SizedBox(height: 14),

                AuthField(
                  controller: _passwordController,
                  hint: 'Password (min 8 characters)',
                  icon: Icons.lock_outline,
                  obscure: _obscure,
                  suffix: IconButton(
                    icon: Icon(
                      _obscure ? Icons.visibility_off : Icons.visibility,
                      color: Colors.white54,
                    ),
                    onPressed: () => setState(() => _obscure = !_obscure),
                  ),
                ),
                const SizedBox(height: 14),

                AuthField(
                  controller: _confirmController,
                  hint: 'Confirm password',
                  icon: Icons.lock_outline,
                  obscure: _obscure,
                  action: TextInputAction.done,
                  onSubmitted: (_) => _signUp(),
                ),

                const SizedBox(height: 28),

                SizedBox(
                  height: 56,
                  child: ElevatedButton(
                    onPressed: _isLoading ? null : _signUp,
                    style: ElevatedButton.styleFrom(
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16)),
                    ),
                    child: _isLoading
                        ? const SizedBox(
                            height: 22, width: 22,
                            child: CircularProgressIndicator(strokeWidth: 2))
                        : const Text('Create account',
                            style: TextStyle(fontSize: 17)),
                  ),
                ),

                const SizedBox(height: 20),

                Row(children: const [
                  Expanded(child: Divider(color: Colors.white30)),
                  Padding(
                    padding: EdgeInsets.symmetric(horizontal: 12),
                    child: Text('or', style: TextStyle(color: Colors.white54)),
                  ),
                  Expanded(child: Divider(color: Colors.white30)),
                ]),

                const SizedBox(height: 20),

                SizedBox(
                  height: 56,
                  child: OutlinedButton.icon(
                    onPressed: _googleLoading ? null : _googleSignIn,
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.white,
                      side: const BorderSide(color: Colors.white38),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16)),
                    ),
                    icon: _googleLoading
                        ? const SizedBox(
                            height: 20, width: 20,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: Colors.white))
                        : Image.asset(
                            'assets/images/google_logo.png',
                            height: 22,
                            errorBuilder: (_, __, ___) => const Icon(
                                Icons.g_mobiledata,
                                color: Colors.white, size: 24),
                          ),
                    label: const Text('Continue with Google'),
                  ),
                ),

                const SizedBox(height: 24),

                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Text('Already have an account? ',
                        style: TextStyle(color: Colors.white70)),
                    GestureDetector(
                      onTap: () => Navigator.pop(context),
                      child: const Text(
                        'Sign in',
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                          decoration: TextDecoration.underline,
                          decorationColor: Colors.white,
                        ),
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 24),

                // Privacy note — important for a health/accessibility app
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.10),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Text(
                    'Your EEG data and BCI calibration stay on your device. '
                    'WaveFlight never uploads brain signal data to any server.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.white60, fontSize: 12),
                  ),
                ),

                const SizedBox(height: 24),
              ],
            ),
          ),
        ),
      ),
    );
  }
}