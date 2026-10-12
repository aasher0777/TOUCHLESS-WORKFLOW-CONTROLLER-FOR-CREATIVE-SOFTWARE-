"""
Member 1: Camera & Preprocessing Lead (Ashirbad)
-----------------------------------------------
- Connects the system to standard USB or laptop webcams to acquire video frames.
- Temporarily stores incoming frames into the system's active memory.
- Normalizes the frames by scaling or cropping, and mathematically converts
  OpenCV's native BGR format to RGB format for the machine learning models.
"""

from .member_1 import CameraAcquisition

__all__ = ["CameraAcquisition"]
