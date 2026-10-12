"""
train.py
--------
Training and testing pipeline for hand gesture classification:
- Trains GestureLandmarkMLP on archive (5) (Rock, Paper, Scissors: 45,050 samples)
- Trains GestureLandmarkMLP on archive (6) (Gesture landmarks: 364 samples)
- Trains GestureCNN on archive (10) (Hand images: A-Z + space)
- Generates comprehensive testing metrics (Loss, Accuracy, Classification Report, Confusion Matrix)
- Saves checkpoints to models/ directory.
"""

import argparse
import json
import os
import sys
import time
from typing import Dict, List, Tuple
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import classification_report, confusion_matrix

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

try:
    from member_2.dataset import load_archive5_data, load_archive6_data, load_archive10_data
    from member_2.model import GestureLandmarkMLP, GestureCNN
except ImportError:
    from dataset import load_archive5_data, load_archive6_data, load_archive10_data
    from model import GestureLandmarkMLP, GestureCNN



def train_epoch(
    model: nn.Module,
    loader: torch.utils.data.DataLoader,
    criterion: nn.Module,
    optimizer: optim.Optimizer,
    device: torch.device,
) -> Tuple[float, float]:
    """Train for one epoch."""
    model.train()
    total_loss = 0.0
    correct = 0
    total = 0

    for inputs, targets in loader:
        inputs = inputs.to(device)
        targets = targets.to(device)

        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * inputs.size(0)
        _, preds = torch.max(outputs, 1)
        correct += (preds == targets).sum().item()
        total += targets.size(0)

    avg_loss = total_loss / total
    accuracy = (correct / total) * 100.0
    return avg_loss, accuracy


def evaluate(
    model: nn.Module,
    loader: torch.utils.data.DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> Tuple[float, float, List[int], List[int]]:
    """Evaluate on a validation or test set."""
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0
    all_preds: List[int] = []
    all_targets: List[int] = []

    with torch.no_grad():
        for inputs, targets in loader:
            inputs = inputs.to(device)
            targets = targets.to(device)

            outputs = model(inputs)
            loss = criterion(outputs, targets)

            total_loss += loss.item() * inputs.size(0)
            _, preds = torch.max(outputs, 1)
            correct += (preds == targets).sum().item()
            total += targets.size(0)

            all_preds.extend(preds.cpu().tolist())
            all_targets.extend(targets.cpu().tolist())

    avg_loss = total_loss / total
    accuracy = (correct / total) * 100.0
    return avg_loss, accuracy, all_preds, all_targets


def train_landmark_model(
    dataset_type: str = "archive5",
    epochs: int = 10,
    lr: float = 0.001,
    models_dir: str = "models",
) -> None:
    """Train and test GestureLandmarkMLP."""
    print("=" * 70)
    print(f"🚀 Training GestureLandmarkMLP on {dataset_type.upper()}")
    print("=" * 70)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    if dataset_type == "archive5":
        train_loader, test_loader, encoder, in_dim, num_classes = load_archive5_data()
    else:
        train_loader, test_loader, encoder, in_dim, num_classes = load_archive6_data()

    print(f"Features: {in_dim} dimensions | Classes ({num_classes}): {list(encoder.classes_)}")
    print(f"Training samples: {len(train_loader.dataset)} | Test samples: {len(test_loader.dataset)}")

    model = GestureLandmarkMLP(
        input_dim=in_dim,
        num_classes=num_classes,
        hidden_dims=[128, 64, 32],
        dropout_rate=0.2,
    ).to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=2)

    best_test_acc = 0.0
    best_preds: List[int] = []
    best_targets: List[int] = []

    start_time = time.time()
    for epoch in range(1, epochs + 1):
        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, device)
        test_loss, test_acc, preds, targets = evaluate(model, test_loader, criterion, device)
        scheduler.step(test_loss)

        if test_acc > best_test_acc:
            best_test_acc = test_acc
            best_preds = preds
            best_targets = targets

        print(
            f"Epoch {epoch:02d}/{epochs:02d} | "
            f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}% | "
            f"Test Loss: {test_loss:.4f}, Test Acc: {test_acc:.2f}%"
        )

    duration = time.time() - start_time
    print(f"\n✅ Training completed in {duration:.2f} seconds. Best Test Accuracy: {best_test_acc:.2f}%\n")

    # Classification Report
    print("-" * 50)
    print("📊 CLASSIFICATION REPORT (TEST SET):")
    print("-" * 50)
    print(classification_report(best_targets, best_preds, target_names=[str(c) for c in encoder.classes_]))

    print("🧩 CONFUSION MATRIX:")
    cm = confusion_matrix(best_targets, best_preds)
    print(cm)

    # Save model and metadata
    os.makedirs(models_dir, exist_ok=True)
    model_path = os.path.join(models_dir, f"gesture_mlp_{dataset_type}.pth")
    meta_path = os.path.join(models_dir, f"classes_{dataset_type}.json")

    torch.save(model.state_dict(), model_path)
    with open(meta_path, "w") as f:
        json.dump(
            {
                "input_dim": in_dim,
                "num_classes": num_classes,
                "classes": [str(c) for c in encoder.classes_],
                "test_accuracy": best_test_acc,
            },
            f,
            indent=2,
        )
    print(f"\n💾 Model weights saved to: {model_path}")
    print(f"📄 Class metadata saved to: {meta_path}\n")


def train_image_cnn(
    epochs: int = 5,
    samples_per_class: int = 50,
    image_size: int = 64,
    lr: float = 0.001,
    models_dir: str = "models",
) -> None:
    """Train and test GestureCNN on archive (10) own_dataset."""
    print("=" * 70)
    print("🚀 Training GestureCNN on ARCHIVE (10) (own_dataset)")
    print("=" * 70)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    train_loader, test_loader, encoder, num_classes = load_archive10_data(
        image_size=image_size, samples_per_class=samples_per_class
    )

    print(f"Classes ({num_classes}): {list(encoder.classes_)}")
    print(f"Training samples: {len(train_loader.dataset)} | Test samples: {len(test_loader.dataset)}")

    model = GestureCNN(
        num_classes=num_classes,
        in_channels=1,
        input_size=image_size,
    ).to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    best_test_acc = 0.0
    best_preds: List[int] = []
    best_targets: List[int] = []

    start_time = time.time()
    for epoch in range(1, epochs + 1):
        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, device)
        test_loss, test_acc, preds, targets = evaluate(model, test_loader, criterion, device)

        if test_acc > best_test_acc:
            best_test_acc = test_acc
            best_preds = preds
            best_targets = targets

        print(
            f"Epoch {epoch:02d}/{epochs:02d} | "
            f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}% | "
            f"Test Loss: {test_loss:.4f}, Test Acc: {test_acc:.2f}%"
        )

    duration = time.time() - start_time
    print(f"\n✅ Training completed in {duration:.2f} seconds. Best Test Accuracy: {best_test_acc:.2f}%\n")

    # Classification Report
    print("-" * 50)
    print("📊 CLASSIFICATION REPORT (TEST SET):")
    print("-" * 50)
    print(classification_report(best_targets, best_preds, target_names=[str(c) for c in encoder.classes_]))

    # Save model and metadata
    os.makedirs(models_dir, exist_ok=True)
    model_path = os.path.join(models_dir, "gesture_cnn_archive10.pth")
    meta_path = os.path.join(models_dir, "classes_archive10.json")

    torch.save(model.state_dict(), model_path)
    with open(meta_path, "w") as f:
        json.dump(
            {
                "input_size": image_size,
                "in_channels": 1,
                "num_classes": num_classes,
                "classes": [str(c) for c in encoder.classes_],
                "test_accuracy": best_test_acc,
            },
            f,
            indent=2,
        )
    print(f"\n💾 Model weights saved to: {model_path}")
    print(f"📄 Class metadata saved to: {meta_path}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and Test Gesture Classification Models")
    parser.add_argument(
        "--dataset",
        type=str,
        choices=["archive5", "archive6", "archive10", "all"],
        default="all",
        help="Dataset to train on (default: all)",
    )
    parser.add_argument("--epochs", type=int, default=8, help="Number of training epochs")
    parser.add_argument("--lr", type=float, default=0.001, help="Learning rate")
    args = parser.parse_args()

    if args.dataset in ("archive5", "all"):
        train_landmark_model(dataset_type="archive5", epochs=args.epochs, lr=args.lr)

    if args.dataset in ("archive6", "all"):
        train_landmark_model(dataset_type="archive6", epochs=args.epochs, lr=args.lr)

    if args.dataset in ("archive10", "all"):
        train_image_cnn(epochs=5, samples_per_class=40, image_size=64, lr=args.lr)


if __name__ == "__main__":
    main()
