# Changelog

## 1.0.0 — 2026-10-07

First public release.

- `bpmn`: generates BPMN 2.0 XML with full layout (opens in bpmn.io and Camunda Modeler) from a description, and reads an existing `.bpmn` file back into structured prose. It checks its own output with the `bpmn-coach` validator before saving. Two generic templates: an IT helpdesk ticket (lanes, decisions, a loop back, a non-interrupting SLA timer) and a purchase approval (two pools, a parallel split and join, message flows). The HTML viewer card pins bpmn-js 18.31.0 for every asset.
- `bpmn-coach`: validation now runs in `scripts/validate.py` (standard library, deterministic, JSON or text output, exit codes for CI). The skill applies the one judgement rule (task names without a verb) and writes the plain-language report.
- Ruleset changes since the private drafts:
  - GW-001 (a gateway that merges and splits) is a WARNING, not an ERROR. The BPMN standard allows it; it is just hard to read.
  - GW-002 covers every gateway type with one way in and one way out, not only exclusive gateways.
  - STR-006 reports the step where a path stops, not every step upstream of it.
  - SF-005 is merged into GW-003, and NM-003 into GW-006, so one problem is reported once.
  - STR-003 and DI-002 now also cover message flows. DI-001 also covers pools and lanes.
- `bpmn-to-figjam`: draws into a new `BPMN: <process>` section to the right of existing content and never deletes board content. Replacing an earlier render needs the user's confirmation. Fonts are loaded explicitly, and the Figma MCP tool is named.
- Evals for all three skills (`skills/*/evals/evals.json`). The FigJam evals now match the bpmn.io colour scheme the skill uses.
- Tests: one broken fixture per rule family with exact expected findings, a check that the rules reference matches the script, repo hygiene checks, and a bpmn-moddle parse check of every shipped diagram. CI on Python 3.9 and 3.13.
