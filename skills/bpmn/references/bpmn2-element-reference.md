# BPMN 2.0 Element Reference
**Quick cheat sheet — natural language → BPMN element**

---

## Events

| Natural language | BPMN element | XML tag | Symbol |
|---|---|---|---|
| "Process starts", "ticket received", "customer calls" | Start Event | `<bpmn:startEvent>` | ○ (thin circle) |
| "Process ends", "done", "resolved", "closed" | End Event | `<bpmn:endEvent>` | ● (thick circle) |
| "Message received", "notification sent" | Message Event | `<bpmn:startEvent>/<bpmn:endEvent>` with `<bpmn:messageEventDefinition>` | ✉ in circle |
| "Wait 24 hours", "timer fires" | Timer Event | `<bpmn:intermediateCatchEvent>` with `<bpmn:timerEventDefinition>` | ⏱ in circle |
| "Error occurred", "exception thrown" | Error Event | with `<bpmn:errorEventDefinition>` | ⚡ in circle |

---

## Activities (Tasks)

| Natural language | BPMN element | XML tag | Notes |
|---|---|---|---|
| "Person does X", "coordinator reviews", "engineer fixes" | User Task | `<bpmn:userTask>` | Human performs action |
| "System does X automatically", "bot processes", "AI classifies" | Service Task | `<bpmn:serviceTask>` | Automated step |
| "General step", "process action" (default) | Task | `<bpmn:task>` | Use when type is unclear |
| "Group of steps", "sub-process" | Sub-Process | `<bpmn:subProcess>` | Collapsed or expanded |
| "Call another process" | Call Activity | `<bpmn:callActivity>` | References another process |

**Task attributes:**
```xml
<bpmn:task id="T_1" name="Display name">
  <bpmn:incoming>SF_in</bpmn:incoming>  <!-- incoming sequence flow ID -->
  <bpmn:outgoing>SF_out</bpmn:outgoing> <!-- outgoing sequence flow ID -->
</bpmn:task>
```

---

## Gateways

| Natural language | BPMN element | XML tag | Symbol | Behavior |
|---|---|---|---|---|
| "If urgent", "decision point", "either/or" | Exclusive Gateway (XOR) | `<bpmn:exclusiveGateway>` | ◇ with X | Only one outgoing path taken |
| "All paths at once", "parallel work" | Parallel Gateway (AND) | `<bpmn:parallelGateway>` | ◇ with + | All outgoing paths taken |
| "One or more paths", "inclusive" | Inclusive Gateway (OR) | `<bpmn:inclusiveGateway>` | ◇ with O | One or more outgoing paths |
| "Merge converging paths" | Gateway (closing) | same tags | | Multiple incoming, one outgoing |

**Exclusive Gateway (decision + merge):**
```xml
<!-- Opening/decision gateway -->
<bpmn:exclusiveGateway id="GW_1" name="Decision?">
  <bpmn:incoming>SF_in</bpmn:incoming>
  <bpmn:outgoing>SF_yes</bpmn:outgoing>
  <bpmn:outgoing>SF_no</bpmn:outgoing>
</bpmn:exclusiveGateway>

<!-- Condition on the outgoing flow -->
<bpmn:sequenceFlow id="SF_yes" name="Yes" sourceRef="GW_1" targetRef="T_Next_Yes"/>
<bpmn:sequenceFlow id="SF_no" name="No" sourceRef="GW_1" targetRef="T_Next_No"/>

<!-- Closing/merge gateway (unnamed) -->
<bpmn:exclusiveGateway id="GW_Merge">
  <bpmn:incoming>SF_yes_done</bpmn:incoming>
  <bpmn:incoming>SF_no_done</bpmn:incoming>
  <bpmn:outgoing>SF_continue</bpmn:outgoing>
</bpmn:exclusiveGateway>
```

---

## Sequence Flows

Connect elements within the **same pool/process**:
```xml
<bpmn:sequenceFlow id="SF1" sourceRef="SE_Start" targetRef="T_Task1"/>
<!-- With label: -->
<bpmn:sequenceFlow id="SF2" name="Urgent" sourceRef="GW_1" targetRef="T_Escalate"/>
```

---

## Pools and Lanes

**Pool** = one organization or participant (one `<bpmn:participant>` + one `<bpmn:process>`).
**Lane** = subdivision of a pool by role (all in one `<bpmn:process>`).

```xml
<!-- Single pool with 2 lanes -->
<bpmn:collaboration id="Collab_1">
  <bpmn:participant id="Pool_1" name="Organization" processRef="Process_1"/>
</bpmn:collaboration>

<bpmn:process id="Process_1" isExecutable="false">
  <bpmn:laneSet id="LaneSet_1">
    <bpmn:lane id="Lane_A" name="Role A">
      <bpmn:flowNodeRef>SE_Start</bpmn:flowNodeRef>
      <bpmn:flowNodeRef>T_Task_A</bpmn:flowNodeRef>
      <!-- list ALL element IDs that belong to this lane -->
    </bpmn:lane>
    <bpmn:lane id="Lane_B" name="Role B">
      <bpmn:flowNodeRef>T_Task_B</bpmn:flowNodeRef>
      <bpmn:flowNodeRef>SE_End</bpmn:flowNodeRef>
    </bpmn:lane>
  </bpmn:laneSet>
  <!-- All tasks, gateways, events at process level regardless of lane -->
  ...
</bpmn:process>
```

Cross-lane handoffs are **sequence flows** (not message flows — same organization).
Message flows are used between **different pools** (different organizations).

---

## DI Coordinate Reference

| Element | Width | Height | y position |
|---|---|---|---|
| Start / End Event | 36 | 36 | `y_center - 18` |
| Task | 100 | 80 | `y_center - 40` |
| Exclusive/Parallel Gateway | 50 | 50 | `y_center - 25` |
| Lane shape | pool_width - 30 | lane_height | lane top y |
| Pool shape | total_width | total_height | 80 (default top) |

**Standard layout values:**
- Pool label column: 30px (x=10 to x=40)
- Lane label column: 30px (x=40 to x=70)
- First element x: 90
- Element horizontal gap: 150–160px
- Lane height: 150–180px
- y_center per lane: `lane_y + lane_h / 2`

**Edge waypoints — 2 points for horizontal flow:**
```xml
<bpmndi:BPMNEdge id="SF1_DI" bpmnElement="SF1">
  <di:waypoint x="[source_right_edge]" y="[source_y_center]"/>
  <di:waypoint x="[target_left_edge]" y="[target_y_center]"/>
</bpmndi:BPMNEdge>
```

**Edge waypoints — 3 points for cross-lane vertical flow:**
```xml
<!-- Going DOWN from Lane A to Lane B, same x -->
<bpmndi:BPMNEdge id="SF_cross_DI" bpmnElement="SF_cross">
  <di:waypoint x="[source_x_center]" y="[source_bottom]"/>
  <di:waypoint x="[source_x_center]" y="[target_top]"/>
</bpmndi:BPMNEdge>

<!-- Going DOWN with horizontal offset (L-shape) -->
<bpmndi:BPMNEdge id="SF_lshape_DI" bpmnElement="SF_lshape">
  <di:waypoint x="[source_x_center]" y="[source_bottom]"/>
  <di:waypoint x="[source_x_center]" y="[midpoint_y]"/>
  <di:waypoint x="[target_x_left]" y="[midpoint_y]"/>
  <di:waypoint x="[target_x_left]" y="[target_top]"/>
</bpmndi:BPMNEdge>
```

---

## Common Patterns

### Happy path
```
startEvent → task → task → endEvent
```

### Decision with two paths
```
startEvent → task → exclusiveGateway → [Yes] task → exclusiveGateway(merge) → task → endEvent
                                      → [No]  task ↗
```

### Escalation across lanes
```
Lane A: task → [cross-lane sequenceFlow ↓]
Lane B:                                    task → gateway → endEvent
                                                           ↓ [cross-lane]
Lane C:                                                       task → endEvent
```

### Three parallel independent processes (same pool, no connections)
```
Lane A: start → task → task → end
Lane B: start → task → task → end
Lane C: start → task → task → end
```
(This is illustrative BPMN — valid with `isExecutable="false"`)
