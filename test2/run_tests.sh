# run_tests.sh
pytest tests/unit
pytest tests/concurrency
pytest tests/performance
locust -f tests/load/locustfile.py
