# Debugging Log

This log records the bugs reported in the challenge, how each one was fixed in [`service.py`](../service.py), and which regression test now guards against it.

> **Note:** The symptoms and the repair checklist come from the original brief ([`TASK.md`](TASK.md)). The **Fix** and **Guarded by** entries describe the final code and tests in this repo. Lines marked _TODO_ are for the exact starter-code snippet, which isn't in this repository.

---

## Reported symptoms

From the challenge scenario:

1. Loans disappear after creation.
2. Funded balances move incorrectly.
3. Repayments fail unexpectedly.

The brief also lists five required repairs. Each one has its own entry below.

---

## Workflow used for each bug

```text
1. Reproduce  → write a test, using only the public API, that shows the symptom
2. Locate     → trace the failing call through service.py to the faulty line
3. Fix        → make the smallest change that satisfies the spec
4. Verify     → the new test passes, and the full suite (test_client.py + test_regression.py) is still green
```

---

## 1. Loans disappear after creation

| | |
|---|---|
| **Symptom** | `create()` returns a loan, but a later `get(id)` raises `loan_not_found`. |
| **Spec** | Validate the amount, check the borrower exists, store the loan under its returned ID, and allocate IDs only on success. |
| **Starter code** | _TODO: paste the original lines_ |
| **Fix** | `create` validates `type(amount) is int and amount > 0`, then checks the borrower exists. It then stores the loan in `self._loans[loan['id']]` and only then increments `_next_id`. |
| **Guarded by** | `test_exact_create_shape`, `test_failed_create_does_not_consume_ids` |

---

## 2. Funded balances move incorrectly

| | |
|---|---|
| **Symptom** | After `fund()`, the lender and borrower balances don't reflect a transfer of the principal. |
| **Spec** | On success, move the full principal from lender to borrower. An exact balance is sufficient. |
| **Starter code** | _TODO: paste the original lines_ |
| **Fix** | `self._balances[lender] -= principal` and `self._balances[borrower] += principal`. The balance check uses `available < principal`, so an exact balance passes. The loan records `lender` and becomes `active`. |
| **Guarded by** | `test_exact_balance_funds`, `test_concurrent_double_funding` (conservation assertion) |

---

## 3. Repayments fail unexpectedly or leave partial state

| | |
|---|---|
| **Symptom** | Valid repayments raise errors, and failed ones can change balances or loans. |
| **Spec** | Check amount → loan exists → caller is borrower → active and not overpaying → balance, **in that order**. Every failure leaves all state unchanged. |
| **Starter code** | _TODO: paste the original lines_ |
| **Fix** | All checks run before any mutation. On success, the payment moves borrower → lender, `outstanding` decreases, and `status` becomes `repaid` at zero. |
| **Guarded by** | `test_repay_rules_and_order`, `test_repay_insufficient_balance_preserves_state`, `test_concurrent_repay_conserves` |

---

## 4. Returned data leaks internal state

| | |
|---|---|
| **Symptom** | Mutating a returned loan dict, or the dict passed to the constructor, changes the service's state. |
| **Spec** | Copy the input balances. Every returned dictionary is a detached snapshot. |
| **Starter code** | _TODO: paste the original lines_ |
| **Fix** | The constructor stores `dict(balances)`, and every method returns `deepcopy(loan)`. |
| **Guarded by** | `test_snapshots_and_instance_isolation` |

---

## 5. A loan can be funded more than once under concurrency

| | |
|---|---|
| **Symptom** | Simultaneous `fund()` calls can each see `pending`, so the borrower is paid several times. |
| **Spec** | A loan funds exactly once. Later or concurrent attempts raise `invalid_state`, and total balances are conserved. |
| **Starter code** | _TODO: paste the original lines_ |
| **Fix** | Each public method holds the instance `RLock` for its entire check-then-act sequence. A re-entrant lock is used because `fund`/`repay` call `get`/`balance` internally. |
| **Guarded by** | `test_concurrent_double_funding` (32 threads × 30 rounds behind a `Barrier`), `test_fund_failures_preserve_state`, `test_fund_after_full_repayment_is_rejected` |

---

## Final verification

```bash
python3 -B test_client.py                   # visible tests supplied with the challenge
python3 -B -m unittest test_regression -v   # my 10 regression tests
```

- Visible and regression tests: all passing.
- Hidden grader: **17 / 17**.

---

## Lessons

The grader rated **Debugging Loop** and **Repository Orientation** as *Needs Improvement*, even though every test passed. What I'd do differently:

- Run the supplied tests **before** editing, and record which ones fail and why.
- Commit a failing reproduction test for each symptom **before** the fix, so the history shows red → green.
- Keep notes like this log *while* debugging, not afterwards.
