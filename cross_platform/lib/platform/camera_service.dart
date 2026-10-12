/// camera_service.dart
/// Unified Cross-Platform Camera Abstraction Layer interfacing with:
/// - AndroidX CameraX on Android
/// - AVFoundation on iOS
/// - Windows Media Foundation on Windows

import 'dart:io';
import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';

class CameraStreamConfig {
  final ResolutionPreset resolution;
  final bool enableAudio;
  final ImageFormatGroup imageFormat;

  const CameraStreamConfig({
    this.resolution = ResolutionPreset.medium, // 720p balance for ML inference
    this.enableAudio = false,
    this.imageFormat = ImageFormatGroup.yuv420,
  });
}

class CameraService {
  List<CameraDescription> _availableCameras = [];
  CameraController? _controller;
  int _selectedCameraIndex = 0;
  bool _isStreaming = false;

  List<CameraDescription> get availableCameras => _availableCameras;
  CameraController? get controller => _controller;
  bool get isInitialized => _controller != null && _controller!.value.isInitialized;
  int get selectedCameraIndex => _selectedCameraIndex;

  /// Initializes hardware cameras and selects optimal default
  Future<void> initialize() async {
    try {
      _availableCameras = await availableCameras();
      if (_availableCameras.isEmpty) {
        debugPrint("[CameraService] No physical camera devices detected.");
        return;
      }

      // Default: Front-facing on mobile, primary index 0 on desktop
      int defaultIdx = 0;
      if (Platform.isAndroid || Platform.isIOS) {
        final frontIdx = _availableCameras.indexWhere(
          (c) => c.lensDirection == CameraLensDirection.front,
        );
        if (frontIdx != -1) defaultIdx = frontIdx;
      }

      await switchCamera(defaultIdx, ResolutionPreset.medium);
    } catch (e) {
      debugPrint("[CameraService] Initialization error: $e");
    }
  }

  /// Switches active camera (e.g. Front vs Back on mobile, Integrated vs USB on Windows)
  Future<void> switchCamera(int cameraIndex, ResolutionPreset preset) async {
    if (cameraIndex < 0 || cameraIndex >= _availableCameras.length) return;

    if (_controller != null) {
      await _controller!.stopImageStream().catchError((_) {});
      await _controller!.dispose();
    }

    _selectedCameraIndex = cameraIndex;
    final camera = _availableCameras[cameraIndex];

    _controller = CameraController(
      camera,
      preset,
      enableAudio: false,
      imageFormatGroup: Platform.isAndroid
          ? ImageFormatGroup.yuv420
          : Platform.isIOS
              ? ImageFormatGroup.bgra8888
              : ImageFormatGroup.unknown,
    );

    await _controller!.initialize();
    _isStreaming = true;
    debugPrint(
      "[CameraService] Connected to ${camera.name} on ${Platform.operatingSystem} "
      "(${camera.lensDirection}) at preset: ${preset.name}",
    );
  }

  /// Sets up continuous image stream pipeline to MediaPipe inference engine
  Future<void> startImageStream(Function(CameraImage image) onFrame) async {
    if (_controller == null || !_controller!.value.isInitialized) return;
    if (_controller!.value.isStreamingImages) return;

    await _controller!.startImageStream((CameraImage image) {
      onFrame(image);
    });
  }

  Future<void> stopImageStream() async {
    if (_controller != null && _controller!.value.isStreamingImages) {
      await _controller!.stopImageStream();
    }
  }

  Future<void> dispose() async {
    await stopImageStream();
    await _controller?.dispose();
    _controller = null;
  }
}
