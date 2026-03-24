// import 'package:flutter/material.dart';

// class SigninScreen extends StatefulWidget {
//   const SigninScreen({super.key});

//   @override
//   State<SigninScreen> createState() => _SigninScreenState();
// }

// class _SigninScreenState extends State<SigninScreen> {
//   final TextEditingController _emailTextController = TextEditingController();
//   final TextEditingController _passwordTextController = TextEditingController();

//   bool _isLoading = false;

//   @override
//   void dispose() {
//     _emailTextController.dispose();
//     _passwordTextController.dispose();
//     super.dispose();
//   }

//   void _signIn() async {
//     final email = _emailTextController.text.trim();
//     final password = _passwordTextController.text;

//     if (email.isEmpty || password.isEmpty) {
//       ScaffoldMessenger.of(context).showSnackBar(
//         const SnackBar(
//           content: Text('Please enter a username/email and password.'),
//         ),
//       );
//       return;
//     }

//     setState(() {
//       _isLoading = true;
//     });

//     await Future.delayed(const Duration(milliseconds: 500));

//     if (!mounted) return;

//     setState(() {
//       _isLoading = false;
//     });

//     Navigator.pushNamedAndRemoveUntil(context, '/home', (route) => false);
//   }

//   @override
//   Widget build(BuildContext context) {
//     return Scaffold(
//       body: Container(
//         width: double.infinity,
//         decoration: const BoxDecoration(
//           gradient: LinearGradient(
//             colors: [Color(0xFF3A86FF), Color(0xFF240046)],
//             begin: Alignment.topLeft,
//             end: Alignment.bottomRight,
//           ),
//         ),
//         child: SafeArea(
//           child: Padding(
//             padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
//             child: Column(
//               mainAxisAlignment: MainAxisAlignment.center,
//               children: [
//                 const Spacer(),
//                 Image.asset(
//                   'assets/brain.png',
//                   height: 160,
//                   errorBuilder: (_, __, ___) => const Icon(
//                     Icons.psychology,
//                     size: 120,
//                     color: Colors.white,
//                   ),
//                 ),
//                 const SizedBox(height: 48),
//                 TextField(
//                   controller: _emailTextController,
//                   decoration: InputDecoration(
//                     hintText: 'Username or email',
//                     prefixIcon: const Icon(Icons.person_outline),
//                     filled: true,
//                     fillColor: Colors.white.withOpacity(0.25),
//                     border: OutlineInputBorder(
//                       borderRadius: BorderRadius.circular(18),
//                       borderSide: BorderSide.none,
//                     ),
//                   ),
//                   style: const TextStyle(color: Colors.white),
//                 ),
//                 const SizedBox(height: 20),
//                 TextField(
//                   controller: _passwordTextController,
//                   obscureText: true,
//                   decoration: InputDecoration(
//                     hintText: 'Password',
//                     prefixIcon: const Icon(Icons.lock_outline),
//                     filled: true,
//                     fillColor: Colors.white.withOpacity(0.25),
//                     border: OutlineInputBorder(
//                       borderRadius: BorderRadius.circular(18),
//                       borderSide: BorderSide.none,
//                     ),
//                   ),
//                   style: const TextStyle(color: Colors.white),
//                 ),
//                 const SizedBox(height: 28),
//                 SizedBox(
//                   width: double.infinity,
//                   height: 56,
//                   child: ElevatedButton(
//                     onPressed: _isLoading ? null : _signIn,
//                     style: ElevatedButton.styleFrom(
//                       shape: RoundedRectangleBorder(
//                         borderRadius: BorderRadius.circular(18),
//                       ),
//                     ),
//                     child: _isLoading
//                         ? const SizedBox(
//                             height: 22,
//                             width: 22,
//                             child: CircularProgressIndicator(strokeWidth: 2),
//                           )
//                         : const Text(
//                             'Sign In',
//                             style: TextStyle(fontSize: 18),
//                           ),
//                   ),
//                 ),
//                 const SizedBox(height: 16),
//                 TextButton(
//                   onPressed: () {
//                     ScaffoldMessenger.of(context).showSnackBar(
//                       const SnackBar(
//                         content: Text('Signup is not enabled in local demo mode yet.'),
//                       ),
//                     );
//                   },
//                   child: const Text(
//                     'Create a free account. Sign Up',
//                     style: TextStyle(color: Colors.white),
//                   ),
//                 ),
//                 const Spacer(),
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

class SigninScreen extends StatefulWidget {
  const SigninScreen({super.key});

  @override
  State<SigninScreen> createState() => _SigninScreenState();
}

class _SigninScreenState extends State<SigninScreen> {
  final _emailController    = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading     = false;
  bool _googleLoading = false;
  bool _obscure       = true;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  // ── Email / password ──────────────────────────────────────────────────────

  Future<void> _signIn() async {
    final email    = _emailController.text.trim();
    final password = _passwordController.text;

    if (email.isEmpty || password.isEmpty) {
      _snack('Please enter your email and password.');
      return;
    }

    setState(() => _isLoading = true);
    try {
      await FirebaseAuth.instance.signInWithEmailAndPassword(
        email: email,
        password: password,
      );
      if (!mounted) return;
      Navigator.pushNamedAndRemoveUntil(context, '/home', (_) => false);
    } on FirebaseAuthException catch (e) {
      _snack(_authError(e));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  // ── Google sign-in ────────────────────────────────────────────────────────

  Future<void> _googleSignIn() async {
    setState(() => _googleLoading = true);
    try {
      final googleUser = await GoogleSignIn().signIn();
      if (googleUser == null) return; // cancelled by user

      final googleAuth = await googleUser.authentication;
      final credential = GoogleAuthProvider.credential(
        accessToken: googleAuth.accessToken,
        idToken:     googleAuth.idToken,
      );

      await FirebaseAuth.instance.signInWithCredential(credential);
      if (!mounted) return;
      Navigator.pushNamedAndRemoveUntil(context, '/home', (_) => false);
    } on FirebaseAuthException catch (e) {
      _snack(_authError(e));
    } catch (_) {
      _snack('Google sign-in failed. Please try again.');
    } finally {
      if (mounted) setState(() => _googleLoading = false);
    }
  }

  String _authError(FirebaseAuthException e) {
    switch (e.code) {
      case 'user-not-found':    return 'No account found for that email.';
      case 'wrong-password':
      case 'invalid-credential': return 'Incorrect email or password.';
      case 'invalid-email':     return 'Please enter a valid email address.';
      case 'user-disabled':     return 'This account has been disabled.';
      case 'too-many-requests': return 'Too many attempts — please wait and try again.';
      default: return e.message ?? 'Sign-in failed. Please try again.';
    }
  }

  void _snack(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  // ── UI ────────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
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
            padding: const EdgeInsets.symmetric(horizontal: 32),
            child: Column(
              children: [
                SizedBox(height: MediaQuery.of(context).size.height * 0.08),

                // Logo
                Image.asset(
                  'assets/images/brain_logo.png',
                  height: 140,
                  errorBuilder: (_, __, ___) =>
                      const Icon(Icons.psychology, size: 120, color: Colors.white),
                ),
                const SizedBox(height: 8),
                const Text(
                  'WaveFlight',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 26,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.5,
                  ),
                ),
                const SizedBox(height: 4),
                const Text(
                  'BCI accessibility platform',
                  style: TextStyle(color: Colors.white60, fontSize: 13),
                ),

                const SizedBox(height: 40),

                // Email
                AuthField(
                  controller: _emailController,
                  hint: 'Email address',
                  icon: Icons.email_outlined,
                  inputType: TextInputType.emailAddress,
                ),
                const SizedBox(height: 16),

                // Password
                AuthField(
                  controller: _passwordController,
                  hint: 'Password',
                  icon: Icons.lock_outline,
                  obscure: _obscure,
                  action: TextInputAction.done,
                  onSubmitted: (_) => _signIn(),
                  suffix: IconButton(
                    icon: Icon(
                      _obscure ? Icons.visibility_off : Icons.visibility,
                      color: Colors.white54,
                    ),
                    onPressed: () => setState(() => _obscure = !_obscure),
                  ),
                ),

                // Forgot password
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton(
                    onPressed: () => Navigator.pushNamed(context, '/reset'),
                    child: const Text(
                      'Forgot password?',
                      style: TextStyle(color: Colors.white70),
                    ),
                  ),
                ),

                const SizedBox(height: 8),

                // Sign In button
                SizedBox(
                  width: double.infinity,
                  height: 56,
                  child: ElevatedButton(
                    onPressed: _isLoading ? null : _signIn,
                    style: ElevatedButton.styleFrom(
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16)),
                    ),
                    child: _isLoading
                        ? const SizedBox(
                            height: 22, width: 22,
                            child: CircularProgressIndicator(strokeWidth: 2))
                        : const Text('Sign In', style: TextStyle(fontSize: 17)),
                  ),
                ),

                const SizedBox(height: 20),

                // Divider
                Row(children: [
                  const Expanded(child: Divider(color: Colors.white30)),
                  const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 12),
                    child: Text('or', style: TextStyle(color: Colors.white54)),
                  ),
                  const Expanded(child: Divider(color: Colors.white30)),
                ]),

                const SizedBox(height: 20),

                // Google sign-in
                SizedBox(
                  width: double.infinity,
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
                            errorBuilder: (_, __, ___) =>
                                const Icon(Icons.g_mobiledata,
                                    color: Colors.white, size: 24),
                          ),
                    label: const Text('Continue with Google'),
                  ),
                ),

                const SizedBox(height: 24),

                // Sign up link
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Text('New to WaveFlight? ',
                        style: TextStyle(color: Colors.white70)),
                    GestureDetector(
                      onTap: () => Navigator.pushNamed(context, '/signup'),
                      child: const Text(
                        'Create account',
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

                const SizedBox(height: 32),
              ],
            ),
          ),
        ),
      ),
    );
  }
}