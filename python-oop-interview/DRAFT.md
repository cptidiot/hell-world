# Python OOP — Technical Screening Question Bank (DRAFT v1)
**Role:** Full-Stack Data Scientist (mid → senior) · **Format:** 1-hour session, 3–4 questions · **Per-question budget:** ≤15 min

---

## How to run a session (interviewer)
- Pick 3–4 questions spanning difficulty tiers (≥1 Foundational warm-up, ≥1 Advanced).
- Share the prompt; let the candidate think aloud. Code can be on a shared editor or whiteboard.
- Score each question 0–4 (rubric below). Capture *signal*, not just correctness.
- Senior bar: clears Advanced questions with little prompting + articulates trade-offs.

### Scoring rubric (per question, 0–4)
- **0 — No signal:** cannot start; fundamental misconceptions.
- **1 — Emerging:** partial recall, needs heavy hints, code doesn't run.
- **2 — Competent:** correct core answer with minor gaps; runs after small fixes.
- **3 — Strong:** correct, idiomatic, explains *why*, handles edge cases.
- **4 — Exceptional:** all of 3 + trade-offs, alternatives, performance/maintenance lens, teaches the interviewer something.

Difficulty tiers: **F** = Foundational, **M** = Intermediate, **A** = Advanced.

---

## Q1 — The shared mutable class attribute [F · attributes · 10 min]
**Prompt:** A teammate reports that two `Dataset` objects seem to share data: adding a sample to one shows up in the other.
```python
class Dataset:
    samples = []
    def __init__(self, name):
        self.name = name
    def add(self, x):
        self.samples.append(x)
```
Explain the bug and fix it. What's the difference between a class attribute and an instance attribute?

**Solution:**
```python
class Dataset:
    def __init__(self, name):
        self.name = name
        self.samples = []          # per-instance
    def add(self, x):
        self.samples.append(x)
```
**Skills tested:** attribute lookup, mutability vs. rebinding, the most common Python OOP bug.
**Explanation:**
- `samples` is defined on the *class*, so all instances share one list object.
- `self.samples.append(x)` reads `samples` (found on the class, since no instance attribute shadows it) and **mutates it in place** — it never rebinds, so every instance sees the change.
- Assignment in `__init__` (`self.samples = []`) creates a distinct instance attribute that shadows the class one.
- Class attributes are appropriate for **constants/shared config** (e.g., `DEFAULT_BATCH = 32`); mutable class attributes are a footgun.
**Strong vs. weak:** Weak: "just move it into `__init__`" with no reason. Strong: explains lookup order + mutate-vs-rebind, notes the same trap appears with mutable default arguments.
**Follow-up:** Show `def add(self, x, bucket=[])` — same bug class.

---

## Q2 — `__repr__` vs `__str__` [F · data model · 10 min]
**Prompt:** When do you implement `__repr__` vs `__str__`? Write a `Money` class (amount + currency) with both. What happens if you define only one?

**Solution:**
```python
class Money:
    def __init__(self, amount, currency="USD"):
        self.amount = amount
        self.currency = currency
    def __repr__(self):
        return f"Money(amount={self.amount!r}, currency={self.currency!r})"
    def __str__(self):
        return f"{self.amount:,.2f} {self.currency}"
```
**Skills tested:** the two string protocols, developer ergonomics, debuggability.
**Explanation:**
- `__repr__`: unambiguous, developer-facing, ideally round-trips (`eval(repr(x)) == x`). Used in the REPL, in containers (a list of objects prints each `repr`), and in logs/tracebacks.
- `__str__`: human-readable, end-user facing. Used by `print()`, `str()`, and f-string `{x}`.
- If only `__repr__` is defined, `__str__` falls back to it. **Not** the reverse — define `__repr__` first.
**Strong vs. weak:** Strong candidate notes that containers always use `repr`, and that a good `__repr__` is the single highest-leverage debugging aid; mentions `!r` conversion in f-strings.
**Follow-up:** Why might `repr` not be `eval`-able for some objects, and is that OK? (Yes — "looks like a useful description" is the real rule.)

---

## Q3 — `@classmethod` vs `@staticmethod`, alternative constructors [F/M · methods · 12 min]
**Prompt:** Explain instance method vs `@classmethod` vs `@staticmethod`. Add an alternative constructor `from_csv` and a validation helper to a `TimeSeries`. Why return `cls(...)` rather than `TimeSeries(...)`?

**Solution:**
```python
class TimeSeries:
    def __init__(self, timestamps, values):
        self.timestamps = timestamps
        self.values = values

    @classmethod
    def from_csv(cls, path):
        ts, vals = [], []
        with open(path) as f:
            for line in f:
                t, v = line.strip().split(",")
                ts.append(t); vals.append(float(v))
        return cls(ts, vals)            # respects subclasses

    @staticmethod
    def is_regular(timestamps):
        return len(set(b - a for a, b in zip(timestamps, timestamps[1:]))) <= 1
```
**Skills tested:** factory pattern, the role of `cls`, inheritance-awareness, namespacing utilities.
**Explanation:**
- **Instance method** takes `self`; operates on one object.
- **classmethod** takes `cls`; ideal for **alternative constructors / factories**. Using `cls` means a subclass `Daily(TimeSeries)` gets `Daily.from_csv(...)` returning a `Daily`, not a `TimeSeries`.
- **staticmethod** takes no implicit arg; a plain function namespaced under the class for cohesion/discoverability.
**Strong vs. weak:** Strong candidate immediately reaches for `@classmethod` for `from_csv` and explains the subclass-correctness benefit of `cls`.
**Follow-up:** Could `is_regular` be a module function? (Yes — staticmethod is mostly about cohesion; some teams prefer module functions.)

---

## Q4 — `@property`: computed & validated attributes [F/M · encapsulation · 12 min]
**Prompt:** Make `fahrenheit` a read-only computed property derived from `celsius`, and validate that `celsius` is never below absolute zero. When is a property worth it, and what does it cost?

**Solution:**
```python
class Reading:
    def __init__(self, celsius):
        self.celsius = celsius              # routes through the setter

    @property
    def celsius(self):
        return self._celsius

    @celsius.setter
    def celsius(self, value):
        if value < -273.15:
            raise ValueError("below absolute zero")
        self._celsius = value

    @property
    def fahrenheit(self):
        return self._celsius * 9 / 5 + 32
```
**Skills tested:** encapsulation without breaking the API, computed attributes, validation placement.
**Explanation:**
- A property exposes **attribute syntax** (`r.fahrenheit`) backed by **method behavior** (compute/validate).
- Killer feature: you can turn a plain attribute into a property **without changing callers** — so start with public attributes and add properties only when you need logic (Python's "uniform access principle").
- `__init__` assigning `self.celsius` reuses the setter's validation — no duplication.
- Cost: per-access function-call overhead; risk of hiding expensive work behind innocent-looking attribute access.
**Strong vs. weak:** Strong candidate avoids premature getters/setters ("don't write Java in Python"), and notes properties make read-only/derived values clean.
**Follow-up:** Add a `fahrenheit` setter that updates `celsius`. Or: what about `functools.cached_property` for an expensive derived value?

---

## Q5 — Inheritance and `super()` [F/M · inheritance · 10 min]
**Prompt:** Implement `BaseModel(name)` and `LinearModel(name, learning_rate)` that extends it. Use `super()` correctly. What does `super()` actually return, and why avoid `BaseModel.__init__(self, ...)`?

**Solution:**
```python
class BaseModel:
    def __init__(self, name):
        self.name = name

class LinearModel(BaseModel):
    def __init__(self, name, learning_rate=0.01):
        super().__init__(name)
        self.learning_rate = learning_rate
```
**Skills tested:** subclass initialization, cooperative inheritance, MRO awareness.
**Explanation:**
- `super()` returns a **proxy object** that dispatches attribute lookups to the **next class in the MRO** of `type(self)` — not necessarily the literal parent.
- Hardcoding `BaseModel.__init__(self, ...)` breaks under multiple inheritance (it can skip or double-call siblings) and is fragile if the hierarchy changes.
- `super()` (no-arg form) is Python 3 sugar for `super(LinearModel, self)`.
**Strong vs. weak:** Strong candidate says "next in MRO," not "the parent," and knows the no-arg form.
**Follow-up:** leads naturally into Q6.

---

## Q6 — MRO and the diamond problem [A · MRO · 15 min]
**Prompt:** Predict the output and `D.__mro__`. Why does `A` print once?
```python
class A:
    def process(self): print("A")
class B(A):
    def process(self): print("B"); super().process()
class C(A):
    def process(self): print("C"); super().process()
class D(B, C):
    def process(self): print("D"); super().process()

D().process()
```
**Solution:** Output:
```
D
B
C
A
```
`D.__mro__ == [D, B, C, A, object]`.
**Skills tested:** C3 linearization, cooperative `super()`, the real mental model of method dispatch.
**Explanation:**
- MRO is computed by **C3 linearization**: a consistent order preserving local precedence (B before C because `D(B, C)`) and monotonicity.
- `super()` walks **the MRO**, not the class's own parents. So inside `B`, `super().process()` goes to `C` (the next class after B in `D`'s MRO), **not** `A`.
- `A` runs once because each class appears once in the MRO — this is exactly what cooperative `super()` chains solve (no duplicate base calls in a diamond).
**Strong vs. weak:** Weak: predicts `D B A C A` (thinks super == parent). Strong: states C3 rules and the "super follows the instance's MRO" insight.
**Follow-up:** What if `B` called `A.process(self)` directly? (`C` would be skipped — the classic diamond bug.) Why must `super().process()` be called in each method for the chain to work?

---

## Q7 — `__eq__` / `__hash__` contract [M · data model · 12 min]
**Prompt:** Make a `Point(x, y)` value object usable as a `dict` key and `set` member. What happens to hashability once you define `__eq__`? State the `__eq__`/`__hash__` contract.

**Solution:**
```python
class Point:
    def __init__(self, x, y):
        self.x, self.y = x, y
    def __eq__(self, other):
        if not isinstance(other, Point):
            return NotImplemented
        return (self.x, self.y) == (other.x, other.y)
    def __hash__(self):
        return hash((self.x, self.y))
```
**Skills tested:** the hash/eq invariant, value semantics, how `set`/`dict` actually work, `NotImplemented`.
**Explanation:**
- Defining `__eq__` makes the class **unhashable** (`__hash__` is set to `None`) — Python's safety default, since custom equality usually invalidates the default identity hash.
- **Contract:** `a == b` ⟹ `hash(a) == hash(b)`. (The converse need not hold — collisions are fine.) Hash must depend only on fields used in `__eq__`, and those fields should be **immutable** (mutating a key corrupts the container).
- Returning `NotImplemented` (not `False`) lets Python try `other.__eq__(self)` — correct for cross-type comparisons.
**Strong vs. weak:** Strong candidate mentions immutability of hashed fields and `NotImplemented` vs `False`; may reach for `@dataclass(frozen=True)` as the idiomatic shortcut.
**Follow-up:** What breaks if `x`/`y` are mutable and you change them after inserting into a set?

---

## Q8 — Dataclasses done right [M · modern Python · 12 min]
**Prompt:** Rewrite a boilerplate-heavy class as a `@dataclass`: make it immutable, give a field a **mutable default** safely, and exclude a timestamp from equality. Why does `@dataclass` reject mutable defaults?

**Solution:**
```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Experiment:
    name: str
    params: dict = field(default_factory=dict)        # safe per-instance default
    created_at: float = field(default=0.0, compare=False)
```
**Skills tested:** modern stdlib fluency, recognizing the mutable-default trap (again), immutability/hashability.
**Explanation:**
- `@dataclass` generates `__init__`, `__repr__`, `__eq__` from annotated fields.
- A bare `params: dict = {}` would share one dict across instances (the Q1 bug). Dataclasses **raise `ValueError` at class definition** for known-mutable defaults; use `field(default_factory=...)`.
- `frozen=True` blocks attribute writes (`__setattr__` raises `FrozenInstanceError`) and makes instances **hashable** (eligible as dict keys / set members).
- `compare=False` excludes `created_at` from generated `__eq__`/ordering — two runs with the same config compare equal regardless of when they ran.
**Strong vs. weak:** Strong candidate knows `default_factory`, `frozen`, and per-field options; mentions `slots=True` (3.10+) for memory, `kw_only`, or `__post_init__` for validation.
**Follow-up:** How would you validate `name` is non-empty in a dataclass? (`__post_init__`.)

---

## Q9 — Abstract base classes & Protocols [M · interfaces · 13 min]
**Prompt:** Define an `Estimator` interface (`fit`, `predict`) with `abc`. Show that a subclass missing `predict` can't be instantiated. When prefer an ABC over duck typing? How does `typing.Protocol` differ?

**Solution:**
```python
from abc import ABC, abstractmethod

class Estimator(ABC):
    @abstractmethod
    def fit(self, X, y): ...
    @abstractmethod
    def predict(self, X): ...

class MeanRegressor(Estimator):
    def fit(self, X, y):
        self._mu = sum(y) / len(y); return self
    def predict(self, X):
        return [self._mu] * len(X)
# Missing predict -> TypeError at instantiation
```
With `Protocol` (structural typing):
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class SupportsPredict(Protocol):
    def predict(self, X): ...
```
**Skills tested:** interface design, fail-fast contracts, nominal vs structural typing.
**Explanation:**
- An ABC **can't be instantiated**; a concrete subclass that leaves any `@abstractmethod` unimplemented also can't (`TypeError` at construction) — fails fast and loudly.
- Choose **ABC** when you own the hierarchy, want a shared base/mixin logic, and want explicit `isinstance` contracts.
- Choose **`Protocol`** for **structural typing** ("if it has `predict`, it qualifies") — great for typing third-party/duck-typed objects you don't control, no inheritance required; checked by static type checkers (and at runtime if `@runtime_checkable`).
**Strong vs. weak:** Strong candidate frames it as nominal (ABC) vs structural (Protocol) and ties it to real DS code (sklearn-like estimators, accepting any object with `.predict`).
**Follow-up:** Can you give an ABC method a default implementation a subclass may override? (Yes.)

---

## Q10 — Operator overloading & `__radd__` for `sum()` [M · data model · 14 min]
**Prompt:** Implement a `Vector` supporting `+` (vector), `*` (scalar), `len()`, indexing, and `==`. Make `sum([v1, v2, v3])` work. Use `NotImplemented` correctly.

**Solution:**
```python
class Vector:
    def __init__(self, data):
        self.data = list(data)
    def __add__(self, other):
        if isinstance(other, Vector):
            return Vector(a + b for a, b in zip(self.data, other.data))
        return NotImplemented
    def __radd__(self, other):
        if other == 0:                 # sum() starts from int 0
            return self
        return NotImplemented
    def __mul__(self, scalar):
        return Vector(x * scalar for x in self.data)
    __rmul__ = __mul__
    def __len__(self):
        return len(self.data)
    def __getitem__(self, i):
        return self.data[i]
    def __eq__(self, other):
        return isinstance(other, Vector) and self.data == other.data
    def __repr__(self):
        return f"Vector({self.data})"
```
**Skills tested:** numeric data model, reflected operators, `NotImplemented` semantics, sequence protocol.
**Explanation:**
- `sum()` computes `0 + v1 + ...`; `0 + v1` calls `int.__add__` first → returns `NotImplemented` → Python falls back to `v1.__radd__(0)`. Hence `__radd__`.
- Returning the singleton **`NotImplemented`** (not raising, not `False`) tells Python to try the reflected operator; raising `TypeError` would short-circuit that.
- `__getitem__` + `__len__` give sequence-like behavior (iteration, indexing).
**Strong vs. weak:** Weak: forgets `__radd__`, so `sum()` raises `TypeError`. Strong: explains the reflected-operator fallback and the `NotImplemented` singleton vs the `NotImplementedError` exception.
**Follow-up:** What's the difference between `NotImplemented` and `NotImplementedError`? Add `start=Vector(...)` to `sum` to avoid `__radd__`.

---

## Q11 — Context managers [M · resource mgmt · 12 min]
**Prompt:** Write a `Timer` context manager two ways: a class (`__enter__`/`__exit__`) and `contextlib.contextmanager`. How does `__exit__` see exceptions, and when does returning `True` matter?

**Solution:**
```python
import time
from contextlib import contextmanager

class Timer:
    def __enter__(self):
        self.start = time.perf_counter()
        return self                      # bound to `as t`
    def __exit__(self, exc_type, exc, tb):
        self.elapsed = time.perf_counter() - self.start
        return False                     # don't suppress exceptions

@contextmanager
def timer():
    start = time.perf_counter()
    try:
        yield
    finally:
        print(f"{time.perf_counter() - start:.4f}s")
```
**Skills tested:** the context-manager protocol, deterministic cleanup, exception flow, `contextlib`.
**Explanation:**
- `__enter__`'s return value binds to the `as` target. `__exit__` always runs — normal exit or exception.
- On exception, `__exit__` receives `(exc_type, exc, tb)`; returning a **truthy** value **suppresses** the exception. Returning `False`/`None` lets it propagate (the safe default).
- In the generator form, `try/finally` around `yield` guarantees cleanup; code before `yield` is setup, after is teardown.
**Strong vs. weak:** Strong candidate warns against accidentally swallowing exceptions, knows `__enter__`'s return is the `as` value, and mentions reusing context managers for DB sessions / temp files / `torch.no_grad()`-style scopes.
**Follow-up:** How would you make `Timer` reentrant or support `contextlib.ExitStack` for many resources?

---

## Q12 — Iterables vs iterators (re-iterability) [M · iteration · 13 min]
**Prompt:** Build a `BatchLoader` that yields fixed-size batches from a sequence and can be iterated **multiple times**. What's the difference between an *iterable* and an *iterator*? Why can a class whose `__iter__` returns `self` only be iterated once?

**Solution:**
```python
class BatchLoader:
    def __init__(self, data, batch_size):
        self.data = data
        self.batch_size = batch_size
    def __iter__(self):                          # generator → fresh each time
        for i in range(0, len(self.data), self.batch_size):
            yield self.data[i:i + self.batch_size]
```
**Skills tested:** iteration protocol, generators, statefulness — directly relevant to data pipelines/`DataLoader`s.
**Explanation:**
- **Iterable**: implements `__iter__`, returning a fresh **iterator**. **Iterator**: implements `__next__` (and `__iter__` returning `self`); it is **stateful and single-use** (raises `StopIteration` when done).
- A `__iter__` written as a **generator** produces a brand-new iterator on every `for` loop → re-iterable.
- If instead the object *is* its own iterator (`__iter__` returns `self`, with `__next__` advancing a cursor), the cursor is shared/exhausted, so a second loop yields nothing.
**Strong vs. weak:** Strong candidate explains the re-iterability difference precisely and notes that generators give lazy, memory-efficient streaming (important for data that doesn't fit in memory).
**Follow-up:** Write the explicit `__iter__`/`__next__` version and show it exhausts after one pass.

---

## Q13 — `__slots__` and memory at scale [A · performance · 13 min]
**Prompt:** You instantiate tens of millions of small objects and hit memory limits. Explain `__slots__`, rewrite a class to use it, and list the trade-offs.

**Solution:**
```python
class Particle:
    __slots__ = ("x", "y", "mass")
    def __init__(self, x, y, mass):
        self.x, self.y, self.mass = x, y, mass
```
**Skills tested:** CPython object model, memory/perf awareness at data scale, knowing the costs.
**Explanation:**
- By default each instance carries a `__dict__` for dynamic attributes — flexible but heavy. `__slots__` stores attributes in a fixed, array-like layout: **less memory per instance** and slightly **faster attribute access**.
- Trade-offs: (1) **no new attributes** beyond the declared slots; (2) **no `__dict__`/`__weakref__`** unless explicitly added; (3) **inheritance caveats** — subclasses regain a `__dict__` unless they also define `__slots__`; multiple inheritance of two slotted classes with nonempty slots conflicts; (4) can clash with class-level defaults for slotted names.
**Strong vs. weak:** Strong candidate quantifies the win ("hundreds of bytes/instance → tens"), mentions profiling first, and knows alternatives (`@dataclass(slots=True)`, NumPy/`array`/columnar storage, which is usually the *real* fix for millions of records).
**Follow-up:** When is `__slots__` the wrong tool? (When the right answer is columnar/NumPy/pandas, not millions of Python objects.)

---

## Q14 — Composition over inheritance [A · design · 15 min]
**Prompt:** A `DataPipeline` needs optional, combinable behaviors: logging, caching, validation. Sketch why a class-per-combination inheritance design fails, then refactor to composition. When are mixins still appropriate?

**Solution (sketch):**
```python
class Pipeline:
    def __init__(self, steps, *, logger=None, cache=None, validator=None):
        self.steps = steps
        self.logger = logger or NullLogger()
        self.cache = cache or NullCache()
        self.validator = validator

    def run(self, data):
        if self.validator:
            self.validator.check(data)
        key = self.cache.key(data)
        if (hit := self.cache.get(key)) is not None:
            self.logger.info("cache hit"); return hit
        for step in self.steps:
            data = step(data)
        self.cache.set(key, data)
        self.logger.info("computed")
        return data
```
**Skills tested:** design judgment (SOLID), dependency injection, recognizing combinatorial inheritance explosion.
**Explanation:**
- Inheritance for behavior combos explodes: `LoggingPipeline`, `CachingPipeline`, `LoggingCachingValidatingPipeline`, … — N behaviors → 2ᴺ classes.
- **Composition** injects collaborators (strategy objects). Behaviors are independent, swappable, testable in isolation (pass a fake logger/cache). Null-object defaults keep `run()` branch-free.
- **Mixins** remain fine for *orthogonal, cross-cutting* behavior designed to cooperate via `super()` (e.g., a `SerializableMixin`), but avoid deep mixin stacks and shared mutable state.
**Strong vs. weak:** Strong candidate reaches for composition/DI quickly, talks testability and the open/closed principle, and doesn't over-engineer. This is an open question — score the *reasoning*.
**Follow-up:** How would you unit-test caching behavior in isolation? How does this enable swapping Redis vs in-memory cache?

---

## Q15 — Custom exception hierarchy [M · error handling · 11 min]
**Prompt:** Design exceptions for a data-validation library: a base plus `SchemaError` and `MissingValueError`. Why a common base? Show catching at different granularities and chaining context with `raise ... from`.

**Solution:**
```python
class DataError(Exception):
    """Base for all data-validation errors."""

class SchemaError(DataError):
    pass

class MissingValueError(DataError):
    def __init__(self, column):
        super().__init__(f"missing values in column {column!r}")
        self.column = column

# usage
try:
    validate(df)
except MissingValueError as e:        # specific
    fill_defaults(e.column)
except DataError:                     # catch-all for this library
    abort()

# chaining
try:
    int(raw)
except ValueError as e:
    raise SchemaError("expected integer id") from e
```
**Skills tested:** exception design, API ergonomics, error context preservation.
**Explanation:**
- A **common base** lets callers catch every library error with one `except DataError` while still allowing fine-grained handling of subclasses — and keeps your errors distinct from built-ins.
- Subclass exceptions can carry **structured data** (`e.column`) for programmatic handling, not just a message.
- `raise NewError(...) from original` sets `__cause__`, preserving the chain in the traceback ("The above exception was the direct cause…"); use `from None` to deliberately suppress a noisy cause.
**Strong vs. weak:** Strong candidate inherits from `Exception` (not `BaseException`), attaches structured attributes, and knows `from`/`from None`.
**Follow-up:** When inherit from a more specific builtin (e.g., `ValueError`) instead of `Exception`?

---

## Q16 — Descriptors (reusable validation) [A · data model · 15 min]
**Prompt:** Multiple fields across classes need "must be positive" validation. Write one reusable descriptor instead of repeating property boilerplate. Explain `__set_name__`, `__get__`, `__set__`, and how `@property` relates.

**Solution:**
```python
class Positive:
    def __set_name__(self, owner, name):
        self._name = f"_{name}"          # auto-captures the attribute name
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self                  # access via class -> the descriptor
        return getattr(obj, self._name)
    def __set__(self, obj, value):
        if value <= 0:
            raise ValueError(f"{self._name[1:]} must be positive, got {value}")
        setattr(obj, self._name, value)

class Account:
    balance = Positive()
    rate = Positive()
    def __init__(self, balance, rate):
        self.balance = balance           # triggers Positive.__set__
        self.rate = rate
```
**Skills tested:** the descriptor protocol — the machinery *behind* properties/methods — and building reusable abstractions. Strong senior signal.
**Explanation:**
- A **descriptor** is any object defining `__get__`/`__set__`/`__delete__`; placed as a **class attribute**, it intercepts instance attribute access.
- `__set_name__(owner, name)` (3.6+) is called at class creation with the attribute's name, so one descriptor instance knows where to store data (`_balance`, `_rate`) — no manual wiring.
- `@property` is itself a descriptor; descriptors generalize it to **reuse one validation across many attributes and classes** (DRY).
- `__get__` returning `self` when `obj is None` is the convention for class-level access.
**Strong vs. weak:** Strong candidate explains *data* vs *non-data* descriptors (defining `__set__` makes it a data descriptor that takes precedence over the instance `__dict__`) and connects to how methods are descriptors.
**Follow-up:** Why store in `obj.__dict__['_balance']` rather than on the descriptor instance? (Descriptor is shared by all instances → per-instance state must live on the instance.)

---

## Q17 — A scikit-learn-style transformer [M · DS-applied · 14 min]
**Prompt:** Implement a `StandardScaler`-like transformer with `fit`, `transform`, `fit_transform`. Store learned state, raise if `transform` runs before `fit`, and follow sklearn conventions.

**Solution:**
```python
class StandardScaler:
    def fit(self, X):
        n = len(X)
        self.mean_ = sum(X) / n
        var = sum((x - self.mean_) ** 2 for x in X) / n
        self.scale_ = var ** 0.5 or 1.0          # avoid divide-by-zero
        return self                               # enable chaining
    def transform(self, X):
        if not hasattr(self, "mean_"):
            raise RuntimeError("call fit() before transform()")
        return [(x - self.mean_) / self.scale_ for x in X]
    def fit_transform(self, X):
        return self.fit(X).transform(X)
```
**Skills tested:** applying OOP to the core DS workflow; state management; library conventions.
**Explanation:**
- **Convention:** learned attributes end with a trailing underscore (`mean_`, `scale_`) and are created in `fit`, signaling "fitted state." Constructor args (hyperparameters) would *not* have the underscore.
- `fit` **returns `self`** so you can chain `scaler.fit(X).transform(X)` and slot into pipelines.
- Calling `transform` before `fit` should fail explicitly (here `RuntimeError`; sklearn raises `NotFittedError`).
- `fit_transform` composes the two (and can be overridden for efficiency).
**Strong vs. weak:** Strong candidate knows the trailing-underscore convention and the fit/transform/predict separation, and why it matters for avoiding train/test leakage (fit on train only, transform both).
**Follow-up:** Why must you `fit` on train and only `transform` test? Where would `get_params`/`set_params` fit for grid search?

---

## Q18 — Singleton: `__new__`, threading, and why it's often wrong [A · creation/concurrency · 14 min]
**Prompt:** Implement a thread-safe singleton (e.g., a model registry / config). Use `__new__`. Then argue when a singleton is an anti-pattern and what you'd use instead.

**Solution:**
```python
import threading

class Registry:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:                 # fast path, no lock
            with cls._lock:
                if cls._instance is None:         # re-check under lock
                    cls._instance = super().__new__(cls)
        return cls._instance
```
**Skills tested:** `__new__` vs `__init__`, double-checked locking / race conditions, design maturity.
**Explanation:**
- `__new__` **creates** the instance (the actual constructor); `__init__` only **initializes** an already-created object. Singleton logic lives in `__new__`.
- **Double-checked locking**: the outer check avoids locking on the common path; the inner check (under the lock) prevents two threads both creating an instance in a race.
- Gotcha: `__init__` runs **on every call** even when `__new__` returns the cached instance — guard re-initialization or you'll clobber state.
- **Anti-pattern lens:** singletons are global mutable state → hard to test (can't isolate), hidden dependencies, awkward in concurrency. Alternatives: a **module-level instance** (Python modules are effectively singletons, imported once), or **dependency injection** (pass the registry in) for testability.
**Strong vs. weak:** Strong candidate volunteers the testability/DI critique *unprompted* and knows the `__init__`-runs-every-time gotcha.
**Follow-up:** Show the simplest correct singleton in Python. (A module-level object.)

---

## Q19 — Registry-based factory (Strategy) for model selection [M/A · patterns · 14 min]
**Prompt:** You must select among many model/strategy implementations by name at runtime (e.g., from a config). Build a registry-based factory using a decorator to register classes. Why is this better than a long `if/elif`?

**Solution:**
```python
class ModelFactory:
    _registry = {}

    @classmethod
    def register(cls, name):
        def deco(model_cls):
            cls._registry[name] = model_cls
            return model_cls
        return deco

    @classmethod
    def create(cls, name, **kwargs):
        try:
            return cls._registry[name](**kwargs)
        except KeyError:
            raise ValueError(f"unknown model {name!r}; have {list(cls._registry)}")

@ModelFactory.register("linear")
class LinearModel:
    def __init__(self, lr=0.01): self.lr = lr

model = ModelFactory.create("linear", lr=0.1)
```
**Skills tested:** Strategy/Factory patterns, decorators as registration, open/closed principle, extensibility.
**Explanation:**
- The **decorator** registers each class at import time, keyed by name. `create` looks up and instantiates.
- **Open/closed:** add a new model by writing a class + decorator — **no edits** to the factory or a central `if/elif`. New strategies can even live in plugins.
- Cleaner error handling and discoverability (can list registered names) than a sprawling conditional.
**Strong vs. weak:** Strong candidate connects this to real config-driven ML systems ("`model: xgboost` in YAML → object"), and notes pitfalls (registration requires the module to be imported; name collisions).
**Follow-up:** How do you ensure plugin modules are imported so they self-register? (entry points / explicit import.)

---

## Q20 — Callable objects: `__call__` vs closures [M · data model · 12 min]
**Prompt:** Implement a `MovingAverage(window)` whose **instances are callable** and maintain state across calls. Compare a class with `__call__` to a closure/generator. When prefer the class?

**Solution:**
```python
from collections import deque

class MovingAverage:
    def __init__(self, window):
        self.window = window
        self._buf = deque(maxlen=window)
    def __call__(self, x):
        self._buf.append(x)
        return sum(self._buf) / len(self._buf)
    def reset(self):
        self._buf.clear()

ma = MovingAverage(3)
ma(10); ma(20); ma(30)   # -> 20.0
```
Closure version:
```python
def moving_average(window):
    buf = deque(maxlen=window)
    def step(x):
        buf.append(x)
        return sum(buf) / len(buf)
    return step
```
**Skills tested:** `__call__`, stateful callables, choosing between OO and functional styles.
**Explanation:**
- `__call__` makes an instance behave like a function (`ma(x)`) while holding **inspectable, resettable** state — useful for stateful transforms, parameterized loss/metric objects, or anything you pass where a "function" is expected.
- A **closure** is lighter for simple cases but its state is hidden in the cell, harder to introspect/serialize/extend.
- Prefer the **class** when you need multiple methods (`reset`), introspection, pickling, or subclassing; prefer the **closure** for quick, single-purpose callables.
**Strong vs. weak:** Strong candidate notes both achieve "function with memory," and picks the class for testability/serialization (e.g., a stateful transform that must be checkpointed), the closure for brevity.
**Follow-up:** Why is `deque(maxlen=...)` better than a list here? How would you pickle the class vs the closure? (Closures aren't picklable by default.)

---

## Coverage map (for balancing a session)
| Theme | Questions |
|---|---|
| Attributes & state | Q1, Q4, Q7, Q8 |
| Methods & constructors | Q3, Q5, Q18, Q20 |
| Inheritance & MRO | Q5, Q6, Q14 |
| Data model / dunders | Q2, Q7, Q10, Q11, Q12, Q20 |
| Interfaces & typing | Q9, Q16 |
| Performance | Q13 |
| Design & patterns | Q14, Q18, Q19 |
| Error handling | Q15 |
| DS-applied | Q3, Q9, Q17, Q19 |

**Suggested balanced 1-hour sets:**
- *Mid-level:* Q1, Q3, Q9, Q17
- *Senior:* Q6, Q13, Q16, Q14 (or Q18)
- *Mixed:* Q2, Q7, Q12, Q19
