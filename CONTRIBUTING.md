# Contributing

Thanks for helping improve these skills. Issues and pull requests are welcome.

## Ground rules

- **Standard library only** for anything a skill runs. Anyone should be able to install with `./install.sh` and nothing else. The bpmn-moddle check in `tests/bpmnio/` is a development tool, not a runtime dependency.
- **Python 3.9+.** CI runs the tests on 3.9 and on a current version.
- **No real data.** Examples, templates and fixtures use generic processes (helpdesk, purchasing, onboarding). Never commit a diagram, name or figure from a real organisation. `tests/test_repo.py` blocks some terms that leaked into early drafts.
- **Keep checks deterministic, and keep judgement in `SKILL.md`.** If a rule can be decided from the XML alone, it belongs in `validate.py` with a test. If it needs reading comprehension (is this name a verb phrase?), it belongs in the skill.

## Running the tests

```bash
python -m unittest discover -s tests -v
cd tests/bpmnio && npm ci && npm run check
```

## Adding or changing a rule

1. Add or change it in `RULES` in `skills/bpmn-coach/scripts/validate.py`.
2. Document it in `skills/bpmn-coach/references/bpmn-validation-rules.md` with the same ID and severity. `tests/test_rules_doc.py` fails if the two disagree.
3. Add a fixture to `tests/fixtures/` that triggers it, and record the exact findings in `tests/fixtures/expected.json`. A test fails if any rule has no fixture.
4. Never reuse a retired ID. List retired IDs in the rules reference.

## Changing a skill

- `skills/<name>/SKILL.md` is what Claude reads. Keep it accurate: if you change the validator's output or a template, update the skill text too.
- Templates in `skills/bpmn/templates/` must produce zero validator findings and parse cleanly in bpmn-moddle (both are tested).
- Update `skills/<name>/evals/evals.json` when behaviour changes, and run the affected evals in Claude Code before opening a pull request.
- Add a line to [CHANGELOG.md](CHANGELOG.md).
