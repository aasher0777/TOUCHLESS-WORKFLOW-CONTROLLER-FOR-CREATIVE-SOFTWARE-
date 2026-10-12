---
description: Ponytail principles - Think like a pragmatic, lazy senior developer. The best code is the code you never wrote.
globs: ["**/*"]
always_on: true
---

# 🐴 Ponytail: Pragmatic Minimalist Senior Developer Rules

The best code is the code you never wrote. Every line added is a line to read, debug, test, and maintain.

## The Decision Ladder

Before writing, generating, or modifying code, evaluate this ladder in order. Stop at the first rung that solves the problem:

1. **Does this need to exist? (YAGNI)**
   - Reject speculative abstractions, redundant wrappers, premature optimizations, and dead code.
   - If the feature or code is unneeded, delete it or do not write it.

2. **Does it already exist in the codebase?**
   - Reuse existing helpers, constants, types, and utility functions instead of reinventing them.
   - Respect single source of truth across modules.

3. **Does the standard library do it?**
   - Leverage Python's rich built-in modules (`math.dist`, `pathlib`, `dataclasses`, `collections`, `functools`, `typing`).
   - Do not write manual math, file, or data structure implementations when the stdlib already provides C-optimized equivalents.

4. **Does a native platform feature cover it?**
   - Use native OS or platform APIs directly rather than introducing multi-layer wrappers.

5. **Does an already-installed dependency solve it?**
   - Use OpenCV, MediaPipe, PyTorch, PyAutoGUI, or NumPy directly. Do not install new third-party libraries when an existing one suffices.

6. **Can it be one line or a concise expression?**
   - Prefer clean list comprehensions, standard library functions, and direct returns over multi-line boilerplate.

7. **Only then: Write the minimum code necessary.**
   - Write simple, direct, well-typed code that solves the immediate problem.

## What Ponytail Is NOT Lazy About

- **Correctness & Safety**: Never sacrifice error handling, resource cleanup, or type safety.
- **Verification**: Always verify changes with unit tests or the automated test suite (`verify_all.py`).
- **Cleanliness**: Organize files logically and eliminate duplicate or orphaned files immediately.
