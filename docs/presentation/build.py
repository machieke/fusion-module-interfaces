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
M2 = EVIDENCE / "m2"
RECORD = json.loads((M2 / "manifest.json").read_text())
VERIFY = json.loads((M2 / "final/verification.json").read_text())
BASELINE = json.loads((M2 / "final/m1_2/verification.json").read_text())
SWAP = json.loads((M12 / "m11-swap-demo.json").read_text())
DEMO = json.loads((M2 / "final/demo.json").read_text())
BUILD = json.loads((M2 / "fresh-build.json").read_text())
NATIVE = BUILD["native_build"]
HISTORICAL_CHAIN = json.loads((EVIDENCE / "chain-demo.json").read_text())
BASE_COMMIT = RECORD["tested_commit"]
EVIDENCE_COMMIT = "f0cee248294a1fce42913782390e6c084025c67e"
MAIN_SLIDES = 30
COMMANDS = {item["name"]: item for item in VERIFY["commands"]}
BASE_COMMANDS = {item["name"]: item for item in BASELINE["commands"]}
COUNTS = {name: int(re.search(r"Ran (\d+) tests", BASE_COMMANDS[name]["test_summaries"][0])[1])
          for name in ("fixture", "detta")}
COUNTS.update({name: BASE_COMMANDS[name]["tests"]["tests"] for name in ("native-baseline", "hive-integration")})
COUNTS.update({name: int(re.search(r"Ran (\d+) tests", COMMANDS[name]["summaries"][0])[1])
               for name in ("m2-fixtures", "upstream-revision-guards", "m2-native-revision", "m2-recovery-privacy")})
COUNTS["m2-native-hive"] = COMMANDS["m2-native-hive"]["tests"]["tests"]
UPSTREAM_COUNTS = [int(re.search(r"(\d+) passed", summary)[1])
                   for summary in BASE_COMMANDS["upstream-detta"]["test_summaries"]]
EVIDENCE_FILES = [M2 / name for name in ("manifest.json", "final/verification.json", "final/demo.json",
                  "final/m1_2/verification.json", "fresh-build.json", "source-preservation.json",
                  "checksums.json")] + [M12 / "m11-swap-demo.json", EVIDENCE / "chain-demo.json"]
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
        self.text(72, 853, 1300, f"OMEGA × ASI   /   THROUGH M2   /   {self.source}", 15, color)
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
    s = Slide("", "Module-interface architecture", source="M2 evidence f0cee24 · tested d9e7577", dark=True)
    s.text(72, 169, 1380, "Memory that remembers.\nBeliefs that can change.\nBoundaries that hold.", 72, C["white"], "bold", 1.15)
    s.text(76, 481, 1250, "Omega Hive × ASI", 42, C["dim"])
    s.text(76, 550, 1390, "From replaceable modules to private memory and guarded native revision", 30, C["white"])
    s.tag(76, 676, "M2 · C1 + C2 COMPLETE", "teal", C["mint"], 20)
    s.tag(486, 676, "REAL HIVE · DETTA · PLN", "blue", C["ice"], 20)
    s.text(76, 754, 1350, "Architecture and evidence • 16 October 2026 • supported local scope", 22, C["dim"])
    note(s, "Open with the ELI16 executive summary, then the helicopter view and all fifteen module responsibilities before implementation details. M1.1 proved independent storage substitution and separate owner commits. M1.2 connected the real native Hive caller. M2 adds only C1 EpisodicMemory and C2 BeliefRevision, including actual guarded native PLN revision and one real Hive episode scenario. This is a bounded engineering integration, not a general reasoning agent or production system. Suggested delivery: 35–40 minutes through slide 30; eight appendices support questions. Current evidence is the final clean d9e7577 run, recorded in unchanged-code descendant f0cee24. Rebuilding this presentation does not rerun integrations.")

    s = Slide("ELI16: a notebook, an evidence ledger, a calculator", "Executive summary · 1 of 2",
              "An agent needs to remember what happened without treating every report as a new fact.", source="m2-evidence.md · architecture.md")
    for x, tag, title, body in [
        (72,"C1 · THE NOTEBOOK","Keep the original story","Record events in order, including who they came from. Replaying the same event does not add a new entry."),
        (568,"C2 · THE EVIDENCE LEDGER","Keep disagreement visible","Track which observations support a belief. A copied report does not become independent evidence."),
        (1064,"PINNED PLN · THE CALCULATOR","Update only when justified","Use the existing formula for an explicitly allowed pair. Save the decision and the evidence behind it.")]:
        s.box(x,250,464,344,title,body,"teal","white",tag=tag,title_size=32,body_size=27)
    s.box(72,610,704,139,"What works", "Real Hive + local storage + native revision survive tested process restarts.","blue","ice",title_size=27,body_size=23)
    s.box(800,610,728,139,"What this does not prove", "That reports are true, sources are independent, or the system is production-ready.","amber","sand",title_size=27,body_size=23)
    band(s,"Why it matters: we can inspect, retry and replace parts without silently changing their meaning.",size=25)
    note(s, "ELI16 means explain the idea to a technically curious sixteen-year-old without assuming distributed-systems or PLN vocabulary. The notebook is C1: what happened, in what order and with what provenance. The evidence ledger is C2: what was admitted, what contributes to the current aggregate and what remains an alternative. The calculator is the narrow RevisionMath dependency; it does not decide what to think about. The runtime is real, while the observations and independence declarations in the demonstration are generated fixtures. We killed actual processes and recovered from local files. That supports a local restart claim, not power-loss or distributed failover. Benefits are auditable history, duplicate-safe contributions and explicit provider choices.")

    s = Slide("ELI16: a copied report is not a new source", "Executive summary · 2 of 2",
              "Imagine deciding whether a sensor reading is reliable. Keep the source trail, not just the message count.",source="C1 provenance · C2 support coverage")
    s.box(72,260,410,153,"Original report", "One observation from source A.","blue","ice",title_size=32,body_size=27)
    s.box(592,260,410,153,"Copied report", "A second message still traces to A.","blue","ice",title_size=32,body_size=27)
    s.box(1112,260,416,153,"Contrary observation", "Source B can disagree; retain it.","amber","sand",title_size=30,body_size=27)
    s.line(482,337,592,337,C["blue"],arrow=True)
    s.text(500,294,90,"copy",22,C["blue"])
    s.path([(277,413),(277,478),(797,478),(797,413)],C["blue"],arrow=False)
    s.text(308,493,650,"Same origin → no extra numerical weight",25,C["blue"],"bold")
    s.box(72,584,690,147,"Store all three observations", "Remembering a report does not mean believing it.","teal","mint",title_size=32,body_size=27)
    s.box(810,584,718,147,"Combine only an eligible pair", "Explicit independence assumption + lineage guards + native formula.","teal","mint",title_size=30,body_size=25)
    band(s,"A retry is not a new event. A copy is not a new source. A disagreement is not erased.",size=26)
    note(s,"This sensor example is an explanatory analogy, not an additional experiment. The actual generated scenario uses the same distinctions: a report without a truth value, an explicit assessment, a copy with the original roots, and a contrary assessment. Admission preserves observations even when numerical aggregation is refused. Known common origins or overlapping evidence block additional weight despite an independence declaration. The operator's assertion of independence is an assumption, not proof; undisclosed copying is not detected. A separate generated independent pair exercises actual native revision.")

    s = Slide("Fifteen modules; four responsibility groups", "01 / Helicopter view",
              "A module owns a responsibility. It need not be a separate process or repository.")
    lanes=[(72,320,"CLIENT / COGNITION","lavender"),(420,400,"APPLICATION PORTS","ice"),
           (848,322,"CONTROL & POLICY","pale"),(1198,330,"PROVIDER ADAPTERS","mint")]
    for x,w,title,fill in lanes:
        s.rect(x,230,w,495,C[fill],radius=14);s.text(x+18,251,w-36,title,18,C["ink"],"bold")
    for i,(label,color) in enumerate([("Episodic memory","blue"),("Belief revision","blue"),
                                     ("PLN kernel","violet"),("ECAN / attention","violet"),("Inference control","violet")]):
        s.box(90,300+i*78,284,62,label,color=color,title_size=22,dashed=color=="violet")
    for i,(label,color) in enumerate([("AtomStorage","blue"),("Relations · future","violet"),
                                    ("Search projection · future","violet"),("Agent messaging","blue"),("Delegated execution","blue")]):
        s.box(438,300+i*78,364,62,label,color=color,title_size=23,dashed=color=="violet")
    for i,label in enumerate(["Registry","Compatibility resolver","Authorization"]):
        s.box(866,300+i*108,286,95,label,color="blue",title_size=22)
    s.box(1216,300,294,144,"DA storage","Real local DeTTa","teal",title_size=27,body_size=23)
    s.box(1216,485,294,168,"Consensus / finality","M1 historical; M2 NOT_RUN","amber",title_size=26,body_size=22)
    s.text(866,649,282,"Local test policy\nand static descriptors",20,C["muted"])
    s.tag(72,760,"SPECIFIED / FUTURE","violet",C["lavender"])
    s.tag(365,760,"IMPLEMENTED LOCAL","blue",C["ice"])
    s.tag(687,760,"REAL PROVIDER","teal",C["mint"])
    s.text(987,766,540,"Narrow RevisionMath ≠ general PLN kernel",20,C["muted"])
    note(s,"The fifteen responsibility groups remain the same. C1 and C2 are now implemented private local modules; Relations, Search, the general PLN kernel, ECAN and inference control remain specifications. RevisionMath is a narrow dependency inside the C2 integration, not a claim to have implemented the general PLN kernel. Hive is a consumer. Provider, process and repository boundaries are independent. Blue means implemented local contracts, not production readiness. Authorization uses real native Hive authentication followed by a development Fusion policy. Finality has historical M1 evidence only; no M2 chain action occurred. Maintainer assignments remain unassigned.")

    s = Slide("Data responsibilities: bytes → references → history", "01 / Responsibility atlas · 1 of 3",
              "Persistence, identity, structure, discovery and provenance have different owners.")
    table(s,["Module","Function / primary operations","Owned state / status"],[
        ("DA storage","Persist opaque bytes\nput · get · availability","Payloads + shares\nREAL LOCAL PROVIDER"),
        ("AtomStorage","Scoped immutable envelopes\ncreate · get · getMany · availability","Reference + replay metadata\nIMPLEMENTED"),
        ("Relations","Represent ordered structural roles\nassertRelation · getRelation","Immutable relation records\nSPECIFIED"),
        ("Search projection","Find refs at a known watermark\nquery","Rebuildable index\nSPECIFIED"),
        ("Episodic memory C1","Record / append / read ordered events\npendingEvidence · acknowledgeEvidence","Private history + delivery intents\nIMPLEMENTED · M2")],[330,600,526],row_h=92,size=24)
    band(s,"DA persists bytes. Only the application owners interpret events, claims or beliefs.",size=27)
    note(s,"AtomStorage owns immutable scoped references and replay metadata, while DA only persists opaque payloads and generic coordinates. Relations and Search remain typed specifications. C1's local v2 operations are recordEpisode, appendEvent, readEpisode, readEvidence, pendingEvidence and trusted acknowledgeEvidence. findEpisodes is not advertised. C1 preserves committed episode-local order and admitted provenance; observed time is metadata. It can run without C2 or PLN and against an independently implemented AtomStorage fixture. Its event bytes are immutable atoms, while its episode head and delivery intents belong to C1.")

    s = Slide("Cognitive responsibilities: history ≠ truth ≠ attention", "01 / Responsibility atlas · 2 of 3",
              "M2 implements belief revision. General rule execution and attention remain future work.")
    table(s,["Module","Function / primary operations","Owned state / boundary"],[
        ("Belief revision C2","Admit evidence; read immutable snapshots\nsubmitEvidence · readBelief","Evidence, supports, snapshots, attempts\nIMPLEMENTED · no agenda"),
        ("PLN kernel","Apply a rule to explicit premises\nprofiles · applyRule","No mutable domain state\nSPECIFIED · not RevisionMath"),
        ("ECAN / attention","Allocate, select and decay attention\nsubmitStimulus · select · advance","Balances + logical time\nSPECIFIED · no PLN dependency"),
        ("Inference control","Schedule bounded reasoning work\nstep","Receipts + checkpoint\nSPECIFIED · no truth ownership")],[330,630,496],row_h=109,size=24)
    band(s,"C2 asks a pure revision provider for a proposal, then authorizes and commits its own decision.",size=25)
    note(s,"C2 exclusively owns admitted observations/supports, immutable belief snapshots and exact semantic attempts. Its narrow RevisionMath port reuses the unchanged Reachability PLNAdapter.revise guards and the actual Truth_Revision formula. The general PLNKernel.applyRule contract remains unimplemented. Attention owns its own balances and logical time, with no hidden PLN or LLM dependency. Inference control would orchestrate bounded retrieval, selection and rules; it cannot own or mutate truth or attention behind their owners. No ECAN, inference-control or chain work is included in M2.")

    s = Slide("Control responsibilities: move work, preserve authority", "01 / Responsibility atlas · 3 of 3",
              "The remaining six modules connect owners and report specific facts.")
    table(s,["Module","Function / primary operations","Owned state / status"],[
        ("Messaging","Accept, deliver, acknowledge\nsend · poll · ack","Inbox + deduplication · IMPLEMENTED"),
        ("Execution","Run one named operation\nsubmit · status · result","Jobs + completion outbox · IMPLEMENTED"),
        ("Registry","Describe configured providers\ndescriptors","Static configuration · IMPLEMENTED"),
        ("Resolver","Match required semantics\nresolve","No mutable state · IMPLEMENTED"),
        ("Consensus / finality","Submit approved commitment; observe\nsubmit · observe","Signed intents · HISTORICAL M1"),
        ("Authorization","Check current caller + scope + method\nauthorize / live policy checks","Operator policy · LOCAL FIXTURE")],[330,590,536],row_h=82,size=23)
    note(s,"Messaging acceptance differs from delivery and acknowledgement. Execution accepts only inspect_atom and owns jobs plus its completion outbox; result atoms commit independently. The registry advertises descriptors, and the resolver matches consumer requirements. Neither grants permission. Finality records independent chain observations from historical M1; it is not a C1/C2 dependency. Native authentication supplies trusted actor context, while local Fusion policy determines current access. The M2 relay is a narrow delivery cursor between two owners, not a sixteenth general service, event bus or inference controller.")

    s = Slide("Function dependencies: the exercised M2 path", "01 / Dependency map · private cognition",
              "Solid arrows point from caller to provider. Each effect stays behind its declared port.",source="ports.py · private.py · evidence_relay.py")
    s.box(72,245,330,120,"Real Hive plugin","Trusted actor → private mapping","teal","mint",title_size=27,body_size=22)
    s.box(535,245,430,120,"Generated scenario","Explicit assessment + assumption policy","blue","ice",title_size=28,body_size=22)
    s.box(1080,245,448,120,"Private composition","Resolve descriptors + live authority","blue","ice",title_size=28,body_size=22)
    s.line(402,305,535,305,C["teal"],arrow=True);s.line(965,305,1080,305,C["blue"],arrow=True)
    s.box(72,452,330,120,"C1 episodes","append · readEvidence","blue",title_size=29,body_size=23)
    s.box(535,452,430,120,"Durable relay","pending / ack → C1; submit → C2","blue",title_size=29,body_size=22)
    s.box(1080,452,448,120,"C2 beliefs","submitEvidence · readBelief","blue",title_size=29,body_size=23)
    s.line(535,507,402,507,C["blue"],arrow=True);s.line(965,507,1080,507,C["blue"],arrow=True)
    s.path([(650,365),(650,405),(237,405),(237,452)],C["blue"])
    s.line(750,365,750,452,C["blue"],arrow=True)
    s.path([(850,365),(850,405),(1304,405),(1304,452)],C["blue"])
    s.path([(1106,572),(1106,612),(237,612),(237,572)],C["blue"])
    s.rect(553,592,470,34,C["bg"]);s.text(566,597,444,"C2 → C1.readEvidence",22,C["blue"],"bold")
    s.box(72,692,330,109,"Private AtomStorage","C1 + C2: create / get","blue",title_size=26,body_size=22)
    s.box(535,692,430,109,"Real local DeTTa","Opaque put / get / availability","teal","mint",title_size=28,body_size=22)
    s.box(1080,692,448,109,"RevisionMath","Guarded PLN → native PeTTa / SWI","teal","mint",title_size=28,body_size=22)
    s.line(180,572,180,692,C["blue"],arrow=True)
    s.path([(1160,572),(1160,655),(330,655),(330,692)],C["blue"])
    s.line(402,746,535,746,C["teal"],arrow=True);s.line(1304,572,1304,692,C["teal"],arrow=True)
    note(s,"Composition alone selects concrete providers and binds authenticated private authority. The generated scenario appends to C1, drains the relay and can submit an explicit pair assumption to C2. The relay invokes C1 pendingEvidence/acknowledgeEvidence and C2 readBelief/submitEvidence, storing exact attempts in its own journal. C2 resolves C1 EvidenceRefs through readEvidence and validates immutable records/claims through AtomStorage. C1 and C2 never read each other's SQL. C2 alone calls RevisionMath. C1's dependencies exclude C2, Hive, PLN, mailbox and execution. Registry/authority checks surround each invocation and the final C2 commit; omitted side arrows keep the function diagram readable. All illustrated arrows are exercised local calls, not promises of remote placement.")

    # The preserved M1.2 path remains useful context beside the new private path.
    s = Slide("Function dependencies: the preserved M1.2 path", "01 / Dependency map · shared application ports",
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

    s = Slide("The DA boundary remains application-neutral", "02 / Boundary · application-neutral persistence",
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

    s = Slide("Replace the provider; keep the consumer’s contract", "02 / Substitution and compatibility",
              "Interface, implementation, transport and placement remain independent choices.",source="m11-swap-demo.json · memory_contracts.py")
    table(s,["AtomStorage implementation","In-process binding","Private stdio binding"],[
        ("Real DeTTa libraries","PASS · independent workflow","PASS · independent workflow"),
        ("Atomic-file fixture","PASS · independent workflow","PASS · independent workflow")],[510,473,473],row_h=108,size=26)
    s.box(72,543,704,181,"M2 C1 works without cognition","An independent, hostile port wrapper rejects access to provider internals or foreign SQL.","blue","ice",title_size=30,body_size=26)
    s.box(800,543,728,181,"Compatibility is explicit","Select exact profiles, operations and descriptor tokens. Pin native source and binary identity.","teal","mint",title_size=30,body_size=26)
    band(s,"Observed replacement uses fresh stores. Existing accepted state is not migrated.",size=28)
    note(s,f"The four recorded M1.2 substitution workflows use protocol fixture callers, two AtomStorage implementations and two bindings. The independent file fixture neither inherits AtomOwner nor uses its atom table. The final M2 regression reruns the preserved matrix. M2 separately proves C1 against the independent file provider with cognition absent and hostile declared-port wrappers. Do not label the file fixture as another real DA provider. Wire remains 1.0.0 and immutable-bytes/1 remains unchanged. C1/C2 use local interface 2.0.0, implementation 0.2.0 and explicit private profiles. Descriptor hashes bind selection consistency, not provider honesty. These are fresh-store tests, not live namespace replacement or migration.")

    s = Slide("Private history stays in a separate local composition", "02 / Placement · ownership before routing",
              "The authenticated actor selects an operator-configured scope; request data cannot nominate authority.",source="private.py · episode_program/program.py")
    s.rect(72,242,920,485,C["mint"],C["teal"],16)
    s.text(100,264,858,"ONE PRINCIPAL · PRIVATE-LOCAL-ONLY",21,C["teal"],"bold")
    for x,y,w,title,body in [(100,318,410,"C1 owner","Events + head + delivery intents"),(554,318,410,"C2 owner","Snapshots + attempts + decisions"),
                             (100,510,410,"Private AtomStorage","Separate payloads + metadata"),(554,510,410,"Relay owner","Exact handoff requests + progress")]:
        s.box(x,y,w,156,title,body,"teal","white",title_size=30,body_size=25)
    s.box(1040,242,488,190,"Public Hive receipt","Generated counts + public command ID. Private lineage and content hashes stay local.","blue","ice",title_size=30,body_size=26)
    s.box(1040,474,488,253,"Shared services","No private mailbox, execution or chain port is constructed. Overlapping private/shared roots are rejected.","amber","sand",title_size=30,body_size=26)
    band(s,"Privacy evidence covers the tested routes under a trusted host/operator with intact local files.",size=25)
    note(s,"open_private resolves private descriptors and constructs separate local owners over actual DeTTa. It rejects overlap with configured shared roots. C1, C2, atoms and relay have distinct owner journals; the local composition grants one authenticated principal per private scope. Native Hive supplies actor and command context, and operator configuration maps actor/swarm to the private credential and scope. Canary tests inspect real shared stores/messages, intercepted outbound bindings, diagnostics, native responses and Hive traces. This is routing and placement isolation under a trusted host/operator, not encryption, administrator secrecy or remote privacy. Native authentication is real; the downstream Fusion policy remains the labelled local test policy.")

    s = Slide("Contract gaps are resolved before adding behavior", "02 / C1 + C2 local contracts",
              "Local v2 contracts state identity, ordering, numerical meaning and replay explicitly.",source="memory_types.py · memory_contracts.py · ADR 008/009")
    table(s,["Question","Explicit choice","Consequence"],[
        ("What identifies an episode?","Stable scope + ID; separate mutable head","History grows without changing identity"),
        ("What is a new occurrence?","Occurrence ID distinct from bytes and key","Same bytes can describe distinct events"),
        ("What counts as evidence?","Explicit assessment + admitted provenance","A report alone has no truth value"),
        ("What claim is revised?","Exact predicate, ordered arguments, polarity, context","No hidden semantic or negation conversion"),
        ("What did submit do?","Admission outcome + numerical outcome","Accepted evidence may stay an alternative"),
        ("What is retried?","Full semantic input + pinned runtime selection","Same key cannot acquire new meaning")],[390,560,506],row_h=81,size=23)
    note(s,"C1 profile is episode-local-sequence/2; C2 is pln-revision-private/1. Local interface version is 2.0.0, implementation 0.2.0. No new remote cognitive wire schema or M1 mutation route was added. EpisodeRef is stable while head tracks committed sequence; observed time is metadata. Evidence distinguishes report and explicit numerical assessment. Grounded claims use exact predicate, ordered string arguments and positive polarity plus exact context. A contrary low-strength assessment of the same claim differs from a negated claim. Admission admitted/duplicate is independent of initialized/revised/no-change/retained-alternative/model-inapplicable. Every attempt binds semantic input and selection. The separate belief.revision.assume permission authorizes pair assumptions; it is not an invented public method.")

    s = Slide("C1: one occurrence, one position in the story", "03 / Episodic memory",
              "Immutable event atoms sit behind a stable episode identity and a committed sequence.",source="episodes.py · tests/test_m2.py")
    s.tag(72,236,"EpisodeRef = scope + ID", "blue",C["ice"],22)
    for i,(title,body) in enumerate([("1 · Report","No numerical claim"),("2 · Assessment","Explicit strength / confidence"),("3 · Copy","Inherits original roots"),("4 · Contrary","Kept in the history")]):
        x=72+i*370
        s.box(x,322,346,182,title,body,"blue","white",title_size=29,body_size=26)
        if i<3:s.line(x+346,413,x+365,413,C["blue"],arrow=True)
    s.box(72,556,704,169,"Same occurrence + same body","Return the original receipt, even under a new request key. The head does not advance.","teal","mint",title_size=29,body_size=26)
    s.box(800,556,728,169,"Same occurrence + changed meaning","Conflict on body or provenance changes. Distinct real occurrences may share identical bytes.","amber","sand",title_size=28,body_size=26)
    band(s,"C1 commits event + evidence intent together; AtomStorage has already committed independently.",size=25)
    note(s,"The four illustrated event roles match the generated story. Each immutable event is referenced by an AtomRef; the episode head begins at zero and advances by one for accepted occurrences. A duplicate occurrence with the same semantic content returns its original receipt before a stale expected-head check, even under a new request key. Changed content or provenance for that occurrence conflicts. Distinct occurrences can have identical bytes. Payload persistence can precede episode commit and leave an orphan after death; replay recovers the same atom without inventing an acknowledged event. C1 exposes bounded reads, pending evidence and trusted acknowledgements, with no cognition dependency. No dynamic episode search or garbage collector is implemented.")

    s = Slide("C2: admitting evidence and changing belief are separate", "03 / Belief revision",
              "New observations remain visible even when they cannot change the current aggregate.",source="beliefs.py · memory_types.py")
    s.box(72,252,380,180,"Evidence submission","C1 evidence reference or an existing C2 support; exact claim and context.","blue","ice",title_size=30,body_size=25)
    s.line(452,342,554,342,C["blue"],arrow=True)
    s.box(554,252,400,180,"Admission decision","ADMITTED or DUPLICATE\nTrack occurrence and provenance.","blue","white",title_size=30,body_size=25)
    s.line(954,342,1056,342,C["blue"],arrow=True)
    s.box(1056,252,472,180,"Numerical decision","Initialize, revise, no change, retain alternative, or model-inapplicable.","teal","mint",title_size=30,body_size=25)
    s.box(72,510,704,211,"Aggregate with exact coverage","Every numerical result names the contributing leaves, origins, premises, formula and assumption.","teal","white",title_size=31,body_size=27)
    s.box(800,510,728,211,"Unaggregated alternatives","Copied or contrary observations remain in the snapshot. Later eligible assumptions can combine existing supports.","amber","sand",title_size=30,body_size=27)
    band(s,"One saved truth value is not a summary of every observation. Read its coverage and alternatives.",size=25)
    note(s,"The first eligible explicit assessment initializes the aggregate. Later evidence is retained without automatic aggregation unless an exact pair assumption and guards permit revision. Unknown origins cannot initialize a justified numerical aggregate. A report without numerical assessment is model-inapplicable. The ledger retains observations, support records, immutable snapshots and exact decisions. A later authorized independence declaration may combine already admitted supports, without creating another observation. Exact successful replay returns the original historical decision even after later revisions; a new-key duplicate returns current state without adding weight. Retained-alternative is a pair outcome, so an already covered ancestor need not produce a new alternative list entry or revision. Coverage fields state the actual result.")

    s = Slide("Lineage blocks double counting, even after aggregation", "03 / Evidence dependencies",
              "An independence declaration cannot override known overlapping roots or evidence.",source="PLNAdapter.revise · beliefs.py")
    for x,title,body,color in [(72,"Support A","Origin A · evidence a","blue"),(568,"Copy of A","Origin A · evidence a′","blue"),(1064,"Support B","Origin B · evidence b","teal")]:
        s.box(x,248,464,145,title,body,color,"white",title_size=32,body_size=26)
    s.line(536,320,568,320,C["blue"],arrow=True)
    s.text(580,419,440,"Known common origin → no extra weight",23,C["amber"],"bold")
    s.box(72,562,464,164,"Aggregate A + B","Coverage {a, b}\nRoots {A, B}","teal","mint",title_size=30,body_size=27)
    s.path([(210,393),(210,562)],C["teal"])
    s.path([(1296,393),(1296,510),(420,510),(420,562)],C["teal"])
    s.text(567,530,850,"Only with an eligible exact-pair assumption",24,C["teal"],"bold")
    s.box(824,594,704,132,"Aggregate + ancestor A","Overlap detected → no additional weight.","amber","sand",title_size=30,body_size=27)
    s.line(536,651,824,651,C["amber"],arrow=True)
    band(s,"New IDs, aliases or request keys do not manufacture independence.",size=29)
    note(s,"This is a support-lineage diagram, not a general inference graph. Registered source origins are operator assumptions. Copies inherit the union of admitted provenance roots. The unchanged upstream guards require an exact independence declaration binding both supports, with matching model, claim, context and disjoint relevant lineage. Known shared origin or evidence overlap takes precedence over that declaration. Aggregation unions lineage; reintroducing an ancestor cannot increase weight. In the generated demo ancestor_outcome is retained-alternative, while the aggregate and contribution coverage remain unchanged. The model does not detect undisclosed copying or establish the truth of source registration.")

    s = Slide("Native revision reuses the guarded implementation", "03 / Runtime compatibility",
              "A narrow revision provider binds the upstream guards, formula and native runtime explicitly.",source="pln_revision.py · integration/pln/sources.json")
    steps=[(72,"C2 owner","Exact support snapshots","blue"),(442,"PLNAdapter.revise","Unchanged Reachability guards","teal"),
           (812,"Truth_Revision","Pinned PLN source","teal"),(1182,"PeTTa / SWI","Actual native evaluation","teal")]
    for i,(x,title,body,color) in enumerate(steps):
        s.box(x,260,346,194,title,body,color,"white",title_size=27,body_size=26)
        if i<3:s.line(x+346,357,x+365,357,C[color],arrow=True)
    s.box(72,526,704,195,"Explicit runtime rebaseline","Historical SWI 10.0.1 remains unchanged. This gate selects SWI 10.1.14 under a new revision-only profile.","blue","ice",title_size=30,body_size=26)
    s.box(800,526,728,195,"Fail closed on drift","Source hashes, model, runtime profile and built binary digest are bound to durable attempts.","amber","sand",title_size=30,body_size=26)
    band(s,"No replacement production mathematics, applyRule, PLN.Derive or PLN.Query was introduced.",size=25)
    note(s,f"Reachability is pinned at {VERIFY['runtime']['reachability']}; PLN at {VERIFY['runtime']['pln']}; PeTTa at {VERIFY['runtime']['petta']}. C2 loads the unchanged PLNAdapter.revise and its truth/support guards, injecting only a revision-specific native runner. The runtime profile is fusion-petta-swi-10.1.14-revision/1, with model trueagi-pln-stv-finite-k1/v1. The upstream historical 10.0.1 checks/locks were not weakened. Source and binary drift, missing binaries, invalid outputs and timeouts are refused. This is not a general PLN rule kernel or an AdmissionService/AtomSpace projection. C2 rechecks live authority and expected revision after computation before committing.")

    s = Slide("Independent goldens check the actual native result", "03 / Numerical evidence",
              "Pairs are explicit assessments of the same claim, with permitted independence and disjoint lineage.",source="integration/pln/test_revision.py · final/demo.json")
    table(s,["Input pair · (strength, confidence)","Expected native result","Meaning"],[
        ("(0.75, 0.50) + (0.25, 0.50)","(0.50, 2/3)","Equal weight balances the assessments"),
        ("(0.75, 0.50) + (0.25, 0.75)","(0.375, 0.80)","Higher confidence shifts the result"),
        ("Same unequal pair, reversed","(0.375, 0.80)","Order does not change this revision")],[620,340,496],row_h=107,size=26)
    s.box(72,622,704,127,"Domain: finite values only","0 ≤ strength ≤ 1; 0 ≤ confidence < 1","teal","mint",title_size=25,body_size=23)
    s.box(800,622,728,127,"No silent clamping","Invalid inputs and zero total weight are refused.","amber","sand",title_size=25,body_size=23)
    band(s,"Confidence belongs to the selected model; it is not a guarantee that the real-world claim is true.",size=25)
    note(s,"These are independent expected-value oracles for actual Truth_Revision through native PeTTa/SWI, not replacement production arithmetic. The valid-result absolute tolerance is 1e-12. Decimal-string inputs must pass both decimal and float64 domain checks; a value that rounds confidence to one is refused, not clamped. Nonfinite values, wrong model/context/claim, zero total weight and malformed native output fail explicitly. evidence_count remains null. The golden tests include equal, unequal and swapped input order. Malformed/empty/multiple output tests are labelled injected fixtures inside the broader native-provider suite. These computations do not validate the external truth or statistical independence of observations.")

    s = Slide("Four crash gaps across independent commits", "03 / Recovery · actual SIGKILL",
              "Restart recovers intent and decisions. Repeated calculation does not add another logical contribution.",source="test_recovery.py · test_m2_integration.py")
    for i,(title,body) in enumerate([("AtomStorage","Persist immutable bytes"),("C1 episodes","Commit event + intent"),("C2 beliefs","Commit snapshot + decision"),("C1 acknowledgement","Commit handoff receipt")]):
        x=72+i*370
        s.box(x,254,346,158,title,body,"blue","white",title_size=27,body_size=25)
        if i<3:s.line(x+346,332,x+365,332,C["blue"],arrow=True)
    rows=[("1 · Payload persisted; no C1 commit","Replay recovers the atom; an orphan is not an event."),
          ("2 · C1 intent committed; no C2 decision","The relay resubmits its exact durable request."),
          ("3 · Formula returned; no C2 commit","Calculation may repeat; CAS and replay guard the effect."),
          ("4 · C2 committed; no C1 acknowledgement","Recover the same decision, then acknowledge separately.")]
    table(s,["Killed at this boundary","After a new process starts"],rows,[700,756],y=453,row_h=62,size=23)
    band(s,"All four boundaries also run through the actual native Hive caller’s restart path.",size=27)
    note(s,"These are actual OS-process SIGKILL tests with intact persistent local files. Atom persistence, C1 append+intent, C2 snapshot+decision and C1 acknowledgement are independent commits. The relay owns a separate exact request/cursor record, never foreign SQL. C2 saves its full semantic attempt before calculation, then rechecks authority and expected revision before final commit. Formula work may repeat after a crash, but logical evidence weight is duplicate-safe. Tests also exercise a two-process CAS race, retrying the unchanged key/occurrence/head through transient contention until a genuine final conflict. None of this proves power-loss durability, distributed failover or exactly-once physical evaluation.")

    s = Slide("Authority, replay and compatibility stay live", "03 / Refusals and bounded recovery",
              "Saved success is evidence of an earlier decision, not permission to bypass current checks.",source="private.py · beliefs.py · evidence_relay.py")
    table(s,["Attempt or interruption","Required behavior","Protected boundary"],[
        ("Supply actor identity in Hive params","Native HTTP 400 identity_in_request","Trusted actor context"),
        ("Revoke access after saved success","UNAUTHORIZED on replay","Current scope and method authority"),
        ("Revoke authority during formula work","Recheck before C2 commit","No unauthorized state change"),
        ("Change input under the same key","CONFLICT","Full semantic fingerprint"),
        ("Change descriptor / source / runtime","Fail selected compatibility checks","No weaker fallback provider"),
        ("Transient owner contention or timeout","Keep exact intent pending; no ack","Recoverability without extra evidence")],[510,490,456],row_h=80,size=23)
    band(s,"A genuine CAS conflict needs a new key with the reconciled revision; transient retries keep the original key.",size=23)
    note(s,"Private authority validates complete descriptor selection and current principal, scope and method on every operation, including cached replay. The separate belief.revision.assume permission governs explicit pair assumptions. C2 also checks authority and expected revision after native calculation. Full acknowledgement-body fingerprints prevent substituting a different decision behind the same acknowledgement identity. Inputs are detached from caller mutation. Same-key semantic changes conflict, including expected revision and runtime selection. Genuine CAS conflicts require a new attempt identity; retryable NOT_AVAILABLE preserves the exact attempt. The relay is bounded to three CAS retries per drain and at most 32 attempts per delivery. It is not a general retry scheduler or inference controller.")
    s = Slide("One actual Hive episode reaches private C1 and C2", "04 / Native integration",
              "Same verified Hive source and native Programs entrypoint; a sibling plugin hosts the generated scenario.",source="episode_program/program.py · test_m2_integration.py")
    s.rect(72,235,1456,91,C["dark"],radius=12)
    s.text(100,261,1390,"POST /api/programs/fusion-episode/act",34,C["white"],"mono")
    xs=[172,590,1008,1426]
    for x,label in zip(xs,["Native Hive","Scenario + relay","Private C1 / C2","Native PLN"]):
        s.rect(x-100,375,200,53,C["mint"],radius=7);s.text(x-89,391,181,label,19,C["teal"],"bold")
        s.line(x,440,x,725,C["line"],dash=True)
    for x1,x2,label,y in [(172,590,"1  Authenticate; trusted actor + command",478),
                          (590,1008,"2  Record events; submit exact evidence",539),
                          (1008,1426,"3  Eligible pair → actual Truth_Revision",600),
                          (1008,590,"4  Save decision; acknowledge evidence",661),
                          (590,172,"5  Return counts + public command receipt",722)]:
        left=min(x1,x2);s.rect(left+4,y-30,width(label,21)+12,28,C["bg"])
        s.text(left+9,y-29,1510-left,label,21,C["ink"]);s.line(x1,y,x2,y,C["teal"],arrow=True)
    band(s,"7 native Hive tests passed: real app, authentication, Supervisor, PeTTa and plugin loader.",size=26)
    note(s,"The verified schematics pin actual Hive 34b0fb32ab3806e5609fc89bb7535518a35e1aea. Native startup is python -m hive; the integration driver uses the actual create_app, default Supervisor, PeTTa and native authenticated Programs dispatch in real processes. ASGI TestClient is only the transport. The sibling fusion-episode plugin derives authority from trusted actor context and operator principal/swarm mapping; it does not expose arbitrary observations over the shared wire. The original fusion-inspect plugin and thirteen tests remain unchanged. The seven M2 cases cover completion, exact replay/restart, all four SIGKILL boundaries, live revocation and private result isolation. Generated observations and assumptions remain fixtures even when the caller and providers are real.")

    s = Slide("The recorded story keeps copies and disagreement", "04 / Demonstrated behavior",
              "Generated scenario, real local DeTTa and native PLN; the CLI record is separate from the real Hive gate.",source="m2/final/demo.json · test_m2_integration.py")
    table(s,["Story event","Numerical outcome","What remains visible"],[
        ("Report without an assessment",DEMO['story_decisions'][0],"Original report; no invented truth value"),
        ("Explicit assessment (0.75, 0.50)",DEMO['story_decisions'][1],"One eligible support initializes the aggregate"),
        ("Copy with the same origin",DEMO['story_decisions'][2],"Copy retained; no extra aggregate weight"),
        ("Contrary assessment (0.25, 0.50)",DEMO['story_decisions'][3],"Disagreement retained without an assumption")],[550,390,516],row_h=82,size=23)
    s.box(72,622,704,127,f"{DEMO['story_events']} events · {DEMO['retained_alternatives']} unaggregated alternatives","Duplicate appends do not advance the episode.","blue","ice",title_size=26,body_size=23)
    s.box(800,622,728,127,"Separate eligible pair → (0.5, 2/3)","Native revision; ancestor re-entry adds no weight.","teal","mint",title_size=27,body_size=23)
    band(s,"Reopening preserves the exact snapshots and decisions. The native Hive route exercises the same scenario.",size=24)
    note(s,f"This slide reads the committed CLI demo record, whose own classification is: {DEMO['scenario']}. It is not relabelled as a native Hive trace. The real Hive test suite independently exercises the same integration/m2_scenario.py through native authentication and Programs dispatch. The story contains {DEMO['story_events']} events and {DEMO['retained_alternatives']} retained alternatives. A separate pair of {DEMO['independent_observations']} generated independent observations produces strength {DEMO['native_revision']['strength']}, confidence {DEMO['native_revision']['confidence']}, evidence_count null. Exact restart result equality is {DEMO['restart_exact_results']}. The ancestor outcome is {DEMO['ancestor_outcome']}; no extra observation or numerical contribution is created. No real-world source reliability is inferred from generated assessments.")

    s = Slide("M1.2 remains a working, separate integration", "04 / Regression and scope preservation",
              "Private cognition is added alongside the original storage, messaging and execution path.",source="source-preservation.json · final/m1_2/verification.json")
    s.box(72,250,704,208,"Original native operation","fusion-inspect still stores bytes, shares a ref, delegates inspect_atom, recovers completion and acknowledges it.","blue","ice",title_size=32,body_size=27)
    s.box(800,250,728,208,"New private operation","fusion-episode records private events and revises eligible evidence. It constructs no mailbox, execution or chain port.","teal","mint",title_size=32,body_size=27)
    table(s,["Preserved source boundary","Final regression"],[
        ("M1 wire schemas, registry/resolver, AtomStorage, DA adapter","Byte-identical to the requested M1.2 baseline"),
        ("Mailbox, execution, original Hive plugin and driver","Original behavior preserved"),
        ("Original native Hive integration tests",f"{COUNTS['hive-integration']} passed; test source unchanged")],[980,476],y=505,row_h=74,size=24)
    band(s,"Upstream guarded sources are unchanged. Application semantics remain above opaque DA.",size=27)
    note(s,"The M2 verifier explicitly compares the preserved source files against requested M1.2 evidence ancestor 4ee5cbe8b84689a5d2432530083738b263142f90. It reruns the original thirteen real native Hive tests, the selected native baseline, upstream DeTTa and the full conformance suite. ports.py grows new local protocols, while the preserved original wire schemas and bindings remain unchanged. All six built provider source trees are clean after testing, and supplied sibling sources remain unchanged. No ECAN, inference control, general PLN kernel, live migration or chain action is added.")

    s = Slide("Real providers and fixtures answer different questions", "04 / Evidence classification",
              "A real runtime can execute generated data. Neither label cancels the other.",source="m2/manifest.json · final/verification.json")
    table(s,["Component","Classification","What the evidence supports"],[
        ("Hive app / Supervisor / PeTTa","REAL NATIVE RUNTIME","Actual authenticated dispatch and caller restart"),
        ("DeTTa DA + FileStorage","REAL LOCAL PROVIDER","Opaque persistence, reconstruction, owner recovery"),
        ("Guarded PLN + Truth_Revision","REAL NATIVE REVISION","Pinned guards + actual formula goldens"),
        ("Generated data / origin assumptions","FIXTURES","Deterministic scenario, not empirical truth"),
        ("File provider / RecordingRuntime / injections","FIXTURES","Independent contracts and refusal behavior"),
        ("Fusion policy / transport / failpoints","TEST SUPPORT","Local grants and controlled failure placement")],[530,400,526],row_h=80,size=23)
    band(s,"Native Hive authentication is real. Downstream Fusion authorization is a local development policy.",size=25)
    note(s,"Do not flatten the system into one real/fixture label. The runtime/provider gates execute actual pinned source. The scenario data, source-origin registrations and independence declarations are generated assumptions. The independent file provider proves the AtomStorage contract but is not real DeTTa. Eight upstream guard tests use RecordingRuntime fixtures; malformed output tests inject fixtures into an otherwise native suite. The upstream Hive baseline uses its fixture process driver, while the actual integration tests use the real default Supervisor. ASGI TestClient is transport, not a fake native application. The historical chain observation remains separate, and the M2 chain gate is NOT_RUN.")

    s = Slide("Executed suites cover distinct layers of the claim", "04 / Tests · recorded final run",
              "Counts overlap: the 51 original fixtures and 16 M2 fixtures are included in the 106-case matrix.",source="m2/final/verification.json · final/m1_2/verification.json")
    table(s,["Suite","Cases","Classification / observed use"],[
        ("Full conformance matrix",str(COUNTS['detta']),"Original 90 + 16 M2 fixtures; separate 51-fixture run"),
        ("Clean DeTTa libraries",' + '.join(map(str,UPSTREAM_COUNTS)),"Real DA and FileStorage"),
        ("Hive baseline + original native integration",f"{COUNTS['native-baseline']} + {COUNTS['hive-integration']}","Baseline fixture driver / real native caller"),
        ("M2 isolated fixtures + upstream guard fixtures",f"{COUNTS['m2-fixtures']} + {COUNTS['upstream-revision-guards']}","Real-provider paths absent / RecordingRuntime"),
        ("M2 native revision",str(COUNTS['m2-native-revision']),"Actual goldens; malformed-output injections labelled"),
        ("M2 recovery / privacy + real Hive",f"{COUNTS['m2-recovery-privacy']} + {COUNTS['m2-native-hive']}","Actual SIGKILL, CAS race, native authenticated route")],[600,180,676],row_h=79,size=23)
    band(s,"All final commands returned 0. Native suites reported zero skipped tests. No new runtime tests run for this deck.",size=23)
    note(s,"The final comprehensive run is recorded from clean detached d9e75773c34987d5791a9207190fcbf0a8c1fd7b with PYTHONPATH forced to that checkout. The 106-case matrix includes the original 90 tests plus sixteen M2 fixtures; the fifty-one original fixtures and sixteen M2 fixtures are also run separately for isolation. Do not sum those repeated runs as unique tests. DeTTa has 62 DA and 38 storage tests. The 34 selected Hive baseline tests retain their upstream process-driver fixture; thirteen unchanged M1.2 tests and seven M2 tests exercise the real caller. Twelve native revision tests include real computations and deliberately injected malformed responses. Six recovery/privacy tests use actual local providers and SIGKILL. The CLI demo also passed with exact reopen results. Failed development runs remain in the evidence archive and are not counted as passing gates.")

    s = Slide("M2 gates: contracts, memory and native revision", "04 / Gate-by-gate results · 1 of 2",
              "All required M2 gates passed for the supported local profile.",source="m2/manifest.json · m2-evidence.md")
    gate_rows=[("BASELINE","Original behavior and native integration preserved"),
               ("CONTRACTS","Closed local inputs / outputs, profiles, bounds and fingerprints"),
               ("C1","Real-backed ordered history, replay, provenance and intents"),
               ("C1_INDEPENDENT","Independent AtomStorage; cognition absent; declared ports only"),
               ("C2_GUARDS","Unchanged upstream guards + hostile-input refusals"),
               ("C2_NATIVE","Actual native equal / unequal / reversed-pair goldens")]
    table(s,["Gate","Result","Evidence obligation met"],[(n,RECORD['gates'][n].split(':')[0],v) for n,v in gate_rows],[345,190,921],row_h=81,size=25)
    note(s,"Gate statuses are read from the committed M2 manifest, not inferred from slide content. BASELINE includes source preservation and regression. CONTRACTS includes local v2 protocol fidelity and response validation. C1 combines sequence/CAS/replay with real DeTTa persistence. C1_INDEPENDENT is a fixture conformance gate, deliberately independent of the real math provider. C2_GUARDS includes eight unchanged upstream RecordingRuntime tests, local guards and native-suite refusal cases. C2_NATIVE includes actual native formula computations plus source/runtime compatibility checks. Fixture gate success is not relabelled as native numerical execution.")

    s = Slide("M2 gates: privacy, recovery, Hive and reproducibility", "04 / Gate-by-gate results · 2 of 2",
              "No M2 prerequisite remains blocked. Optional or excluded work retains its own status.",source="m2/manifest.json · source-preservation.json")
    gate_rows=[("PRIVACY","Tested private routing; cross-principal / scope and revocation"),
               ("RECOVERY","Four real kill boundaries, stable decisions, two-process CAS"),
               ("HIVE_M2","Seven actual authenticated native caller tests"),
               ("REPRO","Fresh providers + clean Fusion run; download caches warm"),
               ("SCOPE","C1 + C2 only; M1.2 and upstream guarded sources preserved"),
               ("CHAIN","Outside M2; no chain action or fallback")]
    table(s,["Gate","Result","Observed boundary"],[(n,RECORD['gates'][n].split(':')[0],v) for n,v in gate_rows],[345,190,921],row_h=79,size=24)
    band(s,"Historical exact chain-source reproduction remains BLOCKED; it is not a missing M2 prerequisite.",color="amber",fill="sand",size=25)
    note(s,"PRIVACY proves canary isolation over the tested local routes under the trusted-host threat model. RECOVERY proves process restart, not power loss or distributed failover. HIVE_M2 uses actual native dispatch and the real private provider path. REPRO uses fresh native objects, venv and DeTTa Cargo target, while Git/Python/Cargo downloads may use warm caches. SCOPE limits the change to C1/C2 and preserves named original source files. CHAIN is explicitly NOT_RUN. No required M2 prerequisite remains blocked. A different historical question—exact reproduction of the dirty M1 F1R3 source state—remains blocked by unavailable source inputs and is documented separately in the appendix.")

    s = Slide("Reproducibility binds source, build and execution", "04 / Reproduction evidence",
              "The final code is tested from a clean detached checkout; native inputs are independently pinned.",source="m2/fresh-build.json · final/verification.json")
    for x,title,body in [(72,"1 · Fetch exact sources","Hive + DeTTa via authorized SSH; Reachability, PLN, PeTTa and SWI at full commits."),
                          (568,"2 · Build fresh providers","New native objects, venv, Janus and DeTTa target. Download caches may be warm."),
                          (1064,"3 · Verify exact Fusion","Clean d9e7577 checkout. All supported gates; exact commands, hashes and logs retained.")]:
        s.box(x,252,464,304,title,body,"teal","white",title_size=31,body_size=27)
    s.box(72,602,704,137,"Observed build: 337.325 seconds","A build observation on this host; no throughput or latency claim.","blue","ice",title_size=29,body_size=25)
    s.box(800,602,728,137,"Evidence snapshot: f0cee24","Documentation/evidence descendant with the same tested implementation.","blue","ice",title_size=29,body_size=25)
    band(s,"A reproducible source/build recipe does not promise bit-identical binaries across hosts.",size=26)
    note(s,f"The fresh build took {BUILD['seconds']} seconds, including {NATIVE['seconds']} seconds for native SWI/Janus/Hive. Its native-build record names 6452fa7 because provider construction began before the M2 commits; the native recipe/locks and compiled DeTTa adapter source were unchanged, and the recipe hash matches the committed M2 build script. Final Fusion verification separately used clean detached {BASE_COMMIT}. Exact source hashes, built binary digest, commands, logs and provider-cleanliness checks remain recorded. All six provider trees remained clean. No native target, venv or compiled object was copied from the original workspace. Globally empty-cache builds are NOT_RUN. The binary digest identifies the selected built runtime, not cross-host bit reproducibility. This deck updates presentation artifacts only and does not rerun native gates.")

    s = Slide("The guarantees stop at the tested boundary", "04 / Limits and stopping point",
              "Useful evidence is specific about the assumptions that made it possible.",source="m2-evidence.md · manifest.json")
    table(s,["Observed guarantee","Limit or unrun extension"],[
        ("Duplicate-safe occurrences and numerical contributions","Physical formula evaluation may repeat after a crash"),
        ("Retained contrary observations and exact coverage","No proof of source truth; undisclosed copying is undetected"),
        ("Private local placement and tested route isolation","Trusted host/operator; no encryption or admin secrecy claim"),
        ("Independent owner commits; process restart recovery","Power loss and distributed failover NOT_RUN"),
        ("Fresh-store substitution; explicit model/runtime profiles","No live state migration or universal-model claim"),
        ("Fresh pinned build; selected native Hive tests","Empty-cache build, historical SWI 10.0.1, full Hive suite NOT_RUN")],[730,726],row_h=78,size=23)
    band(s,"Stopped at M2: no ECAN, inference control, general rule kernel, chain action or live migration.",color="violet",fill="lavender",size=25)
    note(s,"The local profiles are deliberately bounded: 256 events per episode, pages/pending batches of sixteen, 32 observations per belief, at most 64 support records, and three CAS retries per drain. Owner history is retained without garbage collection or a total disk quota. Authority is a development local policy, not production identity management. Explicit model semantics and exact runtime selection are required. Native caller evidence is for the chosen Programs route and selected tests, not the full Hive suite, LLM operation or arbitrary application behavior. Future Relations/Search, ECAN, inference control and general PLN rules remain outside implemented scope. Chain and live migration are unrun. No new runtime guarantee is created by rebuilding this presentation.")

    s = Slide("", "04 / Takeaway", source="M2 tested d9e7577 · evidence f0cee24", dark=True)
    s.text(72,183,1410,"Remember the event.\nKeep the disagreement.\nJustify the update.",72,C["white"],"bold",1.16)
    s.text(76,505,1370,"Each state owner commits its part. Each retry keeps its meaning.",35,C["dim"])
    s.text(76,610,1390,"Real Hive · real local DeTTa · actual guarded PLN revision",31,C["white"])
    s.tag(76,711,"M2 COMPLETE · C1 + C2 ONLY","teal",C["mint"],22)
    note(s,"Return to the executive summary: the notebook preserves occurrences, the evidence ledger preserves disagreement and lineage, and the pinned calculator runs only when the explicit pair qualifies. The practical result is a private local memory/revision slice exercised by a real Hive caller, with duplicate-safe evidence and recovery across independent commits. It is not yet an autonomous reasoning loop or production deployment. All required M2 gates passed; fixtures, real providers, historical blocked source reproduction and unrun extensions retain their labels. The work stops at M2.")
    s = Slide("Implementation map: each owner has a small surface", "Appendix A / Code navigation",
              "Composition selects providers. Domain owners consume declared ports.",source="m2-evidence.md · architecture.md",appendix=True)
    table(s,["Files / area","Responsibility","State or exclusion"],[
        ("memory_types.py · memory_contracts.py · ports.py","Local C1/C2 DTOs, protocols and validation","No provider construction"),
        ("private.py","Private placement, descriptors, live authority","Only composition chooses concrete owners"),
        ("episodes.py","C1 occurrences, head, replay and intents","episodes.sqlite"),
        ("beliefs.py","C2 snapshots and semantic attempts","beliefs.sqlite"),
        ("evidence_relay.py","Bounded exact evidence handoff","relay.sqlite; no foreign SQL"),
        ("adapters/pln_revision.py","Pinned guards + revision-only native runtime","Pure proposal; no truth setter"),
        ("integration/m2_scenario.py · episode_program/","Generated policy + sibling native Hive plugin","Private owners; minimal public receipt")],[660,440,356],row_h=71,size=21)
    note(s,"Paths without prefixes are under fusion/. The adapter is fusion/adapters/pln_revision.py; the plugin is integration/hive/episode_program/. Source/build scripts are scripts/build_m2.py, verify_m2.py and m2_demo.py. Fixture tests live in tests/test_m2.py and tests/m2_support.py. Native and recovery tests live in integration/pln/; real Hive tests in integration/hive/test_m2_integration.py. C1 tables own episodes/events/mutations/deliveries, C2 owns snapshots/attempts, and the relay owns only exact handoff progress. Immutable payload and event bytes remain in private AtomStorage over separate local DeTTa. No upstream source is patched.")

    s = Slide("Exact sources include the explicit runtime rebaseline", "Appendix B / Source ledger",
              "Prefixes are navigation aids. Full SHAs and formula/binary digests are embedded in these notes.",source="final/verification.json · integration/pln/sources.json",appendix=True)
    pins=VERIFY['hive_sources']; runtime=VERIFY['runtime']
    table(s,["Input","Commit / version","Role"],[
        ("Fusion tested / evidence",BASE_COMMIT[:12]+' / '+EVIDENCE_COMMIT[:12],"Clean run / same-code evidence descendant"),
        ("Schematics → actual Hive",pins['schematics']['commit'][:12]+' → '+pins['repositories']['omegahive']['commit'][:12],"Intended native source and Programs route"),
        ("DeTTa",pins['repositories']['secured-contract-spaces']['commit'][:12],"Real clean local DA / FileStorage"),
        ("Reachability",runtime['reachability'][:12],"Unchanged guarded PLNAdapter.revise"),
        ("PLN",runtime['pln'][:12],"Actual Truth_Revision formula"),
        ("PeTTa / SWI source",runtime['petta'][:12]+' / '+pins['repositories']['swipl']['commit'][:12],"Native runtime at explicit source pins"),
        ("SWI / Python / Janus","10.1.14 / 3.12.12 / 1.5.3","Narrow rebaseline; historical 10.0.1 unchanged")],[360,500,596],row_h=70,size=22)
    note(s,f"Requested ancestor: {RECORD['requested_ancestor']}. Starting checkout: {RECORD['starting_commit']}, presentation/docs-only descendant. Final clean tested Fusion: {BASE_COMMIT}; evidence snapshot: {EVIDENCE_COMMIT}. Schematics: {pins['schematics']['commit']}; Hive: {pins['repositories']['omegahive']['commit']}; DeTTa: {pins['repositories']['secured-contract-spaces']['commit']}; Reachability: {runtime['reachability']}; PLN: {runtime['pln']}; PeTTa: {runtime['petta']}; SWI source: {pins['repositories']['swipl']['commit']}. Formula SHA-256: {runtime['formula_sha256']}. Built SWI SHA-256: {runtime['binary_sha256']}. Runtime profile: {runtime['runtime_profile']}; model: {runtime['model']}. Python 3.12.12, Janus 1.5.3; fixture orchestration Python 3.11.14. Native source trees remained clean after the recorded final run. The supplied brief's content hash and fetch URL remain in the manifest.")

    s = Slide("Profiles and bounds are part of compatibility", "Appendix C / Contract ledger",
              "A matching method name alone does not establish substitutability.",source="memory_contracts.py · contracts.md",appendix=True)
    table(s,["Selection","Exact profile or limit","Implication"],[
        ("C1 / C2 local interface","2.0.0; implementation 0.2.0","No new remote cognitive wire routes"),
        ("C1 / C2 semantics","episode-local-sequence/2 · pln-revision-private/1","Bound identity, ordering and numerical decisions"),
        ("Numerical / runtime profiles","trueagi-pln-stv-finite-k1/v1\nfusion-petta-swi-10.1.14-revision/1","Explicit model + native selection"),
        ("Private atom / event bytes","65,536 / 16,384 bytes","Immutable bounded records"),
        ("Episode / provenance / batch","256 events; 8 provenance + 8 causation; page 16","No unbounded query surface"),
        ("Belief / snapshot / relay","32 observations; 64 supports; 262,144 bytes\n3 CAS retries/drain; 32 attempts/delivery","Retained history; no GC or total disk quota")],[350,670,436],row_h=83,size=21)
    note(s,"AtomStorage remains immutable-bytes/1 with original interface 1.0; M2 selects a separate private-local-only descriptor. C1/C2 local interface 2.0.0 is not a silent change to the existing M1 wire 1.0.0. Ingestion is explicit-generated-assessment/1, keeping generated assessment policy outside the owners. Numerical input uses finite decimal strings validated again at the float64 boundary; strength is in [0,1], confidence in [0,1), and evidence_count is null. The bounds listed are semantic contract limits. History is retained without garbage collection or a total storage quota. Live migration and generic query/search are not implemented.")

    s = Slide("Future cognition remains a set of review obligations", "Appendix D / Proposed dependencies",
              "Dashed arrows are specified future calls. The M2 owners in blue are already implemented.",source="ports.py · architecture.md",appendix=True)
    s.box(72,252,330,137,"Inference control","step(budget)","violet","lavender",title_size=29,body_size=25,dashed=True)
    for x,title,body in [(535,"Search projection","query(profile, watermark)"),(1080,"ECAN / attention","select · submitStimulus")]:
        s.box(x,252,448 if x==1080 else 430,137,title,body,"violet",title_size=29,body_size=24,dashed=True)
    s.line(402,302,535,302,C['violet'],dash=True,arrow=True)
    s.path([(402,278),(456,278),(456,225),(1304,225),(1304,252)],C['violet'],True)
    s.box(535,487,430,137,"Belief revision C2","readBelief · submitEvidence","blue","ice",title_size=29,body_size=24)
    s.box(1080,487,448,137,"General PLN kernel","applyRule(premise snapshots)","violet",title_size=28,body_size=22,dashed=True)
    s.path([(402,348),(456,348),(456,555),(535,555)],C['violet'],True)
    s.path([(402,375),(427,375),(427,438),(1304,438),(1304,487)],C['violet'],True)
    s.box(72,487,330,137,"C1 episodes","Private ordered history","blue","ice",title_size=29,body_size=24)
    s.text(76,677,1430,"Attention: budget, allocation, decay, tie-breaking.  Rules: model, premises, golden tests.",27,C['violet'],'bold')
    s.text(76,730,1430,"Control: bounded work and feedback.  Search: profile and freshness watermark.",27,C['violet'],'bold')
    note(s,"This is a proposed future dependency map, not evidence of an executed cognitive loop. Inference control would use Search, Attention, C2 and a general pure PLN kernel through explicit ports. Attention owns its own budgets/balances and logical time, without a required PLN or LLM dependency. The general kernel returns proposals over immutable premises. Inference control owns only step receipts/checkpoints, not truth or attention state. Relations/Search, ECAN, general rules and inference control remain future contracts with model/policy and conformance obligations. M2's narrow RevisionMath provider is distinct from applyRule. No new work in these modules was undertaken.")
    s = Slide("One native operation crosses the existing interfaces", "Appendix E / Preserved M1.2 sequence",
              "The caller stores intent; each provider commits only its own state.",source="program.py · execution.py · messaging.py",appendix=True)
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

    s = Slide("Historical M1: one result reached an isolated chain", "Appendix F / Historical chain evidence",
              "This is the earlier protocol-peer artifact. No M1.2 or M2 Hive result was submitted.",source="evidence/chain-demo.json · M1 historical",appendix=True)
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
    band(s,"M2 CHAIN = NOT_RUN. Historical source reproduction requires exact F1R3 changes or a separate rebaseline.",color='amber',fill='sand',size=22)
    note(s,"Preserve this historical result without promoting it into the new real-caller gate. The M1 chain JSON records pending, included with effect finality Pending, then finalized, at height 3 with no execution error, no rejection and cost 351 phlo. The committed digest belongs to the original protocol-peer result, not the generated native Hive result in M1.2. The M1 adapter used a registered approved digest, injected signer and durable signed intent against one isolated local node. That source had local changes and an untracked input. Exact historical reproduction remains blocked until those authorized bytes are supplied or a different clean revision is separately validated. No chain process or transaction was run during M1.2, M2 or this presentation update. Finality does not establish indefinite off-chain availability.")

    s = Slide("Reproduce the supported M2 gates", "Appendix G / Commands and prerequisites",
              "Run from the evidence revision or a reviewed descendant. See the runbook for Linux and source access.",source="runbook.md · build_m2.py · verify_m2.py",appendix=True)
    for y,label,line1,line2 in [(245,"BUILD FRESH PINNED PROVIDERS","uv run --python 3.11 --locked python","  scripts/build_m2.py artifacts/m2-providers"),
                               (465,"VERIFY BASELINE, C1, C2, PRIVACY, RECOVERY AND REAL HIVE","uv run --python 3.11 --locked python","  scripts/verify_m2.py artifacts/m2-providers/environment.json")]:
        s.rect(72,y,1456,187,C['dark'],radius=12)
        s.text(100,y+22,1380,label,19,'77DDC4','bold')
        s.text(100,y+69,1380,line1+' \\',27,C['white'],'mono')
        s.text(100,y+117,1380,line2,27,C['white'],'mono')
    s.text(78,697,1430,"Read: manifest.json → final/verification.json → per-suite logs → final/demo.json",26,C['ink'],'bold')
    band(s,"Fixture success, native provider success, blocked historical inputs and unrun extensions remain separate.",size=24)
    note(s,"Use a fresh destination; the build refuses to overwrite existing work. Authorized SSH access to the exact Hive and DeTTa sources is required. Public HTTPS retrieves the pinned Reachability/PLN inputs. The native build uses pinned PeTTa/SWI, hashed Python dependencies and new Janus objects; DeTTa is compiled into a fresh target. Git/Python/Cargo download caches may be warm. scripts/verify_m2.py runs the preserved M1.2 verifier and then isolated M2 fixtures, eight upstream revision guard tests, native revision, recovery/privacy, native Hive and a deterministic CLI demo. The exact final evidence run used a clean detached d9e7577 checkout and recorded commands/output paths. Failed development runs remain preserved. Building the presentation is a separate operation and never reruns or overwrites these integration records.")

    s = Slide("Retry decisions preserve meaning across owners", "Appendix H / Operational semantics",
              "Separate acceptance, numerical effect and acknowledgement before choosing a recovery action.",source="episodes.py · beliefs.py · evidence_relay.py",appendix=True)
    table(s,["Observation","Meaning","Next action"],[
        ("Lost response / process death","The owner may already have committed","Replay exact input, key and pinned selection"),
        ("NOT_AVAILABLE / transient contention","No final decision yet","Keep intent pending; retry unchanged"),
        ("CONFLICT: stale expected revision","Another owner-local update won","Read current snapshot; new key for revised intent"),
        ("CONFLICT: same key, changed input","Replay identity no longer matches","Do not overwrite the original meaning"),
        ("UNAUTHORIZED / profile mismatch","Access or selected semantics fail","Correct authority / compatibility; no fallback"),
        ("Decision durable; ack missing","C2 effect complete, C1 handoff pending","Recover same decision; acknowledge full receipt")],[475,490,491],row_h=81,size=23)
    band(s,"Trusted local acknowledgement binds the complete decision; it is not a portable cryptographic proof.",size=25)
    note(s,"Exact successful C2 replay returns the original decision and historical snapshot even after later revisions. New-key duplicate evidence reads current state without adding weight. The relay saves exact requests and runtime selection in its own journal; a transient provider failure never acknowledges the intent. After a genuine CAS conflict it reconciles and allocates a new semantic attempt under bounded retry limits. C1 acknowledgement is a separate commit and validates the complete decision body. The receipt is trusted local evidence, not a remote proof. The physical formula may execute more than once; only the logical admission and contribution are duplicate-safe. Retained-alternative describes the pair decision, with actual coverage and unaggregated lists controlling interpretation.")

    assert len(SLIDES) == 38
    assert sum(not s.appendix for s in SLIDES) == MAIN_SLIDES


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
    prs.core_properties.title = "Omega × ASI — Private memory and guarded belief revision"
    prs.core_properties.subject = "Through M2: private episodic memory, guarded PLN revision and real Hive recovery"
    prs.core_properties.author = "Omega × ASI module-interface project"
    prs.core_properties.keywords = "Omega, ASI, M2, ELI16, Hive, DeTTa, PLN, episodic memory, belief revision, recovery"
    pdf_path = HERE / "omega-asi-module-interfaces.pdf"
    pdf = canvas.Canvas(str(pdf_path), pagesize=(W*SCALE,H*SCALE), invariant=1)
    pdf.setTitle(prs.core_properties.title)
    pdf.setAuthor(prs.core_properties.author)
    notes = ["# Omega × ASI — speaker notes", "", f"Implementation baseline: `{BASE_COMMIT}`.",
             f"Evidence snapshot: `{EVIDENCE_COMMIT}`.",
             f"Suggested delivery: 35–40 minutes for slides 1–{MAIN_SLIDES}, with appendices for discussion.",
             "Current claims use the recorded 16 October 2026 M2 evidence. The M1 chain observation is historical and separately labelled.", ""]
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
        title=s.title or ("Memory that remembers. Beliefs that can change. Boundaries that hold." if index==1 else "Remember the event. Keep the disagreement. Justify the update.")
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
