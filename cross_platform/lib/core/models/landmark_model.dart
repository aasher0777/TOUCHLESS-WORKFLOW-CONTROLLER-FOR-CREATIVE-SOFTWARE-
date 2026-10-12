/// landmark_model.dart
/// Platform-agnostic data models representing MediaPipe 3D Hand Landmarks,
/// Stage 1 Bounding Boxes, and Stage 2 Skeletal Joint coordinates.

import 'dart:math' as math;

/// Single 3D spatial coordinate joint from MediaPipe Hands (Nodes 0 to 20).
class LandmarkNode {
  final int index;
  final String name;
  final double x; // Normalized [0.0, 1.0]
  final double y; // Normalized [0.0, 1.0]
  final double z; // Depth relative to wrist [normalized]
  final double visibility;
  final double presence;

  const LandmarkNode({
    required this.index,
    required this.name,
    required this.x,
    required this.y,
    required this.z,
    this.visibility = 1.0,
    this.presence = 1.0,
  });

  /// Factory constructor from raw JSON / FFI array
  factory LandmarkNode.fromCoordinates(int idx, String label, double x, double y, double z) {
    return LandmarkNode(index: idx, name: label, x: x, y: y, z: z);
  }

  /// Calculates 3D Euclidean distance to another joint node
  double distanceTo(LandmarkNode other) {
    final dx = x - other.x;
    final dy = y - other.y;
    final dz = z - other.z;
    return math.sqrt(dx * dx + dy * dy + dz * dz);
  }

  /// Calculates 2D Euclidean distance (screen-space)
  double distance2DTo(LandmarkNode other) {
    final dx = x - other.x;
    final dy = y - other.y;
    return math.sqrt(dx * dx + dy * dy);
  }
}

/// Stage 1 Bounding Box enclosing the detected hand.
class HandBoundingBox {
  final double xMin;
  final double yMin;
  final double xMax;
  final double yMax;
  final double confidence;

  const HandBoundingBox({
    required this.xMin,
    required this.yMin,
    required this.xMax,
    required this.yMax,
    this.confidence = 0.95,
  });

  double get width => (xMax - xMin).abs();
  double get height => (yMax - yMin).abs();
}

/// Complete MediaPipe Inference Result for a single hand frame.
class HandLandmarksResult {
  final List<LandmarkNode> landmarks;
  final HandBoundingBox? boundingBox;
  final String handedness; // "Right" or "Left"
  final double score;
  final double inferenceLatencyMs;
  final DateTime timestamp;

  const HandLandmarksResult({
    required this.landmarks,
    this.boundingBox,
    this.handedness = "Right",
    this.score = 0.95,
    this.inferenceLatencyMs = 12.5,
    required this.timestamp,
  });

  bool get isValid => landmarks.length == 21;

  LandmarkNode operator [](int index) => landmarks[index];
}

/// MediaPipe Hand Anatomical Joint Labels
const List<String> kHandLandmarkNames = [
  "WRIST", // 0
  "THUMB_CMC", // 1
  "THUMB_MCP", // 2
  "THUMB_IP", // 3
  "THUMB_TIP", // 4
  "INDEX_FINGER_MCP", // 5
  "INDEX_FINGER_PIP", // 6
  "INDEX_FINGER_DIP", // 7
  "INDEX_FINGER_TIP", // 8
  "MIDDLE_FINGER_MCP", // 9
  "MIDDLE_FINGER_PIP", // 10
  "MIDDLE_FINGER_DIP", // 11
  "MIDDLE_FINGER_TIP", // 12
  "RING_FINGER_MCP", // 13
  "RING_FINGER_PIP", // 14
  "RING_FINGER_DIP", // 15
  "RING_FINGER_TIP", // 16
  "PINKY_MCP", // 17
  "PINKY_PIP", // 18
  "PINKY_DIP", // 19
  "PINKY_TIP", // 20
];
