# -*- mode: python ; coding: utf-8 -*-
"""
gesture_controller.spec
-----------------------
PyInstaller specification file to bundle the Gesture Studio / OS Controller pipeline,
OpenCV binaries, MediaPipe 3D Hand Landmarker models, and GUI dashboard into a standalone executable.
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Base directory resolution
spec_dir = os.path.abspath(SPECPATH)
project_dir = os.path.abspath(os.path.join(spec_dir, "..")) if os.path.basename(spec_dir) in ("member_5", "member_5_rahul_ui_release") else spec_dir
main_script = os.path.join(project_dir, 'main.py')

# Model assets and data files
added_datas = [
    (os.path.join(project_dir, 'models'), 'models'),
]

# Collect MediaPipe data files and models if present
try:
    added_datas += collect_data_files('mediapipe')
except Exception:
    pass

# Hidden imports required by dynamic loaders
hidden_imports = [
    'mediapipe',
    'mediapipe.tasks',
    'mediapipe.tasks.python',
    'mediapipe.tasks.python.vision',
    'pyautogui',
    'keyboard',
    'pygetwindow',
    'cv2',
    'numpy',
    'PIL',
    'torch',
    'sklearn',
    'pandas',
]

try:
    hidden_imports += collect_submodules('mediapipe')
except Exception:
    pass

a = Analysis(
    [main_script],
    pathex=[project_dir],
    binaries=[],
    datas=added_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['IPython', 'notebook', 'matplotlib'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GestureStudioPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging terminal output if desired
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
