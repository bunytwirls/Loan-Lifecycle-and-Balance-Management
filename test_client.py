import unittest
from concurrent.futures import ThreadPoolExecutor
from tempfile import TemporaryDirectory
from pathlib import Path
from service import LoanService
from models import ServiceError

class Cases(unittest.TestCase):
    """Visible behavior checks for loan-management."""
    def error(self,expected_status,code,fn,*args,**kwargs):
        with self.assertRaises(ServiceError) as ctx:
            fn(*args,**kwargs)
        self.assertEqual((ctx.exception.status,ctx.exception.code),(expected_status,code))

    def test_create_and_read(self):
        """Retrieves a newly created loan using its returned ID."""
        service=LoanService({'borrower':0,'lender':10000})
        loan=service.create('borrower',5000)
        self.assertEqual(service.get(loan['id']),loan)

    def test_fund_and_repay(self):
        """Transfers funds to the borrower and completes a full repayment."""
        s=LoanService({'b':0,'l':100});loan=s.create('b',60)
        s.fund(loan['id'],'l');self.assertEqual(s.balance('b'),60)
        self.assertEqual(s.repay(loan['id'],'b',60)['status'],'repaid')

    def test_invalid_amount(self):
        """Rejects creation of a loan with a zero amount."""
        self.error(400,'invalid_amount',LoanService({'b':0}).create,'b',0)

if __name__ == '__main__':
    unittest.main()
