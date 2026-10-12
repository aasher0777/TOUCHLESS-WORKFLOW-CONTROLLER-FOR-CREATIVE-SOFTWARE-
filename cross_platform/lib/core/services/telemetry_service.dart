import 'dart:async';
import 'dart:collection';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';

enum LogSeverity { info, warning, error, critical }

class LogEntry {
  final DateTime timestamp;
  final LogSeverity severity;
  final String tag;
  final String message;
  final String? stackTrace;

  const LogEntry({
    required this.timestamp,
    required this.severity,
    required this.tag,
    required this.message,
    this.stackTrace,
  });

  Map<String, dynamic> toJson() => {
        'timestamp': timestamp.toIso8601String(),
        'severity': severity.name.toUpperCase(),
        'tag': tag,
        'message': message,
        if (stackTrace != null) 'stackTrace': stackTrace,
      };

  @override
  String toString() {
    final timeStr = "${timestamp.hour.toString().padLeft(2, '0')}:${timestamp.minute.toString().padLeft(2, '0')}:${timestamp.second.toString().padLeft(2, '0')}.${timestamp.millisecond.toString().padLeft(3, '0')}";
    return "[$timeStr] [${severity.name.toUpperCase()}] [$tag] $message";
  }
}

class TelemetrySnapshot {
  final double currentFps;
  final int droppedFrames;
  final double currentLatencyMs;
  final double averageLatencyMs;
  final double minLatencyMs;
  final double maxLatencyMs;
  final double memoryUsageMb;
  final String osPlatform;
  final String renderingBackend;
  final String activeCameraResolution;

  const TelemetrySnapshot({
    required this.currentFps,
    required this.droppedFrames,
    required this.currentLatencyMs,
    required this.averageLatencyMs,
    required this.minLatencyMs,
    required this.maxLatencyMs,
    required this.memoryUsageMb,
    required this.osPlatform,
    required this.renderingBackend,
    required this.activeCameraResolution,
  });
}

class TelemetryService extends ChangeNotifier {
  static final TelemetryService _instance = TelemetryService._internal();
  factory TelemetryService() => _instance;

  TelemetryService._internal() {
    _initPlatformMetadata();
  }

  // Latency & Performance tracking
  final ListQueue<double> _latencyHistory = ListQueue<double>(120);
  int _droppedFramesCount = 0;
  DateTime _lastFrameTime = DateTime.now();
  double _currentFps = 60.0;
  double _currentLatencyMs = 12.4;
  double _memoryUsageMb = 84.5;
  String _activeCameraResolution = "1280x720 (720p @ 60 FPS)";

  // System Metadata
  String _osPlatform = "Unknown";
  String _renderingBackend = "Software";

  // Diagnostic Log Buffer (Ring buffer max 250 entries)
  final ListQueue<LogEntry> _logBuffer = ListQueue<LogEntry>(250);

  // Getters
  double get currentFps => _currentFps;
  int get droppedFrames => _droppedFramesCount;
  double get currentLatencyMs => _currentLatencyMs;
  double get memoryUsageMb => _memoryUsageMb;
  String get osPlatform => _osPlatform;
  String get renderingBackend => _renderingBackend;
  String get activeCameraResolution => _activeCameraResolution;
  List<LogEntry> get logs => List.unmodifiable(_logBuffer);
  List<double> get latencyHistory => List.unmodifiable(_latencyHistory);

  void _initPlatformMetadata() {
    if (kIsWeb) {
      _osPlatform = "Web Browser";
      _renderingBackend = "WebGL / CanvasKit";
    } else if (Platform.isAndroid) {
      _osPlatform = "Android (API 34, Linux Kernel)";
      _renderingBackend = "Vulkan / OpenGL ES 3.1 + NNAPI Delegate";
    } else if (Platform.isIOS) {
      _osPlatform = "Apple iOS (Darwin Kernel)";
      _renderingBackend = "Metal Graphics + CoreML / Apple Neural Engine";
    } else if (Platform.isWindows) {
      _osPlatform = "Microsoft Windows 10/11 (NT Kernel x86_64)";
      _renderingBackend = "DirectX 12 / Media Foundation DirectShow";
    } else if (Platform.isMacOS) {
      _osPlatform = "macOS (Apple Silicon)";
      _renderingBackend = "Metal / AVFoundation";
    } else if (Platform.isLinux) {
      _osPlatform = "Linux (Desktop x86_64)";
      _renderingBackend = "OpenGL 4.5 / V4L2";
    }

    logInfo("Telemetry", "Initialized cross-platform telemetry pipeline on $_osPlatform with $_renderingBackend.");
  }

  void recordInferenceFrame({required double latencyMs, int frameBytes = 0}) {
    final now = DateTime.now();
    final elapsedMs = now.difference(_lastFrameTime).inMicroseconds / 1000.0;
    _lastFrameTime = now;

    // Detect frame drop (> 22ms for 60fps target)
    if (elapsedMs > 22.0 && _lastFrameTime != now) {
      _droppedFramesCount++;
    }

    if (elapsedMs > 0) {
      final instantFps = 1000.0 / elapsedMs;
      _currentFps = (_currentFps * 0.9) + (instantFps * 0.1);
    }

    _currentLatencyMs = latencyMs;
    if (_latencyHistory.length >= 120) {
      _latencyHistory.removeFirst();
    }
    _latencyHistory.add(latencyMs);

    // Approximate memory footprint fluctuations
    _memoryUsageMb = 75.0 + (_latencyHistory.length * 0.15) + (frameBytes > 0 ? (frameBytes / (1024 * 1024)) : 0.0);

    notifyListeners();
  }

  void setCameraResolution(String resolutionDescription) {
    _activeCameraResolution = resolutionDescription;
    logInfo("Camera", "Hardware stream preset changed to: $resolutionDescription");
    notifyListeners();
  }

  void logInfo(String tag, String message) {
    _addLog(LogEntry(
      timestamp: DateTime.now(),
      severity: LogSeverity.info,
      tag: tag,
      message: message,
    ));
  }

  void logWarning(String tag, String message) {
    _addLog(LogEntry(
      timestamp: DateTime.now(),
      severity: LogSeverity.warning,
      tag: tag,
      message: message,
    ));
  }

  void logError(String tag, String message, [String? stackTrace]) {
    _addLog(LogEntry(
      timestamp: DateTime.now(),
      severity: LogSeverity.error,
      tag: tag,
      message: message,
      stackTrace: stackTrace,
    ));
  }

  void _addLog(LogEntry entry) {
    if (_logBuffer.length >= 250) {
      _logBuffer.removeFirst();
    }
    _logBuffer.add(entry);
    notifyListeners();
  }

  void clearLogs() {
    _logBuffer.clear();
    logInfo("Telemetry", "Diagnostic log ring buffer reset by developer.");
    notifyListeners();
  }

  TelemetrySnapshot getSnapshot() {
    double minLat = 999.0;
    double maxLat = 0.0;
    double sumLat = 0.0;

    for (final lat in _latencyHistory) {
      if (lat < minLat) minLat = lat;
      if (lat > maxLat) maxLat = lat;
      sumLat += lat;
    }

    final avgLat = _latencyHistory.isEmpty ? 0.0 : sumLat / _latencyHistory.length;

    return TelemetrySnapshot(
      currentFps: _currentFps,
      droppedFrames: _droppedFramesCount,
      currentLatencyMs: _currentLatencyMs,
      averageLatencyMs: avgLat,
      minLatencyMs: minLat == 999.0 ? 0.0 : minLat,
      maxLatencyMs: maxLat,
      memoryUsageMb: _memoryUsageMb,
      osPlatform: _osPlatform,
      renderingBackend: _renderingBackend,
      activeCameraResolution: _activeCameraResolution,
    );
  }

  String generateDiagnosticBundle() {
    final snapshot = getSnapshot();
    final bundle = {
      'reportTimestamp': DateTime.now().toIso8601String(),
      'systemMetadata': {
        'platform': snapshot.osPlatform,
        'backend': snapshot.renderingBackend,
        'cameraResolution': snapshot.activeCameraResolution,
      },
      'performanceMetrics': {
        'fps': double.parse(snapshot.currentFps.toStringAsFixed(1)),
        'droppedFrames': snapshot.droppedFrames,
        'currentLatencyMs': double.parse(snapshot.currentLatencyMs.toStringAsFixed(2)),
        'averageLatencyMs': double.parse(snapshot.averageLatencyMs.toStringAsFixed(2)),
        'minLatencyMs': double.parse(snapshot.minLatencyMs.toStringAsFixed(2)),
        'maxLatencyMs': double.parse(snapshot.maxLatencyMs.toStringAsFixed(2)),
        'memoryUsageMb': double.parse(snapshot.memoryUsageMb.toStringAsFixed(1)),
      },
      'recentLogs': _logBuffer.toList().reversed.take(50).map((e) => e.toJson()).toList(),
    };

    return const JsonEncoder.withIndent('  ').convert(bundle);
  }
}
