"""Build an editable PowerPoint, vector PDF/SVG, notes and a visual QA contact sheet.

One measured layout drives every format. No application code or runtime state is
changed. Presentation dependencies are separate from the conformance environment.
"""
from __future__ import annotations

import hashlib
import html
import json
import math
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
DEMO = json.loads((EVIDENCE / "demo.json").read_text())
CHAIN = json.loads((EVIDENCE / "chain-demo.json").read_text())
BASE_COMMIT = "3f75db993d354d18dff2a3e36498eabe4a33afb3"
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
        self.text(72, 853, 1120, f"OMEGA × ASI   /   M0–M1   /   {self.source}", 15, color)
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
    s = Slide("", "Module-interface architecture", source="brief + implementation commit 3f75db9", dark=True)
    s.text(72, 169, 1330, "One responsibility.\nOne state owner.\nMany possible backends.", 78, C["white"], "bold", 1.12)
    s.text(76, 482, 1250, "Omega Hive × ASI:chain", 42, C["dim"])
    s.text(76, 550, 1290, "From a module map to a working storage, messaging and execution slice", 31, C["white"])
    s.tag(76, 676, "M0 + M1 COMPLETE", "teal", C["mint"], 20)
    s.tag(366, 676, "M2 NOT STARTED", "violet", C["lavender"], 20)
    s.text(76, 754, 1300, "Architecture review • 16 October 2026 • proposed v0 contracts", 22, C["dim"])
    note(s, "This talk explains how independently implemented modules can cooperate without taking ownership of each other's state. Start with the helicopter view, then module responsibilities and function dependencies. Only after those boundaries are clear do we examine the running M1 slice. M0 and the bounded local M1 integration are complete. M2 and the cognitive stack are explicitly outside the completed work. These contracts are proposed engineering choices, not a finalized community AtomSpace specification. Suggested delivery: 25–30 minutes for slides 1–24; remaining slides are discussion material.")

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
    s.text(75, 630, 1400, "M1 demonstrates one narrow path through that architecture", 30, C["ink"], "bold")
    labels = ["STORE", "SHARE REF", "FETCH", "DELEGATE", "RECOVER", "COMMIT DIGEST"]
    for i, label in enumerate(labels):
        x = 72+i*248
        s.rect(x, 696, 216, 66, C["mint"] if i < 5 else C["sand"], radius=8)
        s.text(x+16, 718, 190, label, 20, C["teal"] if i < 5 else C["amber"], "bold")
        if i < 5:
            s.line(x+218, 729, x+243, 729, arrow=True)
    note(s, "The three commitments are the architecture's thesis. Behavior means operation semantics and guarantees, not merely a matching method name. Ownership means only an owner's methods may mutate its state, even when modules share a database. Evidence means a stored payload, an accepted job, an acknowledged message and a finalized chain deploy remain different facts. The M1 path below is a conformance experiment using two protocol peers, actual DeTTa libraries, a separate worker and an optional real local chain runtime.")

    s = Slide("Fifteen modules; four responsibility groups", "01 / System map",
              "Logical boundaries are independent of process and repository boundaries.")
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
    s.box(1216, 485, 294, 168, "Consensus / finality", "Real isolated F1R3 node", "teal", title_size=26, body_size=22)
    s.text(866, 649, 282, "Local harness policy\nand static descriptors", 20, C["muted"])
    s.tag(72, 760, "SPECIFICATION ONLY", "violet", C["lavender"])
    s.tag(374, 760, "IMPLEMENTED HARNESS", "blue", C["ice"])
    s.tag(713, 760, "REAL PROVIDER INTEGRATION", "teal", C["mint"])
    note(s, "This is the placement map, not a process topology. All fifteen modules from the brief appear here. The five cognitive modules plus Relations and Search are specifications only. Blue modules are implemented by the local harness; Authorization is explicitly a test policy. Teal shows actual provider integration: local DeTTa DA/storage libraries and a real isolated single-validator F1R3node. Consensus/finality includes the bounded commitment adapter. Private episodic history belongs on the client in future work. A module may be co-located with another module without surrendering its state boundary. The actual Hive runtime was unavailable, so no box here implies a running Hive agent.")

    s = Slide("Data responsibilities: bytes → references → history", "01 / Responsibility atlas · 1 of 3",
              "The first five modules separate persistence, identity, structure, discovery and provenance.")
    table(s, ["Module", "Function / primary operations", "Owned state / status"], [
        ("DA storage", "Persist opaque bytes\nput · get · availability", "Payloads and shares\nREAL LOCAL PROVIDER"),
        ("AtomStorage", "Assign scoped immutable references\ncreate · get · getMany", "Reference + replay metadata\nIMPLEMENTED"),
        ("Relations", "Represent ordered structural roles\nassertRelation · getRelation", "Immutable relation records\nSPECIFIED"),
        ("Search projection", "Find references at a known watermark\nquery", "Rebuildable index\nSPECIFIED"),
        ("Episodic memory", "Preserve ordered events + provenance\nrecordEpisode · appendEvent", "Private episode history\nSPECIFIED · M2")], [330, 600, 526], row_h=92, size=25)
    band(s, "Capture and retrieve data before choosing its meaning.")
    note(s, "DA persists opaque payloads and erasure shares. AtomStorage owns the application reference metadata, immutable revision and semantic replay keys. Relations describe explicit ordered roles; a link is not automatically a belief. Search is a rebuildable projection that exposes its watermark, not the authoritative store. Episodic memory adds occurrence identities and episode-local ordering, so equal payload bytes may describe different observations. Its full private history remains client-side. This design deliberately does not require a parser, ontology, embedding model or LLM just to store data. Additional relation operations are outgoing/incoming; episode reads are readEpisode/findEpisodes. Those contracts are specified but have no M1 runtime.")

    s = Slide("Cognitive responsibilities: history ≠ truth ≠ attention", "01 / Responsibility atlas · 2 of 3",
              "All four modules below are typed specifications. No cognitive provider runs in M1.")
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
        ("Consensus / finality", "Submit approved commitment; observe\nsubmit · observe", "Signed intent journal · REAL LOCAL CHAIN"),
        ("Authorization", "Check current caller + scope + method\nauthorize / live policy checks", "Server-owned policy · LOCAL FIXTURE")], [330, 590, 536], row_h=82, size=23)
    note(s, "Messaging owns accepted inbox entries and acknowledgements. Execution owns jobs and its outbox, and only accepts inspect_atom in M1. Registry is a static provider catalogue, not capability authority or chain registration; the resolver is a pure selection function over those descriptors. Finality is a separate bounded adapter with a registered approved commitment, durable signed intent and direct node observations. It does not establish belief confidence, execution success or indefinite availability. Authorization reads current server-owned policy from authenticated transport context; the implemented policy is a fixture for the trusted local harness. No caller-supplied sender field grants authority.")

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

    s = Slide("Function dependencies: admission, work and delivery", "01 / Dependency map · runtime control",
              "Resolve once per configured capability; authorize every invocation.", source="client.py · service.py · registry.py")
    s.box(72, 254, 270, 120, "Client + setup", "store · share · delegate", "blue", title_size=28, body_size=22)
    s.box(463, 254, 320, 120, "Resolver", "resolve(requirement)", "blue", title_size=28, body_size=23)
    s.box(905, 254, 320, 120, "Registry", "descriptors(binding)", "blue", title_size=28, body_size=23)
    s.line(342, 312, 463, 312, arrow=True)
    s.line(905, 312, 783, 312, dash=True, arrow=True)
    s.text(795, 276, 110, "offers", 20, C["muted"])
    s.box(72, 478, 270, 125, "Authorization", "caller · scope · operation", "blue", "ice", title_size=26, body_size=22)
    s.line(207, 374, 207, 478, C["blue"], arrow=True)
    s.text(225, 409, 520, "binding → validated dispatch", 22, C["muted"])
    s.box(463, 478, 320, 125, "Execution", "submit · status · result", "blue", title_size=28, body_size=23)
    s.box(905, 478, 320, 125, "AtomStorage", "get(input) · create(result)", "blue", title_size=28, body_size=21)
    s.line(342, 541, 463, 541, C["blue"], arrow=True)
    s.line(783, 541, 905, 541, C["blue"], arrow=True)
    s.box(463, 689, 320, 94, "Messaging", "send → poll → ack", "blue", title_size=25, body_size=21)
    s.line(623, 603, 623, 689, C["blue"], arrow=True)
    s.text(647, 631, 270, "durable outbox → inbox", 20, C["muted"])
    s.box(1271, 478, 257, 125, "DA storage", "put · get", "teal", "mint", title_size=25, body_size=22)
    s.line(1225, 541, 1271, 541, C["teal"], arrow=True)
    s.box(997, 689, 531, 94, "Consensus / finality", "submit(approved digest) · observe", "teal", title_size=25, body_size=21)
    s.text(1255, 270, 277, "Optional separate caller\n+ registered approval\n+ injected signer", 23, C["muted"])
    s.path([(1390, 384), (1550, 384), (1550, 736), (1528, 736)], C["teal"])
    note(s, "Demo setup resolves suitable descriptors, then Peer invokes the configured binding. The dashed offers arrow supplies descriptor data to the resolver. Each service invocation validates the wire envelope and checks the current local policy before the explicit dispatch allowlist. This diagram focuses on delegated execution; direct store and messaging calls pass through the same authorization boundary. Worker execution calls the atom owner to read inputs and create a persisted result. Completion goes through a durable outbox into the message owner's inbox; poll/ack are recipient-owned operations. The chain adapter is a separate optional consumer of one approved result digest. It is not on the mandatory storage or execution path. Scope/method checks also apply to worker reads and completion delivery. The static resolver does not grant permissions.")

    s = Slide("State ownership survives co-location", "02 / Design details · authority",
              "A shared database is a deployment choice. Its tables still have different writers.", source="architecture.md · ADR 002–004")
    s.text(75, 245, 660, "M1: TRUSTED LOCAL SERVICE", 20, C["blue"], "bold")
    s.rect(72, 290, 884, 354, C["ice"], radius=15)
    for i, (title, state) in enumerate([("Atom owner", "refs · mutations"), ("Message owner", "inbox · acknowledgements"), ("Execution owner", "jobs · completion outbox")]):
        x = 94+i*286
        s.box(x, 315, 264, 140, title, state, "blue", title_size=25, body_size=22)
        s.line(x+132, 455, x+132, 509, C["blue"], arrow=True)
    s.rect(94, 510, 834, 104, C["white"], C["blue"], 10)
    s.text(124, 532, 750, "SQLite FULL / WAL", 30, C["ink"], "bold")
    s.text(124, 574, 750, "Owned transitions serialize through one writer", 23, C["muted"])
    s.box(1010, 290, 518, 160, "Payload authority", "DeTTa FileStorage owns the bytes and erasure shares.", "teal", "mint", title_size=30, body_size=25)
    s.box(1010, 481, 518, 163, "Future private client state", "Episodes, beliefs and attention stay behind their respective owner ports.", "violet", "lavender", title_size=28, body_size=24, dashed=True)
    band(s, "External callers receive methods and receipts; they receive no table or owner setters.")
    note(s, "M1 uses one SQLite journal to keep the example small. That journal stores several logically owned categories: atom metadata, messaging inbox state, execution jobs and outbox, plus replay records. Public dispatch only exposes declared operations, never raw SQL, worker controls or setters for another owner. Shared storage therefore does not erase responsibility boundaries. DA payloads and erasure shares live in actual DeTTa FileStorage outside SQLite. In future work, private episode history remains client-side, and truth or attention can change only through the relevant owner. This is logical ownership, not a claim of multi-tenant process isolation against the same OS user.")

    s = Slide("Keep four architecture choices independent", "02 / Design details · substitution",
              "Changing placement must not silently change the meaning of an operation.", source="ADR 004–005 · bindings.py")
    rows = [("INTERFACE", "What behavior is promised?", "atom.storage / immutable-bytes/1", "blue"),
            ("IMPLEMENTATION", "Who provides that behavior?", "AtomOwner + injected DeTTa adapter", "teal"),
            ("TRANSPORT", "How does a caller cross the boundary?", "In-process call or private JSON stdio", "blue"),
            ("PLACEMENT", "Where does the implementation run?", "Trusted local service; optional chain adapter", "amber")]
    for i, (label, question, example, color) in enumerate(rows):
        y = 254+i*116
        s.rect(72, y, 1456, 100, C["white"], radius=10)
        s.rect(72, y, 8, 100, C[color])
        s.text(101, y+33, 290, label, 24, C[color], "bold")
        s.text(405, y+20, 520, question, 27, C["ink"], "bold")
        s.text(971, y+23, 520, example, 26, C["muted"])
    band(s, "Only composition imports concrete adapters. Domain contracts stay backend-neutral.")
    note(s, "A service contract is an interface, not necessarily a blockchain smart contract. One module can run in process, behind a message boundary or through an inspected chain API, provided the profile and required behavior are preserved. The current proof runs identical Peer consumer code under in-process and subprocess service bindings. Both still use real DA helper processes and separate workers. This demonstrates a transport substitution within the local composition; it does not demonstrate an alternate DA provider or a distributed deployment. Constructor/composition code imports concrete adapters. The typed domain ports do not depend on DeTTa, F1R3, PLN or ECAN implementations.")

    s = Slide("Compatibility is a semantic filter", "02 / Design details · resolution",
              "A matching name is only the start of provider selection.", source="registry.py · test_adapters.py")
    labels = [("Version", "Explicit same-major range"), ("Profile", "Exact semantics + features"),
              ("Operations", "Required calls available"), ("Guarantees", "Durability, privacy, limits")]
    for i, (title, body) in enumerate(labels):
        x = 72+i*370
        s.box(x, 280, 346, 189, title, body, "blue", "white", title_size=33, body_size=27)
        if i < 3:
            s.line(x+346, 376, x+365, 376, C["blue"], arrow=True)
    s.box(72, 524, 704, 180, "Required proof? Fail closed.", "No verifier is installed. A proof-shaped field cannot satisfy a verification requirement.", "amber", "sand", title_size=30, body_size=27)
    s.box(800, 524, 728, 180, "Actual wire version: 1.0.0", "Additive 1.2.3 compatibility is a resolver fixture, not an available wire provider.", "blue", "ice", title_size=30, body_size=27)
    note(s, "The resolver filters interface identity and a consumer's explicit same-major interval, exact profile and required features, supported operations, advertised guarantees, payload limits and privacy. Any required measured latency must be present in descriptor measurements. Required verification always fails because no verifier is available. Advertisements and evidence remain distinct. The actual M1 dispatch only accepts wire 1.0.0. A separate descriptor fixture at 1.2.3 exercises additive resolution; it is not evidence of a deployed 1.2.3 service. Unsupported requirements produce typed errors instead of weaker fallback selection. Interface 1.0.0 stabilizes this prototype, not an agreed community standard.")

    s = Slide("Identity, replay and authority travel separately", "02 / Design details · invocation",
              "The invocation names an operation; trusted context identifies the caller.", source="contracts.py · wire.schema.json")
    s.rect(72, 245, 750, 476, C["dark"], radius=15)
    example = ["interface_ref: atom.storage@1.0.0", "profile: immutable-bytes/1", "operation: create", "scope_ref: shared-test", "message_id: delivery-042", "idempotency_key: capture-007", "body: {content_type, bytes, sharing}"]
    for i, line in enumerate(example):
        s.text(102, 276+i*53, 696, line, 24, C["white"] if i != 5 else "77DDC4", "mono")
    s.text(102, 665, 680, "Illustrative field view · not a literal wire request", 19, C["dim"])
    s.box(870, 245, 658, 132, "Occurrence ≠ content", "Identical bytes can be distinct observations.", "ink", title_size=30, body_size=26)
    s.box(870, 405, 658, 132, "Retry ≠ new mutation", "Same key + semantic input recovers the same effect.", "ink", title_size=30, body_size=26)
    s.box(870, 565, 658, 156, "Scope identifier ≠ permission", "Live policy uses the authenticated principal. Correlation + reply route make async work traceable.", "ink", title_size=29, body_size=25)
    note(s, "This is an illustrative field view, not a copy-paste wire JSON request. The actual schema is contracts/wire.schema.json. Immutable AtomRef identifies a scoped record with revision and integrity digest; the digest does not grant permission or establish truth. A mutation key is scoped by principal, scope, interface and operation, and bound to semantic input. Changing the body, routing or deadline with the same key is a conflict. Message ID and causation are delivery metadata. Async send/submit include correlation and an authorized reply route. Trusted transport supplies the opaque credential, which current service policy maps to a principal. The body cannot nominate its own authority.")

    s = Slide("One slice crosses real process and storage boundaries", "03 / Running integration · end-to-end",
              "Two independent protocol peers. One allowlisted operation. Two interchangeable service bindings.", source="scripts/demo.py · evidence/demo.json")
    xs = [120, 438, 756, 1074, 1392]
    for x, label in zip(xs, ["Peer A", "Owners", "Peer B", "Worker", "DeTTa"]):
        s.rect(x-75, 236, 150, 52, C["mint"] if label=="DeTTa" else C["ice"], radius=8)
        s.text(x-62, 251, 140, label, 22, C["teal"] if label=="DeTTa" else C["blue"], "bold")
        s.line(x, 300, x, 763, C["line"], dash=True)
    steps = [(120,438,"1  create fixture",332),(438,1392,"2  persist bytes → scoped ref",385),
             (120,756,"3  share ref through durable mailbox",438),
             (756,438,"4  get(ref) → identical bytes",491),
             (120,438,"5  submit inspect_atom → durable acceptance",544),
             (1074,1392,"6  read + compute + persist",597),
             (1074,438,"7  commit result + completion outbox",650),
             (120,438,"8  restart → status / result / poll / ack",719)]
    for x1,x2,label,y in steps:
        left = min(x1,x2)
        s.text(left+12, y-28, min(max(abs(x2-x1), 630), 1515-left), label, 20, C["ink"])
        s.line(x1, y, x2, y, C["teal"] if y in (385,597) else C["blue"], 2, arrow=True)
    note(s, "The arrows summarize the logical sequence; reads and writes from the worker pass through the atom/storage adapter, even when omitted for clarity. Peer A creates a generated 62-byte fixture through AtomStorage into real DeTTa. It sends the reference through the durable mailbox. Peer B receives it and fetches exactly the same bytes. A submits inspect_atom; the separate worker reads the referenced bytes and returns their digest and length. The demo kills the worker twice at persisted boundaries, restarts, then recovers a correlated completion and result. Every acknowledgement refers to its stated durability scope. Both service bindings use the same Peer code and validation. The peers and operation are fixtures, not Omega agents or reasoning.")

    s = Slide("A receipt proves one fact at one boundary", "03 / Running integration · evidence model",
              "These observations are independent. They are not one universal success state.", source="contracts.md · evidence.md")
    cards = [(72,252,"STORAGE","Payload persisted","Local shares; declared durability", "teal"),
             (568,252,"MESSAGING","Message accepted","Delivery repeats until recipient ack", "blue"),
             (1064,252,"EXECUTION","Result committed","Job result + completion outbox", "blue"),
             (72,502,"CHAIN SUBMISSION","Signed intent accepted","Deploy ID; outcome still pending", "amber"),
             (568,502,"CHAIN INCLUSION","Deploy observed in block","Block ID; effects may be pending", "amber"),
             (1064,502,"CHAIN FINALITY","Effects reported finalized","Node observation + evidence", "teal")]
    for x,y,tag,title,body,color in cards:
        s.box(x,y,464,210,title,body,color,"white",tag=tag,title_size=29,body_size=25)
    band(s, "Finality does not establish indefinite availability of off-chain bytes.", color="amber", fill="sand")
    note(s, "Avoid turning this grid into a linear distributed transaction. A result can be durable before a chain commitment exists; messaging can be delayed while result retrieval already works. Payload persistence is qualified by its local durability scope. Mailbox acceptance is different from recipient acknowledgement. Execution completion is different from whether its outbox was delivered. Chain submission yields a deploy ID, inclusion yields a block observation and effect finality comes from the specific inspected endpoint. A finalized digest does not prove a payload will remain available, nor does any of these receipts establish belief confidence. This separation is central to both interfaces and reporting.")

    s = Slide("Crash recovery is a replay protocol", "03 / Running integration · durability",
              "SQLite and DA do not share an atomic commit. The gap is handled explicitly.", source="ADR 003 · test_contract.py")
    stages = [(72, "Accept job", "SQLite commit"), (442, "Persist result", "Real DA write"),
              (812, "Complete job", "Result + outbox commit"), (1182, "Deliver reply", "Inbox + outbox commit")]
    for i,(x,title,body) in enumerate(stages):
        s.box(x,275,346,139,title,body,"blue" if i!=1 else "teal",title_size=29,body_size=24)
        if i<3:
            s.line(x+346,344,x+365,344,C["blue"],arrow=True)
    for x,num,title,body in [(90,"A","Before acceptance reply","Retry recovers the accepted job."),
                             (556,"B","After DA write","Replay reuses the same coordinate; an unreferenced artifact may remain."),
                             (1030,"C","Before dispatch","The persisted outbox survives and later reaches the inbox.")]:
        s.tag(x,462,f"SIGKILL {num}","red",C["blush"],20)
        s.text(x,521,420,title,29,C["ink"],"bold")
        s.text(x,610,420,body,27,C["muted"])
    band(s,"One logical result; physical computation may repeat. Tested failure model: same-host process death.",size=25)
    note(s,"The three tested fault boundaries are acceptance committed before a response, DA result persisted before the completion transaction, and completion committed before dispatch. The demo itself performs the latter two worker kills; the contract suite also tests the acceptance-reply boundary. Deterministic storage coordinates and semantic deduplication let an attempt replay without a second logical result. A DA write before journal commit can leave an unreferenced artifact: there is no cross-store atomicity claim. Result metadata, job completion and outbox intent commit together in SQLite; inbox delivery and outbox completion also commit together. A full or revoked reply route keeps completion pending. These tests cover SIGKILL on the same host, not power loss, disk loss, Byzantine behavior or exactly-once physical computation.")

    s = Slide("The DA boundary carries bytes, not cognition", "03 / Running integration · storage",
              "The application adapter is outside the unchanged DeTTa core.", source="adapters/detta/src/main.rs · test_adapters.py")
    s.box(72,253,450,164,"Application contracts","AtomRef · scope · semantic replay", "blue", "ice",title_size=31,body_size=27)
    s.box(619,253,405,164,"External adapter","Opaque payload + generic coordinate", "teal","mint",title_size=31,body_size=25)
    s.box(1121,253,407,164,"DeTTa core","DA encoding + FileStorage", "teal","mint",title_size=31,body_size=26)
    s.line(522,335,619,335,C["teal"],arrow=True)
    s.line(1024,335,1121,335,C["teal"],arrow=True)
    s.text(75,477,1000,"4 data shares + 2 parity shares",38,C["ink"],"bold")
    for i in range(6):
        x=74+i*153
        missing=i>=4
        s.rect(x,555,125,115,C["pale"] if missing else C["mint"],C["line"] if missing else C["teal"],10,missing)
        s.text(x+31,580,90,f"S{i+1}",35,C["muted"] if missing else C["teal"],"mono")
        s.text(x+16,631,110,"removed" if missing else "present",17,C["muted"])
    s.box(1060,506,468,195,"Observed reconstruction","Cached payload + 2 shares removed: exact bytes recovered. Third missing share: unavailable.","teal",title_size=28,body_size=25)
    band(s,"No Omega IDs, truth values, ECAN balances or job state inside the generic DA schema.",size=25)
    note(s,"The Rust helper links actual detta-da and detta-storage from the inspected working tree. It maps bytes into an opaque application profile and binds the scope through generic coordinate metadata. The generic DA schema remains application-neutral; Omega-specific reference metadata lives above it. Reads reconstruct and verify persisted Reed–Solomon shares rather than retrieving a cached copy from SQLite. Tests remove the cached full payload and two of six shares and still recover exact bytes. A third missing share and corrupted-share cases fail explicitly; the tests do not establish an exhaustive adversarial-correction guarantee. This is real local library integration, not a running distributed validator/custody network. No certificate or remote replication guarantee is fabricated.")

    s = Slide("Authorization is checked where state is owned", "03 / Running integration · isolation",
              "Authenticated context → current policy → explicit method → owner transition.", source="service.py · ADR 002")
    table(s,["Attempt", "Observed behavior", "Boundary"],[
        ("Read another scope", "UNAUTHORIZED", "Scope IDs confer no authority"),
        ("Poll or ack another route", "UNAUTHORIZED", "Recipient owns delivery state"),
        ("Reuse key with different input", "CONFLICT", "Semantic idempotency"),
        ("Call after policy revocation", "Rejected on next checked call", "Policy is live, including retries"),
        ("Overfill job queue / inbox", "OVERLOADED / retained outbox", "No silent acknowledged-work drops")],[470,470,516],row_h=84,size=24)
    s.box(72,735,1456,78,"Local fixture policy; trusted OS user and files. Production SCS enforcement remains open.",color="amber",fill="sand",title_size=25)
    note(s,"The local policy fixture maps opaque credentials to principals and stores current scope, method and route requirements on the service side. It is reloaded for each checked invocation, including retries and worker operations. A sender field or scope name in a request is never sufficient. The tests exercise foreign scopes, foreign routes, live revocation, ownership-safe dispatch, conflicting retries and overload. A full inbox retains execution completion in the outbox until delivery can occur. The same OS user can directly access trusted service files, so this harness does not claim production multi-tenancy, encrypted private storage or an SCS enforcement integration. Before private data use, real enforcement and service isolation are separate gates.")

    s = Slide("What ran, what was a fixture, what is unavailable", "03 / Evidence · provider honesty",
              "Seven requested repositories inspected; only demonstrated integrations are marked real.", source="discovery.md · evidence.md")
    table(s,["Component", "Classification", "Evidence / limit"],[
        ("DeTTa DA + FileStorage", "REAL PROVIDER LIBRARIES", "Persisted shares + actual reconstruction"),
        ("F1R3node / ASI seam", "REAL ISOLATED CHAIN", "Signed deploy; inclusion + effect finality"),
        ("Peer A / Peer B / inspect_atom", "PROTOCOL + OPERATION FIXTURES", "Real separate worker; no reasoning"),
        ("Policy + chain unit responses", "EXPLICIT FIXTURES", "Revocation / failure mapping / timeout tests"),
        ("Omega Hive", "RUNTIME UNAVAILABLE", "Onboarding index present; Hive checkout absent"),
        ("DAS / MeTTaClaw / ECAN / PLN", "INSPECTED; NOT INTEGRATED", "Candidate seams and future adapters recorded")],[445,475,536],row_h=82,size=23)
    note(s,"DeTTa means actual DA and FileStorage code executed against local persisted shares, not a mock and not a custody network. F1R3node means a real local node with a fresh isolated genesis and one validator, not public mainnet/testnet or multi-validator safety. Peers are independently instantiated protocol fixtures; inspect_atom is a deterministic fixture operation running in a real OS process. Authorization is an explicit local policy fixture. Fake chain responses exist only in unit tests and are distinct from the real chain evidence. The supplied omegahive-start-here repository is an onboarding index; the intended Hive runtime checkout is absent. DAS, MeTTaClaw, metta-attention and reachability were inspected, but their cognitive/channel providers were not integrated. No upstream source files were changed.")

    s = Slide("A real result digest reached a real local chain", "03 / Evidence · optional chain gate",
              "One registered approved commitment. Durable signed intent. Direct node observations.", source="evidence/chain-demo.json · f1r3.py")
    for x,label,body,color in [(72,"PENDING","Signed deploy accepted","amber"),(568,"INCLUDED","Block observed; effects pending","amber"),(1064,"FINALIZED","Deploy effects reported finalized","teal")]:
        s.box(x,258,464,150,label,body,color,"sand" if color=="amber" else "mint",title_size=34,body_size=24)
        if x<1064:s.line(x+464,333,x+492,333,C["muted"],arrow=True)
    s.text(75,457,700,"Recorded inclusion",29,C["ink"],"bold")
    for i,(k,v) in enumerate([("Block height",str(CHAIN["inclusion"]["blockNumber"])),("Execution error","false"),("Rejection count","0"),("Execution cost","351 phlo")]):
        s.text(75,511+i*48,325,k,26,C["muted"])
        s.text(406,511+i*48,290,v,27,C["ink"],"bold")
    s.rect(785,452,743,255,C["white"],radius=13)
    s.text(811,477,680,"Commitment = persisted result digest",27,C["ink"],"bold")
    s.text(811,531,680,CHAIN["commitment"][:32]+"\n"+CHAIN["commitment"][32:],24,C["teal"],"mono")
    s.text(811,621,680,f"Observation window: {CHAIN['observation_seconds']:.3f} s\nOne local sample; no latency SLA",25,C["muted"])
    band(s,"Only the generated result digest entered Rholang. Full payload stayed in local DA.",size=26)
    note(s,"Read the recorded chain JSON as the primary evidence. Its actual sequence is pending, included with effects Pending, then finalized. All three observations are present; the earlier report prose was corrected to match this trace. The block is height 3, execution errored=false, rejection count zero, cost 351 phlo. The approved commitment digest matches the persisted result ref in both demo bindings. Signing intent is stored before network submission, so an ambiguous timeout can reuse the same transaction signature. The local node was built from the inspected dirty working source and shut down with exit 0. Node startup took 25.735 seconds and the observed submission/propose/finality window took 4.013 seconds. These node responses are not independently verified consensus proofs or a public-network test.")

    s = Slide("Evidence concentrates on boundaries that can fail", "03 / Evidence · executed verification",
              "Recorded passing tests and experiments; future cognitive test names are not included.", source="evidence/tests.log · evidence/detta-tests.log")
    for x,num,label in [(72,"27","contract + adapter tests"),(568,"102","upstream DA / storage tests"),(1064,"2","bindings; same consumer")]:
        s.rect(x,252,464,190,C["white"],radius=14)
        s.text(x+26,270,410,num,78,C["teal"],"bold")
        s.text(x+27,380,410,label,24,C["ink"])
    cases=[("Identity + isolation","Exact bytes, immutable revision, scoped routes, live revocation."),
           ("Replay + recovery","Conflicting keys, concurrent retries, three SIGKILL boundaries."),
           ("Admission + compatibility","Bounded overload, deadlines, versions, profiles and required features."),
           ("Provider behavior","Real erasure recovery, corrupt shares, chain mapping and signed-intent retry.")]
    for i,(title,body) in enumerate(cases):
        x=72+(i%2)*744;y=495+(i//2)*144
        s.text(x,y,704,title,28,C["ink"],"bold")
        s.text(x,y+45,692,body,25,C["muted"])
    note(s,"The final local verification run passed 27 unittest tests with zero failures or skips. Applicable service conformance cases run under both in-process and subprocess bindings. Separately, the upstream detta-da library passed 62 tests and detta-storage passed 40, totalling 102. These are distinct counts and do not imply 27 tests for each binding or a full upstream regression for every repository. The chain build and real local chain demo also passed as separately recorded gates. Other checks included Rust formatting, Python compilation and git diff validation. Do not count unimplemented episode, belief, attention or inference test specifications as executed functionality. No full F1R3node, DAS, MeTTaClaw or cognitive regression suite is claimed.")

    s = Slide("A small baseline, with the failure path included", "03 / Evidence · measured limits",
              "One 62-byte fixture, one slice per binding. Bars share a zero baseline; this is not a benchmark.", source="evidence/demo.json")
    runs=DEMO["runs"]
    s.tag(75,233,"IN-PROCESS SERVICE","blue",C["ice"])
    s.tag(458,233,"SUBPROCESS SERVICE","teal",C["mint"])
    labels=[("Store", "store_ms"),("Message acceptance","share_accept_ms"),("Job acceptance","job_accept_ms")]
    for i,(label,key) in enumerate(labels):
        y=321+i*137
        s.text(73,y,360,label,27,C["ink"],"bold")
        for j,run in enumerate(runs):
            value=run["timings"][key]
            s.rect(440,y+j*43, value*3.0,27,C["blue"] if j==0 else C["teal"],radius=3)
            s.text(452+value*3.0,y+j*43-1,165,f"{value:.1f} ms",23,C["muted"])
    s.line(440,688,1040,688,C["line"])
    for v in [0,50,100,150,200]:s.text(432+v*3,699,95,str(v),18,C["muted"],"mono")
    s.text(1084,699,95,"ms",18,C["muted"])
    s.box(1180,310,348,199,"Entire slice",f"{runs[0]['elapsed_seconds']:.3f} s / {runs[1]['elapsed_seconds']:.3f} s\nIncludes two worker kills and recovery.","ink",title_size=30,body_size=25)
    s.box(1180,538,348,180,"0 observed loss","Acknowledged data; tested same-host SIGKILL model only.","teal","mint",title_size=28,body_size=24)
    band(s,"Both bindings still use real DA subprocesses and separate workers. No scalability conclusion.",size=24)
    note(s,"Values are read directly from the committed demo.json, not retyped as marketing claims. The in-process binding is about the service call only; both configurations launch real DA helpers and separate workers. End-to-end slices include failure injection and recovery: approximately 0.756 and 1.761 seconds. Each used 17 client calls with 6,550 request bytes and 5,731 response bytes. In-process counts are logical serialization sizes; subprocess counts are actual pipe bytes. Canonical DA fixture/result payloads were 1,027 and 1,284 bytes, but DA framing and worker-control traffic were not measured. Both runs ended with two atoms, one job, two acknowledged messages and no pending outbox. Zero observed acknowledged-data loss is bounded by this failure model and sample, not a general durability theorem or performance guarantee.")

    s = Slide("The design trades breadth for inspectable guarantees", "04 / Decisions and gates",
              "Accepted prototype choices; community models and production guarantees remain unresolved.", source="decisions.md")
    table(s,["Decision", "What it makes explicit", "Cost / open boundary"],[
        ("Immutable scoped references", "Identity and replay are separate", "No GC, merge or mutable atom revisions"),
        ("One writer + durable outbox", "Recovery has a clear authority", "Small local harness; no distributed scheduler"),
        ("Exact semantic profiles", "Provider swaps preserve behavior", "Numerical models require specialist review"),
        ("Generic DA + external adapter", "Cognition stays above storage", "No distributed custody or lifetime guarantee"),
        ("Approved digest on chain", "Finality evidence stays separate", "No arbitrary deploy or private episode upload")],[451,475,530],row_h=90,size=24)
    note(s,"These are proposed v0 engineering decisions that operationalize the brief, not claims of community consensus. Immutable scoped reference metadata and replay keys provide a small auditable starting point; deletion, retention and cross-scope merging are deferred. SQLite serialization and an outbox make process-death behavior testable at the cost of throughput and distributed scheduling. Exact profiles avoid pretending numerical semantics or query dialects are interchangeable. The DeTTa adapter remains external to the application-neutral DA core. A chain adapter registers a single approved non-sensitive result commitment; it is not an arbitrary deployment service. All unassigned specialists remain unassigned. No invented arithmetic, ontology or STI policy was silently chosen.")

    s = Slide("M0 and M1 are complete. The next gate stays closed.", "04 / Scope and stopping point",
              "The architecture describes the next steps; this implementation stops before M2.", source="brief · evidence.md")
    for x,label,title,body,color,fill in [(72,"M0","Contracts","Discovery, ownership, typed ports, conformance obligations.","teal","mint"),
        (442,"M1","Real local slice","Store, share, inspect, recover; optional chain commitment.","teal","mint"),
        (812,"M2","Episodes + revision","Private ordering, evidence lineage, reviewed numerical model.","violet","lavender"),
        (1182,"M3 / M4","Cognition + Hive","Bounded attention / inference; selected workflow integration.","violet","lavender")]:
        s.box(x,253,346,250,title,body,color,fill,tag=label,title_size=28,body_size=25,dashed=color=="violet")
    s.text(75,552,1400,"Open gates",34,C["ink"],"bold")
    for x,title,body in [(72,"Integration","Intended Hive runtime / version; production authorization."),
                         (568,"Guarantees","Distributed custody; multi-validator operation; verified proofs."),
                         (1064,"Cognition","Reviewed revision model; STI policy; specialist ownership.")]:
        s.text(x,610,450,title,28,C["ink"],"bold")
        s.text(x,659,450,body,25,C["muted"])
    note(s,"M0 and the bounded local M1 gate are complete. The next increment is M2, with private ordered episodes and duplicate-safe, lineage-aware belief revision, including contradictory evidence and numerical golden tests for a reviewed existing model. That work has not started. M3 attention/inference and M4 Hive workflow integration remain later milestones. Actual Hive integration is blocked by the missing intended runtime and unsettled version/registry target. Production authorization, multi-host DA custody, public or multi-validator chain operation, independently verified proofs and meaningful load characterization remain open. Their absence does not erase the local evidence; local evidence does not pass those gates. Ending here respects the original stopping condition.")

    s = Slide("", "04 / Takeaway",source="implementation 3f75db9 · evidence.md",dark=True)
    s.text(72,179,1390,"Modularity is a promise\nabout behavior and authority.",67,C["white"],"bold",1.16)
    s.text(78,399,1350,"The working slice makes that promise reviewable.",36,C["dim"])
    for i,(n,txt) in enumerate([("01","State changes through its owner."),("02","Providers are selected by declared semantics."),("03","Receipts say precisely what was observed.")]):
        y=506+i*89
        s.text(79,y,100,n,35,"77DDC4","mono")
        s.text(191,y,1300,txt,34,C["white"])
    s.text(79,790,1350,"M0 + M1 delivered   •   No M2 implementation   •   Evidence and reproduction in the repository",22,C["dim"])
    note(s,"Close on the central idea: functional decomposition alone is insufficient. A module boundary needs an owner, behavioral semantics and evidence for its guarantees. This work turns that idea into an inspectable contract package and one bounded running slice. The storage integration is real, the local chain integration is real, peers and test policy are fixtures, and the cognitive stack is specified only. The architecture can evolve without embedding cognition in DA or requiring every operation to run on chain. Pause here for discussion; the remaining slides provide method mappings, exact provenance, failure semantics and reproduction commands.")

    s = Slide("Implementation dependency map", "Appendix A / Code navigation",
              "Solid lines identify actual calls/import composition; file names locate the corresponding seam.",source="fusion/ · adapters/detta/",appendix=True)
    s.box(72,246,330,128,"Peer","client.py → Binding.invoke", "blue", title_size=30,body_size=23)
    s.box(520,246,450,128,"Bindings","bindings.py → Service.invoke / host", "blue",title_size=30,body_size=21)
    s.box(1088,246,440,128,"Composition","composition.py injects DettaStorage", "teal",title_size=30,body_size=21)
    s.line(402,310,520,310,C["blue"],arrow=True)
    s.line(970,310,1088,310,C["blue"],arrow=True)
    s.box(520,460,450,139,"Service + owners","service.py → validate / policy / dispatch", "blue",title_size=30,body_size=21)
    s.line(745,374,745,460,C["blue"],arrow=True)
    s.box(72,460,330,139,"Contracts","contracts.py · ports.py\nNo backend imports", "ink",title_size=30,body_size=22)
    s.line(520,529,402,529,C["muted"],arrow=True)
    s.box(1088,460,440,139,"Opaque storage adapter","adapters/detta.py → Rust helper\n→ detta-da + detta-storage", "teal",title_size=26,body_size=22)
    s.line(970,529,1088,529,C["teal"],arrow=True)
    s.box(72,687,650,110,"Operator worker entry","host.py work / flush → ExecutionOwner", "blue",title_size=27,body_size=23)
    s.path([(722,741),(775,741),(775,599)],C["blue"])
    s.box(866,687,662,110,"Optional separate chain composition","chain_demo.py → F1R3Commitments → F1R3HTTP", "teal",title_size=27,body_size=22)
    note(s,"Navigate implementation from Peer methods to binding.invoke, then to Service.invoke validation and policy. In-process invokes the service in the current Python process; subprocess invokes the host through private EOF-framed stdin and one JSON stdout response. Trusted composition chooses the concrete storage adapter. Atom, message and execution owner logic is in service.py. The operator-only work and flush entry points are separate from public dispatch. detta.py calls the Rust helper linked to the original DA/storage libraries. chain_demo.py separately registers an approved commitment with F1R3Commitments, injected signer, signed-intent journal and F1R3HTTP. The drawing abstracts call paths; it does not imply contracts import implementation files.")

    s = Slide("Specified cognitive contracts carry test obligations", "Appendix B / Review checklist",
              "These are future acceptance cases, not executed M1 tests.",source="ports.py · contracts.md",appendix=True)
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

    s = Slide("Provenance includes working-tree state", "Appendix D / Source ledger",
              "Exact paths, remotes and source fingerprints are recorded in evidence/sources.json.",source="discovery.md · evidence/sources.json",appendix=True)
    table(s,["Repository", "Inspected commit", "Use / source state"],[
        ("omegahive-start-here", "0b15d2bed730", "Clean · onboarding only; runtime absent"),
        ("metta-attention", "3e1c8147dc17", "Clean · ECAN interfaces inspected"),
        ("das", "8afab5daa635", "Clean · atom/query proxies inspected"),
        ("mettaclaw", "d2da47207fec", "Existing untracked artifacts · interfaces read"),
        ("reachability-atomspace-prototype", "dd56f3f053ed", "Clean · ownership / PLN seams inspected"),
        ("secured-contract-spaces", "272888f264dd", "Existing modifications · linked + tested"),
        ("f1r3node-rust", "9ec1096e1077", "Existing modifications · built + executed")],[552,300,604],row_h=69,size=22)
    note(s,"The commit prefixes are navigation aids; the committed sources.json contains full identifiers, absolute roots, remotes, dirty-file lists and relevant working-source fingerprints. The real DeTTa and F1R3 builds used pre-existing modified source, so clean HEAD alone is insufficient to reproduce identical behavior. MeTTaClaw had untracked runtime/project artifacts. This task did not alter upstream sources or commit those upstream changes. Only the fusion-module-interfaces workspace is committed. The supplied Hive repository is an index; no actual Hive runtime checkout was available. Meeting transcripts were referenced in the brief but not independently supplied or inspected. The intended earlier Omega type/interface registry was not found; the static registry remains a bounded harness implementation.")

    s = Slide("Reproduce the gates; inspect the evidence", "Appendix E / Reproduction",
              "Run from the fusion-module-interfaces checkout; see runbook.md for prerequisites and exact commands.",source="runbook.md · evidence.md",appendix=True)
    s.rect(72,248,1456,162,C["dark"],radius=12)
    s.text(101,270,1370,"LOCAL M0 / M1 GATE",20,"77DDC4","bold")
    s.text(101,317,1370,"uv run --python 3.11 python scripts/verify.py",31,C["white"],"mono")
    s.text(101,370,1370,"Builds DeTTa adapter offline, runs 27 tests, executes both demo bindings.",23,C["dim"])
    s.box(72,450,704,220,"Optional real chain gate","scripts/build_chain.py\nscripts/chain_demo.py\nPinned extra tools + isolated local genesis; exact invocation in runbook.","teal","mint",title_size=30,body_size=25)
    s.box(800,450,728,220,"Review artifacts","evidence/demo.json + chain-demo.json\ntests.log + detta-tests.log\nsources.json + workspace-files.json", "ink",title_size=30,body_size=24)
    s.text(74,718,1420,"Requires inspected sibling checkouts and cached Cargo dependencies. No production keys or private episodes.",25,C["muted"])
    note(s,"The main command is executable as shown. It builds the actual DA adapter offline, runs the tests and executes both bindings. The optional chain build requires staged grpcio-tools; chain_demo requires pinned cryptography, pycryptodome and grpcio-tools extras, documented exactly in runbook.md. Initial native CLI/protoc/stack bring-up failures and the resolved local configuration are recorded in evidence.md rather than omitted. The demonstration uses generated non-sensitive data and fresh local keys under ignored artifacts; do not copy private data into it. For the presentation itself, build.py and requirements.txt in this directory generate the editable PowerPoint, vector PDF/SVG and speaker notes from one layout. No M2 implementation is required or created by these reproduction commands.")


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
    prs.core_properties.subject = "M0/M1 module interfaces, dependency maps and observed integration evidence"
    prs.core_properties.author = "Omega × ASI module-interface project"
    prs.core_properties.keywords = "Omega, ASI, M0, M1, DeTTa, module interfaces, state ownership"
    pdf_path = HERE / "omega-asi-module-interfaces.pdf"
    pdf = canvas.Canvas(str(pdf_path), pagesize=(W*SCALE,H*SCALE), invariant=1)
    pdf.setTitle(prs.core_properties.title)
    pdf.setAuthor(prs.core_properties.author)
    notes = ["# Omega × ASI — speaker notes", "", f"Implementation baseline: `{BASE_COMMIT}`.",
             "Suggested delivery: 25–30 minutes for slides 1–24, with appendices for discussion.",
             "All claims refer to the recorded 16 October 2026 local M0/M1 run.", ""]
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
        title=s.title or ("One responsibility. One state owner. Many possible backends." if index==1 else "Modularity is a promise about behavior and authority.")
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
                evidence_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
                                 [EVIDENCE/"demo.json",EVIDENCE/"chain-demo.json"]},slides_manifest=manifest)
    (HERE/"build-manifest.json").write_text(json.dumps(checks,indent=2)+"\n")
    print(json.dumps({"slides":len(SLIDES),"pdf":str(pdf_path),"pptx":str(pptx_path),"qa":str(QA)},indent=2))


if __name__=="__main__":
    build_content()
    export()
