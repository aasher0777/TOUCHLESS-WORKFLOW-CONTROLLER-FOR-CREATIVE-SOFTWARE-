# 🎯 Member 4: OS Context & Automation Specialist (Swastik)

## 📌 Responsibilities & Architecture Role
* **Context Routing Queries**: Active foreground application detection using `pygetwindow` with low-overhead TTL caching to detect target creative suites (**Adobe Premiere Pro**, **Figma**), browsers, media players, and presentation software.
* **Application Profile Matching**: Routes classified gestures to application-specific macro actions (e.g. Razor Cut in Premiere Pro, Undo in Figma, Volume control in media players).
* **Dual-Engine Macro Dispatch**: Executes native hotkeys with instantaneous low-level `keyboard` library dispatch combined with `pyautogui` for mouse clicks and cursor operations.
* **Profile Persistence**: Custom profiles saved and restored from [`custom_profiles.json`](custom_profiles.json).

## 📁 Contained Files
* [`member_4.py`](member_4.py): Application context detector, macro routing tables, and keyboard/mouse dispatch engine.
* [`custom_profiles.json`](custom_profiles.json): Persistent customized shortcut profiles.

## 🚀 Independent Testing
```bash
python -c "from member_4 import OSMacroController; osm = OSMacroController(); print('Premiere detected:', osm.detect_context('Adobe Premiere Pro 2024'))"
```
