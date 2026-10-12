# 🧠 Member 2: Perceptual Pipeline (ML) Engineer ([Aryan](https://github.com/OM200328))

## 📌 Responsibilities & Architecture Role
* **MediaPipe Framework Integration**: Integrates Google's pre-trained MediaPipe Hands framework with dual compatibility across legacy `mp.solutions.hands` and modern MediaPipe Tasks API (`hand_landmarker.task`).
* **Stage 1 (Palm Detector)**: Establishes the hand bounding box with spatial padding while suppressing background clutter, lighting variations, and human faces.
* **Stage 2 (Joint Coordinate Inference)**: Extracts normalized $(X, Y, Z)$ and pixel coordinates for all 21 hand joints and fingertips.
* **Deep Learning Models & Checkpoints**: PyTorch neural architectures (`GestureLandmarkMLP` and `GestureCNN`), dataset loaders for Archive 5, 6, and 10, training script (`train.py`), and model evaluator (`evaluate.py`).

## 📁 Contained Files
* [`member_2.py`](member_2.py): MediaPipe Stage 1 & Stage 2 inference engine and skeleton renderer.
* [`model.py`](model.py): Deep MLP and CNN network architectures.
* [`dataset.py`](dataset.py): Dataset loaders and preprocessing pipelines.
* [`train.py`](train.py): PyTorch training script.
* [`evaluate.py`](evaluate.py): Model evaluation and metrics generation.

## 🚀 Independent Testing & Evaluation
```bash
python member_2/evaluate.py --dataset archive5
python member_2/evaluate.py --dataset archive6
```
