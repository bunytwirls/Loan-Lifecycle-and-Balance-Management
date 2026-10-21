"""Regression tests for LoanService. Uses only the public API."""
import unittest
from threading import Barrier
from concurrent.futures import ThreadPoolExecutor
from service import LoanService
from models import ServiceError


def snapshot(service, users, loan_ids):
    return ({u: service.balance(u) for u in users},
            {i: service.get(i) for i in loan_ids})


class Regression(unittest.TestCase):
    def err(self, status, code, fn, *args):
        with self.assertRaises(ServiceError) as ctx:
            fn(*args)
        self.assertEqual((ctx.exception.status, ctx.exception.code), (status, code))

    def test_concurrent_double_funding(self):
        for _ in range(30):
            lenders = {f"l{i}": 100 for i in range(32)}
            s = LoanService({"b": 0, **lenders})
            loan = s.create("b", 60)
            barrier = Barrier(len(lenders))

            def go(lender):
                barrier.wait()
                try:
                    s.fund(loan["id"], lender)
                    return ("ok", lender)
                except ServiceError as e:
                    return (e.code, lender)

            with ThreadPoolExecutor(len(lenders)) as ex:
                results = list(ex.map(go, lenders))
            winners = [l for r, l in results if r == "ok"]
            self.assertEqual(len(winners), 1)
            self.assertTrue(all(r in ("ok", "invalid_state") for r, _ in results))
            self.assertEqual(s.balance("b"), 60)
            self.assertEqual(s.balance(winners[0]), 40)
            self.assertEqual(sum(s.balance(u) for u in ["b", *lenders]), 3200)
            self.assertEqual(s.get(loan["id"])["lender"], winners[0])

    def test_concurrent_repay_conserves(self):
        s = LoanService({"b": 0, "l": 1000})
        loan = s.create("b", 1000)
        s.fund(loan["id"], "l")

        def pay(_):
            try:
                s.repay(loan["id"], "b", 10)
                return 1
            except ServiceError:
                return 0

        with ThreadPoolExecutor(64) as ex:
            ok = sum(ex.map(pay, range(150)))
        self.assertEqual(ok, 100)
        self.assertEqual(s.get(loan["id"])["status"], "repaid")
        self.assertEqual((s.balance("b"), s.balance("l")), (0, 1000))

    def test_fund_failures_preserve_state(self):
        s = LoanService({"b": 0, "l": 50, "x": 100})
        loan = s.create("b", 60)
        users, ids = ["b", "l", "x"], [loan["id"]]
        before = snapshot(s, users, ids)
        self.err(409, "insufficient_balance", s.fund, loan["id"], "l")
        self.err(409, "invalid_state", s.fund, loan["id"], "b")
        self.err(404, "user_not_found", s.fund, loan["id"], "nobody")
        self.err(404, "loan_not_found", s.fund, 99, "x")
        self.assertEqual(snapshot(s, users, ids), before)
        s.fund(loan["id"], "x")
        self.err(409, "invalid_state", s.fund, loan["id"], "x")

    def test_exact_balance_funds(self):
        s = LoanService({"b": 0, "l": 60})
        s.fund(s.create("b", 60)["id"], "l")
        self.assertEqual((s.balance("b"), s.balance("l")), (60, 0))

    def test_repay_rules_and_order(self):
        s = LoanService({"b": 0, "l": 100, "o": 5})
        loan = s.create("b", 60)
        self.err(409, "invalid_state", s.repay, loan["id"], "b", 10)  # pending
        s.fund(loan["id"], "l")
        self.err(400, "invalid_amount", s.repay, 99, "b", 0)
        self.err(404, "loan_not_found", s.repay, 99, "b", 10)
        self.err(403, "forbidden", s.repay, loan["id"], "o", 10)
        self.err(409, "invalid_state", s.repay, loan["id"], "b", 61)
        self.assertEqual(s.repay(loan["id"], "b", 20)["status"], "active")
        self.assertEqual(s.get(loan["id"])["outstanding"], 40)
        self.assertEqual((s.balance("b"), s.balance("l")), (40, 60))
        done = s.repay(loan["id"], "b", 40)
        self.assertEqual((done["status"], done["outstanding"]), ("repaid", 0))
        self.err(409, "invalid_state", s.repay, loan["id"], "b", 1)

    def test_fund_after_full_repayment_is_rejected(self):
        s = LoanService({"b": 0, "l": 100, "m": 100})
        loan = s.create("b", 40)
        s.fund(loan["id"], "l")
        s.repay(loan["id"], "b", 40)
        before = snapshot(s, ["b", "l", "m"], [loan["id"]])
        self.err(409, "invalid_state", s.fund, loan["id"], "m")
        self.assertEqual(snapshot(s, ["b", "l", "m"], [loan["id"]]), before)

    def test_repay_insufficient_balance_preserves_state(self):
        # Built with public calls only: b receives 60, then spends 55 by
        # funding a loan for c, leaving b with 5 against a 60 debt.
        s = LoanService({"b": 0, "l": 100, "c": 0})
        debt = s.create("b", 60)
        s.fund(debt["id"], "l")
        other = s.create("c", 55)
        s.fund(other["id"], "b")
        self.assertEqual(s.balance("b"), 5)
        users, ids = ["b", "l", "c"], [debt["id"], other["id"]]
        before = snapshot(s, users, ids)
        self.err(409, "insufficient_balance", s.repay, debt["id"], "b", 10)
        self.assertEqual(snapshot(s, users, ids), before)

    def test_failed_create_does_not_consume_ids(self):
        s = LoanService({"b": 10})
        for bad in (0, -1, True, False, 1.5, "5", None):
            self.err(400, "invalid_amount", s.create, "b", bad)
        self.err(404, "user_not_found", s.create, "zz", 5)
        self.err(400, "invalid_amount", s.create, "zz", 0)  # amount checked first
        self.assertEqual(s.create("b", 5)["id"], 1)
        self.err(404, "user_not_found", s.balance, "zz")

    def test_snapshots_and_instance_isolation(self):
        init = {"b": 0, "l": 100}
        s = LoanService(init)
        init["l"] = 0
        self.assertEqual(s.balance("l"), 100)
        created = s.create("b", 10)
        created["status"] = "hacked"
        self.assertEqual(s.get(1)["status"], "pending")
        fetched = s.get(1)
        fetched["outstanding"] = 0
        self.assertEqual(s.get(1)["outstanding"], 10)
        funded = s.fund(1, "l")
        funded["lender"] = "x"
        self.assertEqual(s.get(1)["lender"], "l")
        repaid = s.repay(1, "b", 4)
        repaid["outstanding"] = 0
        self.assertEqual(s.get(1)["outstanding"], 6)
        self.err(404, "loan_not_found", LoanService({"b": 0}).get, 1)

    def test_exact_create_shape(self):
        s = LoanService({"b": 0})
        self.assertEqual(s.create("b", 7), {
            "id": 1, "borrower": "b", "lender": None,
            "principal": 7, "outstanding": 7, "status": "pending"})


if __name__ == "__main__":
    unittest.main()
