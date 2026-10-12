"""
ui_frontend.py
--------------
Sleek, minimalist, high-performance UI/UX dashboard & interactive developer workbench
for MediaPipe hand tracking, 3D coordinate spatial distance calculation, and gesture classification.

Features:
- Dark-mode aesthetic (#0f0f17 / #181825 / #11111b) with crisp typography & subtle borders.
- Left Sidebar: Interactive Gesture Catalog with search filter and status badges.
- Center Stage: High-performance 2D/3D Hand Landmark Diagram with interactive click-to-select nodes,
  glow highlights (#fab387), dashed measurement vectors, and coordinate labels.
- Right Panel: Continuous Euclidean Distance Gauge with pulse feedback and real-time telemetry.
- Developer Calibration Workbench (Editor Mode):
  * Node Inspector & dropdown selectors (e.g. Node 4 and Node 8)
  * Dynamic threshold sliders
  * Synthetic Data & Test Runner Simulator (verify state transitions without webcam)
  * Live JSON Config Exporter / Importer
- Collapsible Bottom Drawer: Plain-English usage guide & live timestamped event feed.
"""

from collections import deque
import json
import math
import time
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple
import numpy as np

try:
    import cv2
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


try:
    from member_3.member_3 import (
        GestureClassifier,
        GestureType,
        GESTURE_DICTIONARY,
        GestureDefinition,
    )
    from member_2.member_2 import HandLandmarksResult, LandmarkInference
    from member_4.member_4 import OSMacroController
except ImportError:
    from member_3 import (
        GestureClassifier,
        GestureType,
        GESTURE_DICTIONARY,
        GestureDefinition,
    )
    from member_2 import HandLandmarksResult, LandmarkInference
    from member_4 import OSMacroController


# =============================================================================
# THEME PALETTE & CONSTANTS
# =============================================================================
THEME = {
    "bg_root": "#0f0f17",        # Deep obsidian / charcoal
    "bg_card": "#181825",        # Panel card surface
    "bg_canvas": "#11111b",      # Deep canvas background
    "bg_surface": "#1e1e2e",     # Hover / elevated surface
    "bg_input": "#14141f",       # Textbox / search field
    "border": "#2b2c3d",         # Subtle 1px borders
    "border_focus": "#89b4fa",   # Focused border
    "text_main": "#cdd6f4",      # High contrast light text
    "text_muted": "#a6adc8",     # Secondary / label text
    "accent_blue": "#89b4fa",    # Electric Ice Blue
    "accent_green": "#a6e3a1",   # Neon Mint Green (Active / Triggered)
    "accent_gold": "#fab387",    # Warm Amber Glow (Key nodes)
    "accent_pink": "#f38ba8",    # Coral Red (Threshold line)
    "accent_cyan": "#94e2d5",    # Teal accent
}

NODE_NAMES = [
    "0: Wrist", "1: Thumb CMC", "2: Thumb MCP", "3: Thumb IP", "4: Thumb Tip",
    "5: Index MCP", "6: Index PIP", "7: Index DIP", "8: Index Tip",
    "9: Middle MCP", "10: Middle PIP", "11: Middle DIP", "12: Middle Tip",
    "13: Ring MCP", "14: Ring PIP", "15: Ring DIP", "16: Ring Tip",
    "17: Pinky MCP", "18: Pinky PIP", "19: Pinky DIP", "20: Pinky Tip",
]


# =============================================================================
# COMPONENT 1: HAND LANDMARK CANVAS & 3D NODE MAP
# =============================================================================
class HandLandmarkCanvas:
    """High-performance 2D/3D hand landmark visualizer with click-to-select node calibration."""

    CANONICAL_COORDS = [
        (0.50, 0.90),  # 0: Wrist
        (0.38, 0.78),  # 1: Thumb CMC
        (0.28, 0.66),  # 2: Thumb MCP
        (0.20, 0.54),  # 3: Thumb IP
        (0.14, 0.42),  # 4: Thumb Tip
        (0.38, 0.48),  # 5: Index MCP
        (0.34, 0.35),  # 6: Index PIP
        (0.31, 0.23),  # 7: Index DIP
        (0.28, 0.12),  # 8: Index Tip
        (0.50, 0.46),  # 9: Middle MCP
        (0.50, 0.31),  # 10: Middle PIP
        (0.50, 0.19),  # 11: Middle DIP
        (0.50, 0.08),  # 12: Middle Tip
        (0.62, 0.48),  # 13: Ring MCP
        (0.66, 0.35),  # 14: Ring PIP
        (0.69, 0.23),  # 15: Ring DIP
        (0.71, 0.12),  # 16: Ring Tip
        (0.74, 0.52),  # 17: Pinky MCP
        (0.79, 0.42),  # 18: Pinky PIP
        (0.82, 0.32),  # 19: Pinky DIP
        (0.85, 0.22),  # 20: Pinky Tip
    ]

    CONNECTIONS = LandmarkInference.HAND_CONNECTIONS

    def __init__(
        self,
        parent: tk.Widget,
        width: int = 520,
        height: int = 440,
        on_node_clicked: Optional[Callable[[int], None]] = None,
    ) -> None:
        self.width = width
        self.height = height
        self.on_node_clicked = on_node_clicked

        self.canvas = tk.Canvas(
            parent,
            width=self.width,
            height=self.height,
            bg=THEME["bg_canvas"],
            highlightthickness=1,
            highlightbackground=THEME["border"],
        )
        self.canvas.pack(fill="both", expand=True)

        self.highlight_nodes: List[int] = [4, 8]
        self.selected_node_a: int = 4
        self.selected_node_b: int = 8
        self.is_pinching: bool = False
        self.current_distance: float = 0.0
        self.camera_feed_active: bool = False
        self.show_camera_feed: bool = True
        self.node_pixel_cache: List[Tuple[float, float]] = []
        self._photo_image: Optional[Any] = None
        self.latest_frame: Optional[Any] = None

        self.canvas.bind("<Button-1>", self._handle_click)

    def _handle_click(self, event: tk.Event) -> None:
        """Detect if the user clicked directly on any of the 21 MediaPipe nodes."""
        if not self.node_pixel_cache:
            return

        click_x, click_y = event.x, event.y
        closest_node = -1
        min_dist = float("inf")

        for idx, (px, py) in enumerate(self.node_pixel_cache):
            dist = math.hypot(click_x - px, click_y - py)
            if dist < min_dist and dist <= 20:  # 20px radius hit zone
                min_dist = dist
                closest_node = idx

        if closest_node != -1 and self.on_node_clicked:
            self.on_node_clicked(closest_node)

    def render(
        self,
        landmarks: Optional[List[Tuple[float, float, float]]] = None,
        highlight_nodes: Optional[List[int]] = None,
        node_a: int = 4,
        node_b: int = 8,
        distance: float = 0.0,
        is_pinching: bool = False,
        frame: Optional[Any] = None,
    ) -> None:
        """Render either the merged live camera video stream or 21-node wireframe."""
        if frame is not None:
            self.latest_frame = frame

        self.highlight_nodes = highlight_nodes or [node_a, node_b]
        self.selected_node_a = node_a
        self.selected_node_b = node_b
        self.current_distance = distance
        self.is_pinching = is_pinching

        w = self.canvas.winfo_width() or self.width
        h = self.canvas.winfo_height() or self.height
        if w < 50:
            w = self.width
        if h < 50:
            h = self.height

        # --- MODE 1: LIVE CAMERA VIDEO FEED WITH OS CONTENT & HUD ---
        if self.show_camera_feed and self.latest_frame is not None and HAS_PIL:
            try:
                if isinstance(self.latest_frame, np.ndarray):
                    rgb_frame = cv2.cvtColor(self.latest_frame, cv2.COLOR_BGR2RGB)
                else:
                    rgb_frame = self.latest_frame

                fh, fw = rgb_frame.shape[:2]
                scale = min(w / fw, h / fh)
                new_w = max(1, int(fw * scale))
                new_h = max(1, int(fh * scale))

                resized = cv2.resize(rgb_frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                pil_img = Image.fromarray(resized)
                self._photo_image = ImageTk.PhotoImage(image=pil_img, master=self.canvas)

                self.canvas.delete("all")
                self.canvas.create_image(w // 2, h // 2, image=self._photo_image)
                self.canvas.image = self._photo_image
                self.camera_feed_active = True

                # Compute interactive hit zones on the camera feed for node calibration
                offset_x = (w - new_w) // 2
                offset_y = (h - new_h) // 2
                coords: List[Tuple[float, float]] = []
                if landmarks and len(landmarks) == 21:
                    for pt in landmarks:
                        px = offset_x + pt[0] * new_w
                        py = offset_y + pt[1] * new_h
                        coords.append((px, py))
                    self.node_pixel_cache = coords
                else:
                    self.node_pixel_cache = []

                # Subtle live status tag
                self.canvas.create_text(
                    15, h - 16,
                    anchor="w",
                    text="● LIVE CAMERA FEED + OS HUD",
                    fill=THEME["accent_green"],
                    font=("Segoe UI", 8, "bold"),
                )
                return
            except Exception:
                pass  # Fall back to wireframe rendering

        # --- MODE 2: 3D SCHEMATIC SKELETON WIREFRAME ---
        self.canvas.delete("all")
        self._photo_image = None
        pad_x, pad_y = 35, 35

        # Draw subtle grid dots
        for gx in range(20, w, 40):
            for gy in range(20, h, 40):
                self.canvas.create_oval(gx, gy, gx + 2, gy + 2, fill="#1c1c2a", outline="")

        # Compute pixel coordinates
        coords: List[Tuple[float, float]] = []
        if landmarks and len(landmarks) == 21:
            self.camera_feed_active = True
            for pt in landmarks:
                # Direct X orientation matching mirrored camera feed
                px = pad_x + pt[0] * (w - 2 * pad_x)
                py = pad_y + pt[1] * (h - 2 * pad_y)
                coords.append((px, py))
        else:
            self.camera_feed_active = False
            for pt in self.CANONICAL_COORDS:
                px = pad_x + pt[0] * (w - 2 * pad_x)
                py = pad_y + pt[1] * (h - 2 * pad_y)
                coords.append((px, py))

        self.node_pixel_cache = coords

        # Draw connecting bones
        for start_idx, end_idx in self.CONNECTIONS:
            p1 = coords[start_idx]
            p2 = coords[end_idx]
            if start_idx in self.highlight_nodes and end_idx in self.highlight_nodes:
                line_color = THEME["accent_gold"]
                width = 3
            elif start_idx in self.highlight_nodes or end_idx in self.highlight_nodes:
                line_color = THEME["accent_blue"]
                width = 2
            else:
                line_color = "#2b2c3d"
                width = 1.5
            self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill=line_color, width=width)

        # Draw dashed measurement vector between tracked Node A and Node B
        if node_a < len(coords) and node_b < len(coords):
            pa = coords[node_a]
            pb = coords[node_b]
            vec_color = THEME["accent_green"] if is_pinching else THEME["accent_pink"]
            self.canvas.create_line(
                pa[0], pa[1], pb[0], pb[1],
                fill=vec_color,
                width=2.5,
                dash=(4, 3),
            )
            mid_x = (pa[0] + pb[0]) / 2
            mid_y = (pa[1] + pb[1]) / 2
            self.canvas.create_rectangle(
                mid_x - 32, mid_y - 10, mid_x + 32, mid_y + 10,
                fill=THEME["bg_card"],
                outline=vec_color,
                width=1,
            )
            self.canvas.create_text(
                mid_x, mid_y,
                text=f"d={distance:.3f}",
                fill=vec_color,
                font=("Consolas", 8, "bold"),
            )

        # Draw 21 landmark joint nodes
        for idx, (px, py) in enumerate(coords):
            is_active_node = (idx == node_a or idx == node_b)
            is_gesture_node = idx in self.highlight_nodes

            if is_active_node:
                halo_color = THEME["accent_green"] if is_pinching else THEME["accent_gold"]
                self.canvas.create_oval(
                    px - 14, py - 14, px + 14, py + 14,
                    fill="",
                    outline=halo_color,
                    width=1.5,
                )
                self.canvas.create_oval(
                    px - 9, py - 9, px + 9, py + 9,
                    fill=halo_color,
                    outline="#ffffff",
                    width=1.5,
                )
                self.canvas.create_text(
                    px, py,
                    text=str(idx),
                    fill="#11111b",
                    font=("Segoe UI", 8, "bold"),
                )
            elif is_gesture_node:
                self.canvas.create_oval(
                    px - 7, py - 7, px + 7, py + 7,
                    fill=THEME["accent_blue"],
                    outline="#ffffff",
                    width=1,
                )
                self.canvas.create_text(
                    px, py,
                    text=str(idx),
                    fill="#11111b",
                    font=("Segoe UI", 7, "bold"),
                )
            else:
                self.canvas.create_oval(
                    px - 4, py - 4, px + 4, py + 4,
                    fill="#2a2b3d",
                    outline="#45475a",
                    width=1,
                )

        # Mode watermark in corner
        src_label = "● LIVE WEBCAM FEED (WIREFRAME)" if self.camera_feed_active else "○ SCHEMATIC 3D MODEL"
        src_color = THEME["accent_green"] if self.camera_feed_active else THEME["text_muted"]
        self.canvas.create_text(
            15, h - 15,
            anchor="w",
            text=src_label,
            fill=src_color,
            font=("Segoe UI", 8, "bold"),
        )


# =============================================================================
# COMPONENT 2: CONTINUOUS EUCLIDEAN DISTANCE GAUGE
# =============================================================================
class ContinuousDistanceGauge:
    """Visual progress meter rendering continuous Euclidean distance with threshold marker."""

    def __init__(self, parent: tk.Widget, width: int = 320, height: int = 24) -> None:
        self.width = width
        self.height = height

        self.canvas = tk.Canvas(
            parent,
            width=self.width,
            height=self.height,
            bg=THEME["bg_canvas"],
            highlightthickness=1,
            highlightbackground=THEME["border"],
        )
        self.canvas.pack(fill="x", pady=4)

        self.max_scale: float = 0.20
        self.current_dist: float = 0.0
        self.threshold: float = 0.06
        self.is_pinching: bool = False

    def update_gauge(self, distance: float, threshold: float, is_pinching: bool) -> None:
        """Redraw distance bar and threshold line."""
        self.canvas.delete("all")
        self.current_dist = distance
        self.threshold = threshold
        self.is_pinching = is_pinching

        w = self.canvas.winfo_width() or self.width
        h = self.height

        # Fill background bar
        clamped_dist = min(distance, self.max_scale)
        bar_w = int((clamped_dist / self.max_scale) * w)

        fill_color = THEME["accent_green"] if is_pinching else THEME["accent_blue"]
        if bar_w > 0:
            self.canvas.create_rectangle(0, 0, bar_w, h, fill=fill_color, outline="")

        # Draw threshold limit vertical marker line
        thresh_x = int((threshold / self.max_scale) * w)
        self.canvas.create_line(thresh_x, 0, thresh_x, h, fill=THEME["accent_pink"], width=2.5)

        # Text readout
        text_pos_x = bar_w + 35 if bar_w + 70 < w else max(bar_w - 40, 40)
        self.canvas.create_text(
            text_pos_x, h // 2,
            text=f"{distance:.3f}",
            fill=THEME["text_main"],
            font=("Consolas", 8, "bold"),
        )
        self.canvas.create_text(
            thresh_x - 30 if thresh_x > 60 else thresh_x + 30,
            h // 2,
            text=f"limit {threshold:.3f}",
            fill=THEME["accent_pink"],
            font=("Segoe UI", 7, "bold"),
        )


# =============================================================================
# MAIN ORCHESTRATOR: GESTURE CONTROLLER UI
# =============================================================================
class GestureControllerUI:
    """Sleek, minimalist dashboard and integrated developer calibration workbench."""

    def __init__(
        self,
        classifier: GestureClassifier,
        macro_controller: OSMacroController,
        on_sensitivity_change: Optional[Callable[[Dict[str, float]], None]] = None,
    ) -> None:
        self.classifier = classifier
        self.macro_controller = macro_controller
        self.on_sensitivity_change = on_sensitivity_change

        self.root = tk.Tk()
        self.root.title("Gesture Studio Pro - Calibration & Telemetry Workbench")
        self.root.geometry("1180x820")
        self.root.minsize(1024, 720)
        self.root.configure(bg=THEME["bg_root"])

        # State Variables
        self.is_running: bool = True
        self.editor_mode_active: bool = False
        self.selected_gesture_type: GestureType = GestureType.PINCH
        self.selected_node_a: int = 4
        self.selected_node_b: int = 8
        self.latest_hand_landmarks: Optional[List[Tuple[float, float, float]]] = None
        self.latest_pinch_dist: float = 0.0
        self.latest_is_pinching: bool = False
        self.latest_frame: Optional[Any] = None
        self.event_log_queue: Deque[str] = deque(maxlen=20)
        self.simulation_active: bool = False

        self._configure_styles()
        self._build_top_navbar()
        self._build_main_grid()
        self._build_bottom_drawer()

        # Window protocols & key bindings
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Key-m>", lambda e: self._toggle_air_mouse())
        self.root.bind("<Key-M>", lambda e: self._toggle_air_mouse())
        self.root.bind("<Key-k>", lambda e: self._toggle_air_keyboard())
        self.root.bind("<Key-K>", lambda e: self._toggle_air_keyboard())
        self.root.bind("<Key-v>", lambda e: self._toggle_view_mode())
        self.root.bind("<Key-V>", lambda e: self._toggle_view_mode())
        self.root.bind("<Key-q>", lambda e: self._on_close())
        self.root.bind("<Key-Q>", lambda e: self._on_close())
        self.root.bind("<Escape>", lambda e: self._on_close())

        # Sync air-mouse and air-keyboard button states with controller
        self._update_air_mouse_button()
        self._update_air_keyboard_button()

        # Initial selection setup
        self._select_gesture(GestureType.PINCH)

    def _configure_styles(self) -> None:
        """Apply modern dark theme styling to standard ttk widgets."""
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure(".", background=THEME["bg_root"], foreground=THEME["text_main"], font=("Segoe UI", 10))
        style.configure("Card.TFrame", background=THEME["bg_card"], relief="flat")
        style.configure("Surface.TFrame", background=THEME["bg_surface"], relief="flat")
        style.configure("Header.TLabel", font=("Segoe UI", 13, "bold"), foreground=THEME["accent_blue"], background=THEME["bg_card"])
        style.configure("SubHeader.TLabel", font=("Segoe UI", 10, "bold"), foreground=THEME["text_main"], background=THEME["bg_card"])
        style.configure("Muted.TLabel", font=("Segoe UI", 9), foreground=THEME["text_muted"], background=THEME["bg_card"])
        style.configure("Value.TLabel", font=("Segoe UI", 10, "bold"), foreground=THEME["accent_green"], background=THEME["bg_card"])
        style.configure("BadgeActive.TLabel", font=("Segoe UI", 8, "bold"), background=THEME["accent_green"], foreground="#11111b")
        style.configure("BadgeIdle.TLabel", font=("Segoe UI", 8, "bold"), background="#2b2c3d", foreground=THEME["text_muted"])

        style.configure("Action.TButton", font=("Segoe UI", 9, "bold"), background=THEME["accent_blue"], foreground="#11111b", borderwidth=0)
        style.configure("ToggleActive.TButton", font=("Segoe UI", 9, "bold"), background=THEME["accent_green"], foreground="#11111b")
        style.configure("ToggleIdle.TButton", font=("Segoe UI", 9), background=THEME["bg_surface"], foreground=THEME["text_main"])

    # -------------------------------------------------------------------------
    # TOP NAVIGATION BAR
    # -------------------------------------------------------------------------
    def _build_top_navbar(self) -> None:
        """Top navigation bar with telemetry badges and Editor Mode toggle."""
        navbar = tk.Frame(self.root, bg=THEME["bg_card"], height=52, bd=0, highlightthickness=1, highlightbackground=THEME["border"])
        navbar.pack(fill="x", side="top")
        navbar.pack_propagate(False)

        # Left Branding
        left_box = tk.Frame(navbar, bg=THEME["bg_card"])
        left_box.pack(side="left", padx=16, fill="y")

        lbl_logo = tk.Label(left_box, text="🖐️ GESTURE STUDIO", font=("Segoe UI", 12, "bold"), fg=THEME["accent_blue"], bg=THEME["bg_card"])
        lbl_logo.pack(side="left")

        lbl_ver = tk.Label(left_box, text="v2.4 PRO", font=("Segoe UI", 8, "bold"), fg="#11111b", bg=THEME["accent_gold"], padx=5, pady=1)
        lbl_ver.pack(side="left", padx=(8, 0))

        # Center Telemetry Pills
        center_box = tk.Frame(navbar, bg=THEME["bg_card"])
        center_box.pack(side="left", expand=True, fill="y")

        self.pill_gesture = tk.Label(center_box, text="ACTIVE: NONE", font=("Segoe UI", 9, "bold"), fg=THEME["accent_cyan"], bg=THEME["bg_surface"], padx=10, pady=3)
        self.pill_gesture.pack(side="left", padx=6, pady=12)

        self.pill_context = tk.Label(center_box, text="CONTEXT: default", font=("Segoe UI", 9), fg=THEME["text_muted"], bg=THEME["bg_surface"], padx=10, pady=3)
        self.pill_context.pack(side="left", padx=6, pady=12)

        self.pill_fps = tk.Label(center_box, text="60.0 FPS", font=("Consolas", 9, "bold"), fg=THEME["accent_green"], bg=THEME["bg_surface"], padx=10, pady=3)
        self.pill_fps.pack(side="left", padx=6, pady=12)

        # Right Action Buttons
        right_box = tk.Frame(navbar, bg=THEME["bg_card"])
        right_box.pack(side="right", padx=16, fill="y")

        self.btn_editor_mode = tk.Button(
            right_box,
            text="🛠️ Editor Mode: OFF",
            font=("Segoe UI", 9, "bold"),
            bg=THEME["bg_surface"],
            fg=THEME["text_main"],
            activebackground=THEME["accent_blue"],
            activeforeground="#11111b",
            relief="flat",
            padx=12,
            pady=4,
            command=self._toggle_editor_mode,
        )
        self.btn_editor_mode.pack(side="right", pady=10)

    # -------------------------------------------------------------------------
    # MAIN GRID LAYOUT: 3-COLUMN FLEX SPLIT
    # -------------------------------------------------------------------------
    def _build_main_grid(self) -> None:
        """Build the 3-column split view (Catalog, Center Stage, Right Workbench)."""
        self.grid_container = tk.Frame(self.root, bg=THEME["bg_root"])
        self.grid_container.pack(fill="both", expand=True, padx=16, pady=(12, 6))

        # COLUMN 1: Left Sidebar (Gesture Catalog) - Width: ~280px
        self._build_catalog_sidebar(self.grid_container)

        # COLUMN 2: Center Stage (Hand Landmark Diagram & Live Canvas)
        self._build_center_stage(self.grid_container)

        # COLUMN 3: Right Panel (Distance Gauge & Calibration Workbench) - Width: ~340px
        self._build_right_panel(self.grid_container)

    # -------------------------------------------------------------------------
    # COLUMN 1: INTERACTIVE GESTURE CATALOG SIDEBAR
    # -------------------------------------------------------------------------
    def _build_catalog_sidebar(self, parent: tk.Widget) -> None:
        """Build left sidebar with search filter and pill-shaped gesture list."""
        sidebar = tk.Frame(parent, bg=THEME["bg_card"], width=270, highlightthickness=1, highlightbackground=THEME["border"])
        sidebar.pack(side="left", fill="y", padx=(0, 10))
        sidebar.pack_propagate(False)

        # Header
        hdr_box = tk.Frame(sidebar, bg=THEME["bg_card"])
        hdr_box.pack(fill="x", padx=12, pady=(12, 6))
        tk.Label(hdr_box, text="GESTURE CATALOG", font=("Segoe UI", 10, "bold"), fg=THEME["accent_blue"], bg=THEME["bg_card"]).pack(side="left")

        # Search filter box
        search_box = tk.Frame(sidebar, bg=THEME["bg_input"], highlightthickness=1, highlightbackground=THEME["border"])
        search_box.pack(fill="x", padx=12, pady=(0, 10))

        tk.Label(search_box, text="🔍", font=("Segoe UI", 9), fg=THEME["text_muted"], bg=THEME["bg_input"]).pack(side="left", padx=4)
        self.var_search = tk.StringVar()
        self.var_search.trace_add("write", self._on_search_query_changed)
        entry_search = tk.Entry(
            search_box,
            textvariable=self.var_search,
            font=("Segoe UI", 9),
            bg=THEME["bg_input"],
            fg=THEME["text_main"],
            insertbackground=THEME["accent_blue"],
            relief="flat",
        )
        entry_search.pack(side="left", fill="x", expand=True, padx=4, pady=4)

        # Scrollable gesture list container
        self.list_frame = tk.Frame(sidebar, bg=THEME["bg_card"])
        self.list_frame.pack(fill="both", expand=True, padx=8, pady=(0, 10))

        self.catalog_buttons: Dict[GestureType, tk.Button] = {}
        self._populate_catalog_list()

    def _populate_catalog_list(self, query: str = "") -> None:
        """Render pill-shaped gesture items into the catalog sidebar."""
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        self.catalog_buttons.clear()

        query_clean = query.strip().lower()

        for g_type, g_def in GESTURE_DICTIONARY.items():
            if query_clean and query_clean not in g_def.name.lower() and query_clean not in g_def.actionable_state.lower():
                continue

            is_selected = (g_type == self.selected_gesture_type)
            bg_col = THEME["bg_surface"] if is_selected else THEME["bg_card"]
            border_col = THEME["accent_blue"] if is_selected else THEME["border"]

            card_btn = tk.Button(
                self.list_frame,
                text=f"{g_def.icon}  {g_def.name}\n   ↳ {g_def.actionable_state}",
                justify="left",
                font=("Segoe UI", 9),
                bg=bg_col,
                fg=THEME["text_main"],
                activebackground=THEME["bg_surface"],
                activeforeground=THEME["accent_blue"],
                relief="flat",
                bd=0,
                padx=10,
                pady=6,
                highlightthickness=1,
                highlightbackground=border_col,
                command=lambda gt=g_type: self._select_gesture(gt),
            )
            card_btn.pack(fill="x", pady=3)
            self.catalog_buttons[g_type] = card_btn

    def _on_search_query_changed(self, *_args: Any) -> None:
        """Filter gesture catalog in real-time as user types."""
        self._populate_catalog_list(self.var_search.get())

    def _select_gesture(self, g_type: GestureType) -> None:
        """Select a gesture to inspect its 3D nodes, formulas, and calibration parameters."""
        self.selected_gesture_type = g_type
        g_def = GESTURE_DICTIONARY.get(g_type)
        if not g_def:
            return

        # Update button highlights
        for gt, btn in self.catalog_buttons.items():
            if gt == g_type:
                btn.config(bg=THEME["bg_surface"], highlightbackground=THEME["accent_blue"])
            else:
                btn.config(bg=THEME["bg_card"], highlightbackground=THEME["border"])

        # Update node selections
        if len(g_def.key_nodes) >= 2:
            self.selected_node_a = g_def.key_nodes[0]
            self.selected_node_b = g_def.key_nodes[1]
        elif len(g_def.key_nodes) == 1:
            self.selected_node_a = g_def.key_nodes[0]
            self.selected_node_b = 0  # Wrist comparison

        # Update dropdowns if workbench initialized
        if hasattr(self, "combo_node_a") and hasattr(self, "combo_node_b"):
            self.combo_node_a.current(min(self.selected_node_a, len(NODE_NAMES) - 1))
            self.combo_node_b.current(min(self.selected_node_b, len(NODE_NAMES) - 1))

        # Update Center Stage & Bottom Drawer
        self._update_center_stage_details(g_def)
        self._update_bottom_drawer_details(g_def)
        self._update_json_config_preview()

        # Redraw Hand Landmark Canvas
        self.hand_canvas.render(
            landmarks=self.latest_hand_landmarks,
            highlight_nodes=g_def.key_nodes,
            node_a=self.selected_node_a,
            node_b=self.selected_node_b,
            distance=self.latest_pinch_dist,
            is_pinching=self.latest_is_pinching,
        )

    # -------------------------------------------------------------------------
    # COLUMN 2: CENTER STAGE (EXPANDED CANVAS & HUD)
    # -------------------------------------------------------------------------
    def _build_center_stage(self, parent: tk.Widget) -> None:
        """Build center stage housing the Live Camera Feed and 2D/3D Hand Landmark Diagram."""
        center_panel = tk.Frame(parent, bg=THEME["bg_card"], highlightthickness=1, highlightbackground=THEME["border"])
        center_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Top Center Header
        top_hdr = tk.Frame(center_panel, bg=THEME["bg_card"])
        top_hdr.pack(fill="x", padx=14, pady=10)

        left_hdr = tk.Frame(top_hdr, bg=THEME["bg_card"])
        left_hdr.pack(side="left")

        self.lbl_stage_title = tk.Label(
            left_hdr,
            text="🤏 Index Pinch",
            font=("Segoe UI", 13, "bold"),
            fg=THEME["accent_blue"],
            bg=THEME["bg_card"],
        )
        self.lbl_stage_title.pack(side="left")

        self.lbl_stage_badge = tk.Label(
            left_hdr,
            text="ACTION: Mouse Left Click",
            font=("Segoe UI", 8, "bold"),
            fg=THEME["accent_gold"],
            bg=THEME["bg_surface"],
            padx=8,
            pady=3,
        )
        self.lbl_stage_badge.pack(side="left", padx=(10, 0))

        # Center Stage Controls: View Mode & Air-Mouse Toggles
        right_hdr = tk.Frame(top_hdr, bg=THEME["bg_card"])
        right_hdr.pack(side="right")

        self.btn_view_mode = tk.Button(
            right_hdr,
            text="📹 Camera Feed: ON",
            font=("Segoe UI", 8, "bold"),
            bg=THEME["bg_surface"],
            fg=THEME["accent_green"],
            activebackground=THEME["bg_canvas"],
            relief="flat",
            bd=0,
            padx=8,
            pady=3,
            highlightthickness=1,
            highlightbackground=THEME["accent_green"],
            command=self._toggle_view_mode,
        )
        self.btn_view_mode.pack(side="left", padx=3)

        self.btn_air_mouse = tk.Button(
            right_hdr,
            text="🖱️ Air-Mouse: OFF",
            font=("Segoe UI", 8, "bold"),
            bg=THEME["bg_surface"],
            fg=THEME["text_muted"],
            activebackground=THEME["bg_canvas"],
            relief="flat",
            bd=0,
            padx=8,
            pady=3,
            highlightthickness=1,
            highlightbackground=THEME["border"],
            command=self._toggle_air_mouse,
        )
        self.btn_air_mouse.pack(side="left", padx=3)

        self.btn_air_keyboard = tk.Button(
            right_hdr,
            text="⌨️ Air Keys: OFF",
            font=("Segoe UI", 8, "bold"),
            bg=THEME["bg_surface"],
            fg=THEME["text_muted"],
            activebackground=THEME["bg_canvas"],
            relief="flat",
            bd=0,
            padx=8,
            pady=3,
            highlightthickness=1,
            highlightbackground=THEME["border"],
            command=self._toggle_air_keyboard,
        )
        self.btn_air_keyboard.pack(side="left", padx=3)

        # Hand Canvas Component (Live Camera Video / 3D Landmark Wireframe)
        canvas_wrapper = tk.Frame(center_panel, bg=THEME["bg_canvas"])
        canvas_wrapper.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        self.hand_canvas = HandLandmarkCanvas(
            canvas_wrapper,
            width=540,
            height=460,
            on_node_clicked=self._on_canvas_node_clicked,
        )

        # Hotkey legend instruction
        tk.Label(
            center_panel,
            text="💡 Hotkeys: [M] Air-Mouse | [K] Air-Keyboard | [V] Camera/Wireframe | [Q/Esc] Exit | Click node in Editor to calibrate",
            font=("Segoe UI", 8, "italic"),
            fg=THEME["text_muted"],
            bg=THEME["bg_card"],
        ).pack(anchor="w", padx=14, pady=(0, 8))

    def _update_center_stage_details(self, g_def: GestureDefinition) -> None:
        """Update center stage title and action badge."""
        self.lbl_stage_title.config(text=f"{g_def.icon}  {g_def.name}")
        self.lbl_stage_badge.config(text=f"ACTION: {g_def.actionable_state}")

    def _on_canvas_node_clicked(self, node_idx: int) -> None:
        """Handle user clicking a node on the canvas."""
        if not self.editor_mode_active:
            # Inform user how to use click calibration
            self._log_event(f"Node {node_idx} ({NODE_NAMES[node_idx]}) clicked. Enable Editor Mode to calibrate.")
            return

        # Alternate selecting Node A and Node B
        if self.selected_node_a != node_idx:
            self.selected_node_b = node_idx
        else:
            self.selected_node_a = node_idx

        self.combo_node_a.current(self.selected_node_a)
        self.combo_node_b.current(self.selected_node_b)
        self._on_node_selector_changed()
        self._log_event(f"Calibration targets updated: Node {self.selected_node_a} <-> Node {self.selected_node_b}")

    # -------------------------------------------------------------------------
    # COLUMN 3: RIGHT PANEL (DISTANCE GAUGE & CALIBRATION WORKBENCH)
    # -------------------------------------------------------------------------
    def _build_right_panel(self, parent: tk.Widget) -> None:
        """Build right panel with Euclidean distance meter and developer tools."""
        right_panel = tk.Frame(parent, bg=THEME["bg_card"], width=340, highlightthickness=1, highlightbackground=THEME["border"])
        right_panel.pack(side="right", fill="both", expand=False)
        right_panel.pack_propagate(False)

        # 1. Telemetry & Continuous Euclidean Distance Gauge
        gauge_box = tk.Frame(right_panel, bg=THEME["bg_card"])
        gauge_box.pack(fill="x", padx=14, pady=(12, 8))

        tk.Label(gauge_box, text="CONTINUOUS EUCLIDEAN GAUGE", font=("Segoe UI", 9, "bold"), fg=THEME["accent_blue"], bg=THEME["bg_card"]).pack(anchor="w")

        # The Distance Gauge Canvas
        self.gauge = ContinuousDistanceGauge(gauge_box, width=310, height=22)

        # Numeric readout row
        metric_row = tk.Frame(gauge_box, bg=THEME["bg_card"])
        metric_row.pack(fill="x", pady=(4, 0))

        tk.Label(metric_row, text="Live Normalized d:", font=("Segoe UI", 9), fg=THEME["text_muted"], bg=THEME["bg_card"]).pack(side="left")
        self.lbl_live_distance = tk.Label(metric_row, text="0.000", font=("Consolas", 10, "bold"), fg=THEME["accent_green"], bg=THEME["bg_card"])
        self.lbl_live_distance.pack(side="left", padx=(4, 0))

        self.lbl_gauge_state = tk.Label(metric_row, text="IDLE", font=("Segoe UI", 8, "bold"), fg=THEME["text_muted"], bg=THEME["bg_surface"], padx=6, pady=1)
        self.lbl_gauge_state.pack(side="right")

        # Separator line
        tk.Frame(right_panel, height=1, bg=THEME["border"]).pack(fill="x", padx=14, pady=8)

        # 2. Dedicated Editor & Developer Calibration Workbench
        self.workbench_box = tk.Frame(right_panel, bg=THEME["bg_card"])
        self.workbench_box.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        self._build_editor_workbench(self.workbench_box)

    def _build_editor_workbench(self, parent: tk.Widget) -> None:
        """Construct the integrated developer calibration tools inside right panel."""
        tk.Label(parent, text="CALIBRATION WORKBENCH", font=("Segoe UI", 9, "bold"), fg=THEME["accent_gold"], bg=THEME["bg_card"]).pack(anchor="w", pady=(0, 6))

        # A. Node Selector Dropdowns
        node_grid = tk.Frame(parent, bg=THEME["bg_card"])
        node_grid.pack(fill="x", pady=2)

        tk.Label(node_grid, text="Node A:", font=("Segoe UI", 8, "bold"), fg=THEME["text_muted"], bg=THEME["bg_card"]).grid(row=0, column=0, sticky="w")
        self.combo_node_a = ttk.Combobox(node_grid, values=NODE_NAMES, state="readonly", width=14, font=("Segoe UI", 8))
        self.combo_node_a.current(4)
        self.combo_node_a.grid(row=0, column=1, padx=(4, 8), pady=2)
        self.combo_node_a.bind("<<ComboboxSelected>>", self._on_node_selector_changed)

        tk.Label(node_grid, text="Node B:", font=("Segoe UI", 8, "bold"), fg=THEME["text_muted"], bg=THEME["bg_card"]).grid(row=1, column=0, sticky="w")
        self.combo_node_b = ttk.Combobox(node_grid, values=NODE_NAMES, state="readonly", width=14, font=("Segoe UI", 8))
        self.combo_node_b.current(8)
        self.combo_node_b.grid(row=1, column=1, padx=(4, 8), pady=2)
        self.combo_node_b.bind("<<ComboboxSelected>>", self._on_node_selector_changed)

        # B. Real-Time Threshold Sliders
        thresh_frame = tk.Frame(parent, bg=THEME["bg_card"])
        thresh_frame.pack(fill="x", pady=6)

        # Pinch Threshold Slider
        row_p = tk.Frame(thresh_frame, bg=THEME["bg_card"])
        row_p.pack(fill="x", pady=2)
        tk.Label(row_p, text="Pinch Threshold:", font=("Segoe UI", 8), fg=THEME["text_muted"], bg=THEME["bg_card"]).pack(side="left")
        self.lbl_slider_pinch = tk.Label(row_p, text=f"{self.classifier.pinch_threshold:.3f}", font=("Consolas", 8, "bold"), fg=THEME["accent_green"], bg=THEME["bg_card"])
        self.lbl_slider_pinch.pack(side="right")

        self.scale_pinch = ttk.Scale(
            thresh_frame,
            from_=0.02,
            to=0.15,
            value=self.classifier.pinch_threshold,
            command=self._on_threshold_slider_moved,
        )
        self.scale_pinch.pack(fill="x")

        # Swipe Threshold Slider
        row_s = tk.Frame(thresh_frame, bg=THEME["bg_card"])
        row_s.pack(fill="x", pady=(4, 2))
        tk.Label(row_s, text="Swipe Threshold:", font=("Segoe UI", 8), fg=THEME["text_muted"], bg=THEME["bg_card"]).pack(side="left")
        self.lbl_slider_swipe = tk.Label(row_s, text=f"{self.classifier.swipe_threshold:.3f}", font=("Consolas", 8, "bold"), fg=THEME["accent_green"], bg=THEME["bg_card"])
        self.lbl_slider_swipe.pack(side="right")

        self.scale_swipe = ttk.Scale(
            thresh_frame,
            from_=0.05,
            to=0.30,
            value=self.classifier.swipe_threshold,
            command=self._on_threshold_slider_moved,
        )
        self.scale_swipe.pack(fill="x")

        # C. Synthetic Data & Test Runner Simulator
        sim_frame = tk.Frame(parent, bg=THEME["bg_card"])
        sim_frame.pack(fill="x", pady=6)

        tk.Label(sim_frame, text="TEST RUNNER SIMULATOR", font=("Segoe UI", 8, "bold"), fg=THEME["accent_blue"], bg=THEME["bg_card"]).pack(anchor="w", pady=(0, 4))

        btn_row1 = tk.Frame(sim_frame, bg=THEME["bg_card"])
        btn_row1.pack(fill="x", pady=2)
        tk.Button(
            btn_row1,
            text="Sim Open Hand (0.35)",
            font=("Segoe UI", 8),
            bg=THEME["bg_surface"],
            fg=THEME["text_main"],
            relief="flat",
            command=lambda: self._simulate_hand_state(pinch_dist=0.35, is_pinch=False),
        ).pack(side="left", expand=True, fill="x", padx=(0, 2))

        tk.Button(
            btn_row1,
            text="Sim Pinch (0.03)",
            font=("Segoe UI", 8, "bold"),
            bg=THEME["bg_surface"],
            fg=THEME["accent_green"],
            relief="flat",
            command=lambda: self._simulate_hand_state(pinch_dist=0.03, is_pinch=True),
        ).pack(side="right", expand=True, fill="x", padx=(2, 0))

        btn_row2 = tk.Frame(sim_frame, bg=THEME["bg_card"])
        btn_row2.pack(fill="x", pady=2)
        tk.Button(
            btn_row2,
            text="Sim Swipe Right",
            font=("Segoe UI", 8),
            bg=THEME["bg_surface"],
            fg=THEME["accent_cyan"],
            relief="flat",
            command=lambda: self._simulate_swipe(GestureType.SWIPE_RIGHT),
        ).pack(side="left", expand=True, fill="x", padx=(0, 2))

        tk.Button(
            btn_row2,
            text="Reset to Live Camera",
            font=("Segoe UI", 8),
            bg=THEME["bg_surface"],
            fg=THEME["accent_pink"],
            relief="flat",
            command=self._reset_simulation,
        ).pack(side="right", expand=True, fill="x", padx=(2, 0))

        # D. Config Exporter / Importer (Live JSON preview)
        tk.Label(parent, text="CONFIG REGISTRY EXPORT (JSON)", font=("Segoe UI", 8, "bold"), fg=THEME["text_muted"], bg=THEME["bg_card"]).pack(anchor="w", pady=(6, 2))

        self.txt_config = tk.Text(
            parent,
            height=4,
            bg=THEME["bg_input"],
            fg="#a6e3a1",
            font=("Consolas", 7),
            relief="flat",
            highlightthickness=1,
            highlightbackground=THEME["border"],
        )
        self.txt_config.pack(fill="x", pady=(0, 4))

        tk.Button(
            parent,
            text="📋 Copy Calibrated Config",
            font=("Segoe UI", 8),
            bg=THEME["bg_surface"],
            fg=THEME["accent_blue"],
            relief="flat",
            command=self._copy_config_to_clipboard,
        ).pack(fill="x")

    def _on_node_selector_changed(self, _=None) -> None:
        """Handle dropdown selection change for tracked nodes."""
        self.selected_node_a = self.combo_node_a.current()
        self.selected_node_b = self.combo_node_b.current()
        self.hand_canvas.render(
            landmarks=self.latest_hand_landmarks,
            highlight_nodes=[self.selected_node_a, self.selected_node_b],
            node_a=self.selected_node_a,
            node_b=self.selected_node_b,
            distance=self.latest_pinch_dist,
            is_pinching=self.latest_is_pinching,
        )
        self._update_json_config_preview()

    def _on_threshold_slider_moved(self, _=None) -> None:
        """Synchronize threshold slider movements in real-time."""
        p_val = self.scale_pinch.get()
        s_val = self.scale_swipe.get()

        self.lbl_slider_pinch.config(text=f"{p_val:.3f}")
        self.lbl_slider_swipe.config(text=f"{s_val:.3f}")

        self.classifier.pinch_threshold = p_val
        self.classifier.swipe_threshold = s_val

        self.gauge.update_gauge(self.latest_pinch_dist, p_val, self.latest_is_pinching)
        self._update_json_config_preview()

        if self.on_sensitivity_change:
            self.on_sensitivity_change({"pinch": p_val, "swipe": s_val})

    def _simulate_hand_state(self, pinch_dist: float, is_pinch: bool) -> None:
        """Simulate synthetic hand data to test threshold transitions and UI responsiveness."""
        self.simulation_active = True
        self.latest_pinch_dist = pinch_dist
        self.latest_is_pinching = is_pinch

        # Build synthetic landmarks
        syn_lm = [pt for pt in HandLandmarkCanvas.CANONICAL_COORDS]
        if is_pinch:
            # Move thumb tip close to index tip
            syn_lm[4] = (syn_lm[8][0] - 0.02, syn_lm[8][1] + 0.02)

        self.latest_hand_landmarks = [(x, y, 0.0) for (x, y) in syn_lm]

        gesture = GestureType.PINCH if is_pinch else GestureType.NONE
        self._update_telemetry_ui(gesture, "simulator", pinch_dist, is_pinch)
        self._log_event(f"🧪 SIMULATOR: Set distance={pinch_dist:.3f} | is_pinching={is_pinch}")

    def _simulate_swipe(self, swipe_type: GestureType) -> None:
        """Simulate dynamic swipe motion in the UI."""
        self.simulation_active = True
        self._update_telemetry_ui(swipe_type, "simulator", 0.15, False)
        self._log_event(f"🧪 SIMULATOR: Triggered {swipe_type.name}")

    def _reset_simulation(self) -> None:
        """Reset simulator state back to live camera feed."""
        self.simulation_active = False
        self.latest_hand_landmarks = None
        self._log_event("🔄 Reset simulator. Waiting for live camera frames.")

    def _update_json_config_preview(self) -> None:
        """Update live JSON export text box with current parameters."""
        config_dict = {
            "gesture": self.selected_gesture_type.name,
            "tracked_nodes": [self.selected_node_a, self.selected_node_b],
            "pinch_threshold": round(self.classifier.pinch_threshold, 4),
            "swipe_threshold": round(self.classifier.swipe_threshold, 4),
            "gesture_cooldown": round(self.classifier.gesture_cooldown, 3),
        }
        json_str = json.dumps(config_dict, indent=2)
        self.txt_config.delete("1.0", "end")
        self.txt_config.insert("end", json_str)

    def _copy_config_to_clipboard(self) -> None:
        """Copy active config JSON to system clipboard."""
        text = self.txt_config.get("1.0", "end-1c")
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self._log_event("📋 Configuration copied to clipboard!")

    # -------------------------------------------------------------------------
    # BOTTOM DRAWER: USAGE GUIDE & LIVE TELEMETRY FEED
    # -------------------------------------------------------------------------
    def _build_bottom_drawer(self) -> None:
        """Build collapsible bottom drawer with usage instructions and event log."""
        self.drawer_frame = tk.Frame(self.root, bg=THEME["bg_card"], height=130, highlightthickness=1, highlightbackground=THEME["border"])
        self.drawer_frame.pack(fill="x", side="bottom", padx=16, pady=(0, 10))
        self.drawer_frame.pack_propagate(False)

        # Drawer Header with toggle
        hdr_row = tk.Frame(self.drawer_frame, bg=THEME["bg_card"])
        hdr_row.pack(fill="x", padx=12, pady=(6, 4))

        tk.Label(hdr_row, text="USAGE GUIDE & LIVE EVENT FEED", font=("Segoe UI", 9, "bold"), fg=THEME["accent_blue"], bg=THEME["bg_card"]).pack(side="left")

        # Two columns: Left (Instructions & Math formula), Right (Event log)
        body_row = tk.Frame(self.drawer_frame, bg=THEME["bg_card"])
        body_row.pack(fill="both", expand=True, padx=12, pady=(0, 6))

        # Instructions Box (Left)
        inst_col = tk.Frame(body_row, bg=THEME["bg_surface"], width=520, highlightthickness=1, highlightbackground=THEME["border"])
        inst_col.pack(side="left", fill="both", expand=True, padx=(0, 8))
        inst_col.pack_propagate(False)

        self.lbl_drawer_formula = tk.Label(inst_col, text="Formula: -", font=("Consolas", 8, "bold"), fg=THEME["accent_green"], bg=THEME["bg_surface"], anchor="w")
        self.lbl_drawer_formula.pack(fill="x", padx=8, pady=(4, 2))

        self.lbl_drawer_instructions = tk.Label(
            inst_col,
            text="Instructions: -",
            font=("Segoe UI", 8),
            fg=THEME["text_main"],
            bg=THEME["bg_surface"],
            wraplength=500,
            justify="left",
            anchor="w",
        )
        self.lbl_drawer_instructions.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        # Event Log Feed (Right)
        log_col = tk.Frame(body_row, bg=THEME["bg_input"], width=460, highlightthickness=1, highlightbackground=THEME["border"])
        log_col.pack(side="right", fill="both", expand=True)
        log_col.pack_propagate(False)

        self.txt_event_log = tk.Text(
            log_col,
            bg=THEME["bg_input"],
            fg=THEME["text_muted"],
            font=("Consolas", 8),
            relief="flat",
            wrap="word",
        )
        self.txt_event_log.pack(fill="both", expand=True, padx=6, pady=4)
        self._log_event("System initialized. Awaiting hand gesture telemetry...")

    def _update_bottom_drawer_details(self, g_def: GestureDefinition) -> None:
        """Update instructions and mathematical formula in the bottom drawer."""
        self.lbl_drawer_formula.config(text=f"Formula: {g_def.mathematical_formula}  [{g_def.rule_summary}]")
        self.lbl_drawer_instructions.config(text=f"How to perform: {g_def.instructions}\nDescription: {g_def.description}")

    def _log_event(self, message: str) -> None:
        """Append timestamped telemetry log to the event drawer."""
        ts = time.strftime("%H:%M:%S")
        entry = f"[{ts}] {message}"
        self.event_log_queue.append(entry)
        self.txt_event_log.delete("1.0", "end")
        self.txt_event_log.insert("end", "\n".join(self.event_log_queue))
        self.txt_event_log.see("end")

    # -------------------------------------------------------------------------
    # VIEW MODE & AIR-MOUSE TOGGLES
    # -------------------------------------------------------------------------
    def _toggle_view_mode(self) -> None:
        """Toggle between Live Camera Feed + OS HUD and 3D Schematic Wireframe."""
        self.hand_canvas.show_camera_feed = not self.hand_canvas.show_camera_feed
        if self.hand_canvas.show_camera_feed:
            self.btn_view_mode.config(
                text="📹 Camera Feed: ON",
                fg=THEME["accent_green"],
                highlightbackground=THEME["accent_green"],
            )
            self._log_event("Display switched to Live Camera Feed + OS HUD.")
        else:
            self.btn_view_mode.config(
                text="📐 Wireframe Mode",
                fg=THEME["accent_blue"],
                highlightbackground=THEME["accent_blue"],
            )
            self._log_event("Display switched to 3D Schematic Wireframe.")

        # Immediately refresh canvas
        g_def = GESTURE_DICTIONARY.get(self.selected_gesture_type)
        active_nodes = g_def.key_nodes if g_def else [self.selected_node_a, self.selected_node_b]
        self.hand_canvas.render(
            landmarks=self.latest_hand_landmarks,
            highlight_nodes=active_nodes,
            node_a=self.selected_node_a,
            node_b=self.selected_node_b,
            distance=self.latest_pinch_dist,
            is_pinching=self.latest_is_pinching,
        )

    def _toggle_air_mouse(self) -> None:
        """Toggle touchless air-mouse tracking on/off."""
        if not self.macro_controller:
            return
        self.macro_controller.mouse_tracking_enabled = not self.macro_controller.mouse_tracking_enabled
        self._update_air_mouse_button()
        status_str = "ENABLED" if self.macro_controller.mouse_tracking_enabled else "DISABLED"
        self._log_event(f"🖱️ Touchless Air-Mouse mode: {status_str}")

    def _update_air_mouse_button(self) -> None:
        """Update air-mouse button visual appearance."""
        if not hasattr(self, "btn_air_mouse") or not self.macro_controller:
            return
        is_on = getattr(self.macro_controller, "mouse_tracking_enabled", False)
        if is_on:
            self.btn_air_mouse.config(
                text="🖱️ Air-Mouse: ON",
                fg=THEME["accent_green"],
                highlightbackground=THEME["accent_green"],
            )
        else:
            self.btn_air_mouse.config(
                text="🖱️ Air-Mouse: OFF",
                fg=THEME["text_muted"],
                highlightbackground=THEME["border"],
            )

    def _toggle_air_keyboard(self) -> None:
        """Toggle touchless in-air virtual shortcut keyboard."""
        if not self.macro_controller:
            return
        self.macro_controller.air_keyboard_enabled = not self.macro_controller.air_keyboard_enabled
        self._update_air_keyboard_button()
        status_str = "ENABLED" if self.macro_controller.air_keyboard_enabled else "DISABLED"
        self._log_event(f"⌨️ Touchless Air-Keyboard: {status_str}")

    def _update_air_keyboard_button(self) -> None:
        """Update visual state of Air Keyboard button."""
        if not hasattr(self, "btn_air_keyboard") or not self.macro_controller:
            return
        is_on = getattr(self.macro_controller, "air_keyboard_enabled", False)
        if is_on:
            self.btn_air_keyboard.config(
                text="⌨️ Air Keys: ON",
                fg=THEME["accent_green"],
                highlightbackground=THEME["accent_green"],
            )
        else:
            self.btn_air_keyboard.config(
                text="⌨️ Air Keys: OFF",
                fg=THEME["text_muted"],
                highlightbackground=THEME["border"],
            )

    def _on_close(self) -> None:
        """Clean shutdown handler when window is closed or Esc/Q is pressed."""
        self.is_running = False
        try:
            self.root.destroy()
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # EDITOR MODE TOGGLE
    # -------------------------------------------------------------------------
    def _toggle_editor_mode(self) -> None:
        """Toggle developer calibration workbench mode."""
        self.editor_mode_active = not self.editor_mode_active
        if self.editor_mode_active:
            self.btn_editor_mode.config(
                text="🛠️ Editor Mode: ON",
                bg=THEME["accent_gold"],
                fg="#11111b",
            )
            self._log_event("Developer Editor Mode enabled. Click nodes on canvas to calibrate.")
        else:
            self.btn_editor_mode.config(
                text="🛠️ Editor Mode: OFF",
                bg=THEME["bg_surface"],
                fg=THEME["text_main"],
            )
            self._log_event("Developer Editor Mode disabled.")

    # -------------------------------------------------------------------------
    # PIPELINE TELEMETRY HOOK (CALLED BY main.py)
    # -------------------------------------------------------------------------
    def update_telemetry(
        self,
        gesture: GestureType,
        context: str,
        pinch_metric: float,
        metrics: Optional[Dict[str, Any]] = None,
        detected_hand: Optional[HandLandmarksResult] = None,
        frame: Optional[Any] = None,
        fps: Optional[float] = None,
    ) -> None:
        """
        Thread-safe telemetry update from the background camera & pipeline loop.

        :param gesture: Current detected gesture classification.
        :param context: Active foreground OS window context.
        :param pinch_metric: Real-time continuous Euclidean pinch distance.
        :param metrics: Full metric dictionary.
        :param detected_hand: HandLandmarksResult for canvas coordinate overlay.
        :param frame: Live video frame containing overlaid HUD and hand landmarks.
        :param fps: Real-time frames-per-second measurement.
        """
        if not self.root or not self.root.winfo_exists():
            return

        if fps is not None and hasattr(self, "pill_fps"):
            self.pill_fps.config(text=f"{fps:.1f} FPS")

        if self.simulation_active:
            return  # Simulator has temporary priority

        is_pinching = bool(metrics.get("is_pinching", 0.0)) if metrics else False
        self.latest_pinch_dist = pinch_metric
        self.latest_is_pinching = is_pinching
        self.latest_frame = frame

        if detected_hand and detected_hand.normalized_landmarks:
            self.latest_hand_landmarks = detected_hand.normalized_landmarks
        else:
            self.latest_hand_landmarks = None

        self._update_telemetry_ui(gesture, context, pinch_metric, is_pinching, frame=frame)

        # Log discrete gesture transitions
        if gesture != GestureType.NONE:
            self._log_event(f"Gesture Triggered: {gesture.name} (Context: {context})")

    def _update_telemetry_ui(
        self,
        gesture: GestureType,
        context: str,
        pinch_metric: float,
        is_pinching: bool,
        frame: Optional[Any] = None,
    ) -> None:
        """Update telemetry navbar pills, gauge, and canvas."""
        # Top Navbar pills
        if gesture != GestureType.NONE:
            self.pill_gesture.config(text=f"ACTIVE: {gesture.name}", fg=THEME["accent_green"])
        else:
            self.pill_gesture.config(text="ACTIVE: NONE", fg=THEME["accent_cyan"])

        self.pill_context.config(text=f"CONTEXT: {context}")

        # Live metric readout
        self.lbl_live_distance.config(text=f"{pinch_metric:.3f}")
        if is_pinching:
            self.lbl_gauge_state.config(text="ACTIONABLE: PINCH", fg=THEME["accent_green"])
        elif pinch_metric > 0:
            self.lbl_gauge_state.config(text="TRACKING", fg=THEME["accent_blue"])
        else:
            self.lbl_gauge_state.config(text="IDLE", fg=THEME["text_muted"])

        # Update Gauge
        self.gauge.update_gauge(pinch_metric, self.classifier.pinch_threshold, is_pinching)

        # Update Hand Canvas
        g_def = GESTURE_DICTIONARY.get(self.selected_gesture_type)
        active_nodes = g_def.key_nodes if g_def else [self.selected_node_a, self.selected_node_b]

        self.hand_canvas.render(
            landmarks=self.latest_hand_landmarks,
            highlight_nodes=active_nodes,
            node_a=self.selected_node_a,
            node_b=self.selected_node_b,
            distance=pinch_metric,
            is_pinching=is_pinching,
            frame=frame,
        )

    def run(self) -> None:
        """Start the Tkinter event loop."""
        self.root.mainloop()

    def update_idle(self) -> None:
        """Process pending Tkinter events (non-blocking)."""
        if self.root and self.root.winfo_exists():
            self.root.update_idletasks()
            self.root.update()
