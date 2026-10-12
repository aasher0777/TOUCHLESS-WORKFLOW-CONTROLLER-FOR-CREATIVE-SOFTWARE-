---
name: ponytail
description: >-
  Pragmatic Senior Developer Skill based on DietrichGebert/ponytail.
  Applies the decision ladder: YAGNI, code reuse, standard library optimization,
  and minimal concise implementations while strictly preserving safety and tests.
---

# 🐴 Ponytail: Pragmatic Senior Developer Skill

When activated, this skill guides optimization, refactoring, and code generation using the **Decision Ladder**.

## Core Directive
> "The best code is the code you never wrote."

## The 7-Rung Decision Ladder
1. **YAGNI (You Ain't Gonna Need It)**: Eliminate speculative code, duplicate files, and dead abstractions.
2. **Reuse**: Check if the function, class, or pattern already exists in the codebase before adding new code.
3. **Standard Library**: Prefer native standard library solutions (e.g. `math.dist`, `pathlib.Path`, `dataclasses`, `functools.lru_cache`) over custom math or utility loops.
4. **Native Platform Features**: Leverage OS/platform features directly.
5. **Existing Dependencies**: Avoid adding new dependencies when existing libraries (`numpy`, `cv2`, `torch`) can do the job.
6. **Conciseness**: Simplify multi-line boilerplate into readable, direct expressions.
7. **Minimum Code**: Write only what is strictly necessary to satisfy requirements.

## Review & Audit Commands
- When reviewing files, identify duplicate logic, dead imports, redundant math loops, and unneeded files.
- Ensure all test suites (`verify_all.py`) continue to pass after any optimization.
