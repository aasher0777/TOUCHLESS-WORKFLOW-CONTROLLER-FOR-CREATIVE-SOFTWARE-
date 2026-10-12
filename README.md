# 🖐️ Gesture Studio Pro — Spatial 3D Hand Tracking & OS Macro Controller

[![Build & CI Pipeline](https://github.com/gesture-studio/project/actions/workflows/build_pipeline.yml/badge.svg)](https://github.com)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11-blue.svg)](https://www.python.org/)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10+-brightgreen.svg)](https://developers.google.com/mediapipe)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-ee4c2c.svg)](https://pytorch.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Touchless Operating System Control** powered by Google MediaPipe 3D joint landmark extraction, continuous Euclidean spatial calculations, deep learning neural inference, and context-aware macro routing for **Adobe Premiere Pro**, **Figma**, and web browsers.

---

## 📑 Table of Contents
1. [Key Features](#-key-features)
2. [Architecture Overview](#-architecture-overview)
3. [Quick Start Guide](#-quick-start-guide)
4. [Trained Deep Learning Models & Performance](#-trained-deep-learning-models--performance)
5. [3D Gesture Dictionary & Macro Routing](#-3d-gesture-dictionary--macro-routing)
6. [Developer Calibration Workbench & Simulator](#-developer-calibration-workbench--simulator)
7. [Standalone Executable Packaging](#-standalone-executable-packaging)
8. [Automated CI/CD Pipeline & Distribution Landing Page](#-automated-cicd-pipeline--distribution-landing-page)
9. [Subsystem Verification Suite](#-subsystem-verification-suite)

---

## ✨ Key Features

* **📷 Fast Camera Ingestion & 3D Normalization**: Real-time webcam acquisition via DirectShow, active memory frame buffering, center-cropping, software scaling, and BGR-to-RGB conversion.
* **🧠 Two-Stage MediaPipe ML Pipeline**:
  * **Stage 1 (BlazePalm Detector)**: Establishes the hand bounding box while suppressing background clutter, lighting shifts, and human faces.
  * **Stage 2 (Hand Landmarker)**: Extracted exact $(X, Y, Z)$ spatial coordinates for all 21 hand joints and fingertips.
* **📐 Continuous 3D Euclidean Calculations**: Real-time distance tracking between arbitrary node pairs (e.g. Node 4 Thumb Tip to Node 8 Index Tip) with dynamic hand-scale normalization and state-machine debounce flags.
* **🎯 Context-Aware Application Routing**: Real-time window inspection via `pygetwindow` routes gestures into native hotkeys for **Adobe Premiere Pro** (Razor Cut, Shuttle, Zoom Timeline), **Figma** (Undo/Redo, Canvas Zoom, Pan), Browsers, and Media Players.
* **⚡ Dual-Engine Macro Dispatch**: Combines the low-level `keyboard` library for instantaneous key combinations with `pyautogui` for mouse cursor manipulation.
* **🖥️ Sleek Modern Dashboard (Dark Theme)**: Interactive gesture catalog, live 2D/3D skeleton canvas with glowing amber halos, real-time distance gauge, and custom profile management.
* **📦 One-Click Standalone Executable**: Packaged with PyInstaller into a standalone Windows `.exe` with all bundled models and dependencies.

---

## 🏗️ Architecture Overview

```
 [ Webcam / USB Stream ]
           │
           ▼
 ┌────────────────────────────────────────┐
 │ Stage 1: Camera Acquisition            │ ──> Active RAM Ring Buffer & Normalization
 └────────────────────────────────────────┘
           │ (RGB Frame)
           ▼
 ┌────────────────────────────────────────┐
 │ Stage 2: MediaPipe Landmark Inference  │ ──> Stage 1: BlazePalm Bounding Box
 └────────────────────────────────────────┘ ──> Stage 2: 21 3D Spatial Coordinates (X, Y, Z)
           │
           ▼
 ┌────────────────────────────────────────┐
 │ Stage 3: Gesture Classifier & Geometry │ ──> Continuous 3D Euclidean Math d(N4, N8)
 └────────────────────────────────────────┘ ──> State-Machine Debounce (Pinch / Swipes)
           │
           ▼
 ┌────────────────────────────────────────┐
 │ Stage 4: OS Macro Controller           │ ──> pygetwindow Context Router (Premiere, Figma)
 └────────────────────────────────────────┘ ──> Dual Dispatch (keyboard + pyautogui)
           │
           ▼
 ┌────────────────────────────────────────┐
 │ Stage 5: Modern Visual Dashboard       │ ──> Interactive Canvas, Gauge & Workbench
 └────────────────────────────────────────┘
```

---

## 🚀 Quick Start Guide

### 1. Installation
Clone the repository and install dependencies in your virtual environment:
```bash
git clone https://github.com/gesture-studio/project.git
cd project
pip install -r requirements.txt
```

### 2. Run the Interactive Dashboard
Launch the full pipeline with live camera tracking and the modern UI workbench:
```bash
python main.py
```

### 3. Run Headless (CLI-only mode)
Run without the Tkinter frontend (ideal for background or low-resource environments):
```bash
python main.py --no-ui
```

---

## 📊 Trained Deep Learning Models & Performance

The project includes trained PyTorch neural networks for high-confidence static and dynamic gesture classification:

| Model Architecture | Dataset Source | Accuracy | Checkpoint Path | Classes |
| :--- | :--- | :---: | :--- | :--- |
| **GestureLandmarkMLP** | Archive 5 (RPS Landmarks) | **97.56%** | `models/gesture_mlp_archive5.pth` | Rock, Paper, Scissors |
| **GestureLandmarkMLP** | Archive 6 (12-Gesture 3D Joints) | **91.78%** | `models/gesture_mlp_archive6.pth` | Open, Close, Peace, Point, Rock, Thumb (+ Inverted) |
| **GestureCNN** | Archive 10 (Raw Hand Images) | **93.20%** | `models/gesture_cnn_archive10.pth` | 27 Alpha-numeric Sign Classes |

### Run Model Evaluation
Verify trained weights against the test split:
```bash
# Evaluate Archive 5 MLP Model
python member_2/evaluate.py --dataset archive5

# Evaluate Archive 6 12-Gesture Landmark Model
python member_2/evaluate.py --dataset archive6
```

### Retrain Models
To retrain any model checkpoint:
```bash
python member_2/train.py --dataset archive5 --epochs 8
python member_2/train.py --dataset archive6 --epochs 12
python member_2/train.py --dataset all
```

---

## 📖 3D Gesture Dictionary & Macro Routing

| Gesture | Tracked 3D Nodes | Spatial Formula / Condition | Adobe Premiere Pro | Figma | Browser |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **🤏 Index Pinch** | Node 4 (Thumb) & Node 8 (Index) | $d_{3D}(N_4, N_8) / \text{scale} < 0.060$ | **Razor Cut** (`Ctrl+K`) | **Select & Drag** (Click) | Mouse Click |
| **👈 Swipe Left** | Node 9 (Palm Center) | $\Delta X < -0.120$ in $0.35\text{s}$ | **Prev Edit Point** (`Shift+←`) | **Undo** (`Ctrl+Z`) | Prev Tab (`Ctrl+Shift+Tab`) |
| **👉 Swipe Right** | Node 9 (Palm Center) | $\Delta X > +0.120$ in $0.35\text{s}$ | **Next Edit Point** (`Shift+→`) | **Redo** (`Ctrl+Y`) | Next Tab (`Ctrl+Tab`) |
| **👆 Swipe Up** | Node 9 (Palm Center) | $\Delta Y < -0.120$ in $0.35\text{s}$ | **Zoom In Timeline** (`=`) | **Zoom In Canvas** (`Ctrl++`) | Scroll Up (`PageUp`) |
| **👇 Swipe Down** | Node 9 (Palm Center) | $\Delta Y > +0.120$ in $0.35\text{s}$ | **Zoom Out Timeline** (`-`) | **Zoom Out Canvas** (`Ctrl+-`) | Scroll Down (`PageDown`) |
| **🖐️ Open Palm** | All 5 Digit Tips (Nodes 4, 8, 12, 16, 20) | $\text{count}(\text{extended}) == 5$ | **Play / Stop** (`Space`) | **Hand / Pan Tool** (`H`) | Play / Pause |
| **✊ Closed Fist** | All 5 Digit Tips (Nodes 4, 8, 12, 16, 20) | $\text{count}(\text{extended}) == 0$ | **Ripple Delete** (`Shift+Del`) | **Delete Selection** (`Del`) | Close Tab (`Ctrl+W`) |
| **☝️ Pointing** | Node 8 (Index Tip) extended | $d(N_8, N_0) > d(N_6, N_0)$, others curled | **Selection Tool** (`V`) | **Move Tool** (`V`) | Navigation |
| **✌️ Peace Sign** | Nodes 8 & 12 extended | Nodes 8 & 12 extended, ring/pinky curled | **Mark In Point** (`I`) | **Toggle UI** (`Ctrl+\`) | Context Switch |

---

## 🛠️ Developer Calibration Workbench & Simulator

When launching `python main.py`, toggle the **"🛠️ Editor Mode"** button in the top navigation bar to access the integrated developer suite:
1. **Click-to-Select Node Calibration**: Click any joint on the 21-node canvas to instantly set distance measurement targets between Node A and Node B.
2. **Dynamic Threshold Sliders**: Adjust pinch distance (`0.02` to `0.15`) and swipe displacement (`0.05` to `0.30`) with real-time visual feedback on the continuous gauge.
3. **Synthetic Data & Test Runner Simulator**: Test gesture state transitions without needing an active webcam:
   * `Sim Open Hand (0.35)`
   * `Sim Pinch (0.03)`
   * `Sim Swipe Right`
   * `Reset to Live Camera`
4. **Live Config JSON Exporter**: Export and copy calibrated parameters directly into your project configuration.

---

## 📦 Standalone Executable Packaging

The project includes an automated PyInstaller specification ([`member_5/gesture_controller.spec`](member_5/gesture_controller.spec)) and packaging runner ([`member_5/package_app.py`](member_5/package_app.py)) that bundles all OpenCV dependencies, MediaPipe models, and PyTorch weights into a standalone `.exe`.

To package the application into a standalone Windows executable:
```bash
python member_5/package_app.py
```
The output binary will be generated at `dist/GestureStudioPro.exe`.

---

## 🌐 Automated CI/CD Pipeline & Distribution Landing Page

* **GitHub Actions Workflow** ([`.github/workflows/build_pipeline.yml`](.github/workflows/build_pipeline.yml)):
  1. **Stage 1 (Test & Validate)**: Runs multi-OS (Ubuntu, Windows) linting and unit tests on Python 3.10 and 3.11.
  2. **Stage 2 (Build Standalone Executable)**: Runs PyInstaller on Windows runners, uploads build artifacts, and automates GitHub Releases on version tags (`v*`).
  3. **Stage 3 (Deploy Landing Page)**: Automatically deploys the dedicated distribution landing page to **GitHub Pages**.
* **Distribution Landing Page** ([`docs/index.html`](docs/index.html)): A high-performance, dark-themed responsive website featuring live mockups, feature deep dives, a gesture cheatsheet, and one-click download buttons.

---

## 🧪 Subsystem Verification Suite

To run the complete automated end-to-end verification suite across all 7 subsystems simultaneously:
```bash
python -X utf8 verify_all.py
```

### Expected Output:
```text
======================================================================
 GESTURE STUDIO PRO — END-TO-END SUBSYSTEM VERIFICATION SUITE
======================================================================
Python Runtime: 3.14.3 on win32

----------------------------------------------------------------------
SUBSYSTEM                                     | STATUS | NOTES
----------------------------------------------------------------------
Camera Acquisition & 3D Normalization         | ✅ PASS | Scaling, cropping, BGR->RGB & RAM buffer ok
MediaPipe Stage 1 & Stage 2 Inference         | ✅ PASS | Palm bounding box & 21 3D joint models ok
Gesture Dictionary & Continuous 3D Euclidean  | ✅ PASS | 9 gestures mapped, Node 4-8 pinch state machine ok
Context Routing & Macro Dispatch Engine       | ✅ PASS | Premiere, Figma, Browser & dual keyboard/pyautogui ok
UI Dashboard & Developer Workbench            | ✅ PASS | Dark theme, canvas, gauge, simulator & exporter ok
Deep Learning Models & Checkpoints            | ✅ PASS | Archive 5 (97.6%) & Archive 6 (91.8%)
Packaging Spec, CI/CD & Landing Page          | ✅ PASS | PyInstaller spec, GitHub Actions 3-stage CI/CD & docs/index.html ok
----------------------------------------------------------------------

🎉 ALL 7 CORE SUBSYSTEMS FULLY VERIFIED & OPERATIONAL!
The project is 100% complete, tested, and ready for deployment.
```

---

## 👥 Group Members & 5-Folder Architecture

The repository is modularly structured across five dedicated folders and primary files, individually owned and implemented by each group member:

| Member & Role | Dedicated Folder | Primary Member File | Key Responsibilities |
| :--- | :--- | :--- | :--- |
| **Member 1: Camera & Preprocessing Lead**<br>*(Ashirbad)* | [`member_1/`](member_1/) | [`member_1.py`](member_1/member_1.py) | • Connects to USB/laptop webcams via DirectShow/MSMF/V4L<br>• Zero-copy active RAM ring buffer (`collections.deque`)<br>• Aspect center-cropping, scaling & BGR-to-RGB conversion |
| **Member 2: Perceptual Pipeline (ML) Engineer**<br>*(Aryan)* | [`member_2/`](member_2/) | [`member_2.py`](member_2/member_2.py)<br>• [`model.py`](member_2/model.py)<br>• [`dataset.py`](member_2/dataset.py)<br>• [`train.py`](member_2/train.py)<br>• [`evaluate.py`](member_2/evaluate.py) | • MediaPipe Hands integration (legacy & Tasks API)<br>• Stage 1 Palm Detector bounding box estimation<br>• Stage 2 21 3D joint coordinate inference ($X, Y, Z$)<br>• Deep MLP and CNN PyTorch training & evaluation |
| **Member 3: State-Machine Logic Developer**<br>*(Subham)* | [`member_3/`](member_3/) | [`member_3.py`](member_3/member_3.py) | • 9-gesture 3D coordinate dictionary (`GESTURE_DICTIONARY`)<br>• C-accelerated Euclidean distance calculations (`math.dist`)<br>• Node 4 (Thumb) to Node 8 (Index) pinch state-machine |
| **Member 4: OS Context & Automation Specialist**<br>*(Swastik)* | [`member_4/`](member_4/) | [`member_4.py`](member_4/member_4.py)<br>• [`custom_profiles.json`](member_4/custom_profiles.json) | • Context routing queries via `pygetwindow` with TTL caching<br>• Matches gesture state with application dictionaries (Premiere, Figma)<br>• Dual dispatch engine via `keyboard` and `pyautogui` |
| **Member 5: Packaging, UI & Release Manager**<br>*(Rahul)* | [`member_5/`](member_5/) | [`member_5.py`](member_5/member_5.py)<br>• [`package_app.py`](member_5/package_app.py)<br>• [`gesture_controller.spec`](member_5/gesture_controller.spec) | • Modern Tkinter dark dashboard & developer workbench<br>• Standalone `.exe` compilation via PyInstaller<br>• GitHub Actions 3-stage CI/CD & distribution landing page |
