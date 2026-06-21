# Python OOP — Technical Screening Bank

A self-contained interview kit for screening **mid-to-senior full-stack data scientists** on
object-oriented Python.

## What's here
- **`index.html`** — the complete deliverable. Open it in any browser; no internet or build step.
  It contains both:
  1. **Question bank** — 20 questions, each solvable in ≤15 min (a 1-hour session fits 3–4).
  2. **Interviewer guide** — for every question: reference solution, skills tested, a
     point-by-point explanation, 0–4 scoring anchors, "reward / watch for" notes, and follow-ups.

## Using it
- **Interviewer guide** (default view) shows full solutions and rubrics — use it to train
  interviewers and standardize grading.
- **Candidate sheet** (top-right toggle) hides all solutions for a clean question sheet; **Print / PDF**
  always renders the full guide.
- **Tier filter** (Foundational / Intermediate / Advanced) and a **coverage map** with suggested
  balanced 1-hour sets help you assemble a session.

## Design notes
- Topics span the OOP surface a full-stack DS actually uses: class/instance state, the data model
  (`__repr__`, `__eq__`/`__hash__`, operators, `__call__`), dataclasses, ABCs vs `Protocol`,
  context managers, iteration, `__slots__`, descriptors, MRO/cooperative mixins, composition vs
  inheritance, exceptions, the Strategy/Factory pattern, a scikit-learn-style transformer,
  copy semantics, and **serialization/reproducibility** of fitted objects.
- Examples are framed on real DS objects (estimators, configs, feature/cache keys, mergeable
  aggregates, loss objects) rather than generic CS toys.
- Every reference solution was executed on CPython to confirm it runs and is correct.
- Calibration principle baked into the rubric: a candidate who reaches for
  NumPy/pandas/`dataclasses`/sklearn (and explains *when* hand-rolling is justified) scores
  **higher**, not lower.

The question set was drafted, then reviewed by a software-engineering pass (correctness, timing,
coverage) and a data-science pass (role relevance, realism), and revised to incorporate both.
