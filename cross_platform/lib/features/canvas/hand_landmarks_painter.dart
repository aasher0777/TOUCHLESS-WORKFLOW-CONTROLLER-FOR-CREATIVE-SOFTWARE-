/// hand_landmarks_painter.dart
/// High-performance GPU-accelerated CustomPainter rendering the 21 MediaPipe
/// skeletal landmarks, active calibration nodes, and Stage 1 bounding box at locked 60 FPS.

import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import '../../core/models/landmark_model.dart';

class HandLandmarksPainter extends CustomPainter {
  final HandLandmarksResult? result;
  final List<int> highlightedNodes;
  final double currentDistance;
  final bool mirrorHorizontal;

  static const List<List<int>> kHandConnections = [
    // Thumb
    [0, 1], [1, 2], [2, 3], [3, 4],
    // Index Finger
    [0, 5], [5, 6], [6, 7], [7, 8],
    // Middle Finger
    [9, 10], [10, 11], [11, 12],
    // Ring Finger
    [13, 14], [14, 15], [15, 16],
    // Pinky
    [0, 17], [17, 18], [18, 19], [19, 20],
    // Palm Knuckles
    [5, 9], [9, 13], [13, 17],
  ];

  HandLandmarksPainter({
    required this.result,
    this.highlightedNodes = const [4, 8],
    this.currentDistance = 0.0,
    this.mirrorHorizontal = true,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (result == null || !result!.isValid) return;

    // 1. Stage 1 Bounding Box
    if (result!.boundingBox != null) {
      _drawBoundingBox(canvas, size, result!.boundingBox!);
    }

    // 2. Skeletal Bones (Edges)
    final bonePaint = Paint()
      ..color = const Color(0xFF38BDF8).withOpacity(0.65) // Cyan glow
      ..strokeWidth = 3.0
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;

    for (final edge in kHandConnections) {
      final p1 = _projectPoint(result![edge[0]], size);
      final p2 = _projectPoint(result![edge[1]], size);
      canvas.drawLine(p1, p2, bonePaint);
    }

    // 3. Highlighted Distance Line (e.g. Node 4 Thumb to Node 8 Index)
    if (highlightedNodes.length >= 2) {
      final pA = _projectPoint(result![highlightedNodes[0]], size);
      final pB = _projectPoint(result![highlightedNodes[1]], size);

      final distanceLinePaint = Paint()
        ..color = const Color(0xFFF59E0B) // Amber
        ..strokeWidth = 2.5
        ..style = PaintingStyle.stroke;

      canvas.drawLine(pA, pB, distanceLinePaint);

      // Distance Metric Tag
      final midPoint = Offset((pA.dx + pB.dx) / 2, (pA.dy + pB.dy) / 2 - 12);
      _drawTextTag(canvas, "d: ${currentDistance.toStringAsFixed(3)}", midPoint);
    }

    // 4. Joint Landmark Nodes (21 Points)
    final nodePaint = Paint()
      ..color = const Color(0xFFE2E8F0)
      ..style = PaintingStyle.fill;

    final activeHaloPaint = Paint()
      ..color = const Color(0xFFF59E0B).withOpacity(0.35)
      ..style = PaintingStyle.fill;

    final activeBorderPaint = Paint()
      ..color = const Color(0xFFF59E0B)
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke;

    for (int i = 0; i < result!.landmarks.length; i++) {
      final node = result![i];
      final pt = _projectPoint(node, size);
      final isHighlighted = highlightedNodes.contains(i);

      if (isHighlighted) {
        // Outer pulsing amber halo
        canvas.drawCircle(pt, 12.0, activeHaloPaint);
        canvas.drawCircle(pt, 8.0, activeBorderPaint);
        canvas.drawCircle(pt, 5.0, Paint()..color = const Color(0xFFF59E0B));
        _drawNodeNumber(canvas, "$i", pt);
      } else {
        canvas.drawCircle(pt, 4.0, nodePaint);
      }
    }
  }

  Offset _projectPoint(LandmarkNode node, Size size) {
    double px = node.x * size.width;
    if (mirrorHorizontal) {
      px = size.width - px; // Mirror front camera view
    }
    double py = node.y * size.height;
    return Offset(px, py);
  }

  void _drawBoundingBox(Canvas canvas, Size size, HandBoundingBox box) {
    double left = box.xMin * size.width;
    double right = box.xMax * size.width;
    if (mirrorHorizontal) {
      final origLeft = left;
      left = size.width - right;
      right = size.width - origLeft;
    }

    final rect = Rect.fromLTRB(left, box.yMin * size.height, right, box.yMax * size.height);
    final boxPaint = Paint()
      ..color = const Color(0xFF10B981).withOpacity(0.7) // Emerald green
      ..strokeWidth = 1.8
      ..style = PaintingStyle.stroke;

    canvas.drawRRect(RRect.fromRectAndRadius(rect, const Radius.circular(8.0)), boxPaint);
    _drawTextTag(canvas, "Hand: ${(box.confidence * 100).toInt()}%", Offset(rect.left + 6, rect.top - 18));
  }

  void _drawTextTag(Canvas canvas, String text, Offset position) {
    final textSpan = TextSpan(
      text: text,
      style: const TextStyle(
        color: Color(0xFFF8FAFC),
        fontSize: 10,
        fontWeight: FontWeight.w600,
        backgroundColor: Color(0xCC0F172A),
      ),
    );
    final textPainter = TextPainter(text: textSpan, textDirection: TextDirection.ltr);
    textPainter.layout();
    textPainter.paint(canvas, position);
  }

  void _drawNodeNumber(Canvas canvas, String number, Offset position) {
    final textSpan = TextSpan(
      text: number,
      style: const TextStyle(
        color: Color(0xFF0F172A),
        fontSize: 8,
        fontWeight: FontWeight.bold,
      ),
    );
    final textPainter = TextPainter(text: textSpan, textDirection: TextDirection.ltr);
    textPainter.layout();
    textPainter.paint(canvas, Offset(position.dx - textPainter.width / 2, position.dy - textPainter.height / 2));
  }

  @override
  bool shouldRepaint(covariant HandLandmarksPainter oldDelegate) => true;
}
