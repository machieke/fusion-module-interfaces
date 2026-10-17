"""Vector PDF/SVG and editable PowerPoint export using the established deck primitives.

The export loop follows the existing conference renderer. The original overview
builder and its outputs remain unchanged. All layout and evidence checks are local.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build as base
from build import *  # established measured vector/text primitives and fonts
import catalogue

def export(module, slides, destination, qa_dir, evidence_files):
    HERE, QA, SLIDES = destination, qa_dir, slides
    EVIDENCE_FILES = evidence_files
    BASE_COMMIT, EVIDENCE_COMMIT = catalogue.TESTED_COMMIT, catalogue.EVIDENCE_COMMIT
    MAIN_SLIDES = len(slides)
    HERE.mkdir(exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    svg_dir = HERE / "slides-svg"
    svg_dir.mkdir(exist_ok=True)
    prs = Presentation()
    prs.slide_width = Inches(13.333333)
    prs.slide_height = Inches(7.5)
    prs.core_properties.title = "Omega × ASI — " + module["name"]
    prs.core_properties.subject = module["role"]
    prs.core_properties.author = "Omega × ASI module-interface project"
    prs.core_properties.keywords = "Omega, ASI, M5, ELI16, " + module["name"]
    pdf_path = HERE / "slides.pdf"
    pdf = canvas.Canvas(str(pdf_path), pagesize=(W*SCALE,H*SCALE), invariant=1)
    pdf.setTitle(prs.core_properties.title)
    pdf.setAuthor(prs.core_properties.author)
    notes = ["# " + module["name"] + " — speaker notes", "", f"Implementation baseline: `{BASE_COMMIT}`.",
             f"Evidence snapshot: `{EVIDENCE_COMMIT}`.",
             f"Suggested delivery: 12–15 minutes for {MAIN_SLIDES} slides; follow the notes for technical discussion.",
             "Source snapshot: " + catalogue.SOURCE_COMMIT + ". Current M5 regressions and historical observations retain distinct source labels. No runtime or performance tests are rerun by this presentation build. Proposed benchmarks/future directions are unrun.", ""]
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
    pptx_path=HERE/"slides.pptx"
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
    checks=dict(module=module["id"], title=module["name"], repository_snapshot=catalogue.SOURCE_COMMIT, slides=len(SLIDES),pptx_reopened=True,pdf_pages_rendered=len(doc),
                layout_bounds_checked=True,text_overlaps=0,fonts="DejaVu Sans / DejaVu Sans Mono (PDF embedded; TTFs bundled)",
                independent_renderer_check="Recorded separately in qa.json",source_commit=BASE_COMMIT,
                evidence_commit=EVIDENCE_COMMIT,main_talk_slides=MAIN_SLIDES,
                evidence_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in EVIDENCE_FILES},slides_manifest=manifest)
    (HERE/"build-manifest.json").write_text(json.dumps(checks,indent=2)+"\n")
    return checks
