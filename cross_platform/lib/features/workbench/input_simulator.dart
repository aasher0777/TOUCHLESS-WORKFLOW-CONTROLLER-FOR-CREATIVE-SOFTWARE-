import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../../core/models/landmark_model.dart';
import '../../core/gesture/gesture_dictionary.dart';
import '../../core/services/telemetry_service.dart';

enum SimulationInputMode {
  mockTouchOnDesktop,
  mockMouseOnMobile,
}

class CrossPlatformInputSimulator extends StatefulWidget {
  final Function(HandLandmarksResult simulatedResult)? onSimulatedFrame;
  final Function(Offset normalizedCoord, bool isDown)? onCoordinateStream;

  const CrossPlatformInputSimulator({
    super.key,
    this.onSimulatedFrame,
    this.onCoordinateStream,
  });

  @override
  State<CrossPlatformInputSimulator> createState() => _CrossPlatformInputSimulatorState();
}

class _CrossPlatformInputSimulatorState extends State<CrossPlatformInputSimulator> {
  SimulationInputMode _inputMode = SimulationInputMode.mockTouchOnDesktop;
  Offset _pointerPosition = const Offset(0.5, 0.5);
  bool _isPointerDown = false;
  double _pinchDistance = 0.080; // Distance between thumb and index
  GestureType _currentSimulatedGesture = GestureType.pinch;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Row(
                children: [
                  Icon(Icons.touch_app_rounded, color: Color(0xFF38BDF8), size: 18),
                  SizedBox(width: 8),
                  Text(
                    "CROSS-PLATFORM INPUT SIMULATOR",
                    style: TextStyle(
                      color: Color(0xFFE2E8F0),
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 0.8,
                    ),
                  ),
                ],
              ),
              SegmentedButton<SimulationInputMode>(
                segments: const [
                  ButtonSegment(
                    value: SimulationInputMode.mockTouchOnDesktop,
                    label: Text("Touch on Desktop", style: TextStyle(fontSize: 10)),
                    icon: Icon(Icons.touch_app, size: 12),
                  ),
                  ButtonSegment(
                    value: SimulationInputMode.mockMouseOnMobile,
                    label: Text("Mouse on Mobile", style: TextStyle(fontSize: 10)),
                    icon: Icon(Icons.mouse, size: 12),
                  ),
                ],
                selected: {_inputMode},
                onSelectionChanged: (set) {
                  setState(() {
                    _inputMode = set.first;
                  });
                  TelemetryService().logInfo(
                    "InputSimulator",
                    "Switched input emulation to: ${_inputMode.name}",
                  );
                },
                style: const ButtonStyle(
                  visualDensity: VisualDensity.compact,
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
              ),
            ],
          ),

          const SizedBox(height: 12),

          // Interactive Touchpad / Canvas Area
          ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: AspectRatio(
              aspectRatio: 16 / 9,
              child: Container(
                color: const Color(0xFF0F172A),
                child: Stack(
                  children: [
                    // Grid background
                    CustomPaint(
                      size: Size.infinite,
                      painter: _GridBackgroundPainter(),
                    ),

                    // Gesture / Pointer listener
                    GestureDetector(
                      onPanDown: (details) => _updatePointer(details.localPosition, isDown: true),
                      onPanUpdate: (details) => _updatePointer(details.localPosition, isDown: true),
                      onPanEnd: (_) => _endPointer(),
                      child: Container(
                        color: Colors.transparent,
                        width: double.infinity,
                        height: double.infinity,
                      ),
                    ),

                    // Virtual pointer cursor
                    LayoutBuilder(
                      builder: (context, constraints) {
                        final px = _pointerPosition.dx * constraints.maxWidth;
                        final py = _pointerPosition.dy * constraints.maxHeight;

                        return Positioned(
                          left: px - 20,
                          top: py - 20,
                          child: IgnorePointer(
                            child: AnimatedContainer(
                              duration: const Duration(milliseconds: 50),
                              width: 40,
                              height: 40,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: _isPointerDown
                                    ? const Color(0xFF38BDF8).withOpacity(0.3)
                                    : const Color(0xFF94A3B8).withOpacity(0.15),
                                border: Border.all(
                                  color: _isPointerDown
                                      ? const Color(0xFF38BDF8)
                                      : const Color(0xFF94A3B8),
                                  width: 2,
                                ),
                              ),
                              child: Center(
                                child: Container(
                                  width: 6,
                                  height: 6,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    color: _isPointerDown
                                        ? const Color(0xFF38BDF8)
                                        : const Color(0xFFE2E8F0),
                                  ),
                                ),
                              ),
                            ),
                          ),
                        );
                      },
                    ),

                    // Coordinates Overlay
                    Positioned(
                      bottom: 8,
                      left: 10,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                        decoration: BoxDecoration(
                          color: const Color(0xFF1E293B).withOpacity(0.85),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          "X: ${_pointerPosition.dx.toStringAsFixed(3)}  Y: ${_pointerPosition.dy.toStringAsFixed(3)}  [${_isPointerDown ? 'PRESSED' : 'HOVER'}]",
                          style: const TextStyle(
                            color: Color(0xFF38BDF8),
                            fontSize: 10,
                            fontFamily: 'monospace',
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),

          const SizedBox(height: 12),

          // Quick Gesture Preset Injection Buttons
          const Text(
            "QUICK GESTURE INJECTION PRESETS",
            style: TextStyle(
              color: Color(0xFF94A3B8),
              fontSize: 10,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.0,
            ),
          ),
          const SizedBox(height: 8),

          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _buildInjectionButton(
                label: "Pinch (Close)",
                icon: Icons.compress,
                color: const Color(0xFFF59E0B),
                onTap: () => _injectGesture(GestureType.pinch, pinchDist: 0.035),
              ),
              _buildInjectionButton(
                label: "Pinch (Open)",
                icon: Icons.expand,
                color: const Color(0xFF10B981),
                onTap: () => _injectGesture(GestureType.pinch, pinchDist: 0.140),
              ),
              _buildInjectionButton(
                label: "Pointing",
                icon: Icons.navigation_outlined,
                color: const Color(0xFF38BDF8),
                onTap: () => _injectGesture(GestureType.pointing),
              ),
              _buildInjectionButton(
                label: "Peace Sign",
                icon: Icons.pan_tool_alt,
                color: const Color(0xFFA855F7),
                onTap: () => _injectGesture(GestureType.peaceSign),
              ),
              _buildInjectionButton(
                label: "Closed Fist",
                icon: Icons.front_hand,
                color: const Color(0xFFEF4444),
                onTap: () => _injectGesture(GestureType.closedFist),
              ),
              _buildInjectionButton(
                label: "Swipe Left",
                icon: Icons.arrow_back,
                color: const Color(0xFF6366F1),
                onTap: () => _simulateSwipe(-0.35, 0.0),
              ),
              _buildInjectionButton(
                label: "Swipe Right",
                icon: Icons.arrow_forward,
                color: const Color(0xFF6366F1),
                onTap: () => _simulateSwipe(0.35, 0.0),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildInjectionButton({
    required String label,
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
  }) {
    return ElevatedButton.icon(
      onPressed: onTap,
      icon: Icon(icon, size: 14, color: color),
      label: Text(
        label,
        style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w600),
      ),
      style: ElevatedButton.styleFrom(
        backgroundColor: const Color(0xFF0F172A),
        foregroundColor: color,
        side: BorderSide(color: color.withOpacity(0.4), width: 1),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      ),
    );
  }

  void _updatePointer(Offset localOffset, {required bool isDown}) {
    // In practice, this would use the RenderBox size
    final normX = (localOffset.dx / 320.0).clamp(0.0, 1.0);
    final normY = (localOffset.dy / 180.0).clamp(0.0, 1.0);

    setState(() {
      _pointerPosition = Offset(normX, normY);
      _isPointerDown = isDown;
    });

    widget.onCoordinateStream?.call(_pointerPosition, isDown);
    _emitSimulatedLandmarks();
  }

  void _endPointer() {
    setState(() {
      _isPointerDown = false;
    });
    widget.onCoordinateStream?.call(_pointerPosition, false);
  }

  void _injectGesture(GestureType type, {double? pinchDist}) {
    setState(() {
      _currentSimulatedGesture = type;
      if (pinchDist != null) {
        _pinchDistance = pinchDist;
      }
    });

    TelemetryService().logInfo(
      "Simulator",
      "Injected mock gesture: ${type.name} (pinch distance: ${_pinchDistance.toStringAsFixed(3)})",
    );

    _emitSimulatedLandmarks();
  }

  void _simulateSwipe(double dx, double dy) {
    TelemetryService().logInfo(
      "Simulator",
      "Injected continuous swipe vector (dx: $dx, dy: $dy)",
    );
    // Simulates dynamic coordinate drift
    _updatePointer(Offset((_pointerPosition.dx + dx).clamp(0.1, 0.9) * 320, _pointerPosition.dy * 180), isDown: true);
    Future.delayed(const Duration(milliseconds: 150), _endPointer);
  }

  void _emitSimulatedLandmarks() {
    if (widget.onSimulatedFrame == null) return;

    final baseX = _pointerPosition.dx;
    final baseY = _pointerPosition.dy;
    final simulated = <LandmarkNode>[];

    // Build 21 realistic MediaPipe hand coordinates anchored around baseX, baseY
    // Node 0: Wrist
    simulated.add(LandmarkNode(index: 0, name: "WRIST", x: baseX, y: baseY + 0.15, z: 0.0));

    // Thumb (Nodes 1, 2, 3, 4)
    simulated.add(LandmarkNode(index: 1, name: "THUMB_CMC", x: baseX - 0.04, y: baseY + 0.10, z: -0.01));
    simulated.add(LandmarkNode(index: 2, name: "THUMB_MCP", x: baseX - 0.07, y: baseY + 0.05, z: -0.02));
    simulated.add(LandmarkNode(index: 3, name: "THUMB_IP", x: baseX - 0.09, y: baseY + 0.01, z: -0.02));
    // Node 4: Thumb Tip
    final thumbTipX = baseX - (_pinchDistance / 2);
    simulated.add(LandmarkNode(index: 4, name: "THUMB_TIP", x: thumbTipX, y: baseY - 0.02, z: -0.01));

    // Index (Nodes 5, 6, 7, 8)
    simulated.add(LandmarkNode(index: 5, name: "INDEX_FINGER_MCP", x: baseX - 0.03, y: baseY + 0.03, z: -0.01));
    simulated.add(LandmarkNode(index: 6, name: "INDEX_FINGER_PIP", x: baseX - 0.02, y: baseY - 0.04, z: -0.02));
    simulated.add(LandmarkNode(index: 7, name: "INDEX_FINGER_DIP", x: baseX - 0.01, y: baseY - 0.08, z: -0.02));
    // Node 8: Index Tip
    final indexTipX = baseX + (_pinchDistance / 2);
    simulated.add(LandmarkNode(index: 8, name: "INDEX_FINGER_TIP", x: indexTipX, y: baseY - 0.02, z: -0.01));

    // Middle (Nodes 9, 10, 11, 12)
    simulated.add(LandmarkNode(index: 9, name: "MIDDLE_FINGER_MCP", x: baseX, y: baseY + 0.03, z: -0.01));
    simulated.add(LandmarkNode(index: 10, name: "MIDDLE_FINGER_PIP", x: baseX, y: baseY - 0.05, z: -0.02));
    simulated.add(LandmarkNode(index: 11, name: "MIDDLE_FINGER_DIP", x: baseX, y: baseY - 0.10, z: -0.02));
    simulated.add(LandmarkNode(index: 12, name: "MIDDLE_FINGER_TIP", x: baseX, y: baseY - 0.14, z: -0.02));

    // Ring (Nodes 13, 14, 15, 16)
    simulated.add(LandmarkNode(index: 13, name: "RING_FINGER_MCP", x: baseX + 0.03, y: baseY + 0.04, z: -0.01));
    simulated.add(LandmarkNode(index: 14, name: "RING_FINGER_PIP", x: baseX + 0.03, y: baseY - 0.03, z: -0.01));
    simulated.add(LandmarkNode(index: 15, name: "RING_FINGER_DIP", x: baseX + 0.03, y: baseY - 0.07, z: -0.01));
    simulated.add(LandmarkNode(index: 16, name: "RING_FINGER_TIP", x: baseX + 0.03, y: baseY - 0.11, z: -0.01));

    // Pinky (Nodes 17, 18, 19, 20)
    simulated.add(LandmarkNode(index: 17, name: "PINKY_MCP", x: baseX + 0.06, y: baseY + 0.06, z: 0.00));
    simulated.add(LandmarkNode(index: 18, name: "PINKY_PIP", x: baseX + 0.07, y: baseY + 0.00, z: 0.00));
    simulated.add(LandmarkNode(index: 19, name: "PINKY_DIP", x: baseX + 0.07, y: baseY - 0.04, z: 0.00));
    simulated.add(LandmarkNode(index: 20, name: "PINKY_TIP", x: baseX + 0.07, y: baseY - 0.08, z: 0.00));

    final result = HandLandmarksResult(
      landmarks: simulated,
      boundingBox: HandBoundingBox(
        xMin: (baseX - 0.15).clamp(0.0, 1.0),
        yMin: (baseY - 0.18).clamp(0.0, 1.0),
        xMax: (baseX + 0.15).clamp(0.0, 1.0),
        yMax: (baseY + 0.18).clamp(0.0, 1.0),
        confidence: 0.98,
      ),
      handedness: "Right",
      score: 0.98,
      inferenceLatencyMs: 11.2,
      timestamp: DateTime.now(),
    );

    widget.onSimulatedFrame!(result);
  }
}

class _GridBackgroundPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0xFF1E293B).withOpacity(0.5)
      ..strokeWidth = 1;

    const step = 24.0;
    for (double x = 0; x < size.width; x += step) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }
    for (double y = 0; y < size.height; y += step) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
