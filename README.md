# BPMN for Claude Code

Three [Claude Code](https://code.claude.com) skills that turn process-mapping sessions into standard BPMN 2.0 diagrams. Give Claude the meeting transcript and get back a diagram plus mapping notes: every step traced to a quote, contradictions between speakers flagged, and open questions listed for the process owner. Then check the diagram against the notation rules and hand it to stakeholders in FigJam.

```
/bpmn Map the refund process from this transcript: refund-mapping-session.vtt
```

![A customer refund process mapped from a meeting transcript, rendered in bpmn.io](docs/images/transcript-customer-refund.png)

That diagram came from a [three-minute fictional session](examples/transcript-to-bpmn/refund-mapping-session.vtt). The [mapping notes](examples/transcript-to-bpmn/customer-refund-mapping-notes.md) show what the skill does with what it hears:

- **Every step has evidence.** "Issue refund to original payment method" links to 00:02:09, Dana: "we issue the refund to the original payment method".
- **It flags contradictions instead of picking a side.** The agent said the approval limit is $200 and the lead said $250, so the diagram asks "Over approval limit?" and the notes record both.
- **It leaves gaps open instead of inventing them.** Nobody agreed what happens when the lead rejects a refund, so that path ends in "Rejected by lead (next step open)" and becomes question 1 for the process owner.
- **Roles, not people.** Speakers become lanes (Support Agent, Support Lead, Finance). Names stay in the notes, which go back to the participants for sign-off.

| Skill | What it does |
|---|---|
| [`bpmn`](skills/bpmn/SKILL.md) | Turns a mapping-session transcript (`.vtt`, `.srt`, `.txt`, `.md`) or a plain description into a `.bpmn` file that opens in [bpmn.io](https://demo.bpmn.io) and Camunda Modeler. Transcript mode also writes the mapping notes. It can read an existing `.bpmn` back into structured prose: roles, steps, decisions, handoffs |
| [`bpmn-coach`](skills/bpmn-coach/SKILL.md) | Validates a diagram and explains every problem in plain business language, ranked Must fix / Should fix / Consider. The checks run in a [standard-library Python script](skills/bpmn-coach/scripts/validate.py), so the same file always gets the same findings |
| [`bpmn-to-figjam`](skills/bpmn-to-figjam/SKILL.md) | Draws a `.bpmn` file in a FigJam board through the Figma MCP server, styled like bpmn.io, inside its own section so existing board content is never touched |

The skills work together. `bpmn` checks its own output with `bpmn-coach` before saving. `bpmn-coach` can ask `bpmn` to regenerate a corrected diagram, and the result is checked again.

## Get started

### 1. Check what you need

- [Claude Code](https://code.claude.com), signed in.
- Python 3.9 or newer (`python --version`). The skills use it for the validator.
- Optional: a connected [Figma MCP server](https://help.figma.com/hc/en-us/articles/32132100833559), only for `bpmn-to-figjam`.

### 2. Install the skills

**macOS, Linux, or Windows with Git Bash:**

```bash
git clone https://github.com/gersoncorreias/claude-bpmn.git
cd claude-bpmn
./install.sh
```

**Windows PowerShell:**

```powershell
git clone https://github.com/gersoncorreias/claude-bpmn.git
cd claude-bpmn
$dest = "$env:USERPROFILE\.claude\skills"
New-Item -ItemType Directory -Force $dest | Out-Null
Copy-Item -Recurse -Force skills\bpmn, skills\bpmn-coach, skills\bpmn-to-figjam $dest
```

Both copy three folders into `~/.claude/skills/`, which makes the skills available in every project. To install for one project only, run `./install.sh --project <dir>`.

### 3. Check that it worked

```bash
python ~/.claude/skills/bpmn-coach/scripts/validate.py ~/.claude/skills/bpmn/templates/purchase-approval.bpmn --format text
```

You should see `0 error(s), 0 warning(s), 0 info`. Then **start a new Claude Code session**, so it loads the skills, and type `/bpmn`. The skill should appear in the list.

### 4. Try the bundled example

From the `claude-bpmn` folder, in a new Claude Code session:

```
/bpmn Map the refund process from examples/transcript-to-bpmn/refund-mapping-session.vtt
```

You get two files in the current folder:

- `customer-refund.bpmn`. Open it at [demo.bpmn.io](https://demo.bpmn.io) (drag the file onto the page) or in Camunda Modeler.
- `customer-refund-mapping-notes.md`, with the evidence for each step, the contradictions and the open questions.

Compare them with the reference output in [`examples/transcript-to-bpmn/`](examples/transcript-to-bpmn/). The wording will differ from run to run; the structure should match.

### 5. Map one of your own sessions

1. **Record the session with everyone's consent**, and download the transcript. Teams and Zoom both export `.vtt` files; a plain-text transcript or notes also work.
2. Keep it to **one process per session** where you can. If several are discussed, the skill asks which one to map.
3. Run `/bpmn Map the <name> process from <path to transcript>`.
4. **Send the mapping notes to the participants and the process owner.** The diagram is a draft until they confirm the open questions.
5. After changes, check the diagram again with `/bpmn-coach validate <file>.bpmn`, and share it with `/bpmn-to-figjam <file>.bpmn <FigJam board URL>`.

You can also describe a process directly, with no transcript:

```
/bpmn Create a BPMN for our employee onboarding: HR prepares the contract, IT sets up the laptop and
accounts in parallel, then the manager schedules the first week.
```

**[examples/README.md](examples/README.md)** walks through each skill with real output, including a flawed diagram and the coach's report on it.

### Update or remove

- **Update:** `git pull` in the `claude-bpmn` folder, then run the install step again. Use `./install.sh --link` once, and every later `git pull` updates the skills on its own (macOS and Linux).
- **Remove:** delete the `bpmn`, `bpmn-coach` and `bpmn-to-figjam` folders from `~/.claude/skills/`.

### If something doesn't work

| Symptom | Fix |
|---|---|
| `/bpmn` is not in the list | Start a new Claude Code session; skills load at session start. Check that `~/.claude/skills/bpmn/SKILL.md` exists |
| `python: command not found` | Install Python 3.9+, or use `python3`. Without Python the coach still works, but checks by hand and says so |
| The diagram opens but shapes overlap | The layout is generated. Open the file in bpmn.io or Camunda Modeler and drag things into place; the process logic is unaffected |
| `/bpmn-to-figjam` says no Figma tool is available | Connect Figma's MCP server in Claude Code, then retry |

## The validator on its own

The coach's checks are a single script with no dependencies. You can use it outside Claude, in CI or a pre-commit hook:

```text
$ python skills/bpmn-coach/scripts/validate.py examples/broken-expense-claim.bpmn --format text
ERROR    STR-006  Employee / Revise expense claim: This element has no outgoing flow, so the process stops here without reaching an end event.
WARNING  GW-003   Manager / Decision: 2 of 2 outgoing paths have no condition label (Flow_4, Flow_5).
INFO     GW-006   Manager / Decision: Name decisions as a question, e.g. 'Approved?'.
1 error(s), 1 warning(s), 1 info
```

- **Output.** JSON by default (`--format text` for people). Each finding carries the lane, pool and neighbouring steps, so it can be described without IDs.
- **Exit codes.** `0` means no errors, `1` means at least one error, and `2` means the file is not valid XML or not BPMN 2.0.
- **Rules.** 32 checks run in the script, plus one that needs judgement (task names without a verb), which the skill applies. Run `--rules` for the list. [The rules reference](skills/bpmn-coach/references/bpmn-validation-rules.md) has the condition and fix for each.

| Family | Catches |
|---|---|
| Structure (STR) | Missing start or end, broken references, steps nothing leads to, paths that stop before the end, lane assignment |
| Gateways (GW) | Diamonds that merge and split at once, decisions that decide nothing, unlabelled paths, parallel splits that never join |
| Events (EVT) | Flows into a start or out of an end, boundary events on the wrong thing, catch events with no trigger |
| Flows (SF) | Sequence flows across pools, loops with no way out, message flows inside one pool |
| Pools and lanes (LP) | Pools pointing at missing processes, single-lane pools |
| Naming (NM) | Unnamed steps and events, task names without a verb |
| Layout (DI) | Elements or flows missing from the drawing, stray shapes, overlaps, shapes outside their pool |

Valid patterns that simple checkers get wrong are handled correctly: link events, event sub-processes, compensation handlers, boundary events, nested lanes and expanded sub-processes.

## What it will and won't do

- **Descriptive diagrams, not executable ones.** Generated processes are `isExecutable="false"`, for documentation, analysis and stakeholder review. Nothing here deploys to a BPMN engine.
- **A draft, not a verdict.** A transcript only holds what people said in the room. The mapping notes exist so the process owner can confirm or correct each step before anyone relies on the diagram.
- **Files stay local.** `bpmn` and `bpmn-coach` read and write files on your machine. Transcripts are read by Claude in your session like any other file, so handle recordings of colleagues according to your company's policy. Only `bpmn-to-figjam` sends anything out, and only to the Figma board you name.
- **FigJam renders are approximate.** FigJam has no BPMN shapes, so events, gateways and markers are drawn with FigJam's basic shapes and connectors. Expanded sub-processes are supported one level deep.
- **Layout is generated, not designed.** `bpmn` places elements on a grid. Complex diagrams may need a tidy-up in bpmn.io or Camunda Modeler before you present them.

## Development

```bash
python -m unittest discover -s tests -v              # validator, rules doc, repo hygiene (standard library only)
cd tests/bpmnio && npm ci && npm run check           # every shipped .bpmn parses cleanly in bpmn-moddle
```

`tests/fixtures/` has one deliberately broken diagram per rule family. `expected.json` lists the exact findings each must produce, and a test fails if any rule has no fixture. Each skill also has `evals/evals.json` with prompts and assertions for checking the skill's behaviour in Claude Code. See [CONTRIBUTING.md](CONTRIBUTING.md).

## About

Built by [Gerson Correia](https://gersoncorreia.com), a delivery consultant for remote software teams. I run process-mapping sessions with the people who do the work, and built these skills so the map comes out of the session instead of a week of follow-up. Questions and ideas are welcome in [Issues](https://github.com/gersoncorreias/claude-bpmn/issues) or on [LinkedIn](https://www.linkedin.com/in/gerson-correia).

## License

[MIT](LICENSE)
