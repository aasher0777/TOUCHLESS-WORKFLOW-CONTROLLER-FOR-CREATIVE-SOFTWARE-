/// euclidean_tracker.dart
/// Continuous 3D Euclidean distance calculation engine, hand-scale normalization,
/// live gauge metrics, and debounced finite state machine for MediaPipe landmark nodes.

import 'dart:collection';
import 'dart:math' as math;
import '../models/landmark_model.dart';
import 'gesture_dictionary.dart';

enum GaugeState {
  idle,
  approaching,
  triggered,
}

class EuclideanTracker {
  int nodeA;
  int nodeB;
  double pinchThreshold;
  double swipeThreshold;
  double smoothingFactor;

  double _smoothedDistance = 0.0;
  GaugeState _currentState = GaugeState.idle;

  EuclideanTracker({
    this.nodeA = 4, // Thumb Tip
    this.nodeB = 8, // Index Tip
    this.pinchThreshold = 0.060,
    this.swipeThreshold = 0.120,
    this.smoothingFactor = 0.65,
  });

  /// Computes continuous 3D Euclidean distance normalized by the user's hand size.
  /// Hand scale is computed as distance between Wrist (Node 0) and Middle MCP (Node 9).
  double computeNormalizedDistance(HandLandmarksResult result) {
    if (!result.isValid || nodeA >= result.landmarks.length || nodeB >= result.landmarks.length) {
      return 0.0;
    }

    final nA = result[nodeA];
    final nB = result[nodeB];

    // Reference Scale: Palm height (Node 0 Wrist to Node 9 Middle Finger MCP)
    final wrist = result[0];
    final middleMcp = result[9];
    final rawScale = wrist.distanceTo(middleMcp);
    final handScale = rawScale > 0.05 ? rawScale : 1.0;

    // 3D Euclidean Distance
    final raw3DDistance = nA.distanceTo(nB);
    final normalized = raw3DDistance / handScale;

    // Exponential Moving Average (EMA) smoothing to eliminate sensor jitter
    _smoothedDistance = (_smoothingFactor * _smoothedDistance) + ((1.0 - smoothingFactor) * normalized);

    // State Classification
    if (_smoothedDistance <= pinchThreshold) {
      _currentState = GaugeState.triggered;
    } else if (_smoothedDistance <= pinchThreshold * 1.6) {
      _currentState = GaugeState.approaching;
    } else {
      _currentState = GaugeState.idle;
    }

    return _smoothedDistance;
  }

  /// Returns continuous gauge fill percentage [0.0, 1.0] for the UI
  double getGaugeFill(double maxDistanceRange) {
    if (maxDistanceRange <= 0) return 0.0;
    final fill = 1.0 - (_smoothedDistance / maxDistanceRange);
    return fill.clamp(0.0, 1.0);
  }

  double get smoothedDistance => _smoothedDistance;
  GaugeState get currentState => _currentState;

  void setTrackingNodes(int a, int b) {
    nodeA = a;
    nodeB = b;
    _smoothedDistance = 0.0;
  }

  void updateThresholds({double? pinch, double? swipe}) {
    if (pinch != null) pinchThreshold = pinch;
    if (swipe != null) swipeThreshold = swipe;
  }
}

class GestureTransitionEvent {
  final GestureType gesture;
  final String actionName;
  final double confidence;
  final DateTime timestamp;

  GestureTransitionEvent({
    required this.gesture,
    required this.actionName,
    required this.confidence,
    required this.timestamp,
  });
}

class GestureStateMachine {
  final EuclideanTracker tracker;
  final int requiredConsecutiveFrames;
  final Duration cooldownDuration;

  GestureType _currentGesture = GestureType.none;
  GestureType _pendingGesture = GestureType.none;
  int _consecutiveCounter = 0;
  DateTime _lastTriggerTime = DateTime.fromMillisecondsSinceEpoch(0);

  // Position history for swipe trajectory computation (wrist / center of hand)
  final Queue<Map<String, dynamic>> _trajectoryHistory = Queue();
  static const int kMaxHistoryLen = 8;

  GestureStateMachine({
    required this.tracker,
    this.requiredConsecutiveFrames = 2,
    this.cooldownDuration = const Duration(milliseconds: 250),
  });

  /// Evaluates hand landmarks frame and returns an actionable transition event if triggered
  GestureTransitionEvent? processFrame(HandLandmarksResult result, String activeContext) {
    if (!result.isValid) {
      _currentGesture = GestureType.none;
      _pendingGesture = GestureType.none;
      _consecutiveCounter = 0;
      return null;
    }

    // 1. Update continuous 3D Euclidean distance between calibration nodes
    final currentDistance = tracker.computeNormalizedDistance(result);

    // 2. Track wrist spatial trajectory for swipes
    final wrist = result[0];
    final now = DateTime.now();
    _trajectoryHistory.addLast({'x': wrist.x, 'y': wrist.y, 'time': now});
    if (_trajectoryHistory.length > kMaxHistoryLen) {
      _trajectoryHistory.removeFirst();
    }

    // 3. Classify instant raw gesture candidate
    final candidate = _classifyCandidate(result, currentDistance);

    // 4. Consecutive frame debounce verification
    if (candidate == _pendingGesture) {
      _consecutiveCounter++;
    } else {
      _pendingGesture = candidate;
      _consecutiveCounter = 1;
    }

    // 5. Cooldown verification to prevent rapid re-triggering of one-shot actions
    if (_consecutiveCounter >= requiredConsecutiveFrames && candidate != GestureType.none) {
      if (candidate != _currentGesture || now.difference(_lastTriggerTime) > cooldownDuration) {
        _currentGesture = candidate;
        _lastTriggerTime = now;

        final def = GestureDictionary.get(_currentGesture);
        return GestureTransitionEvent(
          gesture: _currentGesture,
          actionName: def.getActionForContext(activeContext),
          confidence: result.score,
          timestamp: now,
        );
      }
    }

    if (candidate == GestureType.none) {
      _currentGesture = GestureType.none;
    }

    return null;
  }

  GestureType _classifyCandidate(HandLandmarksResult result, double continuousDistance) {
    // A. Check Pinch first using continuous Euclidean metric
    if (continuousDistance <= tracker.pinchThreshold) {
      return GestureType.pinch;
    }

    // B. Check Swipes via trajectory velocity
    final swipe = _detectSwipe();
    if (swipe != GestureType.none) {
      return swipe;
    }

    // C. Check Finger Extension States
    final thumbTip = result[4];
    final indexTip = result[8];
    final indexPip = result[6];
    final middleTip = result[12];
    final middlePip = result[10];
    final ringTip = result[16];
    final ringPip = result[14];
    final pinkyTip = result[20];
    final pinkyPip = result[18];
    final wrist = result[0];

    final isIndexExtended = indexTip.y < indexPip.y;
    final isMiddleExtended = middleTip.y < middlePip.y;
    final isRingExtended = ringTip.y < ringPip.y;
    final isPinkyExtended = pinkyTip.y < pinkyPip.y;

    // D. Open Palm: All 4 fingers extended
    if (isIndexExtended && isMiddleExtended && isRingExtended && isPinkyExtended) {
      return GestureType.openPalm;
    }

    // E. Closed Fist: All 4 fingers curled closer to wrist
    final isIndexCurled = indexTip.distanceTo(wrist) < result[5].distanceTo(wrist);
    final isMiddleCurled = middleTip.distanceTo(wrist) < result[9].distanceTo(wrist);
    final isRingCurled = ringTip.distanceTo(wrist) < result[13].distanceTo(wrist);
    final isPinkyCurled = pinkyTip.distanceTo(wrist) < result[17].distanceTo(wrist);

    if (isIndexCurled && isMiddleCurled && isRingCurled && isPinkyCurled) {
      return GestureType.closedFist;
    }

    // F. Peace / V-Sign: Index and Middle extended, Ring and Pinky curled
    if (isIndexExtended && isMiddleExtended && !isRingExtended && !isPinkyExtended) {
      return GestureType.peaceSign;
    }

    // G. Pointing: Index extended, Middle, Ring, Pinky curled
    if (isIndexExtended && !isMiddleExtended && !isRingExtended && !isPinkyExtended) {
      return GestureType.pointing;
    }

    return GestureType.none;
  }

  GestureType _detectSwipe() {
    if (_trajectoryHistory.length < 4) return GestureType.none;

    final oldest = _trajectoryHistory.first;
    final newest = _trajectoryHistory.last;

    final double dx = newest['x'] - oldest['x'];
    final double dy = newest['y'] - oldest['y'];
    final Duration dt = (newest['time'] as DateTime).difference(oldest['time'] as DateTime);

    if (dt.inMilliseconds == 0) return GestureType.none;

    final double vx = dx / (dt.inMilliseconds / 1000.0);
    final double vy = dy / (dt.inMilliseconds / 1000.0);

    // Horizontal Swipe
    if (dx.abs() > tracker.swipeThreshold && dx.abs() > dy.abs() * 1.5) {
      _trajectoryHistory.clear();
      return vx > 0 ? GestureType.swipeRight : GestureType.swipeLeft;
    }

    // Vertical Swipe
    if (dy.abs() > tracker.swipeThreshold && dy.abs() > dx.abs() * 1.5) {
      _trajectoryHistory.clear();
      return vy > 0 ? GestureType.swipeDown : GestureType.swipeUp;
    }

    return GestureType.none;
  }

  GestureType get currentGesture => _currentGesture;
}
