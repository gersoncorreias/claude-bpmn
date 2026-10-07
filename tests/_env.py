"""Shared paths for the tests. Import this before importing a skill script."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
FIXTURES = os.path.join(ROOT, "tests", "fixtures")
VALIDATOR = os.path.join(SKILLS, "bpmn-coach", "scripts", "validate.py")

sys.path.insert(0, os.path.dirname(VALIDATOR))
