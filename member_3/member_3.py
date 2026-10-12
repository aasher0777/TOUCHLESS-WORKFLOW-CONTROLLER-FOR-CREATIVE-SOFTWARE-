"""
gesture_classification.py
-------------------------
Contains the state-machine logic to calculate Euclidean distances between nodes
(such as the thumb tip and index tip) to classify gestures like "Pinch" or "Swipe".
"""

from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
import math
import time
from typing import Dict, List, Optional, Tuple
try:
    from member_2.member_2 import HandLandmarksResult, LandmarkInference
except ImportError:
    from member_2 import HandLandmarksResult, LandmarkInference


class GestureType(Enum):
    """Supported gesture classifications."""

    NONE = auto()
    PINCH = auto()
    SWIPE_LEFT = auto()
    SWIPE_RIGHT = auto()
    SWIPE_UP = auto()
    SWIPE_DOWN = auto()
    OPEN_PALM = auto()
    FIST = auto()
    POINTING = auto()
    PEACE = auto()


@dataclass
class GestureDefinition:
    """Formal definition and specification of a gesture mapped to 3D coordinates."""

    gesture_type: GestureType
    name: str
    icon: str
    key_nodes: List[int]
    node_names: List[str]
    description: str
    rule_summary: str
    mathematical_formula: str
    threshold_param: str
    actionable_state: str
    instructions: str


GESTURE_DICTIONARY: Dict[GestureType, GestureDefinition] = {
    GestureType.PINCH: GestureDefinition(
        gesture_type=GestureType.PINCH,
        name="Index Pinch",
        icon="🤏",
        key_nodes=[LandmarkInference.THUMB_TIP, LandmarkInference.INDEX_FINGER_TIP],
        node_names=["Node 4 (Thumb Tip)", "Node 8 (Index Tip)"],
        description="Continuous 3D Euclidean distance between thumb tip and index fingertip falls below the pinch threshold.",
        rule_summary="Normalized 3D/2D distance between Node 4 and Node 8 < pinch_threshold",
        mathematical_formula="d_3d(N_4, N_8) / scale < tau_pinch",
        threshold_param="pinch_threshold (default: 0.06)",
        actionable_state="Mouse Left Click / Drag & Drop / Select",
        instructions="Bring the tips of your thumb (Node 4) and index finger (Node 8) close together until they touch.",
    ),
    GestureType.POINTING: GestureDefinition(
        gesture_type=GestureType.POINTING,
        name="Pointing / Cursor Mode",
        icon="☝️",
        key_nodes=[
            LandmarkInference.INDEX_FINGER_TIP,
            LandmarkInference.INDEX_FINGER_PIP,
            LandmarkInference.MIDDLE_FINGER_TIP,
            LandmarkInference.RING_FINGER_TIP,
            LandmarkInference.PINKY_TIP,
        ],
        node_names=[
            "Node 8 (Index Tip)",
            "Node 6 (Index PIP)",
            "Node 12 (Middle Tip)",
            "Node 16 (Ring Tip)",
            "Node 20 (Pinky Tip)",
        ],
        description="Index finger extended while middle, ring, and pinky fingers are curled inward.",
        rule_summary="Node 8 extended past Node 6 relative to wrist; Nodes 12, 16, 20 curled below PIP joints",
        mathematical_formula="d(N_8, N_0) > d(N_6, N_0) and forall j in {12, 16, 20}: d(N_j, N_0) <= d(N_j-2, N_0)",
        threshold_param="PIP joint radial extension threshold",
        actionable_state="Cursor Navigation / Laser Pointer / Focus",
        instructions="Extend only your index finger while folding your middle, ring, and pinky fingers against your palm.",
    ),
    GestureType.PEACE: GestureDefinition(
        gesture_type=GestureType.PEACE,
        name="Peace / V-Sign",
        icon="✌️",
        key_nodes=[
            LandmarkInference.INDEX_FINGER_TIP,
            LandmarkInference.MIDDLE_FINGER_TIP,
            LandmarkInference.RING_FINGER_TIP,
            LandmarkInference.PINKY_TIP,
        ],
        node_names=[
            "Node 8 (Index Tip)",
            "Node 12 (Middle Tip)",
            "Node 16 (Ring Tip)",
            "Node 20 (Pinky Tip)",
        ],
        description="Index and middle fingers extended simultaneously in a V-shape; ring and pinky curled.",
        rule_summary="Nodes 8 and 12 extended past PIP joints; Nodes 16 and 20 curled",
        mathematical_formula="d(N_8, N_0) > d(N_6, N_0) and d(N_12, N_0) > d(N_10, N_0) and ring/pinky curled",
        threshold_param="Dual finger extension threshold",
        actionable_state="Context Switch / Mode Toggle / Shortcut Trigger",
        instructions="Raise your index and middle fingers in a 'V' peace sign, keeping ring and pinky fingers closed.",
    ),
    GestureType.OPEN_PALM: GestureDefinition(
        gesture_type=GestureType.OPEN_PALM,
        name="Open Palm / Hand Wave",
        icon="🖐️",
        key_nodes=[
            LandmarkInference.WRIST,
            LandmarkInference.THUMB_TIP,
            LandmarkInference.INDEX_FINGER_TIP,
            LandmarkInference.MIDDLE_FINGER_TIP,
            LandmarkInference.RING_FINGER_TIP,
            LandmarkInference.PINKY_TIP,
        ],
        node_names=[
            "Node 0 (Wrist)",
            "Node 4 (Thumb Tip)",
            "Node 8 (Index Tip)",
            "Node 12 (Middle Tip)",
            "Node 16 (Ring Tip)",
            "Node 20 (Pinky Tip)",
        ],
        description="All five digits extended outward away from the wrist coordinate (Node 0).",
        rule_summary="All 5 fingertips extended beyond their respective joint segments",
        mathematical_formula="count(extended_fingers) == 5",
        threshold_param="Full hand extension count = 5",
        actionable_state="Play / Pause Media / Start Slideshow",
        instructions="Open your hand fully flat facing the camera with all five fingers spread open.",
    ),
    GestureType.FIST: GestureDefinition(
        gesture_type=GestureType.FIST,
        name="Closed Fist",
        icon="✊",
        key_nodes=[
            LandmarkInference.WRIST,
            LandmarkInference.THUMB_TIP,
            LandmarkInference.INDEX_FINGER_TIP,
            LandmarkInference.MIDDLE_FINGER_TIP,
            LandmarkInference.RING_FINGER_TIP,
            LandmarkInference.PINKY_TIP,
        ],
        node_names=[
            "Node 0 (Wrist)",
            "Node 4 (Thumb Tip)",
            "Node 8 (Index Tip)",
            "Node 12 (Middle Tip)",
            "Node 16 (Ring Tip)",
            "Node 20 (Pinky Tip)",
        ],
        description="All fingers curled tightly toward the palm and wrist (Node 0).",
        rule_summary="Zero extended fingers; all fingertips curled below PIP joints",
        mathematical_formula="count(extended_fingers) == 0",
        threshold_param="Full hand extension count = 0",
        actionable_state="Close Tab / Stop Presentation / Escape",
        instructions="Clench your fingers into a ball or fist facing the camera.",
    ),
    GestureType.SWIPE_LEFT: GestureDefinition(
        gesture_type=GestureType.SWIPE_LEFT,
        name="Swipe Left",
        icon="👈",
        key_nodes=[LandmarkInference.MIDDLE_FINGER_MCP],
        node_names=["Node 9 (Middle MCP / Palm Center)"],
        description="Dynamic horizontal leftward displacement of palm center over a sliding time window.",
        rule_summary="Displacement Delta X < -swipe_threshold over swipe_window_seconds",
        mathematical_formula="Delta x = x_end - x_start < -tau_swipe and |Delta x| > |Delta y|",
        threshold_param="swipe_threshold (default: 0.12, window: 0.35s)",
        actionable_state="Previous Tab / Previous Track / Previous Slide",
        instructions="Quickly swipe your hand from right to left across the camera view.",
    ),
    GestureType.SWIPE_RIGHT: GestureDefinition(
        gesture_type=GestureType.SWIPE_RIGHT,
        name="Swipe Right",
        icon="👉",
        key_nodes=[LandmarkInference.MIDDLE_FINGER_MCP],
        node_names=["Node 9 (Middle MCP / Palm Center)"],
        description="Dynamic horizontal rightward displacement of palm center over a sliding time window.",
        rule_summary="Displacement Delta X > +swipe_threshold over swipe_window_seconds",
        mathematical_formula="Delta x = x_end - x_start > +tau_swipe and |Delta x| > |Delta y|",
        threshold_param="swipe_threshold (default: 0.12, window: 0.35s)",
        actionable_state="Next Tab / Next Track / Next Slide",
        instructions="Quickly swipe your hand from left to right across the camera view.",
    ),
    GestureType.SWIPE_UP: GestureDefinition(
        gesture_type=GestureType.SWIPE_UP,
        name="Swipe Up",
        icon="👆",
        key_nodes=[LandmarkInference.MIDDLE_FINGER_MCP],
        node_names=["Node 9 (Middle MCP / Palm Center)"],
        description="Dynamic vertical upward displacement of palm center over a sliding time window.",
        rule_summary="Displacement Delta Y < -swipe_threshold over swipe_window_seconds",
        mathematical_formula="Delta y = y_end - y_start < -tau_swipe and |Delta y| > |Delta x|",
        threshold_param="swipe_threshold (default: 0.12, window: 0.35s)",
        actionable_state="Volume Up / Page Up / Scroll Up",
        instructions="Flick your hand upwards briskly in front of the camera.",
    ),
    GestureType.SWIPE_DOWN: GestureDefinition(
        gesture_type=GestureType.SWIPE_DOWN,
        name="Swipe Down",
        icon="👇",
        key_nodes=[LandmarkInference.MIDDLE_FINGER_MCP],
        node_names=["Node 9 (Middle MCP / Palm Center)"],
        description="Dynamic vertical downward displacement of palm center over a sliding time window.",
        rule_summary="Displacement Delta Y > +swipe_threshold over swipe_window_seconds",
        mathematical_formula="Delta y = y_end - y_start > +tau_swipe and |Delta y| > |Delta x|",
        threshold_param="swipe_threshold (default: 0.12, window: 0.35s)",
        actionable_state="Volume Down / Page Down / Scroll Down",
        instructions="Flick your hand downwards briskly in front of the camera.",
    ),
}


class GestureClassifier:
    """Calculates Euclidean distances and runs a state-machine for robust gesture classification."""

    def __init__(
        self,
        pinch_threshold: float = 0.06,
        swipe_threshold: float = 0.12,
        swipe_window_seconds: float = 0.35,
        gesture_cooldown: float = 0.4,
    ) -> None:
        """
        Initialize the gesture classification state machine.

        :param pinch_threshold: Normalized Euclidean distance to trigger a pinch.
        :param swipe_threshold: Minimum displacement across time window to qualify as a swipe.
        :param swipe_window_seconds: Time window for tracking trajectory of swipes.
        :param gesture_cooldown: Seconds before a new discrete gesture can trigger again.
        """
        self.pinch_threshold = pinch_threshold
        self.swipe_threshold = swipe_threshold
        self.swipe_window_seconds = swipe_window_seconds
        self.gesture_cooldown = gesture_cooldown

        # State tracking
        self.is_pinching: bool = False
        self.last_gesture: GestureType = GestureType.NONE
        self.last_gesture_time: float = 0.0
        self.last_swipe_time: float = 0.0

        # Trajectory buffer for velocity and swipe calculations: deque of (timestamp, x, y)
        self.position_history: Deque[Tuple[float, float, float]] = deque()

    @staticmethod
    def euclidean_distance_3d(
        p1: Tuple[float, float, float], p2: Tuple[float, float, float]
    ) -> float:
        """Calculate Euclidean distance between two 3D spatial points using native C-accelerated math.dist."""
        return math.dist(p1, p2)

    @staticmethod
    def euclidean_distance_2d(
        p1: Tuple[float, ...], p2: Tuple[float, ...]
    ) -> float:
        """Calculate Euclidean distance between two 2D points using native C-accelerated math.dist."""
        return math.dist(p1[:2], p2[:2])

    def _get_hand_scale(self, norm_lm: List[Tuple[float, float, float]]) -> float:
        """Estimate hand scale from wrist (0) to middle finger MCP (9) to normalize distances."""
        wrist = norm_lm[LandmarkInference.WRIST]
        mcp = norm_lm[LandmarkInference.MIDDLE_FINGER_MCP]
        scale = self.euclidean_distance_2d(wrist, mcp)
        return max(scale, 0.001)

    def _detect_swipe(self, current_time: float) -> GestureType:
        """Analyze palm trajectory history to detect directional swipes."""
        if current_time - self.last_swipe_time < self.gesture_cooldown:
            return GestureType.NONE

        # Purge stale positions outside the time window
        while (
            self.position_history
            and current_time - self.position_history[0][0] > self.swipe_window_seconds
        ):
            self.position_history.popleft()

        if len(self.position_history) < 3:
            return GestureType.NONE

        start_time, start_x, start_y = self.position_history[0]
        end_time, end_x, end_y = self.position_history[-1]

        dx = end_x - start_x
        dy = end_y - start_y

        abs_dx = abs(dx)
        abs_dy = abs(dy)

        # Ensure displacement exceeds swipe threshold
        if abs_dx < self.swipe_threshold and abs_dy < self.swipe_threshold:
            return GestureType.NONE

        swipe_result = GestureType.NONE
        if abs_dx > abs_dy:
            # Horizontal motion
            if dx > self.swipe_threshold:
                swipe_result = GestureType.SWIPE_RIGHT
            elif dx < -self.swipe_threshold:
                swipe_result = GestureType.SWIPE_LEFT
        else:
            # Vertical motion (Note: y is 0 at top, 1 at bottom)
            if dy > self.swipe_threshold:
                swipe_result = GestureType.SWIPE_DOWN
            elif dy < -self.swipe_threshold:
                swipe_result = GestureType.SWIPE_UP

        if swipe_result != GestureType.NONE:
            self.last_swipe_time = current_time

        return swipe_result

    def _are_fingers_extended(
        self, norm_lm: List[Tuple[float, float, float]]
    ) -> Dict[str, bool]:
        """Determine whether individual fingers are curled or extended using 3D joint kinematics."""
        wrist = norm_lm[LandmarkInference.WRIST]
        scale = self._get_hand_scale(norm_lm)

        extended = {}
        finger_indices = {
            "index": (
                LandmarkInference.INDEX_FINGER_TIP,
                LandmarkInference.INDEX_FINGER_DIP,
                LandmarkInference.INDEX_FINGER_PIP,
                LandmarkInference.INDEX_FINGER_MCP,
            ),
            "middle": (
                LandmarkInference.MIDDLE_FINGER_TIP,
                LandmarkInference.MIDDLE_FINGER_DIP,
                LandmarkInference.MIDDLE_FINGER_PIP,
                LandmarkInference.MIDDLE_FINGER_MCP,
            ),
            "ring": (
                LandmarkInference.RING_FINGER_TIP,
                LandmarkInference.RING_FINGER_DIP,
                LandmarkInference.RING_FINGER_PIP,
                LandmarkInference.RING_FINGER_MCP,
            ),
            "pinky": (
                LandmarkInference.PINKY_TIP,
                LandmarkInference.PINKY_DIP,
                LandmarkInference.PINKY_PIP,
                LandmarkInference.PINKY_MCP,
            ),
        }

        for finger, (tip_idx, dip_idx, pip_idx, mcp_idx) in finger_indices.items():
            tip_pt = norm_lm[tip_idx]
            dip_pt = norm_lm[dip_idx]
            pip_pt = norm_lm[pip_idx]
            mcp_pt = norm_lm[mcp_idx]

            tip_wrist = self.euclidean_distance_3d(wrist, tip_pt)
            dip_wrist = self.euclidean_distance_3d(wrist, dip_pt)
            pip_wrist = self.euclidean_distance_3d(wrist, pip_pt)

            tip_mcp = self.euclidean_distance_3d(mcp_pt, tip_pt)
            pip_mcp = self.euclidean_distance_3d(mcp_pt, pip_pt)

            # Finger is extended if fingertip projects outward beyond PIP from wrist and MCP base
            # When curled into a fist, tip folds inwards toward MCP/wrist (tip_mcp <= pip_mcp * 1.25)
            is_ext = (tip_wrist > pip_wrist) and (tip_mcp > pip_mcp * 1.25) and (tip_wrist > dip_wrist * 0.95)
            extended[finger] = bool(is_ext)

        # Thumb extension relative to pinky MCP and index MCP
        thumb_tip = norm_lm[LandmarkInference.THUMB_TIP]
        thumb_ip = norm_lm[LandmarkInference.THUMB_IP]
        pinky_mcp = norm_lm[LandmarkInference.PINKY_MCP]
        index_mcp = norm_lm[LandmarkInference.INDEX_FINGER_MCP]

        d_tip_pinky = self.euclidean_distance_3d(thumb_tip, pinky_mcp)
        d_ip_pinky = self.euclidean_distance_3d(thumb_ip, pinky_mcp)
        d_tip_index = self.euclidean_distance_3d(thumb_tip, index_mcp)

        extended["thumb"] = bool(d_tip_pinky > d_ip_pinky and d_tip_index > 0.35 * scale)

        return extended

    def continuous_node_distance(
        self,
        norm_lm: List[Tuple[float, float, float]],
        node_a: int,
        node_b: int,
        use_3d: bool = True,
    ) -> float:
        """
        Calculate continuous Euclidean distance between two specific coordinate nodes.

        :param norm_lm: 21 normalized hand landmark coordinates.
        :param node_a: First landmark node index (e.g. Node 4 - Thumb Tip).
        :param node_b: Second landmark node index (e.g. Node 8 - Index Tip).
        :param use_3d: If True, computes 3D Euclidean distance (x, y, z); else 2D (x, y).
        :return: Continuous Euclidean distance float.
        """
        if node_a >= len(norm_lm) or node_b >= len(norm_lm):
            return 0.0
        p1 = norm_lm[node_a]
        p2 = norm_lm[node_b]
        if use_3d and len(p1) >= 3 and len(p2) >= 3:
            return self.euclidean_distance_3d(p1, p2)
        return self.euclidean_distance_2d(p1, p2)

    def calculate_key_distances(
        self, norm_lm: List[Tuple[float, float, float]], scale: float = 1.0
    ) -> Dict[str, float]:
        """
        Continuously compute 3D & normalized Euclidean distances across key coordinate node pairs.

        :param norm_lm: 21 normalized landmarks.
        :param scale: Hand scale factor for normalization.
        :return: Dictionary mapping node-pair descriptors to normalized distances.
        """
        safe_scale = max(scale, 0.001)
        pairs = {
            "dist_4_8_thumb_index": (LandmarkInference.THUMB_TIP, LandmarkInference.INDEX_FINGER_TIP),
            "dist_4_12_thumb_middle": (LandmarkInference.THUMB_TIP, LandmarkInference.MIDDLE_FINGER_TIP),
            "dist_8_0_index_wrist": (LandmarkInference.INDEX_FINGER_TIP, LandmarkInference.WRIST),
            "dist_12_0_middle_wrist": (LandmarkInference.MIDDLE_FINGER_TIP, LandmarkInference.WRIST),
            "dist_16_0_ring_wrist": (LandmarkInference.RING_FINGER_TIP, LandmarkInference.WRIST),
            "dist_20_0_pinky_wrist": (LandmarkInference.PINKY_TIP, LandmarkInference.WRIST),
            "dist_4_20_thumb_pinky": (LandmarkInference.THUMB_TIP, LandmarkInference.PINKY_MCP),
        }
        distances = {}
        for key, (na, nb) in pairs.items():
            d3 = self.continuous_node_distance(norm_lm, na, nb, use_3d=True)
            distances[key] = d3 / safe_scale
            distances[f"{key}_raw"] = d3
        return distances

    def classify(
        self, hand_result: Optional[HandLandmarksResult]
    ) -> Tuple[GestureType, Dict[str, Any]]:
        """
        Classify gestures using spatial landmark nodes and state-machine tracking.

        :param hand_result: HandLandmarksResult from inference model.
        :return: Tuple of (GestureType, metrics_dict).
        """
        current_time = time.time()
        metrics: Dict[str, Any] = {
            "pinch_distance": 0.0,
            "pinch_distance_3d": 0.0,
            "normalized_pinch_distance": 0.0,
            "normalized_pinch_distance_3d": 0.0,
            "hand_scale": 1.0,
            "is_pinching": 0.0,
            "key_distances": {},
            "extended_fingers": {},
        }

        if hand_result is None or not hand_result.normalized_landmarks:
            self.position_history.clear()
            self.is_pinching = False
            return GestureType.NONE, metrics

        norm_lm = hand_result.normalized_landmarks
        scale = self._get_hand_scale(norm_lm)
        metrics["hand_scale"] = scale

        # Continuous Euclidean distance calculations between Node 4 (Thumb Tip) and Node 8 (Index Tip)
        thumb_tip = norm_lm[LandmarkInference.THUMB_TIP]
        index_tip = norm_lm[LandmarkInference.INDEX_FINGER_TIP]
        pinch_dist_2d = self.euclidean_distance_2d(thumb_tip, index_tip)
        pinch_dist_3d = self.euclidean_distance_3d(thumb_tip, index_tip)
        norm_pinch_dist = pinch_dist_2d / scale
        norm_pinch_dist_3d = pinch_dist_3d / scale

        # Populate continuous node distance metrics
        metrics["pinch_distance"] = pinch_dist_2d
        metrics["pinch_distance_3d"] = pinch_dist_3d
        metrics["normalized_pinch_distance"] = norm_pinch_dist
        metrics["normalized_pinch_distance_3d"] = norm_pinch_dist_3d
        metrics["key_distances"] = self.calculate_key_distances(norm_lm, scale)

        # Palm center approximation (MCP of middle finger) for swipe detection
        palm_center = norm_lm[LandmarkInference.MIDDLE_FINGER_MCP]
        self.position_history.append((current_time, palm_center[0], palm_center[1]))

        # Check static posture states via finger extension
        extended = self._are_fingers_extended(norm_lm)
        metrics["extended_fingers"] = extended

        idx_ext = extended["index"]
        mid_ext = extended["middle"]
        rng_ext = extended["ring"]
        pnk_ext = extended["pinky"]

        # 1. FIST: All 4 non-thumb fingers are curled tightly inward into the palm
        # A fist is a closed hand. It must NEVER be mistaken for a pinch even if thumb touches fingers.
        if not idx_ext and not mid_ext and not rng_ext and not pnk_ext:
            self.is_pinching = False
            metrics["is_pinching"] = 0.0
            self.last_gesture = GestureType.FIST
            self.last_gesture_time = current_time
            return GestureType.FIST, metrics

        # 2. State machine and threshold evaluation for PINCH
        pinch_enter_threshold = self.pinch_threshold
        pinch_exit_threshold = self.pinch_threshold * 1.35

        is_pinch_active = False
        if self.is_pinching:
            # Retain pinch state until distance exceeds hysteresis exit threshold
            if norm_pinch_dist < pinch_exit_threshold:
                is_pinch_active = True
            else:
                self.is_pinching = False
        else:
            if norm_pinch_dist < pinch_enter_threshold:
                self.is_pinching = True
                is_pinch_active = True

        metrics["is_pinching"] = 1.0 if is_pinch_active else 0.0

        # Middle Click: Thumb-to-Middle (Node 4 to Node 12) pinch or middle click while pointing
        dist_thumb_middle = self.continuous_node_distance(norm_lm, 4, 12, use_3d=True) / max(scale, 0.001)
        is_middle_click = bool(dist_thumb_middle < self.pinch_threshold * 1.35 and (idx_ext or mid_ext))
        metrics["is_middle_click"] = 1.0 if is_middle_click else 0.0
        metrics["dist_thumb_middle"] = dist_thumb_middle

        # Double Pointing: Index & Middle fingers both extended, Ring & Pinky curled inward (mutually exclusive with middle click & pinch)
        is_double_pointing = bool(idx_ext and mid_ext and not rng_ext and not pnk_ext and not is_middle_click and not is_pinch_active)
        metrics["is_double_pointing"] = 1.0 if is_double_pointing else 0.0

        if is_pinch_active:
            self.last_gesture = GestureType.PINCH
            self.last_gesture_time = current_time
            return GestureType.PINCH, metrics

        # 3. Dynamic Swipe motion (evaluated when hand is moving rapidly)
        swipe = self._detect_swipe(current_time)
        if swipe != GestureType.NONE:
            self.last_gesture = swipe
            self.last_gesture_time = current_time
            self.position_history.clear()
            return swipe, metrics

        # 4. POINTING: Index finger extended, middle/ring/pinky curled, not pinching
        if idx_ext and not mid_ext and not rng_ext and not pnk_ext:
            self.last_gesture = GestureType.POINTING
            self.last_gesture_time = current_time
            return GestureType.POINTING, metrics

        # 5. PEACE: Index and Middle extended, Ring and Pinky curled
        elif idx_ext and mid_ext and not rng_ext and not pnk_ext:
            self.last_gesture = GestureType.PEACE
            self.last_gesture_time = current_time
            return GestureType.PEACE, metrics

        # 6. OPEN PALM: All 4 non-thumb fingers extended
        elif idx_ext and mid_ext and rng_ext and pnk_ext:
            self.last_gesture = GestureType.OPEN_PALM
            self.last_gesture_time = current_time
            return GestureType.OPEN_PALM, metrics

        self.last_gesture = GestureType.NONE
        return GestureType.NONE, metrics

    def load_dl_model(
        self,
        model_path: str = "models/gesture_mlp_archive5.pth",
        meta_path: str = "models/classes_archive5.json",
    ) -> bool:
        """
        Load trained PyTorch deep learning model for neural inference.

        :param model_path: Path to .pth model checkpoint.
        :param meta_path: Path to class metadata JSON.
        :return: True if loaded successfully, False otherwise.
        """
        import json
        import os
        import torch

        if not os.path.exists(model_path) or not os.path.exists(meta_path):
            return False

        try:
            try:
                from member_2.model import GestureLandmarkMLP
            except ImportError:
                from model import GestureLandmarkMLP

            with open(meta_path, "r") as f:
                meta = json.load(f)

            self.dl_classes = meta["classes"]
            self.dl_input_dim = meta["input_dim"]
            self.dl_model = GestureLandmarkMLP(
                input_dim=self.dl_input_dim,
                num_classes=meta["num_classes"],
                hidden_dims=[128, 64, 32],
            )
            self.dl_model.load_state_dict(torch.load(model_path, map_location="cpu"))
            self.dl_model.eval()
            return True
        except Exception:
            return False

    def predict_dl(
        self, norm_lm: List[Tuple[float, float, float]]
    ) -> Optional[Tuple[str, float]]:
        """
        Predict gesture class using the loaded deep learning neural network.

        :param norm_lm: 21 normalized landmarks.
        :return: Tuple of (predicted_class_name, confidence_probability) or None.
        """
        if not hasattr(self, "dl_model") or self.dl_model is None:
            return None

        import numpy as np
        import torch

        try:
            # Flatten 2D or 3D landmarks to match model input dimension
            if self.dl_input_dim == 42:
                features = [coord for pt in norm_lm for coord in (pt[0], pt[1])]
            else:
                features = [coord for pt in norm_lm for coord in (pt[0], pt[1], pt[2])]

            x_tensor = torch.tensor([features], dtype=torch.float32)
            with torch.no_grad():
                logits = self.dl_model(x_tensor)
                probs = torch.softmax(logits, dim=1)[0]
                conf, pred_idx = torch.max(probs, dim=0)

            cls_name = self.dl_classes[pred_idx.item()]
            return cls_name, conf.item()
        except Exception:
            return None

