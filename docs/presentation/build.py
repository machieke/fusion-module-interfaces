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
HISTORICAL_CHAIN = json.loads((EVIDENCE / "chain-demo.json").read_text())
M3 = EVIDENCE / "m3"
M3RECORD = json.loads((M3 / "manifest.json").read_text())
M3VERIFY = json.loads((M3 / "final/verification.json").read_text())
M3BUILD = json.loads((M3 / "build.json").read_text())
COMPARISON = json.loads((M3 / "final/comparison.json").read_text())
M3COUNTS = {item["name"]: int(re.search(r"Ran (\d+) tests", item["summaries"][0])[1])
            for item in M3VERIFY["commands"] if item["name"] not in
            {"m2-regression", "m3-native-hive", "m3-comparison"}}
M3COUNTS["m3-native-hive"] = next(item["tests"]["tests"] for item in M3VERIFY["commands"]
                                      if item["name"] == "m3-native-hive")
M31 = EVIDENCE / "m3_1"
M31RECORD = json.loads((M31 / "manifest.json").read_text())
M31VERIFY = json.loads((M31 / "final/verification.json").read_text())
M31BUILD = json.loads((M31 / "build.json").read_text())
M4 = ROOT / "evidence/m4"
M4RECORD = json.loads((M4 / "manifest.json").read_text())
M4VERIFY = json.loads((M4 / "final/verification.json").read_text())
M4TRACE = json.loads((M4 / "final/same-artifact.json").read_text())
M4READBACK = json.loads((M4 / "final/readback.json").read_text())
M4_BASE_COMMIT = M4RECORD["tested_implementation"]
M5 = ROOT / "evidence/m5"
M5RECORD = json.loads((M5 / "manifest.json").read_text())
M5VERIFY = json.loads((M5 / "final/verification.json").read_text())
M5CHECKSUMS = json.loads((M5 / "checksums.json").read_text())
BASE_COMMIT = M5RECORD["tested_source"]
EVIDENCE_COMMIT = "3dc6c1146601a0d0aa8785e61884970ec84a57c6"
MAIN_SLIDES = 54
TOTAL_SLIDES = 64
EVIDENCE_FILES = [M2 / name for name in ("manifest.json", "final/verification.json", "final/demo.json",
                  "final/m1_2/verification.json", "fresh-build.json", "source-preservation.json",
                  "checksums.json")] + [M12 / "m11-swap-demo.json", EVIDENCE / "chain-demo.json"]
EVIDENCE_FILES += [M3 / name for name in ("manifest.json", "final/verification.json",
                   "final/comparison.json", "build.json", "supplemental-empty-selection.json")]
EVIDENCE_FILES += [M31 / name for name in ("manifest.json", "final/verification.json",
    "build.json", "source-audit.json", "baseline/gaps.json", "non-numeric-processing.json")]
EVIDENCE_FILES += [M4 / "manifest.json"] + [M4 / name for name in M4RECORD["files"]]
EVIDENCE_FILES += [ROOT / "docs/module-interfaces/m4-evidence.md"]
EVIDENCE_FILES += [M5 / "checksums.json"] + [M5 / name for name in M5CHECKSUMS]
EVIDENCE_FILES += [ROOT / "docs/module-interfaces/m5-evidence.md", ROOT / "docs/module-interfaces/m5-contracts.md", ROOT / "docs/module-interfaces/m5-capability-ledger.json"]
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
        self.text(72, 853, 1300, f"OMEGA × ASI   /   THROUGH M5   /   {self.source}", 15, color)
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
    s = Slide("", "Module-interface architecture", source="M5 evidence 3dc6c11 · tested bfb0ec8", dark=True)
    s.text(72,169,1430,"Discover the knowledge.\nBound the work.\nVerify the result.",72,C["white"],"bold",1.15)
    s.text(76,481,1250,"Omega Hive × ASI",42,C["dim"])
    s.text(76,550,1390,"Private lookup, bounded cognition and verified chain commitments",30,C["white"])
    s.tag(76,676,"THROUGH M5 · LOOKUP + C1–C4 + CHAIN", "teal",C["mint"],20)
    s.tag(770,676,"HIVE · DETTA · PLN · F1R3", "blue",C["ice"],20)
    s.text(76,754,1350,"Architecture and evidence • 16 October 2026 • supported local scope",22,C["dim"])
    note(s,f"Start with five ELI16 executive-summary slides, then all fifteen module responsibilities and the exercised dependency maps before implementation detail. M1 establishes replaceable ports; M1.2 connects real Hive; M2 adds private memory and guarded revision; M3 adds independent STI and bounded inference; M3.1 accounts for delivery and feedback. M4 connects a generated, shareable native inspect result to an isolated real chain and checks its actual post-state effect plus matching deploy-effect finality. M5 adds four Relations operations, an authoritative commit feed and exact-attribute Search. Actual native lookup discovers roots, traverses relations and retrieves payloads without seeded answer references. The lookup, cognition and commitment paths have separate owners. Suggested delivery: 60–65 minutes through slide {MAIN_SLIDES}; ten appendices support discussion. Tested source {BASE_COMMIT}; evidence-only descendant {EVIDENCE_COMMIT}. Presentation changes do not rerun integrations or expand their guarantees.")

    s = Slide("ELI16: remember, weigh evidence, do the calculation", "Executive summary · 1 of 5",
              "Think of a student investigating a question with a notebook, evidence ledger and calculator.",source="M2 preserved · M3 derived admission")
    for x,tag,title,body in [
        (72,"C1 · NOTEBOOK","Keep the original story","Record what happened and where each report came from. Keep contrary observations; replay does not add another event."),
        (568,"C2 · EVIDENCE LEDGER","Know what supports a belief","A copy is still the same source. A conclusion keeps its parents; it does not become a fresh observation."),
        (1064,"PLN · CALCULATOR","Apply a guarded formula","Use the existing pinned mathematics on exact inputs. C2 checks and saves the result; the calculator owns no beliefs.")]:
        s.box(x,252,464,380,title,body,"teal","white",tag=tag,title_size=31,body_size=27)
    s.box(72,650,1456,99,"What this gives us","An inspectable trail from original observations to admitted conclusions.","blue","ice",title_size=26,body_size=24)
    band(s,"A repeated message, a new conclusion and an independent observation mean different things.",size=26)
    note(s,"ELI16 assumes a technically curious sixteen-year-old. The analogy explains responsibilities, not an additional experiment. C1 records occurrences and provenance. C2 distinguishes admission from numerical aggregation and retains disagreement. The pure providers reuse guarded Truth_Revision and one grounded Truth_Deduction rule. Their outputs remain model-specific heuristics, not proof of external truth or source independence. Derived conclusions inherit evidence roots and ancestry and add no observation or evidence count. Generated observations and operator assumptions remain fixtures, even when they travel through real runtimes.")

    s = Slide("ELI16: a priority list and a limited attempt budget", "Executive summary · 2 of 5",
              "There are two prepared questions, but time for only one calculation. Which should run first?",source="C3 attention · C4 bounded inference")
    s.box(72,254,464,272,"C3 · Priority list","Give each eligible task an integer score. Rank it, decay it explicitly, and remember feedback once.","blue","ice",title_size=34,body_size=29)
    s.box(568,254,464,272,"C4 · Work coordinator","Choose from that list. Save the attempt reservation before calculation, then track admission and feedback.","teal","mint",title_size=34,body_size=29)
    s.box(1064,254,464,272,"Restart · Same budget","Reopening the notebook does not refill the budget. Recover a saved decision; do not credit it twice.","amber","sand",title_size=34,body_size=29)
    s.line(536,390,568,390,C["blue"],arrow=True);s.line(1032,390,1064,390,C["teal"],arrow=True)
    s.box(72,574,704,159,"Observed in real Hive","One native action, one admitted conclusion, one feedback credit; restart and replay tested.","teal","white",title_size=29,body_size=26)
    s.box(800,574,728,159,"The deliberate tradeoff","A crash can spend the last attempt without producing a conclusion. The receipt says so.","amber","white",title_size=29,body_size=26)
    band(s,"Priority is not truth. A bounded step finishing is not a promise that a conclusion was found.",size=26)
    note(s,"Short-term importance, or STI, is a simple deterministic priority score. It is separate from PLN truth values. C4 handles a fixed explicit workset; it does not invent new tasks or search the knowledge base. The measured two-task experiment changes initial attention to select the other task while keeping the one-attempt budget fixed. Attempts are durable physical evaluation opportunities. A crash after reservation spends the slot even if no result commits. Successful replay recovers recorded admission and feedback without extra native calls. These are local process-restart observations, not hard real-time or production-quality claims.")

    s = Slide("ELI16: finishing the job and settling its receipts", "Executive summary · 3 of 5",
              "A notebook entry, a calculation and a reward can finish at different times.",source="M3.1 delivery closure · owner receipts")
    for x,tag,title,body,color in [
        (72,"C1 + RELAY","The report was processed","The notebook gets a delivery receipt even when a report cannot change a number. Contrary evidence stays in the story.","teal"),
        (568,"C3 · ATTENTION","The reward has one outcome","Ask the priority-list owner: already credited, retired without credit, or still pending. A lost reply never earns a second reward.","blue"),
        (1064,"C4 + HIVE","The receipt tells both stories","Show the original work result and the later cleanup progress separately. Cleanup does not buy another attempt.","amber")]:
        s.box(x,252,464,390,title,body,color,"white",tag=tag,title_size=31,body_size=27)
    s.box(72,650,1456,99,"Observed","33 observations drained; 20 new process-kill cases; no new formula calls during reconciliation.","teal","mint",title_size=25,body_size=23)
    band(s,"M3.1 settles recorded effects. It does not extend the deadline, change the past or start new thinking.",size=25)
    note(s,"Closure means accounting for recorded effects, not guaranteeing global completion. Nine fixture methods, five real-provider methods, sixteen direct SIGKILL cases and seven native Hive cases (four with kills) support the new behavior. The 33-event episode uses real DeTTa/native PLN with generated observations. A report can be durably processed without a numerical truth value. Feedback resolution never newly applies eligible feedback: it returns an existing receipt, creates a no-credit retirement if stale or expired, or stays pending. C4 exposes progress separately from immutable execution counters. New profiles require fresh journals; old M3 pending stores are not migrated or repaired.")

    s = Slide("ELI16: approve a fingerprint, then check the receipt", "Executive summary · 4 of 5",
              "Imagine signing a sealed envelope containing the fingerprint of one shareable result.",source="M4 · native Hive → isolated F1R3node")
    for x,tag,title,body,color in [
        (72,"1 · APPROVE","Name the exact result","Hive finishes a generated task. The operator approves that result, its destination and who may sign it.","blue"),
        (568,"2 · SAVE, THEN SEND","Keep the same envelope","Save the signed request before sending. After a crash, retry those same bytes; a lost reply does not mean a new request.","amber"),
        (1064,"3 · VERIFY","Read what was stored","Check the fingerprint in the block’s resulting state and the matching deployment’s finalized effect. Repeat after restart.","teal")]:
        s.box(x,252,464,390,title,body,color,"white",tag=tag,title_size=31,body_size=27)
    s.box(72,650,1456,99,"Private notebooks stay private","Only the approved generated workflow is eligible. Episodes, beliefs and their identifying hashes stay off-chain.","teal","mint",title_size=25,body_size=22)
    band(s,"A stored fingerprint identifies the approved result. It does not establish that the reasoning is true.",size=25)
    note(s,"The sealed-envelope analogy describes durable signed-intent replay. M4 uses the real native fusion-inspect operation and a separate fusion-commitment action, with generated shareable input and a labelled fixture counterparty. Operator approval binds exact result reference/digest, actor, expiry, chain/genesis/profile, signer and operation. The same stored signed request survives caller/adapter kills, including a lost response after real finality. A separate reader verifies DA bytes and the chain tuple without opening a caller journal or signing key. The chain records a commitment; it neither executes PLN nor certifies off-chain reasoning. This is one real local validator, not decentralized security or a production network.")

    s = Slide("ELI16: a catalogue, labelled links and the actual books", "Executive summary · 5 of 5",
              "Ask the library for matching records, follow their links, then read the stored content.",source="M5 · actual native fusion-lookup")
    for x,tag,title,body,color in [
        (72,"SEARCH · CATALOGUE","Find matching records","Ask for exact attributes. The catalogue returns references and says how far it has indexed the accepted records.","blue"),
        (568,"RELATIONS · LINKS","Follow explicit structure","A record may require three other records. Follow the labelled, ordered roles to discover their references.","teal"),
        (1064,"ATOMSTORAGE · BOOKS","Retrieve the actual bytes","Read the discovered references through the storage contract. The consumer was never given an answer list.","blue")]:
        s.box(x,252,464,390,title,body,color,"white",tag=tag,title_size=31,body_size=27)
    s.box(72,650,1456,99,"Observed in real Hive","5 matching records → 15 relations → 8 payloads. Append, catch up, rebuild, restart and replace Search.","teal","mint",title_size=25,body_size=23)
    band(s,"“No match in this indexed prefix” and “the index is too far behind” are different answers.",size=26)
    note(s,"The catalogue is a rebuildable projection of an AtomStorage-owned accepted commit feed. It indexes a single explicit exact-attribute profile; it is not an embedding engine or inference search. Relations owns acceptance and incidence separately from immutable payload storage. Setup writes the generated corpus through public ports and exits before actual authenticated native Hive lookup. The private request contains query attributes and a freshness barrier only. The test-only oracle is removed before consumer startup. At page size two, five roots require three Search pages. Fifteen requires edges connect them to three prerequisites, producing eight unique payloads. One new matching record later yields six roots and nine payloads. Public receipts show counts/status; full records remain private.")

    s = Slide("Fifteen modules; four responsibility groups", "01 / Helicopter view",
              "A module owns a responsibility. It need not be a separate process or repository.")
    lanes=[(72,320,"CLIENT / COGNITION","lavender"),(420,400,"APPLICATION PORTS","ice"),
           (848,322,"CONTROL & POLICY","pale"),(1198,330,"PROVIDER ADAPTERS","mint")]
    for x,w,title,fill in lanes:
        s.rect(x,230,w,495,C[fill],radius=14);s.text(x+18,251,w-36,title,18,C["ink"],"bold")
    for i,(label,color) in enumerate([("Episodic memory","blue"),("Belief revision","blue"),
                                     ("PLN · one rule","blue"),("STI attention","blue"),("Inference control","blue")]):
        s.box(90,300+i*78,284,62,label,color=color,title_size=22,dashed=color=="violet")
    for i,(label,color) in enumerate([("AtomStorage","blue"),("Relations","blue"),
                                    ("Search projection","blue"),("Agent messaging","blue"),("Delegated execution","blue")]):
        s.box(438,300+i*78,364,62,label,color=color,title_size=23,dashed=color=="violet")
    for i,label in enumerate(["Registry","Compatibility resolver","Authorization"]):
        s.box(866,300+i*108,286,95,label,color="blue",title_size=22)
    s.box(1216,300,294,144,"DA storage","Real local DeTTa","teal",title_size=27,body_size=23)
    s.box(1216,485,294,168,"Consensus / finality","Real isolated F1R3node · M4","teal",title_size=26,body_size=22)
    s.text(866,649,282,"Local test policy\nand static descriptors",20,C["muted"])
    s.tag(72,760,"15 / 15 BOUNDED FAMILIES","blue",C["ice"],16)
    s.tag(365,760,"IMPLEMENTED LOCAL","blue",C["ice"])
    s.tag(687,760,"REAL PROVIDER","teal",C["mint"])
    s.text(987,766,540,"One grounded rule; no ECAN or LTI",20,C["muted"])
    note(s,"All fifteen responsibility groups remain visible. C1/C2 implement private memory and beliefs; M3 adds independent STI and bounded C4 plus a pure kernel for one grounded rule. M5 implements bounded Relations and exact-attribute Search with explicit private profiles. All fifteen reference families are represented; this is not full Omega requirement coverage. Attention implements a bounded reference policy, not ECAN, LTI or the coupled metta-attention algorithm. RevisionMath is separate from PLNKernel.applyRule. Hive consumes these modules; a module need not be a separate process or repository. Blue means implemented local contracts, not production readiness. Authorization uses real Hive authentication followed by local test policy. M4 selects a new explicit finality profile against clean pinned F1R3node; the required real chain gate passes. It commits only the approved generated inspect result, with no cognitive dependency. Maintainer assignments remain unassigned.")

    s = Slide("Data responsibilities: bytes → references → history", "01 / Responsibility atlas · 1 of 3",
              "Persistence, identity, structure, discovery and provenance have different owners.")
    table(s,["Module","Function / primary operations","Owned state / status"],[
        ("DA storage","Persist opaque bytes\nput · get · availability","Payloads + shares\nREAL LOCAL PROVIDER"),
        ("AtomStorage","Scoped immutable envelopes\ncreate · get/getMany · head/readCommits","Reference + replay + accepted feed\nIMPLEMENTED · M5"),
        ("Relations","Represent ordered structural roles\nassert/getRelation · outgoing/incoming","Accepted structures + incidence\nIMPLEMENTED · M5"),
        ("Search projection","Find refs at a known watermark\nquery · catchUp · beginRebuild","Index + checkpoint + generation\nIMPLEMENTED · M5"),
        ("Episodic memory C1","Record / append / read ordered events\npendingEvidence · trusted completion","Private history + delivery intents\nIMPLEMENTED · M3.1")],[330,600,526],row_h=92,size=24)
    band(s,"DA persists bytes. Only the application owners interpret events, claims or beliefs.",size=27)
    note(s,"AtomStorage owns immutable scoped references and replay metadata, while DA only persists opaque payloads and generic coordinates. AtomStorage now offers an accepted commit feed in a fresh profile. Relations owns accepted structure and incidence; Search owns only a rebuildable projection and checkpoint. All four relation operations and query/catchUp/beginRebuild are exercised through declared ports. C1 exposes recordEpisode, appendEvent, readEpisode, readEvidence and pendingEvidence. The new local v3 completion port is bound to a trusted relay context separately from the ordinary EpisodeJournal. C1 validates completion identity and selected consumer, not PLN snapshots. Original v2 remains selectable. findEpisodes is not advertised. C1 preserves committed episode-local order and admitted provenance; observed time is metadata. It can run without C2 or PLN and against an independently implemented AtomStorage fixture. Its event bytes are immutable atoms, while its episode head and delivery intents belong to C1.")

    s = Slide("Cognitive responsibilities: four separate roles", "01 / Responsibility atlas · 2 of 3",
              "Attention, belief admission, pure mathematics and work coordination remain separate.")
    table(s,["Module","Function / primary operations","Owned state / boundary"],[
        ("Belief revision C2","submitEvidence · readBelief\nsubmitDerivation · readDerivation","Supports, snapshots, attempts\nOnly C2 commits belief changes"),
        ("PLN kernel","Apply one grounded rule to exact premises\nprofiles · applyRule","No mutable domain state\nPure native proposal"),
        ("Attention C3","select · advance · submitStimulus\nsubmitFeedback · resolveFeedback","STI, clock, causal receipts / retirement\nNo cognition dependency"),
        ("Inference control C4","Run one immutable workset\nstep · readProgress · reconcile","Selection, budgets, closure progress\nNo truth or attention ownership")],[330,630,496],row_h=109,size=24)
    band(s,"C4 calls C2 for admission. C2 invokes the kernel, then checks authority and commits its decision.",size=25)
    note(s,"C3 implements the bounded sti-additive-linear-decay/1 reference policy, not ECAN or the inspected metta-attention implementation. C4 owns selection and physical attempt reservations; it depends on AtomStorage, Attention, DerivedBeliefRevision and PrivateAuthority. It does not call PLNKernel directly. C2 depends on AtomStorage, C1 readEvidence, RevisionMath, PLNKernel and PrivateAuthority. The pure kernel owns no belief, agenda or attention state. M2 revision-only local v2 remains selectable; derived private C2 is a fresh local v3 profile.")

    s = Slide("Control responsibilities: move work, preserve authority", "01 / Responsibility atlas · 3 of 3",
              "The remaining six modules connect owners and report specific facts.")
    table(s,["Module","Function / primary operations","Owned state / status"],[
        ("Messaging","Accept, deliver, acknowledge\nsend · poll · ack","Inbox + deduplication · IMPLEMENTED"),
        ("Execution","Run one named operation\nsubmit · status · result","Jobs + completion outbox · IMPLEMENTED"),
        ("Registry","Describe configured providers\ndescriptors","Static configuration · IMPLEMENTED"),
        ("Resolver","Match required semantics\nresolve","No mutable state · IMPLEMENTED"),
        ("Consensus / finality","Submit approved commitment; observe\nsubmit · observe","Signed intents + observations · REAL M4"),
        ("Authorization","Check current caller + scope + method\nauthorize / live policy checks","Operator policy · LOCAL FIXTURE")],[330,590,536],row_h=82,size=23)
    note(s,"Messaging acceptance differs from delivery and acknowledgement. Execution accepts only inspect_atom and owns jobs plus its completion outbox; result atoms commit independently. The registry advertises descriptors, and the resolver matches consumer requirements. Neither grants permission. Finality owns durable logical/signed intents and verified chain observations in M4; it is not a C1/C2 dependency. Native commitment progress holds only caller mapping and receipts. Native authentication supplies trusted actor context, while local Fusion policy determines current access. The preserved M2 relay is a narrow delivery cursor between C1 and C2. M3 C4 separately owns its bounded step journal; neither grants authority.")

    s = Slide("Function dependencies: the exercised M3.1 path", "01 / Dependency map · private cognition",
              "Arrows point from caller to provider; the relay and every state owner commit separately.",source="cognition.py · ports.py · evidence_relay.py")
    s.box(72,240,350,118,"Native Hive plugin","Scenario + trusted actor","teal","mint",title_size=29,body_size=23)
    s.box(555,240,440,118,"C4 · InferenceControl","step · readProgress · reconcile","blue","ice",title_size=29,body_size=23)
    s.box(1128,240,400,118,"C3 · Attention","select · submit/resolveFeedback","blue","ice",title_size=29,body_size=22)
    s.line(422,298,555,298,C["teal"],arrow=True);s.line(995,298,1128,298,C["blue"],arrow=True)
    for x,w,title,body,color,fill in [
        (72,300,"C1 · Episodes","readEvidence · pending · ack","blue","white"),
        (444,300,"Evidence relay","submit → validate → ack","blue","ice"),
        (816,340,"C2 · Beliefs","submit/read decisions","blue","ice"),
        (1228,300,"Pure PLN","applyRule / revise","teal","mint")]:
        s.box(x,480,w,120,title,body,color,fill,title_size=27,body_size=21)
    s.line(444,540,372,540,C["blue"],arrow=True);s.line(744,540,816,540,C["blue"],arrow=True)
    s.line(1156,540,1228,540,C["teal"],arrow=True)
    s.path([(930,358),(930,480)],C["blue"])
    s.text(973,401,500,"C4 → C2: read / submit derivation",20,C["blue"])
    s.path([(160,358),(160,421),(594,421),(594,480)],C["teal"])
    s.text(181,388,620,"Scenario appends C1 events, then drains via relay",19,C["teal"])
    s.path([(986,600),(986,650),(222,650),(222,600)],C["blue"])
    s.text(413,620,495,"C2 → C1: readEvidence",20,C["blue"])
    s.box(72,704,1000,107,"C1 / C2 / C4 → private AtomStorage → real DeTTa","Opaque bytes below the application boundary; each owner keeps its own journal.","teal","mint",title_size=27,body_size=23)
    s.box(1128,704,400,107,"Authority + descriptors","Checked at every owner port","blue","pale",title_size=26,body_size=22)
    note(s,"This graph shows exercised calls. Hive's scenario appends private C1 events and uses the selected relay as its only new-profile evidence-admission path. Relay calls C1 pending/ack and C2 submitEvidence; it validates the complete selected C2 decision before attesting completion to C1. C4 reads private task/workset atoms and C2 snapshots, selects through C3, reserves work and submits or recovers C2 derivations. C4 reconciliation calls only Attention.resolveFeedback on recorded intents: no task selection, C2 admission or PLN call. C2 reads evidence through C1 and calls the unchanged pure math providers. C3 requires authority and reference syntax only. Bottom cards summarize storage/authority dependencies; each owner has an independent local commit. Original M2/M3 profiles remain selectable.")

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
    s.text(87,796,1360,"M4 adds a separate commitment caller after acceptance; this original inspect path stays unchanged.",21,C["muted"])
    note(s,"Follow the real native dispatch into the thin plugin, which holds a caller-owned receipt and uses Subprocess/Peer through descriptor-bound validation. Direct storage, messaging and execution calls all cross the same authenticated boundary. Trusted composition supplies concrete owners; the plugin never constructs them or accesses their tables. Messaging.send validates the referenced bytes through caller-authorized AtomStorage.get; Execution.submit reads the input before accepting a new job. The worker calls declared AtomStorage get/create, then execution commits terminal state/outbox. CompletionDelivery.accept belongs to the mailbox owner and commits separately. The original M1.2 operation does not invoke chain. M4 adds a separate native sibling and caller-owned completed-result accessor after acceptance. This is a logical call map; it does not force one process per module.")

    s = Slide("Function dependencies: an approved result reaches finality", "01 / Dependency map · M4 shared workflow",
              "A native sibling consumes the completed inspect result; private cognition has no chain dependency.",source="hive/commitment · completed.py · f1r3_m4.py")
    s.box(72,244,420,136,"Native Hive dispatch","Authenticated original_command","teal","mint",title_size=29,body_size=24)
    s.box(588,244,420,136,"fusion-commitment","commit / observe(original_command)","blue","ice",title_size=29,body_size=22)
    s.box(1104,244,424,136,"Operator policy","Exact result + actor + chain + signer","blue","ice",title_size=29,body_size=24)
    s.line(492,312,588,312,C["teal"],arrow=True)
    s.line(1008,312,1104,312,C["blue"],arrow=True)
    s.box(72,430,420,113,"Completed-result accessor","Read inspect acceptance + ack","blue","ice",title_size=27,body_size=23)
    s.box(72,577,420,113,"AtomStorage → DeTTa","Re-read exact shared bytes","teal","mint",title_size=29,body_size=24)
    s.box(588,503,420,140,"ConsensusFinality","submit · observe\nLogical intent + signed journal","blue","ice",title_size=29,body_size=24)
    s.box(1104,503,424,140,"Real local F1R3node","Fixed tuple → inclusion post-state\nMatching deploy-effect finality","teal","mint",title_size=29,body_size=24)
    s.line(798,380,798,503,C["blue"],arrow=True)
    s.path([(650,380),(650,425),(535,425),(535,486),(492,486)],C["blue"])
    s.path([(710,380),(710,462),(550,462),(550,633),(492,633)],C["teal"])
    s.text(817,426,700,"Typed session + explicit descriptor/profile",21,C["blue"])
    s.line(1008,573,1104,573,C["teal"],arrow=True)
    s.box(72,716,1456,105,"Each owner commits separately","DA · job/outbox · messaging · inspect acceptance/ack · signed intent/observation · native progress","blue","pale",title_size=29,body_size=23)
    note(s,"Arrows show caller-to-provider dependencies, not a cross-owner transaction. Actual authenticated Programs dispatch loads the new narrow sibling fusion-commitment. Its only user parameter is original_command; operator configuration controls the approved generated workflow and selected chain. A read-only completed-result accessor lives beside the original inspect plugin and rechecks accepted/acknowledged result and live authority. The sibling also retrieves exact bytes via the selected AtomStorage interface. A typed local ConsensusFinality session validates the explicit f1r3-generated-post-state/2 profile; existing port signatures and the legacy adapter are unchanged. The adapter owns logical plan, signed request, submission and observation state. The caller owns only command/progress mapping and calls no other owner's SQL. The original inspect plugin, cognition and DA core are unchanged. Private C1/C2/C3/C4 state has no edge to the chain.")

    s = Slide("Function dependencies: discover → traverse → retrieve", "01 / Dependency map · M5 private lookup",
              "Solid arrows show caller-to-provider calls; each owner commits its own state.",source="lookup.py · lookup_composition.py · ports.py")
    s.box(72,235,380,126,"Native Hive dispatch","Authenticated request label","teal","mint",title_size=30,body_size=25)
    s.box(610,235,458,126,"LookupConsumer","Private pages, snapshots and result","blue","ice",title_size=30,body_size=25)
    s.box(1190,235,338,126,"Current authority","Scope + caller + operation","blue","white",title_size=28,body_size=23)
    s.line(452,298,610,298,C['teal'],arrow=True);s.line(1068,298,1190,298,C['blue'],arrow=True)
    for x,title,body in [(72,"1 · Search.query","Exact attributes → discovered refs"),(576,"2 · Relations","outgoing / getRelation / incoming"),(1080,"3 · AtomStorage","get / getMany → authorized bytes")]:
        s.box(x,440,448,140,title,body,"blue","white",title_size=31,body_size=24)
    s.path([(715,361),(715,402),(296,402),(296,440)],C['blue'])
    s.line(800,361,800,440,C['blue'],arrow=True)
    s.path([(890,361),(890,402),(1304,402),(1304,440)],C['blue'])
    s.box(72,642,448,139,"Projection maintenance","catchUp / beginRebuild\nAtomStorage head/readCommits/get","teal","mint",title_size=28,body_size=23)
    s.box(576,642,448,139,"Relation acceptance","assertRelation → AtomStorage\nPayload first; acceptance separately","blue","ice",title_size=28,body_size=23)
    s.box(1080,642,448,139,"Opaque DA · DeTTa","AtomStorage calls put/get\nDA interprets no query or relation","teal","mint",title_size=28,body_size=23)
    s.line(1304,580,1304,642,C['teal'],arrow=True)
    s.text(74,603,1400,"Setup and bounded maintenance use separate commands. Query never advances the index.",23,C['muted'])
    note(s,"LookupConsumer depends only on ExactSearch, PagedRelations, AtomStorage and current private authority. Numbered calls show discovery, one-hop traversal including reverse-incidence verification, and payload retrieval. The caller owns its journal and retained full result. Search owns derived rows, checkpoint and generation and reads only declared source ports; it never opens another owner's database. Relations owns accepted structures, replay keys and incidence; immutable relation payload creation commits before relation acceptance. AtomStorage owns immutable envelopes plus its contiguous scoped accepted feed, above unchanged opaque DeTTa. Head/readCommits/get dependencies belong to maintenance, not query. Neither lookup nor these new owners invokes C1/C2, attention, inference or chain. Existing caller intents retain their selected provider; fresh replacement uses a new request and rebuilt derived store.")

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

    s = Slide("Independent replacements preserve the caller contract", "02 / Provider replacement",
              "Select explicit profiles; rebuild derived state through the authoritative source.",source="M1.1 · M3 · M5 substitution evidence")
    for x,title,body,color in [
        (72,"AtomStorage · M1 / M5","Real DeTTa-backed owner or atomic-file fixture. The M5 feed remains ordered and replayable.","teal"),
        (568,"Attention · M3","SQLite or atomic-file fixture. Same STI policy, tasks and budgets; same consumer outcomes.","blue"),
        (1064,"Search · M5","SQLite or atomic-file fixture. Same corpus and prefix; independent predicate evaluation and persistence.","teal")]:
        s.box(x,252,464,370,title,body,color,"white",title_size=32,body_size=29)
    s.text(76,660,1430,"The Search fixture still answers when the primary predicate helper is disabled.",28,C["ink"],"bold")
    band(s,"Fresh stores and explicit profiles; accepted state is not migrated.",size=29)
    note(s,"M1.1 covers two AtomStorage implementations times two bindings. M5 adds independent atomic-file feed and Search fixtures. Search shares only pure DTO validation, extraction and encoding, not primary SQL, owner transitions or the predicate helper. A regression disables the primary predicate helper while the fixture evaluates positive and empty queries. Native lookup keeps the same consumer, source, corpus and prefix across replacement; the new Search store rebuilds its derived state. Provider choice is bound to an existing caller intent, so substitution uses a fresh request. Attention retains its separately implemented transitions. File providers are labelled fixtures, not second production services. No populated-state migration is claimed.")

    s = Slide("Private state has explicit owners and placement", "02 / Privacy and authorization",
              "A trusted Hive actor maps to an operator-configured private scope and credential.",source="cognition.py · inference_program/program.py")
    s.rect(72,243,940,487,C["ice"],radius=14)
    s.text(98,268,890,"PRIVATE LOCAL COMPOSITION",23,C["blue"],"bold")
    for x,y,title,body in [(98,329,"C1 · Episodes","History + delivery intents"),(555,329,"C2 · Beliefs","Supports + exact attempts"),(98,516,"C3 · Attention","STI + clock + causal replay"),(555,516,"C4 · Controller","Budgets + progress + feedback")]:
        s.box(x,y,430,150,title,body,"blue","white",title_size=29,body_size=25)
    s.box(1082,243,446,212,"Public Hive receipt","Generated counters, status and public command receipt ID.","teal","mint",title_size=32,body_size=28)
    s.box(1082,493,446,237,"Private trace","Task/support hashes, premises, lineage, attention and payloads stay private.","amber","sand",title_size=32,body_size=28)
    band(s,"Shared M1 wire and DA contracts stay unchanged; every owner rechecks current authorization.",size=25)
    note(s,"The native plugin receives authenticated actor context and derives authority from operator configuration. Request parameters cannot select credentials, arbitrary scopes or private premise identities. Public parameters are generated seed, preference a/b and an absolute deadline. Privacy tests intercept shared bindings, populate shared stores and inspect native receipts/logs/state for canaries and private hashes. This is tested local placement under a trusted operator/host, not secrecy from administrators. Each journal has one owner and commits independently; there is no cross-owner SQL transaction.")

    s = Slide("Executable contracts make the inference step finite", "02 / Contract decisions before behavior",
              "The supported task is explicit, immutable and grounded before the controller starts.",source="attention_contracts.py · cognition_contracts.py")
    table(s,["Contract","What is fixed","Why it matters"],[
        ("Context + task","Private context; exact role references","Labels cannot merge distinct identities"),
        ("Workset","1–16 unique immutable tasks","No search or automatic task expansion"),
        ("Premise snapshot","Claim / context / revision / support ID","No silent substitution with latest state"),
        ("Derived support","Closed tag + inherited roots / ancestry","No fresh observation or evidence count"),
        ("Work budget","Candidates, attempts, generation, deadline","Restart cannot silently refill the allowance")],[330,625,501],row_h=91,size=24)
    band(s,"Profile mismatch, malformed response or changed semantic intent fails explicitly.",size=27)
    note(s,"The contracts use closed bounded DTOs and detach nested request inputs before authorization or foreign calls. A task binds P,Q,R,P⇒Q,Q⇒R to exact private references. Premise vectors record each belief's historical revision and support ID; the upstream knowledge revision of zero is only a local evaluation ID, not a global ledger. Derived support tags distinguish observation, two-local-premise revision and five-foreign-premise deduction. C2 local v3 is explicit and does not widen M2 v2. WorkBudget contains an absolute Unix-ms deadline, max_candidates, max_rule_applications and max_feedback_generation. Historical reads and recovered owner responses are validated against the exact request.")

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

    s = Slide("C1 delivery closes without understanding PLN", "03 / M3.1 evidence delivery",
              "Completion attests durable processing. Belief support and numerical truth remain C2 responsibilities.",source="delivery_contracts.py · evidence_relay.py · m3_1 evidence")
    steps=[("C1 event","Event + delivery intent"),("C2 decision","Full selected-profile result"),("Relay decision","Validate + save completion"),("C1 acknowledgment","Exact identity + live consumer"),("Relay acknowledgment","Save progress; recover replies")]
    for i,(title,body) in enumerate(steps):
        x=72+i*294
        s.box(x,260,280,184,title,body,"teal" if i in (1,3) else "blue","white",title_size=25,body_size=24)
        if i<4:s.line(x+280,352,x+291,352,C["muted"],arrow=True)
    s.box(72,504,704,223,"33 events · one persistent episode","Append 16 → drain to 0\nAppend 16 → drain to 0\nAppend 1 → drain to 0","teal","mint",title_size=32,body_size=28)
    s.box(800,504,728,223,"Acknowledgment is model-independent","The trusted relay checks C2's full decision. C1 checks its event, delivery, request and selected consumer; it parses no PLN snapshot.","blue","ice",title_size=30,body_size=27)
    band(s,"16 pending deliveries is still the bound. Draining frees pending capacity; episode lifetime stays 256 events.",size=24)
    note(s,"Five commits belong to three owners; there is no cross-owner transaction. The selected adapter validates exactly one C2 profile and full response, including v3 support fields after a real deduction. C1 accepts trusted-evidence-completion/1 through a separately bound context unavailable to ordinary episode/Hive clients. A completion identifies scope, delivery, exact evidence/claim/context, selected consumer, request and decision digests. It asserts committed processing, not truth. Relay recovers its own committed intents when the C1 acknowledgment response was lost and the delivery no longer appears pending. The real-provider run drains 33 generated observations in batches 16/16/1. Capacity testing refuses append 17, then uses public drain before appending. Reports and unregistered-origin observations close as model-inapplicable with null numerical truth; contrary observations remain retained. Four evidence boundaries times two providers give eight direct kills, plus two native caller evidence kills.")

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
    note(s,"This slide describes preserved observation admission. M3 adds a separate derivation command with inherited evidence, described next. The first eligible explicit assessment initializes the aggregate. Later evidence is retained without automatic aggregation unless an exact pair assumption and guards permit revision. Unknown origins cannot initialize a justified numerical aggregate. A report without numerical assessment is model-inapplicable. The ledger retains observations, support records, immutable snapshots and exact decisions. A later authorized independence declaration may combine already admitted supports, without creating another observation. Exact successful replay returns the original historical decision even after later revisions; a new-key duplicate returns current state without adding weight. Retained-alternative is a pair outcome, so an already covered ancestor need not produce a new alternative list entry or revision. Coverage fields state the actual result.")

    s = Slide("A derived conclusion inherits its evidence trail", "03 / Derived-support admission",
              "The result is a new support record, while its original observations and ancestry remain the same.",source="derived_beliefs.py · pln_deduction.py")
    for i,label in enumerate(["P","Q","R","P ⇒ Q","Q ⇒ R"]):
        x=72+i*296
        s.box(x,249,272,135,label,"Exact historical support","blue","ice",title_size=35,body_size=22)
        s.path([(x+136,384),(x+136,429),(800,429)],C["blue"],arrow=False)
    s.line(800,429,800,489,C["teal"],arrow=True)
    s.box(421,489,758,142,"Derived P ⇒ R","Inherited evidence roots + actual grounded ancestry","teal","mint",title_size=34,body_size=26)
    s.text(78,680,1430,"Unknown target: initialize inferential support. Existing truth: keep the alternative.",28,C["ink"],"bold")
    band(s,"No new observation, root, independence assertion or evidence count is created.",size=29)
    note(s,"The five foreign premises are not five independent observations of the output claim. local-admitted-supports/1 treats the deduction as one local support unit with its inherited evidence/root union. Logical derivation identity is independent of request/step IDs, deadlines and output CAS. A duplicate cannot gain another admission or causal feedback credit. A separately authorized independence assumption can request the unchanged guarded native revision of eligible supports. Derive → revise retains grounded ancestry; a cyclic subsequent deduction is refused. Claims remain heuristic and lineage-aware, not calibrated uncertainty or proven entailment.")

    s = Slide("One grounded rule reuses the actual native PLN", "03 / Kernel and runtime compatibility",
              "No replacement arithmetic and no general search loop: five explicit premises produce one proposal.",source="deduction-sources.json · integration/pln/test_deduction.py")
    for x,w,title,body in [(72,420,"Fusion PLNKernel","Exact bindings, source/profile checks and remaining deadline"),(560,480,"Pinned Reachability","PLNAdapter.apply_rule\nDeductionRule + guards"),(1108,420,"Native PLN / PeTTa","Truth_Deduction\nSWI 10.1.14 + Janus")]:
        s.box(x,260,w,224,title,body,"teal","mint",title_size=31,body_size=28)
    s.line(492,372,560,372,C["teal"],arrow=True);s.line(1040,372,1108,372,C["teal"],arrow=True)
    s.box(72,548,704,183,"Two probability checks","Upstream exact Python precheck and the native consistency guard both apply.","blue","ice",title_size=30,body_size=27)
    s.box(800,548,728,183,"Separate compatibility profile","Deduction has its own source/runtime allowlist; the revision-only profile stays intact.","blue","ice",title_size=30,body_size=27)
    band(s,"Kernel output is a proposal. C2 performs final authorization, CAS and admission.",size=28)
    note(s,"The unchanged Reachability dd56f3f implementation invokes PLN 4405956 Truth_Deduction on PeTTa ae66fa8 and SWI source 6977543, version 10.1.14. The exact runtime profile is fusion-petta-swi-10.1.14-deduction/1. No PLN.Derive, PLN.Query or task search is used. The Q>0.9999 branch and its assumptions remain upstream semantics and are tested. Kernel source checks and native subprocesses use the remaining absolute deadline. This pure component owns no belief, agenda or attention state. Source drift, malformed output and timeout are explicit refusals, with fault injections labelled in the native suite.")

    s = Slide("Native goldens check deduction and preserved revision", "03 / Numerical evidence",
              "Independent expected values check pinned native formulas; no replacement math runs in the owners.",source="test_deduction.py · preserved test_revision.py")
    s.box(72,248,704,347,"M3 · Grounded deduction","P, Q, R = (0.5, 0.8)\nP⇒Q, Q⇒R = (0.8, 0.7)\n\nExpected P⇒R: (0.68, 0.3136)","teal","mint",title_size=32,body_size=29)
    s.box(800,248,728,347,"M2 · Guarded revision","(0.75, 0.50) + (0.25, 0.50)\n→ (0.50, 2/3)\n\nUnequal confidence 0.50 / 0.75\n→ (0.375, 0.80)","blue","ice",title_size=32,body_size=28)
    s.text(78,642,1430,"Observed deduction: 0.6800000000000002 / 0.31360000000000005",27,C["ink"],"mono")
    s.text(78,698,1430,"Absolute tolerance 1e−12; finite-domain and lineage guards remain active.",28,C["ink"])
    band(s,"These are model-specific heuristics, not calibrated real-world confidence or proven entailment.",size=25)
    note(s,"The M3 golden has five ordered premises and uses the actual native Truth_Deduction. Expected values are independent test oracles, not production mathematics. M2 revision goldens still pass in the M3 regression, including reversed unequal pairs. Native suites include actual computation plus explicitly injected malformed responses, timeouts, source-drift clones and authorization/CAS interleavings. Fifteen upstream guard-only tests use RecordingRuntime and are not counted as native numerical evaluation. Evidence_count remains null, and a derived conclusion never turns into a fresh independent observation.")

    s = Slide("C3: a small, independent attention policy", "03 / Short-term importance",
              "sti-additive-linear-decay/1 · integer STI · explicit logical time · persistent causal identity",source="attention.py · fixture_attention.py")
    s.box(72,250,464,331,"Stimulate","Add within per-target saturation. Refuse the whole change if the context budget would be exceeded.","blue","ice",title_size=34,body_size=29)
    s.box(568,250,464,331,"Select","Rank positive eligible targets by descending STI, then the full canonical reference. Reads do not decay state.","teal","mint",title_size=34,body_size=29)
    s.box(1064,250,464,331,"Advance","Explicitly decay by logical steps. Stored causal generation survives decay, new ingress and new step IDs.","blue","ice",title_size=34,body_size=29)
    s.text(77,628,1440,"Default limits: 100 STI per target · 300 per context · decay 1 per logical step",29,C["ink"],"bold")
    s.text(77,691,1440,"Only authority and opaque-reference syntax are required; no Hive, storage or PLN runtime.",27,C["muted"])
    band(s,"This reference policy is implemented. ECAN, LTI, diffusion and new attention research are out of scope.",size=24)
    note(s,"The reference policy is frozen in its identity. Bounds are 16 targets, 16 advance steps per call, eight contexts, 512 causes per context, 1024 commands per owner and feedback generation three. Capacities refuse without silent eviction of acknowledged commands. Stimulus saturation is min(amount, Smax-current); total context budget is enforced atomically. Successful replay is checked before logical clock CAS under live authorization. Causal deduplication is independent of request identity; changing a causal body conflicts. Fresh feedback follows the target's current causal parent and next generation. metta-attention 3e1c8147 was inspected but not integrated because it couples STI/LTI/VLTI, wages and shared funds. C3 has no hidden dependency on AtomStorage, C1, C2, PLN or Hive.")

    s = Slide("Attention replacement preserves the measured outcome", "03 / Controlled substitution experiment",
              "Recorded M3 comparison: same tasks, evidence, policy and budgets; provider and preference vary.",source="m3/final/comparison.json")
    rows=[]
    for case in COMPARISON["cases"]:
        label="SQLite" if case["attention_provider"]=="sqlite" else "Atomic-file fixture"
        rows.append((label,case["prefer"].upper()," → ".join(case["selection_order"]),f'{case["step_seconds"]:.6f} s'))
    table(s,["Attention provider","Prefer","Selection order","Step time"],rows,[590,190,346,330],row_h=88,size=27)
    s.box(72,645,704,105,"Every case","1 native call · 1 unique admission · 1 feedback credit","teal","mint",title_size=24,body_size=22)
    s.box(800,645,728,105,"Reopen all owners","Same receipt · zero additional native calls","teal","mint",title_size=24,body_size=22)
    band(s,"Four local observations demonstrate substitution and selection effect; they are not a performance ranking.",size=23)
    note(s,"All four fresh cases use two tasks, five premises per task, ten generated observations, two episodes and twelve claim atoms. Held fixed: exact task/evidence refs, policy parameters, one-attempt/two-candidate budgets, absolute deadline and logical schedule. Separate preference cases exchange initial scores 20/10 and 10/20. Only composition chooses SQLite or the independently implemented file fixture; no consumer code changes. Every result records examined=2, reserved=1, completed=1, refused=0, unique admission=1 and feedback_applied=1, ending at rule-budget. The second candidate is counted before discovering the exhausted rule budget. Preparation takes about 11.5–11.8 seconds and is separate from the reported step time. Store sizes are 1,040,671 and 1,020,409 bytes respectively. These are one-run local measurements, not throughput or cognitive-quality evidence.")

    s = Slide("C4: reserve work durably before invoking the rule", "03 / Bounded inference control",
              "A work budget limits physical evaluation opportunities, even when the process dies.",source="inference.py · deadlines.py")
    for x,title,body,color in [(72,"1 · Freeze selection","Read the immutable workset and exact attention order.","blue"),(442,"2 · Reserve attempt","Commit candidate progress and a physical attempt slot.","amber"),(812,"3 · Ask C2","Recover a decision or dispatch the exact derivation attempt.","teal"),(1182,"4 · Reconcile","Save decision and causal feedback acknowledgment.","blue")]:
        s.box(x,265,346,240,title,body,color,"white",title_size=29,body_size=27)
        if x<1182:s.line(x+346,385,x+367,385,C["muted"],arrow=True)
    s.box(72,565,704,166,"Budget survives restart","Candidate count, reserved attempts, generation limit and absolute deadline are persisted.","amber","sand",title_size=30,body_size=27)
    s.box(800,565,728,166,"Selection changes next step","Current selection is frozen. A unique admission records one causal feedback intent.","blue","ice",title_size=30,body_size=27)
    band(s,"No refund for a lost pending attempt. A new evaluation needs another slot and attempt identity.",size=25)
    note(s,"C4 counts a candidate before resolving it, including unresolved or refused candidates. It commits reservation before dispatch and queries a prior C2 decision first during recovery. C2 persists semantic intent before evaluation, evaluates outside its commit transaction, then rechecks authority and output CAS. A killed pending attempt needs a new reserved slot/key; a committed decision is read back without evaluation. Logical derivation identity is distinct from transport request, controller step, attempt key, deadline and output CAS. Feedback is a fixed one-unit workflow signal tied to logical derivation identity, never a truth update. Absolute Unix-ms deadline survives restart; scheduling/file I/O remain cooperative, not hard real-time.")

    s = Slide("C3 alone settles the feedback outcome", "03 / M3.1 bounded reconciliation",
              "C4 asks about the exact recorded intent. Attention serializes application and retirement.",source="attention.py · fixture_attention.py · inference.py")
    s.box(72,270,390,165,"Exact feedback intent","Original clock, cause, parent, generation and effect deadline","blue","ice",title_size=31,body_size=26)
    s.box(600,270,338,165,"C3 · resolveFeedback","One owner transaction\nor one file-owner lock","blue","ice",title_size=28,body_size=26)
    s.line(462,352,600,352,C["blue"],arrow=True)
    for y,title,body,color,fill in [(238,"APPLIED","Return original durable receipt","teal","mint"),(405,"RETIRED · NO CREDIT","Expired or obsolete clock / parent","amber","sand"),(572,"PENDING","Eligible, unavailable or malformed","blue","ice")]:
        s.box(1070,y,458,143,title,body,color,fill,title_size=27,body_size=24)
        s.path([(938,352),(1000,352),(1000,y+72),(1070,y+72)],C[color])
    s.box(72,503,866,212,"C4 keeps a separate closure journal","1–16 resolutions per call · 128 commands per step\nOriginal execution, spent budget and deadline stay fixed.\nReconciliation makes zero new native formula calls.","teal","white",title_size=31,body_size=26)
    band(s,"Applied before a lost reply → recover once. Retired first → delayed delivery cannot award credit.",size=26)
    note(s,"resolveFeedback never applies fresh eligible feedback. Existing application wins even after expiry or decay; it returns the original receipt without changing current STI. Otherwise stale/expired intent can create a no-credit tombstone atomically; eligible or unavailable/malformed responses remain pending, and revocation fails closed. Application and retirement share SQLite transaction or independent atomic-file locking. Concurrent eligible application versus clock advance/retirement and both serialized outcomes were exercised on both providers. First retirement consumes one existing cause and command slot; existing receipts/tombstones need no new slot. No capacity enlargement or eviction. C4 persists a bounded cursor and separate closure version. Same reconciliation key returns its original observation; fresh keys/readProgress can see newer closure. It never calls selection, C2 admission or PLN, refunds reservations, resets deadlines or retimes feedback. Finite exhausted capacity can leave work pending.")

    s = Slide("Five crash boundaries, independent owner commits", "03 / Recovery · actual SIGKILL",
              "10 direct boundary cases + 5 actual Hive caller boundary cases in the recorded M3 run.",source="test_m3_recovery.py · test_m3_integration.py")
    table(s,["Process dies after…","Durable fact","Recovery result"],[
        ("Attention stimulus commit","C3 causal receipt","Replay does not add STI again"),
        ("C4 attempt reservation","Slot already spent","One-slot budget can end without a result"),
        ("Kernel return; before C2 commit","Pending attempt; no admission","Another evaluation needs another slot"),
        ("C2 belief commit","Authoritative saved decision","Recover without another native call"),
        ("C3 feedback commit; before C4 ack","Credit recorded by logical cause","Recover ack without a second credit")],[500,420,536],row_h=91,size=24)
    band(s,"The evidence proves tested local process recovery, not a distributed transaction or power-loss durability.",size=24)
    note(s,"Three native recovery methods cover ten actual SIGKILL cases: stimulus commit for both attention providers; reservation and kernel-return loss under budgets one and two; belief/feedback recovery for both providers. The real Hive suite adds five actual caller kills across the same boundaries. A one-slot loss conservatively exhausts the budget; a two-slot case may recover one logical admission after another physical calculation. Thus there is no claim of exactly one physical calculation per logical derivation. Committed admission and feedback are duplicate-safe. This is intact-local-file, same-host process restart, not reboot, power loss or distributed failover.")

    s = Slide("Authorization, replay and profiles remain live", "03 / Boundary guarantees",
              "Cached success does not bypass current authority, and compatibility is never silently widened.",source="cognition.py · derived_beliefs.py · tests/test_m3.py")
    table(s,["Trigger","Observed decision","Preserved boundary"],[
        ("Same key, altered nested request","CONFLICT / validation refusal","Exact immutable semantic intent"),
        ("Permission revoked before replay","DENIED","Live authority even for cached receipts"),
        ("Authority / CAS changes during math","Refuse final admission","C2 rechecks before its own commit"),
        ("Runtime or response binding changes","Explicit compatibility failure","No weaker fallback or invented result"),
        ("Clock advances before feedback","Retire without credit via owner","Original clock, parent and generation retained")],[510,470,476],row_h=91,size=24)
    band(s,"Attention ingress and feedback have distinct trusted bindings; selection never grants authority.",size=25)
    note(s,"Input records are copied before foreign calls and authorization so a malicious boundary cannot mutate the retained command. Recovered C2 and attention responses are checked against exact owner/request identities and semantics. Current principal, scope, method and descriptor permissions apply on every invocation. The assumption permission for revision remains separate. Native proposal calculation runs outside the owner commit transaction; final authorization and expected output revision are rechecked afterward. Old-profile feedback can remain CONFLICT after a clock change. The new profile lets Attention resolve recorded stale feedback by no-credit retirement; eligible or unavailable feedback stays pending. The controller never rewrites the logical schedule. These are local trusted-authority guarantees, not a production identity system.")

    s = Slide("One real Hive action reaches the entire private path", "04 / Native integration",
              "Existing authenticated Programs runtime → fusion-inference / infer-generated.",source="inference_program/program.py · test_m3_integration.py")
    s.rect(72,235,1456,85,C["dark"],radius=12)
    s.text(100,259,1390,"POST /api/programs/fusion-inference/act",33,C["white"],"mono")
    xs=[172,590,1008,1426]
    for x,label in zip(xs,["Native Hive","Scenario + relay","C4 / C3 / C2","Native PLN"]):
        s.rect(x-100,366,200,53,C["mint"],radius=7);s.text(x-89,382,181,label,19,C["teal"],"bold")
        s.line(x,432,x,725,C["line"],dash=True)
    for x1,x2,label,y in [(172,590,"1  Trusted actor; generated seed + preference",467),
                          (590,1008,"2  C1 → relay → C2; two tasks, one attempt",525),
                          (1008,1426,"3  Reserve → C2 → actual Truth_Deduction",583),
                          (1426,1008,"4  Proposal → admission → one feedback credit",641),
                          (590,172,"5  Record result; return counters + receipt",711)]:
        left=min(x1,x2)
        if x2==1426 or x1==1426:left=735
        s.rect(left+4,y-29,width(label,20)+12,27,C["bg"])
        s.text(left+8,y-29,1510-left,label,20,C["ink"])
        s.line(x1,y,x2,y,C["teal"],arrow=True)
    band(s,"One private episode: 10 generated observations + action + result. Public receipt contains no private trace.",size=24)
    note(s,"The real pinned Hive create_app, authenticated Programs dispatch, default Supervisor and native PeTTa run in the integration. The narrow sibling plugin uses native assessment role, action infer-generated, and trusted actor mapping. ASGI TestClient, identities, observations and operator assumptions are fixtures; the runtime, DeTTa and formula execution are actual providers. The plugin owns caller intent/receipt and invokes the private scenario; it owns no belief, STI or controller state. The preserved M3 suite has eight native cases and five kills. The new M3.1 suite adds seven native cases, four with actual kills, covering both providers, closure progress, evidence recovery and explicit zero-conclusion execution. The new-profile scenario drains C1 evidence through the relay. The diagram summarizes the call sequence; each owner commits independently. M1 fusion-inspect and M2 fusion-episode remain supported and rerun in regression.")

    s = Slide("Native Hive exposes execution and closure separately", "04 / M3.1 actual caller progress",
              "infer-generated → restart → reconcile-generated(original_command, limit)",source="inference_program/program.py · test_m3_1_integration.py")
    s.box(72,250,704,241,"Original execution · immutable","One examined candidate\nOne reserved / completed attempt\nOne unique admission · zero feedback applied","blue","ice",title_size=31,body_size=27)
    s.box(824,250,704,241,"Later closure · versioned","Same original result and counters\nEvidence backlog and feedback outcomes\nStale feedback retired without credit","teal","mint",title_size=31,body_size=27)
    s.line(776,370,824,370,C["teal"],arrow=True)
    s.box(72,535,704,198,"Lost reply after feedback applied","Recover the original receipt after expiry or decay, even when current STI has reached zero.","teal","white",title_size=29,body_size=27)
    s.box(824,535,704,198,"Expired before execution","Hive can finish the action with zero admissions and zero reservations. Those counts stay explicit.","amber","sand",title_size=29,body_size=27)
    band(s,"Public done / committed means the action returned. Detail reports execution, evidence and feedback closure.",size=24)
    note(s,"The top row summarizes the tested stale-feedback case: original execution has one admission and zero acknowledged feedback; after controlled clock advance STI is nine, and reconciliation retires the stale effect without changing that execution. The bottom row covers separate applied-before-lost-reply and expired-before-execution tests, not one combined run. The actual authenticated native Programs 0.1 dispatcher selects the existing plugin. Prepared original-command mapping is private and persisted before step. Public parameter original_command respects the unchanged Hive credential guard. The response exposes execution status/reason, admissions, original counts/remaining, evidence pending/state, feedback closure counts and version. Private episode/task/support IDs, roots, snapshots, credentials and paths are excluded. Seven native cases include four process kills; both attention providers are exercised. Same public reconciliation identifier replays the same observation; use a new one for newer progress.")

    s = Slide("The same one-attempt budget makes attention visible", "04 / Demonstrated behavior",
              "Two eligible tasks have exact premises. Initial STI selects which one can consume the attempt.",source="m3/final/comparison.json · native Hive scenario")
    for x,title,a,b,winner in [(72,"Prefer task A",20,10,"A"),(824,"Prefer task B",10,20,"B")]:
        s.rect(x,250,704,377,C["white"],C["line"],14)
        s.text(x+26,277,650,title,34,C["ink"],"bold")
        for y,label,value,color in [(365,"A",a,"blue"),(453,"B",b,"teal")]:
            s.text(x+30,y+8,60,label,32,C[color],"bold")
            s.rect(x+110,y,value*21,56,C["ice"] if color=="blue" else C["mint"],radius=7)
            s.text(x+124,y+10,110,str(value),28,C[color],"bold")
        s.text(x+28,555,650,f"First attempt → {winner}",31,C["ink"],"bold")
    s.text(78,675,1440,"Both attention providers preserve this effect; replay adds no native call and no second credit.",27,C["ink"],"bold")
    band(s,"Attention changes scheduling. It does not alter premise truth values or manufacture independent evidence.",size=24)
    note(s,"This chart depicts the explicitly configured STI scores in the controlled scenarios, not a learned score or performance estimate. The comparison exercises both preferences with both providers; the real Hive tests separately exercise actual native action and replacement. A step freezes the ranked selection. Subsequent feedback affects a later step, not the order already accepted. C4 examines two candidates but reserves and executes only one attempt, so terminal reason is rule-budget. All four comparison cases recover identical receipts after reopening owners and invoke the native formula zero additional times on successful replay. Cognitive usefulness of the chosen conclusion is not measured.")

    s = Slide("One artifact connects Hive, DA and the chain", "05 / M4 · measured native workflow",
              "The approved result is the exact result retrieved, committed and independently read back.",source="evidence/m4/final/same-artifact.json · readback.json")
    for x,title,body,color in [
        (72,"53-byte input","Generated and explicitly shareable\nReal native fusion-inspect","blue"),
        (568,"143-byte result","Real worker + real DeTTa\nCaller accepts and acknowledges","teal"),
        (1064,"One commitment","Approved digest in real post-state\nMatching finalized deploy effect","teal")]:
        s.box(x,252,464,207,title,body,color,"white",title_size=34,body_size=27)
        if x<1064:s.line(x+464,354,x+492,354,C["teal"],arrow=True)
    s.rect(72,498,1456,130,C["dark"],radius=12)
    s.text(99,518,1360,"APPROVED RESULT SHA-256 · SAME VALUE AT EVERY STAGE",20,C["dim"],"bold")
    s.text(99,564,1360,M4TRACE["approved"]["commitment_digest"],27,C["white"],"mono")
    t=M4TRACE["timing"]
    s.box(72,643,704,104,"Counts remain stable","1 job · 1 outbox · 2 messages · 2 shared atoms","blue","ice",title_size=24,body_size=22)
    s.box(824,643,704,104,"First finalized-effect observation",f'{t["finality_first_observed_seconds"]:.3f} s · one native observe call · 675 phlo',"teal","mint",title_size=24,body_size=22)
    band(s,"These are local observations from one run, including proposal/observation overhead; no throughput claim.",size=24)
    note(s,f"Generated command {M4TRACE['command']}. The original inspect action creates a 53-byte shared input, sends its reference to the labelled fixture counterparty, delegates inspect_atom and accepts/acknowledges the 143-byte result. The approved digest shown is public generated data, not a private cognitive identifier. Timings: storage/worker/acceptance 2.296 s; signing callback including serialization/imports 0.040513 s; submission HTTP 0.041256 s; full authorized signing/submission 2.522 s; first inclusion and finalized-effect observation 4.066 s; same-genesis node restart to readiness 1.148 s. Signed JSON request 673 bytes; node execution cost 675 phlo. Regressions ran concurrently. Inclusion/finality times include proposal and authorization overhead and are not pure consensus latency. Full exact identifiers and effect transcript are in the same-artifact JSON; a separate read-only process confirms the same digest, deploy, inclusion and post-state.")

    s = Slide("Approval freezes the result and its destination", "05 / M4 · current authority + exact intent",
              "The public action accepts only original_command. Trusted composition supplies all sensitive choices.",source="f1r3_m4.py · hive/commitment/program.py")
    for x,y,title,body,color in [
        (72,249,"Exact result","Generated command + seed + shared scope\nAccepted result reference and digest","teal"),
        (824,249,"Exact authority","Authenticated actor + swarm + expiry\nLive checks on new calls, replay and send","blue"),
        (72,499,"Exact destination","Source/profile + network + shard + genesis\nRegistered signer and protobuf identity","blue"),
        (824,499,"Exact operation","Fixed tuple and gas limits\nCanonical copies detach mutable inputs","amber")]:
        s.box(x,y,704,218,title,body,color,"white",title_size=33,body_size=28)
    band(s,"No caller-supplied code, digest, endpoint, signer or approval; revocation also blocks cached replies.",size=25)
    note(s,"The new profile is f1r3-generated-post-state/2; provider f1r3-local; interface 1.0.0; implementation 0.4.0. Approval binds the exact generated operation to one native principal/swarm, scope, result, expiry, chain and signer. Chain identity is not an RPC URL. The adapter persists canonical copies of approval and binding rather than retaining nested aliases. A negative regression on 1219bb5 demonstrated that a frozen dataclass alone allowed nested mutation; 55ed540 fixes it and passes the full rerun. Current authority is checked for accepted/replayed work and before submission. Wrong result, private scope, changed profile/genesis, malformed receipt or revoked authority fails explicitly. Only this generated shareable inspect workflow is eligible; there is no generic private-state publishing service.")

    s = Slide("Finality is tied to the actual stored effect", "05 / M4 · source-verified readback",
              "Submission, inclusion and verified finalized effect are different observations.",source="F1R3node 9ec1096 · f1r3-generated-post-state/2")
    for x,title,body,color in [
        (72,"1 · Submission","The node accepts the saved signed deploy. The effect is still pending.","amber"),
        (568,"2 · Inclusion","The exact deploy appears in a block with successful execution and cost.","blue"),
        (1064,"3 · Verified effect","Read the exact tuple in that block’s post-state; match the deploy’s finalized effect.","teal")]:
        s.box(x,252,464,253,title,body,color,"sand" if color=="amber" else "white",title_size=33,body_size=28)
        if x<1064:s.line(x+464,380,x+492,380,C["muted"],arrow=True)
    s.box(72,550,704,177,"Fixed on-chain value","(namespace, generated operation ID, approved result digest)","teal","mint",title_size=30,body_size=28)
    s.box(824,550,704,177,"Independent verification","Same digest + deploy + block + post-state after node restart; no caller journal or signer.","blue","ice",title_size=30,body_size=28)
    band(s,"The adapter verifies node-observed evidence. The chain does not certify off-chain PLN reasoning.",size=26)
    note(s,f"Pinned node source was inspected, built and probed before adapter implementation. /api/prepare-deploy derives the unforgeable read name from saved public deployer and timestamp. /api/data-at-name-by-block-hash performs a non-consuming read of inclusion-block post-state. The inspected source ignores the pre-state switch, so this profile fixes usePreStateHash:false. The name must occur in that block's reductions; a later heartbeat or current-head block is not a substitute. Verification checks exact namespace/operation/digest, target signed deploy, successful inclusion/cost and matching deploy-effect Finalized state. A finalized block alone is insufficient. Inclusion block {M4READBACK['inclusion_block']}; post-state {M4READBACK['post_state']}. The separate reader receives DA get-only authority and read RPC, and opens neither signer nor caller journal. Readback is node-observed, not a trustless attestation.")

    s = Slide("A lost reply reuses the same signed request", "05 / M4 · four native SIGKILL boundaries",
              "Persist the logical plan before signing, then persist the complete signed deploy before HTTP submission.",source="evidence/m4/final/recovery-*.json")
    table(s,["Kill boundary","Authoritative durable fact","Observed recovery"],[
        ("After result acceptance","Caller acceptance; completion may need ack","Acknowledge same result, then approve"),
        ("After signed-intent commit","Exact signed bytes and timestamp","Replay with signing key unavailable"),
        ("After node send, before receipt","Original signed deploy identity","Retry after real finality; same request"),
        ("After effect, before progress","Chain observation committed separately","Native caller recovers that observation")],[480,450,526],row_h=108,size=24)
    band(s,"Node outage preserves the off-chain result. Restart the same genesis/data and read the same finalized effect.",size=24)
    note(s,"Four real native caller/adapter SIGKILL cases cover acceptance, durable signed intent, submission-response loss, and observation before caller progress. The last case uses the first native observation with no owner reset. The lost-response test waits for actual finality before retry, demonstrating recovery even when the chain has already completed. Signed bytes, timestamp, signature, gas limits and deploy identity are reused: no re-signing or validity extension. commit replay returns the original submission receipt; observe obtains fresh evidence without signing/submitting. A separate node SIGKILL/outage/restart preserves accepted and acknowledged off-chain state. Original counts remain one job, one outbox, two messages and two atoms. These are same-host process-restart guarantees with intact files, not a distributed transaction, global exactly-once effect or power-loss durability.")

    s = Slide("The real chain ran in a disposable isolated network", "05 / M4 · reproducible source + safe isolation",
              "Clean pinned F1R3node source; no public connection, upstream patch or consensus rewrite.",source="evidence/m4/build/chain.json · final/isolation.json")
    s.rect(72,243,920,488,C["mint"],C["teal"],14)
    s.text(99,269,866,"UNPRIVILEGED NETWORK NAMESPACE · LOOPBACK ONLY",22,C["teal"],"bold")
    s.box(105,337,386,175,"Generated test genesis","One validator\nGenerated stake, wallet and key","teal","white",title_size=30,body_size=26)
    s.box(573,337,386,175,"Real F1R3node","9ec1096e1077…\nFresh source and local build","teal","white",title_size=30,body_size=26)
    s.line(491,423,573,423,C["teal"],arrow=True)
    s.box(105,560,854,134,"Observed sockets stay inside","P2P and gRPC wildcard listeners exist only in the namespace; no route to an external network.","blue","ice",title_size=29,body_size=26)
    s.box(1064,243,464,224,"From the host","All six probed ports refused connections while the node was ready.","blue","white",title_size=32,body_size=29)
    s.box(1064,507,464,224,"From the namespace","External connection failed: ENETUNREACH. Host firewall unchanged.","amber","sand",title_size=32,body_size=29)
    band(s,"Single-validator evidence establishes this local integration; multi-validator safety remains unrun.",size=25)
    note(s,"F1R3node pin 9ec1096e10774926ea8e72f0823482f0bf9213e1 was obtainable from the authorized repository. The historical dirty workspace at the same SHA has eight tracked modifications and one untracked input; it was untouched and unused. M4 deliberately validates the clean source as a new baseline. Fresh node build uses nightly-2026-02-09, cargo --offline --locked -j2 -p node --bin node, debug 0, incremental 0 and RUST_MIN_STACK 8388608. Node binary SHA-256 2021389d8e1a1db0470d55ba6744124e33f2bc44f5155e6cfa662798b4ffd085. Each chain run uses disposable data/genesis within an unprivileged user/network namespace; only loopback is brought up. Live socket/route tests verify actual isolation. All generated nodes are stopped after verification. Warm downloads and possible cached upstream Rust regression binaries are explicit; fresh provider binaries were not copied.")

    s = Slide("Four Relations operations expose accepted structure", "06 / M5 · Relations",
              "Relation meaning includes schema, direction, ordered roles and private scope.",source="relations.py · lookup_contracts.py · m5-contracts.md")
    table(s,["Operation","Responsibility","Observed semantics"],[
        ("assertRelation","Persist payload, then accept structure","Semantic duplicates converge; changed replay intent conflicts"),
        ("getRelation","Read an accepted relation","A payload orphan alone is never an accepted relation"),
        ("outgoing","Page source-role incidence","Fixed accepted head; query-bound continuation"),
        ("incoming","Page target-role incidence","Reverse incidence verified by the native consumer")],[330,540,586],row_h=104,size=25)
    s.text(88,718,1410,"requires: dependent → prerequisite    ·    transfer: 3 roles    ·    association: symmetric",25,C['ink'],'bold')
    band(s,"Role order is preserved. Repeated endpoints and self-links are explicit, with each incidence returned once.",size=24)
    note(s,"All four logical operations are executable in schema-ordered-relations/2, contract 2.0.0. Structural identity excludes the transport idempotency key but includes type/schema/direction/ordered roles/scope. Same-key changed semantics fails CONFLICT. requires/1 is dependent to prerequisite; transfer/1 has sender, object and recipient roles; association/1 has symmetric incidence while retaining stored role order. Pagination fixes an accepted-head snapshot; cursors bind operation, direction, endpoint, principal, scope and owner incarnation. Tests cover ordering, repeats, self-links, symmetric and three-role semantics, malformed records, cross-scope denial and crash recovery. The four operations do not imply a general graph database or transitive traversal engine.")

    s = Slide("A committed source makes the index rebuildable", "06 / M5 · authoritative source",
              "The source enumerates accepted immutable envelopes; Search interprets one declared content type.",source="atom_feed.py · search.py · ports.py")
    for x,title,body,color in [
        (72,"AtomStorage owner","Accept immutable envelope + feed metadata in one local commit. Source UUID, scope and contiguous sequence identify the prefix.","blue"),
        (568,"Bounded maintenance","Read head/readCommits, retrieve bytes with get, validate each envelope, then extract exact attributes. At most eight new records per call.","teal"),
        (1064,"Search owner","Commit derived index rows + checkpoint together. Replay resumes from that committed prefix. beginRebuild creates a new generation.","blue")]:
        s.box(x,255,464,368,title,body,color,"white",title_size=32,body_size=28)
    s.line(536,432,568,432,C['blue'],arrow=True);s.line(1032,432,1064,432,C['teal'],arrow=True)
    s.box(72,645,1456,108,"Fail without advancing","Gaps, unavailable bytes, forged metadata or changed anchors block the batch; no invented prefix.","amber","sand",title_size=25,body_size=23)
    band(s,"No foreign owner database is read. The alternate provider consumes the same declared source.",size=27)
    note(s,"Fresh AtomStorage contract 1.1.0 selects immutable-commit-feed/1. The new owner keeps accepted envelope and feed metadata atomically, while opaque DA storage commits independently before acceptance. The feed contains reference, content type, size and sequence, not interpreted knowledge. Search retrieves and validates every envelope, even when its valid content type will be ignored. It indexes only application/fusion-knowledge-v1 under knowledge-attributes/1. No feed entry or checkpoint advances over a failed item. Rebuild clears only derived state, captures a head, changes generation and remains unavailable to queries until that prefix is complete; replay keys and bounded progress survive process kills. Source rollback is rejected. There is no pruning API or automatic repair.")

    s = Slide("A complete page is not a promise of current knowledge", "06 / M5 · exact query + freshness",
              "Search returns separate, inspectable claims about what it has actually indexed.",source="lookup_contracts.py · m5-contracts.md")
    table(s,["Claim","Meaning","Why it is separate"],[
        ("Indexed prefix W","Every accepted source item through W processed","Later source commits may exist"),
        ("Complete page","All matches for this page at its fixed prefix","A continuation can still be required"),
        ("Requested minimum","W meets the caller’s source barrier","Too far behind → NOT_AVAILABLE"),
        ("Observed source head H","Whether W equals H, with observation context","No query-side head poll or ingestion")],[370,580,506],row_h=104,size=25)
    s.text(89,718,1410,"Exact conjunction: 1–3 distinct fields from kind / topic / label; equality only.",26,C['ink'],'bold')
    band(s,"Case and Unicode are exact; missing fields do not match. Search W and Relations R are separate snapshots.",size=24)
    note(s,"The sole Search profile is exact-attributes/1 with knowledge-attributes/1 extraction, contract 2.0.0. Canonical UTF-8 JSON requires kind and permits topic/label, all bounded strings. Search performs exact conjunction without normalization, embeddings or numerical scoring. A genuine empty result at a sufficient prefix differs from source lag. Query neither polls the current head nor advances the index. Cursors bind semantic query, principal/scope, source identity, snapshot and generation. Rebuild invalidates old-generation cursors explicitly; pending callers do not silently reset. The consumer carries independent Search and Relations snapshots, not a fictional cross-owner transaction. A stored completed intent can replay its historical result after current authorization is checked.")

    s = Slide("Actual Hive discovers the answers through the interfaces", "06 / M5 · native lookup demonstration",
              "Setup exits before lookup; the consumer receives query attributes and a freshness barrier only.",source="evidence/m5/traces/lookup-trace-1.json · lookup-trace-2.json")
    for x,value,label in [(72,"5","matching roots"),(568,"15","accepted relations"),(1064,"8","unique payloads")]:
        s.rect(x,248,464,222,C['mint'],radius=14)
        s.text(x+26,266,412,value,83,C['teal'],'bold');s.text(x+26,385,412,label,30,C['ink'],'bold')
    s.line(536,359,568,359,C['teal'],arrow=True);s.line(1032,359,1064,359,C['teal'],arrow=True)
    table(s,["Transition","Native behavior","Evidence"],[
        ("Initial query","3 pages at page size 2","Distractors and another private scope excluded"),
        ("Append → lag → catch up","NOT_AVAILABLE → 6 roots / 9 payloads","Query did not ingest; maintenance advanced prefix"),
        ("Rebuild → restart → substitute","Same discovery and canonical bytes","New generation; independent file Search fixture")],[375,515,566],y=503,row_h=72,size=23)
    band(s,"The oracle is test-only and removed before startup. No answer references are supplied to Hive.",size=26)
    note(s,"The real native fusion-lookup sibling uses authenticated Hive Programs dispatch and the pinned PeTTa runtime. A separate writer uses only declared ports to create five matching task records, three prerequisites, fifteen requires edges, distractors, an unrelated association, an ignored text atom and a same-match record in another scope; IDs are random and insertion order is shuffled. Two native corpus runs confirm counts and restart/rebuild/substitution. The consumer calls query, outgoing, getRelation, incoming and get/getMany through backend-independent ports. Supplemental authorized private probes compare complete reference sets and canonical payload bytes across initial, catch-up, rebuild and substitution, without publishing private identifiers. Search replacement rebuilds from the same feed rather than inheriting primary index state.")

    s = Slide("Thirteen process kills exercise separate commit boundaries", "06 / M5 · recovery + replacement",
              "A lost response does not merge owner transactions or erase accepted work.",source="test_m5_real.py · test_m5_integration.py")
    table(s,["Boundary","Deliberate SIGKILL cases","Recovered fact"],[
        ("Atom / feed acceptance","1","Accepted envelope and contiguous feed stay together"),
        ("Relation payload / acceptance","2","Orphan is invisible; accepted relation replays once"),
        ("Projection checkpoint / rebuild","6 · both Search providers","Before/after checkpoint and rebuild intent resume"),
        ("Native page / result progress","4 · both Search providers","Page continuation and completed result survive")],[420,425,611],row_h=109,size=24)
    band(s,"Same profile, independent Search implementation, unchanged consumer; fresh derived store for substitution.",size=24)
    note(s,"Nine direct process-kill cases plus four native cases total thirteen deliberately placed M5 SIGKILL scenarios. Test hooks pause at known boundaries with SIGSTOP, then the harness kills the actual process; fixtures position the fault but recovery uses real persisted files. Provider methods also verify malformed responses, invalid source ranges and restart. The independent Search fixture uses its own atomic-file state transitions and predicate evaluation. Both providers consume the authoritative commit feed; neither uses the oracle or foreign SQL. Current authorization is checked before reads, continuation, replay and commit, including revocation. These observations cover same-host process termination with intact storage, not filesystem power failure or distributed failover.")

    s = Slide("Private ownership extends without changing cognition", "06 / M5 · placement and profiles",
              "Each new profile is explicit; old M1–M4 owners and behavior remain selectable.",source="lookup_composition.py · hive/lookup · no-cognitive-effects.json")
    table(s,["Owner","State and compatibility","Private boundary"],[
        ("AtomStorage","immutable-commit-feed/1 · contract 1.1.0","Envelopes + accepted source metadata"),
        ("Relations","schema-ordered-relations/2 · contract 2.0.0","Accepted structures + replay + incidence"),
        ("Search","exact-attributes/1 · contract 2.0.0","Derived index + checkpoint + generation"),
        ("Native lookup caller","Request + pages + full authorized result","Operator request label; ordinary receipt = counts/status")],[330,625,501],row_h=109,size=24)
    band(s,"Lookup has no runtime dependency on C1/C2, attention, inference or chain; no private identifiers are exported.",size=24)
    note(s,"Hive logs native parameters, so an operator-registered opaque request label maps to private query attributes and source barrier. It contains no answer references. Credentials, private query text, atom IDs/hashes and full results remain in operator/private state. The private caller journal binds the selected provider and intent; completed historical replay requires current authority. Four populated-state attention/Search configurations confirm unchanged cognitive files, budgets and result replay. Lookup has no cognitive, formula, messaging or chain dependency. Fresh stores are required; historical tuple Relations/Query declarations remain clearly labelled specifications rather than silently widened profiles. No backfill or populated-state migration is added. The DeTTa core and adapter remain unchanged and application-neutral.")

    s = Slide("Coverage has three denominators", "07 / M5 · capability ledger",
              "Module representation, exercised operations and behavioral coverage answer different questions.",source="m5-capability-ledger.json · evidence/m5/manifest.json")
    for x,value,title,body in [
        (72,"15 / 15","Module families","Up from 13. All bounded reference families now have a represented implementation."),
        (568,"9 / 9","New operations","4 Relations + query + 2 feed + 2 maintenance. With inherited storage: 13 / 13 in this slice."),
        (1064,"18 / 18","Behavioral groups","12 required scenario groups + 6 crash-boundary groups. Separate from test-method counts.")]:
        s.rect(x,250,464,444,C['white'],C['teal'],14)
        s.text(x+24,275,416,value,65,C['teal'],'bold')
        s.text(x+24,378,416,title,31,C['ink'],'bold')
        s.text(x+24,445,416,body,29,C['muted'])
    band(s,"This is bounded reference coverage, not full Omega completeness. Line/branch coverage: NOT_MEASURED.",size=24)
    note(s,"The ledger explicitly separates module, operation and behavioral axes. The fifteen-family denominator is the reference inventory, not a complete product requirements set. Nine new operations are assertRelation/getRelation/outgoing/incoming, Search.query, AtomStorage.head/readCommits and Search.catchUp/beginRebuild. Four inherited dependencies create/get/getMany/availability bring the exercised M5 slice to thirteen. Eighteen behavioral groups comprise twelve brief scenarios plus six crash boundaries; thirteen kill instances instantiate those boundaries. No line or branch coverage percentage is measured. The new fixture, real-provider and native methods overlap repeated legacy runs and must not be summed into a false total. Human maintainers remain UNASSIGNED.")

    s = Slide("Real providers, fixtures and unrun work stay distinct", "07 / Evidence classification",
              "All required M5 gates pass; each claim retains its actual provider and source label.",source="evidence/m5/manifest.json")
    table(s,["Classification","M5 evidence","Meaning"],[
        ("REAL PROVIDERS","Authenticated native Hive / PeTTa · DeTTa\nSQLite AtomStorage, Relations and Search","Actual dispatch, persistence,\ndiscovery and restart"),
        ("FIXTURES","Generated corpus / oracle / local policy\nIndependent atomic-file providers; injected faults","Controlled inputs and substitutions;\nnot production data or services"),
        ("BLOCKED","No required M5 prerequisite\nHistorical dirty M1 chain source unavailable","Historical blocker remains separate\nfrom the clean M4 rebaseline"),
        ("UNRUN / OUT OF SCOPE","Power loss, distributed failover, empty caches\nLive migration, public networks, new chain work","No claims for these scenarios;\ncode coverage not measured")],[325,670,461],row_h=112,size=24)
    band(s,"The six real M4 chain cases passed again as legacy regression; M5 adds no chain operation.",size=25)
    note(s,"Generated private records and a test-only oracle do not become real user knowledge because real providers store them. The oracle is removed before the consumer runs and never supplies answer references. Hive authentication and Programs dispatch, local DeTTa and SQLite journals are real. Alternate atomic-file providers and local grants remain fixtures. The required final M5 missing-prerequisite, executed-failure and observation-timeout arrays are separately empty. A negative verifier test deliberately confirms BLOCKED/NOT_RUN classification without fixture fallback. Earlier development failures remain archived and do not count as final passes. Historical dirty M1 chain source reproduction remains blocked; the clean pinned M4 chain is separately verified and rerun in M5.")

    s = Slide("Executed tests cover discovery, recovery and regressions", "07 / M5 final verification",
              "Repeated subsets overlap. These counts must not be added into a unique test total.",source="evidence/m5/final/verification.json")
    table(s,["Layer","Cases / groups","Recorded outcome"],[
        ("New contract / fixture methods","18","PASS · pagination, freshness, auth, independent providers"),
        ("Real DeTTa + owners","4 methods","PASS · includes nine direct SIGKILL cases"),
        ("Actual authenticated Hive","7 cases","PASS · includes four native SIGKILL cases"),
        ("Supplemental private probes","4 + 4","No cognitive effects; complete payload comparisons"),
        ("M1–M3.1 regression","156 aggregate","PASS · includes old 138 plus new 18 methods"),
        ("Unchanged M4 suites","11 fixtures + 6 real","PASS · real isolated chain and independent readback")],[510,290,656],row_h=79,size=23)
    band(s,"Tested bfb0ec8 · 13 deliberate M5 SIGKILL cases · zero final failures, blockers or timeouts.",size=25)
    note(s,"The final clean bfb0ec8 run executed 18 fixture methods in 27.434 seconds, four real-provider methods in 22.088 seconds and seven native Hive cases in 111.519 seconds. Nine direct kills cover atom/feed commit, relation payload/acceptance and projection checkpoint/rebuild boundaries; four native kills cover page/result commits across both Search providers. Ordinary restarts are not extra kill scenarios. Supplemental probes check four attention/Search configurations and four payload transitions. The unchanged M1–M3.1 wrapper passed in 1325.251 seconds with aggregate 156, followed by 11 M4 fixtures and six real M4 cases in a new isolated namespace/state. Reused pinned node binary is explicit. Intermediate failures and repeated subsets are excluded from final counts. This presentation update audits the recorded results; it does not rerun integrations.")

    for part,gate_items in enumerate([
        [("BASELINE","Full M1–M3.1 regression; both attention providers and old profiles"),
         ("CHAIN_SOURCE_BUILD","Clean pinned build; loopback-only namespace; live socket probes"),
         ("NATIVE_HIVE_DA","Actual inspect dispatch + real DeTTa + labelled fixture counterparty"),
         ("APPROVAL_BINDING","Exact immutable result/chain/profile; current authority and refusal cases"),
         ("REAL_CHAIN_EFFECT","Actual inclusion post-state tuple + matching finalized deploy effect")],
        [("RECOVERY","Four caller/adapter kill boundaries; real node outage and restart"),
         ("PRIVACY_ISOLATION","Private canaries and identifying derivatives absent; live isolation"),
         ("REPRO_READBACK","Fresh pinned builds + independent reader checking the same artifact"),
         ("DEMO_HANDOFF","Native receipts/progress, runnable commands and sanitized trace"),
         ("SCOPE","Original DA, cognition, math, ports and inspect plugin preserved")]],1):
        s = Slide("M4 gates: native result to verified chain effect" if part==1 else "M4 gates: recovery, privacy and independent readback",
                  f"07 / Preserved M4 gate evidence · {part} of 2",
                  "All 10 required gates passed. CHAIN is required and real in this milestone.",source="evidence/m4/manifest.json")
        table(s,["Gate","Result","Recorded evidence"],[(key,M4RECORD['gates'][key],description) for key,description in gate_items],[380,150,926],row_h=90,size=24)
        band(s,"No missing prerequisite, final executed failure or positive observation timeout is hidden in PASS.",size=25)
        note(s,"Gate statuses are read directly from the M4 machine manifest and match the final verifier at 55ed540. Earlier M3.1's twelve supported gates remain preserved; its optional CHAIN=NOT_RUN is a historical scope field, not the M4 outcome. M4 uses the actual same-run generated native inspect artifact and mandatory real F1R3node effect. Source discovery and independent clean build/probe preceded adapter implementation. Development failures, including an initial launcher issue and a negative mutable-alias regression, remain in preparation/attempts.json and the red regression log. They were corrected and superseded by the clean final run; they are not reported as missing prerequisites. Results establish the tested local scope only.")

    for part,items in enumerate([
        [("BASELINE_AND_SCOPE","Requested ancestry; clean source; preserved M1–M4 boundaries"),
         ("RELATIONS_CONTRACT","All four operations; ordered roles, schemas and fixed-head pages"),
         ("RELATIONS_REAL","Accepted relations and payloads through actual local DeTTa"),
         ("COMMITTED_SOURCE","Replayable, scoped AtomStorage-owned contiguous feed"),
         ("SEARCH_CONTRACT","Exact attributes; explicit freshness, pagination and error semantics"),
         ("SEARCH_REAL_REBUILD","Bounded catch-up and generation rebuild from real source")],
        [("SUBSTITUTION","Independent feed/Search fixtures; unchanged declared-port consumer"),
         ("RECOVERY","13 deliberate process kills, replay and durable owner boundaries"),
         ("AUTH_PRIVACY","Live authorization, private placement and refusal coverage"),
         ("HIVE_LOOKUP","Actual authenticated native query → traversal → payload retrieval"),
         ("REPRO_AND_LEDGER","Pinned recipes; separate module/operation/behavior coverage"),
         ("LEGACY_REGRESSION","M1–M3.1 and unchanged M4 fixture + real-chain suites pass")]],1):
        s = Slide("M5 gates: contracts, real storage and rebuild" if part==1 else "M5 gates: substitution, recovery and actual Hive",
                  f"07 / M5 gate-by-gate results · {part} of 2",
                  "All 12 required gates pass on the exact final tested implementation.",source="evidence/m5/manifest.json · final/verification.json")
        table(s,["Gate","Result","Recorded evidence"],[(key,M5RECORD['gates'][key],body) for key,body in items],[400,140,916],row_h=78,size=23)
        band(s,"Final missing prerequisites: 0 · executed failures: 0 · observation timeouts: 0.",size=27)
        note(s,"Gate statuses come directly from the committed M5 manifest and match the final verifier at clean bfb0ec8. All six final suite return codes are zero. Earlier intermediate PARTIAL and corrected development failures are preserved separately and contribute no final passes. An intentional missing-environment probe verifies BLOCKED/NOT_RUN classification and no fixture fallback. Legacy real chain is rerun as existing M4 behavior, not an added M5 operation. All fifteen reference families are represented, but scope remains exact-attribute discovery and one-hop traversal over bounded fresh private stores.")

    s = Slide("Source, build and outcome remain independently traceable", "07 / M5 source ledger",
              "The final tested implementation and evidence-only descendant are explicit.",source="evidence/m5/source-state.json · reproduction.json")
    table(s,["Layer","Recorded state","Boundary"],[
        ("Requested / actual start","05b1c52 → 4093301","Presentation-only descendant before M5"),
        ("Clean tested implementation",BASE_COMMIT[:12],"Final native plugin and Python loaded from this source"),
        ("Evidence snapshot",EVIDENCE_COMMIT[:12],"Docs/evidence only; runtime and tests unchanged"),
        ("Fresh native provider build","Hive 34b0fb3 · DeTTa 272888f","Fresh sources, venv and native objects; warm caches"),
        ("Preserved math / chain","PLN 4405956 · F1R3node 9ec1096","Same formulas; reused pinned node binary")],[350,525,581],row_h=91,size=24)
    band(s,"M5 archives final passes, corrected development failures and intentional negative classification separately.",size=24)
    note(s,f"Requested ancestor {M5RECORD['requested_ancestor']}; actual start {M5RECORD['starting_descendant']}; tested {BASE_COMMIT}; evidence-only {EVIDENCE_COMMIT}. M5 implementation commits 0cb61d5, 9b0ed35 and bfb0ec8 precede the evidence commit. The native provider recipe recorded 4093301 because build began before implementation, but its recipe, pins and Rust adapter bytes remained identical at the tested source. Plugins loaded from clean bfb0ec8. The existing M4 Python lock was installed before the final legacy chain run. The pinned M4 node binary was reused with fresh isolated state/genesis. Earlier incorrect test DTO assumption, duplicate PYTHONPATH and missing cryptography dependency were fixed and recorded; intermediate PARTIAL does not count toward final gates. Source/build reproducibility is not cross-host bit reproducibility or an empty-cache claim.")

    s = Slide("The limitations are part of the contract", "07 / Guarantees and stopping point",
              "M5 adds bounded private discovery while preserving the prior cognition and chain limits.",source="m5-contracts.md · m5-evidence.md")
    for x,y,title,body,color in [
        (72,250,"Exact attributes; one-hop lookup","Case-sensitive conjunction over kind, topic and label. No embeddings, semantic search or task generation.","teal"),
        (824,250,"Fresh profiles and intact files","Finite local stores. No migration, eviction or automatic repair; unavailable source bytes block indexing.","amber"),
        (72,505,"Independent snapshots","Search prefix W and Relations head R are explicit. They do not form a global atomic snapshot.","blue"),
        (824,505,"Earlier guarantees retain their limits","Cognitive budgets stay spent; closure can remain pending. Chain proof remains one local validator.","blue")]:
        s.box(x,y,704,219,title,body,color,"sand" if color=="amber" else "ice",title_size=31,body_size=28)
    band(s,"Stopped at M5: no new cognition, embeddings, scheduler, migration or chain operation.",color="violet",fill="lavender",size=26)
    note(s,"Bounds are 512 atoms, 4096 bytes per atom, 128 accepted relations, 512 relation replay keys, 256 indexed records, and pages/batches of at most eight. One lookup permits eight query pages, 32 roots, 128 relations and 64 payloads; caller commands and rebuild keys cap at 64. Strings are bounded to 128 codepoints/512 UTF-8 bytes; query encoding to 1024 bytes. Search trusts the immutable source contract and does not attest cryptographically against a compromised owner. Current authorization is rechecked, including historical result replay. Recovery covers same-host process kills with intact files, not power loss/distributed failover. Old profiles stay explicit; existing stores are not migrated. Maintainership remains UNASSIGNED. These are bounded reference modules, not full Omega product coverage.")

    s = Slide("", "07 / Takeaway", source="M5 tested bfb0ec8 · evidence 3dc6c11", dark=True)
    s.text(72,177,1430,"Discover the knowledge.\nPreserve the boundaries.\nCheck the evidence.",72,C["white"],"bold",1.15)
    s.text(77,508,1370,"Real Hive → exact query → relations → real DeTTa payloads\nwith explicit freshness, independent owners and restart.",34,C["dim"],lineheight=1.35)
    s.tag(76,711,"M5 COMPLETE · ALL 12 REQUIRED GATES PASS","teal",C["mint"],22)
    note(s,"Return to the five ELI16 stories: history and support, priorities and budgets, delivery closure, approved commitments, and a library catalogue with explicit freshness. M5 completes the bounded fifteen-family inventory with four Relations operations and exact-attribute Search. The native consumer discovers five roots, fifteen relations and eight payloads without supplied answer references. Lag, catch-up, rebuild, restart and independent replacement are demonstrated through declared interfaces. M1–M4 regressions pass, including real chain; no new cognition, numerical behavior or chain work is added. Separate module, operation and behavior coverage says precisely what was demonstrated. Private data and identifiers remain private. The useful result is a tested local integration with explicit limits.")

    s = Slide("Implementation map: responsibilities stay local", "Appendix A / Code navigation",
              "Follow interfaces and owner journals before following concrete provider classes.",source="architecture.md · ports.py",appendix=True)
    table(s,["Responsibility","Files / surface","Owned state"],[
        ("C1 / relay / original C2","episodes.py · evidence_relay.py · delivery_contracts.py","History; delivery + trusted completion"),
        ("C2 derived admission","derived_beliefs.py · cognition_contracts.py","Fresh derived-beliefs.sqlite · local v3"),
        ("C3 attention","attention.py · adapters/fixture_attention.py","SQLite or independent atomic-file state"),
        ("Pure PLN providers","adapters/pln_deduction.py · pln_revision.py","No mutable domain state"),
        ("C4 controller","inference.py · deadlines.py","Budgets / execution + separate closure journal"),
        ("Composition / native caller","cognition.py · hive/inference_program/","Explicit provider bindings; caller receipt")],[320,670,466],row_h=81,size=23)
    note(s,"Paths are relative to fusion/ unless marked hive/, which is under integration/. ports.py declares the protocols; attention_contracts.py and cognition_contracts.py enforce the executable bounded schemas. Shared DTO validators are permitted in the independent fixture, shared owner transitions are not. C2 default M2 behavior remains via its original validators and profile; the derived owner selects fresh v3 behavior. The native plugin uses integration/m3_scenario.py and holds only caller intent and public receipt. No owner reaches into another owner's private SQL. Tests and exact source hashes are indexed in the M3.1 machine manifest. Historical protocol declarations are preserved; new closure protocols are explicit.")

    s = Slide("Exact sources identify the verified native stack", "Appendix B / Source ledger",
              "Full revisions are printed here; source files and built binary hashes remain in the committed evidence.",source="evidence/m5/source-state.json · provider-build.json",appendix=True)
    runtime=M31VERIFY['runtime'];pins=M31VERIFY['hive_sources']
    source_rows=[("Fusion · tested",BASE_COMMIT),("Hive schematics",pins['schematics']['commit']),
                 ("Hive",pins['repositories']['omegahive']['commit']),
                 ("DeTTa",pins['repositories']['secured-contract-spaces']['commit']),
                 ("Reachability",runtime['sources']['reachability']['commit']),
                 ("PLN",runtime['sources']['pln']['commit']),
                 ("PeTTa",runtime['sources']['petta']['commit']),
                 ("SWI 10.1.14",pins['repositories']['swipl']['commit']),
                 ("F1R3node",M4VERIFY["source_pins"]["chain"]["commit"])]
    for i,(label,sha) in enumerate(source_rows):
        y=229+i*58;s.rect(72,y,1456,53,C['white'],radius=6)
        s.text(89,y+14,335,label,24,C['ink'],'bold');s.text(445,y+14,1050,sha,25,C['muted'],'mono')
    band(s,"metta-attention inspected at 3e1c8147; not used as the bounded STI provider.",size=27)
    note(s,f"Evidence commit {EVIDENCE_COMMIT}. Full inspected metta-attention revision: 3e1c8147dc17299d17ab34720334fc19277cb6a9, clean. Its coupled STI/LTI/VLTI, wages and funds are not silently adopted. Runtime profile: {runtime['runtime_profile']}; rule profile: {runtime['profile']}; truth model: {runtime['model']}. PLN library SHA-256 {runtime['sources']['pln']['files']['lib_pln.metta']}. Historical M3 SWI binary SHA-256 {runtime['binary_sha256']}; M4 build/binary-identities.json records the new build identities. Native Python 3.12.12, Janus 1.5.3; fixture runner Python 3.11.14. All exercised source checkouts were clean. No upstream formula or runtime implementation was patched. Historical SWI 10.0.1 remains unrun.")

    s = Slide("Profiles and bounds make compatibility explicit", "Appendix C / Contract ledger",
              "fusion-delivery-closure/1 selects fresh C1 / C3 / C4 journals; C2 and the math stay unchanged.",source="contracts.md · cognition.py",appendix=True)
    table(s,["Port / profile","Explicit selection","Key bound"],[
        ("C1 · local 3.0.0","episode-delivery-completion/1","16 pending; 256 events; trusted completion only"),
        ("C2 derived · local 3.0.0","pln-derived-private/1 · unchanged","Historical premises and inherited support roots"),
        ("C3 · local 2.1.0","sti-additive-linear-decay-closure/1","Existing STI, cause and command capacities"),
        ("C4 · local 2.1.0","bounded-grounded-closure/1","1–16 resolutions/call; 128 commands/step"),
        ("PLN kernel · local 2.0.0","grounded-five-premise-deduction/1","One unchanged native rule; five exact premises"),
        ("Historical M1 / M2 / M3","Original descriptors remain selectable","No silent upgrade; no live state migration")],[330,610,516],row_h=81,size=23)
    note(s,"The configuration selector is fusion-delivery-closure/1. C1's trusted completion DTO has profile trusted-evidence-completion/1. C3 arithmetic policy remains sti-additive-linear-decay/1 while its interface/profile explicitly adds submitFeedback and resolveFeedback. C4 adds readProgress and reconcile. Max 16 targets, 16 advance steps, eight contexts, 512 causes/context, 1024 commands/owner and feedback generation three are unchanged. First retirement consumes existing cause/command capacity; recovering an existing application or retirement does not allocate a new slot. Reconciliation has its own finite command budget and cannot reset original WorkBudget/deadline. M1 wire, M2 revision and M3 old cognition profiles remain supported. Algorithm profile, interface version, selected descriptor, runtime and current permissions all matter.")

    s = Slide("New profiles close the seam; old stores stay explicit", "Appendix D / Existing-state compatibility",
              "The M3 findings were reproduced before edits. M3.1 is an opt-in contract extension.",source="m3_1/baseline/gaps.json · test_m3_1_compat.py",appendix=True)
    s.box(72,260,704,310,"Historical M3 profile","C1 expects a closed v2 acknowledgment.\nC2 emits a v3 decision.\nDelivery remains pending; stale feedback can remain CONFLICT.","amber","sand",title_size=33,body_size=29)
    s.box(824,260,704,310,"Fresh M3.1 profile","Relay validates C2; C1 gets narrow completion.\nAttention resolves original feedback.\nC4 tracks closure separately from execution.","teal","mint",title_size=33,body_size=29)
    s.box(72,616,1456,117,"Populated old stores → new selection: UNSUPPORTED_PROFILE","Disposable copies reject without modification and still replay under the original profile. User stores are untouched.","blue","ice",title_size=29,body_size=24)
    band(s,"No automatic conversion, repair of pre-existing pending work, invented acknowledgment or weakened validation.",size=24)
    note(s,"Baseline reproduction against clean 3b34e00 confirms the old acknowledgment/relay NOT_AVAILABLE, 16 pending then append 17 OVERLOADED, and persistent stale-feedback CONFLICT after reopen. Those expected gaps are separate from the passing baseline regression. New-profile delivery drains, including after deduction and for model-inapplicable reports. Neither this extension nor the presentation migrates existing state. Compatibility tests populate old stores, operate on disposable copies, reject new selection without modifying bytes and replay with original descriptors. Fresh profiles preserve strict time and causal semantics. This distinction must survive any claim that the seam is now closed.")

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
    note(s,"All effects originate in the real native operation, not a renamed protocol demo. The caller first commits its original intent. AtomStorage persists generated bytes in actual DeTTa, then Messaging accepts a reference for the explicitly labelled fixture counterparty. DelegatedExecution accepts only inspect_atom under the original key and correlation. The caller records the accepted job. A separate real worker reads/persists through AtomStorage, then commits execution terminal state/outbox. Messaging accepts the completion in a separate transaction. The final arrow summarizes reconciliation: status /2 restores known correlation, poll and get verify the completion, caller acceptance commits, and a stable-key acknowledgement follows. This is not one distributed transaction.")

    s = Slide("Historical M1: one result reached an isolated chain", "Appendix F / Historical chain evidence",
              "This is the earlier protocol-peer artifact. No M1.2, M2, M3 or M3.1 Hive result was submitted.",source="evidence/chain-demo.json · M1 historical",appendix=True)
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
    band(s,"Historical M1 reproduction stays BLOCKED. M4 separately passes with a verified clean source baseline.",color='amber',fill='sand',size=22)
    note(s,"Preserve this historical result without promoting it into the new real-caller gate. The M1 chain JSON records pending, included with effect finality Pending, then finalized, at height 3 with no execution error, no rejection and cost 351 phlo. The committed digest belongs to the original protocol-peer result, not the generated native Hive result in M1.2. The M1 adapter used a registered approved digest, injected signer and durable signed intent against one isolated local node. That source had local changes and an untracked input. Exact historical reproduction remains blocked until those authorized bytes are supplied or a different clean revision is separately validated. M1.2, M2, M3 and M3.1 did not run chain. M4 now has a separate real native artifact, clean source rebaseline, post-state verification and readback. This historical protocol-peer result is not reused as M4 proof. The presentation update itself runs no chain process or transaction. Finality does not establish indefinite off-chain availability.")

    s = Slide("Reproduce the required real M4 gates", "Appendix G / Commands and prerequisites",
              "Use tested 55ed540 or a reviewed descendant; fresh build/evidence destinations and authorized source access.",source="runbook.md · build_m4.py · verify_m4.py",appendix=True)
    for y,label,line1,line2 in [(245,"BUILD PINNED HIVE / DETTA / PLN + CLEAN F1R3NODE","uv run --python 3.11 --locked python","  scripts/build_m4.py <FRESH_BUILD>"),
                               (465,"VERIFY REGRESSIONS + NATIVE CHAIN + RECOVERY + READBACK","uv run --python 3.11 --locked python","  scripts/verify_m4.py <FRESH_BUILD> --output <FRESH_EVIDENCE>")]:
        s.rect(72,y,1456,187,C['dark'],radius=12)
        s.text(100,y+22,1380,label,19,'77DDC4','bold')
        s.text(100,y+69,1380,line1+' \\',27,C['white'],'mono')
        s.text(100,y+117,1380,line2,27,C['white'],'mono')
    s.text(78,697,1430,"Read: manifest → same-artifact → readback → verification → regression summaries",25,C['ink'],'bold')
    band(s,"Separate reader: scripts/readback_m4.py · DA get-only authority + read RPC · no caller journal or signer.",size=24)
    note(s,"Use the runbook M4 required isolated chain reproduction section for actual paths and Linux/SSH/toolchain prerequisites. Build_m4.py obtains all pinned sources and builds providers plus a clean F1R3node with offline locked Cargo build after fetch. User/network namespaces must be available; generated keys/genesis stay inside ignored artifacts. verify_m4.py checks exact source start/end, runs full M1–M3.1 regression plus eleven commitment fixtures and six real native chain tests. It records positive observation timeouts separately from missing prerequisites and executed failures. Independent reproduction: <NATIVE_PYTHON> scripts/readback_m4.py <PRIVATE_READ_ACCESS_JSON> <SAME_ARTIFACT_JSON>, with reachable isolated node and retained post-state. Follow the runbook for the exact invocation and namespace access. Do not publish raw provider environments, journals or keys. Downloads may be warm; provider builds are fresh. This deck's export/check commands do not rerun integrations.")

    s = Slide("Retry identities answer different questions", "Appendix H / Operational semantics",
              "Preserve the logical cause while distinguishing transport replay from physical evaluation attempts.",source="inference.py · derived_beliefs.py · attention.py",appendix=True)
    table(s,["Identity / state","Meaning","Recovery action"],[
        ("Request / step ID","Exact immutable command intent","Same body replays; changed body conflicts"),
        ("Logical derivation ID","The same exact grounded conclusion","Deduplicate admission and causal feedback"),
        ("Attempt key + reserved slot","One physical evaluation opportunity","Pending death spends slot; new key needs budget"),
        ("Committed C2 decision","Saved authoritative admission outcome","Read first; do not recalculate"),
        ("C3 causal feedback receipt","One workflow credit for logical admission","Recover acknowledgment; do not credit twice"),
        ("Deadline / generation watermark","Durable limits across process restarts","Do not reset, refund or implicitly retime")],[375,525,556],row_h=81,size=23)
    note(s,"A derivation's logical ID excludes request/step identity, output CAS and deadline so a retry cannot manufacture new independent support. An attempt key freezes its exact semantic body and is evaluated at most once; a killed pending attempt consumes a physical reservation. Multiple physical calculations for one logical derivation remain possible under distinct reserved attempts. C2 commits its decision before C4 progress; C3 commits feedback before C4 acknowledgment. Recovery queries those owners rather than inferring success from a missing local reply. Feedback_applied counts acknowledged unique logical credits; feedback_duplicate records suppression on duplicate admission. Fixed feedback adds no truth evidence. The semantics distinguish bounded termination, successful admission and fully acknowledged work.")

    s = Slide("M4 adds one profile and two narrow native actions", "Appendix I / Chain contract + code ledger",
              "Existing ConsensusFinality signatures and legacy providers remain unchanged; fresh journals are required.",source="contracts.md · ADR-013 · f1r3_m4.py",appendix=True)
    table(s,["Surface / owner","Contract or code","Durable responsibility"],[
        ("Native commitment caller","integration/hive/commitment/","Original command mapping; public progress"),
        ("Completed-result accessor","integration/hive/program/completed.py","Read caller-owned acceptance and ack"),
        ("ConsensusFinality adapter","fusion/adapters/f1r3_m4.py","Plan → signed intent → receipt → observations"),
        ("Signing boundary","fusion/adapters/f1r3_signing.py","Pinned serialization + registered local signer"),
        ("Explicit compatibility","f1r3-generated-post-state/2","f1r3-local · interface 1.0.0 · impl 0.4.0"),
        ("Bounded native observation","≤120 calls; stop starting after 180 s","≤256 saved observations; explicit exhaustion")],[350,620,486],row_h=81,size=23)
    note(s,"The public sibling exposes commit and observe, with only original_command. It gets completed accepted/acknowledged results through a caller-owned accessor beside the unchanged fusion-inspect plugin. ConsensusFinality signatures remain backend-independent. The new profile pins actual inclusion-block post-state semantics and fixed commitment format; it does not widen the legacy adapter. Logical timestamp/plan commit before signing, full signed deploy commits before HTTP. Replays retain the exact signature, serialization, gas limits, timestamp and deployment identity, without extending validity. Native progress is separate from adapter observations and cannot access other owners' tables. Observation calls are bounded and cooperative; an in-flight socket timeout may complete after the start deadline. Fresh single-operation journals only; no migration. Tests live in tests/test_m4_chain.py and integration/chain/test_m4.py. Build, verify and separate readback scripts provide the evidence workflow.")

    s = Slide("Reproduce M5 from declared sources and private requests", "Appendix J / M5 code + commands",
              "Fresh provider build, existing chain dependencies, then all required gates.",source="runbook.md · scripts/verify_m5.py",appendix=True)
    for i,line in enumerate([
        "uv run --python 3.11 --locked python scripts/build_m3.py <providers>",
        "uv pip install --python <providers>/native/venv/bin/python \\",
        "  -r integration/chain/requirements.lock",
        "uv run --python 3.11 --locked python scripts/verify_m5.py \\",
        "  --environment <providers>/environment.json --chain-build <chain> \\",
        "  --output <fresh-output>"]):
        s.text(89,238+i*48,1430,line,25,C['ink'],'mono')
    table(s,["Code","Responsibility"],[
        ("fusion/atom_feed.py · relations.py · search.py","Accepted source; structural owner; projection owner"),
        ("fusion/lookup.py · lookup_composition.py","Declared-port consumer; private binding and placement"),
        ("integration/hive/lookup/ · test_m5_integration.py","Actual native dispatch and recovery; no answer refs")],[800,656],y=552,row_h=58,size=22)
    band(s,"Use --gates hive for the focused demo. Keep raw environments, private journals, queries and IDs private.",size=24)
    note(s,"The full runbook supplies concrete paths and prerequisites. build_m3.py makes fresh pinned native Hive/PeTTa/SWI/DeTTa providers; the unchanged M4 Python lock supplies legacy-chain dependencies. <chain> is a verified pinned M4 node build, explicitly reused in the recorded run; build_m4.py can create a fresh full build when needed. verify_m5.py supports fixtures, storage, hive, legacy or all. Fixture, real-provider, missing prerequisite, executed failure and timeout classifications remain distinct. The native writer uses declared ports then exits; the operator request map contains query attributes and source barrier only. The private caller journal retains detailed result state. Public evidence publishes sanitized counts, gate results and code/build hashes only. Reading these commands or rebuilding this deck runs no integration or chain process.")

    assert len(SLIDES) == TOTAL_SLIDES
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
    prs.core_properties.title = "Omega × ASI — Private discovery, cognition and verified commitments"
    prs.core_properties.subject = "Through M5: private discovery, bounded cognition and verified chain commitments"
    prs.core_properties.author = "Omega × ASI module-interface project"
    prs.core_properties.keywords = "Omega, ASI, M5, Relations, Search, ELI16, Hive, DeTTa, PLN, F1R3node, commitment, attention, recovery"
    pdf_path = HERE / "omega-asi-module-interfaces.pdf"
    pdf = canvas.Canvas(str(pdf_path), pagesize=(W*SCALE,H*SCALE), invariant=1)
    pdf.setTitle(prs.core_properties.title)
    pdf.setAuthor(prs.core_properties.author)
    notes = ["# Omega × ASI — speaker notes", "", f"Implementation baseline: `{BASE_COMMIT}`.",
             f"Evidence snapshot: `{EVIDENCE_COMMIT}`.",
             f"Suggested delivery: 60–65 minutes for slides 1–{MAIN_SLIDES}, with appendices for discussion.",
             "Current claims use the recorded 16 October 2026 M5 run, including M1–M4 regression. Earlier cognitive observations and M3 timings retain their source labels. Historical M1 chain evidence is distinct from the required real M4 same-artifact proof.", ""]
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
        title=s.title or ("Discover the knowledge. Bound the work. Verify the result." if index==1 else "Discover the knowledge. Preserve the boundaries. Check the evidence.")
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
