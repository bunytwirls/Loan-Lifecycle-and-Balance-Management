
# LedgerBridge: loan lifecycle and balances

## What you should know

Mode: Debugging.

Use Python 3.11 with the standard library. The visible tests need no pip installation.

---

## Scenario

Borrowers report loans disappearing after creation, funded balances moving incorrectly, and repayments failing unexpectedly. Repair the in-memory loan service while preserving its public API.

---

## Files

Edit `service.py` and `REFLECTION.essay`. Keep the public names, signatures and supplied fixed files unchanged. You may add helper modules and your own regression tests.

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

Import the class from `service.py`. `models.ServiceError` exposes integer `status` and string `code`; `(status, code)` below refers to that exception, not a returned tuple, unless a success tuple is explicitly shown.

---

## Requirements

### 1. Balances and amounts

- The constructor receives balances for known users, keyed by nonempty string user IDs, with amounts in nonnegative integer cents.
- Copy these balances so later changes to the input cannot affect the service.
- All amounts use integer cents; booleans, non-integers, and amounts <= 0 raise `ServiceError(400, "invalid_amount")`.
- No interest, fees, deposits, deletion, or disk persistence is required.

### 2. Loan creation and retrieval

- `create` validates amount, then checks the borrower exists.
- Missing users raise `(404, "user_not_found")`.
- Allocate IDs 1, 2, ... `only` for successful creations.
- Return exactly `{id, borrower, lender: None, principal: amount, outstanding: amount, status: "pending"}`.
- Creation does not move money.
- `get` returns the saved loan; a missing ID raises `(404, "loan_not_found")`.
- `balance` rejects missing users with `user_not_found`.

### 3. Funding

- `fund` first checks that the loan and lender exist, then checks the loan state and whether the lender is also the borrower, and finally checks the balance.
- Only pending loans can be funded, and lender must differ from borrower; otherwise raise `(409, "invalid_state")`.
- Lender balance below principal raises `(409, "insufficient_balance")`.
- An exact balance is sufficient.
- Success transfers the full principal from lender to borrower, records the lender and sets `status="active"`; outstanding stays equal to principal.

### 4. Repayment

- `repay` checks the amount, loan existence, borrower ownership, active state and overpayment, then the balance, in that order.
- A request from the wrong borrower raises `(403, "forbidden")`.
- Non-active loans or payments above outstanding raise `(409, "invalid_state")`.
- Insufficient borrower balance raises `(409, "insufficient_balance")`.
- Success transfers the payment from borrower to lender and subtracts it from outstanding.
- Zero outstanding sets `status="repaid"`.
- Partial repayments remain active.
- Every failed operation preserves all loans, balances and ID allocation.

### 5. Concurrency and balance conservation

- All methods are safe for simultaneous calls on one instance.
- A loan can fund exactly once, including concurrent attempts; later attempts raise `invalid_state`.
- Transfers conserve the sum of all balances and cannot make a balance negative.
- Every returned dictionary is a detached snapshot.
- Instances are independent.
- Persistence means retained state across calls on the same instance; process restart is out of scope.

---

## Implementation checklist

Each task is required.

1. Validate amounts and save each newly created loan under its returned ID.
2. Transfer the principal from lender to borrower when funding succeeds.
3. Apply repayments and leave balances and loans unchanged when a request fails.
4. Return snapshots that callers can modify without changing service state.
5. Enforce loan state transitions, including when funding requests arrive concurrently.

---

## Estimated completion time

60 minutes, including investigation, implementation, regression testing and the reflection answers.

---

## Running locally

```bash
bash .theia/run_tests.sh
# Equivalent:
python3 -B test_client.py
```

Some tests will fail against the starter code. After making changes, check the test results as well as whether the process starts. The visible tests cover part of the contract; your implementation must satisfy all the rules above. Tests have time limits and use temporary state.

After completing the code, fill in each question’s `answer` field in `REFLECTION.essay`. The questions ask you to explain your approach and discuss possible future changes. You do not need to implement the proposed extensions.

---

## Example

The values below describe a correct implementation.

```python
service = LoanService({"borrower": 0, "lender": 100})
loan = service.create("borrower", 60)
service.fund(loan["id"], "lender")
# {"id": 1, "borrower": "borrower", "lender": "lender",
#  "principal": 60, "outstanding": 60, "status": "active"}
service.repay(loan["id"], "borrower", 20)["outstanding"]  # 40
(service.balance("borrower"), service.balance("lender"))  # (40, 60)
```
