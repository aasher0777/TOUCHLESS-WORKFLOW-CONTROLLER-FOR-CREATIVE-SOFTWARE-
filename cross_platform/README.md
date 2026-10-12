# Gesture Studio Pro — Unified Cross-Platform Architecture
### Android • iOS • Windows Native MediaPipe Gesture Engine & Telemetry Workbench

---

## 1. Executive Summary & Architectural Overview

Gesture Studio Pro transitions the Python desktop MediaPipe gesture recognition pipeline into a production-grade, unified cross-platform application deployed natively across **Android (APK / AAB)**, **iOS (IPA / TestFlight)**, and **Windows (x86_64 EXE)**.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Unified Flutter Application Core                     │
│         (Gesture Dashboard, Euclidean Gauge, Skeletal Painter)         │
├──────────────────────────────────┬─────────────────────────────────────┤
│      Platform-Agnostic Logic     │    Cross-Platform Dev Workbench     │
│  - 3D Euclidean Normalization    │  - Live Device Telemetry HUD        │
│  - 21-Node Skeletal Math         │  - Camera & Resolution Switcher     │
│  - Gesture State Machine         │  - Touch / Mouse Input Simulator    │
│  - App Macro Router              │  - Crash & Log Diagnostic Exporter  │
├──────────────────────────────────┴─────────────────────────────────────┤
│            Hardware Abstraction & Native Acceleration Layer            │
├───────────────────────┬────────────────────────┬───────────────────────┤
│        Android        │          iOS           │        Windows        │
│  - AndroidX CameraX   │  - AVFoundation Video  │  - Media Foundation   │
│  - Vulkan / GLES 3.1  │  - Metal Graphics      │  - DirectShow / DX12  │
│  - TFLite GPU / NNAPI │  - CoreML / ANE Accel  │  - window_manager     │
└───────────────────────┴────────────────────────┴───────────────────────┘
```

---

## 2. Directory Structure

```
cross_platform/
├── pubspec.yaml                     # Dependencies (camera, window_manager, provider, ffi)
├── README.md                        # Compilation, setup, and architectural guide
├── android/
│   ├── app/
│   │   ├── build.gradle             # NDK filters, aaptOptions noCompress, CameraX deps
│   │   ├── proguard-rules.pro       # R8/ProGuard preservation rules for MediaPipe & TFLite
│   │   └── src/main/
│   │       └── AndroidManifest.xml  # Hardware camera, GLES 3.1, WakeLock permissions
├── ios/
│   ├── Podfile                      # Deployment target iOS 15+, MediaPipeTasksVision pod
│   └── Runner/
│       └── Info.plist               # NSCameraUsageDescription, Metal hardware flags
├── windows/
│   ├── CMakeLists.txt               # C++20 standard, Windows Media Foundation (mf.lib)
│   └── runner/
│       └── main.cpp                 # MFStartup, COM apartment, native Win32 window loop
└── lib/
    ├── main.dart                    # Application bootstrap, window sizing, dark theme
    ├── core/
    │   ├── gesture/
    │   │   ├── euclidean_tracker.dart   # 3D hand-scale normalized Euclidean distance
    │   │   └── gesture_dictionary.dart  # Contextual macro mappings (Default, Premiere, Figma)
    │   ├── models/
    │   │   └── landmark_model.dart      # 21 MediaPipe joint nodes & Bounding Box DTOs
    │   └── services/
    │       └── telemetry_service.dart   # Latency EMA, frame drops, RAM, log ring buffer
    ├── features/
    │   ├── canvas/
    │   │   └── hand_landmarks_painter.dart # GPU CustomPainter for 60 FPS skeletal mesh
    │   ├── dashboard/
    │   │   ├── euclidean_gauge_widget.dart # Radial arc gauge, sensitivity & node selector
    │   │   └── gesture_dashboard.dart      # Responsive desktop/mobile camera viewport
    │   └── workbench/
    │       ├── diagnostic_workbench.dart   # Embedded modal combining dev tooling
    │       ├── telemetry_hud.dart          # Floating real-time hardware telemetry HUD
    │       ├── input_simulator.dart        # Virtual touchpad & mock gesture injector
    │       └── log_exporter.dart           # Terminal log viewer & diagnostic bundle copy
    └── platform/
        └── camera_service.dart             # Unified CameraX / AVFoundation / MF interface
```

---

## 3. Platform Compilation & Deployment Guide

### Prerequisites
* Flutter SDK >= 3.16.0 (`dart >= 3.2.0`)
* **Android**: Android Studio with Android SDK 34, NDK `25.1.8937393`, CMake 3.22+
* **iOS**: macOS Sonoma/Sequoia with Xcode 15+, CocoaPods 1.14+
* **Windows**: Visual Studio 2022 with "Desktop development with C++", Windows 10/11 SDK

### Build Commands

```bash
# 1. Install dependencies
cd cross_platform
flutter pub get

# 2. Build Android APK (Release with R8 minification)
flutter build apk --release --target-platform android-arm64

# 3. Build Android App Bundle (for Google Play Store)
flutter build appbundle --release

# 4. Build iOS Runner (Requires macOS + Xcode)
cd ios && pod install && cd ..
flutter build ipa --release

# 5. Build Windows 64-bit Native Desktop Client
flutter build windows --release
```
The compiled Windows binary will be located at:
`cross_platform/build/windows/x64/runner/Release/GestureStudioCrossPlatform.exe`
