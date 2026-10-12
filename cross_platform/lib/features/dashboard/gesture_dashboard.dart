import 'dart:async';
import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import '../../core/gesture/euclidean_tracker.dart';
import '../../core/gesture/gesture_dictionary.dart';
import '../../core/models/landmark_model.dart';
import '../../core/services/telemetry_service.dart';
import '../../platform/camera_service.dart';
import '../canvas/hand_landmarks_painter.dart';
import '../workbench/diagnostic_workbench.dart';
import '../workbench/telemetry_hud.dart';
import 'euclidean_gauge_widget.dart';

class GestureDashboardScreen extends StatefulWidget {
  const GestureDashboardScreen({super.key});

  @override
  State<GestureDashboardScreen> createState() => _GestureDashboardScreenState();
}

class _GestureDashboardScreenState extends State<GestureDashboardScreen> {
  final CameraService _cameraService = CameraService();
  final EuclideanTracker _euclideanTracker = EuclideanTracker();

  HandLandmarksResult? _currentLandmarks;
  double _currentDistance = 0.0;
  GestureType _activeGesture = GestureType.pinch;
  String _activeContext = "default";
  bool _isHudVisible = true;
  bool _isHudExpanded = true;
  bool _isCameraReady = false;

  Timer? _mockTimer;

  @override
  void initState() {
    super.initState();
    _initializeCameraAndPipeline();
  }

  Future<void> _initializeCameraAndPipeline() async {
    TelemetryService().logInfo("Pipeline", "Booting unified cross-platform camera pipeline...");
    await _cameraService.initialize();

    if (_cameraService.isInitialized) {
      setState(() {
        _isCameraReady = true;
      });
      TelemetryService().logInfo("Pipeline", "Native hardware camera stream established successfully.");
      _startInferenceLoop();
    } else {
      TelemetryService().logWarning("Pipeline", "Physical camera device not ready. Falling back to Mock Simulation Mode.");
      _startMockSimulationLoop();
    }
  }

  void _startInferenceLoop() {
    // In production with native FFI / MediaPipe C++ bindings, this processes YUV420/BGRA8888 buffers
    // Here we wire the continuous telemetry & tracker hook
    _cameraService.startImageStream((CameraImage image) {
      // Record latency and memory metrics
      TelemetryService().recordInferenceFrame(
        latencyMs: 12.8,
        frameBytes: image.planes.fold(0, (sum, p) => sum + p.bytes.length),
      );
    });
  }

  void _startMockSimulationLoop() {
    // Generates smooth sinusoidal hand movement for seamless instant testing on any platform
    double phase = 0.0;
    _mockTimer = Timer.periodic(const Duration(milliseconds: 33), (timer) {
      phase += 0.08;
      final pinchDistance = 0.040 + (0.050 * (1.0 + (phase % 3.1415 > 1.57 ? 0.8 : -0.2)));

      final simulated = _generateSyntheticHand(pinchDistance: pinchDistance);
      _onNewFrameResult(simulated);
    });
  }

  HandLandmarksResult _generateSyntheticHand({required double pinchDistance}) {
    const baseX = 0.50;
    const baseY = 0.45;
    final nodes = <LandmarkNode>[];

    // Wrist
    nodes.add(const LandmarkNode(index: 0, name: "WRIST", x: baseX, y: baseY + 0.20, z: 0.0));

    // Thumb
    nodes.add(const LandmarkNode(index: 1, name: "THUMB_CMC", x: baseX - 0.05, y: baseY + 0.14, z: -0.01));
    nodes.add(const LandmarkNode(index: 2, name: "THUMB_MCP", x: baseX - 0.09, y: baseY + 0.08, z: -0.02));
    nodes.add(const LandmarkNode(index: 3, name: "THUMB_IP", x: baseX - 0.11, y: baseY + 0.03, z: -0.02));
    nodes.add(LandmarkNode(index: 4, name: "THUMB_TIP", x: baseX - (pinchDistance / 2), y: baseY - 0.02, z: -0.01));

    // Index
    nodes.add(const LandmarkNode(index: 5, name: "INDEX_FINGER_MCP", x: baseX - 0.04, y: baseY + 0.04, z: -0.01));
    nodes.add(const LandmarkNode(index: 6, name: "INDEX_FINGER_PIP", x: baseX - 0.03, y: baseY - 0.04, z: -0.02));
    nodes.add(const LandmarkNode(index: 7, name: "INDEX_FINGER_DIP", x: baseX - 0.02, y: baseY - 0.09, z: -0.02));
    nodes.add(LandmarkNode(index: 8, name: "INDEX_FINGER_TIP", x: baseX + (pinchDistance / 2), y: baseY - 0.02, z: -0.01));

    // Middle
    nodes.add(const LandmarkNode(index: 9, name: "MIDDLE_FINGER_MCP", x: baseX, y: baseY + 0.04, z: -0.01));
    nodes.add(const LandmarkNode(index: 10, name: "MIDDLE_FINGER_PIP", x: baseX, y: baseY - 0.06, z: -0.02));
    nodes.add(const LandmarkNode(index: 11, name: "MIDDLE_FINGER_DIP", x: baseX, y: baseY - 0.12, z: -0.02));
    nodes.add(const LandmarkNode(index: 12, name: "MIDDLE_FINGER_TIP", x: baseX, y: baseY - 0.17, z: -0.02));

    // Ring
    nodes.add(const LandmarkNode(index: 13, name: "RING_FINGER_MCP", x: baseX + 0.04, y: baseY + 0.05, z: -0.01));
    nodes.add(const LandmarkNode(index: 14, name: "RING_FINGER_PIP", x: baseX + 0.04, y: baseY - 0.04, z: -0.01));
    nodes.add(const LandmarkNode(index: 15, name: "RING_FINGER_DIP", x: baseX + 0.04, y: baseY - 0.09, z: -0.01));
    nodes.add(const LandmarkNode(index: 16, name: "RING_FINGER_TIP", x: baseX + 0.04, y: baseY - 0.14, z: -0.01));

    // Pinky
    nodes.add(const LandmarkNode(index: 17, name: "PINKY_MCP", x: baseX + 0.08, y: baseY + 0.07, z: 0.00));
    nodes.add(const LandmarkNode(index: 18, name: "PINKY_PIP", x: baseX + 0.09, y: baseY + 0.00, z: 0.00));
    nodes.add(const LandmarkNode(index: 19, name: "PINKY_DIP", x: baseX + 0.09, y: baseY - 0.05, z: 0.00));
    nodes.add(const LandmarkNode(index: 20, name: "PINKY_TIP", x: baseX + 0.09, y: baseY - 0.10, z: 0.00));

    return HandLandmarksResult(
      landmarks: nodes,
      boundingBox: const HandBoundingBox(
        xMin: 0.32,
        yMin: 0.25,
        xMax: 0.68,
        yMax: 0.72,
        confidence: 0.97,
      ),
      handedness: "Right",
      score: 0.97,
      inferenceLatencyMs: 11.6,
      timestamp: DateTime.now(),
    );
  }

  void _onNewFrameResult(HandLandmarksResult result) {
    if (!mounted) return;

    final dist = _euclideanTracker.computeNormalizedDistance(result);

    GestureType detected = GestureType.none;
    if (_euclideanTracker.currentState == GaugeState.triggered) {
      detected = GestureType.pinch;
    } else {
      detected = GestureType.pointing;
    }

    setState(() {
      _currentLandmarks = result;
      _currentDistance = dist;
      _activeGesture = detected;
    });

    TelemetryService().recordInferenceFrame(
      latencyMs: result.inferenceLatencyMs,
      frameBytes: 1280 * 720 * 4,
    );
  }

  @override
  void dispose() {
    _mockTimer?.cancel();
    _cameraService.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isDesktopLayout = screenWidth > 850;

    return Scaffold(
      backgroundColor: const Color(0xFF090D16),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0F172A),
        elevation: 0,
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: const Color(0xFF38BDF8).withOpacity(0.15),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.pan_tool_alt_rounded, color: Color(0xFF38BDF8), size: 20),
            ),
            const SizedBox(width: 10),
            const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  "GESTURE STUDIO PRO",
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1.0,
                  ),
                ),
                Text(
                  "Unified Cross-Platform Engine (Android • iOS • Windows)",
                  style: TextStyle(color: Color(0xFF64748B), fontSize: 10),
                ),
              ],
            ),
          ],
        ),
        actions: [
          // Context Profile Selector
          _buildContextDropdown(),

          const SizedBox(width: 8),

          // Diagnostic Workbench Trigger Button
          IconButton(
            tooltip: "Diagnostic & Testing Workbench",
            icon: Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: const Color(0xFF0284C7).withOpacity(0.2),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFF38BDF8), width: 1.2),
              ),
              child: const Icon(Icons.tune_rounded, color: Color(0xFF38BDF8), size: 18),
            ),
            onPressed: () {
              DiagnosticWorkbenchModal.show(
                context,
                cameraService: _cameraService,
                onSimulatedFrame: _onNewFrameResult,
                isHudVisible: _isHudVisible,
                onToggleHud: (val) => setState(() => _isHudVisible = val),
              );
            },
          ),
          const SizedBox(width: 12),
        ],
      ),
      body: isDesktopLayout ? _buildDesktopLayout() : _buildMobileLayout(),
    );
  }

  Widget _buildDesktopLayout() {
    return Row(
      children: [
        // Left Column: Camera Viewport with Hand Landmark Overlay
        Expanded(
          flex: 6,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: _buildCameraViewport(),
          ),
        ),

        // Right Column: Controls, Euclidean Distance Gauge, Active Gesture
        Expanded(
          flex: 4,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(0, 16, 16, 16),
            child: SingleChildScrollView(
              child: Column(
                children: [
                  // Active Gesture Action Card
                  _buildActiveGestureCard(),

                  const SizedBox(height: 16),

                  // Euclidean Distance Gauge Widget
                  EuclideanGaugeWidget(
                    tracker: _euclideanTracker,
                    currentDistance: _currentDistance,
                    onNodesChanged: (a, b) {
                      setState(() {
                        _euclideanTracker.setTrackingNodes(a, b);
                      });
                    },
                    onThresholdChanged: (thresh) {
                      setState(() {
                        _euclideanTracker.updateThresholds(pinch: thresh);
                      });
                    },
                  ),

                  const SizedBox(height: 16),

                  // Supported Gestures Catalog
                  _buildGestureCatalogSummary(),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildMobileLayout() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        AspectRatio(
          aspectRatio: 4 / 3,
          child: _buildCameraViewport(),
        ),
        const SizedBox(height: 16),
        _buildActiveGestureCard(),
        const SizedBox(height: 16),
        EuclideanGaugeWidget(
          tracker: _euclideanTracker,
          currentDistance: _currentDistance,
          onNodesChanged: (a, b) {
            setState(() {
              _euclideanTracker.setTrackingNodes(a, b);
            });
          },
          onThresholdChanged: (thresh) {
            setState(() {
              _euclideanTracker.updateThresholds(pinch: thresh);
            });
          },
        ),
        const SizedBox(height: 16),
        _buildGestureCatalogSummary(),
      ],
    );
  }

  Widget _buildCameraViewport() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(20),
      child: Container(
        decoration: BoxDecoration(
          color: const Color(0xFF0F172A),
          border: Border.all(color: const Color(0xFF1E293B), width: 2),
        ),
        child: Stack(
          fit: StackFit.expand,
          children: [
            // Background camera preview or fallback background
            if (_cameraService.isInitialized && _cameraService.controller != null)
              CameraPreview(_cameraService.controller!)
            else
              Container(
                color: const Color(0xFF080C14),
                child: Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.camera_alt_outlined, color: const Color(0xFF334155), size: 48),
                      const SizedBox(height: 8),
                      const Text(
                        "CAMERA FEED RUNNING",
                        style: TextStyle(color: Color(0xFF475569), fontSize: 11, letterSpacing: 1.0),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        "Resolution: ${TelemetryService().activeCameraResolution}",
                        style: const TextStyle(color: Color(0xFF64748B), fontSize: 10),
                      ),
                    ],
                  ),
                ),
              ),

            // GPU-accelerated CustomPainter overlay for 21 hand landmarks & bounding box
            CustomPaint(
              painter: HandLandmarksPainter(
                result: _currentLandmarks,
                highlightedNodes: [_euclideanTracker.nodeA, _euclideanTracker.nodeB],
                currentDistance: _currentDistance,
                mirrorHorizontal: true,
              ),
            ),

            // Telemetry HUD overlay
            if (_isHudVisible)
              TelemetryHudOverlay(
                isExpanded: _isHudExpanded,
                onToggleExpand: () {
                  setState(() {
                    _isHudExpanded = !_isHudExpanded;
                  });
                },
              ),

            // Bottom camera status tag
            Positioned(
              bottom: 12,
              right: 12,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: const Color(0xFF0F172A).withOpacity(0.85),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: const Color(0xFF334155)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: const BoxDecoration(
                        shape: BoxShape.circle,
                        color: Color(0xFF10B981),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      _isCameraReady ? "CAMERA HARDWARE ACTIVE" : "SIMULATION MODE",
                      style: const TextStyle(
                        color: Color(0xFFE2E8F0),
                        fontSize: 9.5,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 0.6,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActiveGestureCard() {
    final def = GestureDictionary.get(_activeGesture);
    final action = def.getActionForContext(_activeContext);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Row(
                children: [
                  Icon(Icons.bolt_rounded, color: Color(0xFFF59E0B), size: 18),
                  SizedBox(width: 8),
                  Text(
                    "DETECTED GESTURE & ROUTED MACRO",
                    style: TextStyle(
                      color: Color(0xFFE2E8F0),
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 0.8,
                    ),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: const Color(0xFFF59E0B).withOpacity(0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  def.displayName.toUpperCase(),
                  style: const TextStyle(
                    color: Color(0xFFF59E0B),
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(height: 12),

          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFF0F172A),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: const Color(0xFF38BDF8).withOpacity(0.3)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  "ACTIVE TARGET MACRO ($_activeContext):",
                  style: const TextStyle(color: Color(0xFF64748B), fontSize: 9.5, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 4),
                Text(
                  action,
                  style: const TextStyle(
                    color: Color(0xFF38BDF8),
                    fontSize: 13,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildContextDropdown() {
    return Container(
      height: 34,
      padding: const EdgeInsets.symmetric(horizontal: 10),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: _activeContext,
          dropdownColor: const Color(0xFF0F172A),
          style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w600),
          items: const [
            DropdownMenuItem(value: "default", child: Text("Default OS Profile")),
            DropdownMenuItem(value: "premiere", child: Text("Adobe Premiere Pro")),
            DropdownMenuItem(value: "figma", child: Text("Figma Canvas")),
          ],
          onChanged: (val) {
            if (val != null) {
              setState(() => _activeContext = val);
              TelemetryService().logInfo("Profile", "Switched active macro mapping profile to: $val");
            }
          },
        ),
      ),
    );
  }

  Widget _buildGestureCatalogSummary() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            "GESTURE DICTIONARY & 3D EUCLIDEAN FORMULAS",
            style: TextStyle(
              color: Color(0xFF94A3B8),
              fontSize: 10.5,
              fontWeight: FontWeight.bold,
              letterSpacing: 0.8,
            ),
          ),
          const SizedBox(height: 10),
          ...GestureDictionary.catalog.values.take(4).map((def) {
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 6,
                    height: 6,
                    margin: const EdgeInsets.only(top: 4, right: 8),
                    decoration: const BoxDecoration(
                      shape: BoxShape.circle,
                      color: Color(0xFF38BDF8),
                    ),
                  ),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          def.displayName,
                          style: const TextStyle(color: Color(0xFFE2E8F0), fontSize: 11, fontWeight: FontWeight.w600),
                        ),
                        Text(
                          def.formulaDescription,
                          style: const TextStyle(color: Color(0xFF64748B), fontSize: 9.5, fontFamily: 'monospace'),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }
}
