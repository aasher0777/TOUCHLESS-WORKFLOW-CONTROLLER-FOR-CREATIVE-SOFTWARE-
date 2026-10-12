"""
utils.py
--------
Touchless Workflow Controller Utilities:
1. EMAFilter: Exponential Moving Average filter for 2D cursor coordinate stabilization.
2. GestureDebouncer: Per-gesture debouncing and cooldown management (0.5s limit).
3. CalibrationDashboard: Non-blocking Tkinter slider panel running in a separate daemon thread.
4. draw_hud: Heads-up display visual overlay on the live video stream.
"""

from typing import Dict, List, Optional, Tuple
import threading
import time
import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk


class LightingNormalizer:
    """
    Dynamic CLAHE (Contrast Limited Adaptive Histogram Equalization) preprocessor.
    Normalizes uneven ambient lighting, eliminates monitor glare, and extracts
    hand features from deep silhouettes / backlighting in real time (<2ms overhead).
    Operates strictly on the Luminance (L) channel in LAB color space to preserve
    natural skin tone chromaticity (A & B channels).
    """

    def __init__(
        self, clip_limit: float = 2.2, tile_grid_size: Tuple[int, int] = (8, 8)
    ) -> None:
        """
        Initialize CLAHE equalizer.

        :param clip_limit: Threshold for contrast limiting (prevents noise amplification).
        :param tile_grid_size: Size of grid for local histogram equalization (default: 8x8).
        """
        self.clip_limit: float = float(clip_limit)
        self.tile_grid_size: Tuple[int, int] = tile_grid_size
        self.clahe = cv2.createCLAHE(
            clipLimit=self.clip_limit, tileGridSize=self.tile_grid_size
        )

    def process(self, frame_bgr: np.ndarray) -> np.ndarray:
        """
        Equalize lighting on BGR frame.

        :param frame_bgr: Raw input BGR frame from camera.
        :return: Lighting-normalized BGR frame with shadow detail recovered.
        """
        if frame_bgr is None:
            return frame_bgr
        lab = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l_equalized = self.clahe.apply(l)
        merged = cv2.merge((l_equalized, a, b))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


class EngagementManager:
    """
    Engagement Zone and Wake Gesture state machine.
    Solves the 'Resting Hand' false-positive problem where face-scratching, sipping coffee,
    or resting hands near keyboards triggers accidental pinches or swipes.

    Features:
    1. Engagement Zone: Ignores hands outside a central interaction bounding box.
    2. Wake Gesture: Requires holding a flat OPEN_PALM for 1.2s to unlock active tracking.
    3. Auto-Lock Timeout: Automatically locks tracking after user removes hand for >2.5s.
    """

    def __init__(
        self,
        zone_box: Tuple[float, float, float, float] = (0.10, 0.10, 0.90, 0.88),
        wake_hold_seconds: float = 1.20,
        auto_lock_timeout: float = 2.50,
        require_wake_gesture: bool = True,
    ) -> None:
        """
        Initialize the engagement manager.

        :param zone_box: (x1, y1, x2, y2) normalized box defining active camera interaction zone.
        :param wake_hold_seconds: Duration to hold OPEN_PALM before tracking unlocks.
        :param auto_lock_timeout: Inactivity seconds before tracking auto-locks.
        :param require_wake_gesture: If True, requires wake gesture; if False, zone-only.
        """
        self.zone_x1, self.zone_y1, self.zone_x2, self.zone_y2 = zone_box
        self.wake_hold_seconds: float = float(wake_hold_seconds)
        self.auto_lock_timeout: float = float(auto_lock_timeout)
        self.require_wake_gesture: bool = bool(require_wake_gesture)

        self.is_engaged: bool = not require_wake_gesture
        self.open_palm_start_time: float = 0.0
        self.last_engagement_time: float = 0.0
        self.last_status: str = "INITIALIZED"

    def update(
        self,
        hand_landmarks: Optional[List[Tuple[float, float, float]]],
        gesture_name: str,
        current_time: Optional[float] = None,
    ) -> Tuple[bool, str]:
        """
        Evaluate engagement status for the current frame.

        :param hand_landmarks: 21 normalized landmarks or None.
        :param gesture_name: Currently classified gesture string (e.g. 'OPEN_PALM', 'PINCH').
        :param current_time: Timestamp float (defaults to time.time()).
        :return: Tuple of (is_active_allowed: bool, status_message: str).
        """
        now = current_time if current_time is not None else time.time()

        if not hand_landmarks:
            if self.is_engaged and (now - self.last_engagement_time > self.auto_lock_timeout):
                if self.require_wake_gesture:
                    self.is_engaged = False
            self.open_palm_start_time = 0.0
            self.last_status = "LOCKED (NO HAND)" if self.require_wake_gesture else "IDLE"
            return False, self.last_status

        # 1. Check if palm center (Node 9 - Middle MCP) is within Engagement Zone
        palm_center = hand_landmarks[9] if len(hand_landmarks) > 9 else hand_landmarks[0]
        px, py = palm_center[0], palm_center[1]

        in_zone = (self.zone_x1 <= px <= self.zone_x2) and (self.zone_y1 <= py <= self.zone_y2)
        if not in_zone:
            self.open_palm_start_time = 0.0
            self.last_status = "OUTSIDE ENGAGEMENT ZONE"
            return False, self.last_status

        # If wake gesture is disabled, simply presence in zone is sufficient
        if not self.require_wake_gesture:
            self.is_engaged = True
            self.last_engagement_time = now
            self.last_status = "ACTIVE"
            return True, self.last_status

        # 2. Wake Gesture Logic: User must hold OPEN_PALM
        if not self.is_engaged:
            if gesture_name == "OPEN_PALM":
                if self.open_palm_start_time == 0.0:
                    self.open_palm_start_time = now
                elapsed = now - self.open_palm_start_time
                if elapsed >= self.wake_hold_seconds:
                    self.is_engaged = True
                    self.last_engagement_time = now
                    self.last_status = "ACTIVE (UNLOCKED)"
                    return True, self.last_status
                progress_pct = int(min(elapsed / self.wake_hold_seconds, 1.0) * 100)
                self.last_status = f"HOLD PALM TO WAKE ({progress_pct}%)"
                return False, self.last_status
            else:
                self.open_palm_start_time = 0.0
                self.last_status = "LOCKED (SHOW PALM TO WAKE)"
                return False, self.last_status

        # Active unlocked state
        self.last_engagement_time = now
        self.last_status = "ACTIVE"
        return True, self.last_status



class EMAFilter:
    """
    Exponential Moving Average (EMA) filter acting as a discrete, low-pass,
    infinite-impulse response (IIR) filter. Places more weight on recent data
    while exponentially discounting older frames.

    Difference Equation:
        smoothed_value = (alpha * current_value) + ((1 - alpha) * smoothed_value)
    """

    def __init__(self, alpha: float = 0.20) -> None:
        """
        Initialize the EMA filter.

        :param alpha: Smoothing factor / cutoff aggressiveness between 0 and 1.
                      Lower values yield smoother cursor movement; higher values
                      increase responsiveness. Default is ~0.20.
        """
        self.alpha: float = float(alpha)
        self.smoothed_value: Optional[float] = None

    def update(self, current_value: Optional[float]) -> Optional[float]:
        """
        Process incoming raw coordinate value with exponential moving average smoothing.

        Edge Case Handling:
        If MediaPipe loses hand tracking (hand goes off-screen, current_value is None),
        the filter gracefully pauses without throwing a NoneType math error,
        and returns the last known smoothed position so the cursor remains steady.

        :param current_value: Raw coordinate float or None if hand tracking is lost.
        :return: Smoothed coordinate float, or None if no valid frames received yet.
        """
        if current_value is None:
            return self.smoothed_value

        # Initialize the filter with the first input to prevent "warm up" delay
        if self.smoothed_value is None:
            self.smoothed_value = float(current_value)
        else:
            # The core difference equation for EMA filtering
            self.smoothed_value = (self.alpha * float(current_value)) + (
                (1.0 - self.alpha) * self.smoothed_value
            )
        return self.smoothed_value

    def set_alpha(self, new_alpha: float) -> None:
        """Dynamically adjust smoothing alpha at runtime from UI slider."""
        self.alpha = float(new_alpha)

    def reset(self) -> None:
        """Reset internal filter history."""
        self.smoothed_value = None


class GestureDebouncer:
    """
    Debouncing and cooldown state machine using Python's time module.
    Prevents rapid-fire OS macro execution by enforcing a per-gesture cooldown period (default: 0.5s).
    """

    def __init__(self, cooldown_seconds: float = 0.50) -> None:
        """
        Initialize the gesture debouncer.

        :param cooldown_seconds: Duration in seconds to lock out re-triggering for the same gesture.
        """
        self.cooldown_seconds: float = float(cooldown_seconds)
        self.last_trigger_times: Dict[str, float] = {}
        self.last_triggered_gesture: Optional[str] = None

    def can_trigger(
        self, gesture_name: str, current_time: Optional[float] = None
    ) -> bool:
        """
        Check whether a gesture is eligible to fire an OS macro.

        :param gesture_name: Identifier of gesture (e.g. 'PINCH', 'SWIPE_LEFT').
        :param current_time: Optional timestamp; defaults to time.time().
        :return: True if cooldown has elapsed, False if locked.
        """
        if not gesture_name or gesture_name == "NONE":
            return False

        now = current_time if current_time is not None else time.time()
        last_time = self.last_trigger_times.get(gesture_name, 0.0)
        return (now - last_time) >= self.cooldown_seconds

    def record_trigger(
        self, gesture_name: str, current_time: Optional[float] = None
    ) -> None:
        """
        Record that a gesture successfully triggered an OS macro, starting its cooldown timer.

        :param gesture_name: Triggered gesture identifier.
        :param current_time: Optional timestamp; defaults to time.time().
        """
        now = current_time if current_time is not None else time.time()
        self.last_trigger_times[gesture_name] = now
        self.last_triggered_gesture = gesture_name

    def is_cooldown_active(self, current_time: Optional[float] = None) -> bool:
        """
        Check if any recent gesture trigger is currently in active cooldown.

        :param current_time: Optional timestamp; defaults to time.time().
        :return: True if recently triggered gesture is within cooldown window.
        """
        if not self.last_triggered_gesture:
            return False

        now = current_time if current_time is not None else time.time()
        last_time = self.last_trigger_times.get(self.last_triggered_gesture, 0.0)
        return (now - last_time) < self.cooldown_seconds


class CalibrationDashboard:
    """
    Non-blocking Tkinter calibration control panel running in a separate daemon thread.
    Allows real-time dynamic tuning of pinch_threshold and EMA_alpha without freezing
    the OpenCV video capture while loop.
    """

    def __init__(
        self, initial_pinch: float = 0.06, initial_alpha: float = 0.20
    ) -> None:
        """
        Spawn the background calibration dashboard thread.

        :param initial_pinch: Initial Euclidean distance threshold to trigger pinch.
        :param initial_alpha: Initial EMA smoothing coefficient.
        """
        self.pinch_threshold: float = float(initial_pinch)
        self.ema_alpha: float = float(initial_alpha)
        self.is_running: bool = True
        self.root: Optional[tk.Tk] = None

        self._thread = threading.Thread(target=self._run_ui, daemon=True)
        self._thread.start()

    def _run_ui(self) -> None:
        """Background Tkinter GUI event loop."""
        try:
            self.root = tk.Tk()
            self.root.title("Touchless Calibration Panel")
            self.root.geometry("350x230")
            self.root.configure(bg="#181825")
            self.root.attributes("-topmost", True)

            # Title Header
            lbl_title = tk.Label(
                self.root,
                text="Calibration Dashboard",
                font=("Segoe UI", 12, "bold"),
                bg="#181825",
                fg="#89b4fa",
            )
            lbl_title.pack(pady=(12, 10))

            # --- Slider 1: Pinch Threshold ---
            self.lbl_pinch = tk.Label(
                self.root,
                text=f"Pinch Threshold: {self.pinch_threshold:.3f}",
                bg="#181825",
                fg="#cdd6f4",
                font=("Segoe UI", 9, "bold"),
            )
            self.lbl_pinch.pack(anchor="w", padx=20)

            self.slider_pinch = ttk.Scale(
                self.root,
                from_=0.01,
                to=0.15,
                value=self.pinch_threshold,
                command=self._on_pinch_slider,
            )
            self.slider_pinch.pack(fill="x", padx=20, pady=(2, 10))

            # --- Slider 2: EMA Alpha Smoothing ---
            self.lbl_alpha = tk.Label(
                self.root,
                text=f"EMA Alpha (Smoothing): {self.ema_alpha:.2f}",
                bg="#181825",
                fg="#cdd6f4",
                font=("Segoe UI", 9, "bold"),
            )
            self.lbl_alpha.pack(anchor="w", padx=20)

            self.slider_alpha = ttk.Scale(
                self.root,
                from_=0.05,
                to=0.80,
                value=self.ema_alpha,
                command=self._on_alpha_slider,
            )
            self.slider_alpha.pack(fill="x", padx=20, pady=(2, 14))

            # Status footer
            lbl_hint = tk.Label(
                self.root,
                text="Changes take effect live in the video pipeline.",
                bg="#181825",
                fg="#a6adc8",
                font=("Segoe UI", 8),
            )
            lbl_hint.pack(pady=(0, 6))

            def on_close():
                self.is_running = False
                if self.root:
                    self.root.destroy()

            self.root.protocol("WM_DELETE_WINDOW", on_close)
            self.root.mainloop()
        except Exception:
            self.is_running = False

    def _on_pinch_slider(self, val: str) -> None:
        """Handle real-time pinch threshold slider adjustments."""
        self.pinch_threshold = float(val)
        if hasattr(self, "lbl_pinch") and self.lbl_pinch and self.lbl_pinch.winfo_exists():
            self.lbl_pinch.config(text=f"Pinch Threshold: {self.pinch_threshold:.3f}")

    def _on_alpha_slider(self, val: str) -> None:
        """Handle real-time EMA alpha slider adjustments."""
        self.ema_alpha = float(val)
        if hasattr(self, "lbl_alpha") and self.lbl_alpha and self.lbl_alpha.winfo_exists():
            self.lbl_alpha.config(text=f"EMA Alpha (Smoothing): {self.ema_alpha:.2f}")

    def get_pinch_threshold(self) -> float:
        """Thread-safe getter for active pinch threshold."""
        return self.pinch_threshold

    def get_ema_alpha(self) -> float:
        """Thread-safe getter for active smoothing alpha."""
        return self.ema_alpha

    def close(self) -> None:
        """Clean shutdown of dashboard window."""
        self.is_running = False
        if self.root:
            try:
                self.root.quit()
            except Exception:
                pass


def draw_hud(
    frame: np.ndarray,
    gesture_state: str,
    pinch_distance: float,
    pinch_threshold: float,
    is_cooldown_active: bool,
    fps: float = 60.0,
    ema_alpha: float = 0.20,
    engagement_status: Optional[str] = None,
    engagement_zone: Optional[Tuple[float, float, float, float]] = None,
    clahe_enabled: bool = False,
) -> np.ndarray:
    """
    Renders live heads-up telemetry directly on the OpenCV video frame using cv2.putText.

    Displays:
    - Current Gesture State (e.g., 'State: PINCH', 'State: OPEN_PALM', 'State: NONE')
    - Live Euclidean Distance between Node 4 and Node 8
    - Visual Cooldown Indicator ('COOLDOWN ACTIVE' vs 'COOLDOWN: READY')
    - Active threshold and EMA alpha parameters
    - Current pipeline framerate (FPS) and CLAHE status
    - Engagement Zone boundary and Lock/Unlock status

    :param frame: Target BGR video frame.
    :param gesture_state: Name of active gesture classification.
    :param pinch_distance: Computed continuous Euclidean distance between thumb and index.
    :param pinch_threshold: Active pinch trigger threshold from calibration dashboard.
    :param is_cooldown_active: True if gesture macro cooldown is actively engaged.
    :param fps: Current smoothed frames-per-second measurement.
    :param ema_alpha: Current smoothing factor.
    :param engagement_status: Status string from EngagementManager.
    :param engagement_zone: (x1, y1, x2, y2) normalized box for engagement zone.
    :param clahe_enabled: Whether dynamic CLAHE lighting normalization is active.
    :return: Annotated BGR frame with heads-up overlay.
    """
    overlay = frame.copy()
    h, w = frame.shape[:2]

    # Draw Engagement Zone border if configured
    if engagement_zone is not None:
        zx1 = int(engagement_zone[0] * w)
        zy1 = int(engagement_zone[1] * h)
        zx2 = int(engagement_zone[2] * w)
        zy2 = int(engagement_zone[3] * h)
        # Subtle glowing corner/border for active interaction zone
        zone_color = (0, 255, 120) if (engagement_status and "ACTIVE" in engagement_status) else (60, 100, 200)
        cv2.rectangle(frame, (zx1, zy1), (zx2, zy2), zone_color, 1, cv2.LINE_AA)
        cv2.putText(
            frame,
            "ENGAGEMENT ZONE",
            (zx1 + 8, zy1 + 18),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            zone_color,
            1,
            cv2.LINE_AA,
        )

    # Sleek dark frosted glassmorphism HUD panel (expanded height if engagement shown)
    panel_height = 235 if engagement_status else 205
    cv2.rectangle(overlay, (15, 15), (395, panel_height), (18, 18, 26), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
    cv2.rectangle(frame, (15, 15), (395, panel_height), (80, 80, 105), 1, cv2.LINE_AA)

    # 1. Current Gesture State
    if gesture_state == "PINCH":
        state_color = (0, 255, 120)  # Neon mint green
    elif gesture_state in ("POINTING", "PEACE", "OPEN_PALM", "FIST"):
        state_color = (0, 220, 255)  # Electric cyan
    else:
        state_color = (170, 170, 190)  # Muted silver

    cv2.putText(
        frame,
        f"State: {gesture_state}",
        (30, 48),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        state_color,
        2,
        cv2.LINE_AA,
    )

    # 2. Live Euclidean Distance Calculation
    is_pinching = pinch_distance > 0.0 and pinch_distance < pinch_threshold
    dist_color = (0, 255, 120) if is_pinching else (220, 220, 255)
    cv2.putText(
        frame,
        f"Pinch Dist: {pinch_distance:.4f}",
        (30, 84),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        dist_color,
        2,
        cv2.LINE_AA,
    )

    # 3. Visual Cooldown Indicator
    if is_cooldown_active:
        cv2.putText(
            frame,
            "COOLDOWN ACTIVE",
            (30, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 140, 255),  # High-visibility warning amber/orange
            2,
            cv2.LINE_AA,
        )
    else:
        cv2.putText(
            frame,
            "COOLDOWN: READY",
            (30, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.60,
            (0, 255, 180),  # Bright mint green ready
            1,
            cv2.LINE_AA,
        )

    # 4. Calibration Parameters Readout
    clahe_tag = " | CLAHE: ON" if clahe_enabled else ""
    cv2.putText(
        frame,
        f"Thresh: {pinch_threshold:.3f} | Alpha: {ema_alpha:.2f}{clahe_tag}",
        (30, 156),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.50,
        (190, 190, 210),
        1,
        cv2.LINE_AA,
    )

    # 5. Framerate Readout
    cv2.putText(
        frame,
        f"FPS: {fps:.1f}",
        (30, 188),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.52,
        (100, 255, 100),
        1,
        cv2.LINE_AA,
    )

    # 6. Engagement / Wake Status (if provided)
    if engagement_status:
        if "ACTIVE" in engagement_status:
            eng_color = (0, 255, 120)
        elif "HOLD" in engagement_status or "WAKING" in engagement_status:
            eng_color = (0, 200, 255)
        else:
            eng_color = (120, 140, 255)
        cv2.putText(
            frame,
            f"Zone: {engagement_status}",
            (30, 218),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.50,
            eng_color,
            1,
            cv2.LINE_AA,
        )

    return frame

