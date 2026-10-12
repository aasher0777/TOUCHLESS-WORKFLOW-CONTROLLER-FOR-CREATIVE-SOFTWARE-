/// gesture_dictionary.dart
/// Cross-platform gesture dictionary mapping 3D joint nodes to actionable states,
/// Euclidean formulas, and context-routed keyboard/macro events.

enum GestureType {
  none,
  pinch,
  pointing,
  peaceSign,
  openPalm,
  closedFist,
  swipeLeft,
  swipeRight,
  swipeUp,
  swipeDown,
}

class GestureDefinition {
  final GestureType type;
  final String displayName;
  final String defaultAction;
  final String premiereAction;
  final String figmaAction;
  final List<int> trackedNodes;
  final String formulaDescription;
  final String howToPerform;
  final double defaultThreshold;

  const GestureDefinition({
    required this.type,
    required this.displayName,
    required this.defaultAction,
    required this.premiereAction,
    required this.figmaAction,
    required this.trackedNodes,
    required this.formulaDescription,
    required this.howToPerform,
    required this.defaultThreshold,
  });

  String getActionForContext(String context) {
    switch (context.toLowerCase()) {
      case "premiere":
      case "adobe premiere pro":
        return premiereAction;
      case "figma":
        return figmaAction;
      default:
        return defaultAction;
    }
  }
}

class GestureDictionary {
  static const Map<GestureType, GestureDefinition> catalog = {
    GestureType.pinch: GestureDefinition(
      type: GestureType.pinch,
      displayName: "Index Pinch",
      defaultAction: "Mouse Left Click / Drag & Drop",
      premiereAction: "Blade Cut Tool (C)",
      figmaAction: "Select / Pointer Tool (V)",
      trackedNodes: [4, 8],
      formulaDescription: "d_3D(N_4, N_8) / scale < tau_pinch [Normalized Euclidean Distance]",
      howToPerform: "Bring tips of Thumb (Node 4) and Index Finger (Node 8) together until they touch.",
      defaultThreshold: 0.060,
    ),
    GestureType.pointing: GestureDefinition(
      type: GestureType.pointing,
      displayName: "Pointing / Cursor Mode",
      defaultAction: "Cursor Navigation / Laser Pointer",
      premiereAction: "Timeline Scrubber Navigation",
      figmaAction: "Canvas Pan Navigation",
      trackedNodes: [8, 6, 5],
      formulaDescription: "y(N_8) < y(N_6) AND y(N_tip) > y(N_pip) for fingers 12, 16, 20",
      howToPerform: "Extend only the Index Finger (Node 8) straight while curling other fingers.",
      defaultThreshold: 0.080,
    ),
    GestureType.peaceSign: GestureDefinition(
      type: GestureType.peaceSign,
      displayName: "Peace / V-Sign",
      defaultAction: "Context Switch / Mode Toggle",
      premiereAction: "Ripple Delete (Shift + Delete)",
      figmaAction: "Hand Pan Tool (H)",
      trackedNodes: [8, 12, 4],
      formulaDescription: "Extended(N_8, N_12) AND Curled(N_16, N_20) AND d(N_8, N_12) > tau_v",
      howToPerform: "Extend both Index and Middle fingers in a clear 'V' shape.",
      defaultThreshold: 0.075,
    ),
    GestureType.openPalm: GestureDefinition(
      type: GestureType.openPalm,
      displayName: "Open Palm / Hand Wave",
      defaultAction: "Play / Pause Media / Start Slideshow",
      premiereAction: "Play / Stop Timeline (Space)",
      figmaAction: "Toggle UI Visibility (Ctrl + \\)",
      trackedNodes: [4, 8, 12, 16, 20],
      formulaDescription: "ALL fingers extended: y(N_tip) < y(N_pip) AND spread > tau_spread",
      howToPerform: "Open all 5 fingers fully and present your palm toward the camera.",
      defaultThreshold: 0.250,
    ),
    GestureType.closedFist: GestureDefinition(
      type: GestureType.closedFist,
      displayName: "Closed Fist",
      defaultAction: "Close Tab / Stop Presentation / Escape",
      premiereAction: "Deselect All Clips (Ctrl + Shift + A)",
      figmaAction: "Zoom to 100% (Shift + 0)",
      trackedNodes: [4, 8, 12, 16, 20],
      formulaDescription: "ALL fingers curled: d(N_tip, N_wrist) < d(N_mcp, N_wrist)",
      howToPerform: "Curl all 5 fingers into a tight fist facing the camera sensor.",
      defaultThreshold: 0.180,
    ),
    GestureType.swipeLeft: GestureDefinition(
      type: GestureType.swipeLeft,
      displayName: "Swipe Left",
      defaultAction: "Previous Tab / Previous Track (Ctrl + Shift + Tab)",
      premiereAction: "Step 5 Frames Backward (Shift + Left)",
      figmaAction: "Previous Frame / Artboard",
      trackedNodes: [0, 9, 8],
      formulaDescription: "dx/dt < -tau_swipe AND abs(dy) < delta_y [Horizontal Trajectory]",
      howToPerform: "Flick hand swiftly from right to left across camera frame.",
      defaultThreshold: 0.120,
    ),
    GestureType.swipeRight: GestureDefinition(
      type: GestureType.swipeRight,
      displayName: "Swipe Right",
      defaultAction: "Next Tab / Next Track (Ctrl + Tab)",
      premiereAction: "Step 5 Frames Forward (Shift + Right)",
      figmaAction: "Next Frame / Artboard",
      trackedNodes: [0, 9, 8],
      formulaDescription: "dx/dt > +tau_swipe AND abs(dy) < delta_y [Horizontal Trajectory]",
      howToPerform: "Flick hand swiftly from left to right across camera frame.",
      defaultThreshold: 0.120,
    ),
    GestureType.swipeUp: GestureDefinition(
      type: GestureType.swipeUp,
      displayName: "Swipe Up",
      defaultAction: "Volume Up / Page Up / Scroll Up",
      premiereAction: "Zoom In Timeline (+)",
      figmaAction: "Zoom In Canvas (Ctrl + +)",
      trackedNodes: [0, 9, 8],
      formulaDescription: "dy/dt < -tau_vertical AND abs(dx) < delta_x",
      howToPerform: "Flick hand swiftly upward.",
      defaultThreshold: 0.120,
    ),
    GestureType.swipeDown: GestureDefinition(
      type: GestureType.swipeDown,
      displayName: "Swipe Down",
      defaultAction: "Volume Down / Page Down / Scroll Down",
      premiereAction: "Zoom Out Timeline (-)",
      figmaAction: "Zoom Out Canvas (Ctrl + -)",
      trackedNodes: [0, 9, 8],
      formulaDescription: "dy/dt > +tau_vertical AND abs(dx) < delta_x",
      howToPerform: "Flick hand swiftly downward.",
      defaultThreshold: 0.120,
    ),
  };

  static GestureDefinition get(GestureType type) {
    return catalog[type] ?? catalog[GestureType.pinch]!;
  }
}
