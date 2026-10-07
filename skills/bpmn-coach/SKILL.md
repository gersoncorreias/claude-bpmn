---
name: bpmn-coach
description: "Validates BPMN 2.0 process diagrams for notation errors and workflow mistakes. Runs a deterministic validator script over the XML, then reports the findings by severity in plain business language with actionable fixes. Can call /bpmn to interpret a diagram first, and can trigger /bpmn to regenerate a corrected version. Trigger on: 'validate this BPMN', 'check this process', 'find mistakes in', 'review this diagram', 'is this BPMN correct', 'what's wrong with this process', 'coach me on this BPMN', 'BPMN review', 'process quality check', 'audit this BPMN', 'BPMN mistakes'."
---

# BPMN Coach

Validates BPMN 2.0 diagrams for spec violations, notation mistakes, and workflow anti-patterns.
The checks are done by `scripts/validate.py` (Python standard library, no install), so the same file always gets the same findings. Your job is the part that needs judgement: one naming rule the script cannot check, and turning the findings into a report a business reader can act on.

---

## Invocation modes

| Mode | Trigger | Action |
|------|---------|--------|
| **Validate file** | "Validate this BPMN" + file path | Run validator → judgement rule → report |
| **Validate inline XML** | User pastes raw XML | Save to a temp file → run validator → judgement rule → report |
| **Called by another skill** | skill passes file path or XML string | Return structured report as plain text |
| **Full review + fix** | "Review and fix this BPMN" | Validate → report → offer to call `/bpmn` to regenerate corrected version |

---

## Step 1 — Obtain the BPMN XML

Choose the first source that applies:

1. **File path provided** → use it as is.
2. **Raw XML pasted** → use it directly.
3. **Called by another skill** → accept the XML string parameter passed by the caller.
4. **"Review and fix" mode** → use the file path directly (`/bpmn` Step 0 is only needed if a human-readable process summary is also requested alongside the validation).

If the XML was pasted or passed as a string, save it to a temporary `.bpmn` file first so the validator can read it.

If no XML or file path is provided, ask the user to share the `.bpmn` file path or paste the XML.

---

## Step 2 — Run the validator

```bash
python "{skill_dir}/scripts/validate.py" "path/to/diagram.bpmn"
```

It prints a JSON report and exits with `0` (no errors), `1` (at least one ERROR) or `2` (the file is not well-formed XML or not BPMN 2.0). Use `python3` if `python` is not on the path.

```json
{
  "ok": true,
  "processes": ["Purchase Request"],
  "summary": {"ERROR": 1, "WARNING": 2, "INFO": 0},
  "findings": [
    {
      "rule": "GW-003", "severity": "WARNING", "title": "Decision has an unlabelled outgoing path",
      "element_id": "Gateway_1", "element_name": "Approved?", "element_type": "exclusiveGateway",
      "lane": "Manager", "pool": "Purchase Request",
      "message": "1 of 2 outgoing paths have no condition label (Flow_7).",
      "before": ["Review request"], "after": ["Create purchase order", "Request rejected"]
    }
  ],
  "not_checked": ["NM-002"]
}
```

- `lane`, `pool`, `before` and `after` are there so you can point at the element the way a reader sees it, even when it has no name ("the unlabelled decision after **Review request**").
- Exit code `2` (`"ok": false`): report the `error` text in plain words ("the file is not a valid BPMN diagram: …") and stop.
- `python --rules` lists every rule. The full definitions, with the reason and fix for each, are in `references/bpmn-validation-rules.md`.

**If Python is not available,** apply the rules in `references/bpmn-validation-rules.md` by reading the XML yourself, and say in the report that the check was done by hand.

---

## Step 3 — Apply the judgement rule

`not_checked` lists the rules the script leaves to you. Today that is one:

- **NM-002 (WARNING) — task name has no verb.** Read each task name. Flag names that are only a noun or noun phrase ("Ticket review", "Invoice") and suggest a verb + object rewrite ("Review ticket", "Send invoice"). Do not flag names that already start with a verb, and do not flag events or gateways.

Add these findings to the ones from the script before writing the report.

---

## Step 4 — Produce the validation report

### Language rules — ALWAYS apply

**Never use technical identifiers in the output.** The reader is a business user looking at the diagram image — they cannot open the XML.

| ❌ Never write | ✅ Write instead |
|---------------|-----------------|
| `Activity_0l0zfc2` | "the **Assign reviewer** step" |
| `GW_Status` | "the **Status?** decision" |
| `Flow_1ra3uym` | "the message sent from **Assign reviewer** to the main pool" |
| `Process_1r14ome` | "the **Contract Review** process" |
| `sequenceFlow`, `endEvent`, `exclusiveGateway` | "connecting arrow", "end of the process", "decision point" |
| `Lane_Legal` | "the **Legal** lane" |
| Rule IDs in the body of a finding | Put the rule ID only at the very start of the line as a small tag; never repeat it mid-sentence |

Describe every issue in terms of **what the user sees on the diagram**: the visible step name, the lane name, the arrow label, the diamond shape label. If an element has no visible name, describe it by its position or neighbors ("the unlabelled decision diamond after 'Log request'").

### Output structure

```
## BPMN Coach Report: [process name as it appears on the diagram]

### Summary
[N] issue(s) to fix · [N] improvement(s) to consider

### Must Fix ❌
These issues make the diagram incomplete or incorrect. Resolve them before sharing or using this process.

**[Short issue title]**
[2–3 sentences in plain business language: where in the diagram the problem is, what is wrong, what happens as a result. Reference visible step names, lane names, and arrow labels — no IDs or XML terms.]
→ **How to fix:** [Plain-language instruction a process designer can act on while looking at the diagram.]

### Should Fix ⚠
These issues won't break the diagram but create ambiguity or go against process modeling best practices.

**[Short issue title]**
[Same style as above.]
→ **How to fix:** [Plain-language instruction.]

### Consider Improving ℹ
Optional polish — the diagram works as-is but these changes would make it clearer for readers.

**[Short issue title]**
[One or two sentences.]
→ **Suggestion:** [Plain-language suggestion.]

### Verdict
✅ No issues found — diagram is clean and ready to share
⚠ Ready to share with minor improvements recommended
❌ Issues found — resolve the "Must Fix" items before using this diagram
```

### Formatting rules
- Omit a section entirely when it has zero findings.
- Each finding is a titled block (bold short title + paragraph + fix line) — not a bullet list.
- The rule ID appears only as a small parenthetical at the end of the fix line, e.g. `(STR-002)`. Never put it in the title or body.
- Group related findings under one block when they share the same root cause.
- No jargon: "token", "BPMN spec", "DI section", "sequenceFlow", "isExecutable" must never appear in the output. Translate to plain language: "flow of work", "diagram standard", "visual layout section", "connecting arrow", "descriptive diagram".
- Keep each finding self-contained — a reader should be able to find and fix it using only the diagram image.

---

## Step 5 — Offer to fix (optional)

If any ERRORs or WARNINGs were found, append this offer after the report:

> **Want me to fix this?** I can invoke `/bpmn` to generate a corrected version of the diagram
> with the issues above resolved. Just say "yes, fix it" or point me to a specific rule to address first.

If the user accepts:
1. Describe the corrected process in plain language, incorporating the fixes from the report.
2. Call `/bpmn` with that description to generate new XML + HTML snippet.
3. Run `scripts/validate.py` on the new file and confirm the errors are gone before you say it is fixed. If any remain, fix them and check again.

---

## Inter-skill communication

### Called by another skill
Accept a parameter containing either a file path or a raw XML string.
A calling skill that only needs the raw findings can run `scripts/validate.py` itself and read the JSON.
Otherwise, return the structured report text as plain text so the calling skill can embed it in its own output.
Do not include the Step 5 fix offer when called programmatically — only when responding to a human.

### Calling `/bpmn` for interpretation
When the user requests a human-readable summary alongside validation (e.g. "explain and validate this BPMN"),
invoke the `/bpmn` skill in interpret mode (Step 0) first, then run validation.
Output: prose description first, then the validation report.

### Calling `/bpmn` for regeneration (Step 5 flow)
Pass a corrected process description as plain text to `/bpmn`.
`/bpmn` will generate the corrected XML + HTML snippet.
The coach does not modify XML directly — it delegates all generation to `/bpmn`.

---

## Quick reference — severity guide

| Severity | Meaning | Action |
|----------|---------|--------|
| ERROR | Broken reference or structural fault: the flow cannot run as drawn, or tools may refuse to load it | Must fix before using |
| WARNING | Bad practice, ambiguous meaning, or a missing best-practice element | Should fix before sharing |
| INFO | Style or readability improvement | Fix at your discretion |

For the complete rule definitions with examples, see `references/bpmn-validation-rules.md`.
