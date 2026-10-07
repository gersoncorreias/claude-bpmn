---
name: bpmn-to-figjam
description: "Converts .bpmn XML files into high-fidelity FigJam diagrams using the Figma MCP. Use this skill whenever the user mentions 'convert BPMN', 'BPMN to FigJam', 'import BPMN into Figma', 'visualize process model in Figma/FigJam', 'render BPMN in FigJam', or uploads/pastes a .bpmn file and asks to visualize, share, or push it to Figma. Also triggers when the user has a .bpmn file or BPMN XML and wants a shareable diagram in FigJam. Always require a FigJam board URL before proceeding — block and prompt for it if missing."
---

# BPMN to FigJam Converter

Parses a `.bpmn` XML file and renders a high-fidelity diagram into a FigJam board using the Figma MCP. Matches bpmn.io visual conventions as closely as FigJam allows.

---

## Precondition: FigJam URL required

Confirm the user has provided a FigJam board URL. Extract fileKey from:
```
https://www.figma.com/board/{fileKey}/file-name
```
If missing, stop and ask for it before proceeding.

## Precondition: a Figma MCP server that can write

Rendering runs Figma Plugin API JavaScript inside the board through the Figma MCP server's `use_figma` tool, called with the `fileKey` above and the code built in Steps 2–5. If no connected Figma MCP server offers a tool that runs code in a file, stop and tell the user to connect Figma's MCP server. Do not fall back to describing the diagram.

## Never touch existing board content

The board may hold other people's work. The skill **never deletes or moves anything it did not draw**. Every render goes into a new FigJam section named `BPMN: <process name>`, placed to the right of whatever is already on the board (Step 2, before 2a). To redraw a process, first ask the user whether to replace the earlier section with the same name. Remove only that section, and only if they say yes.

---

## Step 1 — Parse the BPMN XML

Read the `.bpmn` file. Extract:

### 1a. Elements by tag

| Tag | Shape type | Default fill | Stroke |
|---|---|---|---|
| `bpmn:startEvent` | ELLIPSE | bioc fill if present, else `#c8e6c9` | bioc stroke if present, else `#205022`, sw=2 |
| `bpmn:endEvent` | ELLIPSE | bioc fill if present, else `#ffcdd2` | bioc stroke if present, else `#831311`, **sw=4** |
| `bpmn:intermediateThrowEvent` | ELLIPSE | bioc fill or `#ffe0b2` | bioc stroke or `#6b3c00`, sw=2 |
| `bpmn:intermediateCatchEvent` | ELLIPSE | bioc fill or `#bbdefb` | bioc stroke or `#0d4372`, sw=2 |
| `bpmn:task`, `bpmn:userTask`, `bpmn:manualTask`, `bpmn:scriptTask`, `bpmn:serviceTask` | ROUNDED_RECTANGLE | bioc fill or **white `#FFFFFF`** | bioc stroke or `#22242a`, sw=2 |
| `bpmn:subProcess` **(collapsed** — no child `bpmn:*` elements in XML**)** | ROUNDED_RECTANGLE | bioc fill or `#f0f4ff` | bioc stroke or `#22242a`, sw=2, **dashPattern=[6,4]** |
| `bpmn:subProcess` **(expanded** — has child `bpmn:*` elements in XML**)** | `createRectangle()` background | bioc fill or `#eef2ff` at opacity 0.6 | bioc stroke or `#22242a`, sw=1.5, **dashPattern=[6,4]** |
| `bpmn:callActivity` | ROUNDED_RECTANGLE | bioc fill or **white `#FFFFFF`** | bioc stroke or `#22242a`, **sw=3** |
| `bpmn:exclusiveGateway` | DIAMOND | bioc fill or **white `#FFFFFF`** | bioc stroke or `#22242a`, sw=2 |
| `bpmn:parallelGateway` | DIAMOND | bioc fill or `#f0e6ff` | bioc stroke or `#22242a`, sw=2 |
| `bpmn:inclusiveGateway` | DIAMOND | bioc fill or `#fff3e0` | bioc stroke or `#22242a`, sw=2 |

**Color resolution priority:**
1. `bioc:fill` / `color:background-color` → hex → `{r, g, b}` (divide by 255)
2. `bioc:stroke` / `color:border-color` → hex → `{r, g, b}`
3. Element type defaults above

**Text inside shapes:**
- Tasks: dark text `{r:0.13,g:0.14,b:0.17}` on white fill; white text `{r:1,g:1,b:1}` if bioc fill is dark
- Events: **no text inside** — use external label (see Step 3b)
- Gateways: **no text inside** for XOR/parallel/inclusive — use `"×"` for XOR (font 18px, dark), `"+"` for parallel, `"○"` for inclusive; use external label

### 1b. DI coordinates — always use these

```xml
<bpmndi:BPMNShape bpmnElement="T_Review">
  <dc:Bounds x="302" y="172" width="100" height="80"/>
</bpmndi:BPMNShape>
```

Extract `x`, `y`, `width`, `height` for every element including pools and lanes. Also extract `<bpmndi:BPMNLabel><dc:Bounds .../>` — the DI label position is where external labels go.

**Subprocess child collection:** When parsing `<bpmn:subProcess>`, recurse into the element body and collect child BPMN elements. Child element DI coordinates appear in the same `<bpmndi:BPMNShape>` / `<bpmndi:BPMNEdge>` sections as all other elements — look them up by child element ID. Store on the subprocess entry:
```
subProcessEntry.childDefs = [...]     // parsed child node defs with full DI coords
subProcessEntry.childFlows = [...]    // parsed child sequence flow defs
subProcessEntry.isExpanded = childDefs.length > 0
```
Child BPMN elements to detect: `bpmn:task`, `bpmn:userTask`, `bpmn:serviceTask`, `bpmn:scriptTask`, `bpmn:manualTask`, `bpmn:startEvent`, `bpmn:endEvent`, `bpmn:exclusiveGateway`, `bpmn:parallelGateway`, `bpmn:inclusiveGateway`, `bpmn:intermediateThrowEvent`, `bpmn:intermediateCatchEvent`, `bpmn:subProcess`.

### 1c. Flows

- `bpmn:sequenceFlow`: id, sourceRef, targetRef, name (condition label)
- `bpmn:messageFlow`: id, sourceRef, targetRef, name (dashed purple)

---

## Step 2 — Build the layer stack (append in this order)

Order matters: append backgrounds first → they sit below shapes and connectors.

### Prepare the board: fonts and the section

Run this first, before any shape or text is created:

```javascript
// Load fonts before any text operation. FigJam shapes and connectors use Inter Medium by default.
await figma.loadFontAsync({family: "Inter", style: "Regular"});
await figma.loadFontAsync({family: "Inter", style: "Medium"});

const page = figma.currentPage;
const SECTION_NAME = "BPMN: " + PROCESS_NAME;

// Only when the user agreed to replace an earlier render of the same process.
if (REPLACE_PREVIOUS) {
  for (const n of page.children.filter(n => n.type === "SECTION" && n.name === SECTION_NAME)) n.remove();
}

// Place the new section to the right of everything already on the board.
const PAD = 80;
const right = page.children.reduce((m, n) => Math.max(m, n.x + n.width), -Infinity);
const root = figma.createSection();
root.name = SECTION_NAME;
root.x = Number.isFinite(right) ? right + 200 : 0;
root.y = 0;
root.resizeWithoutConstraints(DIAGRAM_W + 2 * PAD, DIAGRAM_H + 2 * PAD);
```

`DIAGRAM_W`, `DIAGRAM_H`, `MIN_X` and `MIN_Y` come from the bounding box of all DI shapes (pools included). Every node below is appended to `root`, not to the page. Translate every DI coordinate into the section first: `x = DI_x - MIN_X + PAD`, `y = DI_y - MIN_Y + PAD`. The snippets below assume the coordinates are already translated.

### 2a. Pool backgrounds

For each pool (DI bounds: x, y, w, h):

```javascript
// Pool background — full bioc fill
const poolBg = figma.createRectangle();
poolBg.x = POOL_X; poolBg.y = POOL_Y;
poolBg.resize(POOL_W, POOL_H);
poolBg.fills  = [{type:'SOLID', color: POOL_FILL, opacity: 0.90}];
poolBg.strokes= [{type:'SOLID', color: POOL_STROKE}];
poolBg.strokeWeight = 1.5;
root.appendChild(poolBg);  // append → bottom layer

// Pool divider line at x = POOL_X + 30 (separates 30px label strip from content)
const poolDiv = figma.createRectangle();
poolDiv.x = POOL_X + 30; poolDiv.y = POOL_Y;
poolDiv.resize(1, POOL_H);  // 1px wide = visual line
poolDiv.fills  = [{type:'SOLID', color: POOL_STROKE}];
poolDiv.strokes= [];
root.appendChild(poolDiv);

// Pool name label (rotated -90°, centered in the 30px strip)
addVLabel(POOL_NAME, POOL_X + 15, POOL_Y + POOL_H/2, 11, POOL_STROKE);
```

### 2b. Lane backgrounds

For each lane (DI bounds: lx, ly, lw, lh):

```javascript
// Lane background (semi-transparent white over pool fill)
const laneBg = figma.createRectangle();
laneBg.x = lx; laneBg.y = ly; laneBg.resize(lw, lh);
laneBg.fills  = [{type:'SOLID', color:{r:1,g:1,b:1}, opacity: 0.25}];
laneBg.strokes= [{type:'SOLID', color:{r:0.13,g:0.14,b:0.17}}];
laneBg.strokeWeight = 1.5;
root.appendChild(laneBg);

// Lane 30px strip divider at lx + 30
const laneDiv = figma.createRectangle();
laneDiv.x = lx + 30; laneDiv.y = ly;
laneDiv.resize(1, lh);
laneDiv.fills = [{type:'SOLID', color:{r:0.13,g:0.14,b:0.17}}];
laneDiv.strokes = [];
root.appendChild(laneDiv);

// Lane label rotated
addVLabel(LANE_NAME, lx + 15, ly + lh/2, 11, {r:0.13,g:0.14,b:0.17});
```

### 2c. Expanded subprocess backgrounds

For each `bpmn:subProcess` where `isExpanded === true`. **Must be appended before child shapes** so the background sits below them in the layer stack.

```javascript
// Expanded subprocess container
const spBg = figma.createRectangle();
spBg.x = sp.x; spBg.y = sp.y;
spBg.resize(sp.w, sp.h);
spBg.fills  = [{type:'SOLID', color:{r:0.933,g:0.945,b:1.0}, opacity:0.6}];
// resolve bioc colors if present, else use defaults above
spBg.strokes = [{type:'SOLID', color:{r:0.13,g:0.14,b:0.17}}];
spBg.strokeWeight = 1.5;
spBg.dashPattern = [6, 4];
root.appendChild(spBg);  // appended first → sits below child shapes

// Subprocess label at top-left (matches bpmn.io convention)
const spLabel = figma.createText();
spLabel.fontName = {family:"Inter", style:"Regular"};
spLabel.characters = sp.name;
spLabel.fontSize = 11;
spLabel.fills = [{type:'SOLID', color:{r:0.13,g:0.14,b:0.17}}];
spLabel.x = sp.x + 8;
spLabel.y = sp.y + 6;
root.appendChild(spLabel);

// Register background rect in nodeMap so boundary connectors wire to it
nodeMap[sp.id] = spBg;
// Mark as rendered — skip this subProcess in the main shape loop
subProcessEntry.bgAppended = true;
```

**Layer order (append sequence matters):**
1. Pool backgrounds (Step 2a)
2. Lane backgrounds (Step 2b)
3. Expanded subprocess backgrounds + labels ← this step
4. Regular shapes — tasks, events, gateways, collapsed subprocesses (Step 3)
5. Connectors (Step 4)

### 2d. Rotated label helper

```javascript
function addVLabel(str, cx, cy, fontSize, color) {
  const t = figma.createText();
  t.fontName = {family:"Inter", style:"Regular"};
  t.characters = str;
  t.fontSize = fontSize;
  t.fills = [{type:'SOLID', color}];
  // Position center BEFORE rotation — rotation is around center
  t.x = cx - t.width/2;
  t.y = cy - t.height/2;
  t.rotation = 90;  // clockwise = bottom-to-top = BPMN standard
  root.appendChild(t);
}
```

---

## Step 3 — Nodes

### 3a. Shape creation

```javascript
for (const node of NODE_DEFS) {
  const shape = figma.createShapeWithText();
  shape.shapeType = node.shapeType;
  shape.x = node.x; shape.y = node.y;
  shape.resize(node.w, node.h);
  shape.fills  = [{type:'SOLID', color: node.fill}];
  shape.strokes= [{type:'SOLID', color: node.stroke}];
  shape.strokeWeight = node.sw;
  shape.text.characters = node.name;  // "" for events; "×"/"+" for gateways
  shape.text.fontSize   = node.fs;
  shape.text.fills = [{type:'SOLID', color: node.textColor}];
  nodeMap[node.id] = shape;
  root.appendChild(shape);
}
```

**Events — DI size 36×36 → render as 46×46 centered on DI center:**
```
DI element center = (DI_x + DI_w/2, DI_y + DI_h/2)
FigJam shape: x = center_x - 23, y = center_y - 23, w = 46, h = 46
```

**End event** must have `strokeWeight = 4` (the thick border IS the end-event BPMN marker).

### 3b. External labels (events and gateways)

Use the `<bpmndi:BPMNLabel><dc:Bounds>` position from DI. If no DI label, place below events and above gateways.

```javascript
function addExtLabel(str, x, y, fontSize, color) {
  const t = figma.createText();
  t.fontName = {family:"Inter", style:"Regular"};
  t.characters = str;
  t.fontSize = fontSize || 11;
  t.fills = [{type:'SOLID', color}];
  t.x = x; t.y = y;
  root.appendChild(t);
}
// Event label: use DI label x, y directly
// Gateway label: use DI label x, y directly
```

### 3c. Subprocess and callActivity rendering

**Decision tree — applied in the main shape loop:**

```
bpmn:subProcess
  ├── bgAppended (isExpanded === true)
  │     → SKIP in shape loop (background already created in Step 2c)
  │     → process childDefs through the same createShapeWithText() loop
  │     → process childFlows through the connector loop (Step 4)
  │     → register all child elements in nodeMap
  └── collapsed (isExpanded === false)
        → create ROUNDED_RECTANGLE, fill=#f0f4ff, sw=2, dashPattern=[6,4]
        → register in nodeMap
        → call addPlusMarker(shape)

bpmn:callActivity
  → create ROUNDED_RECTANGLE, fill=#FFFFFF, sw=3
  → register in nodeMap
  → call addPlusMarker(shape)
```

**Plus marker helper** — add after the `wrap()` helper below:

```javascript
function addPlusMarker(parentShape) {
  // 14×14 "+" badge centered at the bottom edge of parentShape
  const mW = 14, mH = 14;
  const marker = figma.createShapeWithText();
  marker.shapeType = 'ROUNDED_RECTANGLE';
  marker.x = parentShape.x + (parentShape.width / 2) - (mW / 2);
  marker.y = parentShape.y + parentShape.height - mH - 2;
  marker.resize(mW, mH);
  marker.fills   = [{type:'SOLID', color:{r:1,g:1,b:1}}];
  marker.strokes = [{type:'SOLID', color:{r:0.13,g:0.14,b:0.17}}];
  marker.strokeWeight = 1;
  marker.text.characters = '+';
  marker.text.fontSize   = 10;
  marker.text.fills = [{type:'SOLID', color:{r:0.13,g:0.14,b:0.17}}];
  root.appendChild(marker);
  // Do NOT add marker to nodeMap — no BPMN ID, connectors never attach here
}
```

### 3d. Task text pre-wrapping

FigJam shapes have internal padding (~10px per side). At 9px font in a 100px wide task:
- Effective text width ≈ 80px → ~15 chars per line
- At 8px → ~17 chars per line

Pre-wrap before setting characters to prevent overflow:

```javascript
function wrap(str, maxChars) {
  const words = str.split(' ');
  const lines = [];
  let cur = '';
  for (const w of words) {
    const test = cur ? cur + ' ' + w : w;
    if (test.length <= maxChars) cur = test;
    else { if (cur) lines.push(cur); cur = w; }
  }
  if (cur) lines.push(cur);
  return lines.join('\n');
}
// Usage: wrap("Check documents and confirm identity", 15)
```

Font size guidance for 100×80 tasks:
- ≤20 chars: 12px
- 21–35 chars: 10px
- 36–50 chars: 9px
- >50 chars: 8px

---

## Step 4 — Connectors

```javascript
for (const flow of FLOW_DEFS) {
  const src = nodeMap[flow.s], tgt = nodeMap[flow.t];
  if (!src || !tgt) continue;
  const conn = figma.createConnector();
  conn.connectorStart = {endpointNodeId: src.id, magnet: flow.sm || 'AUTO'};
  conn.connectorEnd   = {endpointNodeId: tgt.id, magnet: flow.em || 'AUTO'};
  conn.strokes = [{type:'SOLID', color:{r:0.13,g:0.14,b:0.17}}];
  conn.strokeWeight = 1.5;
  if (flow.lbl) {
    try {
      conn.text.characters = flow.lbl;
      conn.text.fontSize = 10;
    } catch(e) {}
  }
  root.appendChild(conn);
}
```

**Loop-back connectors** (flow goes from right to left — target.x < source.x):
```javascript
// Use BOTTOM magnets to route below the swimlane
{s:"GW_MoreItems", t:"T_PickItem", lbl:"Yes", sm:'BOTTOM', em:'BOTTOM'}
```

**Message flows** — dashed purple:
```javascript
conn.dashPattern = [8, 4];
conn.strokes = [{type:'SOLID', color:{r:0.5,g:0.3,b:0.8}}];
```

---

## Step 5 — Viewport and report

```javascript
figma.viewport.scrollAndZoomIntoView([root]);
return "ok: N shapes, N connectors, N total nodes";
```

Always wrap the entire code in `(async () => { try { ... return "ok: ..."; } catch(e) { return "ERROR: "+e.message; } })()` — never use `.catch(console.error)` as it swallows errors silently.

**Report after rendering:**
```
Rendered: [Process name]
  Tasks: N | Gateways: N | Events: N (Start: N, End: N)
  Flows: N (Sequence: N, Message: N)
  Lanes: N | Pools: N
  Subprocesses: N (Expanded: N, Collapsed: N) | CallActivities: N
  Colors: bioc-preserved where present; bpmn.io defaults otherwise
  Placed in section: BPMN: [Process name] (existing board content untouched)
```

---

## Edge cases

- **No DI section** → compute BFS layout: depth × 240px column step, lane y-band center
- **bioc colors present** → always use them, never override
- **Loop-back connectors** → set `sm:'BOTTOM', em:'BOTTOM'` to route below the pool area
- **Overlapping labels** → offset by ±15px in y from DI label position
- **Large diagrams (>50 nodes)** → note in report; suggest user group in FigJam
- **Existing content on the board** → never remove or move it. Draw inside a new section to its right (see "Prepare the board"). Replace an earlier `BPMN: <process name>` section only after the user confirms
- **Expanded subprocess with missing child DI bounds** → treat as collapsed (set `isExpanded = false`); note in report: "N subprocess(es) rendered as collapsed (child DI missing)"
- **Nested expanded subprocesses** → supported one level deep only; a subprocess inside an expanded subprocess is always rendered as collapsed to avoid recursive background stacking
