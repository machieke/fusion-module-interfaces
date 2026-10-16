"""Build an editable PowerPoint, vector PDF/SVG, notes and a visual QA contact sheet.

One measured layout drives every format. No application code or runtime state is
changed. Presentation dependencies are separate from the conformance environment.
"""
from __future__ import annotations

import hashlib
import html
import json
import math
import re
from pathlib import Path

import fitz
from PIL import Image, ImageDraw
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.xmlchemy import OxmlElement
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
QA = ROOT / "artifacts/presentation-qa"
EVIDENCE = ROOT / "docs/module-interfaces/evidence"
M12 = EVIDENCE / "m1_2"
RECORD = json.loads((M12 / "manifest.json").read_text())
VERIFY = json.loads((M12 / "verification.json").read_text())
SWAP = json.loads((M12 / "m11-swap-demo.json").read_text())
TRACE = json.loads((M12 / "hive-trace.json").read_text())["detail"]
NATIVE = json.loads((M12 / "native-build.json").read_text())
HISTORICAL_CHAIN = json.loads((EVIDENCE / "chain-demo.json").read_text())
BASE_COMMIT = RECORD["tested_fusion_commit"]
EVIDENCE_COMMIT = "4ee5cbe8b84689a5d2432530083738b263142f90"
MAIN_SLIDES = 26
COMMANDS = {item["name"]: item for item in VERIFY["commands"]}
COUNTS = {name: int(re.search(r"Ran (\d+) tests", COMMANDS[name]["test_summaries"][0])[1])
          for name in ("fixture", "detta")}
COUNTS.update({name: COMMANDS[name]["tests"]["tests"] for name in ("native-baseline", "hive-integration")})
UPSTREAM_COUNTS = [int(re.search(r"(\d+) passed", summary)[1])
                   for summary in COMMANDS["upstream-detta"]["test_summaries"]]
EVIDENCE_FILES = [M12 / name for name in ("manifest.json", "verification.json", "m11-swap-demo.json",
                  "hive-trace.json", "native-build.json")] + [EVIDENCE / "chain-demo.json"]
W, H, SCALE = 1600, 900, 0.6
C = dict(bg="F4F2EB", ink="102B3F", muted="536775", line="C9D2D4",
         white="FFFFFF", pale="E7ECEB", teal="007C78", mint="DCEFE8",
         blue="315E9C", ice="E4EBF5", violet="7458A2", lavender="EBE5F3",
         amber="A86A15", sand="F3E7CE", red="A84E39", blush="F4E3DC",
         dark="0B2233", dim="AAC0CC")
FONTS = {
    "regular": ("Deck", "DejaVuSans", str(HERE / "fonts/DejaVuSans.ttf")),
    "bold": ("DeckBold", "DejaVuSans", str(HERE / "fonts/DejaVuSans-Bold.ttf")),
    "mono": ("DeckMono", "DejaVuSansMono", str(HERE / "fonts/DejaVuSansMono.ttf")),
}
for name, _, path in FONTS.values():
    pdfmetrics.registerFont(TTFont(name, path))


def width(text, size, style="regular"):
    return pdfmetrics.stringWidth(text, FONTS[style][0], size)


SLIDES = []


class Slide:
    def __init__(self, title, section, subtitle="", source="architecture.md", dark=False,
                 notes="", appendix=False):
        self.title, self.section, self.source, self.notes = title, section, source, notes
        self.dark, self.appendix, self.elements = dark, appendix, []
        self.bg = C["dark"] if dark else C["bg"]
        self.fg = C["white"] if dark else C["ink"]
        SLIDES.append(self)
        self.text(72, 43, 1420, section.upper(), 19, C["dim"] if dark else C["teal"], "bold")
        title_size = 52
        while width(title, title_size, "bold") > 1460:
            title_size -= 1
        self.text(70, 95, 1460, title, title_size, self.fg, "bold")
        if subtitle:
            self.text(73, 165, 1450, subtitle, 25, C["dim"] if dark else C["muted"])

    def rect(self, x, y, w, h, fill, stroke=None, radius=0, dash=False):
        self.elements.append(dict(kind="rect", x=x, y=y, w=w, h=h, fill=fill,
                                  stroke=stroke, radius=radius, dash=dash))

    def text(self, x, y, w, text, size=29, color=None, style="regular", lineheight=1.28):
        color = color or self.fg
        lines = []
        for paragraph in str(text).split("\n"):
            current = ""
            for word in paragraph.split():
                proposed = f"{current} {word}" if current else word
                if width(proposed, size, style) > w:
                    if not current:
                        raise ValueError(f"Unbreakable text: {word} on {self.title}")
                    lines.append(current)
                    current = word
                else:
                    current = proposed
            lines.append(current)
        for n, line in enumerate(lines):
            self.elements.append(dict(kind="text", x=x, y=y+n*size*lineheight,
                                      w=w, h=size*lineheight, text=line, size=size,
                                      color=color, style=style))
        return len(lines)*size*lineheight

    def line(self, x1, y1, x2, y2, color=None, thick=2, dash=False, arrow=False):
        color = color or C["muted"]
        self.elements.append(dict(kind="line", x1=x1, y1=y1, x2=x2, y2=y2,
                                  color=color, thick=thick, dash=dash))
        if arrow:
            angle = math.atan2(y2-y1, x2-x1)
            points = [(x2, y2), (x2-13*math.cos(angle)+5*math.sin(angle),
                                 y2-13*math.sin(angle)-5*math.cos(angle)),
                                (x2-13*math.cos(angle)-5*math.sin(angle),
                                 y2-13*math.sin(angle)+5*math.cos(angle))]
            self.elements.append(dict(kind="polygon", points=points, fill=color))

    def path(self, points, color=None, dash=False, arrow=True, thick=2):
        for i, (a, b) in enumerate(zip(points, points[1:])):
            self.line(*a, *b, color, thick, dash, arrow and i == len(points)-2)

    def tag(self, x, y, text, color="teal", fill=None, size=18):
        w = width(text, size, "bold") + 28
        self.rect(x, y, w, size+18, fill or C["mint"], radius=7)
        self.text(x+14, y+7, w-25, text, size, C[color], "bold")
        return w

    def box(self, x, y, w, h, title, body="", color="ink", fill="white", tag=None,
            title_size=29, body_size=24, dashed=False):
        start = len(self.elements)
        while True:
            del self.elements[start:]
            self.rect(x, y, w, h, C[fill], C[color], 13, dashed)
            top = y+22
            if tag:
                self.text(x+22, top, w-44, tag.upper(), 16, C[color], "bold")
                top += 31
            used = self.text(x+22, top, w-44, title, title_size, C[color], "bold")
            if body:
                used += 10 + self.text(x+22, top+used+10, w-44, body, body_size, C["muted"])
            if top+used <= y+h-8:
                break
            if body_size > 21:
                body_size -= 1
            elif title_size > 22:
                title_size -= 1
            elif body_size > 19:
                body_size -= 1
            else:
                raise ValueError(f"Box overflow on {self.title}: {title}")

    def footer(self, n, total):
        color = C["dim"] if self.dark else C["muted"]
        self.line(72, 839, 1528, 839, C["muted"] if self.dark else C["line"], 1)
        self.text(72, 853, 1300, f"OMEGA × ASI   /   THROUGH M1.2   /   {self.source}", 15, color)
        self.text(1410, 849, 120, f"{n:02d} / {total:02d}", 21, color, "mono")


def note(s, text):
    s.notes = text


def band(s, text, y=765, color="ink", fill="pale", size=27):
    while width(text, size, "bold") > 1410:
        size -= 1
    s.rect(72, y, 1456, 53, C[fill], radius=8)
    s.text(94, y+10, 1410, text, size, C[color], "bold")


def table(s, headers, rows, widths, y=235, row_h=88, size=25):
    x0 = 72
    x = x0
    for h, w in zip(headers, widths):
        s.text(x+16, y, w-32, h.upper(), 17, C["muted"], "bold")
        x += w
    y += 42
    for row in rows:
        s.rect(x0, y, sum(widths), row_h-5, C["white"], radius=6)
        x = x0
        for j, (cell, w) in enumerate(zip(row, widths)):
            s.text(x+16, y+17, w-32, cell, size, C["ink"] if j == 0 else C["muted"],
                   "bold" if j == 0 else "regular")
            x += w
        y += row_h


def build_content():
    s = Slide("", "Module-interface architecture", source="M1.2 evidence snapshot 4ee5cbe", dark=True)
    s.text(72, 169, 1330, "One responsibility.\nOne state owner.\nMany possible backends.", 78, C["white"], "bold", 1.12)
    s.text(76, 482, 1250, "Omega Hive × ASI:chain", 42, C["dim"])
    s.text(76, 550, 1290, "From independent module contracts to a real Hive caller that recovers", 31, C["white"])
    s.tag(76, 676, "M1.2 COMPLETE", "teal", C["mint"], 20)
    s.tag(366, 676, "M2 NOT STARTED", "violet", C["lavender"], 20)
    s.text(76, 754, 1300, "Architecture review • 16 October 2026 • verified native integration", 22, C["dim"])
    note(s, 'Start with the helicopter view, all fifteen module responsibilities and function dependencies before the implementation details. M1.1 separated owner commits and proved an independent AtomStorage replacement. M1.2 now connects a pinned real Hive runtime through its native Programs action route, with real DeTTa and a fixture counterparty. The cognitive modules remain specifications. These are engineering contracts, not a final community AtomSpace or numerical model. Suggested delivery: 30–35 minutes through slide 26; seven appendices support discussion. Current evidence is the recorded 16 October 2026 M1.2 run, implementation bb22ef5, evidence snapshot 4ee5cbe.')

    s = Slide("The architecture separates three commitments", "01 / Helicopter view",
              "A function boundary, an authority boundary, and an evidence boundary.")
    for x, num, title, body in [
        (72, "01", "Replace behavior safely", "Select a versioned contract and semantic profile. Keep the consumer independent of the provider."),
        (568, "02", "Write through the owner", "Episodes, beliefs, attention and jobs each have a single logical authority for their state."),
        (1064, "03", "Name what was observed", "Storage, delivery, execution and finality carry separate receipts and explicit limits.")]:
        s.rect(x, 255, 464, 330, C["white"], radius=15)
        s.text(x+26, 280, 410, num, 49, C["teal"], "mono")
        s.text(x+26, 359, 412, title, 31, C["ink"], "bold")
        s.text(x+26, 453, 405, body, 26, C["muted"])
    s.text(75, 630, 1400, "One real Hive operation exercises these boundaries", 30, C["ink"], "bold")
    labels = ["STORE", "SHARE REF", "DELEGATE", "RECOVER", "ACCEPT", "ACK"]
    for i, label in enumerate(labels):
        x = 72+i*248
        s.rect(x, 696, 216, 66, C["mint"], radius=8)
        s.text(x+16, 718, 190, label, 20, C["teal"], "bold")
        if i < 5:
            s.line(x+218, 729, x+243, 729, arrow=True)
    note(s, 'The thesis remains behavior, authority and evidence. A matching method name is insufficient: profiles define semantics and guarantees. Only the state owner may write its state. Receipts describe specific facts rather than one universal success. The real Hive operator action generates a non-sensitive sample, stores it through AtomStorage, sends its reference to a labelled fixture counterparty, submits inspect_atom, recovers completion, records its accepted outcome and acknowledges delivery. Chain submission is not part of this M1.2 path.')

    s = Slide("Fifteen modules; four responsibility groups", "01 / System map",
              "Real Hive consumes these ports; module, process and repository boundaries remain independent.")
    lanes = [(72, 320, "CLIENT / COGNITION", C["lavender"]),
             (420, 400, "SHARED APPLICATION PORTS", C["ice"]),
             (848, 322, "CONTROL & POLICY", C["pale"]),
             (1198, 330, "PROVIDER ADAPTERS", C["mint"])]
    for x, w, title, fill in lanes:
        s.rect(x, 230, w, 495, fill, radius=14)
        s.text(x+18, 251, w-36, title, 18, C["ink"], "bold")
    for i, label in enumerate(["Episodic memory", "Belief revision", "PLN kernel", "ECAN / attention", "Inference control"]):
        s.box(90, 300+i*78, 284, 62, label, color="violet", title_size=23, dashed=True)
    for i, (label, color) in enumerate([("AtomStorage", "blue"), ("Relations · spec", "violet"),
                                      ("Search projection · spec", "violet"), ("Agent messaging", "blue"),
                                      ("Delegated execution", "blue")]):
        s.box(438, 300+i*78, 364, 62, label, color=color, title_size=23, dashed=color=="violet")
    for i, label in enumerate(["Registry", "Compatibility resolver", "Authorization"]):
        s.box(866, 300+i*108, 286, 95, label, color="blue", title_size=22)
    s.box(1216, 300, 294, 144, "DA storage", "Real DeTTa libraries", "teal", title_size=27, body_size=22)
    s.box(1216, 485, 294, 168, "Consensus / finality", "M1 historical; M1.2 NOT_RUN", "amber", title_size=26, body_size=22)
    s.text(866, 649, 282, "Local harness policy\nand static descriptors", 20, C["muted"])
    s.tag(72, 760, "SPECIFICATION ONLY", "violet", C["lavender"])
    s.tag(374, 760, "IMPLEMENTED HARNESS", "blue", C["ice"])
    s.tag(713, 760, "REAL PROVIDER INTEGRATION", "teal", C["mint"])
    note(s, 'All fifteen modules remain visible: five cognition modules, five shared application ports, three control/policy functions and two provider-facing responsibilities. Hive is a consumer of these modules, not a newly invented sixteenth module. Dashed violet boxes remain specifications. Blue is the implemented local contract harness. DeTTa is real local DA/FileStorage; an independent file provider is a contract fixture. Finality has a historical real isolated-chain observation from M1, but the M1.2 chain gate was not run. Native Hive authentication is real; the downstream Fusion credential/scope policy remains a development fixture. No cognitive module is implemented by this increment.')

    s = Slide("Data responsibilities: bytes → references → history", "01 / Responsibility atlas · 1 of 3",
              "The first five modules separate persistence, identity, structure, discovery and provenance.")
    table(s, ["Module", "Function / primary operations", "Owned state / status"], [
        ("DA storage", "Persist opaque bytes\nput · get · availability", "Payloads and shares\nREAL LOCAL PROVIDER"),
        ("AtomStorage", "Assign scoped immutable references\ncreate · get · getMany · availability", "Reference + replay metadata\nIMPLEMENTED"),
        ("Relations", "Represent ordered structural roles\nassertRelation · getRelation", "Immutable relation records\nSPECIFIED"),
        ("Search projection", "Find references at a known watermark\nquery", "Rebuildable index\nSPECIFIED"),
        ("Episodic memory", "Preserve ordered events + provenance\nrecordEpisode · appendEvent", "Private episode history\nSPECIFIED · M2")], [330, 600, 526], row_h=92, size=25)
    band(s, "Capture and retrieve data before choosing its meaning.")
    note(s, "DA persists opaque payloads and erasure shares. AtomStorage owns the application reference metadata, immutable revision and semantic replay keys. Relations describe explicit ordered roles; a link is not automatically a belief. Search is a rebuildable projection that exposes its watermark, not the authoritative store. Episodic memory adds occurrence identities and episode-local ordering, so equal payload bytes may describe different observations. Its full private history remains client-side. This design deliberately does not require a parser, ontology, embedding model or LLM just to store data. Additional relation operations are outgoing/incoming; episode reads are readEpisode/findEpisodes. Those future contracts remain unimplemented through M1.2.")

    s = Slide("Cognitive responsibilities: history ≠ truth ≠ attention", "01 / Responsibility atlas · 2 of 3",
              "All four modules below are typed specifications. Fusion adds no cognitive provider.")
    table(s, ["Module", "Function / primary operations", "Owned state / exclusion"], [
        ("Belief revision", "Revise under an explicit numerical model\nsubmitEvidence · readBelief", "Belief + evidence ledger\nNo agenda or attention writes"),
        ("PLN kernel", "Apply a rule to explicit premises\nprofiles · applyRule", "No mutable domain state\nReturns a proposed derivation"),
        ("ECAN / attention", "Allocate, select and decay attention\nsubmitStimulus · select · advance", "Attention balances + logical time\nNo PLN dependency"),
        ("Inference control", "Schedule bounded reasoning work\nstep", "Step receipts + checkpoint\nNo ownership of truth or attention")], [330, 630, 496], row_h=109, size=25)
    band(s, "Mathematics and attention policy remain explicit review gates.", color="violet", fill="lavender")
    note(s, "Belief revision is the only owner of the truth/evidence aggregate. Its numerical profile has not been selected as a universal model. The PLN kernel is pure over ordered immutable premise snapshots and returns a proposal; it cannot update beliefs or choose its own agenda. ECAN owns attention and logical time, including allocation, decay and tie-breaking under a declared policy. readAttention is also part of its contract. Inference control orchestrates retrieval, belief snapshots, rules and feedback within candidate, rule, generation and time budgets. Control stores its own step receipts/checkpoint, not the other owners' state. Reviewers and maintainers for these new contracts remain unassigned.")

    s = Slide("Control responsibilities: move work without moving authority", "01 / Responsibility atlas · 3 of 3",
              "The remaining six modules connect owners and report exactly what happened.")
    table(s, ["Module", "Function / primary operations", "Owned state / status"], [
        ("Messaging", "Accept, deliver, acknowledge\nsend · poll · ack", "Inbox + deduplication · IMPLEMENTED"),
        ("Execution", "Run one named operation\nsubmit · status · result", "Jobs + completion outbox · IMPLEMENTED"),
        ("Registry", "Describe configured providers\ndescriptors", "Static configuration · IMPLEMENTED"),
        ("Resolver", "Match required semantics\nresolve", "No mutable state · IMPLEMENTED"),
        ("Consensus / finality", "Submit approved commitment; observe\nsubmit · observe", "Signed intents · HISTORICAL M1"),
        ("Authorization", "Check current caller + scope + method\nauthorize / live policy checks", "Server-owned policy · LOCAL FIXTURE")], [330, 590, 536], row_h=82, size=23)
    note(s, 'Messaging owns accepted inbox entries, acknowledgements and replay. Execution owns jobs and the completion outbox, and accepts only inspect_atom. Its result atoms belong to AtomStorage, a separate owner. Registry and resolver select a configured descriptor, not permission. Finality is a separate adapter with a historical real M1 observation; it is not invoked by the real Hive M1.2 workflow. Native Hive authenticates the operator and supplies trusted actor context. Fusion then enforces current scope, method and route policy through a labelled local test-policy implementation. Caller-supplied identity does not confer authority.')

    s = Slide("Function dependencies: the proposed cognitive path", "01 / Dependency map · data and cognition",
              "Dashed arrows = specified calls. Solid arrow = implemented call. Direction = caller → provider.", source="ports.py + contracts.md")
    s.box(72, 261, 326, 122, "Inference control", "step(budget)", "violet", "lavender", title_size=28, dashed=True)
    for x, title, body in [(516, "Search", "query(profile, watermark)"), (1008, "ECAN / attention", "select · submitStimulus")]:
        s.box(x, 253, 434, 111, title, body, "violet", title_size=26, body_size=22, dashed=True)
    s.box(516, 458, 434, 111, "Belief revision", "readBelief · submitEvidence", "violet", title_size=26, body_size=22, dashed=True)
    s.box(1008, 458, 434, 111, "PLN kernel", "applyRule(premise snapshots)", "violet", title_size=26, body_size=21, dashed=True)
    s.path([(398, 290), (516, 290)], C["violet"], True)
    s.path([(398, 278), (447, 278), (447, 225), (1225, 225), (1225, 253)], C["violet"], True)
    s.path([(398, 338), (450, 338), (450, 510), (516, 510)], C["violet"], True)
    s.path([(398, 355), (424, 355), (424, 414), (1225, 414), (1225, 458)], C["violet"], True)
    s.text(525, 385, 650, "Calls carry snapshots, evidence and bounded feedback", 21, C["violet"])
    s.box(72, 458, 326, 111, "Episodic memory", "appendEvent · readEpisode", "violet", title_size=25, body_size=21, dashed=True)
    s.text(420, 595, 1108, "Episodes emit evidence; the orchestrator submits it to revision.", 24, C["muted"])
    for x, title, color in [(72, "Relations", "violet"), (516, "AtomStorage", "blue"), (1008, "DA storage", "teal")]:
        s.box(x, 680, 326 if x==72 else 434, 80, title, color=color, title_size=27, dashed=color=="violet")
    s.line(398, 720, 516, 720, C["violet"], dash=True, arrow=True)
    s.text(414, 681, 98, "create", 19, C["violet"])
    s.line(950, 720, 1008, 720, C["teal"], arrow=True)
    s.text(962, 681, 95, "put/get", 18, C["teal"])
    s.path([(235, 569), (235, 649), (650, 649), (650, 680)], C["violet"], True)
    s.text(727, 639, 695, "Search reads records/events; revision reads evidence snapshots.", 20, C["muted"])
    note(s, "This is a declared runtime dependency view, not a claim that the cognitive loop was executed. Arrows point from a caller to the port it invokes. Inference control calls Search.query, attention.select and submitStimulus, belief.readBelief and submitEvidence, and PLN.applyRule. Episode history produces EvidenceRef values for the orchestrator; episode writes do not invoke hidden truth setters. Relations can persist ordinary atom records and episodic memory stores referenced payloads. AtomStorage then calls the opaque DA storage port: this is the solid implemented path. Search reads immutable records/events and belief revision consumes evidence/atom snapshots; those data dependencies are named below the diagram to avoid a misleading tangle of arrows. Interface imports remain acyclic; runtime feedback is expressed through explicit commands and values.")


    s = Slide("Function dependencies: the real native path", "01 / Dependency map · runtime control",
              "Solid arrows = exercised calls. Every provider effect crosses an existing validated interface.",
              source="program.py · ports.py · execution.py")
    s.box(72,246,330,130,"Native Hive", "POST /programs/…/act\nTrusted actor + command", "teal","mint",title_size=29,body_size=22)
    s.box(535,246,430,130,"Fusion inspect plugin", "Owns caller receipts\nUses selected stdio binding", "blue","ice",title_size=29,body_size=23)
    s.box(1080,246,448,130,"Registry + resolver", "describe → select\nPin full descriptor tokens", "blue",title_size=28,body_size=23)
    s.line(402,312,535,312,C["teal"],arrow=True)
    s.line(965,312,1080,312,C["blue"],arrow=True)
    s.box(535,455,430,120,"Validated binding + policy", "Wire/profile checks · live authority", "blue","ice",title_size=27,body_size=22)
    s.line(750,376,750,455,C["blue"],arrow=True)
    s.box(72,455,330,120,"Execution", "submit · status · result", "blue",title_size=29,body_size=22)
    s.box(1080,455,448,120,"AtomStorage", "create · get · getMany · availability", "blue",title_size=29,body_size=21)
    s.line(535,514,402,514,C["blue"],arrow=True)
    s.line(965,514,1080,514,C["blue"],arrow=True)
    s.path([(237,455),(237,414),(1304,414),(1304,455)],C["blue"])
    s.text(800,386,700,"Submit → get(input) · worker → get / create",21,C["blue"])
    s.box(535,677,430,105,"Messaging", "send · poll · ack", "blue",title_size=28,body_size=22)
    s.line(750,575,750,677,C["blue"],arrow=True)
    s.path([(237,575),(237,729),(535,729)],C["blue"])
    s.text(282,626,430,"Outbox → CompletionDelivery.accept",19,C["blue"])
    s.path([(965,729),(1020,729),(1020,550),(1080,550)],C["blue"])
    s.text(802,626,210,"send → get(ref)",20,C["blue"])
    s.box(1080,677,448,105,"DeTTa DA / FileStorage", "Opaque put · get · availability", "teal","mint",title_size=27,body_size=21)
    s.line(1304,575,1304,677,C["teal"],arrow=True)
    s.text(87,796,1360,"Optional finality uses a separate caller + approved digest + signer; M1.2 does not invoke it.",21,C["muted"])
    note(s,"Follow the real native dispatch into the thin plugin, which holds a caller-owned receipt and uses Subprocess/Peer through descriptor-bound validation. Direct storage, messaging and execution calls all cross the same authenticated boundary. Trusted composition supplies concrete owners; the plugin never constructs them or accesses their tables. Messaging.send validates the referenced bytes through caller-authorized AtomStorage.get; Execution.submit reads the input before accepting a new job. The worker calls declared AtomStorage get/create, then execution commits terminal state/outbox. CompletionDelivery.accept belongs to the mailbox owner and commits separately. Chain remains a separate, uninvoked adapter. This is a logical call map; it does not force one process per module.")

    s = Slide("Separate owners now have separate durable commits", "02 / Ownership · M1.1 preserved",
              "Result atoms, execution state, mailbox acceptance and caller acceptance do not share a transaction.",
              source="architecture.md · atoms.py · messaging.py · program.py")
    cards=[(72,250,"AtomStorage","Immutable refs + replay","Own metadata journal over opaque DA; independent file fixture also supported.","teal"),
           (568,250,"Execution","Jobs + completion outbox","One terminal-state transaction; result persistence already committed.","blue"),
           (1064,250,"Messaging","Inbox + acknowledgements","Own acceptance and ack journal; delivery may repeat until acknowledged.","blue"),
           (72,506,"Native caller","Intent + accepted outcome","Minimal plugin receipt; stable job context survives loss of caller RAM.","teal"),
           (568,506,"Wire admission","Mutation response + fingerprint","Colocated with execution; each effect owner also keeps replay identity.","blue"),
           (1064,506,"Authorization","Current grants + routes","Operator-owned configuration; access is rechecked on retries and work.","amber")]
    for x,y,title,tag,body,color in cards:
        s.box(x,y,464,220,title,body,color,"white",tag=tag,title_size=29,body_size=24)
    band(s,"Co-location is allowed. Foreign SQL and shared transaction assumptions are not part of the contracts.",size=24)
    note(s,"This replaces the old M1 shared-journal drawing. M1.1 split atom metadata, messages and execution into separately committed owner stores and declared the dependencies actually exercised by the worker. Execution's own terminal state and outbox are atomic with each other, not with atom persistence or mailbox acceptance. Wire replay metadata is colocated with execution, while cross-owner operations have owner-local replay. M1.2 adds only a minimal caller boundary receipt, not episodes or a new journal framework. It serializes one caller journal and permits one unfinished intent per dedicated route. All observations concern persistent local files and process restart.")

    s = Slide("AtomStorage replacement is independently exercised", "02 / Substitution · four-way matrix",
              "Protocol fixture callers exercise two providers and two transports; the worker logic is unchanged.",
              source="evidence/m1_2/m11-swap-demo.json · test_m11.py")
    table(s,["Selected AtomStorage", "In-process binding", "Private stdio binding"],[
        ("Real DeTTa libraries", "PASS · independent workflow", "PASS · independent workflow"),
        ("Atomic-file fixture", "PASS · independent workflow", "PASS · independent workflow")],[510,473,473],row_h=130,size=28)
    s.box(72,592,704,140,"Independent implementation", "The file fixture does not inherit AtomOwner or use its SQLite atom table.","blue","ice",title_size=30,body_size=25)
    s.box(800,592,728,140,"Fresh stores only", "No accepted jobs or existing references are moved between providers.","amber","sand",title_size=30,body_size=25)
    band(s,"Interface, implementation, transport and placement remain independent choices.",size=27)
    note(s,f"The committed M1.2 matrix contains {len(SWAP['runs'])} workflows: DeTTa and fixture-files under both in-process and private subprocess bindings. These peers remain fixtures; this matrix is not relabelled as the new native Hive test. Execution depends on declared AtomStorage and CompletionDelivery ports and does not inspect concrete atom owners. The file fixture owns atomic payload/record files and is independently implemented. This proves substitutability in the documented fresh-store profile. It is not another DA network, live namespace switching, a journal migration or distributed placement. M1.2 preserves these boundaries without changing fusion/.")

    s = Slide("Compatibility binds semantics and selected replies", "02 / Compatibility · exact profiles",
              "Consumer requirements are independent of provider advertisements.",source="registry.py · bindings.py · responses.py")
    for i,(title,body) in enumerate([("Version","Wire remains 1.0.0"),("Profile","Exact behavioral semantics"),("Operations","Required methods and limits"),("Descriptor","Token checked on invocation and reply")]):
        x=72+i*370
        s.box(x,263,346,173,title,body,"blue",title_size=31,body_size=25)
        if i<3:s.line(x+346,347,x+364,347,C["blue"],arrow=True)
    for x,title,body in [(72,"AtomStorage","immutable-bytes/1"),(568,"Messaging","durable-mailbox/2"),(1064,"Execution","inspect-atom/2")]:
        s.box(x,486,464,130,title,body,"teal","mint",title_size=29,body_size=26)
    s.text(77,660,1430,"Descriptor implementation 0.1.1   •   Deterministic inspect output algorithm 0.1.0",28,C["ink"],"bold")
    band(s,"Descriptor hashes establish binding consistency; remote identity and provider truth remain separate.",size=24)
    note(s,"The resolver uses fixed consumer requirements, exact profiles, supported operations, privacy and claimed guarantees. Binding invocation and success replies carry the selected descriptor token; response validation checks shape, scope, references, integrity, receipts and known correlation. The native adapter loads operator-selected descriptors and uses that same boundary. Native-path tests reject an incompatible profile and a changed descriptor. Wire remains 1.0.0; the /2 messaging and execution profiles describe neutral process-restart receipts and recoverable status. They do not imply live 1.x rolling interoperability. No proof verifier is installed, so required verification fails closed.")

    s = Slide("Native identity and stable intent stay separate", "02 / Invocation · trusted context",
              "Hive supplies the actor; the operator supplies the mapping; Fusion checks current authority.",
              source="ProgramActions.person_act · integration/hive/program/program.py")
    s.rect(72,250,744,463,C["dark"],radius=14)
    for i,line in enumerate(["action: inspect", "params: {seed: 12}", "idempotency_key: generated-intent-12", "", "ctx.actor ← native authentication", "ctx.command ← native request digest", "credential ← private operator config"]):
        s.text(99,284+i*51,689,line,23,C["white"] if i<4 else "77DDC4","mono")
    s.box(865,250,663,134,"Only generated shareable input", "The seed produces bytes; no private history or arbitrary remote operation is accepted.","blue","ice",title_size=28,body_size=25)
    s.box(865,412,663,134,"Original input + original key", "An ambiguous response replays the intent; it does not allocate a second job.","blue","ice",title_size=28,body_size=25)
    s.box(865,574,663,139,"Authorization remains live", "Even a recorded successful outcome must pass current module checks before return.","amber","sand",title_size=28,body_size=25)
    band(s,"Scope labels, saved receipts and caller-supplied identity do not grant permission.",size=27)
    note(s,"The diagram shows native action fields, not a complete copy-paste HTTP request; the actual body also includes the swarm and an empty items list. Hive authenticates the operator, checks swarm visibility, rejects identity fields in params, and delivers trusted actor/command context. An exact principal/swarm configuration selects credential, scope, reply route and a fixture counterparty. The plugin accepts only an integer seed and no arbitrary input bytes. Stable keys cover input creation, sharing, job submission and acknowledgement. On retry, status/get/poll/ack continue to enforce the current Fusion policy. Test credentials and private configuration are never embedded in the deck.")

    s = Slide("The intended Hive source now has a verified entrypoint", "03 / Native integration · source first",
              "The supplied schematics identify the runtime and revision used for this engineering gate.",
              source="sources.json · discovery.md · native-baseline.xml")
    s.box(72,250,445,162,"Schematics", "4af00db4e395\nDocumentation points to Hive 34b0fb3.","ink",title_size=31,body_size=26)
    s.box(566,250,445,162,"Actual Hive source", "34b0fb32ab38\nAuthorized SSH fetch; clean checkout.","teal","mint",title_size=30,body_size=26)
    s.box(1060,250,468,162,"Native baseline", f"{COUNTS['native-baseline']} selected tests passed\nUpstream process driver is a fixture.","teal","mint",title_size=30,body_size=26)
    s.line(517,331,566,331,C["teal"],arrow=True);s.line(1011,331,1060,331,C["teal"],arrow=True)
    s.rect(72,466,1456,244,C["dark"],radius=14)
    for i,line in enumerate(["python -m hive → exclusive startup recovery → create_app", "POST /api/programs/fusion-inspect/act", "ProgramActions.person_act → Programs.act → plugin.act"]):
        s.text(101,495+i*66,1384,line,27,C["white"],"mono")
    band(s,"Real native dispatch; ASGI TestClient is the transport. No fake Hive, live LLM or new server.",size=25)
    note(s,"The old runtime-unavailable statement is historical. The user supplied clean omegahive-schematics 4af00db4e395375484dd48d0b9068a59afcf01f8; its component map names 34b0fb3. Authorized SSH retrieved PhysixSNET/omegahive at 34b0fb32ab3806e5609fc89bb7535518a35e1aea. The different observed remote HEAD was not silently selected. Native startup is python -m hive. The test driver uses its lock, startup recovery and create_app in a separate OS process, with real PeTTa and the default Supervisor. It signs in and traverses the actual Programs route. Native baseline tests have their declared fake process driver; the new real-caller tests do not. No LLM or mind is started. This pin selects an engineering experiment, not a final community product release.")

    s = Slide("One native operation crosses the existing interfaces", "03 / Native integration · sequence",
              "The caller stores intent; each provider commits only its own state.",source="program.py · execution.py · messaging.py")
    xs=[155,480,805,1130,1455]
    for x,label in zip(xs,["Real Hive", "Caller receipt", "AtomStorage", "Execution", "Messaging"]):
        s.rect(x-90,235,180,54,C["mint"] if label in {"Real Hive","AtomStorage"} else C["ice"],radius=8)
        s.text(x-79,251,161,label,21,C["ink"],"bold")
        s.line(x,302,x,760,C["line"],dash=True)
    steps=[(155,480, "1  Save original intent",330),(155,805,"2  create → real DeTTa persistence receipt",382),
           (155,1455,"3  send reference to fixture counterparty",434),(155,1130,"4  submit inspect_atom → durable job acceptance",486),
           (155,480,"5  Save pending job context",538),(1130,805,"6  Worker reads input; result atom commits",590),
           (1130,1455,"7  Terminal + outbox commit; mailbox accepts separately",642),
           (155,1455,"8  Recover status → poll → get result → accept → ack",723)]
    for x1,x2,label,y in steps:
        left=min(x1,x2)
        if y in {590,642}:left=510
        s.rect(left+4,y-28,width(label,20)+12,26,C['bg'])
        s.text(left+8,y-28,1510-left,label,20,C["ink"])
        s.line(x1,y,x2,y,C["teal"] if y in {382,590} else C["blue"],arrow=True)
    note(s,"All effects originate in the real native operation, not a renamed protocol demo. The caller first commits its original intent. AtomStorage persists generated bytes in actual DeTTa, then Messaging accepts a reference for the explicitly labelled fixture counterparty. DelegatedExecution accepts only inspect_atom under the original key and correlation. The caller records the accepted job. A separate real worker reads/persists through AtomStorage, then commits execution terminal state/outbox. Messaging accepts the completion in a separate transaction. The final arrow summarizes the reconciliation expanded on the next slides: status /2 restores known correlation, poll and get verify the completion, caller acceptance commits, and a stable-key acknowledgement follows. This is not one distributed transaction.")

    s = Slide("Six receipts describe six different facts", "03 / Native integration · completion semantics",
              "A pending native receipt can be reconciled; it is not a Hive goal or a claim of completed work.",
              source="contracts.md · m1_2-evidence.md")
    entries=[(72,250,"1 · INPUT PERSISTENCE","Bytes have a scoped ref","Real DeTTa receipt; local files/process restart.","teal"),
             (568,250,"2 · JOB ACCEPTANCE","Work is durably queued","No claim yet about execution or reply delivery.","blue"),
             (1064,250,"3 · RESULT + TERMINAL","Execution has an outcome","Atom result first; job terminal/outbox commit second.","blue"),
             (72,501,"4 · MAILBOX ACCEPTANCE","Completion is retained","Poll can repeat until the recipient acknowledges.","blue"),
             (568,501,"5 · CALLER ACCEPTANCE","One outcome is recorded","Known job, correlation and result bytes verified.","teal"),
             (1064,501,"6 · ACKNOWLEDGEMENT","Delivery is acknowledged","Retry reuses the same key if the ack response is lost.","teal")]
    for x,y,tag,title,body,color in entries:s.box(x,y,464,221,title,body,color,"white",tag=tag,title_size=28,body_size=24)
    band(s,"Native done = verified outcome + successful acknowledgement. Terminal failure stays an explicit error.",size=24)
    note(s,"These facts are independent. A result atom can persist while the job is still queued after worker death. A succeeded job may have an unsent outbox when a reply route is full. A caller may have recorded its accepted outcome while acknowledgement is still pending. The plugin commits its outcome before acknowledgement to deduplicate that gap, and rechecks live authorization before returning it on replay. A failed worker completion is verified, recorded and acknowledged as an error, never transformed into empty memory or successful inspection. There is no exactly-once display or physical-execution guarantee. The original acceptance receipt in the trace remains queued/not-observed because it describes admission, not the later outcome.")

    s = Slide("A restarted Hive caller recovers without its old RAM", "03 / Recovery · actual caller SIGKILL",
              "Three kill points traverse the same authenticated native action route.",source="test_integration.py · hive-integration.xml")
    for x,tag,title,body in [
        (72,"AFTER ADMISSION","Response lost", "Fusion accepted the job; the caller has only its original intent. Same input + key recovers the same job."),
        (568,"AFTER SUBMISSION","Caller stops", "The local receipt retains the job. Status /2 restores known correlation after a new process signs in."),
        (1064,"AFTER ACCEPTANCE","Ack not yet sent", "The outcome is durable. Redelivery is checked against it, then acknowledged without a second outcome row.")]:
        s.box(x,258,464,345,title,body,"blue","white",tag=tag,title_size=34,body_size=27)
        s.tag(x+22,627,"SIGKILL → RESTART → REPLAY","red",C["blush"],17)
    s.text(77,705,1430,"Observed: one job · one result atom · one completion · one accepted outcome identity",29,C["teal"],"bold")
    band(s,"Known-job recovery uses durable context and status; unsolicited completions do not establish causality.",size=24)
    note(s,"These are actual OS-process kills, not exceptions standing in for restart. The test caller is a native Hive app process with real authentication and dispatch. Trusted configuration enables a SIGSTOP checkpoint; the test waits for its marker and sends SIGKILL. Admission-loss occurs after durable Fusion acceptance but before saving the job in the caller record. Submission-loss occurs after that local record commits. Acceptance-loss occurs after outcome commit and before ack. A new app process signs in against the same native data directory and reconciles the original request. Tests assert stable job identity, two total atoms (input and one result), one outbox, one completion, one caller outcome and no delivery after ack. The receipt is a minimal boundary record, not an episodic-memory implementation.")

    s = Slide("Worker failure and backpressure preserve pending work", "03 / Recovery · independent commits",
              "A result can survive worker death; a full route can delay completion without losing it.",
              source="execution.py · test_m11.py · test_integration.py")
    stages=[(72,"Result atom","Committed by AtomStorage","teal"),(442,"Job + outbox","Committed by execution","blue"),
            (812,"Completion","Accepted by Messaging","blue"),(1182,"Caller outcome","Accepted, then acknowledged","teal")]
    for i,(x,title,body,color) in enumerate(stages):
        s.box(x,252,346,156,title,body,color,"white",title_size=29,body_size=25)
        if i<3:s.line(x+346,331,x+365,331,C["blue"],arrow=True)
    s.box(72,472,704,238,"Kill after result persistence", "The job remains queued while its atom is durable. Restart reuses the logical result and later publishes completion.","blue","ice",tag="REAL WORKER SIGKILL",title_size=29,body_size=27)
    s.box(800,472,728,238,"Full reply route", "The outbox remains pending. The caller refuses an unrelated delivery; once capacity returns, the known completion is accepted.","amber","sand",tag="NATIVE CALLER BACKPRESSURE",title_size=29,body_size=27)
    band(s,"Worker revocation yields an explicit failed completion with no result atom; no silent success.",size=25)
    note(s,"The native worker-recovery test kills the existing worker after AtomStorage has committed the result and before execution terminal state/outbox commit. The test observes two atoms, one queued job and no outbox, then restarts and verifies one result. In the full-route test, a labelled fixture fills the dedicated reply route. Flush reports zero sent and one pending. The native operation refuses the unrelated delivery and does not record an accepted outcome. After fixture cleanup, flush and native completion succeed. A separate test revokes worker create authority after admission and observes an explicit UNAUTHORIZED failed completion without a result atom. Temporary input unavailability is exercised in the preserved M1.1 matrix; the new native representative provider-failure case is route backpressure. No cross-owner atomicity is claimed.")

    s = Slide("The DA boundary remains application-neutral", "03 / Storage · opaque persistence",
              "The external adapter translates application references into generic coordinates and opaque bytes.",source="adapters/detta/src/main.rs · test_contract.py")
    for x,w,title,body,color,fill in [(72,450,"Application contracts","Scope · references · replay identity","blue","ice"),
        (619,405,"External adapter","Opaque payload + generic coordinate","teal","mint"),
        (1121,407,"DeTTa core","DA encoding + FileStorage","teal","mint")]:
        s.box(x,253,w,164,title,body,color,fill,title_size=30,body_size=26)
    s.line(522,335,619,335,C["teal"],arrow=True);s.line(1024,335,1121,335,C["teal"],arrow=True)
    s.text(75,477,1000,"4 data shares + 2 parity shares",38,C["ink"],"bold")
    for i in range(6):
        x=74+i*153;missing=i>=4
        s.rect(x,555,125,115,C["pale"] if missing else C["mint"],C["line"] if missing else C["teal"],10,missing)
        s.text(x+31,580,90,f"S{i+1}",35,C["muted"] if missing else C["teal"],"mono")
        s.text(x+16,631,110,"removed" if missing else "present",17,C["muted"])
    s.box(1060,506,468,195,"Observed reconstruction","Cached payload + two shares removed: exact bytes recovered. A third missing share is unavailable.","teal",title_size=28,body_size=25)
    band(s,"The DA core does not interpret Hive identities, truth values, attention balances or job state.",size=25)
    note(s,"This unchanged DA boundary is exercised against a freshly fetched clean secured-contract-spaces revision 272888f264dd2dde18b574cabb53c266b0dac2ec. No Hive-specific schema is added to DeTTa. Application references and replay semantics belong above opaque DA. Conformance removes the cached payload and two erasure shares and verifies reconstruction; three missing shares and corruption fail explicitly. This is actual local library execution, not a validator/custody network or an indefinite-retention claim. The independent atomic-file provider is an AtomStorage contract fixture, not a second DA network. The clean-source rebaseline excludes historical dirty storage-format and custody-pruning additions and reruns applicable tests.")

    s = Slide("Native-path refusals preserve authorization and replay", "03 / Authorization · fail closed",
              "The host and module boundaries each keep their own checks.",source="program_actions.py · policy.py · test_integration.py")
    table(s,["Attempt", "Observed result", "What stays protected"],[
        ("Supply principal in action params", "Native identity_in_request", "Hive derives the actor"),
        ("Map caller to the wrong scope", "UNAUTHORIZED", "Scope alone confers no access"),
        ("Revoke caller after completion", "UNAUTHORIZED on replay", "Saved outcome grants no authority"),
        ("Change profile / descriptor", "UNSUPPORTED_PROFILE", "No weaker provider fallback"),
        ("Change input under original key", "CONFLICT", "No second job with new meaning"),
        ("Revoke worker after admission", "Explicit failed completion", "No unauthorized result write")],[530,420,506],row_h=79,size=23)
    band(s,"Real Hive authentication + development Fusion policy. Production isolation remains unproven.",color="amber",fill="sand",size=25)
    note(s,"Every row here is tested through the actual native route, except the trusted operator's setup/failure injection. The first row is rejected by Hive before plugin effects. The plugin uses the authenticated actor/swarm mapping and current module credentials; it cannot nominate a principal in the request body. Changed descriptor identity fails binding consistency at the server even if its advertised method set looks compatible. Cached success still requires live status/get/poll/ack authority. The worker rechecks its own and requester permissions after admission. Fusion's credential/scope policy is explicitly a local test policy, not production SCS or isolation against the same OS user.")

    s = Slide("Real runtime, real provider, fixtures and unrun scope", "03 / Evidence · component classification",
              "Each claim stays attached to the component and gate actually exercised.",source="m1_2-evidence.md · manifest.json")
    table(s,["Component", "Classification", "Observed boundary"],[
        ("Hive + PeTTa", "REAL NATIVE RUNTIME", "Authenticated Programs dispatch / restart"),
        ("DeTTa DA + FileStorage", "REAL LOCAL PROVIDER", "Persisted shares and reconstruction"),
        ("Messaging / execution / worker", "IMPLEMENTED LOCAL HARNESS", "Separate owner commits; inspect_atom only"),
        ("Counterparty / data / file provider", "EXPLICIT FIXTURES", "Generated sample and contract experiments"),
        ("Fusion credential policy", "DEVELOPMENT FIXTURE", "Native auth is real; downstream policy local"),
        ("Chain / cognitive implementations", "NOT RUN IN M1.2", "M1 chain historical; M2+ still specified")],[467,459,530],row_h=80,size=22)
    note(s,"The native dispatch is not a wrapper named Omega around Peer. It is the verified Hive app and plugin mechanism with real PeTTa. TestClient is an ASGI test transport and the caller driver is a test harness, not a substituted runtime. The new caller tests use the real default Supervisor without starting minds; the 34 upstream baseline tests use their labelled fake process driver. DeTTa is real local library storage. Mailbox and execution are actual Fusion implementations, while the payload, counterparty and policy are fixtures. The deterministic inspect operation is plumbing, not a cognitive capability. No live LLM is used. The historical chain observation is neither erased nor represented as a new same-artifact Hive-to-chain run.")

    s = Slide("Fresh verification exercises distinct layers", "03 / Evidence · executed tests",
              "Zero failures or skips in the final run. Fixture isolation is a subset, not extra unique coverage.",source="evidence/m1_2/verification.json")
    table(s,["Gate / suite", "Passed", "Scope of the observation"],[
        ("Fixture-only isolation", str(COUNTS['fixture']), "Real DeTTa and Hive paths deliberately absent"),
        ("Provider / transport matrix", str(COUNTS['detta']), "Includes the 51 fixture tests; four workflows"),
        ("Clean upstream DeTTa", ' + '.join(map(str,UPSTREAM_COUNTS)), "DA + storage; historical dirty source had 40 storage tests"),
        ("Native Hive baseline", str(COUNTS['native-baseline']), "Selected native tests; fixture process driver"),
        ("Real-caller integration", str(COUNTS['hive-integration']), "Native dispatch, process recovery and refusals")],[520,196,740],row_h=91,size=25)
    band(s,"Historical 27-test M1 results and earlier dirty sources are retained, not silently reused as current passes.",size=23)
    note(s,"Counts come from the committed M1.2 verification JSON, not a new test run for this deck. The 51 fixture tests are included in the full 90-test matrix. Clean upstream DeTTa passes 62 DA and 38 storage tests; the historical dirty checkout passed 40 storage tests because it included two local additions. The native baseline is 34 selected tests, not the full Hive suite. The new real-caller suite has 13 cases covering success/replay, three caller kill points, worker death, route backpressure, worker revocation and six negative conditions. All final run commands returned zero; native JUnit records no failures, errors or skips. Development failures and their corrections remain in the evidence directory. No new benchmark or integration run is implied by rebuilding the presentation.")

    s = Slide("One trace ties native intent to acknowledged outcome", "03 / Evidence · actual M1.2 artifact",
              "Identifiers below come directly from the recorded real Hive workflow.",source="evidence/m1_2/hive-trace.json")
    for x,title,body,color in [(72,"Native caller",f"{TRACE['caller']['principal']}\nSwarm {TRACE['caller']['swarm']}","teal"),
        (568,"Generated input",f"{TRACE['output']['length']} bytes · scope shared-test\n{TRACE['input']['ref']['id'][:18]}…","blue"),
        (1064,"Delegated job",f"inspect_atom / output 0.1.0\n{TRACE['job']['job_id'][:18]}…","blue")]:
        s.box(x,252,464,170,title,body,color,"white",title_size=30,body_size=25)
        if x<1064:s.line(x+464,337,x+490,337,C["blue"],arrow=True)
    s.rect(72,472,958,243,C["dark"],radius=13)
    s.text(100,496,895,"PERSISTED RESULT DIGEST",19,"77DDC4","bold")
    d=TRACE['result']['ref']['digest']
    s.text(100,545,895,d[:32]+"\n"+d[32:],30,C["white"],"mono")
    s.text(100,648,890,"Job ID = completion delivery ID; caller receipt = correlation ID.",22,C["dim"])
    s.box(1074,472,454,243,"Accepted and acknowledged", "One durable outcome identity.\nBoth atom receipts: real DeTTa, six shares / threshold four.","teal","mint",title_size=29,body_size=26)
    band(s,"CHAIN = NOT_RUN for this result. The earlier M1 digest is a different, explicitly historical artifact.",color="amber",fill="sand",size=24)
    note(s,f"Full source values: actor {TRACE['caller']['principal']}; swarm {TRACE['caller']['swarm']}; input ref {TRACE['input']['ref']['id']}, digest {TRACE['input']['ref']['digest']}, {TRACE['output']['length']} bytes. Job and completion delivery ID {TRACE['job']['job_id']}. Correlation and caller receipt {TRACE['correlation_id']}. Result ref {TRACE['result']['ref']['id']}, digest {TRACE['result']['ref']['digest']}. Both atom receipts identify detta-local-rs/1, local-files-process-restart, six shares and threshold four, with no chain or custody certificate. Native outcome is done after result verification and acknowledgement. The initial job receipt still says queued/not-observed because it describes acceptance. This artifact was not submitted to a chain in M1.2.")

    s = Slide("Reproduction separates source, build and execution", "04 / Handoff · obtainable inputs",
              "Fresh disposable checkout; immutable authorized sources; locked new builds; actual runtime tests.",source="build_hive.py · native-build.json · verification.json")
    for x,tag,title,body in [(72,"1 · SOURCE","Obtain exact bytes", "Fusion commit/bundle; Hive and DeTTa via authorized SSH; public PeTTa and SWI commits."),
        (568,"2 · BUILD","Create new artifacts", "Python 3.12.12, SWI 10.1.14 and Janus 1.5.3; locked packages; fresh native objects and venv."),
        (1064,"3 · RUN","Exercise the seam", "Both bridges and PeTTa evaluate; native baseline precedes the 13 actual caller cases.")]:
        s.box(x,257,464,294,title,body,"teal","white",tag=tag,title_size=31,body_size=27)
        if x<1064:s.line(x+464,405,x+490,405,C["teal"],arrow=True)
    s.box(72,600,704,137,"Warm-cache assumptions are explicit", "Python/uv and Cargo downloads reused; native pip install used --no-cache.","amber","sand",title_size=28,body_size=25)
    s.box(800,600,728,137,"Clean DeTTa was rebaselined", "Historical dirty bytes remain historical; fresh stores and all applicable tests were rerun.","blue","ice",title_size=28,body_size=25)
    note(s,"Source obtainability, buildability and a passing integration are separate questions. Authorized SSH fetches retrieved the exact Hive and DeTTa commits. Public pinned PeTTa/SWI sources and SWI submodule commits identify native inputs. The native build took 139.595 seconds on the recorded host; it observed Prolog-to-Python 42, Python-to-Prolog 2, and a generated PeTTa expression 42. It compiled a private SWI prefix and installed hash-locked dependencies, rebuilding Janus with --no-cache against that prefix. No prior venv, target or binary was copied. Python and Cargo download caches were warm; an entirely empty-cache build is unrun. The CMake cache-type guard and inherited virtual-environment issue were corrected and recorded. The verifier-only import-order correction was obtained by Git fast-forward before the final tests. None of these engineering choices changes upstream source or implies production deployment portability.")

    s = Slide("Nine required gates passed; chain remains unrun", "04 / Gate-by-gate outcome",
              "A fixture pass never substitutes for a real-provider or native-runtime pass.",source="evidence/m1_2/manifest.json")
    gates=[("BASELINE","Initial applicable suites executed"),("HIVE_SOURCE","Intended source and native entrypoint verified"),
           ("FIXTURE_REPRO","Fresh fixture-only run without real sources"),("DETTA_REPRO","Fresh clean provider build and conformance"),
           ("HIVE_ENTRYPOINT","Real authentication and Programs dispatch"),("HIVE_DETTA","Same workflow uses real DeTTa receipts"),
           ("HIVE_RECOVERY","Restart, replay, completion and refusals"),("HIVE_REPRO","Declared fresh source/build recipe exercised"),
           ("SCOPE","No M2, ECAN, inference control or migration"),("CHAIN","No same-artifact M1.2 chain submission")]
    for i,(name,desc) in enumerate(gates):
        x=72+(i%2)*744;y=247+(i//2)*105
        status=RECORD['gates'][name].split(':')[0]
        color='amber' if status=='NOT_RUN' else 'teal'
        s.rect(x,y,712,91,C['sand'] if color=='amber' else C['white'],radius=10)
        s.text(x+20,y+14,480,name,23,C['ink'],'bold')
        s.text(x+550,y+14,146,status,22,C[color],'bold')
        s.text(x+20,y+52,675,desc,21,C['muted'])
    band(s,"Historical chain reproduction is BLOCKED by missing exact F1R3 changes; empty-cache and full-Hive runs are NOT_RUN.",size=21)
    note(s,"This board is generated from the M1.2 manifest. All nine required gates pass within the documented local profile. CHAIN is NOT_RUN, not failed and not a fixture substitute. Historical F1R3 reproduction remains blocked for its undistributed dirty source and untracked input; it would need authorized exact changes or a separately validated clean rebaseline. That optional source distribution issue does not block Hive-to-DeTTa. Empty-cache builds and the full Hive suite are intentionally unrun. Source availability alone does not pass the entrypoint or real-provider gate. Executed failed attempts remain recorded separately from the final successful run.")

    s = Slide("The real caller is proven; the cognitive increment is next", "04 / Scope and stopping point",
              "M1.2 establishes an integration seam. It does not select a numerical model or implement cognition.",source="ADR 006–007 · m1_2-evidence.md")
    for x,tag,title,body,color,fill in [(72,"M0 / M1","Contract slice","Module map, opaque storage, messaging and deterministic delegation.","teal","mint"),
        (442,"M1.1","Owner boundaries","Independent AtomStorage replacement and separate durable commits.","teal","mint"),
        (812,"M1.2","Real native caller","Verified Hive operation, durable caller recovery and fresh-source recipe.","teal","mint"),
        (1182,"M2+ · NOT STARTED","Cognitive work","Private episodes and reviewed revision; later attention and bounded inference.","violet","lavender")]:
        s.box(x,253,346,289,title,body,color,fill,tag=tag,title_size=29,body_size=26,dashed=color=='violet')
    for x,title,body in [(72,"Production boundaries","Isolation, authorization and distributed custody remain separate work."),
                         (568,"Mathematical decisions","Revision model, lineage semantics, STI policy and specialists remain open."),
                         (1064,"State evolution","No live migration, populated-namespace switching or rolling upgrades.")]:
        s.text(x,602,455,title,27,C['ink'],'bold');s.text(x,653,455,body,25,C['muted'])
    note(s,"The stopping point moved from a missing Hive runtime to an evidenced native seam, without implementing M2. The next separately authorized increment can now be chosen from actual integration findings: private episodic provenance and explicitly profiled belief revision remain the cognitive roadmap, followed by attention and bounded inference. Existing upstream mathematics is not redefined here. Production transport/auth/isolation, distributed custody, independently verified proofs, performance characterization and live state migration remain outside this experiment. The minimal caller receipt is not a substitute for episodic memory. Do not describe the future entire Hive workflow or cognition as complete because one deterministic operation is integrated.")

    s = Slide("", "04 / Takeaway",source="M1.2 implementation bb22ef5 · evidence 4ee5cbe",dark=True)
    s.text(72,179,1390,"Modularity now survives\na real caller restart.",70,C['white'],'bold',1.16)
    s.text(78,399,1350,"The native integration preserves the original boundaries.",35,C['dim'])
    for i,(n,txt) in enumerate([("01","State changes through its owner."),("02","Providers remain replaceable by exact contract."),("03","Each receipt names an observed, bounded guarantee.")]):
        y=506+i*89;s.text(79,y,100,n,35,"77DDC4",'mono');s.text(191,y,1300,txt,32,C['white'])
    s.text(79,790,1350,"Real Hive + real local DeTTa   •   Fixture counterparty   •   Chain NOT_RUN   •   Stop before M2",21,C['dim'])
    note(s,"Close on the demonstrated change: a pinned real Hive runtime now invokes the same contracts and recovers across actual caller and worker process death. The consumer remains backend-independent, DA remains application-neutral, owner commits remain separate, and current authority still applies on replay. A fixture is labelled as a fixture; a historical chain observation does not become a new real-caller chain pass. The complete evidence, exact sources, build recipe and failure history are available in the repository. This presentation updates the explanation of completed M1.1/M1.2 work; it adds no runtime or cognitive implementation. Pause for discussion before the appendices.")

    s = Slide("Implementation map: adapt at the native boundary", "Appendix A / Code navigation",
              "Native-specific translation stays outside the backend-independent modules.",source="integration/hive/ · fusion/",appendix=True)
    s.box(72,245,430,134,"Native entrypoint", "Hive Programs.act\n→ integration/hive/program/program.py",'teal','mint',title_size=29,body_size=22)
    s.box(584,245,430,134,"Validated consumer", "Peer → Subprocess.invoke\n→ fusion.host rpc",'blue','ice',title_size=29,body_size=23)
    s.box(1096,245,432,134,"Trusted composition", "composition.py injects\nAtomStorage + CompletionDelivery",'blue',title_size=27,body_size=22)
    s.line(502,312,584,312,C['blue'],arrow=True);s.line(1014,312,1096,312,C['blue'],arrow=True)
    s.box(584,464,430,127,"Service facade", "service.py · policy.py\nregistry.py · responses.py",'blue',title_size=29,body_size=23)
    s.line(799,379,799,464,C['blue'],arrow=True)
    s.box(72,464,430,127,"Shared declarations", "ports.py · contracts.py\nSchemas and exact profiles",'ink',title_size=29,body_size=23)
    s.line(584,526,502,526,C['muted'],arrow=True)
    s.box(1096,464,432,127,"Separate owners", "atoms.py · messaging.py\nexecution.py",'blue',title_size=29,body_size=23)
    s.line(1014,526,1096,526,C['blue'],arrow=True)
    s.box(72,677,704,120,"Operator-only worker", "host.py work / flush; deterministic inspect_atom",'blue',title_size=28,body_size=23)
    s.box(824,677,704,120,"Selected provider", "detta.py + Rust helper OR independent fixture_atoms.py",'teal','mint',title_size=28,body_size=22)
    s.line(1312,591,1312,677,C['teal'],arrow=True)
    note(s,"The actual adapter is integration/hive/program/program.py, registered by plugin.json. It owns only the caller receipt. native_caller.py is a test transport around the unmodified app, not a runtime replacement. The plugin invokes the same public validated binding as protocol consumers. Service is an authenticated facade; owner logic is now in atoms.py, messaging.py and execution.py, not all in service.py as the original deck suggested. composition.py alone selects concrete owner implementations. Execution depends on AtomStorage and trusted CompletionDelivery. The file fixture is independent of AtomOwner. The original Rust opaque adapter remains unchanged. Chain composition remains separate and unrun by this native flow.")
    s = Slide("Specified cognitive contracts carry test obligations", "Appendix B / Review checklist",
              "These are future acceptance cases, not executed M1.2 tests.",source="ports.py · contracts.md",appendix=True)
    table(s,["Contract", "Semantic decision", "Named conformance obligations"],[
        ("Relations / Search", "Ordered roles; dialect + watermark", "REL-order / scope; SEARCH-watermark"),
        ("Episodes · M2", "Occurrence identity; sequence CAS", "EP-order / duplicate / contrary / privacy"),
        ("Belief revision · M2", "Numerical model; lineage; independence", "BR-overlap / cycle / contradiction / golden"),
        ("Attention · M3", "STI policy; logical time; budget; ties", "ECAN-no-PLN / owner / budget / decay"),
        ("PLN kernel · M3", "Rule version; ordered premise snapshots", "PLN-order / golden / purity / lineage"),
        ("Inference control · M3", "Candidate, rule, feedback, time limits", "IC-bounds / feedback / replay / swap")],[370,545,541],row_h=82,size=23)
    note(s,"Episode expected_sequence and belief expected_revision make concurrent updates explicit. Replayed evidence must not add weight; derived cycles and overlapping roots cannot manufacture independent support. Reachability's guarded trueagi-pln-stv-finite-k1/v1 implementation is a candidate for review, not a selected universal model. metta-attention exposes STI/LTI/VLTI and direct setters, so it cannot be silently advertised as the proposed STI-only policy. Attention requires a declared budget, saturation, conservation or nonconservation, decay and tie-breaking behavior. Inference control must bound feedback generations and work, and define durable checkpoint semantics before advertising crash safety. These obligations belong to future milestones; new cognitive services remain absent.")

    s = Slide("Typed failures preserve the caller’s recovery choices", "Appendix C / Error and retry semantics",
              "Unknown outcome is different from known rejection; an empty inbox is different from failure.",source="contracts.md · service.py",appendix=True)
    table(s,["Observation / error", "Meaning", "Caller action"],[
        ("NOT_FOUND", "No such scoped atom metadata", "Correct the reference"),
        ("NOT_AVAILABLE", "Known data / result temporarily unavailable", "Retry or query the owner"),
        ("OVERLOADED", "Capacity or current writer lock unavailable", "Back off; reuse key + semantic input"),
        ("CONFLICT", "Same key changed meaning / revision mismatch", "Reconcile; do not blindly replay"),
        ("UNAUTHORIZED / UNSUPPORTED_*", "Access or contract requirements fail", "Change authorization or requirements"),
        ("Transport loss", "Acceptance may already be durable", "Recover by key / job; do not assume failure")],[420,516,520],row_h=82,size=23)
    note(s,"Permanent-for-unchanged-request failures also include INVALID_ARGUMENT and DEADLINE_EXCEEDED. INTERNAL is reserved and not automatically retryable. NOT_AVAILABLE covers missing persisted DA for a known ref and queued results; NOT_FOUND is absent metadata. Overload never silently drops acknowledged work. When transport fails after acceptance, the caller can retry the same semantic mutation or query the job owner. Already accepted mutations recover their original receipt even after the deadline expires, while new admissions and worker starts still honor the deadline. Empty poll means an authorized, known-empty inbox; failures do not become empty recall results. Live policy still applies to retries.")


    s = Slide("Exact source identity includes the rebaseline", "Appendix D / Source ledger",
              "Commit prefixes are navigation aids; full SHAs, locks and clean-state checks are in the evidence.",source="m1_2/manifest.json · final-source-state.json",appendix=True)
    pins=NATIVE['source_pins']
    table(s,["Input", "Commit / version", "Use and source state"],[
        ("Fusion verification", BASE_COMMIT[:12], "Tested implementation; clean checkout"),
        ("Fusion evidence", EVIDENCE_COMMIT[:12], "Documentation/evidence descendant; same code"),
        ("omegahive-schematics",pins['schematics']['commit'][:12],"User-supplied runtime pointer"),
        ("PhysixSNET/omegahive",pins['repositories']['omegahive']['commit'][:12],"Clean native source; actual dispatch"),
        ("secured-contract-spaces",pins['repositories']['secured-contract-spaces']['commit'][:12],"Clean rebaseline; historical dirty bytes excluded"),
        ("PeTTa",pins['repositories']['PeTTa']['commit'][:12],"Clean native language runtime"),
        ("SWI / Python / Janus","10.1.14 / 3.12.12 / 1.5.3","Pinned native build; hashed Python lock")],[460,375,621],row_h=70,size=22)
    note(s,f"Full tested Fusion commit: {BASE_COMMIT}. Evidence snapshot: {EVIDENCE_COMMIT}. Hive {pins['repositories']['omegahive']['commit']}; clean DeTTa {pins['repositories']['secured-contract-spaces']['commit']}; PeTTa {pins['repositories']['PeTTa']['commit']}; SWI {pins['repositories']['swipl']['commit']}; schematics {pins['schematics']['commit']}. The native build used Fusion 1a627b0; only verifier import ordering changed before bb22ef5 verification. The final evidence descendant changes no implementation. Rust/Cargo 1.88.0, CMake 3.16.3, GCC 9.4.0 and uv 0.10.7 are recorded. Original supplied siblings remain unchanged. Historical F1R3 used a dirty tree at 9ec1096e1077 plus an untracked input; that historical source state is not distributed by the new recipe. The selected Hive revision is the one named by the supplied schematics, not a silent choice of remote HEAD.")

    s = Slide("Reproduce the selected gates from a fresh checkout", "Appendix E / Reproduction",
              "Authorized source access and warm Cargo/Python downloads are prerequisites; see the runbook.",source="runbook.md · build_hive.py · verify_m12.py",appendix=True)
    for y,label,line1,line2 in [(245,"BUILD PINNED NATIVE DEPENDENCIES", "uv run --python 3.11 --locked python", "  scripts/build_hive.py artifacts/native"),
                               (465,"VERIFY FIXTURES, REAL DETTA AND NATIVE HIVE", "uv run --python 3.11 --locked python", "  scripts/verify_m12.py artifacts/native/environment.json")]:
        s.rect(72,y,1456,187,C['dark'],radius=12)
        s.text(100,y+22,1380,label,19,"77DDC4",'bold')
        s.text(100,y+69,1380,line1+' \\',27,C['white'],'mono')
        s.text(100,y+117,1380,line2,27,C['white'],'mono')
    s.text(78,697,1430,"Fixture-only: uv run --python 3.11 --locked python scripts/verify_m11.py --fixture-only",23,C['ink'],'mono')
    band(s,"Read manifest.json, verification.json, hive-trace.json and the preserved failure logs before extending scope.",size=23)
    note(s,"Run both two-line commands from a fresh Fusion checkout at the evidence revision or a reviewed descendant. artifacts/native must be absent or empty: the build refuses to overwrite existing work. SSH must already authorize access to the exact Hive and DeTTa repositories and host keys must be established. Public PeTTa and SWI sources are fetched at full commits. Cargo uses offline locked downloads; the native pip step uses hashes and --no-cache and builds Janus for the private SWI prefix. No dependency target directory, venv or binary is copied from the original workspace. The verifier deliberately hides real source paths for fixture-only testing, then runs the four-way matrix, upstream DeTTa, native baseline and actual caller tests. Chain is separate and not run. The runbook explains Linux prerequisites, missing optional native headers, the CMake guard correction and cache population limits. Building this deck does not rerun those integration tests.")

    s = Slide("Historical M1: one result reached an isolated chain", "Appendix F / Historical evidence only",
              "This is the earlier protocol-peer artifact. The M1.2 Hive result was not submitted.",source="evidence/chain-demo.json · M1 historical",appendix=True)
    for x,label,body,color in [(72,"PENDING","Signed deploy accepted","amber"),(568,"INCLUDED","Block observed; effects pending","amber"),(1064,"FINALIZED","Deploy effects reported finalized","teal")]:
        s.box(x,258,464,150,label,body,color,'sand' if color=='amber' else 'mint',title_size=34,body_size=24)
        if x<1064:s.line(x+464,333,x+492,333,C['muted'],arrow=True)
    chain=HISTORICAL_CHAIN
    s.text(75,466,700,"M1 recorded observation",29,C['ink'],'bold')
    for i,(k,v) in enumerate([("Block height",str(chain['inclusion']['blockNumber'])),("Execution error","false"),("Rejection count","0"),("Execution cost","351 phlo")]):
        s.text(75,519+i*46,325,k,25,C['muted']);s.text(406,519+i*46,290,v,26,C['ink'],'bold')
    s.rect(785,452,743,255,C['white'],radius=13)
    s.text(811,477,680,"Historical commitment digest",27,C['ink'],'bold')
    s.text(811,531,680,chain['commitment'][:32]+'\n'+chain['commitment'][32:],24,C['teal'],'mono')
    s.text(811,625,680,"One local validator; direct node observations.\nNot a consensus proof or production test.",24,C['muted'])
    band(s,"M1.2 CHAIN = NOT_RUN. Historical source reproduction requires exact F1R3 changes or a separate rebaseline.",color='amber',fill='sand',size=22)
    note(s,"Preserve this historical result without promoting it into the new real-caller gate. The M1 chain JSON records pending, included with effect finality Pending, then finalized, at height 3 with no execution error, no rejection and cost 351 phlo. The committed digest belongs to the original protocol-peer result, not the generated native Hive result on slide 22. The M1 adapter used a registered approved digest, injected signer and durable signed intent against one isolated local node. That source had local changes and an untracked input. Exact historical reproduction remains blocked until those authorized bytes are supplied or a different clean revision is separately validated. No chain process or transaction was run during M1.2 or this presentation update. Finality does not establish indefinite off-chain availability.")

    s = Slide("Keep the guarantees inside their observed boundary", "Appendix G / Limits and unrun scope",
              "Local evidence is useful because the untested extensions remain explicit.",source="m1_2-evidence.md · manifest.json",appendix=True)
    table(s,["Observed", "Unrun / unsupported extension", "Why it matters"],[
        ("Same-host process restart", "Power loss / distributed failover", "Persistent files remained intact"),
        ("One logical accepted outcome", "Exactly-once physical execution", "Deterministic work may repeat"),
        ("Fresh-store provider swap", "Live state / journal migration", "Accepted refs and jobs are not moved"),
        ("Exact descriptor/profile binding", "Remote identity / verified proofs", "A hash checks consistency, not truth"),
        ("Fresh builds with declared caches", "Entirely empty-cache build", "Source access and downloads are prerequisites"),
        ("One deterministic native operation", "Full Hive suite / LLM / M2 cognition", "Dispatch evidence is not cognitive capability")],[474,490,492],row_h=80,size=23)
    note(s,"No new performance benchmark is presented. The original M1 single-sample timing chart has been removed from the current evidence story; those measurements remain in historical JSON. The native build and suite durations are reproducibility observations, not runtime latency or throughput claims. One local worker and one pending caller intent per dedicated route bound the tested profile. Production authorization, multi-host DA custody, generic external effects, live rolling upgrades, named-person/mind action paths, full Hive regression and all cognitive work remain unrun or unsupported. The deck makes no claim that rebuilding slides extends any integration guarantee.")


def rgb(hex_color):
    return RGBColor.from_string(hex_color)


def clear_theme_effects(shape):
    style = shape._element.find(qn("p:style"))
    if style is not None:
        shape._element.remove(style)
    shape._element.spPr.append(OxmlElement("a:effectLst"))


def export():
    HERE.mkdir(exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    svg_dir = HERE / "slides-svg"
    svg_dir.mkdir(exist_ok=True)
    prs = Presentation()
    prs.slide_width = Inches(13.333333)
    prs.slide_height = Inches(7.5)
    prs.core_properties.title = "Omega × ASI — One responsibility. One state owner."
    prs.core_properties.subject = "Through M1.2: module boundaries, native Hive, real DeTTa and restart evidence"
    prs.core_properties.author = "Omega × ASI module-interface project"
    prs.core_properties.keywords = "Omega, ASI, M1.1, M1.2, Hive, DeTTa, module interfaces, state ownership, recovery"
    pdf_path = HERE / "omega-asi-module-interfaces.pdf"
    pdf = canvas.Canvas(str(pdf_path), pagesize=(W*SCALE,H*SCALE), invariant=1)
    pdf.setTitle(prs.core_properties.title)
    pdf.setAuthor(prs.core_properties.author)
    notes = ["# Omega × ASI — speaker notes", "", f"Implementation baseline: `{BASE_COMMIT}`.",
             f"Evidence snapshot: `{EVIDENCE_COMMIT}`.",
             f"Suggested delivery: 30–35 minutes for slides 1–{MAIN_SLIDES}, with appendices for discussion.",
             "Current claims use the recorded 16 October 2026 M1.2 evidence. The M1 chain observation is historical and separately labelled.", ""]
    manifest=[]
    for index,s in enumerate(SLIDES,1):
        s.footer(index,len(SLIDES))
        text_items = [e for e in s.elements if e["kind"] == "text" and e["text"]]
        for aidx, a in enumerate(text_items):
            for b in text_items[aidx+1:]:
                right_a = a["x"] + width(a["text"], a["size"], a["style"])
                right_b = b["x"] + width(b["text"], b["size"], b["style"])
                overlap_x = min(right_a, right_b) - max(a["x"], b["x"])
                overlap_y = min(a["y"]+a["size"], b["y"]+b["size"]) - max(a["y"], b["y"])
                if overlap_x > 2 and overlap_y > 2:
                    raise ValueError(f"Text overlap on slide {index}: {a['text']} / {b['text']}")
        slide=prs.slides.add_slide(prs.slide_layouts[6])
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb=rgb(s.bg)
        pdf.setFillColor("#"+s.bg)
        pdf.rect(0,0,W*SCALE,H*SCALE,fill=1,stroke=0)
        svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900" role="img" aria-labelledby="title desc">',
             f'<title id="title">{html.escape(s.title or ("Omega × ASI" if index==1 else "Takeaway"))}</title>',
             f'<desc id="desc">{html.escape(s.notes)}</desc>',
             f'<rect width="1600" height="900" fill="#{s.bg}"/>']
        for e in s.elements:
            k=e["kind"]
            if k in ("rect","text"):
                if e["x"]<0 or e["y"]<0 or e["x"]+e["w"]>W+0.1 or e["y"]+e["h"]>H+0.1:
                    raise ValueError(f"Out of bounds slide {index}: {e}")
            if k=="rect":
                sh=slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if e["radius"] else MSO_SHAPE.RECTANGLE,
                    Pt(e["x"]*SCALE),Pt(e["y"]*SCALE),Pt(e["w"]*SCALE),Pt(e["h"]*SCALE))
                if e["radius"]:sh.adjustments[0]=min(0.3,e["radius"]/min(e["w"],e["h"]))
                sh.fill.solid();sh.fill.fore_color.rgb=rgb(e["fill"])
                if e["stroke"]:
                    sh.line.color.rgb=rgb(e["stroke"]);sh.line.width=Pt(SCALE)
                    if e["dash"]:sh.line.dash_style=MSO_LINE_DASH_STYLE.DASH
                else:sh.line.fill.background()
                clear_theme_effects(sh)
                pdf.setFillColor("#"+e["fill"])
                if e["stroke"]:pdf.setStrokeColor("#"+e["stroke"])
                pdf.setLineWidth(SCALE);pdf.setDash([5*SCALE,4*SCALE] if e["dash"] else [])
                pdf.roundRect(e["x"]*SCALE,(H-e["y"]-e["h"])*SCALE,e["w"]*SCALE,e["h"]*SCALE,e["radius"]*SCALE,fill=1,stroke=int(bool(e["stroke"])))
                stroke=f' stroke="#{e["stroke"]}"' if e["stroke"] else ""
                dash=' stroke-dasharray="5 4"' if e["dash"] else ""
                svg.append(f'<rect x="{e["x"]}" y="{e["y"]}" width="{e["w"]}" height="{e["h"]}" rx="{e["radius"]}" fill="#{e["fill"]}"{stroke}{dash}/>')
            elif k=="text":
                # Every line is pre-wrapped with the embedded PDF font metrics.
                tx=slide.shapes.add_textbox(Pt(e["x"]*SCALE),Pt(e["y"]*SCALE),Pt(e["w"]*SCALE),Pt(e["h"]*SCALE))
                tf=tx.text_frame
                tf.margin_left=tf.margin_right=tf.margin_top=tf.margin_bottom=0
                tf.word_wrap=False;tf.vertical_anchor=MSO_ANCHOR.TOP
                tf.auto_size=MSO_AUTO_SIZE.NONE
                tf._txBody.bodyPr.set("anchorCtr", "0")
                p=tf.paragraphs[0];p.space_before=p.space_after=Pt(0)
                p.alignment=PP_ALIGN.LEFT
                p.line_spacing=1.0
                r=p.add_run();r.text=e["text"]
                r.font.name=FONTS[e["style"]][1].replace("DejaVuSansMono","DejaVu Sans Mono").replace("DejaVuSans","DejaVu Sans")
                r.font.size=Pt(e["size"]*SCALE);r.font.bold=e["style"]=="bold";r.font.color.rgb=rgb(e["color"])
                pdf.setFillColor("#"+e["color"]);pdf.setFont(FONTS[e["style"]][0],e["size"]*SCALE)
                baseline=e["y"]+e["size"]*0.95
                pdf.drawString(e["x"]*SCALE,(H-baseline)*SCALE,e["text"])
                family="DejaVu Sans Mono" if e["style"]=="mono" else "DejaVu Sans"
                svg.append(f'<text x="{e["x"]}" y="{baseline}" font-family="{family}" font-size="{e["size"]}" font-weight="{700 if e["style"]=="bold" else 400}" fill="#{e["color"]}">{html.escape(e["text"])}</text>')
            elif k=="line":
                sh=slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,Pt(e["x1"]*SCALE),Pt(e["y1"]*SCALE),Pt(e["x2"]*SCALE),Pt(e["y2"]*SCALE))
                sh.line.color.rgb=rgb(e["color"]);sh.line.width=Pt(e["thick"]*SCALE)
                clear_theme_effects(sh)
                if e["dash"]:sh.line.dash_style=MSO_LINE_DASH_STYLE.DASH
                pdf.setStrokeColor("#"+e["color"]);pdf.setLineWidth(e["thick"]*SCALE);pdf.setDash([6*SCALE,5*SCALE] if e["dash"] else [])
                pdf.line(e["x1"]*SCALE,(H-e["y1"])*SCALE,e["x2"]*SCALE,(H-e["y2"])*SCALE)
                dash=' stroke-dasharray="6 5"' if e["dash"] else ""
                svg.append(f'<line x1="{e["x1"]}" y1="{e["y1"]}" x2="{e["x2"]}" y2="{e["y2"]}" stroke="#{e["color"]}" stroke-width="{e["thick"]}"{dash}/>')
            elif k=="polygon":
                points=e["points"]
                ff=slide.shapes.build_freeform(points[0][0],points[0][1],scale=Pt(SCALE))
                ff.add_line_segments(points[1:],close=True)
                sh=ff.convert_to_shape();sh.fill.solid();sh.fill.fore_color.rgb=rgb(e["fill"]);sh.line.fill.background()
                clear_theme_effects(sh)
                p=pdf.beginPath();p.moveTo(points[0][0]*SCALE,(H-points[0][1])*SCALE)
                for x,y in points[1:]:p.lineTo(x*SCALE,(H-y)*SCALE)
                p.close();pdf.setFillColor("#"+e["fill"]);pdf.drawPath(p,fill=1,stroke=0)
                svg.append(f'<polygon points="{" ".join(f"{x},{y}" for x,y in points)}" fill="#{e["fill"]}"/>')
        slide.notes_slide.notes_text_frame.text=s.notes+"\n\nSource: "+s.source
        svg.append("</svg>")
        (svg_dir/f"{index:02d}.svg").write_text("\n".join(svg)+"\n")
        pdf.showPage()
        title=s.title or ("One responsibility. One state owner. Many possible backends." if index==1 else "Modularity now survives a real caller restart.")
        notes += [f"## {index:02d} — {title}","",s.notes,"",f"Source: `{s.source}`.",""]
        manifest.append(dict(slide=index,title=title,section=s.section,appendix=s.appendix,source=s.source,
                             text_elements=sum(e["kind"]=="text" for e in s.elements),
                             editable_shapes=len(s.elements)))
    pdf.save()
    pptx_path=HERE/"omega-asi-module-interfaces.pptx"
    prs.save(pptx_path)
    (HERE/"speaker-notes.md").write_text("\n".join(notes))
    # Validate all pages, render all slides, and make contact sheets for visual review.
    doc=fitz.open(pdf_path)
    if len(doc)!=len(SLIDES) or len(Presentation(pptx_path).slides)!=len(SLIDES):
        raise ValueError("Page count mismatch")
    previews=[]
    for i,page in enumerate(doc):
        if len(page.get_text().strip())<50:raise ValueError(f"Empty PDF page {i+1}")
        pix=page.get_pixmap(matrix=fitz.Matrix(1.2,1.2),alpha=False)
        path=QA/f"slide-{i+1:02d}.png";pix.save(path)
        im=Image.open(path).convert("RGB");im.thumbnail((480,270));previews.append(im)
    for offset in range(0,len(previews),9):
        sheet=Image.new("RGB",(1488,915),"#D5DCE0");d=ImageDraw.Draw(sheet)
        for j,im in enumerate(previews[offset:offset+9]):
            x=12+(j%3)*492;y=22+(j//3)*300
            sheet.paste(im,(x,y));d.text((x,y+274),f"Slide {offset+j+1:02d}",fill="#102B3F")
        sheet.save(QA/f"contact-{offset//9+1}.png")
    checks=dict(slides=len(SLIDES),pptx_reopened=True,pdf_pages_rendered=len(doc),
                layout_bounds_checked=True,text_overlaps=0,fonts="DejaVu Sans / DejaVu Sans Mono (PDF embedded; TTFs bundled)",
                independent_renderer_check="Recorded separately in qa.json",source_commit=BASE_COMMIT,
                evidence_commit=EVIDENCE_COMMIT,main_talk_slides=MAIN_SLIDES,
                evidence_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in EVIDENCE_FILES},slides_manifest=manifest)
    (HERE/"build-manifest.json").write_text(json.dumps(checks,indent=2)+"\n")
    print(json.dumps({"slides":len(SLIDES),"pdf":str(pdf_path),"pptx":str(pptx_path),"qa":str(QA)},indent=2))


if __name__=="__main__":
    build_content()
    export()
