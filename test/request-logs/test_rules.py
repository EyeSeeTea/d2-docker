"""Validation of request logs rules (d2_docker.request_logs). Run: test/request-logs/run.sh"""

import json
import os
import unittest

from d2_docker import request_logs, utils

CASES_PATH = os.path.join(os.path.dirname(__file__), "rules-cases.json")


def load_cases():
    with open(CASES_PATH) as cases_file:
        return json.load(cases_file)


def check_rules(case):
    text = case["configText"] if "configText" in case else json.dumps(case["config"])
    request_logs.check_rules(text)


class TestRequestLogsRules(unittest.TestCase):
    def test_valid(self):
        for case in load_cases()["matching"]:
            with self.subTest(case["comment"]):
                check_rules(case)

    def test_invalid(self):
        cases = [case for case in load_cases()["invalid"] if not case.get("gatewayOnly")]
        for case in cases:
            with self.subTest(case["comment"]):
                with self.assertRaises(utils.D2DockerError) as context:
                    check_rules(case)
                if "error" in case:
                    self.assertIn(case["error"], str(context.exception))


if __name__ == "__main__":
    unittest.main()
