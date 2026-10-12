"""
model.py
--------
PyTorch Deep Learning architectures for hand gesture recognition:
1. GestureLandmarkMLP: Deep Multi-Layer Perceptron for 21 2D/3D spatial landmark coordinates.
2. GestureCNN: Lightweight Convolutional Neural Network for direct raw hand gesture images.
"""

from typing import List
import torch
import torch.nn as nn


class GestureLandmarkMLP(nn.Module):
    """Deep Multi-Layer Perceptron for spatial landmark coordinate classification."""

    def __init__(
        self,
        input_dim: int = 42,
        num_classes: int = 3,
        hidden_dims: List[int] = None,
        dropout_rate: float = 0.2,
    ) -> None:
        """
        Initialize the Landmark MLP.

        :param input_dim: Number of input features (42 for 21x 2D landmarks, 63 for 21x 3D landmarks).
        :param num_classes: Number of gesture output classes.
        :param hidden_dims: List of hidden layer dimensions.
        :param dropout_rate: Dropout probability for regularization.
        """
        super().__init__()
        if hidden_dims is None:
            hidden_dims = [128, 64, 32]

        layers = []
        prev_dim = input_dim

        for h_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, h_dim))
            layers.append(nn.BatchNorm1d(h_dim))
            layers.append(nn.ReLU(inplace=True))
            layers.append(nn.Dropout(p=dropout_rate))
            prev_dim = h_dim

        # Final classification head
        layers.append(nn.Linear(prev_dim, num_classes))
        self.network = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        :param x: Input tensor of shape (batch_size, input_dim).
        :return: Logits of shape (batch_size, num_classes).
        """
        return self.network(x)


class GestureCNN(nn.Module):
    """Compact Convolutional Neural Network for raw hand gesture image recognition."""

    def __init__(
        self,
        num_classes: int = 27,
        in_channels: int = 1,
        input_size: int = 64,
    ) -> None:
        """
        Initialize the Gesture CNN.

        :param num_classes: Number of gesture categories (e.g. 27 for ASL A-Z + space).
        :param in_channels: Number of input channels (1 for Grayscale, 3 for RGB).
        :param input_size: Image height/width (assumed square).
        """
        super().__init__()

        self.features = nn.Sequential(
            # Block 1: in_channels -> 32
            nn.Conv2d(in_channels, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),  # input_size / 2
            # Block 2: 32 -> 64
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),  # input_size / 4
            # Block 3: 64 -> 128
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),  # input_size / 8
        )

        # Calculate flattened feature dimension
        spatial_dim = input_size // 8
        flattened_dim = 128 * spatial_dim * spatial_dim

        self.classifier = nn.Sequential(
            nn.Dropout(p=0.3),
            nn.Linear(flattened_dim, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.3),
            nn.Linear(128, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        :param x: Image tensor of shape (batch_size, in_channels, H, W).
        :return: Logits of shape (batch_size, num_classes).
        """
        features = self.features(x)
        flattened = torch.flatten(features, 1)
        return self.classifier(flattened)
