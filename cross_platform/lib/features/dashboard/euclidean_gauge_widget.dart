import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../../core/gesture/euclidean_tracker.dart';
import '../../core/models/landmark_model.dart';

class EuclideanGaugeWidget extends StatelessWidget {
  final EuclideanTracker tracker;
  final double currentDistance;
  final Function(int nodeA, int nodeB)? onNodesChanged;
  final Function(double pinchThresh)? onThresholdChanged;

  const EuclideanGaugeWidget({
    super.key,
    required this.tracker,
    required this.currentDistance,
    this.onNodesChanged,
    this.onThresholdChanged,
  });

  @override
  Widget build(BuildContext context) {
    final state = tracker.currentState;
    final fill = tracker.getGaugeFill(0.200);

    Color stateColor;
    String stateLabel;
    IconData stateIcon;

    switch (state) {
      case GaugeState.triggered:
        stateColor = const Color(0xFF10B981); // Emerald
        stateLabel = "TRIGGERED (PINCH)";
        stateIcon = Icons.check_circle_rounded;
        break;
      case GaugeState.approaching:
        stateColor = const Color(0xFFF59E0B); // Amber
        stateLabel = "APPROACHING";
        stateIcon = Icons.warning_amber_rounded;
        break;
      case GaugeState.idle:
      default:
        stateColor = const Color(0xFF38BDF8); // Cyan
        stateLabel = "IDLE";
        stateIcon = Icons.radio_button_unchecked_rounded;
        break;
    }

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF334155)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.25),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header & State Badge
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Row(
                children: [
                  Icon(Icons.straighten_rounded, color: Color(0xFF38BDF8), size: 18),
                  SizedBox(width: 8),
                  Text(
                    "EUCLIDEAN DISTANCE GAUGE",
                    style: TextStyle(
                      color: Color(0xFFE2E8F0),
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 0.8,
                    ),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: stateColor.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: stateColor, width: 1.2),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(stateIcon, size: 12, color: stateColor),
                    const SizedBox(width: 4),
                    Text(
                      stateLabel,
                      style: TextStyle(
                        color: stateColor,
                        fontSize: 9.5,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),

          const SizedBox(height: 16),

          // Central Radial Arc & Numeric Readout
          Center(
            child: SizedBox(
              width: 140,
              height: 140,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  CustomPaint(
                    size: const Size(140, 140),
                    painter: _RadialGaugePainter(
                      fillFraction: fill,
                      pinchThresholdFraction: 1.0 - (tracker.pinchThreshold / 0.200).clamp(0.0, 1.0),
                      activeColor: stateColor,
                    ),
                  ),
                  Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        currentDistance.toStringAsFixed(3),
                        style: TextStyle(
                          color: stateColor,
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                          fontFamily: 'monospace',
                        ),
                      ),
                      const Text(
                        "NORMALIZED",
                        style: TextStyle(
                          color: Color(0xFF64748B),
                          fontSize: 9,
                          letterSpacing: 1.0,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        "Threshold: ${tracker.pinchThreshold.toStringAsFixed(3)}",
                        style: const TextStyle(
                          color: Color(0xFF94A3B8),
                          fontSize: 10,
                          fontFamily: 'monospace',
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 16),

          // Node Pair Selector & Slider
          Row(
            children: [
              Expanded(
                child: _buildNodeDropdown(
                  label: "Source Node A",
                  selectedIndex: tracker.nodeA,
                  onChanged: (val) {
                    if (val != null) {
                      onNodesChanged?.call(val, tracker.nodeB);
                    }
                  },
                ),
              ),
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 8),
                child: Icon(Icons.swap_horiz_rounded, color: Color(0xFF64748B), size: 18),
              ),
              Expanded(
                child: _buildNodeDropdown(
                  label: "Target Node B",
                  selectedIndex: tracker.nodeB,
                  onChanged: (val) {
                    if (val != null) {
                      onNodesChanged?.call(tracker.nodeA, val);
                    }
                  },
                ),
              ),
            ],
          ),

          const SizedBox(height: 12),

          // Pinch Sensitivity Slider
          Row(
            children: [
              const Text(
                "Trigger Sensitivity:",
                style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
              ),
              Expanded(
                child: SliderTheme(
                  data: SliderThemeData(
                    trackHeight: 3,
                    thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 6),
                    activeTrackColor: stateColor,
                    inactiveTrackColor: const Color(0xFF334155),
                    thumbColor: stateColor,
                  ),
                  child: Slider(
                    value: tracker.pinchThreshold,
                    min: 0.020,
                    max: 0.120,
                    divisions: 20,
                    onChanged: (val) {
                      onThresholdChanged?.call(val);
                    },
                  ),
                ),
              ),
              Text(
                tracker.pinchThreshold.toStringAsFixed(3),
                style: const TextStyle(color: Colors.white, fontSize: 11, fontFamily: 'monospace'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildNodeDropdown({
    required String label,
    required int selectedIndex,
    required ValueChanged<int?> onChanged,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: Color(0xFF64748B), fontSize: 10)),
        const SizedBox(height: 4),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8),
          decoration: BoxDecoration(
            color: const Color(0xFF0F172A),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: const Color(0xFF334155)),
          ),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<int>(
              isExpanded: true,
              value: selectedIndex,
              dropdownColor: const Color(0xFF0F172A),
              items: List.generate(kHandLandmarkNames.length, (idx) {
                return DropdownMenuItem(
                  value: idx,
                  child: Text(
                    "$idx: ${kHandLandmarkNames[idx]}",
                    style: const TextStyle(color: Color(0xFFE2E8F0), fontSize: 11),
                    overflow: TextOverflow.ellipsis,
                  ),
                );
              }),
              onChanged: onChanged,
            ),
          ),
        ),
      ],
    );
  }
}

class _RadialGaugePainter extends CustomPainter {
  final double fillFraction;
  final double pinchThresholdFraction;
  final Color activeColor;

  _RadialGaugePainter({
    required this.fillFraction,
    required this.pinchThresholdFraction,
    required this.activeColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.width - 16) / 2;

    const startAngle = 0.75 * math.pi;
    const sweepAngle = 1.5 * math.pi;

    // Track Background
    final trackPaint = Paint()
      ..color = const Color(0xFF334155)
      ..strokeWidth = 8
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      sweepAngle,
      false,
      trackPaint,
    );

    // Active Progress Fill
    final activePaint = Paint()
      ..color = activeColor
      ..strokeWidth = 8
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;

    final progressSweep = (sweepAngle * fillFraction.clamp(0.0, 1.0));
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      progressSweep,
      false,
      activePaint,
    );

    // Pinch Threshold Tick Mark
    final thresholdAngle = startAngle + (sweepAngle * pinchThresholdFraction.clamp(0.0, 1.0));
    final tickInner = Offset(
      center.dx + (radius - 8) * math.cos(thresholdAngle),
      center.dy + (radius - 8) * math.sin(thresholdAngle),
    );
    final tickOuter = Offset(
      center.dx + (radius + 8) * math.cos(thresholdAngle),
      center.dy + (radius + 8) * math.sin(thresholdAngle),
    );

    final tickPaint = Paint()
      ..color = const Color(0xFFEF4444)
      ..strokeWidth = 2.5
      ..strokeCap = StrokeCap.round;

    canvas.drawLine(tickInner, tickOuter, tickPaint);
  }

  @override
  bool shouldRepaint(covariant _RadialGaugePainter oldDelegate) =>
      oldDelegate.fillFraction != fillFraction ||
      oldDelegate.pinchThresholdFraction != pinchThresholdFraction ||
      oldDelegate.activeColor != activeColor;
}
