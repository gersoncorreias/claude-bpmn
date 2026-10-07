"""Repository hygiene: skills are well-formed, evals point at real files, and no real data slips in."""
import glob
import json
import os
import re
import unittest
import xml.etree.ElementTree as ET

from _env import ROOT, SKILLS

SKILL_NAMES = ["bpmn", "bpmn-coach", "bpmn-to-figjam"]

# Examples must be generic. These terms came from real engagements in early drafts; keep them out.
BANNED = [r"\bAsana\b", r"\bSlack\b", r"\bFDE\b", r"\bDE\b", r"capacity planner", r"10–15", r"30–60"]
TEXT_EXT = {".md", ".bpmn", ".json", ".py", ".mjs", ".sh", ".yml", ".txt"}


def repo_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules", "__pycache__")]
        for name in filenames:
            path = os.path.join(dirpath, name)
            if os.path.splitext(name)[1] in TEXT_EXT and os.path.abspath(path) != os.path.abspath(__file__):
                yield path


class SkillTests(unittest.TestCase):
    def test_frontmatter(self):
        for name in SKILL_NAMES:
            with self.subTest(skill=name):
                with open(os.path.join(SKILLS, name, "SKILL.md"), encoding="utf-8") as fh:
                    text = fh.read()
                self.assertTrue(text.startswith("---\n"))
                front = text.split("---\n")[1]
                self.assertRegex(front, r"(?m)^name: %s$" % re.escape(name))
                self.assertRegex(front, r"(?m)^description: \S")

    def test_referenced_skill_files_exist(self):
        # Paths a skill tells Claude to open, such as references/x.md, templates/x.bpmn, scripts/x.py.
        pattern = re.compile(r"`(?:\{skill_dir\}/)?((?:references|templates|scripts|evals)/[\w./-]+)`")
        for name in SKILL_NAMES:
            with open(os.path.join(SKILLS, name, "SKILL.md"), encoding="utf-8") as fh:
                text = fh.read()
            for rel in pattern.findall(text):
                if "[" in rel:
                    continue
                with self.subTest(skill=name, path=rel):
                    self.assertTrue(os.path.exists(os.path.join(SKILLS, name, rel)), rel)

    def test_no_references_to_skills_outside_this_repo(self):
        for name in SKILL_NAMES:
            with open(os.path.join(SKILLS, name, "SKILL.md"), encoding="utf-8") as fh:
                text = fh.read()
            # Skills are invoked as `/name` in backticks.
            for slash in re.findall(r"`/([a-z][a-z0-9-]+)`", text):
                if slash in SKILL_NAMES:
                    continue
                with self.subTest(skill=name, reference=slash):
                    self.fail("SKILL.md mentions /%s, which is not part of this repo" % slash)

    def test_every_bpmn_file_is_well_formed(self):
        broken = os.path.join(SKILLS, "bpmn-coach", "evals", "files")
        for path in glob.glob(os.path.join(SKILLS, "**", "*.bpmn"), recursive=True):
            if path.startswith(broken):
                continue
            with self.subTest(file=os.path.relpath(path, ROOT)):
                ET.parse(path)


class EvalTests(unittest.TestCase):
    def test_eval_files_parse_and_exist(self):
        for path in glob.glob(os.path.join(SKILLS, "*", "evals", "evals.json")):
            skill_dir = os.path.dirname(os.path.dirname(path))
            with self.subTest(evals=os.path.relpath(path, ROOT)):
                with open(path, encoding="utf-8") as fh:
                    data = json.load(fh)
                self.assertEqual(data["skill_name"], os.path.basename(skill_dir))
                ids = [e["id"] for e in data["evals"]]
                self.assertEqual(len(ids), len(set(ids)))
                for ev in data["evals"]:
                    self.assertTrue(ev["prompt"] and ev["expected_output"] and ev["assertions"])
                    for f in ev.get("files", []):
                        self.assertTrue(os.path.exists(os.path.join(skill_dir, f)), f)

    def test_every_skill_has_evals(self):
        for name in SKILL_NAMES:
            with self.subTest(skill=name):
                self.assertTrue(os.path.exists(os.path.join(SKILLS, name, "evals", "evals.json")))


class NoRealDataTests(unittest.TestCase):
    def test_no_banned_terms(self):
        for path in repo_files():
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            for term in BANNED:
                for m in re.finditer(term, text):
                    line = text.count("\n", 0, m.start()) + 1
                    with self.subTest(file=os.path.relpath(path, ROOT), line=line, term=term):
                        self.fail("generic examples only: found %r" % m.group(0))


if __name__ == "__main__":
    unittest.main()
