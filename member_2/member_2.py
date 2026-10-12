"""
landmark_inference.py
---------------------
Houses the MediaPipe implementation, running the fast palm detector and the
precise coordinate model to extract the 21 3D spatial key points.
"""

from dataclasses import dataclass
import logging
from typing import List, Optional, Tuple
import cv2
import numpy as np

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    mp = None
    MEDIAPIPE_AVAILABLE = False



@dataclass
class HandLandmarksResult:
    """Encapsulates detected hand landmark coordinates and Stage 1 bounding box."""

    # 21 landmarks normalized between [0.0, 1.0] (x, y, z)
    normalized_landmarks: List[Tuple[float, float, float]]
    # 21 landmarks mapped to pixel coordinates (x_px, y_px, z_relative)
    pixel_landmarks: List[Tuple[int, int, float]]
    # Stage 1 established hand bounding box in pixel coordinates (x_min, y_min, x_max, y_max)
    bounding_box: Tuple[int, int, int, int] = (0, 0, 0, 0)
    # Stage 1 normalized bounding box (xmin, ymin, xmax, ymax) in [0.0, 1.0]
    normalized_bounding_box: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    # 21 3D spatial coordinates in world meters if available
    world_landmarks: Optional[List[Tuple[float, float, float]]] = None
    # Handedness label: 'Left' or 'Right'
    handedness: str = "Unknown"
    # Stage 1 palm / hand presence confidence score
    confidence: float = 1.0


class LandmarkInference:
    """Manages the MediaPipe Hands palm detection and 21 3D landmark coordinate model."""

    # Landmark index mappings for convenient lookup
    WRIST = 0
    THUMB_CMC = 1
    THUMB_MCP = 2
    THUMB_IP = 3
    THUMB_TIP = 4
    INDEX_FINGER_MCP = 5
    INDEX_FINGER_PIP = 6
    INDEX_FINGER_DIP = 7
    INDEX_FINGER_TIP = 8
    MIDDLE_FINGER_MCP = 9
    MIDDLE_FINGER_PIP = 10
    MIDDLE_FINGER_DIP = 11
    MIDDLE_FINGER_TIP = 12
    RING_FINGER_MCP = 13
    RING_FINGER_PIP = 14
    RING_FINGER_DIP = 15
    RING_FINGER_TIP = 16
    PINKY_MCP = 17
    PINKY_PIP = 18
    PINKY_DIP = 19
    PINKY_TIP = 20

    def __init__(
        self,
        static_image_mode: bool = False,
        max_num_hands: int = 1,
        model_complexity: int = 1,
        min_detection_confidence: float = 0.7,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        """
        Initialize the MediaPipe Hands model.

        :param static_image_mode: Whether to treat frames as isolated images.
        :param max_num_hands: Maximum number of hands to detect.
        :param model_complexity: Landmark model complexity (0 or 1).
        :param min_detection_confidence: Minimum palm detection confidence [0.0, 1.0].
        :param min_tracking_confidence: Minimum landmark tracking confidence [0.0, 1.0].
        """
        if not MEDIAPIPE_AVAILABLE:
            logging.warning(
                "[LandmarkInference] MediaPipe is not installed in the active environment. "
                "Install with 'pip install mediapipe' to enable live palm detection."
            )
            self.hands = None
            self.mp_hands = None
            self.detector = None
            return

        self.use_tasks_api = False
        self.detector = None
        self.hands = None
        self.mp_hands = None

        # Check for legacy mp.solutions API
        if hasattr(mp, "solutions") and hasattr(mp.solutions, "hands"):
            self.mp_hands = mp.solutions.hands
            self.mp_drawing = mp.solutions.drawing_utils
            self.hands = self.mp_hands.Hands(
                static_image_mode=static_image_mode,
                max_num_hands=max_num_hands,
                model_complexity=model_complexity,
                min_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence,
            )
        else:
            # Modern MediaPipe Tasks API (>= 0.10.30, Python 3.12/3.13/3.14+)
            try:
                import os
                import urllib.request
                from mediapipe.tasks import python as mp_python
                from mediapipe.tasks.python import vision

                model_path = os.path.join(os.path.dirname(__file__), "models", "hand_landmarker.task")
                if not os.path.exists(model_path):
                    os.makedirs(os.path.dirname(model_path), exist_ok=True)
                    url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
                    urllib.request.urlretrieve(url, model_path)

                base_opts = mp_python.BaseOptions(model_asset_path=model_path)
                options = vision.HandLandmarkerOptions(
                    base_options=base_opts,
                    num_hands=max_num_hands,
                    min_hand_detection_confidence=min_detection_confidence,
                    min_hand_presence_confidence=min_tracking_confidence,
                    min_tracking_confidence=min_tracking_confidence,
                    running_mode=vision.RunningMode.IMAGE,
                )
                self.detector = vision.HandLandmarker.create_from_options(options)
                self.use_tasks_api = True
            except Exception as e:
                logging.error(f"[LandmarkInference] Error initializing MediaPipe Tasks: {e}")
                self.detector = None

    HAND_CONNECTIONS = [
        (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
        (0, 5), (5, 6), (6, 7), (7, 8),        # Index
        (5, 9), (9, 10), (10, 11), (11, 12),   # Middle
        (9, 13), (13, 14), (14, 15), (15, 16), # Ring
        (13, 17), (17, 18), (18, 19), (19, 20), (0, 17) # Pinky & Base
    ]

    @staticmethod
    def calculate_bounding_box(
        pixel_pts: List[Tuple[int, int, float]],
        frame_w: int,
        frame_h: int,
        padding: int = 15,
    ) -> Tuple[int, int, int, int]:
        """
        Calculate the spatial bounding box enclosing the hand keypoints.

        :param pixel_pts: List of (x, y, z) pixel landmarks.
        :param frame_w: Image width.
        :param frame_h: Image height.
        :param padding: Pixel margin to expand the bounding box.
        :return: (x_min, y_min, x_max, y_max).
        """
        if not pixel_pts:
            return 0, 0, 0, 0
        xs = [pt[0] for pt in pixel_pts]
        ys = [pt[1] for pt in pixel_pts]
        x_min = max(0, min(xs) - padding)
        y_min = max(0, min(ys) - padding)
        x_max = min(frame_w, max(xs) + padding)
        y_max = min(frame_h, max(ys) + padding)
        return x_min, y_min, x_max, y_max

    def process(self, frame_rgb: np.ndarray) -> List[HandLandmarksResult]:
        """
        Perform 3D hand landmark inference on an RGB frame.

        Stage 1: Palm detection to establish the hand bounding box, suppressing background and faces.
        Stage 2: 21 3D spatial key point and fingertip coordinate estimation.

        :param frame_rgb: Image frame in RGB format.
        :return: List of HandLandmarksResult instances for each detected hand.
        """
        detected_hands: List[HandLandmarksResult] = []
        h, w, _ = frame_rgb.shape

        if getattr(self, "use_tasks_api", False) and self.detector is not None:
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            res = self.detector.detect(mp_image)
            if not res.hand_landmarks:
                return detected_hands

            handedness_list = []
            confidence_list = []
            if res.handedness:
                for handedness_entry in res.handedness:
                    handedness_list.append(handedness_entry[0].category_name)
                    confidence_list.append(getattr(handedness_entry[0], "score", 1.0))

            for i, hand_lms in enumerate(res.hand_landmarks):
                norm_pts: List[Tuple[float, float, float]] = []
                pixel_pts: List[Tuple[int, int, float]] = []

                for lm in hand_lms:
                    norm_pts.append((lm.x, lm.y, lm.z))
                    px_x = int(lm.x * w)
                    px_y = int(lm.y * h)
                    pixel_pts.append((px_x, px_y, lm.z))

                hand_label = handedness_list[i] if i < len(handedness_list) else "Unknown"
                conf = confidence_list[i] if i < len(confidence_list) else 1.0
                bbox = self.calculate_bounding_box(pixel_pts, w, h)
                norm_bbox = (
                    bbox[0] / max(w, 1),
                    bbox[1] / max(h, 1),
                    bbox[2] / max(w, 1),
                    bbox[3] / max(h, 1),
                )

                detected_hands.append(
                    HandLandmarksResult(
                        normalized_landmarks=norm_pts,
                        pixel_landmarks=pixel_pts,
                        bounding_box=bbox,
                        normalized_bounding_box=norm_bbox,
                        world_landmarks=None,
                        handedness=hand_label,
                        confidence=conf,
                    )
                )
            return detected_hands

        if self.hands is None:
            return []

        results = self.hands.process(frame_rgb)
        if not results.multi_hand_landmarks:
            return detected_hands

        # Extract handedness if available
        handedness_list = []
        confidence_list = []
        if results.multi_handedness:
            for hand_class in results.multi_handedness:
                handedness_list.append(hand_class.classification[0].label)
                confidence_list.append(hand_class.classification[0].score)

        for i, hand_landmarks in enumerate(results.multi_hand_landmarks):
            norm_pts: List[Tuple[float, float, float]] = []
            pixel_pts: List[Tuple[int, int, float]] = []

            for lm in hand_landmarks.landmark:
                norm_pts.append((lm.x, lm.y, lm.z))
                px_x = int(lm.x * w)
                px_y = int(lm.y * h)
                pixel_pts.append((px_x, px_y, lm.z))

            world_pts = None
            if results.multi_hand_world_landmarks and i < len(
                results.multi_hand_world_landmarks
            ):
                world_hand = results.multi_hand_world_landmarks[i]
                world_pts = [(w_lm.x, w_lm.y, w_lm.z) for w_lm in world_hand.landmark]

            hand_label = handedness_list[i] if i < len(handedness_list) else "Unknown"
            conf = confidence_list[i] if i < len(confidence_list) else 1.0
            bbox = self.calculate_bounding_box(pixel_pts, w, h)
            norm_bbox = (
                bbox[0] / max(w, 1),
                bbox[1] / max(h, 1),
                bbox[2] / max(w, 1),
                bbox[3] / max(h, 1),
            )

            detected_hands.append(
                HandLandmarksResult(
                    normalized_landmarks=norm_pts,
                    pixel_landmarks=pixel_pts,
                    bounding_box=bbox,
                    normalized_bounding_box=norm_bbox,
                    world_landmarks=world_pts,
                    handedness=hand_label,
                    confidence=conf,
                )
            )

        return detected_hands

    def draw_landmarks(
        self,
        frame_bgr: np.ndarray,
        detected_hands: List[HandLandmarksResult],
        draw_bounding_box: bool = True,
    ) -> np.ndarray:
        """
        Overlay detected 21 spatial key points, skeleton lines, and Stage 1 bounding box.

        :param frame_bgr: Frame in BGR format to draw onto.
        :param detected_hands: Inference results to visualize.
        :param draw_bounding_box: If True, renders Stage 1 hand bounding box with handedness tag.
        :return: Annotated frame.
        """
        connections = self.HAND_CONNECTIONS

        for hand in detected_hands:
            pts = hand.pixel_landmarks

            # Draw Stage 1 Hand Bounding Box
            if draw_bounding_box and hand.bounding_box != (0, 0, 0, 0):
                x_min, y_min, x_max, y_max = hand.bounding_box
                # Bounding box rectangle in cyan/mint green
                cv2.rectangle(frame_bgr, (x_min, y_min), (x_max, y_max), (220, 200, 50), 1)

                # Handedness badge label
                conf_pct = int(hand.confidence * 100)
                badge_text = f"{hand.handedness} [{conf_pct}%]"
                cv2.rectangle(
                    frame_bgr,
                    (x_min, max(0, y_min - 20)),
                    (x_min + len(badge_text) * 9, y_min),
                    (220, 200, 50),
                    -1,
                )
                cv2.putText(
                    frame_bgr,
                    badge_text,
                    (x_min + 2, y_min - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (20, 20, 20),
                    1,
                    cv2.LINE_AA,
                )

            # Draw skeleton connection lines
            for conn in connections:
                start_idx, end_idx = conn
                if start_idx < len(pts) and end_idx < len(pts):
                    p1 = (pts[start_idx][0], pts[start_idx][1])
                    p2 = (pts[end_idx][0], pts[end_idx][1])
                    cv2.line(frame_bgr, p1, p2, (0, 255, 128), 2)

            # Draw 21 keypoint joints
            for idx, pt in enumerate(pts):
                # Highlight thumb and index tips in distinct color
                color = (0, 0, 255) if idx in (self.THUMB_TIP, self.INDEX_FINGER_TIP) else (255, 200, 0)
                cv2.circle(frame_bgr, (pt[0], pt[1]), 5, color, -1)
                cv2.circle(frame_bgr, (pt[0], pt[1]), 6, (255, 255, 255), 1)

        return frame_bgr

    def close(self) -> None:
        """Release MediaPipe resources."""
        if self.hands is not None:
            try:
                self.hands.close()
            except Exception:
                pass
            self.hands = None
        if hasattr(self, "detector") and self.detector is not None:
            try:
                self.detector.close()
            except Exception:
                pass
            self.detector = None


    def __enter__(self) -> "LandmarkInference":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
