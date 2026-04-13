// Firebase configuration is injected with --dart-define so this repo can stay public.
// Copy android/app/google-services.json.example to google-services.json locally if
// you want to use the Android Google Services plugin in a private setup.

import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart'
    show TargetPlatform, defaultTargetPlatform, kIsWeb;

class DefaultFirebaseOptions {
  static const String _apiKey = String.fromEnvironment('FIREBASE_API_KEY');
  static const String _appId = String.fromEnvironment('FIREBASE_APP_ID');
  static const String _messagingSenderId =
      String.fromEnvironment('FIREBASE_MESSAGING_SENDER_ID');
  static const String _projectId = String.fromEnvironment('FIREBASE_PROJECT_ID');
  static const String _storageBucket =
      String.fromEnvironment('FIREBASE_STORAGE_BUCKET');

  static bool get _androidConfigured =>
      _apiKey.isNotEmpty &&
      _appId.isNotEmpty &&
      _messagingSenderId.isNotEmpty &&
      _projectId.isNotEmpty;

  static FirebaseOptions? get currentPlatformOrNull {
    if (kIsWeb) return null;
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return _androidConfigured ? android : null;
      default:
        return null; // Windows, iOS, etc. are not configured here.
    }
  }

  static FirebaseOptions get currentPlatform {
    final opts = currentPlatformOrNull;
    if (opts == null) {
      throw UnsupportedError(
        'No Firebase configuration for $defaultTargetPlatform. '
        'Provide Firebase --dart-define values for Android auth support.',
      );
    }
    return opts;
  }

  static FirebaseOptions get android => const FirebaseOptions(
    apiKey: _apiKey,
    appId: _appId,
    messagingSenderId: _messagingSenderId,
    projectId: _projectId,
    storageBucket: _storageBucket,
  );
}
