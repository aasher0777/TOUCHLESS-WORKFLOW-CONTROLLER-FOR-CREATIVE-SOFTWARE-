"""
package_app.py
--------------
Automates packaging of the Gesture Recognition and OS Macro application
into a standalone .exe file using PyInstaller.
"""

import os
import subprocess
import sys


def check_prerequisites() -> bool:
    """Ensure required model assets and dependencies exist before building."""
    print("[1/4] Checking packaging prerequisites...")
    model_asset = os.path.join("models", "hand_landmarker.task")
    if not os.path.exists(model_asset):
        print(f"Warning: {model_asset} was not found. Attempting to ensure model exists...")
        try:
            try:
                from member_2.member_2 import LandmarkInference
            except ImportError:
                from member_2 import LandmarkInference
            inf = LandmarkInference()
            inf.close()
        except Exception as e:
            print(f"Could not auto-fetch model: {e}")

    # Check for PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller version {PyInstaller.__version__} is available.")
        return True
    except ImportError:
        print("PyInstaller is not installed in the active environment.")
        install = input("Would you like to install PyInstaller now via pip? (y/n): ").strip().lower()
        if install == 'y':
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            return True
        else:
            print("Cannot build standalone executable without PyInstaller.")
            return False


def build_executable() -> bool:
    """Run PyInstaller with gesture_controller.spec."""
    print("[2/4] Initiating PyInstaller build process...")
    spec_file = "member_5/gesture_controller.spec"
    if not os.path.exists(spec_file):
        spec_file = "gesture_controller.spec"
    if not os.path.exists(spec_file):
        print(f"Error: {spec_file} not found!")
        return False

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        spec_file,
        "--clean",
        "--noconfirm",
    ]

    print(f"[3/4] Executing build command: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        exe_path = os.path.join("dist", "GestureStudioPro.exe" if sys.platform == "win32" else "GestureStudioPro")
        print("[4/4] Build succeeded!")
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"Standalone executable generated successfully: {exe_path} ({size_mb:.1f} MB)")
        return True
    else:
        print(f"Build failed with return code {result.returncode}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print(" GESTURE STUDIO PRO - STANDALONE EXECUTABLE BUILDER")
    print("=" * 60)
    if check_prerequisites():
        build_executable()
