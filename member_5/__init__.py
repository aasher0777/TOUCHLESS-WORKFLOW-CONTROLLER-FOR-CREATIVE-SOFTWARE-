"""
Member 5: Packaging, UI & Release Manager (Rahul)
-------------------------------------------------
- Develops a lightweight visual dashboard (using Tkinter, PyQt, or Electron)
  for users to manage custom profiles and gestures.
- Packages the Python scripts, OpenCV dependencies, and MediaPipe models
  into a standalone .exe or .app file using PyInstaller or auto-py-to-exe.
- Sets up the GitHub Actions CI/CD pipeline to automate testing and release cycles,
  and manages distribution via a dedicated landing page.
"""

from .member_5 import GestureControllerUI, HandLandmarkCanvas
from .package_app import check_prerequisites, build_executable

__all__ = [
    "GestureControllerUI",
    "HandLandmarkCanvas",
    "check_prerequisites",
    "build_executable",
]
