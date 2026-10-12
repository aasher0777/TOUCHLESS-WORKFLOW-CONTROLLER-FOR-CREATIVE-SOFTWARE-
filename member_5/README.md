# 🖥️ Member 5: Packaging, UI & Release Manager ([rusher11225-del](https://github.com/rusher11225-del))

## 📌 Responsibilities & Architecture Role
* **Visual Dashboard & Developer Workbench**: Lightweight dark-themed Tkinter dashboard (`member_5.py`) featuring an interactive gesture catalog, live 2D/3D skeleton canvas with glowing node halos, real-time Euclidean distance gauge, synthetic calibration simulator, and JSON profile manager.
* **Standalone Binary Packaging**: PyInstaller packaging script (`package_app.py`) and Windows distribution build spec (`gesture_controller.spec`) that bundles MediaPipe models, OpenCV, PyTorch, and all dependencies into a portable one-click `.exe`.
* **CI/CD Automation & Landing Page**: Multi-OS GitHub Actions workflow ([`.github/workflows/build_pipeline.yml`](../.github/workflows/build_pipeline.yml)) for linting, bytecode testing, binary packaging, and automated deployment to GitHub Pages landing page ([`docs/index.html`](../docs/index.html)).

## 📁 Contained Files
* [`member_5.py`](member_5.py): Modern dashboard, landmark canvas, distance gauge, and developer workbench.
* [`package_app.py`](package_app.py): Automated PyInstaller builder script.
* [`gesture_controller.spec`](gesture_controller.spec): Standalone executable configuration.

## 🚀 Independent Testing
```bash
python member_5/package_app.py
```
