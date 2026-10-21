# Reflection

A readable copy of my answers from [`REFLECTION.essay`](../REFLECTION.essay). The original JSON file stays at the repository root as part of the graded submission. The wording below is unchanged; only the formatting differs.

---

## Q1. Explain the invariant that prevents double funding and how you tested it.

- **Invariant:** a loan's `pending` to `active` transition, the lender being recorded, and the money transfer all happen together in one critical section, so a loan can be funded at most once.
- **How it's enforced:**
  - `fund` holds the instance lock for the whole check-then-act sequence.
  - It checks the loan, the lender, `status == 'pending'`, lender ≠ borrower, and the balance, and only then moves money and sets `lender` and `status='active'`.
  - A second concurrent funder gets the lock later, sees `active`, and receives `409 invalid_state`.
- **Failed calls change nothing:** all validation runs before any mutation.
- **Conservation:** the principal moves only on that single transition, so the sum of balances is preserved.
- **Tests:**
  - **Concurrency test:** one pending loan, several funded lenders, and 20-50 threads released together with a `threading.Barrier` through a `ThreadPoolExecutor`. It asserts exactly one success, all the others `invalid_state`, the borrower credited once, and only the winning lender debited. I repeated it many times to shake out races.
  - **Conservation test:** the total of all balances is unchanged and no balance is negative.
  - **Sequential failure-path tests:** funding an active loan, funding your own loan, insufficient balance, and a missing lender or loan. Each checks that balances and the loan snapshot are identical before and after.

---

## Q2. How would you move balances and loans into a transactional database shared by several service instances?

- **Why the lock must go:** an `RLock` only protects one process, so the database becomes the single source of truth and the service instances become stateless.
- **Schema:**
  - `users(id, balance_cents CHECK (balance_cents >= 0))`.
  - `loans(id, borrower, lender NULL, principal, outstanding, status)`, with `CHECK` constraints on the amounts and status.
- **Transactions:** each public method runs in one transaction.
- **`fund`:**
  - `SELECT ... FOR UPDATE` on the loan row and both user rows.
  - Lock user rows in a fixed order (for example sorted by ID) to avoid deadlocks between opposite transfers.
  - Validate in the same order as today, then update both balances and the loan, then commit.
  - Alternative: an atomic `UPDATE loans SET status='active', lender=? WHERE id=? AND status='pending'`, where zero affected rows maps to `invalid_state`.
- **`repay`:** the same pattern, locking the loan plus both users.
- **Balance safety:** keep the explicit balance check so the API returns `insufficient_balance`, with the `CHECK` constraint as a last line of defence.
- **Isolation option:** serializable isolation with bounded retries on serialization failures.
- **Loan IDs:**
  - A sequence or identity column can leave gaps after rollbacks.
  - If IDs must stay gap-free, use a counter row updated inside the transaction, at the cost of serializing creations.
- **Snapshots:** build the returned dictionaries from the rows, so they stay detached.
- **Testing:** run the concurrent-funding test from several processes against a real database.

---

## Q3. How would repayment idempotency differ from forbidding overpayment?

- **Forbidding overpayment:**
  - A state-based validation: a payment above `outstanding` is rejected with `invalid_state`.
  - It keeps the owed balance from going negative.
  - It looks only at current loan state, not at whether this request was already processed.
- **Idempotency:**
  - It addresses client retries of the same request, such as a timeout followed by a resend.
  - A retried "repay 20" must not pay 20 twice.
- **Why the overpayment rule isn't enough:**
  - A retried 20 against 40 outstanding looks like a valid new payment and would succeed twice.
  - A retry after the loan is fully repaid returns an error that looks like a fresh rejection, even though the first call succeeded.
- **How to get idempotency:**
  - The client sends a unique idempotency key with each repayment.
  - The service stores the key, a fingerprint (loan, borrower, amount), and the result in the same transaction as the balance change.
  - The same key with the same fingerprint returns the stored result without moving money.
  - The same key with a different payload is rejected as a conflict.
- **How they fit together:** idempotency makes retries safe, and the overpayment check protects the invariant when different requests race.
- **API impact:** the key is a new parameter, so it would be an optional extension to keep the public signature unchanged.
