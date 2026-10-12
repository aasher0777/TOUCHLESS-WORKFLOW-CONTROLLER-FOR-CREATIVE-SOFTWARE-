# 📷 Member 1: Camera & Preprocessing Lead ([Ashirbad Jena](https://github.com/ashirbadjena2005-code))

## 📌 Responsibilities & Architecture Role
* **Webcam Ingestion**: Connects the system to standard USB or integrated laptop webcams (`cv2.VideoCapture`) with multi-backend fallback (DirectShow, MSMF, V4L) and smart sensor warmup.
* **Active Memory Buffering**: Implements a zero-copy RAM ring buffer (`collections.deque`) to store recent raw and RGB frames for smooth real-time downstream processing.
* **Normalization & Geometric Scaling**: Aspect-ratio center-cropping (`crop_center`), software resolution scaling (`scale_frame`), intensity normalization, and BGR-to-RGB color space conversion for machine learning stages.

## 📁 Contained Files
* [`member_1.py`](member_1.py): Complete camera acquisition engine, frame normalization pipeline, and streaming generators.

## 🚀 Independent Testing
```bash
python member_1/member_1.py
```
