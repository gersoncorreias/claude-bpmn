---
name: bpmn
description: "Generates standard BPMN 2.0 XML process diagrams AND interprets existing .bpmn files into structured prose descriptions for other skills. Use to: model a process, create a BPMN diagram, visualize a workflow, document a ticket flow, map a process for process improvement, or export a .bpmn file. Also used to READ and DESCRIBE an existing .bpmn file — returning roles, steps, gateways, and handoffs as structured text that any other skill can consume. Trigger on: 'create a BPMN', 'model this process', 'draw a process diagram', 'generate a .bpmn file', 'visualize this workflow', 'BPMN for', 'process map', 'swimlane diagram', 'flowchart for Camunda', 'bpmn.io', 'interpret this .bpmn', 'describe this .bpmn', 'read this bpmn file', 'what does this bpmn show', 'explain this process diagram', 'summarize this .bpmn for'."
---

# BPMN 2.0 Diagram Generator

Produces two artefacts per invocation:
1. **A `.bpmn` file** — valid BPMN 2.0 XML with DI coordinates, openable in Camunda / bpmn.io
2. **An HTML snippet** — self-contained viewer card for embedding in any HTML report

---

## Invocation modes

| Mode | Trigger | Action |
|---|---|---|
| **From description** | "Create a BPMN for our support ticket flow" | Generate XML from the described process |
| **From text steps** | "Convert: Request → Manager approval → Finance → Done" | Parse steps, map to BPMN elements, generate |
| **From template** | "Use the purchase-approval template" | Load `templates/[name].bpmn` and adapt it |
| **Called by another skill** | a process-analysis or reporting skill | Accept process name + steps, return XML + HTML snippet |
| **Interpret .bpmn file** | "Describe this .bpmn", another skill passes a file path | Parse the XML, return structured prose — no new diagram generated |

When invoked **only to interpret** (no generation requested), jump directly to [Step 0 — Interpret a .bpmn file](#step-0--interpret-a-bpmn-file) and stop. Do not generate any new XML or HTML.

---

## Step 0 — Interpret a .bpmn file

Use this mode when:
- The caller passes a `.bpmn` file path or raw XML and asks for a description
- Another skill (process analysis, reporting, coaching) needs a plain-language summary of an existing process before doing its own analysis
- The user asks "what does this .bpmn show?", "explain this process", "summarize this diagram for me"

### How to parse

1. **Read the file** — use the Read tool on the provided path, or accept the raw XML string from the caller.
2. **Extract the structure** from the XML:
   - `<bpmn:collaboration>` / `<bpmn:participant>` → pool name (= overall process name)
   - `<bpmn:lane name="...">` + child `<bpmn:flowNodeRef>` → role and which elements belong to it
   - `<bpmn:startEvent>`, `<bpmn:endEvent>` → process boundaries
   - `<bpmn:task>`, `<bpmn:userTask>`, `<bpmn:serviceTask>`, `<bpmn:sendTask>`, `<bpmn:receiveTask>` → work steps (note the type)
   - `<bpmn:exclusiveGateway>` → XOR decision (one path taken)
   - `<bpmn:parallelGateway>` → AND split/join (all paths taken)
   - `<bpmn:inclusiveGateway>` → OR gateway (one or more paths)
   - `<bpmn:sequenceFlow sourceRef="..." targetRef="..." name="...">` → flow order and condition labels
   - `<bpmn:boundaryEvent>`, `<bpmn:intermediateThrowEvent>`, `<bpmn:intermediateCatchEvent>` → intermediate events
   - `<bpmn:messageFlow>` → cross-pool communication
3. **Reconstruct the flow order** by following `sequenceFlow` chains from each start event to each end event.
4. **Identify cross-lane handoffs** — any `sequenceFlow` connecting a `flowNodeRef` in one lane to a `flowNodeRef` in another lane.

### Output format (structured prose)

Return this exact structure so other skills can parse it reliably:

```
## Process: [pool/participant name]

### Roles (swimlanes)
- [Lane name 1]
- [Lane name 2]
...

### Flow summary
[2–4 sentences describing the end-to-end flow in plain language — start trigger, main path, how it ends.]

### Steps by role
**[Lane name 1]**
1. [Step name] ([element type: task / user task / service task / etc.])
2. [Step name]
...

**[Lane name 2]**
1. [Step name]
...

### Decision points (gateways)
- [Gateway name or ID]: [XOR / AND / OR] — [what is being decided or split, and what the outgoing paths are]

### Cross-lane handoffs
- [Source lane] → [Target lane]: after "[source step name]", triggers "[target step name]"

### Process boundaries
- Starts: [start event name or trigger]
- Ends: [end event name(s)]

### Notes
[Any boundary events, intermediate events, error flows, or unusual patterns worth flagging — omit section if none.]
```

### Rules
- **Never generate new XML** in this mode. Output only the structured prose above.
- If the XML is malformed or a referenced ID is missing from the DI section, note it under Notes but still describe what can be parsed.
- If called by another skill, return the structured prose as plain text so the calling skill can embed it directly in its own output.
- Keep the Flow summary concise — it is the part most likely to be quoted by the calling skill.

---

## Output rules (read before generating anything)

1. **Never print XML to the terminal.** Always use the Write tool to save `.bpmn` files to disk.
2. **One diagram per response.** If multiple diagrams are requested, generate the first, confirm it is saved, then stop. Generate the next on the following turn.
3. **Skip HTML snippet for complex diagrams** (>8 tasks or >4 lanes) unless explicitly requested.
4. **Always include `<bpmndi:BPMNEdge>` for every sequence flow.** bpmn.io requires them to draw connecting lines — omitting them produces disconnected shapes with no arrows. Use compact single-line format with the fewest waypoints that draw the line: 2 for a straight flow (right edge of source → left edge of target), 3 or 4 for a flow that changes lane or row (see the DI conventions in Step 2).
5. **Compact DI formatting.** Write each `BPMNShape` and `BPMNEdge` on one line.

Violating any of these rules risks hitting the output limit and truncating the diagram.

---

## Step 1 — Understand the process

Before generating XML, identify:
- **Process name** — becomes the file name and diagram title
- **Swimlanes / roles** — who does what (Support Coordinator, Engineer, Manager, etc.)
- **Steps per lane** — ordered list of tasks, decisions, and events
- **Cross-lane handoffs** — where does control pass from one lane to another?
- **Gateways** — decision points (exclusive/XOR = one path, parallel/AND = all paths)

Consult `references/bpmn2-element-reference.md` to map natural language to correct BPMN elements.

---

## Step 2 — Generate BPMN 2.0 XML

### Option A — Start from a bundled template

Two worked examples ship in `{skill_dir}/templates/`. Read one with the Read tool when the requested process is close to it, then rename lanes, steps and labels and adjust the layout. Do not ship a template unchanged as if it were the user's process.

| Template | Shows |
|---|---|
| `templates/it-helpdesk-ticket.bpmn` | Three lanes, two decisions, a merge, a loop back, and a non-interrupting timer (SLA) boundary event |
| `templates/purchase-approval.bpmn` | Two pools, a parallel split and join, and message flows to an external participant |

### Option B — Generate inline for a new process

Build BPMN 2.0 XML directly using the structure in `references/bpmn2-element-reference.md`.

**Required namespaces (always include all four):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions
  xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
  xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
  targetNamespace="http://example.com/bpmn"
  id="Definitions_1">
```

**Single-pool collaboration with lanes:**
```xml
<bpmn:collaboration id="Collab_1">
  <bpmn:participant id="Pool_1" name="Process Name" processRef="Process_1"/>
</bpmn:collaboration>

<bpmn:process id="Process_1" isExecutable="false">
  <bpmn:laneSet id="LaneSet_1">
    <bpmn:lane id="Lane_A" name="Role A">
      <bpmn:flowNodeRef>SE_Start</bpmn:flowNodeRef>
      <bpmn:flowNodeRef>T_Task1</bpmn:flowNodeRef>
      <!-- all element IDs in this lane -->
    </bpmn:lane>
    <bpmn:lane id="Lane_B" name="Role B">
      <bpmn:flowNodeRef>T_Task2</bpmn:flowNodeRef>
      <bpmn:flowNodeRef>SE_End</bpmn:flowNodeRef>
    </bpmn:lane>
  </bpmn:laneSet>

  <bpmn:startEvent id="SE_Start" name="Start"><bpmn:outgoing>SF1</bpmn:outgoing></bpmn:startEvent>
  <bpmn:task id="T_Task1" name="Task Name"><bpmn:incoming>SF1</bpmn:incoming><bpmn:outgoing>SF2</bpmn:outgoing></bpmn:task>
  <bpmn:task id="T_Task2" name="Task Name"><bpmn:incoming>SF2</bpmn:incoming><bpmn:outgoing>SF3</bpmn:outgoing></bpmn:task>
  <bpmn:endEvent id="SE_End" name="End"><bpmn:incoming>SF3</bpmn:incoming></bpmn:endEvent>

  <bpmn:sequenceFlow id="SF1" sourceRef="SE_Start" targetRef="T_Task1"/>
  <bpmn:sequenceFlow id="SF2" sourceRef="T_Task1" targetRef="T_Task2"/>
  <bpmn:sequenceFlow id="SF3" sourceRef="T_Task2" targetRef="SE_End"/>
</bpmn:process>
```

**DI (Diagram Interchange) — always include for correct rendering:**
```xml
<bpmndi:BPMNDiagram id="Diagram_1">
  <bpmndi:BPMNPlane id="Plane_1" bpmnElement="Collab_1">
    <!-- Pool boundary -->
    <bpmndi:BPMNShape id="Pool_1_DI" bpmnElement="Pool_1" isHorizontal="true">
      <dc:Bounds x="10" y="80" width="900" height="300"/>
    </bpmndi:BPMNShape>
    <!-- Lane shapes -->
    <bpmndi:BPMNShape id="Lane_A_DI" bpmnElement="Lane_A" isHorizontal="true">
      <dc:Bounds x="40" y="80" width="870" height="150"/>
    </bpmndi:BPMNShape>
    <bpmndi:BPMNShape id="Lane_B_DI" bpmnElement="Lane_B" isHorizontal="true">
      <dc:Bounds x="40" y="230" width="870" height="150"/>
    </bpmndi:BPMNShape>
    <!-- Element shapes -->
    <bpmndi:BPMNShape id="SE_Start_DI" bpmnElement="SE_Start">
      <dc:Bounds x="90" y="137" width="36" height="36"/>
    </bpmndi:BPMNShape>
    <!-- ... -->
    <!-- Sequence flow edges -->
    <bpmndi:BPMNEdge id="SF1_DI" bpmnElement="SF1">
      <di:waypoint x="126" y="155"/>
      <di:waypoint x="186" y="155"/>
    </bpmndi:BPMNEdge>
  </bpmndi:BPMNPlane>
</bpmndi:BPMNDiagram>
```

**DI coordinate conventions:**
- Pool label column: x=10 to x=40 (30px)
- Lane label column: x=40 to x=70 (30px)
- First element starts at x=90
- Horizontal spacing between elements: 150–160px
- Task size: 100×80 · Gateway: 50×50 · Events (start/end): 36×36
- Lane height: 150–180px; y_center = lane_y + lane_h/2
- Element y = y_center - element_h/2
- Edge waypoints: right edge of source → left edge of target at y_center; use 3 waypoints for L-shaped cross-lane flows

**BPMNEdge — always required, always compact:**

Every `sequenceFlow` must have a matching `BPMNEdge`. Without it bpmn.io renders shapes but draws no connecting arrows. Use the minimal 2-waypoint form on **one line**:

```xml
<bpmndi:BPMNEdge id="SF_01_DI" bpmnElement="SF_01"><di:waypoint x="126" y="155"/><di:waypoint x="186" y="155"/></bpmndi:BPMNEdge>
```

For cross-lane flows add a 3rd bend-point waypoint (right edge of source → x_mid at source_y → x_mid at target_y):

```xml
<bpmndi:BPMNEdge id="SF_02_DI" bpmnElement="SF_02"><di:waypoint x="190" y="125"/><di:waypoint x="250" y="125"/><di:waypoint x="250" y="275"/></bpmndi:BPMNEdge>
```

This compresses each edge from ~5 lines to 1 line, reducing DI output by ~80% while keeping all connections visible.

**BPMNShape — compact format:**
```xml
<bpmndi:BPMNShape id="T_1_DI" bpmnElement="T_1"><dc:Bounds x="90" y="107" width="100" height="80"/></bpmndi:BPMNShape>
```

---

## Step 3 — Write the .bpmn file

**Always use the Write tool to save the file. Never print the full XML as part of your text response.**

```
Write tool → file_path: "./{process-name}.bpmn", content: [full XML string]
```

**Self-check before confirming.** If the `bpmn-coach` skill is installed next to this one, run its validator on the file you just wrote:

```bash
python "{skill_dir}/../bpmn-coach/scripts/validate.py" "./{process-name}.bpmn" --format text
```

Fix every ERROR and WARNING it reports (rewrite the file), then run it again. The exit code is 0 when no errors remain. If the validator is not installed, skip this step.

After writing, confirm with a single line:
```
Saved: ./[name].bpmn — [N] tasks/gateways/events, [N] lanes
```

Default output path: `./{process-name}.bpmn` in the current working directory.

**Multiple diagrams:** If more than one diagram is requested, generate and write **one at a time**. Confirm the first file is saved, then proceed to the next. Never generate two diagrams in the same response.

---

## Step 4 — Produce the HTML snippet

**Complexity gate — skip by default for large diagrams:**
- If the diagram has **more than 8 tasks OR more than 4 lanes**: skip the HTML snippet unless the user explicitly asked for it. Confirm the .bpmn file path and offer the snippet on request.
- For small diagrams (≤8 tasks AND ≤4 lanes): produce the snippet as usual.

When generating the HTML snippet, the caller (user or another skill) embeds it in any HTML page.

**In the `<head>` of the page (add once):**
```html
<link rel="stylesheet" href="https://unpkg.com/bpmn-js@18.31.0/dist/assets/diagram-js.css">
<link rel="stylesheet" href="https://unpkg.com/bpmn-js@18.31.0/dist/assets/bpmn-js.css">
<link rel="stylesheet" href="https://unpkg.com/bpmn-js@18.31.0/dist/assets/bpmn-font/css/bpmn.css">
<script src="https://unpkg.com/bpmn-js@18.31.0/dist/bpmn-navigated-viewer.production.min.js"></script>
```

**Diagram card (one per diagram):**
```html
<div style="background:#fff;border:1px solid #e2e8f0;border-radius:6px;overflow:hidden;margin-bottom:24px">
  <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:1px solid #e2e8f0">
    <div>
      <div style="font-family:'Geist Mono',monospace;font-size:11px;font-weight:500;color:#6b7280;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px">PROCESS MODEL</div>
      <div style="font-size:14px;font-weight:600;color:#111827">[Process Title]</div>
    </div>
    <button onclick="downloadBpmn_[id]()"
      style="display:inline-flex;align-items:center;gap:6px;height:28px;padding:0 12px;border:1px solid #d1d5db;border-radius:6px;background:#fff;font-size:12px;font-weight:500;cursor:pointer">
      ↓ Download .bpmn
    </button>
  </div>
  <div id="bpmn-[id]" style="height:420px"></div>
</div>

<script>
const bpmnXML_[id] = `[BPMN 2.0 XML — paste full XML here]`;

(function() {
  const viewer = new BpmnJS({ container: '#bpmn-[id]' });
  viewer.importXML(bpmnXML_[id]).then(function() {
    viewer.get('canvas').zoom('fit-viewport');
  }).catch(function(err) {
    document.getElementById('bpmn-[id]').innerHTML =
      '<div style="padding:24px;color:#6b7280;font-size:13px">Diagram requires internet connection to load bpmn-js viewer. XML is always available via Download.</div>';
  });
})();

function downloadBpmn_[id]() {
  var blob = new Blob([bpmnXML_[id]], { type: 'application/bpmn+xml' });
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'process-[id].bpmn';
  a.click();
  URL.revokeObjectURL(a.href);
}
</script>
```

Replace `[id]` with a slug that is a valid JavaScript identifier (e.g., `purchase_approval`). IDs must be unique per page.

The XML sits inside a JavaScript template literal. Before pasting it, escape every backtick as `` \` `` and every `${` as `\${`, or the page will break.

---

## Bundled templates

See the table in Step 2, Option A. Both templates are checked on every commit: they parse with no warnings in bpmn-moddle (the parser bpmn.io and Camunda Modeler use) and pass the `bpmn-coach` validator with zero findings.

---

## Notes

- **Offline rendering**: If bpmn-js CDN is unavailable, the viewer div shows a message. The XML is always downloadable regardless.
- **Camunda / bpmn.io compatibility**: Generated XML includes DI coordinates so bpmn.io and Camunda Modeler can draw it. The bundled templates are tested against bpmn-moddle; for new diagrams, the self-check in Step 3 catches broken references and missing layout.
- **`isExecutable="false"`**: All generated diagrams are descriptive (not executable). Change to `true` only if feeding into a BPMN engine.
- **Mermaid.js**: Not used. Mermaid cannot produce `.bpmn` files and uses a different notation. bpmn-js renders BPMN 2.0 natively.
- Read `references/bpmn2-element-reference.md` for the full element cheat sheet when generating from natural language descriptions.
