"""
evaluate.py
-----------
Stand-alone testing and evaluation script:
Loads trained model weights from the models/ directory,
evaluates performance against test sets, and displays full classification metrics.
"""

import argparse
import json
import os
import sys
import torch
import torch.nn as nn
from sklearn.metrics import classification_report, confusion_matrix

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


def evaluate_mlp(model_path: str, meta_path: str, dataset_type: str = "archive5") -> None:
    """Evaluate saved MLP checkpoint on test split."""
    if not os.path.exists(model_path) or not os.path.exists(meta_path):
        print(f"Error: Missing model file '{model_path}' or metadata '{meta_path}'. Run train.py first.")
        return

    with open(meta_path, "r") as f:
        meta = json.load(f)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if dataset_type == "archive5":
        _, test_loader, encoder, in_dim, num_classes = load_archive5_data()
    else:
        _, test_loader, encoder, in_dim, num_classes = load_archive6_data()

    model = GestureLandmarkMLP(
        input_dim=meta["input_dim"],
        num_classes=meta["num_classes"],
        hidden_dims=[128, 64, 32],
    ).to(device)

    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()

    criterion = nn.CrossEntropyLoss()
    total_loss = 0.0
    correct = 0
    total = 0
    all_preds = []
    all_targets = []

    with torch.no_grad():
        for inputs, targets in test_loader:
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

    accuracy = (correct / total) * 100.0
    avg_loss = total_loss / total

    print(f"\n=======================================================")
    print(f" EVALUATION REPORT: {dataset_type.upper()}")
    print(f"=======================================================")
    print(f"Test Loss: {avg_loss:.4f} | Test Accuracy: {accuracy:.2f}% ({correct}/{total} correct)")
    print("\nClassification Metrics:")
    print(classification_report(all_targets, all_preds, target_names=meta["classes"]))
    print("Confusion Matrix:")
    print(confusion_matrix(all_targets, all_preds))
    print("=======================================================\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Trained Gesture Recognition Models")
    parser.add_argument(
        "--dataset",
        type=str,
        choices=["archive5", "archive6"],
        default="archive5",
        help="Dataset to evaluate on",
    )
    args = parser.parse_args()

    model_path = f"models/gesture_mlp_{args.dataset}.pth"
    meta_path = f"models/classes_{args.dataset}.json"
    evaluate_mlp(model_path, meta_path, dataset_type=args.dataset)


if __name__ == "__main__":
    main()
