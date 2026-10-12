# Agent Guidelines: Ponytail Philosophy

This project strictly adheres to the **Ponytail** engineering philosophy:

1. **YAGNI (You Ain't Gonna Need It)**: Do not add unrequested features, premature abstractions, or dead code.
2. **Reuse Existing Code**: Check existing member modules (`member_1/member_1.py` through `member_5/member_5.py`) before adding new utilities.
3. **Use the Standard Library**: Use built-in C-accelerated modules (e.g. `math.dist`) over custom loops.
4. **Minimal, Clean Code**: Keep implementations concise, readable, and well-typed.
5. **Continuous Verification**: Any refactoring or optimization must pass `python verify_all.py` with 100% success.
