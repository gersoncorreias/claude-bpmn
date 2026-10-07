# BPMN 2.0 Validation Rules

**The complete ruleset for `/bpmn-coach`.**

Every rule except NM-002 is checked by `scripts/validate.py`. NM-002 needs judgement, so the skill applies it. Each entry gives the ID, severity, what is detected and how to fix it. `tests/test_rules_doc.py` checks that this file and the script list the same rules with the same severities.

Severity meaning:

- **ERROR**: a broken reference or structural fault. The flow cannot run as drawn, or tools may refuse to load the file.
- **WARNING**: bad practice or ambiguous meaning.
- **INFO**: readability polish.

---

## STRUCTURAL (STR)

| ID | Severity | Condition to detect | Fix |
|----|----------|---------------------|-----|
| STR-001 | ERROR | A `<bpmn:process>` that has flow nodes but no `<bpmn:startEvent>` | Add a start event as the process entry point |
| STR-002 | ERROR | A `<bpmn:process>` that has flow nodes but no `<bpmn:endEvent>` | Add at least one end event |
| STR-003 | ERROR | A sequence flow or message flow whose `sourceRef` or `targetRef` is not the `id` of any element | Remove or correct the broken reference |
| STR-004 | ERROR | A `<bpmn:flowNodeRef>` inside a lane that is not the `id` of any flow node in the process | Remove the stale reference or add the missing element |
| STR-005 | ERROR | An element that cannot be reached by following sequence flows (and link events) from any start event of its process or sub-process: an orphaned node | Connect it to the flow or remove it |
| STR-006 | ERROR | A reachable element, other than an end event, with no outgoing sequence flow: the flow stops there. (Steps upstream of it are not reported again. A loop that never leads out is SF-003) | Add an outgoing flow to a downstream element, or end the path with an end event |
| STR-007 | ERROR | In a process that has lanes, a flow node that no lane lists in its `<bpmn:flowNodeRef>` | Add the element's ID to the correct lane |
| STR-008 | WARNING | A flow node listed in more than one leaf lane (nested lanes that repeat their children's refs are fine) | Remove it from all but the correct lane |

Event sub-processes (`triggeredByEvent="true"`) and compensation handlers (`isForCompensation="true"`) start on their own trigger, so STR-005 and STR-006 do not apply to them. A boundary event counts as reachable when the activity it is attached to is reachable.

---

## GATEWAYS (GW)

| ID | Severity | Condition to detect | Fix |
|----|----------|---------------------|-----|
| GW-001 | WARNING | A gateway with ≥2 incoming and ≥2 outgoing sequence flows, merging and splitting in one shape | Split it into two gateways: one that merges (many in, one out) followed by one that splits (one in, many out) |
| GW-002 | ERROR | A gateway with at most one incoming and at most one outgoing flow. It decides nothing, and the BPMN standard requires a gateway to have several incoming or several outgoing flows | Remove the gateway and connect its predecessor directly to its successor |
| GW-003 | WARNING | An exclusive, inclusive or complex gateway that splits (2+ outgoing) where one or more outgoing flows have no `name` | Add a condition label to every outgoing flow (e.g. "Yes", "No", "Urgent", "Standard") |
| GW-004 | WARNING | A parallel split (2+ outgoing) whose branches never all reach the same parallel join (2+ incoming) downstream | Add a parallel join where all branches converge before continuing |
| GW-005 | WARNING | An inclusive gateway with exactly two outgoing paths | Replace it with an exclusive gateway, unless "one or both" really is the intended meaning |
| GW-006 | INFO | A deciding gateway (exclusive, inclusive or complex, with 2+ outgoing) with no `name`, or a name that does not end with `?` | Name it as a question (e.g. "Approved?", "Urgent?", "Error occurred?") |

**Split vs. join quick reference:**

- Split: 1 incoming, 2+ outgoing.
- Join: 2+ incoming, 1 outgoing.
- GW-001 fires when both are true at once.

The BPMN standard allows a single gateway to merge and split. GW-001 is a WARNING, not an ERROR, because the shape is legal but hard to read.

---

## EVENTS (EVT)

| ID | Severity | Condition to detect | Fix |
|----|----------|---------------------|-----|
| EVT-001 | ERROR | A `<bpmn:startEvent>` that is the target of one or more sequence flows | Remove all incoming sequence flows from the start event |
| EVT-002 | ERROR | A `<bpmn:endEvent>` that is the source of one or more sequence flows | Remove all outgoing sequence flows from the end event |
| EVT-003 | ERROR | A `<bpmn:boundaryEvent>` with no `attachedToRef`, or one that does not point to an activity in the same process | Set `attachedToRef` to the ID of the task or sub-process it belongs to |
| EVT-004 | WARNING | A `<bpmn:intermediateCatchEvent>` with no event definition (message, timer, signal, conditional, link, …) | Add the event definition that says what it waits for |
| EVT-005 | WARNING | A process or sub-process with more than one start event that has no event definition | Keep only one plain start event, or give each start event a message, signal or timer definition |

---

## SEQUENCE FLOWS (SF)

| ID | Severity | Condition to detect | Fix |
|----|----------|---------------------|-----|
| SF-001 | ERROR | A sequence flow that connects to an element in a different pool, or across a sub-process boundary | Between pools, use a `<bpmn:messageFlow>` in the collaboration. Into a sub-process, connect to the sub-process itself |
| SF-002 | ERROR | A `<bpmn:sequenceFlow>` with no `id` attribute | Add a unique `id` (e.g. `Flow_review_to_approve`) |
| SF-003 | WARNING | A loop of sequence flows (A → B → … → A) with no flow and no boundary event leading out of it | Add a decision on the loop with at least one path that leaves it |
| SF-004 | WARNING | A `<bpmn:messageFlow>` whose two ends are in the same pool | Replace it with a sequence flow. Message flows are for communication between pools |

---

## LANES & POOLS (LP)

| ID | Severity | Condition to detect | Fix |
|----|----------|---------------------|-----|
| LP-001 | WARNING | A `<bpmn:participant processRef="X">` where `X` is not the `id` of any `<bpmn:process>` in the file | Correct `processRef` to the actual process `id` |
| LP-002 | INFO | A pool with exactly one top-level lane | Remove the lane set and assign the elements directly to the process |

---

## NAMING CONVENTIONS (NM)

| ID | Severity | Condition to detect | Fix |
|----|----------|---------------------|-----|
| NM-001 | WARNING | An activity (any task type, sub-process or call activity) with no `name`, or a name equal to its `id` (e.g. `Task_3`) | Add a descriptive name |
| NM-002 | WARNING | A task name that is a noun phrase with no verb (e.g. "Ticket review", "Invoice"). **Judgement: applied by the skill, not the script** | Rewrite it as verb + object (e.g. "Review ticket", "Send invoice") |
| NM-004 | INFO | A start or end event with no `name` | Name the trigger (start) or the outcome (end) |

---

## DIAGRAM INTERCHANGE (DI)

DI is the layout part of the file: where each shape and line is drawn.

| ID | Severity | Condition to detect | Fix |
|----|----------|---------------------|-----|
| DI-001 | WARNING | A flow node, pool or lane with no `<bpmndi:BPMNShape>`, or a file with no `<bpmndi:BPMNDiagram>` at all | Add a `BPMNShape` with `dc:Bounds` coordinates |
| DI-002 | WARNING | A sequence flow or message flow with no `<bpmndi:BPMNEdge>` | Add a `BPMNEdge` with at least two `di:waypoint` entries |
| DI-003 | WARNING | A `BPMNShape` or `BPMNEdge` whose `bpmnElement` is not the `id` of anything in the model | Remove the orphaned layout entry |
| DI-004 | INFO | Two flow nodes drawn with identical `dc:Bounds` | Move one shape so they don't overlap |
| DI-005 | INFO | A flow node whose shape extends outside its pool's bounds (boundary events excluded) | Move or resize so the shape sits inside the pool |

---

## Retired IDs

These were merged into other rules in 1.0.0 so the same problem is not reported twice. The IDs are not reused.

| ID | Merged into |
|----|-------------|
| SF-005 | GW-003 (unlabelled path out of a decision) |
| NM-003 | GW-006 (decision not phrased as a question) |

---

## Common multi-rule failure patterns

### "Spaghetti gateway": GW-001 + GW-003
A single diamond has 3 incoming and 3 outgoing flows, and none of the outgoing flows are named.

### "Hanging parallel": GW-004
A parallel gateway splits into two lanes, but there is no join, and each branch ends at its own end event. The diagram shows parallel work that never comes back together.

### "Zombie task": STR-005 + DI-001
A task exists in the XML, has no sequence flows and no layout shape. It was copied in and forgotten.

### "Missing conditions": GW-003 + GW-006
An exclusive gateway splits into three paths. It has no question as its name and no labels on its flows, so a reader cannot tell which path is taken when.
