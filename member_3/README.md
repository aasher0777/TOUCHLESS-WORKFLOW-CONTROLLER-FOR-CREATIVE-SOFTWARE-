# 📐 Member 3: State-Machine Logic Developer (Subham)

## 📌 Responsibilities & Architecture Role
* **3D Gesture Dictionary**: Formalizes the mathematical gesture dictionary (`GESTURE_DICTIONARY`) mapping 9 distinct gestures to 3D joint node indices, key formulas, and actionable trigger rules.
* **Continuous Euclidean Distance Engine**: Fast C-accelerated Euclidean distance calculations (`math.dist`) between arbitrary landmark pairs (e.g. Node 4 Thumb Tip to Node 8 Index Tip).
* **State-Machine & Dynamic Thresholds**: Dynamic hand-scale normalization ($d(\text{Wrist}, \text{Middle MCP})$), directional velocity tracking (swipes), debounce cooldown timers, and pinch state classification.

## 📁 Contained Files
* [`member_3.py`](member_3.py): Gesture definitions, state machine, distance calculations, and classifier logic.

## 🚀 Independent Testing
```bash
python -c "from member_3 import GestureClassifier, GESTURE_DICTIONARY; print('Gestures mapped:', len(GESTURE_DICTIONARY))"
```
