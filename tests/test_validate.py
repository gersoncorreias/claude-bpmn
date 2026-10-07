import glob
import io
import json
import os
import subprocess
import sys
import unittest

from _env import FIXTURES, ROOT, SKILLS, VALIDATOR

import validate


def pairs(report):
    return sorted([[f["rule"], f["element_id"]] for f in report["findings"]], key=lambda p: (p[0], p[1] or ""))


def run_cli(*args, stdin=None):
    return subprocess.run([sys.executable, VALIDATOR] + list(args), input=stdin, capture_output=True)


class FixtureTests(unittest.TestCase):
    """Each broken fixture produces exactly the findings listed in tests/fixtures/expected.json."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(FIXTURES, "expected.json"), encoding="utf-8") as fh:
            cls.expected = json.load(fh)

    def test_every_fixture_has_an_expectation(self):
        on_disk = sorted(os.path.basename(p) for p in glob.glob(os.path.join(FIXTURES, "*.bpmn")))
        self.assertEqual(on_disk, sorted(self.expected))

    def test_findings_match(self):
        for name, want in self.expected.items():
            with self.subTest(fixture=name):
                report = validate.validate(os.path.join(FIXTURES, name))
                if want.get("parse_error"):
                    self.assertFalse(report["ok"])
                    self.assertTrue(report["error"])
                else:
                    self.assertTrue(report["ok"], report.get("error"))
                    self.assertEqual(pairs(report), want["findings"])

    def test_exit_codes(self):
        for name, want in self.expected.items():
            with self.subTest(fixture=name):
                self.assertEqual(run_cli(os.path.join(FIXTURES, name)).returncode, want["exit"])

    def test_every_rule_is_exercised(self):
        fired = {rule for want in self.expected.values() for rule, _ in want.get("findings", [])}
        self.assertEqual(set(validate.RULES) - fired, set(), "add a fixture for these rules")


class CleanDiagramTests(unittest.TestCase):
    """Shipped diagrams must be clean, so the examples teach good habits."""

    def test_templates_have_no_findings(self):
        templates = glob.glob(os.path.join(SKILLS, "bpmn", "templates", "*.bpmn"))
        self.assertGreaterEqual(len(templates), 2)
        for path in templates:
            with self.subTest(template=os.path.basename(path)):
                report = validate.validate(path)
                self.assertEqual(report["findings"], [])

    def test_examples_have_no_findings(self):
        for path in glob.glob(os.path.join(ROOT, "examples", "**", "*.bpmn"), recursive=True):
            if os.path.basename(path).startswith("broken-"):
                continue
            with self.subTest(example=os.path.relpath(path, ROOT)):
                self.assertEqual(validate.validate(path)["findings"], [])

    def test_figjam_eval_files_are_structurally_sound(self):
        # Three of the FigJam eval files deliberately have no layout, to exercise the skill's
        # auto-layout path. Apart from that, they must be clean.
        for path in glob.glob(os.path.join(SKILLS, "bpmn-to-figjam", "evals", "files", "*.bpmn")):
            with self.subTest(file=os.path.basename(path)):
                found = pairs(validate.validate(path))
                self.assertIn(found, ([], [["DI-001", None]]))


class ReportShapeTests(unittest.TestCase):
    def test_report_fields(self):
        report = validate.validate(os.path.join(FIXTURES, "dead-end.bpmn"))
        self.assertEqual(set(report), {"ok", "validator", "processes", "summary", "findings", "not_checked"})
        self.assertEqual(report["not_checked"], ["NM-002"])
        self.assertEqual(report["summary"], {"ERROR": 1, "WARNING": 1, "INFO": 0})
        finding = next(f for f in report["findings"] if f["rule"] == "STR-006")
        self.assertEqual(finding["element_name"], "Escalate complaint")
        self.assertEqual(finding["element_type"], "task")
        self.assertEqual(finding["before"], ["Serious?"])
        self.assertEqual(finding["after"], [])
        self.assertEqual(finding["severity"], validate.RULES["STR-006"][0])

    def test_lane_and_pool_context(self):
        report = validate.validate(os.path.join(FIXTURES, "broken-references.bpmn"))
        finding = next(f for f in report["findings"] if f["rule"] == "STR-006")
        self.assertEqual(finding["lane"], "Clerk")

    def test_findings_sorted_by_severity(self):
        report = validate.validate(os.path.join(FIXTURES, "naming-and-gateways.bpmn"))
        order = {"ERROR": 0, "WARNING": 1, "INFO": 2}
        ranks = [order[f["severity"]] for f in report["findings"]]
        self.assertEqual(ranks, sorted(ranks))

    def test_deterministic(self):
        path = os.path.join(FIXTURES, "pool-mistakes.bpmn")
        self.assertEqual(json.dumps(validate.validate(path)), json.dumps(validate.validate(path)))


class CliTests(unittest.TestCase):
    def test_stdin(self):
        with open(os.path.join(FIXTURES, "dead-end.bpmn"), "rb") as fh:
            result = run_cli("-", stdin=fh.read())
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout.decode("utf-8"))["summary"]["ERROR"], 1)

    def test_text_format(self):
        out = run_cli(os.path.join(FIXTURES, "dead-end.bpmn"), "--format", "text").stdout.decode("utf-8")
        self.assertIn("STR-006", out)
        self.assertIn("Escalate complaint", out)
        self.assertTrue(out.strip().endswith("1 error(s), 1 warning(s), 0 info"))

    def test_rules_listing(self):
        result = run_cli("--rules")
        self.assertEqual(result.returncode, 0)
        out = result.stdout.decode("utf-8")
        for rid in list(validate.RULES) + list(validate.JUDGEMENT_RULES):
            self.assertIn(rid, out)

    def test_parse_error_is_reported_not_raised(self):
        result = run_cli(os.path.join(FIXTURES, "malformed.bpmn"))
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout.decode("utf-8"))["ok"])

    def test_missing_file(self):
        result = run_cli(os.path.join(FIXTURES, "does-not-exist.bpmn"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("Cannot read file", result.stdout.decode("utf-8"))

    def test_non_ascii_names_print_on_any_console(self):
        xml = (b'<?xml version="1.0" encoding="UTF-8"?><bpmn:definitions '
               b'xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" id="D"><bpmn:process id="P">'
               b'<bpmn:startEvent id="S" name="In\xc3\xadcio"/><bpmn:endEvent id="E" name="Fim"/>'
               b'<bpmn:task id="T" name="Revis\xc3\xa3o \xe2\x86\x92 aprova\xc3\xa7\xc3\xa3o"/></bpmn:process>'
               b'</bpmn:definitions>')
        result = run_cli("-", "--format", "text", stdin=xml)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Revisão → aprovação", result.stdout.decode("utf-8"))

    def test_namespace_prefix_does_not_matter(self):
        xml = io.BytesIO(
            b'<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" id="D"><process id="P">'
            b'<startEvent id="S" name="Go"/><task id="T" name="Do it"/><endEvent id="E" name="Done"/>'
            b'<sequenceFlow id="f1" sourceRef="S" targetRef="T"/><sequenceFlow id="f2" sourceRef="T" targetRef="E"/>'
            b'</process></definitions>')
        self.assertEqual(pairs(validate.validate(xml)), [["DI-001", None]])


if __name__ == "__main__":
    unittest.main()
