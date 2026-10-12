"""
dataset.py
----------
Data loading, preprocessing, and PyTorch Dataset implementations for:
1. archive (5) / archive (6) landmark CSV datasets (21 hand joints).
2. archive (10) raw image dataset (A-Z + space).
"""

import json
import os
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler


class LandmarkCSVDataset(Dataset):
    """PyTorch Dataset for hand landmark coordinate tables."""

    def __init__(self, features: np.ndarray, labels: np.ndarray) -> None:
        """
        :param features: 2D numpy array of shape (N, feature_dim).
        :param labels: 1D numpy array of integer encoded labels (N,).
        """
        self.features = torch.tensor(features, dtype=torch.float32)
        self.labels = torch.tensor(labels, dtype=torch.long)

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.features[idx], self.labels[idx]


class HandImageDataset(Dataset):
    """PyTorch Dataset for hand gesture image folders."""

    def __init__(
        self,
        image_paths: List[str],
        labels: List[int],
        image_size: int = 64,
        grayscale: bool = True,
    ) -> None:
        """
        :param image_paths: List of absolute filepaths to images.
        :param labels: List of corresponding integer target labels.
        :param image_size: Target square image dimension in pixels.
        :param grayscale: If True, convert to single-channel 8-bit image.
        """
        self.image_paths = image_paths
        self.labels = labels
        self.image_size = image_size
        self.grayscale = grayscale

    def __len__(self) -> int:
        return len(self.image_paths)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        img_path = self.image_paths[idx]
        if self.grayscale:
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                img = np.zeros((self.image_size, self.image_size), dtype=np.uint8)
            else:
                img = cv2.resize(img, (self.image_size, self.image_size))
            img_tensor = torch.tensor(img, dtype=torch.float32).unsqueeze(0) / 255.0  # (1, H, W)
        else:
            img = cv2.imread(img_path, cv2.IMREAD_COLOR)
            if img is None:
                img = np.zeros((self.image_size, self.image_size, 3), dtype=np.uint8)
            else:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img = cv2.resize(img, (self.image_size, self.image_size))
            # HWC -> CHW
            img_tensor = torch.tensor(img, dtype=torch.float32).permute(2, 0, 1) / 255.0

        label_tensor = torch.tensor(self.labels[idx], dtype=torch.long)
        return img_tensor, label_tensor


def load_archive5_data(
    csv_path: str = "archive (5)/data.csv",
    test_size: float = 0.2,
    random_state: int = 42,
) -> Tuple[DataLoader, DataLoader, LabelEncoder, int, int]:
    """
    Load and preprocess the Rock-Paper-Scissors landmark dataset from archive (5).

    :return: (train_loader, test_loader, label_encoder, input_dim, num_classes)
    """
    if not os.path.exists(csv_path):
        # Fallback search
        for candidate in ["../archive (5)/data.csv", "data.csv", "../data.csv"]:
            if os.path.exists(candidate):
                csv_path = candidate
                break

    df = pd.read_csv(csv_path)

    # Features are columns 0..41 (21 points * 2 coords), label is last column 'Category'
    X = df.iloc[:, :-1].values.astype(np.float32)
    y_raw = df.iloc[:, -1].values

    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(y_raw)

    scaler = StandardScaler()
    X = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    train_ds = LandmarkCSVDataset(X_train, y_train)
    test_ds = LandmarkCSVDataset(X_test, y_test)

    train_loader = DataLoader(train_ds, batch_size=64, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=128, shuffle=False)

    return train_loader, test_loader, label_encoder, X.shape[1], len(label_encoder.classes_)


def load_archive6_data(
    csv_path: str = "archive (6)/gesture_landmarks.csv",
    test_size: float = 0.2,
    random_state: int = 42,
) -> Tuple[DataLoader, DataLoader, LabelEncoder, int, int]:
    """
    Load and preprocess landmark dataset from archive (6) / alternative archive.

    :return: (train_loader, test_loader, label_encoder, input_dim, num_classes)
    """
    if not os.path.exists(csv_path):
        for candidate in [
            "../archive (6)/gesture_landmarks.csv",
            "gesture_landmarks.csv",
            "archive (4)/gesture_landmarks.csv",
            "archive 4/gesture_landmarks.csv",
        ]:
            if os.path.exists(candidate):
                csv_path = candidate
                break

    df = pd.read_csv(csv_path)
    # Strip whitespace from column names if any
    df.columns = [c.strip() for c in df.columns]

    X = df.iloc[:, :-1].values.astype(np.float32)
    y_raw = df.iloc[:, -1].values

    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(y_raw)

    scaler = StandardScaler()
    X = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    train_ds = LandmarkCSVDataset(X_train, y_train)
    test_ds = LandmarkCSVDataset(X_test, y_test)

    train_loader = DataLoader(train_ds, batch_size=16, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=32, shuffle=False)

    return train_loader, test_loader, label_encoder, X.shape[1], len(label_encoder.classes_)


def load_archive10_data(
    dataset_dir: str = "archive (10) (1)/own_dataset",
    image_size: int = 64,
    samples_per_class: Optional[int] = 50,
    test_size: float = 0.2,
    random_state: int = 42,
) -> Tuple[DataLoader, DataLoader, LabelEncoder, int]:
    """
    Load raw image dataset from archive (10) / own_dataset.

    :param samples_per_class: Max samples per class to load (None for all).
    :return: (train_loader, test_loader, label_encoder, num_classes)
    """
    if not os.path.exists(dataset_dir):
        for candidate in [
            "archive (10)/own_dataset",
            "../archive (10) (1)/own_dataset",
            "own_dataset",
        ]:
            if os.path.exists(candidate):
                dataset_dir = candidate
                break

    classes = sorted([d for d in os.listdir(dataset_dir) if os.path.isdir(os.path.join(dataset_dir, d))])
    image_paths: List[str] = []
    labels: List[str] = []

    for cls in classes:
        cls_folder = os.path.join(dataset_dir, cls)
        files = [f for f in os.listdir(cls_folder) if f.lower().endswith((".jpg", ".png", ".jpeg"))]
        if samples_per_class is not None:
            files = files[:samples_per_class]

        for f in files:
            image_paths.append(os.path.join(cls_folder, f))
            labels.append(cls)

    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(labels)

    train_paths, test_paths, y_train, y_test = train_test_split(
        image_paths, y, test_size=test_size, random_state=random_state, stratify=y
    )

    train_ds = HandImageDataset(train_paths, y_train, image_size=image_size, grayscale=True)
    test_ds = HandImageDataset(test_paths, y_test, image_size=image_size, grayscale=True)

    train_loader = DataLoader(train_ds, batch_size=32, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=32, shuffle=False)

    return train_loader, test_loader, label_encoder, len(label_encoder.classes_)
