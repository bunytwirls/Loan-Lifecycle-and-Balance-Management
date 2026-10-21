# Loan Lifecycle & Balance Management

A thread-safe, in-memory loan service (**LedgerBridge**) that tracks user balances and moves loans through `pending → active → repaid`. Built as a **debugging challenge**: the starter service had bugs where loans disappeared after creation, funded balances moved incorrectly, and repayments failed unexpectedly. The job was to repair it without changing its public API.

![Python](https://img.shields.io/badge/python-3.11-blue)
![Dependencies](https://img.shields.io/badge/dependencies-stdlib%20only-brightgreen)
![Hidden tests](https://img.shields.io/badge/hidden%20tests-17%2F17-brightgreen)

---

## Table of Contents

- [About the Challenge](#about-the-challenge)
- [Results](#results)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Public API](#public-api)
- [Loan Lifecycle](#loan-lifecycle)
- [Design Decisions](#design-decisions)
- [Invariants](#invariants)
- [Testing](#testing)
- [Reflection Highlights](#reflection-highlights)
- [Known Limitations & Future Work](#known-limitations--future-work)
- [Acknowledgements](#acknowledgements)

---

## About the Challenge

This project comes from **LeetCode Projects**, a beta feature where you work on a small, realistic codebase in a browser IDE instead of solving a single algorithm problem.

| | |
|---|---|
| **Platform** | LeetCode Projects (beta) |
| **Mode** | Debugging: repair an existing service |
| **Time limit** | 60 minutes (investigation, implementation, regression tests and reflection) |
| **My time** | **47 / 60 minutes** |
| **Grading** | AI-graded: hidden test suite + rubric covering code, tests and working process |
| **Tooling** | In-app AI agent available inside the workspace; how you direct it is part of the grade |
| **Language** | Python 3.11, standard library only |

**Rules of the task:**

- Edit only `service.py` and `REFLECTION.essay`.
- Keep public names, signatures and the supplied fixed files (such as `models.py`) unchanged.
- Helper modules and your own regression tests are allowed.

The original task brief is preserved word for word in [`docs/TASK.md`](docs/TASK.md).

---

## Results

| Category | Result |
|---|---|
| Completion (hidden tests) | **17 / 17 (100%)** |
| Change Quality | Excellent |
| Testing Discipline | Excellent |
| AI Direction | Good |
| Repository Orientation | Needs Improvement |
| Debugging Loop | Needs Improvement |
| Release Confidence | Needs Improvement |
| Change Control | Not evaluated |

**My takeaways.** The code and tests scored well, but the process categories did not. Those categories reward *how* the work is done, not just the final diff. Next time I would:

- **Orient first:** read every file and run the existing test suite before touching code.
- **Reproduce before fixing:** write a failing test for each reported symptom, then fix it and watch it turn green.
- **Verify before shipping:** rerun the full suite (and confirm the process starts) as a final, explicit step.

---

## Project Structure

| File | Role |
|---|---|
| [`docs/DEBUGGING_LOG.md`](docs/DEBUGGING_LOG.md) | Each reported bug: symptom, fix, and the test that guards it |
| [`docs/REFLECTION.md`](docs/REFLECTION.md) | Readable Markdown copy of `REFLECTION.essay` |
| [`docs/TASK.md`](docs/TASK.md) | Original LeetCode task brief |
| [`docs/TESTING.md`](docs/TESTING.md) | Testing notes |
| [`.gitignore`](.gitignore) | Excludes caches, virtual environments, and editor/OS files |
| [`models.py`](models.py) | `ServiceError(status, code)`: supplied file, unchanged |
| [`README.md`](README.md) | This overview |
| [`REFLECTION.essay`](REFLECTION.essay) | JSON file with my answers to the three reflection questions (as submitted) |
| [`requirements.txt`](requirements.txt) | Optional test tooling (pytest); not needed to run the tests |
| [`service.py`](service.py) | `LoanService`: the repaired implementation (my main change) |
| [`test_client.py`](test_client.py) | Visible tests supplied with the challenge |
| [`test_regression.py`](test_regression.py) | 10 regression tests I wrote, using only the public API |

---

## Quick Start

Requires **Python 3.11+**. No installation needed.

```bash
git clone https://github.com/bunytwirls/Loan-Lifecycle-and-Balance-Management.git
cd Loan-Lifecycle-and-Balance-Management

# Visible tests supplied with the challenge
python3 -B test_client.py

# My regression tests (standard library only)
python3 -B -m unittest test_regression -v

# Or, with pytest (optional)
pip install -r requirements.txt
pytest -v
```

### Example

```python
from service import LoanService

service = LoanService({"borrower": 0, "lender": 100})
loan = service.create("borrower", 60)
service.fund(loan["id"], "lender")
# {"id": 1, "borrower": "borrower", "lender": "lender",
#  "principal": 60, "outstanding": 60, "status": "active"}

service.repay(loan["id"], "borrower", 20)["outstanding"]   # 40
(service.balance("borrower"), service.balance("lender"))   # (40, 60)
```

---

## Public API

```text
LoanService(balances: dict[str, int])
create(borrower: str, amount: int) -> dict
get(loan_id: int) -> dict
fund(loan_id: int, lender: str) -> dict
repay(loan_id: int, borrower: str, amount: int) -> dict
balance(user: str) -> int
```

- All amounts are **integer cents**.
- Every returned loan is a detached dictionary of the form:

```python
{"id": int, "borrower": str, "lender": str | None,
 "principal": int, "outstanding": int, "status": "pending" | "active" | "repaid"}
```

### Errors

Failures raise `models.ServiceError` with an integer `status` (HTTP-style) and a stable string `code`.

| Method | Status | Code | Raised when |
|---|---|---|---|
| `create` | 400 | `invalid_amount` | Amount is a bool, not an int, or `<= 0` |
| `create` | 404 | `user_not_found` | Borrower does not exist |
| `get` | 404 | `loan_not_found` | No loan with that ID |
| `balance` | 404 | `user_not_found` | User does not exist |
| `fund` | 404 | `loan_not_found` | No loan with that ID |
| `fund` | 404 | `user_not_found` | Lender does not exist |
| `fund` | 409 | `invalid_state` | Loan is not `pending`, or lender is the borrower |
| `fund` | 409 | `insufficient_balance` | Lender balance < principal (an exact balance is enough) |
| `repay` | 400 | `invalid_amount` | Amount is a bool, not an int, or `<= 0` |
| `repay` | 404 | `loan_not_found` | No loan with that ID |
| `repay` | 403 | `forbidden` | Caller is not the loan's borrower |
| `repay` | 409 | `invalid_state` | Loan is not `active`, or amount > outstanding |
| `repay` | 409 | `insufficient_balance` | Borrower balance < amount |

---

## Loan Lifecycle

```text
            create()                 fund()                 repay() until outstanding == 0
  (none) ───────────▶  pending  ───────────────▶  active  ─────────────────────────────▶  repaid
                       no money moves      principal: lender → borrower    payment: borrower → lender
                                                    │    ▲
                                                    └────┘
                                           partial repay() stays active
```

- No transition goes backwards.
- `repaid` is terminal.
- A loan can be funded **exactly once**.

### Validation order

The order matters because, when several rules are broken at once, the first failing check decides which error is returned.

```text
create:  amount  →  borrower exists
fund:    loan exists  →  lender exists  →  status == pending AND lender ≠ borrower  →  lender balance
repay:   amount  →  loan exists  →  caller is borrower  →  status == active AND amount ≤ outstanding  →  borrower balance
```

---

## Design Decisions

| Decision | Why |
|---|---|
| **One `RLock` per instance, held for the whole method** | Each operation is a check-then-act sequence. Holding the lock across both halves makes it atomic, so two concurrent `fund` calls cannot both see `pending`. `RLock` (re-entrant) lets methods reuse `get`/`balance` internally while already holding the lock. |
| **Validate everything before mutating anything** | All checks run first and all writes happen last. A failed call therefore leaves balances, loans and the ID counter untouched, with no rollback logic needed. |
| **`type(amount) is int`** | `isinstance(True, int)` is `True` in Python, so an exact type check is what rejects booleans (and floats, strings, `None`). |
| **IDs allocated only after a successful create** | `_next_id` is incremented only after the loan is stored, so failed creates never leave gaps. |
| **Defensive copies in and out** | The constructor copies the input `balances`, and every returned loan is a copy. Callers cannot change internal state by mutating what they passed in or got back. |
| **No shared state between instances** | All state lives on `self`, so separate `LoanService` objects are fully independent. |

---

## Invariants

These properties hold after every call, successful or not:

1. **Conservation:** the sum of all balances never changes; money only moves between users.
2. **Non-negativity:** no balance ever goes below zero.
3. **Single funding:** a loan moves `pending → active` at most once, even under concurrent `fund` calls.
4. **Bounded debt:** `0 <= outstanding <= principal`, and `outstanding == 0` exactly when `status == "repaid"`.
5. **Atomic failure:** any raised `ServiceError` leaves all loans, balances and the ID counter unchanged.
6. **Gap-free IDs:** loan IDs are `1, 2, 3, ...` with no gaps from failed creates.

---

## Testing

`test_regression.py` has 10 tests that use only the public API:

| Test | What it verifies |
|---|---|
| `test_concurrent_double_funding` | 32 lenders released at once by a `threading.Barrier`, repeated 30 rounds. Exactly one wins, the rest get `invalid_state`, and money is conserved. |
| `test_concurrent_repay_conserves` | 150 concurrent repayments of 10 against a 1000 loan. Exactly 100 succeed, the loan ends `repaid`, and balances are correct. |
| `test_fund_failures_preserve_state` | Every `fund` failure path leaves balances and loans identical. Re-funding is rejected. |
| `test_exact_balance_funds` | A lender with exactly the principal can fund. |
| `test_repay_rules_and_order` | Repaying a pending loan, invalid amount, missing loan, wrong borrower, overpayment, partial repayment, then full repayment. |
| `test_fund_after_full_repayment_is_rejected` | A `repaid` loan cannot be funded again, and state is unchanged. |
| `test_repay_insufficient_balance_preserves_state` | A borrower who can't cover a repayment gets `insufficient_balance` with no side effects. |
| `test_failed_create_does_not_consume_ids` | `0, -1, True, False, 1.5, "5", None` are rejected. Amount is checked before the user. The first successful ID is still `1`. |
| `test_snapshots_and_instance_isolation` | Mutating input or returned dicts never affects the service. Instances don't share state. |
| `test_exact_create_shape` | `create` returns exactly the specified dictionary. |

**Concurrency testing approach.** A race only shows up if threads really hit the critical section at the same moment. The tests line every worker up on a `Barrier`, release them together, and repeat the scenario many times to make a missing lock very likely to fail.

---

## Reflection Highlights

Full answers are in [`docs/REFLECTION.md`](docs/REFLECTION.md) (readable copy). The original submitted file is [`REFLECTION.essay`](REFLECTION.essay).

- **Q1: Preventing double funding.**
  - The status check, the money transfer, and the `lender`/`status` update all happen in one critical section.
  - A second funder acquires the lock later, sees `active`, and receives `invalid_state`.
- **Q2: Moving to a shared transactional database.**
  - An in-process lock can't coordinate several service instances, so the database becomes the source of truth.
  - Each method runs in one transaction using `SELECT ... FOR UPDATE`, with user rows locked in a fixed order to avoid deadlocks.
  - Alternatively, a conditional `UPDATE ... WHERE status = 'pending'` makes funding atomic.
  - `CHECK` constraints act as a last line of defence.
  - Gap-free IDs require a counter row updated inside the transaction.
- **Q3: Idempotency vs. forbidding overpayment.**
  - The overpayment rule validates the current state of the loan.
  - Idempotency protects against *retries* of the same request.
  - A retried "repay 20" against 40 outstanding passes the overpayment check twice. Only an idempotency key, stored with its result in the same transaction, prevents the double charge.

---

## Known Limitations & Future Work

The submission was kept exactly as graded. These are improvements I'd make outside the challenge constraints:

- **Boolean loan IDs:** `get(True)` returns loan `1`, because `True == 1` and hashes the same in Python. A `type(loan_id) is int` check would close this.
- **Constructor validation:** the input balances are copied but not validated (non-empty string keys, non-negative int values).
- **Cheaper snapshots:** loans are flat dicts of immutable values, so `dict(loan)` is enough and is faster than `deepcopy`.
- **Redundant write-back:** `self._loans[loan_id] = loan` after an in-place update has no effect and can be removed.
- **Coarse locking:** one lock serializes every call. Per-loan or per-user locks (acquired in a fixed order) would allow more parallelism if throughput mattered.
- **Extensions discussed in the reflection:** a persistent transactional store, and idempotency keys for `repay`.

---

## Acknowledgements

- The challenge, scenario and `models.py` are from **LeetCode Projects (beta)**.
- The original brief is reproduced in [`docs/TASK.md`](docs/TASK.md) for context.
- The implementation in `service.py`, the tests in `test_regression.py` and the reflection answers are my own work.
