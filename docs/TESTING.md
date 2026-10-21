# Testing

Run everything with one command:

    bash run_all_tests.sh

This runs `test_client.py` (supplied, 3 tests) and `test_regression.py`
(added, 10 tests, public API only). The default runner `.theia/run_tests.sh`
only runs the supplied tests, so use this script before submitting.

The regression suite covers concurrent funding (barrier, 32 threads, repeated),
concurrent repayment, state preservation after every rejection path, error
ordering, exact-balance funding, funding after full repayment, amount
validation, snapshot isolation and instance independence.
