"""
main.py
-------
The core execution script that ties together camera ingestion, inference,
and macro routing into a multi-stage pipeline.
"""

import argparse
import logging
import sys
import time
from typing import Optional
import cv2

try:
    from member_1 import CameraAcquisition
    from member_2 import LandmarkInference
    from member_3 import GestureClassifier, GestureType
    from member_4 import OSMacroController
    from member_5 import GestureControllerUI
except ImportError:
    from member_1.member_1 import CameraAcquisition
    from member_2.member_2 import LandmarkInference
    from member_3.member_3 import GestureClassifier, GestureType
    from member_4.member_4 import OSMacroController
    from member_5.member_5 import GestureControllerUI

from utils import (
    EMAFilter,
    GestureDebouncer,
    CalibrationDashboard,
    draw_hud,
    LightingNormalizer,
    EngagementManager,
)


def parse_args() -> argparse.Namespace:
    """Parse command line configuration options."""
    parser = argparse.ArgumentParser(
        description="Gesture-Driven OS Controller Multi-Stage Pipeline"
    )
    parser.add_argument(
        "--camera-id",
        type=int,
        default=0,
        help="Hardware camera device index (default: 0)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=640,
        help="Capture frame width (default: 640)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=480,
        help="Capture frame height (default: 480)",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=60,
        help="Target capture frame rate (default: 60 FPS)",
    )
    parser.add_argument(
        "--no-ui",
        action="store_true",
        help="Run headless pipeline without the Tkinter dashboard",
    )
    parser.add_argument(
        "--cv-window",
        action="store_true",
        help="Display auxiliary floating OpenCV window in addition to the frontend studio UI",
    )
    parser.add_argument(
        "--mouse",
        action="store_true",
        help="Enable touchless air-mouse cursor control & painting in mid-air (press 'm' in window to toggle)",
    )
    parser.add_argument(
        "--keyboard",
        action="store_true",
        help="Enable touchless in-air virtual shortcut keyboard (press 'k' in window to toggle)",
    )
    parser.add_argument(
        "--clahe",
        action="store_true",
        default=True,
        help="Enable dynamic CLAHE lighting normalization for dark rooms and backlighting (default: enabled)",
    )
    parser.add_argument(
        "--no-clahe",
        action="store_false",
        dest="clahe",
        help="Disable dynamic CLAHE lighting normalization",
    )
    parser.add_argument(
        "--wake-lock",
        action="store_true",
        help="Enable Wake Gesture (hold Open Palm for 1.2s to unlock tracking, suppressing resting-hand false positives)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable detailed debug logging output",
    )
    return parser.parse_args()


def run_pipeline(args: argparse.Namespace) -> None:
    """Execute the multi-stage gesture recognition and macro routing loop."""
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(message)s")

    logging.info("[Pipeline] Initializing modular stages...")

    # Stage 1: Camera Ingestion
    camera = CameraAcquisition(
        camera_index=args.camera_id,
        width=args.width,
        height=args.height,
        fps=getattr(args, "fps", 60),
    )

    # Stage 2: Landmark Inference (MediaPipe Hands)
    inference = LandmarkInference(
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5,
    )

    # Stage 3: Gesture Classifier & Debouncer
    classifier = GestureClassifier()
    debouncer = GestureDebouncer(cooldown_seconds=0.50)

    # Lighting Normalization & Resting-Hand Engagement Management
    use_clahe = getattr(args, "clahe", True)
    lighting_normalizer = LightingNormalizer(clip_limit=2.2) if use_clahe else None
    wake_lock_enabled = getattr(args, "wake_lock", False)
    engagement_mgr = EngagementManager(
        zone_box=(0.10, 0.10, 0.90, 0.88),
        wake_hold_seconds=1.20,
        require_wake_gesture=wake_lock_enabled,
    )

    # Stage 4: OS Macro Controller & Mathematical Smoothing Filters (EMA)
    macro_controller = OSMacroController()
    macro_controller.mouse_tracking_enabled = getattr(args, "mouse", False)
    macro_controller.air_keyboard_enabled = getattr(args, "keyboard", False)
    filter_x = EMAFilter(alpha=0.20)
    filter_y = EMAFilter(alpha=0.20)

    # Stage 5: Calibration Dashboard (threaded non-blocking Tkinter panel)
    dashboard = CalibrationDashboard(initial_pinch=0.06, initial_alpha=0.20)

    # Stage 6: Optional Studio UI Frontend
    ui: Optional[GestureControllerUI] = None
    if not args.no_ui:
        try:
            ui = GestureControllerUI(
                classifier=classifier,
                macro_controller=macro_controller,
            )
            logging.info("[Pipeline] Unified Gesture Studio UI launched.")
        except Exception as e:
            logging.warning(f"[Pipeline] Could not initialize UI dashboard: {e}. Continuing in CLI mode.")
            ui = None

    show_cv_window = args.no_ui or getattr(args, "cv_window", False)

    logging.info("[Pipeline] Starting continuous multi-stage pipeline loop. Press 'q' or ESC to exit.")
    if macro_controller.mouse_tracking_enabled:
        logging.info("[Pipeline] Touchless Air-Mouse mode is ENABLED. Point index finger to move, pinch to paint/click.")
    else:
        logging.info("[Pipeline] Tip: Press 'm' to toggle touchless Air-Mouse | Press 'k' to toggle Air-Keyboard.")

    smooth_fps = 60.0
    prev_time = time.time()
    last_detected_gesture = GestureType.NONE

    try:
        while camera.is_opened():
            curr_time = time.time()
            dt = max(curr_time - prev_time, 1e-5)
            raw_fps = 1.0 / dt
            smooth_fps = 0.88 * smooth_fps + 0.12 * raw_fps
            prev_time = curr_time

            # Dynamic Calibration from Threaded Dashboard Sliders
            active_pinch_thresh = dashboard.get_pinch_threshold()
            classifier.pinch_threshold = active_pinch_thresh
            active_alpha = dashboard.get_ema_alpha()
            filter_x.set_alpha(active_alpha)
            filter_y.set_alpha(active_alpha)

            # Ingestion Stage: capture frame & convert BGR to RGB (already mirrored)
            success, frame_bgr, frame_rgb = camera.read_frame()
            if not success or frame_bgr is None or frame_rgb is None:
                logging.warning("[Pipeline] Blank frame encountered, skipping...")
                time.sleep(0.005)
                continue

            # Preprocessing: Dynamic CLAHE lighting normalization (L-channel of LAB)
            if lighting_normalizer is not None:
                frame_bgr = lighting_normalizer.process(frame_bgr)
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

            # Inference Stage: 21 3D spatial key point extraction
            detected_hands = inference.process(frame_rgb)

            # Gesture Classification Stage: real-time instantaneous evaluation (zero overlapping delay)
            active_hand = detected_hands[0] if detected_hands else None
            raw_gesture, metrics = classifier.classify(active_hand)

            # Resting Hand Prevention: Engagement Zone & Wake Gesture State Machine
            is_engaged, eng_status = engagement_mgr.update(
                active_hand.normalized_landmarks if active_hand else None,
                raw_gesture.name,
                current_time=curr_time,
            )

            # Gate gesture execution based on engagement state
            gesture = raw_gesture if is_engaged else GestureType.NONE
            last_detected_gesture = gesture if active_hand is not None else GestureType.NONE

            # Touchless Air-Mouse Cursor Control with Mathematical Smoothing (Dual EMAFilter)
            # The OS cursor strictly and continuously follows the INDEX FINGER TIP (Node 8)
            # Double Pointing -> Left Click | Middle Click -> Right Click | Pinch -> Drag Latch
            is_pinch = bool(metrics.get("is_pinching", 0.0))
            is_double_point = bool(metrics.get("is_double_pointing", 0.0))
            is_mid_click = bool(metrics.get("is_middle_click", 0.0))

            if active_hand and active_hand.normalized_landmarks and macro_controller.mouse_tracking_enabled:
                index_tip = active_hand.normalized_landmarks[LandmarkInference.INDEX_FINGER_TIP]
                raw_cursor_x = float(index_tip[0])
                raw_cursor_y = float(index_tip[1])

                # Pass coordinates through separate X and Y EMA filters (~0.20 alpha) to stop jitter
                smooth_x = filter_x.update(raw_cursor_x)
                smooth_y = filter_y.update(raw_cursor_y)
                if smooth_x is not None and smooth_y is not None:
                    macro_controller.update_cursor(
                        smooth_x,
                        smooth_y,
                        is_pinching=is_pinch,
                        is_double_pointing=is_double_point,
                        is_middle_click=is_mid_click,
                    )
            else:
                # Edge case: hand goes off-screen, gracefully pause EMA without throwing math error
                filter_x.update(None)
                filter_y.update(None)

            # Touchless Air-Keyboard Interaction (hovering / pinching on in-air virtual keys)
            if active_hand and active_hand.normalized_landmarks and macro_controller.air_keyboard_enabled:
                index_tip = active_hand.normalized_landmarks[LandmarkInference.INDEX_FINGER_TIP]
                triggered_key = macro_controller.update_air_keyboard(
                    index_tip[0], index_tip[1], is_pinch, current_time=curr_time
                )
                if triggered_key and ui is not None:
                    ui._log_event(f"⌨️ Air Key: {triggered_key.label} ({'+'.join(triggered_key.keys)})")

            # OS Macro Routing Stage with 0.5s Debouncing / Cooldown
            if is_engaged and gesture != GestureType.NONE:
                if debouncer.can_trigger(gesture.name, curr_time):
                    macro_controller.execute_gesture(gesture)
                    debouncer.record_trigger(gesture.name, curr_time)

            # Visualization: overlay landmarks, HUD telemetry & floating Air Keyboard
            annotated_frame = inference.draw_landmarks(frame_bgr, detected_hands)

            # Render active cursor reticle directly on Index Finger Tip (Node 8) and Middle Tip (Node 12)
            if active_hand and active_hand.pixel_landmarks and macro_controller.mouse_tracking_enabled:
                ix, iy = active_hand.pixel_landmarks[LandmarkInference.INDEX_FINGER_TIP][:2]
                if is_mid_click:
                    reticle_color = (0, 140, 255)  # Amber / Orange for Right Click
                    reticle_text = "RIGHT CLICK"
                    # Also highlight middle fingertip
                    mx, my = active_hand.pixel_landmarks[LandmarkInference.MIDDLE_FINGER_TIP][:2]
                    cv2.circle(annotated_frame, (int(mx), int(my)), 10, reticle_color, 2, cv2.LINE_AA)
                elif is_double_point:
                    reticle_color = (0, 255, 120)  # Neon mint for Left Click
                    reticle_text = "LEFT CLICK (DOUBLE POINT)"
                    # Highlight both index and middle fingertips
                    mx, my = active_hand.pixel_landmarks[LandmarkInference.MIDDLE_FINGER_TIP][:2]
                    cv2.circle(annotated_frame, (int(mx), int(my)), 10, reticle_color, 2, cv2.LINE_AA)
                elif is_pinch:
                    reticle_color = (0, 255, 120)
                    reticle_text = "DRAG / PINCH"
                else:
                    reticle_color = (0, 220, 255)  # Electric cyan for index tracking
                    reticle_text = "INDEX CURSOR"

                cv2.circle(annotated_frame, (int(ix), int(iy)), 12, reticle_color, 2, cv2.LINE_AA)
                cv2.circle(annotated_frame, (int(ix), int(iy)), 3, reticle_color, -1, cv2.LINE_AA)
                cv2.putText(
                    annotated_frame,
                    reticle_text,
                    (int(ix) + 14, int(iy) - 8),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.42,
                    reticle_color,
                    1,
                    cv2.LINE_AA,
                )

            is_cd_active = debouncer.is_cooldown_active(curr_time)
            annotated_frame = draw_hud(
                annotated_frame,
                gesture_state=last_detected_gesture.name,
                pinch_distance=metrics.get("normalized_pinch_distance", 0.0),
                pinch_threshold=active_pinch_thresh,
                is_cooldown_active=is_cd_active,
                fps=smooth_fps,
                ema_alpha=active_alpha,
                engagement_status=eng_status if wake_lock_enabled else None,
                engagement_zone=engagement_mgr.zone_box if wake_lock_enabled else None,
                clahe_enabled=bool(lighting_normalizer is not None),
            )

            # Overlay floating Air Keyboard keys on top of video feed
            if macro_controller.air_keyboard_enabled:
                annotated_frame = macro_controller.air_keyboard.render_overlay(
                    annotated_frame, current_time=curr_time
                )

            # Auxiliary OpenCV Window (if headless or --cv-window explicitly requested)
            if show_cv_window:
                cv2.imshow("Gesture OS Controller Pipeline", annotated_frame)
                try:
                    if cv2.getWindowProperty("Gesture OS Controller Pipeline", cv2.WND_PROP_VISIBLE) < 1:
                        logging.info("[Pipeline] Visualization window closed. Exiting loop.")
                        break
                except Exception:
                    pass

            # UI Update: stream live camera frame with OS HUD into frontend Center Stage
            if ui is not None:
                try:
                    if not getattr(ui, "is_running", True) or not ui.root.winfo_exists():
                        logging.info("[Pipeline] UI window closed. Exiting loop.")
                        break
                except Exception:
                    logging.info("[Pipeline] UI window closed. Exiting loop.")
                    break
                try:
                    ui.update_telemetry(
                        gesture=last_detected_gesture,
                        context=macro_controller.current_app_context,
                        pinch_metric=metrics.get("normalized_pinch_distance", 0.0),
                        metrics=metrics,
                        detected_hand=active_hand,
                        frame=annotated_frame,
                        fps=smooth_fps,
                    )
                    ui.update_idle()
                except Exception as e:
                    logging.warning(f"[Pipeline] UI telemetry update skipped: {e}")

            # CPU Thermal Throttling Prevention: Yield execution slice back to OS thread scheduler
            # Drastically lowers CPU consumption from 100% peg down to 12-20% alongside creative apps
            time.sleep(0.001)

            # Key controls: Break on 'q'/ESC, toggle Air-Mouse on 'm', toggle Air-Keyboard on 'k'
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q") or key == 27:
                logging.info("[Pipeline] Termination key pressed. Exiting loop.")
                break
            elif key == ord("m") or key == ord("M"):
                macro_controller.mouse_tracking_enabled = not macro_controller.mouse_tracking_enabled
                if ui is not None and hasattr(ui, "_update_air_mouse_button"):
                    ui._update_air_mouse_button()
                status_str = "ENABLED" if macro_controller.mouse_tracking_enabled else "DISABLED"
                logging.info(f"[Pipeline] Touchless Air-Mouse mode toggled: {status_str}")
            elif key == ord("k") or key == ord("K"):
                macro_controller.air_keyboard_enabled = not macro_controller.air_keyboard_enabled
                if ui is not None and hasattr(ui, "_update_air_keyboard_button"):
                    ui._update_air_keyboard_button()
                status_str = "ENABLED" if macro_controller.air_keyboard_enabled else "DISABLED"
                logging.info(f"[Pipeline] Touchless Air-Keyboard mode toggled: {status_str}")

    except KeyboardInterrupt:
        logging.info("[Pipeline] Interrupted by user.")
    finally:
        logging.info("[Pipeline] Cleaning up resources...")
        dashboard.close()
        camera.release()
        inference.close()
        cv2.destroyAllWindows()
        if ui is not None:
            try:
                if ui.root.winfo_exists():
                    ui.root.destroy()
            except Exception:
                pass
        logging.info("[Pipeline] Shutdown complete.")


def main() -> None:
    """Entry point."""
    args = parse_args()
    try:
        run_pipeline(args)
    except Exception as e:
        logging.error(f"[Pipeline] Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
