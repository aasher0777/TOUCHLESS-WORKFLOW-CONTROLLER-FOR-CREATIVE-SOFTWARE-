# Contributing to Gesture Studio Pro

Thank you for your interest in contributing to **Gesture Studio Pro (Touchless Workflow Controller for Creative Software)**! We welcome contributions from developers, machine learning researchers, and creative professionals.

---

## 📌 Development Philosophy: Ponytail Principles

This project strictly adheres to pragmatic, clean engineering practices:

1. **YAGNI (You Ain't Gonna Need It)**: Avoid adding unrequested features, premature abstractions, or dead code.
2. **Code Reuse**: Leverage existing utilities and member modules (`member_1` through `member_5`, `utils.py`) before inventing new ones.
3. **Use the Standard Library**: Prioritize standard library performance (e.g. `math.dist`, `collections.deque`) over bloated dependencies.
4. **Minimal, Clean Code**: Maintain concise, type-annotated, readable implementations.
5. **Continuous Verification**: All changes must pass `python verify_all.py` with 100% success before submitting a pull request.

---

## 🛠️ Local Development Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/aasher0777/TOUCHLESS-WORKFLOW-CONTROLLER-FOR-CREATIVE-SOFTWARE-.git
   cd TOUCHLESS-WORKFLOW-CONTROLLER-FOR-CREATIVE-SOFTWARE-
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   pip install flake8 pytest pyinstaller
   ```

4. **Verify the installation**:
   ```bash
   python verify_all.py
   ```

---

## 🧪 Testing Guidelines

Before opening any Pull Request:
- Run the full end-to-end subsystem verification suite:
  ```bash
  python verify_all.py
  ```
- Run flake8 linting to ensure clean formatting:
  ```bash
  flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
  ```
- If you modified neural architectures or training code, verify model evaluation:
  ```bash
  python member_2/evaluate.py --dataset archive5
  python member_2/evaluate.py --dataset archive6
  ```

---

## 🌿 Git Branching & Commit Conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat: add palm rotation angle calculation`
- `fix: resolve pyautogui coordinate drift on secondary monitor`
- `docs: update gesture mapping table in README`
- `refactor: optimize Euclidean distance matrix with math.dist`
- `perf: reduce camera acquisition latency in ring buffer`
- `test: add unit test for Node 4-8 pinch hysteresis`

### Pull Request Process

1. Create a descriptive feature branch (`git checkout -b feat/your-feature-name`).
2. Implement your changes following PEP 8 conventions and type annotations.
3. Verify all tests pass locally (`python verify_all.py`).
4. Commit your changes with clear commit messages.
5. Push to your fork and submit a Pull Request to `main`.
6. Fill out the PR template completely.

---

## ⚖️ Code of Conduct

Please note that this project is released with a [Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project, you agree to abide by its terms.
