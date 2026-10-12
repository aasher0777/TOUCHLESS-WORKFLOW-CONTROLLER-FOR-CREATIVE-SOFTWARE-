"""
os_macro_controller.py
----------------------
Uses pygetwindow to query the active foreground application window (e.g. Adobe Premiere Pro,
Figma, Web Browsers, Media Players) and dispatches contextual system-level macros directly into
the operating system using both pyautogui and the keyboard library.
"""
import json
import logging
import math
import os
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple
import cv2
import numpy as np

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    pyautogui = None
    PYAUTOGUI_AVAILABLE = False

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    keyboard = None
    KEYBOARD_AVAILABLE = False

try:
    import pygetwindow as gw
    PYGETWINDOW_AVAILABLE = True
except ImportError:
    gw = None
    PYGETWINDOW_AVAILABLE = False

try:
    from member_3.member_3 import GestureType
except ImportError:
    from member_3 import GestureType

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


@dataclass
class MacroAction:
    """Represents an execution macro action."""

    description: str
    action_type: str  # 'hotkey', 'press', 'click', 'custom'
    keys: List[str] = field(default_factory=list)
    custom_func: Optional[Callable[[], None]] = None


KEY_NAME_ALIASES: Dict[str, str] = {
    "playpause": "play/pause media",
    "play_pause": "play/pause media",
    "volumeup": "volume up",
    "volumedown": "volume down",
    "volumemute": "volume mute",
}


@dataclass
class AirKey:
    """Represents a virtual shortcut tile on the touchless Air Keyboard."""

    label: str                     # Short name shown on key e.g. "UNDO", "REDO", "BRUSH"
    keys: List[str]                # Physical shortcut keys e.g. ["ctrl", "z"] or ["b"]
    action_type: str = "hotkey"    # "hotkey" or "press"
    description: str = ""          # Human-readable description
    bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0) # Normalized [x1, y1, x2, y2]


class AirKeyboard:
    """Virtual in-air touchless keyboard overlay providing context-aware shortcut tiles."""

    def __init__(self, dwell_trigger_seconds: float = 0.40, cooldown_seconds: float = 0.45) -> None:
        self.dwell_trigger_seconds = dwell_trigger_seconds
        self.cooldown_seconds = cooldown_seconds
        self.last_trigger_time: float = 0.0
        self.hovered_key_idx: int = -1
        self.hover_start_time: float = 0.0
        self.flash_key_idx: int = -1
        self.flash_until_time: float = 0.0
        self.active_keys: List[AirKey] = []
        self.current_context: str = ""

        # Context-dependent keyboard layouts
        self.layouts: Dict[str, List[AirKey]] = self._init_layouts()
        self.set_context("default")

    def _init_layouts(self) -> Dict[str, List[AirKey]]:
        """Define customized shortcut banks for Photoshop, Premiere, Browser, Figma and Default."""
        return {
            "photoshop": [
                AirKey("UNDO", ["ctrl", "z"], "hotkey", "Undo Canvas Action"),
                AirKey("REDO", ["ctrl", "shift", "z"], "hotkey", "Redo Canvas Action"),
                AirKey("BRUSH", ["b"], "press", "Select Brush Tool"),
                AirKey("ERASER", ["e"], "press", "Select Eraser Tool"),
                AirKey("PAN", ["h"], "press", "Hand / Pan Tool"),
                AirKey("ZOOM+", ["ctrl", "="], "hotkey", "Zoom In Canvas"),
                AirKey("ZOOM-", ["ctrl", "-"], "hotkey", "Zoom Out Canvas"),
                AirKey("DESELECT", ["ctrl", "d"], "hotkey", "Deselect Selection"),
                AirKey("SAVE", ["ctrl", "s"], "hotkey", "Save Document"),
            ],
            "premiere": [
                AirKey("CUT", ["ctrl", "k"], "hotkey", "Razor Cut Split"),
                AirKey("SELECT", ["v"], "press", "Selection Tool"),
                AirKey("RIPPLE", ["shift", "delete"], "hotkey", "Ripple Delete"),
                AirKey("PLAY", ["space"], "press", "Play / Pause Timeline"),
                AirKey("ZOOM+", ["="], "press", "Zoom In Timeline"),
                AirKey("ZOOM-", ["-"], "press", "Zoom Out Timeline"),
                AirKey("UNDO", ["ctrl", "z"], "hotkey", "Undo Edit"),
                AirKey("SAVE", ["ctrl", "s"], "hotkey", "Save Project"),
            ],
            "browser": [
                AirKey("NEW TAB", ["ctrl", "t"], "hotkey", "Open New Tab"),
                AirKey("CLOSE", ["ctrl", "w"], "hotkey", "Close Active Tab"),
                AirKey("REOPEN", ["ctrl", "shift", "t"], "hotkey", "Reopen Closed Tab"),
                AirKey("BACK", ["alt", "left"], "hotkey", "Navigate Back"),
                AirKey("FORWARD", ["alt", "right"], "hotkey", "Navigate Forward"),
                AirKey("REFRESH", ["f5"], "press", "Reload Webpage"),
                AirKey("FIND", ["ctrl", "f"], "hotkey", "Search On Page"),
                AirKey("BOOKMARK", ["ctrl", "d"], "hotkey", "Bookmark Page"),
            ],
            "figma": [
                AirKey("FRAME", ["f"], "press", "Create Frame"),
                AirKey("RECT", ["r"], "press", "Rectangle Tool"),
                AirKey("TEXT", ["t"], "press", "Text Tool"),
                AirKey("GROUP", ["ctrl", "g"], "hotkey", "Group Elements"),
                AirKey("UNGROUP", ["ctrl", "shift", "g"], "hotkey", "Ungroup"),
                AirKey("COPY", ["ctrl", "c"], "hotkey", "Copy"),
                AirKey("PASTE", ["ctrl", "v"], "hotkey", "Paste"),
                AirKey("UNDO", ["ctrl", "z"], "hotkey", "Undo"),
            ],
            "default": [
                AirKey("UNDO", ["ctrl", "z"], "hotkey", "Undo Action"),
                AirKey("REDO", ["ctrl", "y"], "hotkey", "Redo Action"),
                AirKey("COPY", ["ctrl", "c"], "hotkey", "Copy Selection"),
                AirKey("PASTE", ["ctrl", "v"], "hotkey", "Paste Clipboard"),
                AirKey("SAVE", ["ctrl", "s"], "hotkey", "Save File"),
                AirKey("ENTER", ["enter"], "press", "Enter Key"),
                AirKey("ESC", ["esc"], "press", "Escape Key"),
                AirKey("DESKTOP", ["win", "d"], "hotkey", "Toggle Desktop"),
            ],
        }

    def set_context(self, context: str) -> None:
        """Switch active virtual shortcut bank based on active application context."""
        if context == self.current_context and self.active_keys:
            return
        self.current_context = context
        raw_keys = self.layouts.get(context, self.layouts["default"])
        num_keys = len(raw_keys)
        margin_x = 0.02
        gap_x = 0.010
        total_width = 1.0 - 2 * margin_x
        key_width = (total_width - (num_keys - 1) * gap_x) / num_keys
        key_top = 0.025
        key_height = 0.090

        self.active_keys = []
        for idx, key in enumerate(raw_keys):
            x1 = margin_x + idx * (key_width + gap_x)
            x2 = x1 + key_width
            y1 = key_top
            y2 = key_top + key_height
            k_copy = AirKey(
                label=key.label,
                keys=key.keys,
                action_type=key.action_type,
                description=key.description,
                bbox=(x1, y1, x2, y2),
            )
            self.active_keys.append(k_copy)

    def check_interaction(
        self,
        norm_x: float,
        norm_y: float,
        is_pinching: bool = False,
        current_time: Optional[float] = None,
    ) -> Optional[AirKey]:
        """
        Check if fingertip is hovering or pinching on an Air Key.
        Supports both pinch-to-click and dwell-activation.
        """
        now = current_time or time.time()
        if now - self.last_trigger_time < self.cooldown_seconds:
            return None

        # Find which key is under the fingertip
        hovered_idx = -1
        for idx, key in enumerate(self.active_keys):
            x1, y1, x2, y2 = key.bbox
            if x1 <= norm_x <= x2 and y1 <= norm_y <= y2:
                hovered_idx = idx
                break

        if hovered_idx != self.hovered_key_idx:
            self.hovered_key_idx = hovered_idx
            self.hover_start_time = now if hovered_idx != -1 else 0.0

        if hovered_idx == -1:
            return None

        triggered = False
        target_key = self.active_keys[hovered_idx]

        # Trigger option 1: Pinch while hovering over key
        if is_pinching:
            triggered = True

        # Trigger option 2: Dwell on key for dwell_trigger_seconds
        elif (now - self.hover_start_time) >= self.dwell_trigger_seconds:
            triggered = True

        if triggered:
            self.last_trigger_time = now
            self.flash_key_idx = hovered_idx
            self.flash_until_time = now + 0.30
            self.hover_start_time = now
            return target_key

        return None

    def render_overlay(self, frame: np.ndarray, current_time: Optional[float] = None) -> np.ndarray:
        """Draw the floating Air Keyboard virtual keys onto the visualization frame."""
        now = current_time or time.time()
        fh, fw = frame.shape[:2]

        for idx, key in enumerate(self.active_keys):
            x1 = int(key.bbox[0] * fw)
            y1 = int(key.bbox[1] * fh)
            x2 = int(key.bbox[2] * fw)
            y2 = int(key.bbox[3] * fh)

            is_hovered = (idx == self.hovered_key_idx)
            is_flashing = (idx == self.flash_key_idx and now < self.flash_until_time)

            if is_flashing:
                # Bright neon mint green flash on activation
                bg_color = (80, 220, 100)
                border_color = (255, 255, 255)
                text_color = (15, 15, 15)
                border_w = 2
            elif is_hovered:
                # Active electric ice blue / amber hover
                bg_color = (210, 150, 40)
                border_color = (255, 220, 100)
                text_color = (255, 255, 255)
                border_w = 2
            else:
                # Semi-transparent sleek dark card
                bg_color = (35, 30, 45)
                border_color = (90, 80, 100)
                text_color = (210, 210, 230)
                border_w = 1

            sub_rect = frame[y1:y2, x1:x2]
            color_rect = np.full_like(sub_rect, bg_color, dtype=np.uint8)
            alpha = 0.85 if (is_hovered or is_flashing) else 0.65
            cv2.addWeighted(color_rect, alpha, sub_rect, 1.0 - alpha, 0, sub_rect)
            frame[y1:y2, x1:x2] = sub_rect

            cv2.rectangle(frame, (x1, y1), (x2, y2), border_color, border_w, cv2.LINE_AA)

            # Dwell progress bar
            if is_hovered and not is_flashing:
                elapsed = now - self.hover_start_time
                progress = min(1.0, max(0.0, elapsed / self.dwell_trigger_seconds))
                prog_w = int((x2 - x1) * progress)
                cv2.line(frame, (x1, y2 - 2), (x1 + prog_w, y2 - 2), (0, 255, 180), 3)

            # Label text
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.38
            font_thick = 1 if not is_hovered else 2
            text_size = cv2.getTextSize(key.label, font, font_scale, font_thick)[0]
            tx = x1 + max(2, (x2 - x1 - text_size[0]) // 2)
            ty = y1 + (y2 - y1 + text_size[1]) // 2 - 4
            cv2.putText(frame, key.label, (tx, ty), font, font_scale, text_color, font_thick, cv2.LINE_AA)

            # Shortcut subtext (e.g. "Ctrl+Z")
            sub_text = "+".join(key.keys).upper()
            sub_font_scale = 0.28
            sub_size = cv2.getTextSize(sub_text, font, sub_font_scale, 1)[0]
            stx = x1 + max(2, (x2 - x1 - sub_size[0]) // 2)
            sty = ty + 12
            sub_color = (20, 20, 20) if is_flashing else ((240, 240, 240) if is_hovered else (150, 150, 170))
            cv2.putText(frame, sub_text, (stx, sty), font, sub_font_scale, sub_color, 1, cv2.LINE_AA)

        return frame


class OSMacroController:
    """Maps recognized gestures to context-dependent operating system hotkeys and macros."""

    def __init__(self, action_cooldown: float = 0.5) -> None:
        """
        Initialize the OS macro controller.

        :param action_cooldown: Cooldown in seconds between firing macros.
        """
        self.action_cooldown = action_cooldown
        self.last_action_time: float = 0.0
        self.profiles: Dict[str, Dict[GestureType, MacroAction]] = self._init_default_profiles()
        self.current_app_context: str = "default"
        self._cached_window_title: str = ""
        self._last_window_check_time: float = 0.0
        self._window_check_ttl: float = 0.15

        # Touchless Air-Mouse cursor tracking state
        self.mouse_tracking_enabled: bool = False
        self._prev_cursor_x: Optional[float] = None
        self._prev_cursor_y: Optional[float] = None
        self._is_mouse_down: bool = False
        if PYAUTOGUI_AVAILABLE:
            pyautogui.PAUSE = 0.0
            pyautogui.FAILSAFE = False

        # Touchless in-air virtual shortcut keyboard
        self.air_keyboard = AirKeyboard()
        self.air_keyboard_enabled: bool = False

        # Double Pointing & Middle Click state tracking
        self._prev_double_pointing: bool = False
        self._last_left_click_time: float = 0.0
        self._prev_middle_click: bool = False
        self._last_right_click_time: float = 0.0

    def _init_default_profiles(self) -> Dict[str, Dict[GestureType, MacroAction]]:
        """Configure contextual application macro routing profiles including Photoshop, Premiere Pro and Figma."""
        return {
            "default": {
                GestureType.PINCH: MacroAction("Left Click", "click"),
                GestureType.SWIPE_LEFT: MacroAction("Previous Item", "hotkey", ["alt", "left"]),
                GestureType.SWIPE_RIGHT: MacroAction("Next Item", "hotkey", ["alt", "right"]),
                GestureType.SWIPE_UP: MacroAction("Volume Up", "press", ["volumeup"]),
                GestureType.SWIPE_DOWN: MacroAction("Volume Down", "press", ["volumedown"]),
                GestureType.OPEN_PALM: MacroAction("Play / Pause", "press", ["playpause"]),
            },
            "photoshop": {
                GestureType.PINCH: MacroAction("Paint / Click & Drag", "click"),
                GestureType.POINTING: MacroAction("Brush Tool", "press", ["b"]),
                GestureType.SWIPE_LEFT: MacroAction("Undo Canvas Action", "hotkey", ["ctrl", "z"]),
                GestureType.SWIPE_RIGHT: MacroAction("Redo Canvas Action", "hotkey", ["ctrl", "shift", "z"]),
                GestureType.SWIPE_UP: MacroAction("Zoom In Canvas", "hotkey", ["ctrl", "="]),
                GestureType.SWIPE_DOWN: MacroAction("Zoom Out Canvas", "hotkey", ["ctrl", "-"]),
                GestureType.OPEN_PALM: MacroAction("Hand / Pan Tool", "press", ["h"]),
                GestureType.FIST: MacroAction("Deselect Selection", "hotkey", ["ctrl", "d"]),
                GestureType.PEACE: MacroAction("Eyedropper Color Picker", "press", ["i"]),
            },
            "premiere": {
                GestureType.PINCH: MacroAction("Split Clip / Razor Cut", "hotkey", ["ctrl", "k"]),
                GestureType.SWIPE_LEFT: MacroAction("Previous Edit Point", "hotkey", ["shift", "left"]),
                GestureType.SWIPE_RIGHT: MacroAction("Next Edit Point", "hotkey", ["shift", "right"]),
                GestureType.SWIPE_UP: MacroAction("Zoom In Timeline", "press", ["="]),
                GestureType.SWIPE_DOWN: MacroAction("Zoom Out Timeline", "press", ["-"]),
                GestureType.OPEN_PALM: MacroAction("Play / Stop Timeline", "press", ["space"]),
                GestureType.FIST: MacroAction("Ripple Delete Clip", "hotkey", ["shift", "delete"]),
                GestureType.POINTING: MacroAction("Selection Tool", "press", ["v"]),
                GestureType.PEACE: MacroAction("Mark In Point", "press", ["i"]),
            },
            "figma": {
                GestureType.PINCH: MacroAction("Select & Drag", "click"),
                GestureType.SWIPE_LEFT: MacroAction("Undo Canvas Action", "hotkey", ["ctrl", "z"]),
                GestureType.SWIPE_RIGHT: MacroAction("Redo Canvas Action", "hotkey", ["ctrl", "y"]),
                GestureType.SWIPE_UP: MacroAction("Zoom In Canvas", "hotkey", ["ctrl", "="]),
                GestureType.SWIPE_DOWN: MacroAction("Zoom Out Canvas", "hotkey", ["ctrl", "-"]),
                GestureType.OPEN_PALM: MacroAction("Hand / Pan Tool", "press", ["h"]),
                GestureType.FIST: MacroAction("Delete Selection", "press", ["delete"]),
                GestureType.POINTING: MacroAction("Move / Pointer Tool", "press", ["v"]),
                GestureType.PEACE: MacroAction("Toggle UI Zen Mode", "hotkey", ["ctrl", "\\"]),
            },
            "browser": {
                GestureType.PINCH: MacroAction("Click", "click"),
                GestureType.SWIPE_LEFT: MacroAction("Previous Tab", "hotkey", ["ctrl", "shift", "tab"]),
                GestureType.SWIPE_RIGHT: MacroAction("Next Tab", "hotkey", ["ctrl", "tab"]),
                GestureType.SWIPE_UP: MacroAction("Scroll Up", "press", ["pageup"]),
                GestureType.SWIPE_DOWN: MacroAction("Scroll Down", "press", ["pagedown"]),
                GestureType.FIST: MacroAction("Close Tab", "hotkey", ["ctrl", "w"]),
            },
            "media": {
                GestureType.PINCH: MacroAction("Play / Pause", "press", ["space"]),
                GestureType.SWIPE_LEFT: MacroAction("Previous Track", "press", ["prevtrack"]),
                GestureType.SWIPE_RIGHT: MacroAction("Next Track", "press", ["nexttrack"]),
                GestureType.SWIPE_UP: MacroAction("Volume Up", "press", ["volumeup"]),
                GestureType.SWIPE_DOWN: MacroAction("Volume Down", "press", ["volumedown"]),
            },
            "presentation": {
                GestureType.SWIPE_RIGHT: MacroAction("Next Slide", "press", ["right"]),
                GestureType.SWIPE_LEFT: MacroAction("Previous Slide", "press", ["left"]),
                GestureType.OPEN_PALM: MacroAction("Start Presentation", "press", ["f5"]),
                GestureType.FIST: MacroAction("End Presentation", "press", ["esc"]),
            },
        }

    def get_active_window_title(self) -> str:
        """
        Query the title of the active foreground application window using pygetwindow.
        Caches the window title with a short TTL (150ms) to reduce Win32 API system call overhead.

        :return: Active window title string, or empty string if not found.
        """
        if not PYGETWINDOW_AVAILABLE:
            return ""
        now = time.time()
        if now - self._last_window_check_time < self._window_check_ttl:
            return self._cached_window_title
        try:
            active_window = gw.getActiveWindow()
            self._cached_window_title = active_window.title if (active_window and active_window.title) else ""
            self._last_window_check_time = now
            return self._cached_window_title
        except Exception as e:
            logging.debug(f"[OSMacroController] Failed to query active window: {e}")
            return self._cached_window_title

    def is_application_running(self, app_keyword: str) -> bool:
        """
        Query system windows to verify if software like Adobe Premiere Pro or Figma is actively running.

        :param app_keyword: Substring identifier (e.g. 'premiere', 'figma').
        :return: True if matching application window exists, False otherwise.
        """
        if not PYGETWINDOW_AVAILABLE:
            return False
        try:
            kw = app_keyword.lower()
            titles = gw.getAllTitles()
            return any(kw in (t or "").lower() for t in titles)
        except Exception as e:
            logging.debug(f"[OSMacroController] Error querying running windows: {e}")
            return False

    def detect_context(self, window_title: Optional[str] = None) -> str:
        """
        Context routing query: Determine profile category based on the foreground window title.
        Identifies specialized applications like Adobe Premiere Pro and Figma.

        :param window_title: Optional explicit title string.
        :return: Context key ('premiere', 'figma', 'browser', 'media', 'presentation', or 'default').
        """
        title = (window_title or self.get_active_window_title()).lower()

        # Dedicated Creative Suite & Design Tool queries
        if any(term in title for term in ["photoshop", "adobe photoshop"]):
            return "photoshop"
        elif any(term in title for term in ["premiere", "adobe premiere", "pr pro"]):
            return "premiere"
        elif any(term in title for term in ["figma"]):
            return "figma"
        # Standard software categories
        elif any(browser in title for browser in ["chrome", "edge", "firefox", "brave", "opera"]):
            return "browser"
        elif any(player in title for player in ["spotify", "vlc", "youtube", "netflix", "music"]):
            return "media"
        elif any(pres in title for pres in ["powerpoint", "slides", "keynote", "acrobat", "pdf"]):
            return "presentation"
        else:
            return "default"

    def update_cursor(
        self,
        norm_x: float,
        norm_y: float,
        is_pinching: bool = False,
        is_double_pointing: bool = False,
        is_middle_click: bool = False,
        smooth_factor: float = 0.35,
    ) -> None:
        """
        Continuously positions the OS mouse cursor using normalized hand coordinates
        and handles touchless mouse clicks:
        - Index tip tracks cursor position smoothly.
        - Double Pointing (Index + Middle extended) -> Left Click.
        - Middle Click (Middle finger click / pinch) -> Right Click.
        - Index-Thumb Pinch -> Mouse Down / Drag & Drop latch.

        :param norm_x: Normalized horizontal coordinate in [0.0, 1.0].
        :param norm_y: Normalized vertical coordinate in [0.0, 1.0].
        :param is_pinching: Whether pinch state is currently active.
        :param is_double_pointing: Whether double pointing (index + middle) is active.
        :param is_middle_click: Whether middle finger click/pinch is active.
        :param smooth_factor: Exponential smoothing factor (0.0 to 1.0).
        """
        if not PYAUTOGUI_AVAILABLE or not self.mouse_tracking_enabled:
            return

        try:
            now = time.time()
            sw, sh = pyautogui.size()
            # Map active normalized workspace [0.12, 0.88] to full screen dimensions
            clamped_x = max(0.12, min(0.88, norm_x))
            clamped_y = max(0.12, min(0.88, norm_y))
            raw_x = (clamped_x - 0.12) / 0.76 * sw
            raw_y = (clamped_y - 0.12) / 0.76 * sh

            # Dynamic adaptive smoothing:
            # - High agility during fast motion (alpha up to 0.85)
            # - Anti-tremor stability during slow precision drawing
            if self._prev_cursor_x is None or self._prev_cursor_y is None:
                cur_x = raw_x
                cur_y = raw_y
            else:
                dist = math.hypot(raw_x - self._prev_cursor_x, raw_y - self._prev_cursor_y)
                alpha = min(0.85, max(smooth_factor, dist / 120.0))
                cur_x = alpha * raw_x + (1.0 - alpha) * self._prev_cursor_x
                cur_y = alpha * raw_y + (1.0 - alpha) * self._prev_cursor_y

            self._prev_cursor_x = cur_x
            self._prev_cursor_y = cur_y

            # Move mouse cursor safely within screen boundaries (margin of 2px prevents corner failsafe)
            target_x = max(2, min(sw - 3, int(cur_x)))
            target_y = max(2, min(sh - 3, int(cur_y)))
            pyautogui.moveTo(target_x, target_y)

            # 1. Middle Click (Middle finger click / pinch) -> Mouse Right Click (higher precedence)
            if is_middle_click and not self._prev_middle_click:
                if now - self._last_right_click_time >= 0.30:
                    pyautogui.click(button="right")
                    self._last_right_click_time = now
                    logging.info("[OSMacroController] Middle Click -> Right Click!")
            self._prev_middle_click = is_middle_click

            # 2. Double Pointing -> Mouse Left Click
            if is_double_pointing and not is_middle_click and not self._prev_double_pointing:
                if now - self._last_left_click_time >= 0.25:
                    pyautogui.click(button="left")
                    self._last_left_click_time = now
                    logging.info("[OSMacroController] Double Pointing -> Left Click!")
            self._prev_double_pointing = is_double_pointing

            # 3. Handle Drag / Paint latch with index-thumb pinch
            if is_pinching and not self._is_mouse_down:
                pyautogui.mouseDown()
                self._is_mouse_down = True
            elif not is_pinching and self._is_mouse_down:
                pyautogui.mouseUp()
                self._is_mouse_down = False

        except Exception as e:
            logging.debug(f"[OSMacroController] Mouse tracking exception: {e}")

    def update_air_keyboard(
        self,
        norm_x: float,
        norm_y: float,
        is_pinching: bool = False,
        current_time: Optional[float] = None,
    ) -> Optional[AirKey]:
        """
        Check and execute touchless Air Keyboard shortcut interactions.

        :param norm_x: Fingertip horizontal coordinate in [0.0, 1.0].
        :param norm_y: Fingertip vertical coordinate in [0.0, 1.0].
        :param is_pinching: True if pinch gesture is active.
        :param current_time: Current timestamp float.
        :return: Triggered AirKey if shortcut was fired, else None.
        """
        if not self.air_keyboard_enabled:
            return None

        # Synchronize context layout
        self.air_keyboard.set_context(self.current_app_context)

        triggered_key = self.air_keyboard.check_interaction(
            norm_x, norm_y, is_pinching, current_time
        )

        if triggered_key:
            self._dispatch_air_key(triggered_key)
            return triggered_key

        return None

    def _dispatch_air_key(self, key: AirKey) -> bool:
        """Instantly dispatch AirKey shortcut to operating system."""
        try:
            if key.action_type == "hotkey" and key.keys:
                dispatched = False
                if KEYBOARD_AVAILABLE:
                    try:
                        combo = "+".join([KEY_NAME_ALIASES.get(k.lower(), k) for k in key.keys])
                        keyboard.send(combo)
                        dispatched = True
                    except Exception:
                        pass
                if not dispatched and PYAUTOGUI_AVAILABLE:
                    try:
                        pyautogui.hotkey(*key.keys)
                        dispatched = True
                    except Exception:
                        pass
                if dispatched:
                    logging.info(f"[OSMacroController] Air Keyboard fired hotkey: {'+'.join(key.keys)} [{key.label}]")
                return dispatched
            elif key.action_type == "press" and key.keys:
                for k in key.keys:
                    k_trans = KEY_NAME_ALIASES.get(k.lower(), k)
                    dispatched = False
                    if KEYBOARD_AVAILABLE:
                        try:
                            keyboard.send(k_trans)
                            dispatched = True
                        except Exception:
                            pass
                    if not dispatched and PYAUTOGUI_AVAILABLE:
                        try:
                            pyautogui.press(k)
                            dispatched = True
                        except Exception:
                            pass
                logging.info(f"[OSMacroController] Air Keyboard fired press: {','.join(key.keys)} [{key.label}]")
                return True
        except Exception as e:
            logging.error(f"[OSMacroController] Air Keyboard dispatch error: {e}")
        return False

    def execute_gesture(self, gesture: GestureType) -> bool:
        """
        Matches classified gesture state with the active application's gesture dictionary,
        and fires system-level macros directly into the OS using keyboard and pyautogui.

        :param gesture: Recognized GestureType.
        :return: True if a macro was triggered, False otherwise.
        """
        if gesture == GestureType.NONE:
            return False

        now = time.time()
        if now - self.last_action_time < self.action_cooldown:
            return False

        self.current_app_context = self.detect_context()
        profile = self.profiles.get(self.current_app_context, self.profiles["default"])
        macro = profile.get(gesture)

        if not macro:
            # Fallback to default profile if active context doesn't define this gesture
            macro = self.profiles["default"].get(gesture)

        if not macro:
            return False

        logging.info(
            f"[OSMacroController] Executing '{macro.description}' for {gesture.name} "
            f"in context [{self.current_app_context}]."
        )

        success = False

        try:
            # 1. Mouse Click Macro Actions
            if macro.action_type == "click":
                if not self._is_mouse_down and PYAUTOGUI_AVAILABLE:
                    pyautogui.click()
                    success = True

            # 2. Multi-Key Hotkey Macro Actions
            elif macro.action_type == "hotkey" and macro.keys:
                dispatched = False
                if KEYBOARD_AVAILABLE:
                    try:
                        combo = "+".join([KEY_NAME_ALIASES.get(k.lower(), k) for k in macro.keys])
                        keyboard.send(combo)
                        dispatched = True
                    except Exception:
                        pass
                if not dispatched and PYAUTOGUI_AVAILABLE:
                    try:
                        pyautogui.hotkey(*macro.keys)
                        dispatched = True
                    except Exception:
                        pass
                success = dispatched

            # 3. Single Key Press Macro Actions
            elif macro.action_type == "press" and macro.keys:
                for key in macro.keys:
                    k_trans = KEY_NAME_ALIASES.get(key.lower(), key)
                    dispatched = False
                    if KEYBOARD_AVAILABLE:
                        try:
                            keyboard.send(k_trans)
                            dispatched = True
                        except Exception:
                            pass
                    if not dispatched and PYAUTOGUI_AVAILABLE:
                        try:
                            pyautogui.press(key)
                            dispatched = True
                        except Exception:
                            pass
                    if dispatched:
                        success = True

            # 4. Custom Function Actions
            elif macro.action_type == "custom" and macro.custom_func:
                macro.custom_func()
                success = True

            if success:
                self.last_action_time = now
            return success

        except Exception as e:
            logging.error(f"[OSMacroController] Error executing macro {macro.description}: {e}")
            return False

    def update_mapping(
        self, context: str, gesture: GestureType, macro: MacroAction
    ) -> None:
        """Dynamically add or update a gesture mapping for a specific context profile."""
        if context not in self.profiles:
            self.profiles[context] = {}
        self.profiles[context][gesture] = macro

    def save_profiles_to_json(self, filepath: str = "custom_profiles.json") -> bool:
        """Serialize all customized application profiles to JSON for persistence."""
        try:
            if filepath == "custom_profiles.json" and not os.path.exists(filepath):
                member_path = os.path.join(os.path.dirname(__file__), filepath)
                if os.path.exists(os.path.dirname(member_path)):
                    filepath = member_path
            data = {}
            for ctx, gestures in self.profiles.items():
                data[ctx] = {}
                for g_type, macro in gestures.items():
                    data[ctx][g_type.name] = {
                        "description": macro.description,
                        "action_type": macro.action_type,
                        "keys": macro.keys,
                    }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logging.info(f"[OSMacroController] Profiles saved to {filepath}")
            return True
        except Exception as e:
            logging.error(f"[OSMacroController] Failed to save profiles: {e}")
            return False

    def load_profiles_from_json(self, filepath: str = "custom_profiles.json") -> bool:
        """Load and restore application profiles from JSON file."""
        if not os.path.exists(filepath):
            member_path = os.path.join(os.path.dirname(__file__), filepath)
            if os.path.exists(member_path):
                filepath = member_path
            else:
                return False
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            for ctx, gestures in data.items():
                if ctx not in self.profiles:
                    self.profiles[ctx] = {}
                for g_name, m_info in gestures.items():
                    if hasattr(GestureType, g_name):
                        gt = getattr(GestureType, g_name)
                        self.profiles[ctx][gt] = MacroAction(
                            description=m_info.get("description", ""),
                            action_type=m_info.get("action_type", "hotkey"),
                            keys=m_info.get("keys", []),
                        )
            logging.info(f"[OSMacroController] Profiles loaded from {filepath}")
            return True
        except Exception as e:
            logging.error(f"[OSMacroController] Failed to load profiles: {e}")
            return False
