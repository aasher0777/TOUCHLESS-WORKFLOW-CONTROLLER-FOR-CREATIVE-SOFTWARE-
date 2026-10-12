import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:window_manager/window_manager.dart';
import 'core/services/telemetry_service.dart';
import 'features/dashboard/gesture_dashboard.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Desktop Window Configuration for Windows Client
  if (!kIsWeb && Platform.isWindows) {
    try {
      await windowManager.ensureInitialized();
      const windowOptions = WindowOptions(
        size: Size(1280, 840),
        minimumSize: Size(900, 600),
        center: true,
        backgroundColor: Colors.transparent,
        skipTaskbar: false,
        titleBarStyle: TitleBarStyle.normal,
        title: "Gesture Studio Pro - Unified Cross-Platform Engine",
      );

      await windowManager.waitUntilReadyToShow(windowOptions, () async {
        await windowManager.show();
        await windowManager.focus();
      });
      TelemetryService().logInfo("Window", "Configured Windows desktop viewport (1280x840, min 900x600).");
    } catch (e) {
      TelemetryService().logWarning("Window", "Window manager init skipped or not supported: $e");
    }
  }

  runApp(const GestureStudioApp());
}

class GestureStudioApp extends StatelessWidget {
  const GestureStudioApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: "Gesture Studio Pro",
      debugShowCheckedModeBanner: false,
      themeMode: ThemeMode.dark,
      darkTheme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF090D16),
        primaryColor: const Color(0xFF0284C7),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF38BDF8),
          secondary: Color(0xFF10B981),
          tertiary: Color(0xFFF59E0B),
          surface: Color(0xFF0F172A),
          background: Color(0xFF090D16),
        ),
        fontFamily: 'Inter',
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFF0F172A),
          foregroundColor: Colors.white,
          elevation: 0,
        ),
      ),
      home: const GestureDashboardScreen(),
    );
  }
}
