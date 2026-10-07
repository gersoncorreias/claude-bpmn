"""The rules reference that Claude reads must describe exactly the rules the script runs."""
import os
import re
import unittest

from _env import SKILLS

import validate

RULES_DOC = os.path.join(SKILLS, "bpmn-coach", "references", "bpmn-validation-rules.md")
ROW = re.compile(r"^\| ([A-Z]{2,3}-\d{3}) \| (ERROR|WARNING|INFO) \|", re.M)
RETIRED = {"SF-005", "NM-003"}


class RulesDocTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(RULES_DOC, encoding="utf-8") as fh:
            cls.doc = fh.read()
        cls.documented = dict(ROW.findall(cls.doc))

    def test_same_rules_same_severities(self):
        code = {rid: sev for rid, (sev, _) in list(validate.RULES.items()) + list(validate.JUDGEMENT_RULES.items())}
        self.assertEqual(self.documented, code)

    def test_judgement_rules_are_marked(self):
        for rid in validate.JUDGEMENT_RULES:
            row = next(line for line in self.doc.splitlines() if line.startswith("| %s |" % rid))
            self.assertIn("Judgement", row)

    def test_retired_ids_are_not_reused(self):
        self.assertFalse(RETIRED & set(validate.RULES))
        for rid in RETIRED:
            self.assertIn("| %s |" % rid, self.doc)

    def test_skill_names_the_judgement_rules(self):
        with open(os.path.join(SKILLS, "bpmn-coach", "SKILL.md"), encoding="utf-8") as fh:
            skill = fh.read()
        for rid in validate.JUDGEMENT_RULES:
            self.assertIn(rid, skill)


if __name__ == "__main__":
    unittest.main()
