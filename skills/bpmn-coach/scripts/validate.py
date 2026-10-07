#!/usr/bin/env python3
"""
Validate a BPMN 2.0 file against the bpmn-coach ruleset.

Standard library only. Deterministic: the same file always gives the same
findings. Judgement calls (is this task name a verb phrase? how should a
finding be worded for a business reader?) are left to the skill.

Usage:
    python validate.py diagram.bpmn                 JSON report on stdout
    python validate.py diagram.bpmn --format text   one line per finding
    python validate.py - < diagram.bpmn             read from stdin
    python validate.py --rules                      list every rule

Exit codes: 0 no errors · 1 at least one ERROR finding · 2 file could not be parsed
"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET

__version__ = "1.0.0"

BPMN = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI = "http://www.omg.org/spec/BPMN/20100524/DI"
DC = "http://www.omg.org/spec/DD/20100524/DC"

ERROR, WARNING, INFO = "ERROR", "WARNING", "INFO"

# Single source of truth for rule IDs and severities. references/bpmn-validation-rules.md
# documents the same set; tests/test_rules_doc.py keeps the two in sync.
RULES = {
    "STR-001": (ERROR, "Process has no start event"),
    "STR-002": (ERROR, "Process has no end event"),
    "STR-003": (ERROR, "Flow points to an element that does not exist"),
    "STR-004": (ERROR, "Lane lists an element that does not exist"),
    "STR-005": (ERROR, "Element cannot be reached from a start event"),
    "STR-006": (ERROR, "Path stops before reaching an end event"),
    "STR-007": (ERROR, "Element is not in any lane"),
    "STR-008": (WARNING, "Element is in more than one lane"),
    "GW-001": (WARNING, "Gateway both merges and splits"),
    "GW-002": (ERROR, "Gateway has one way in and one way out"),
    "GW-003": (WARNING, "Decision has an unlabelled outgoing path"),
    "GW-004": (WARNING, "Parallel split is never joined"),
    "GW-005": (WARNING, "Inclusive gateway with only two paths"),
    "GW-006": (INFO, "Decision is not phrased as a question"),
    "EVT-001": (ERROR, "Start event has incoming flow"),
    "EVT-002": (ERROR, "End event has outgoing flow"),
    "EVT-003": (ERROR, "Boundary event is not attached to an activity"),
    "EVT-004": (WARNING, "Intermediate catch event has no trigger"),
    "EVT-005": (WARNING, "Several untyped start events"),
    "SF-001": (ERROR, "Sequence flow crosses a pool or sub-process boundary"),
    "SF-002": (ERROR, "Sequence flow has no id"),
    "SF-003": (WARNING, "Loop with no way out"),
    "SF-004": (WARNING, "Message flow inside a single pool"),
    "LP-001": (WARNING, "Pool points to a process that does not exist"),
    "LP-002": (INFO, "Pool has a single lane"),
    "NM-001": (WARNING, "Activity has no name"),
    "NM-004": (INFO, "Start or end event has no name"),
    "DI-001": (WARNING, "Element has no shape in the layout"),
    "DI-002": (WARNING, "Flow has no line in the layout"),
    "DI-003": (WARNING, "Layout shape refers to a missing element"),
    "DI-004": (INFO, "Two shapes sit exactly on top of each other"),
    "DI-005": (INFO, "Shape extends outside its pool"),
}

# Rules the script does not run because they need judgement. The skill applies them.
JUDGEMENT_RULES = {
    "NM-002": (WARNING, "Task name has no verb"),
}

EVENTS = {"startEvent", "endEvent", "intermediateCatchEvent", "intermediateThrowEvent", "boundaryEvent"}
GATEWAYS = {"exclusiveGateway", "parallelGateway", "inclusiveGateway", "eventBasedGateway", "complexGateway"}
SUBPROCESSES = {"subProcess", "transaction", "adHocSubProcess"}
ACTIVITIES = {
    "task", "userTask", "serviceTask", "sendTask", "receiveTask", "manualTask", "scriptTask",
    "businessRuleTask", "callActivity",
} | SUBPROCESSES
FLOW_NODES = EVENTS | GATEWAYS | ACTIVITIES
DECISIONS = {"exclusiveGateway", "inclusiveGateway", "complexGateway"}


def local(tag):
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def is_bpmn(el, name):
    return el.tag == "{%s}%s" % (BPMN, name)


class Node:
    def __init__(self, el, scope):
        self.el = el
        self.id = el.get("id")
        self.type = local(el.tag)
        self.name = (el.get("name") or "").strip() or None
        self.scope = scope
        self.incoming = []   # sequence flows
        self.outgoing = []

    def event_definitions(self):
        return [local(c.tag) for c in self.el if local(c.tag).endswith("EventDefinition")]


class Scope:
    """A process or an expanded sub-process: the space a sequence flow lives in."""

    def __init__(self, el, kind, process_id, parent=None, owner=None):
        self.el = el
        self.kind = kind
        self.process_id = process_id
        self.parent = parent
        self.owner = owner        # the sub-process Node that contains this scope
        self.nodes = {}
        self.flows = []


class Model:
    def __init__(self, root):
        self.root = root
        self.scopes = []
        self.nodes = {}           # every flow node in the document
        self.processes = {}       # id -> process element
        self.participants = {}    # id -> {name, processRef}
        self.process_pool = {}    # process id -> participant id
        self.lanes = {}           # process id -> list of lane dicts
        self.message_flows = []
        self.semantic_ids = set()
        self.shapes = {}          # bpmnElement -> (x, y, w, h)
        self.edges = set()
        self.has_diagram = False
        self.flow_ids_without_id = 0
        self._build()

    # -- building ---------------------------------------------------------

    def _build(self):
        for el in self.root.iter():
            if el.get("id") and not el.tag.startswith("{%s}" % BPMNDI):
                self.semantic_ids.add(el.get("id"))

        for child in self.root:
            if is_bpmn(child, "process"):
                pid = child.get("id")
                self.processes[pid] = child
                self._build_scope(child, "process", pid, None, None)
                self.lanes[pid] = self._collect_lanes(child)
            elif is_bpmn(child, "collaboration"):
                for c in child:
                    if is_bpmn(c, "participant"):
                        self.participants[c.get("id")] = {
                            "name": (c.get("name") or "").strip() or None,
                            "processRef": c.get("processRef"),
                        }
                        if c.get("processRef"):
                            self.process_pool[c.get("processRef")] = c.get("id")
                    elif is_bpmn(c, "messageFlow"):
                        self.message_flows.append(c)

        for diagram in self.root.iter("{%s}BPMNDiagram" % BPMNDI):
            self.has_diagram = True
            for shape in diagram.iter("{%s}BPMNShape" % BPMNDI):
                b = shape.find("{%s}Bounds" % DC)
                if b is not None:
                    try:
                        bounds = tuple(float(b.get(k, "0")) for k in ("x", "y", "width", "height"))
                    except ValueError:
                        bounds = None
                    self.shapes.setdefault(shape.get("bpmnElement"), bounds)
                else:
                    self.shapes.setdefault(shape.get("bpmnElement"), None)
            for edge in diagram.iter("{%s}BPMNEdge" % BPMNDI):
                self.edges.add(edge.get("bpmnElement"))

    def _build_scope(self, el, kind, pid, parent, owner):
        scope = Scope(el, kind, pid, parent, owner)
        self.scopes.append(scope)
        for child in el:
            t = local(child.tag)
            if not child.tag.startswith("{%s}" % BPMN):
                continue
            if t in FLOW_NODES:
                node = Node(child, scope)
                if node.id:
                    scope.nodes[node.id] = node
                    self.nodes[node.id] = node
                if t in SUBPROCESSES and any(local(g.tag) in FLOW_NODES for g in child):
                    self._build_scope(child, "subProcess", pid, scope, node)
            elif t == "sequenceFlow":
                scope.flows.append(child)
        return scope

    def _collect_lanes(self, process):
        lanes = []

        def walk(lane_set, depth):
            for lane in lane_set:
                if not is_bpmn(lane, "lane"):
                    continue
                child_set = lane.find("{%s}childLaneSet" % BPMN)
                entry = {
                    "id": lane.get("id"),
                    "name": (lane.get("name") or "").strip() or None,
                    "refs": [(r.text or "").strip() for r in lane.findall("{%s}flowNodeRef" % BPMN)],
                    "leaf": child_set is None or not any(is_bpmn(c, "lane") for c in child_set),
                    "depth": depth,
                }
                lanes.append(entry)
                if child_set is not None:
                    walk(child_set, depth + 1)

        for lane_set in process.findall("{%s}laneSet" % BPMN):
            walk(lane_set, 0)
        return lanes

    # -- lookups ----------------------------------------------------------

    def top_level_id(self, node):
        """The process-level element that contains this node (the node itself at top level)."""
        while node.scope.owner is not None:
            node = node.scope.owner
        return node.id

    def lane_of(self, node):
        top = self.top_level_id(node)
        leaf = [l for l in self.lanes.get(node.scope.process_id, []) if l["leaf"] and top in l["refs"]]
        return leaf[0]["name"] if leaf else None

    def pool_of_process(self, pid):
        part = self.process_pool.get(pid)
        if part and self.participants[part]["name"]:
            return self.participants[part]["name"]
        proc = self.processes.get(pid)
        return (proc.get("name") or None) if proc is not None else None

    def pool_id_of(self, ref):
        if ref in self.participants:
            return ref
        node = self.nodes.get(ref)
        if node is not None:
            return self.process_pool.get(node.scope.process_id, "process:" + node.scope.process_id)
        return None


class Validator:
    def __init__(self, model):
        self.m = model
        self.findings = []

    def add(self, rule, node=None, message="", element_id=None, element_name=None, element_type=None,
            lane=None, pool=None):
        severity = RULES[rule][0]
        if node is not None:
            element_id = node.id
            element_name = node.name
            element_type = node.type
            lane = self.m.lane_of(node)
            pool = self.m.pool_of_process(node.scope.process_id)
        finding = {
            "rule": rule,
            "severity": severity,
            "title": RULES[rule][1],
            "element_id": element_id,
            "element_name": element_name,
            "element_type": element_type,
            "lane": lane,
            "pool": pool,
            "message": message,
        }
        if node is not None:
            finding["before"] = [self._label(f.get("sourceRef")) for f in node.incoming]
            finding["after"] = [self._label(f.get("targetRef")) for f in node.outgoing]
        self.findings.append(finding)

    def _label(self, ref):
        n = self.m.nodes.get(ref)
        if n is None:
            return ref
        return n.name or "(unnamed %s)" % n.type

    # -- run --------------------------------------------------------------

    def run(self):
        self.wire_flows()
        for scope in self.m.scopes:
            self.check_scope(scope)
        self.check_lanes()
        self.check_events()
        self.check_gateways()
        self.check_message_flows()
        self.check_pools()
        self.check_names()
        self.check_layout()
        order = {ERROR: 0, WARNING: 1, INFO: 2}
        self.findings.sort(key=lambda f: (order[f["severity"]], f["rule"], f["element_id"] or ""))
        return self.findings

    def wire_flows(self):
        for scope in self.m.scopes:
            for flow in scope.flows:
                fid = flow.get("id")
                if not fid:
                    self.add("SF-002", message="A sequence flow from %s to %s has no id." % (
                        flow.get("sourceRef"), flow.get("targetRef")),
                        pool=self.m.pool_of_process(scope.process_id))
                broken = False
                for attr in ("sourceRef", "targetRef"):
                    ref = flow.get(attr)
                    if ref in scope.nodes:
                        continue
                    broken = True
                    if ref and ref in self.m.nodes:
                        self.add("SF-001", element_id=fid, element_type="sequenceFlow",
                                 pool=self.m.pool_of_process(scope.process_id),
                                 message="Sequence flow %s connects %s, which sits in a different pool or "
                                         "sub-process. Use a message flow between pools." % (fid, ref))
                    else:
                        self.add("STR-003", element_id=fid, element_type="sequenceFlow",
                                 pool=self.m.pool_of_process(scope.process_id),
                                 message="Sequence flow %s has %s=%r, which is not an element in this process."
                                         % (fid, attr, ref))
                if not broken:
                    scope.nodes[flow.get("sourceRef")].outgoing.append(flow)
                    scope.nodes[flow.get("targetRef")].incoming.append(flow)

    # -- graph helpers ----------------------------------------------------

    @staticmethod
    def adjacency(scope, with_boundary):
        adj = {nid: [] for nid in scope.nodes}
        for node in scope.nodes.values():
            for f in node.outgoing:
                adj[node.id].append(f.get("targetRef"))
        # Link events jump from a throw to the catch with the same name.
        catches = {}
        for node in scope.nodes.values():
            for d in node.el:
                if local(d.tag) == "linkEventDefinition" and node.type == "intermediateCatchEvent":
                    catches.setdefault(d.get("name"), []).append(node.id)
        for node in scope.nodes.values():
            for d in node.el:
                if local(d.tag) == "linkEventDefinition" and node.type == "intermediateThrowEvent":
                    adj[node.id].extend(catches.get(d.get("name"), []))
        if with_boundary:
            for node in scope.nodes.values():
                host = node.el.get("attachedToRef")
                if node.type == "boundaryEvent" and host in adj:
                    adj[host].append(node.id)
        return adj

    @staticmethod
    def bfs(starts, adj):
        seen = set(starts)
        queue = list(starts)
        while queue:
            n = queue.pop()
            for m in adj.get(n, ()):
                if m not in seen:
                    seen.add(m)
                    queue.append(m)
        return seen

    @staticmethod
    def detached(node):
        """Nodes that start or end on their own: event sub-processes and compensation handlers."""
        return node.el.get("triggeredByEvent") == "true" or node.el.get("isForCompensation") == "true"

    # -- rules ------------------------------------------------------------

    def check_scope(self, scope):
        nodes = scope.nodes
        starts = [n for n in nodes.values() if n.type == "startEvent"]
        ends = [n for n in nodes.values() if n.type == "endEvent"]
        pool = self.m.pool_of_process(scope.process_id)
        where = "process" if scope.kind == "process" else "sub-process %s" % (scope.owner.name or scope.owner.id)

        if scope.kind == "process" and nodes:
            if not starts:
                self.add("STR-001", element_id=scope.process_id, element_type="process", pool=pool,
                         message="The %s has no start event." % where)
            if not ends:
                self.add("STR-002", element_id=scope.process_id, element_type="process", pool=pool,
                         message="The %s has no end event." % where)

        reach_adj = self.adjacency(scope, with_boundary=True)
        flow_adj = self.adjacency(scope, with_boundary=False)
        reverse = {nid: [] for nid in nodes}
        for src, targets in flow_adj.items():
            for t in targets:
                reverse[t].append(src)

        detached = [n.id for n in nodes.values() if self.detached(n)]
        if starts:
            roots = [n.id for n in starts]
        else:
            roots = [n.id for n in nodes.values()
                     if not n.incoming and n.type != "boundaryEvent" and not any(n.id in v for v in flow_adj.values())]
        reachable = self.bfs(roots + detached, reach_adj)

        if ends:
            sinks = [n.id for n in ends]
        else:
            sinks = [nid for nid, out in flow_adj.items() if not out and nodes[nid].type != "boundaryEvent"]
        coreachable = self.bfs(sinks + detached, reverse)

        for node in nodes.values():
            if node.id not in reachable:
                host = nodes.get(node.el.get("attachedToRef") or "")
                if node.type == "boundaryEvent" and host is not None and host.id not in reachable:
                    continue
                self.add("STR-005", node, "No path leads to this element from a start event of the %s." % where)
            elif node.id not in coreachable and not flow_adj[node.id] and not self.detached(node):
                # Report the dead end itself, not every step upstream of it. Steps that do have
                # outgoing flows but still never reach an end are caught by SF-003 (a loop with no
                # way out) or STR-003 (a broken flow, which leaves its source with no outgoing).
                self.add("STR-006", node, "This element has no outgoing flow, so the %s stops here without "
                                          "reaching an end event." % where)

        # Parallel splits that never join again.
        for node in nodes.values():
            if node.type == "parallelGateway" and len(node.outgoing) >= 2:
                joins = None
                for f in node.outgoing:
                    seen = self.bfs([f.get("targetRef")], flow_adj)
                    found = {nid for nid in seen if nodes[nid].type == "parallelGateway"
                             and len(nodes[nid].incoming) >= 2 and nid != node.id}
                    joins = found if joins is None else joins & found
                if not joins:
                    self.add("GW-004", node, "The %d parallel branches never meet at a parallel join."
                             % len(node.outgoing))

        # Loops that nothing can leave.
        for scc in self.strongly_connected(reach_adj):
            members = set(scc)
            if len(members) == 1:
                only = scc[0]
                if only not in reach_adj[only]:
                    continue
            exits = any(t not in members for n in members for t in reach_adj[n])
            if not exits:
                first = nodes[sorted(members)[0]]
                names = sorted(self._label(n) for n in members)
                self.add("SF-003", first, "These steps form a loop with no way out: %s." % ", ".join(names))

    @staticmethod
    def strongly_connected(adj):
        index, low, on_stack, stack, out = {}, {}, set(), [], []
        counter = [0]

        def visit(v):
            index[v] = low[v] = counter[0]
            counter[0] += 1
            stack.append(v)
            on_stack.add(v)
            for w in adj.get(v, ()):
                if w not in index:
                    visit(w)
                    low[v] = min(low[v], low[w])
                elif w in on_stack:
                    low[v] = min(low[v], index[w])
            if low[v] == index[v]:
                comp = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    comp.append(w)
                    if w == v:
                        break
                out.append(comp)

        limit = sys.getrecursionlimit()
        sys.setrecursionlimit(max(limit, 10000))
        try:
            for v in sorted(adj):
                if v not in index:
                    visit(v)
        finally:
            sys.setrecursionlimit(limit)
        return out

    def check_lanes(self):
        for pid, lanes in self.m.lanes.items():
            if not lanes:
                continue
            scope = next(s for s in self.m.scopes if s.kind == "process" and s.process_id == pid)
            pool = self.m.pool_of_process(pid)
            for lane in lanes:
                for ref in lane["refs"]:
                    if ref not in scope.nodes:
                        self.add("STR-004", element_id=lane["id"], element_name=lane["name"], element_type="lane",
                                 lane=lane["name"], pool=pool,
                                 message="Lane %r lists %r, which is not an element of this process."
                                         % (lane["name"] or lane["id"], ref))
            for node in scope.nodes.values():
                homes = [l for l in lanes if l["leaf"] and node.id in l["refs"]]
                if not homes:
                    self.add("STR-007", node, "This element is not assigned to any lane.")
                elif len(homes) > 1:
                    self.add("STR-008", node, "This element is listed in %d lanes: %s." % (
                        len(homes), ", ".join(l["name"] or l["id"] for l in homes)))

    def check_events(self):
        for scope in self.m.scopes:
            starts = []
            for node in scope.nodes.values():
                if node.type == "startEvent":
                    starts.append(node)
                    if node.incoming:
                        self.add("EVT-001", node, "A start event has %d incoming flow(s)." % len(node.incoming))
                elif node.type == "endEvent":
                    if node.outgoing:
                        self.add("EVT-002", node, "An end event has %d outgoing flow(s)." % len(node.outgoing))
                elif node.type == "boundaryEvent":
                    host = node.el.get("attachedToRef")
                    target = scope.nodes.get(host or "")
                    if target is None or target.type not in ACTIVITIES:
                        self.add("EVT-003", node, "attachedToRef=%r is not an activity in this process." % host)
                elif node.type == "intermediateCatchEvent":
                    if not node.event_definitions():
                        self.add("EVT-004", node, "This catch event does not say what it waits for "
                                                  "(message, timer, signal, ...).")
            untyped = [s for s in starts if not s.event_definitions()]
            if len(untyped) > 1:
                for s in untyped[1:]:
                    self.add("EVT-005", s, "%d start events have no trigger, so it is unclear which one "
                                           "starts the process." % len(untyped))

    def check_gateways(self):
        for node in self.m.nodes.values():
            if node.type not in GATEWAYS:
                continue
            n_in, n_out = len(node.incoming), len(node.outgoing)
            if n_in >= 2 and n_out >= 2:
                self.add("GW-001", node, "This gateway has %d incoming and %d outgoing flows." % (n_in, n_out))
            if n_in <= 1 and n_out <= 1:
                self.add("GW-002", node, "This gateway has %d incoming and %d outgoing flow(s), so it decides "
                                         "nothing." % (n_in, n_out))
            if node.type in DECISIONS and n_out >= 2:
                unlabelled = [f.get("id") for f in node.outgoing if not (f.get("name") or "").strip()]
                if unlabelled:
                    self.add("GW-003", node, "%d of %d outgoing paths have no condition label (%s)." % (
                        len(unlabelled), n_out, ", ".join(x or "?" for x in unlabelled)))
                if not node.name or not node.name.rstrip().endswith("?"):
                    self.add("GW-006", node, "Name decisions as a question, e.g. 'Approved?'.")
            if node.type == "inclusiveGateway" and n_out == 2:
                self.add("GW-005", node, "An inclusive gateway with two paths is usually an exclusive choice.")

    def check_message_flows(self):
        for mf in self.m.message_flows:
            src, tgt = mf.get("sourceRef"), mf.get("targetRef")
            missing = [r for r in (src, tgt) if r not in self.m.semantic_ids]
            if missing:
                self.add("STR-003", element_id=mf.get("id"), element_name=mf.get("name"), element_type="messageFlow",
                         message="Message flow %s points to %s, which does not exist." % (
                             mf.get("id"), ", ".join(map(repr, missing))))
                continue
            a, b = self.m.pool_id_of(src), self.m.pool_id_of(tgt)
            if a is not None and a == b:
                self.add("SF-004", element_id=mf.get("id"), element_name=mf.get("name"), element_type="messageFlow",
                         pool=self.m.participants.get(a, {}).get("name"),
                         message="Message flow %s connects two elements in the same pool; use a sequence flow."
                                 % mf.get("id"))

    def check_pools(self):
        for pid, p in self.m.participants.items():
            ref = p["processRef"]
            if ref and ref not in self.m.processes:
                self.add("LP-001", element_id=pid, element_name=p["name"], element_type="participant",
                         pool=p["name"], message="Pool points to process %r, which is not in the file." % ref)
            if ref in self.m.lanes:
                top = [l for l in self.m.lanes[ref] if l["depth"] == 0]
                if len(top) == 1:
                    self.add("LP-002", element_id=pid, element_name=p["name"], element_type="participant",
                             pool=p["name"], lane=top[0]["name"],
                             message="The pool has a single lane; the lane adds nothing.")

    def check_names(self):
        for node in self.m.nodes.values():
            if node.type in ACTIVITIES and (not node.name or node.name == node.id):
                self.add("NM-001", node, "This %s has no readable name." % node.type)
            elif node.type in ("startEvent", "endEvent") and not node.name:
                what = "trigger" if node.type == "startEvent" else "outcome"
                self.add("NM-004", node, "Name the %s of this event." % what)

    def check_layout(self):
        m = self.m
        if not m.has_diagram:
            if m.nodes:
                self.add("DI-001", message="The file has no layout section at all, so no tool can draw it.")
            return
        for node in m.nodes.values():
            if node.id not in m.shapes:
                self.add("DI-001", node, "This element has no shape, so it will not be drawn.")
        for pid, p in m.participants.items():
            if pid not in m.shapes:
                self.add("DI-001", element_id=pid, element_name=p["name"], element_type="participant",
                         pool=p["name"], message="This pool has no shape, so it will not be drawn.")
        for pid, lanes in m.lanes.items():
            for lane in lanes:
                if lane["id"] not in m.shapes:
                    self.add("DI-001", element_id=lane["id"], element_name=lane["name"], element_type="lane",
                             lane=lane["name"], pool=m.pool_of_process(pid),
                             message="This lane has no shape, so it will not be drawn.")
        for scope in m.scopes:
            for flow in scope.flows:
                if flow.get("id") and flow.get("id") not in m.edges:
                    self.add("DI-002", element_id=flow.get("id"), element_name=flow.get("name"),
                             element_type="sequenceFlow", pool=m.pool_of_process(scope.process_id),
                             message="This flow has no line, so the arrow will not be drawn.")
        for mf in m.message_flows:
            if mf.get("id") and mf.get("id") not in m.edges:
                self.add("DI-002", element_id=mf.get("id"), element_name=mf.get("name"), element_type="messageFlow",
                         message="This message flow has no line, so the arrow will not be drawn.")
        for ref in sorted(set(m.shapes) | m.edges, key=lambda r: r or ""):
            if ref not in m.semantic_ids:
                self.add("DI-003", element_id=ref, message="The layout draws %r, which is not in the model." % ref)

        seen = {}
        for ref in sorted(m.shapes, key=lambda r: r or ""):
            bounds = m.shapes[ref]
            if bounds is None or ref not in m.nodes:
                continue
            if bounds in seen:
                self.add("DI-004", m.nodes[ref], "Drawn exactly on top of %s." % self._label(seen[bounds]))
            else:
                seen[bounds] = ref

        for node in m.nodes.values():
            pool_id = m.process_pool.get(node.scope.process_id)
            pool_bounds = m.shapes.get(pool_id) if pool_id else None
            bounds = m.shapes.get(node.id)
            if not pool_bounds or not bounds or node.type == "boundaryEvent":
                continue
            px, py, pw, ph = pool_bounds
            x, y, w, h = bounds
            if x < px or y < py or x + w > px + pw or y + h > py + ph:
                self.add("DI-005", node, "The shape sits partly outside the %s pool." % (
                    m.participants[pool_id]["name"] or pool_id))


def parse(source):
    """Return (Model, None) or (None, error message)."""
    try:
        tree = ET.parse(source)
    except ET.ParseError as exc:
        return None, "Not well-formed XML: %s" % exc
    except OSError as exc:
        return None, "Cannot read file: %s" % exc
    root = tree.getroot()
    if root.tag != "{%s}definitions" % BPMN:
        return None, "Not a BPMN 2.0 file: the root element is %s, expected bpmn:definitions." % root.tag
    return Model(root), None


def validate(source):
    model, error = parse(source)
    if error:
        return {"ok": False, "error": error}
    findings = Validator(model).run()
    summary = {s: sum(1 for f in findings if f["severity"] == s) for s in (ERROR, WARNING, INFO)}
    return {
        "ok": True,
        "validator": __version__,
        "processes": [model.pool_of_process(pid) or pid for pid in model.processes],
        "summary": summary,
        "findings": findings,
        "not_checked": sorted(JUDGEMENT_RULES),
    }


def format_text(report):
    if not report["ok"]:
        return "PARSE ERROR  %s" % report["error"]
    lines = []
    for f in report["findings"]:
        where = " / ".join(x for x in (f["lane"], f["element_name"] or f["element_id"]) if x)
        lines.append("%-7s  %-7s  %s: %s" % (f["severity"], f["rule"], where or "-", f["message"]))
    s = report["summary"]
    lines.append("%d error(s), %d warning(s), %d info" % (s[ERROR], s[WARNING], s[INFO]))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validate a BPMN 2.0 file against the bpmn-coach ruleset.")
    ap.add_argument("file", nargs="?", help="path to a .bpmn file, or - for stdin")
    ap.add_argument("--format", choices=("json", "text"), default="json")
    ap.add_argument("--rules", action="store_true", help="list every rule and exit")
    ap.add_argument("--version", action="version", version=__version__)
    args = ap.parse_args(argv)

    if args.rules:
        for rid, (sev, title) in RULES.items():
            print("%-7s  %-7s  %s" % (rid, sev, title))
        for rid, (sev, title) in JUDGEMENT_RULES.items():
            print("%-7s  %-7s  %s  (judgement: applied by the skill, not this script)" % (rid, sev, title))
        return 0
    if not args.file:
        ap.error("give a .bpmn file, - for stdin, or --rules")

    source = sys.stdin.buffer if args.file == "-" else args.file
    report = validate(source)
    out = format_text(report) if args.format == "text" else json.dumps(report, indent=2, ensure_ascii=False)
    sys.stdout.buffer.write((out + "\n").encode("utf-8"))
    if not report["ok"]:
        return 2
    return 1 if report["summary"][ERROR] else 0


if __name__ == "__main__":
    sys.exit(main())
