"""
camera_acquisition.py
---------------------
Handles hardware initialization using cv2.VideoCapture(), frame-by-frame
extraction in a continuous loop, active memory buffering, frame normalization
(scaling, aspect-ratio cropping, and float intensity scaling), and mathematical
conversion from OpenCV BGR to machine learning RGB format.
"""

from collections import deque
from typing import Deque, Generator, List, Optional, Tuple, Union
import cv2
import numpy as np


class CameraAcquisition:
    """Manages video capture hardware, frame acquisition, active memory buffering, and normalization."""

    def __init__(
        self,
        camera_index: int = 0,
        width: int = 640,
        height: int = 480,
        fps: int = 60,
        buffer_size: int = 10,
        auto_scale: bool = True,
    ) -> None:
        """
        Initialize the camera capture device.

        :param camera_index: Hardware device index (default: 0).
        :param width: Target capture width in pixels.
        :param height: Target capture height in pixels.
        :param fps: Target capture frame rate (default: 60 FPS).
        :param buffer_size: Number of recent frames stored in active system RAM buffer.
        :param auto_scale: Automatically scale/crop frames to exact width/height if hardware differs.
        """
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        self.buffer_size = buffer_size
        self.auto_scale = auto_scale

        # Active system memory buffers
        self.memory_buffer: Deque[np.ndarray] = deque(maxlen=self.buffer_size)
        self.latest_frame_bgr: Optional[np.ndarray] = None
        self.latest_frame_rgb: Optional[np.ndarray] = None

        self.cap: Optional[cv2.VideoCapture] = None
        self._initialize_camera()

    def _initialize_camera(self) -> None:
        """
        Open cv2.VideoCapture stream with smart hardware probing:
        Prioritizes DirectShow with MJPG encoding for native 60 FPS throughput,
        probes backends to prevent black frames, and configures zero-latency buffering.
        """
        import sys

        backends = []
        if sys.platform == "win32":
            backends = [
                (cv2.CAP_DSHOW, "DirectShow (60 FPS Native)"),
                (cv2.CAP_MSMF, "Media Foundation (Native Windows)"),
                (cv2.CAP_ANY, "Default Capture Pipeline"),
            ]
        else:
            backends = [(cv2.CAP_ANY, "Standard Video4Linux/Default")]

        candidate_indices = [self.camera_index]
        for extra in (0, 1, 2):
            if extra not in candidate_indices:
                candidate_indices.append(extra)

        best_cap = None
        best_index = self.camera_index
        best_name = ""
        best_brightness = 0.0

        fallback_cap = None
        fallback_index = self.camera_index
        fallback_name = ""

        for c_idx in candidate_indices:
            for backend, b_name in backends:
                cap = cv2.VideoCapture(c_idx, backend)
                if cap.isOpened():
                    # Set MJPG codec first for high framerate (60 FPS) negotiation
                    try:
                        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
                    except Exception:
                        pass
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    cap.set(cv2.CAP_PROP_FPS, self.fps)
                    try:
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    except Exception:
                        pass

                    # Read up to 5 warmup frames to let sensor auto-exposure and gain settle
                    valid_frames = []
                    for _ in range(5):
                        ret, test_frame = cap.read()
                        if ret and test_frame is not None:
                            valid_frames.append(test_frame)

                    if valid_frames:
                        mean_val = float(valid_frames[-1].mean())
                        if mean_val > 2.0:
                            # Found active physical camera with light!
                            best_cap = cap
                            best_index = c_idx
                            best_name = b_name
                            best_brightness = mean_val
                            break
                        elif fallback_cap is None:
                            fallback_cap = cap
                            fallback_index = c_idx
                            fallback_name = b_name
                            continue
                    cap.release()
            if best_cap is not None:
                break

        if best_cap is not None:
            self.cap = best_cap
            self.camera_index = best_index
            print(
                f"[CameraAcquisition] Connected to camera index {best_index} via {best_name} "
                f"(Brightness: {best_brightness:.1f}, Target: {self.width}x{self.height} @ {self.fps}FPS)"
            )
            if fallback_cap is not None:
                fallback_cap.release()
        elif fallback_cap is not None:
            self.cap = fallback_cap
            self.camera_index = fallback_index
            print(
                f"[CameraAcquisition] Connected to camera index {fallback_index} via {fallback_name} "
                f"(Warning: low light or shutter closed)"
            )
        else:
            # Fallback to standard capture
            self.cap = cv2.VideoCapture(self.camera_index)

        if not self.cap or not self.cap.isOpened():
            raise RuntimeError(
                f"[CameraAcquisition] Failed to open video capture device at index {self.camera_index}."
            )

    def is_opened(self) -> bool:
        """Check if camera device is actively open."""
        return self.cap is not None and self.cap.isOpened()

    # -------------------------------------------------------------------------
    # NORMALIZATION & GEOMETRIC TRANSFORMATIONS
    # -------------------------------------------------------------------------
    @staticmethod
    def crop_center(frame: np.ndarray, target_w: int, target_h: int) -> np.ndarray:
        """
        Center-crop the frame to target dimensions or target aspect ratio without distortion.

        :param frame: Source image array (H, W, C).
        :param target_w: Target width.
        :param target_h: Target height.
        :return: Center-cropped image array.
        """
        h, w = frame.shape[:2]
        if w == target_w and h == target_h:
            return frame

        target_aspect = target_w / max(target_h, 1)
        current_aspect = w / max(h, 1)

        if abs(current_aspect - target_aspect) < 1e-4:
            return frame

        if current_aspect > target_aspect:
            # Source is wider than target: crop sides
            new_w = int(h * target_aspect)
            offset_x = max((w - new_w) // 2, 0)
            return frame[:, offset_x : offset_x + new_w]
        elif current_aspect < target_aspect:
            # Source is taller than target: crop top/bottom
            new_h = int(w / target_aspect)
            offset_y = max((h - new_h) // 2, 0)
            return frame[offset_y : offset_y + new_h, :]

        return frame

    @staticmethod
    def scale_frame(
        frame: np.ndarray,
        target_w: int,
        target_h: int,
        interpolation: int = cv2.INTER_LINEAR,
    ) -> np.ndarray:
        """
        Scale/resize frame dimensions to target width and height.

        :param frame: Source image array.
        :param target_w: Target width in pixels.
        :param target_h: Target height in pixels.
        :param interpolation: OpenCV interpolation algorithm.
        :return: Resized image array.
        """
        h, w = frame.shape[:2]
        if w == target_w and h == target_h:
            return frame
        return cv2.resize(frame, (target_w, target_h), interpolation=interpolation)

    @staticmethod
    def normalize_intensity(
        frame: np.ndarray, dtype: np.dtype = np.float32
    ) -> np.ndarray:
        """
        Mathematically normalize uint8 pixel intensity values [0, 255] to floating point [0.0, 1.0].

        :param frame: Image array with values in [0, 255].
        :param dtype: Target numpy floating point dtype.
        :return: Normalized float array in range [0.0, 1.0].
        """
        return frame.astype(dtype) / 255.0

    def normalize_frame(
        self,
        frame_bgr: np.ndarray,
        target_w: Optional[int] = None,
        target_h: Optional[int] = None,
        crop_to_aspect: bool = False,
        normalize_values: bool = False,
    ) -> Tuple[np.ndarray, Union[np.ndarray, np.ndarray]]:
        """
        Comprehensive normalization pipeline:
        1. Aspect-ratio center cropping (optional).
        2. Software dimension scaling to exact target (width, height).
        3. Mathematical BGR to RGB color conversion.
        4. Value intensity normalization to [0.0, 1.0] (optional).

        :return: Tuple of (processed_bgr, processed_rgb).
        """
        tw = target_w or self.width
        th = target_h or self.height

        out_bgr = frame_bgr
        if crop_to_aspect:
            out_bgr = self.crop_center(out_bgr, tw, th)

        out_bgr = self.scale_frame(out_bgr, tw, th)

        # Mathematical color space conversion from BGR to RGB
        out_rgb = cv2.cvtColor(out_bgr, cv2.COLOR_BGR2RGB)

        if normalize_values:
            out_rgb = self.normalize_intensity(out_rgb)

        return out_bgr, out_rgb

    # -------------------------------------------------------------------------
    # FRAME ACQUISITION & ACTIVE MEMORY BUFFERING
    # -------------------------------------------------------------------------
    def read_frame(
        self,
        crop_to_aspect: bool = False,
        normalize_values: bool = False,
    ) -> Tuple[bool, Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Read a single frame from the camera hardware, normalize geometry,
        convert BGR to RGB, and temporarily store into active system memory.

        :param crop_to_aspect: If True, crops center to preserve aspect ratio before scaling.
        :param normalize_values: If True, scales pixel intensities to [0.0, 1.0] float.
        :return: Tuple containing:
                 - success (bool): True if frame was successfully read.
                 - frame_bgr (np.ndarray or None): Normalized BGR frame.
                 - frame_rgb (np.ndarray or None): Mathematically converted RGB frame.
        """
        if not self.is_opened():
            return False, None, None

        ret, frame_bgr = self.cap.read()
        if not ret or frame_bgr is None:
            return False, None, None

        # Horizontal flip for intuitive mirror interaction
        frame_bgr = cv2.flip(frame_bgr, 1)

        # Normalize scaling & convert BGR to RGB
        if self.auto_scale:
            frame_bgr, frame_rgb = self.normalize_frame(
                frame_bgr,
                target_w=self.width,
                target_h=self.height,
                crop_to_aspect=crop_to_aspect,
                normalize_values=normalize_values,
            )
        else:
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            if normalize_values:
                frame_rgb = self.normalize_intensity(frame_rgb)

        # Temporarily store incoming frames into active system RAM memory buffer
        self.latest_frame_bgr = frame_bgr
        self.latest_frame_rgb = frame_rgb
        self.memory_buffer.append(frame_rgb)

        return True, frame_bgr, frame_rgb

    def get_buffered_frames(self) -> List[np.ndarray]:
        """Retrieve recent active memory buffered frames from RAM."""
        return list(self.memory_buffer)

    def stream_frames(
        self,
    ) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        """
        Continuous generator yielding (frame_bgr, frame_rgb) pairs from active stream.

        :yields: Tuple of (frame_bgr, frame_rgb).
        """
        while self.is_opened():
            success, frame_bgr, frame_rgb = self.read_frame()
            if not success:
                break
            yield frame_bgr, frame_rgb

    def release(self) -> None:
        """Safely release the hardware capture resource and clear memory buffers."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.memory_buffer.clear()
        self.latest_frame_bgr = None
        self.latest_frame_rgb = None

    def __enter__(self) -> "CameraAcquisition":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()


if __name__ == "__main__":
    print("Testing CameraAcquisition...")
    try:
        with CameraAcquisition() as cam:
            for bgr, rgb in cam.stream_frames():
                cv2.imshow("Camera Acquisition Test (BGR)", bgr)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    except Exception as e:
        print(f"Camera test failed or no camera available: {e}")
    finally:
        cv2.destroyAllWindows()
