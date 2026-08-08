"""
Generate polished UML diagrams for C3MR Capstone:
  01_system_architecture.png
  04_component_diagram.png
  05_sequence_diagram.png
"""
from PIL import Image, ImageDraw, ImageFont
import os

# Diturunkan dari lokasi skrip ini sendiri. Sebelumnya dipaku ke
# "/Users/auzasyamil/Documents/Capstone/capstone1" — salinan repo lama — sehingga
# menjalankan skrip ini menulis gambar ke tempat yang tidak pernah dibaca siapa pun,
# lalu tampak seolah diagramnya "tidak berubah" padahal memang tidak pernah sampai.
BASE   = os.path.dirname(os.path.abspath(__file__))
IMGDIR = os.path.join(BASE, "uml", "images")
FONT   = "/System/Library/Fonts/SFNS.ttf"
ARIAL  = "/Library/Fonts/Arial Unicode.ttf"

def fnt(size):
    try:    return ImageFont.truetype(FONT, size)
    except: return ImageFont.truetype(ARIAL, size)

def tsz(d, txt, f):
    bb = d.textbbox((0,0), txt, font=f)
    return bb[2]-bb[0], bb[3]-bb[1]

def rr(d, x1, y1, x2, y2, r, fill, outline=None, lw=1):
    d.rounded_rectangle([x1,y1,x2,y2], radius=r, fill=fill,
                         outline=outline, width=lw)

def shadow(d, x1, y1, x2, y2, r=10):
    d.rounded_rectangle([x1+3,y1+3,x2+3,y2+3], radius=r,
                         fill=(180,190,200,60))

def ctext(d, cx, cy, txt, f, col):
    tw, th = tsz(d, txt, f)
    d.text((cx - tw//2, cy - th//2), txt, font=f, fill=col)

def ltext(d, x, cy, txt, f, col):
    _, th = tsz(d, txt, f)
    d.text((x, cy - th//2), txt, font=f, fill=col)

def arrow_down(d, x, y1, y2, col=(80,80,80), lw=2, label=None, lf=None, lo=None):
    d.line([(x,y1),(x,y2)], fill=col, width=lw)
    # arrowhead
    d.polygon([(x-5,y2-8),(x+5,y2-8),(x,y2)], fill=col)
    if label and lf:
        tw, th = tsz(d, label, lf)
        lx = lo if lo else x+4
        d.text((lx, (y1+y2)//2 - th//2), label, font=lf, fill=(100,100,100))

def arrow_right(d, x1, x2, y, col=(80,80,80), lw=2, label=None, lf=None, dashed=False):
    if dashed:
        seg, gap, cx = 8, 4, x1
        while cx < x2-8:
            d.line([(cx,y),(min(cx+seg,x2),y)], fill=col, width=lw)
            cx += seg+gap
    else:
        d.line([(x1,y),(x2,y)], fill=col, width=lw)
    d.polygon([(x2-8,y-4),(x2-8,y+4),(x2,y)], fill=col)
    if label and lf:
        tw, th = tsz(d, label, lf)
        d.text(((x1+x2)//2 - tw//2, y - th - 3), label, font=lf, fill=(100,100,100))

def arrow_lr(d, x1, x2, y, col=(80,80,80), lw=2, label=None, lf=None):
    """Bidirectional horizontal arrow."""
    d.line([(x1,y),(x2,y)], fill=col, width=lw)
    d.polygon([(x1+8,y-4),(x1+8,y+4),(x1,y)], fill=col)
    d.polygon([(x2-8,y-4),(x2-8,y+4),(x2,y)], fill=col)
    if label and lf:
        tw, th = tsz(d, label, lf)
        d.text(((x1+x2)//2 - tw//2, y - th - 3), label, font=lf, fill=(100,100,100))

def box(d, x1, y1, x2, y2, hdr_col, body_col, title, lines,
        hdr_txt=(255,255,255), r=8, border=None):
    """Rounded box with coloured header and body lines."""
    shadow(d, x1, y1, x2, y2, r)
    rr(d, x1, y1, x2, y2, r, body_col, border or hdr_col, 1)
    # header band
    rr(d, x1, y1, x2, y1+26, r, hdr_col)
    d.rectangle([x1, y1+14, x2, y1+26], fill=hdr_col)
    fh = fnt(12)
    ctext(d, (x1+x2)//2, y1+13, title, fh, hdr_txt)
    fb = fnt(11)
    cy = y1 + 36
    for line in lines:
        tw, th = tsz(d, line, fb)
        d.text(((x1+x2)//2 - tw//2, cy), line, font=fb, fill=(50,50,50))
        cy += th + 5

# ═══════════════════════════════════════════════════════════════
# 1. SYSTEM ARCHITECTURE
# ═══════════════════════════════════════════════════════════════
def make_architecture():
    W, H = 940, 680
    img = Image.new("RGB", (W, H), (248,250,252))
    d   = ImageDraw.Draw(img, "RGBA")

    ft   = fnt(16)
    ctext(d, W//2, 22, "C3MR – System Architecture", ft, (30,30,30))
    d.line([(40,36),(W-40,36)], fill=(200,210,220), width=1)

    LA   = fnt(11)
    LHDR = fnt(13)

    # ── Tier backgrounds ──────────────────────────────────────
    # T1: Client y=50-180
    rr(d, 30,  50, W-30, 180, 10, (235,245,255), (100,149,237), 1)
    ltext(d, 44, 66, "Client Tier  (Presentation Layer)", LHDR, (50,100,200))

    # T2: Internet Gateway y=220-300  (HTTPS only)
    rr(d, 30, 220, 500, 300, 10, (240,240,255), (130,100,200), 1)
    ltext(d, 44, 236, "Internet Gateway", LHDR, (90,60,180))

    # T3: Application Tier y=340-430  (Backend + TgAPI side-by-side)
    rr(d, 30, 340, W-30, 430, 10, (232,245,233), (56,142,60), 1)
    ltext(d, 44, 356, "Application Tier  (Business Logic)", LHDR, (30,120,50))

    # T4: Data y=470-570
    rr(d, 30, 470, W-30, 570, 10, (255,248,225), (245,165,0), 1)
    ltext(d, 44, 486, "Data Tier  (Storage Layer)", LHDR, (160,110,0))

    # ── Boxes ───────────────────────────────────────────────
    # Web Admin (T1)
    box(d, 50, 82, 230, 170, (25,118,210), (227,242,253),
        "Web Admin Portal", ["React.js"])
    # Mini App (T1)
    box(d, 300, 82, 490, 170, (25,118,210), (227,242,253),
        "Telegram Mini App", ["Web App SDK"])
    # Manager Bot (T1 right)
    box(d, 660, 82, 850, 170, (21,101,192), (187,222,251),
        "Manager Bot", ["Telegram Chat"])

    # HTTPS Gateway (T2)
    box(d, 100, 250, 420, 292, (94,53,177), (237,231,246),
        "HTTPS / WSS Gateway", ["Cloudflare / Nginx"])

    # Backend API (T3 left)
    box(d, 50, 368, 480, 412, (46,125,50), (200,230,201),
        "Backend API Server", ["Python  FastAPI"])

    # Telegram Bot API (T3 right) — External
    box(d, 580, 362, 910, 418, (230,81,0), (255,224,178),
        "Telegram Bot API", ["External Service"])

    # Relational DB (T4)
    box(d, 60, 500, 310, 554, (245,127,23), (255,236,179),
        "Relational DB", ["Supabase PostgreSQL"])
    # Object Storage (T4)
    box(d, 370, 500, 600, 554, (245,127,23), (255,236,179),
        "Object Storage", ["Supabase Storage"])

    # ── Arrows ───────────────────────────────────────────────
    # Web Admin → Gateway
    arrow_down(d, 140, 170, 250, label="HTTPS", lf=LA, lo=143)
    # Mini App → Gateway
    arrow_down(d, 395, 170, 250, label="HTTPS", lf=LA, lo=398)
    # Gateway → Backend
    arrow_down(d, 260, 292, 368, label="Route Traffic", lf=LA, lo=263)
    # Backend → DB
    arrow_down(d, 185, 412, 500, label="SQL Queries", lf=LA, lo=188)
    # Backend → Object Storage
    arrow_down(d, 430, 412, 500, label="Upload Photos", lf=LA, lo=433)
    # Backend → TgAPI  (horizontal, clear 100px gap between the two boxes)
    arrow_right(d, 480, 580, 390, label=None, lf=LA)
    ctext(d, 530, 375, "Send Notification", LA, (80,80,80))
    # TgAPI ↔ Manager Bot  (vertical on right side)
    d.line([(735, 362),(735, 170)], fill=(80,80,80), width=2)
    d.polygon([(730,178),(740,178),(735,170)], fill=(80,80,80))
    d.polygon([(730,354),(740,354),(735,362)], fill=(80,80,80))
    lb = fnt(10)
    ctext(d, 800, 268, "Notifications /", lb, (100,100,100))
    ctext(d, 800, 281, "Commands", lb, (100,100,100))

    img.save(os.path.join(IMGDIR, "01_system_architecture.png"), dpi=(150,150))
    print("Saved: 01_system_architecture.png")


# ═══════════════════════════════════════════════════════════════
# 2. COMPONENT DIAGRAM
# ═══════════════════════════════════════════════════════════════
def make_component():
    W, H = 1000, 660
    img = Image.new("RGB", (W, H), (248,250,252))
    d   = ImageDraw.Draw(img, "RGBA")

    ft = fnt(16)
    ctext(d, W//2, 22, "C3MR – Component Diagram", ft, (30,30,30))
    d.line([(40,36),(W-40,36)], fill=(200,210,220), width=1)

    LA = fnt(10)

    # ── Column backgrounds ─────────────────────────────────────
    rr(d, 20,  50, 315, 610, 10, (235,245,255), (100,149,237), 1)
    ctext(d, 167, 68, "Client Layer", fnt(13), (50,100,200))

    rr(d, 355, 50, 665, 610, 10, (232,245,233), (56,142,60), 1)
    ctext(d, 510, 68, "Backend  (FastAPI)", fnt(13), (30,120,50))

    rr(d, 705, 50, 980, 610, 10, (255,248,225), (245,165,0), 1)
    ctext(d, 842, 68, "Supabase + External", fnt(13), (160,110,0))

    # ── Client boxes ───────────────────────────────────────────
    # y=90  Web Admin
    box(d, 40,  90, 290, 162, (25,118,210), (227,242,253),
        "Web Admin (React.js)", ["Dashboard View", "Target Mgmt View"])
    # y=210  Mini App
    box(d, 40, 210, 290, 282, (25,118,210), (227,242,253),
        "Telegram Mini App", ["Task List View", "Report Form View"])
    # y=420  Manager Bot  (aligned with Notification Service)
    box(d, 40, 420, 290, 492, (21,101,192), (187,222,251),
        "Manager Bot", ["Bot Handler  (/summary)"])

    # ── Backend boxes  (well-spaced, no Validator shown) ───────
    # y=90  Target Controller
    box(d, 375,  90, 645, 162, (46,125,50), (200,230,201),
        "Target Controller", ["GET /targets", "POST /targets/assign"])
    # y=220  Report Controller
    box(d, 375, 220, 645, 292, (46,125,50), (200,230,201),
        "Report Controller", ["POST /reports  +  validate()"])
    # y=360  Notification Service
    box(d, 375, 360, 645, 432, (46,125,50), (200,230,201),
        "Notification Service", ["trigger()  →  sendMessage()"])
    # y=490  Summary Controller
    box(d, 375, 490, 645, 562, (46,125,50), (200,230,201),
        "Summary Controller", ["webhook  →  aggregate()"])

    # ── Data + External boxes ──────────────────────────────────
    # y=90  PostgreSQL
    box(d, 725,  90, 960, 180, (245,127,23), (255,236,179),
        "PostgreSQL", ["Users", "Targets", "Reports"])
    # y=220  Object Storage
    box(d, 725, 220, 960, 292, (245,127,23), (255,236,179),
        "Object Storage", ["Photo evidence"])
    # y=400  Telegram Bot API
    box(d, 725, 400, 960, 472, (230,81,0), (255,224,178),
        "Telegram Bot API", ["sendMessage()", "Webhook POST"])

    # ── Arrows ─────────────────────────────────────────────────
    # Web Admin → Target Controller
    arrow_right(d, 290, 375, 126, label="HTTP GET / PUT", lf=LA)

    # Mini App → Target Controller
    arrow_right(d, 290, 375, 246, label="HTTP GET", lf=LA)
    # Mini App → Report Controller (offset slightly below)
    arrow_right(d, 290, 375, 262, label="HTTP POST", lf=LA)

    # Report Controller → Notification Service (vertical, clear gap 292→360)
    arrow_down(d, 510, 292, 360, label="trigger()", lf=LA, lo=514)

    # Report Controller → Notification Service (vertical, clear gap 292→360)
    # Target Controller → PostgreSQL
    arrow_right(d, 645, 725, 126, label="query()", lf=LA)

    # Report Controller → PostgreSQL
    arrow_right(d, 645, 725, 252, label="INSERT report", lf=LA)
    # Report Controller → Object Storage
    arrow_right(d, 645, 725, 268, label="upload()", lf=LA)

    # Notification Service → TgAPI  (horizontal, y=396)
    arrow_right(d, 645, 725, 416, label="sendMessage()", lf=LA)

    # TgAPI → Manager Bot  (push notification, y=436, going left)
    d.line([(725, 436),(290, 456)], fill=(150,150,150), width=1)
    d.polygon([(298,452),(298,460),(290,456)], fill=(150,150,150))
    ctext(d, 507, 444, "push notification", LA, (100,100,100))

    # Manager Bot → TgAPI  (/summary command, y=460, going right)
    d.line([(290, 474),(725, 460)], fill=(100,100,180), width=1)
    d.polygon([(717,456),(717,464),(725,460)], fill=(100,100,180))
    ctext(d, 507, 467, "/summary command", LA, (100,100,180))

    # TgAPI → Summary Controller  (webhook)
    d.line([(843,472),(843,525),(645,525)], fill=(150,150,150), width=1)
    d.polygon([(653,521),(653,529),(645,525)], fill=(150,150,150))
    ltext(d, 848, 500, "webhook", LA, (130,130,130))

    # Summary Controller → PostgreSQL
    arrow_right(d, 645, 725, 525, label="aggregate()", lf=LA)

    img.save(os.path.join(IMGDIR, "04_component_diagram.png"), dpi=(150,150))
    print("Saved: 04_component_diagram.png")


# ═══════════════════════════════════════════════════════════════
# 3. SEQUENCE DIAGRAM
# ═══════════════════════════════════════════════════════════════
def make_sequence():
    participants = [
        ("Field Officer",   (33,150,243),  (227,242,253)),
        ("Mini App",        (81,45,168),   (237,231,246)),
        ("FastAPI",         (46,125,50),   (200,230,201)),
        ("Supabase",        (245,127,23),  (255,236,179)),
        ("Telegram Bot API",(230,81,0),    (255,224,178)),
        ("Manager",         (33,150,243),  (227,242,253)),
    ]
    steps = [
        # (from_idx, to_idx, label, dashed, note)
        (0, 1, "Fill form & upload photo",          False, None),
        (1, 2, "POST /api/reports  (JSON + Image)", False, None),
        (2, 3, "Upload image to Storage",           False, None),
        (3, 2, "Return image URL",                  True,  None),
        (2, 3, "INSERT report & UPDATE target",     False, None),
        (3, 2, "Success",                           True,  None),
        (2, 1, "HTTP 200 OK",                       True,  None),
        (1, 0, "Show  \"Report Submitted\"",         True,  None),
        (2, 4, "sendMessage(chat_id, text)",         False, "Notification triggered"),
        (4, 5, "New Report: [Customer] – [Status] by [Officer]", False, None),
    ]

    N  = len(participants)
    PW = 130   # participant box width
    PH = 44    # participant box height
    GAP = 30   # gap between participant centers ... total width
    MARGIN = 40
    W  = MARGIN*2 + N*PW + (N-1)*GAP
    TOP = 20
    HDR_BOT = TOP + PH
    STEP_H  = 52
    ROWS    = len(steps)
    BOT_PAD = 60
    H = HDR_BOT + ROWS*STEP_H + BOT_PAD

    img = Image.new("RGB", (W, H), (248,250,252))
    d   = ImageDraw.Draw(img, "RGBA")

    ft = fnt(15)
    ctext(d, W//2, 12, "C3MR – Sequence Diagram: Report Submission & Manager Notification", ft, (30,30,30))

    # centres of participants
    centres = []
    for i in range(N):
        cx = MARGIN + i*(PW+GAP) + PW//2
        centres.append(cx)

    # draw participant boxes
    fbh = fnt(11)
    for i,(name,hcol,bcol) in enumerate(participants):
        cx = centres[i]
        x1, x2 = cx-PW//2, cx+PW//2
        shadow(d, x1, TOP, x2, TOP+PH, 6)
        rr(d, x1, TOP, x2, TOP+PH, 6, bcol, hcol, 2)
        # header bar
        rr(d, x1, TOP, x2, TOP+18, 6, hcol)
        d.rectangle([x1, TOP+10, x2, TOP+18], fill=hcol)
        tw, th = tsz(d, name, fbh)
        if tw > PW-8:
            # two lines
            words = name.split()
            mid   = len(words)//2
            l1    = " ".join(words[:mid])
            l2    = " ".join(words[mid:])
            tw1,th1 = tsz(d, l1, fbh)
            tw2,th2 = tsz(d, l2, fbh)
            d.text((cx-tw1//2, TOP+20), l1, font=fbh, fill=(40,40,40))
            d.text((cx-tw2//2, TOP+32), l2, font=fbh, fill=(40,40,40))
        else:
            d.text((cx-tw//2, TOP+24), name, font=fbh, fill=(40,40,40))

    # lifelines
    lline_top    = HDR_BOT
    lline_bot    = HDR_BOT + ROWS*STEP_H + 20
    for i,(_,hcol,_) in enumerate(participants):
        cx = centres[i]
        seg, gap, cy = 6, 4, lline_top
        while cy < lline_bot:
            d.line([(cx,cy),(cx,min(cy+seg,lline_bot))], fill=(180,180,180), width=1)
            cy += seg+gap

    # step rows
    fa = fnt(11)
    fn = fnt(10)
    step_num_col = (180, 180, 180)
    for si, (fi, ti, lbl, dashed, note) in enumerate(steps):
        y = HDR_BOT + si*STEP_H + STEP_H//2

        if note:
            # draw note box
            nx1 = centres[fi]-20
            nw  = 140
            rr(d, nx1, y-14, nx1+nw, y+2, 4, (255,255,180), (180,180,100), 1)
            ctext(d, nx1+nw//2, y-6, note, fn, (100,100,50))
            y += 14

        x1, x2 = centres[fi], centres[ti]
        going_right = x2 > x1

        # draw line
        if dashed:
            seg2, gap2, cx2 = 7, 4, min(x1,x2)
            while cx2 < max(x1,x2)-7:
                d.line([(cx2,y),(min(cx2+seg2,max(x1,x2)),y)],
                       fill=(120,120,120), width=1)
                cx2 += seg2+gap2
        else:
            d.line([(x1,y),(x2,y)], fill=(60,60,60), width=2)

        # arrowhead
        if going_right:
            d.polygon([(x2-8,y-4),(x2-8,y+4),(x2,y)], fill=(60,60,60))
        else:
            d.polygon([(x2+8,y-4),(x2+8,y+4),(x2,y)], fill=(60,60,60))

        # step number
        num_str = str(si+1)
        tw, th = tsz(d, num_str, fn)
        d.text((min(x1,x2) - tw - 6, y - th//2), num_str, font=fn, fill=step_num_col)

        # label above arrow
        tw, th = tsz(d, lbl, fa)
        mx = (x1+x2)//2
        label_col = (80,80,80) if not dashed else (130,130,130)
        d.text((mx-tw//2, y-th-4), lbl, font=fa, fill=label_col)

    img.save(os.path.join(IMGDIR, "05_sequence_diagram.png"), dpi=(150,150))
    print("Saved: 05_sequence_diagram.png")


# ═══════════════════════════════════════════════════════════════
# 4. USE CASE DIAGRAM
# ═══════════════════════════════════════════════════════════════
def make_usecase():
    W, H = 920, 580
    img = Image.new("RGB", (W, H), (248,250,252))
    d   = ImageDraw.Draw(img, "RGBA")

    ft = fnt(16)
    ctext(d, W//2, 22, "C3MR – Use Case Diagram", ft, (30,30,30))
    d.line([(40,36),(W-40,36)], fill=(200,210,220), width=1)

    # System boundary
    SX1, SY1, SX2, SY2 = 145, 50, 775, 555
    rr(d, SX1, SY1, SX2, SY2, 10, (235,242,255), (80,120,200), 2)
    fsys = fnt(12)
    ctext(d, (SX1+SX2)//2, SY1+14, "\u00abSystem\u00bb  C3MR", fsys, (60,100,180))

    def stick_actor(x, y, name):
        # head
        d.ellipse([x-14, y-55, x+14, y-27], outline=(40,40,40), width=2)
        # body
        d.line([(x, y-27),(x, y+15)], fill=(40,40,40), width=2)
        # arms
        d.line([(x-22, y-10),(x+22, y-10)], fill=(40,40,40), width=2)
        # legs
        d.line([(x, y+15),(x-18, y+48)], fill=(40,40,40), width=2)
        d.line([(x, y+15),(x+18, y+48)], fill=(40,40,40), width=2)
        fn = fnt(12)
        tw, _ = tsz(d, name, fn)
        d.text((x - tw//2, y+52), name, font=fn, fill=(30,30,30))

    def uc_oval(cx, cy, text, w=175, h=34):
        x1, y1 = cx-w//2, cy-h//2
        x2, y2 = cx+w//2, cy+h//2
        rr(d, x1, y1, x2, y2, h//2, (255,255,255), (80,120,200), 1)
        fn = fnt(11)
        ctext(d, cx, cy, text, fn, (20,20,20))
        return x1, y1, x2, y2

    def connect(ax, ay, bx, by):
        d.line([(ax,ay),(bx,by)], fill=(130,130,150), width=1)

    # ── Field Officer (left actor) ──
    FA_X, FA_Y = 62, 300
    stick_actor(FA_X, FA_Y, "Field Officer")

    left_ucs = [
        (310, 120, "Open Telegram Mini App"),
        (310, 210, "View Task List"),
        (310, 300, "Submit Field Report"),
        (310, 390, "Upload Photo Evidence"),
        (310, 480, "Receive Task Notification"),
    ]
    for cx, cy, txt in left_ucs:
        x1, y1, x2, y2 = uc_oval(cx, cy, txt)
        connect(FA_X+22, FA_Y - 10, x1, cy)

    # ── Manager (right actor) ──
    MA_X, MA_Y = 858, 300
    stick_actor(MA_X, MA_Y, "Manager")

    right_ucs = [
        (620, 120, "Login to Web Portal"),
        (620, 210, "Upload CSV Targets"),
        (620, 300, "Assign Officers to Targets"),
        (620, 390, "View Dashboard & Analytics"),
        (620, 480, "Request /summary (Bot)"),
    ]
    for cx, cy, txt in right_ucs:
        x1, y1, x2, y2 = uc_oval(cx, cy, txt)
        connect(MA_X-22, MA_Y - 10, x2, cy)

    img.save(os.path.join(IMGDIR, "07_usecase_diagram.png"), dpi=(150,150))
    print("Saved: 07_usecase_diagram.png")


# ═══════════════════════════════════════════════════════════════
# 5. ACTIVITY DIAGRAM
# ═══════════════════════════════════════════════════════════════
def make_activity():
    W, H = 680, 960
    img = Image.new("RGB", (W, H), (248,250,252))
    d   = ImageDraw.Draw(img, "RGBA")

    ft = fnt(16)
    ctext(d, W//2, 22, "C3MR – Activity Diagram", ft, (30,30,30))
    d.line([(40,36),(W-40,36)], fill=(200,210,220), width=1)

    CX   = W // 2       # center x
    fa   = fnt(11)      # arrow label
    fb   = fnt(12)      # box text

    COLORS = {
        "admin":   ((25,118,210),  (227,242,253)),
        "officer": ((46,125,50),   (200,230,201)),
        "system":  ((94,53,177),   (237,231,246)),
        "manager": ((230,81,0),    (255,224,178)),
    }

    def act_box(cy, text, kind, w=340, h=38):
        hcol, bcol = COLORS[kind]
        x1, y1 = CX - w//2, cy - h//2
        x2, y2 = CX + w//2, cy + h//2
        shadow(d, x1, y1, x2, y2, 6)
        rr(d, x1, y1, x2, y2, 8, bcol, hcol, 1)
        rr(d, x1, y1, x2, y1+18, 8, hcol)
        d.rectangle([x1, y1+10, x2, y1+18], fill=hcol)
        ctext(d, CX, cy+4, text, fb, (20,20,20))
        return y2

    def diamond(cy, question, w=280, h=44):
        cx = CX
        pts = [(cx, cy-h//2), (cx+w//2, cy), (cx, cy+h//2), (cx-w//2, cy)]
        d.polygon(pts, fill=(255,253,230), outline=(180,150,0), width=2)
        fn = fnt(11)
        ctext(d, cx, cy, question, fn, (80,60,0))
        return cy + h//2

    def start_end(cy, is_end=False):
        r = 14
        d.ellipse([CX-r, cy-r, CX+r, cy+r],
                  fill=(30,30,30) if not is_end else (255,255,255),
                  outline=(30,30,30), width=3 if is_end else 0)
        if is_end:
            d.ellipse([CX-8, cy-8, CX+8, cy+8], fill=(30,30,30))
        return cy + r

    def arr(y1, y2, label=None):
        d.line([(CX, y1),(CX, y2)], fill=(80,80,80), width=2)
        d.polygon([(CX-5,y2-8),(CX+5,y2-8),(CX,y2)], fill=(80,80,80))
        if label:
            tw, th = tsz(d, label, fa)
            d.text((CX+8, (y1+y2)//2 - th//2), label, font=fa, fill=(110,110,110))

    y = 60
    start_end(y)
    arr(y+14, y+40)
    y = 78

    steps = [
        ("Admin uploads CSV targets via Web Portal", "admin"),
        ("System creates & assigns targets to officers", "system"),
        ("Officer receives task notification (Bot)", "officer"),
        ("Officer opens Mini App & views task list", "officer"),
        ("Officer conducts field visit to customer", "officer"),
        ("Officer fills in report form", "officer"),
    ]

    for text, kind in steps:
        y += 42
        y2 = act_box(y, text, kind)
        arr(y2, y2 + 20)
        y = y2 + 20

    # Decision: Photo uploaded?
    y += 22
    y_dec = y + 22
    bot = diamond(y_dec, "Photo evidence uploaded?")
    # "No" branch — loop back left
    no_x = CX - 140 - 30
    upload_y = bot + 50
    d.line([(CX - 140, y_dec),(no_x, y_dec)], fill=(80,80,80), width=2)
    d.line([(no_x, y_dec),(no_x, upload_y)], fill=(80,80,80), width=2)
    d.line([(no_x, upload_y),(CX - 170, upload_y)], fill=(80,80,80), width=2)
    rr(d, CX-170, upload_y-16, CX+170, upload_y+16, 8, (255,224,178), (230,81,0), 1)
    ctext(d, CX, upload_y, "Upload photo evidence", fnt(11), (20,20,20))
    # label No
    d.text((no_x+4, y_dec-16), "No", font=fa, fill=(180,40,40))
    # arrow from upload box back to diamond left
    d.line([(no_x, upload_y+16),(no_x, y_dec+4)], fill=(80,80,80), width=2)

    # "Yes" arrow down
    d.text((CX+8, bot+6), "Yes", font=fa, fill=(40,140,40))
    arr(bot, bot+30)
    y = bot + 30

    more_steps = [
        ("Officer submits report", "officer"),
        ("System stores report & updates status: Completed", "system"),
        ("System sends notification to Manager Bot", "system"),
        ("Manager receives notification", "manager"),
    ]
    for text, kind in more_steps:
        y += 42
        y2 = act_box(y, text, kind)
        arr(y2, y2 + 20)
        y = y2 + 20

    y += 14
    start_end(y, is_end=True)

    # Legend
    legend_y = H - 105
    d.text((50, legend_y), "Legend:", font=fnt(11), fill=(80,80,80))
    items = [("Admin","admin"),("Field Officer","officer"),("System","system"),("Manager","manager")]
    lx = 50
    for name, kind in items:
        hc, bc = COLORS[kind]
        rr(d, lx, legend_y+16, lx+14, legend_y+30, 3, bc, hc, 1)
        d.text((lx+18, legend_y+17), name, font=fnt(10), fill=(50,50,50))
        lx += 115

    img.save(os.path.join(IMGDIR, "08_activity_diagram.png"), dpi=(150,150))
    print("Saved: 08_activity_diagram.png")


# ═══════════════════════════════════════════════════════════════
# 6. ERD DIAGRAM
# ═══════════════════════════════════════════════════════════════
def make_erd():
    W, H = 960, 580
    img = Image.new("RGB", (W, H), (248,250,252))
    d   = ImageDraw.Draw(img, "RGBA")

    ft = fnt(16)
    ctext(d, W//2, 22, "C3MR – Entity Relationship Diagram", ft, (30,30,30))
    d.line([(40,36),(W-40,36)], fill=(200,210,220), width=1)

    fb = fnt(11)
    fk = fnt(10)

    def entity(x1, y1, name, attrs, hdr_col, body_col):
        """Draw entity box. Returns (x1,y1,x2,y2,cx,cy)."""
        row_h = 20
        h = 28 + len(attrs) * row_h + 6
        x2, y2 = x1 + 210, y1 + h
        shadow(d, x1, y1, x2, y2, 6)
        rr(d, x1, y1, x2, y2, 6, body_col, hdr_col, 2)
        rr(d, x1, y1, x2, y1+28, 6, hdr_col)
        d.rectangle([x1, y1+16, x2, y1+28], fill=hdr_col)
        ctext(d, (x1+x2)//2, y1+14, name, fnt(12), (255,255,255))
        ay = y1 + 34
        for attr in attrs:
            col = (180,80,80) if "PK" in attr else ((80,80,180) if "FK" in attr else (50,50,50))
            d.text((x1+10, ay), attr, font=fk, fill=col)
            ay += row_h
        return x1, y1, x2, y2, (x1+x2)//2, (y1+y2)//2

    def rel_line(x1,y1,x2,y2, card1="1", card2="N", label=None):
        d.line([(x1,y1),(x2,y2)], fill=(100,100,120), width=2)
        fn = fnt(10)
        # cardinality labels
        d.text((x1+4, y1+2), card1, font=fn, fill=(40,40,180))
        d.text((x2-18, y2+2), card2, font=fn, fill=(40,40,180))
        if label:
            mx, my = (x1+x2)//2, (y1+y2)//2
            tw, th = tsz(d, label, fn)
            rr(d, mx-tw//2-2, my-th//2-1, mx+tw//2+2, my+th//2+1, 3, (248,250,252))
            d.text((mx-tw//2, my-th//2), label, font=fn, fill=(100,100,100))

    # ── Entities ──
    # users (top-left)
    ux1,uy1,ux2,uy2,ucx,ucy = entity(
        40, 60, "users",
        ["PK  user_id","    name","    telegram_id","    role","    created_at"],
        (25,118,210), (227,242,253)
    )

    # targets (top-right)
    tx1,ty1,tx2,ty2,tcx,tcy = entity(
        390, 60, "targets",
        ["PK  target_id","    customer_name","    address","    phone",
         "    amount_due","    status","FK  assigned_officer_id","    created_at"],
        (46,125,50), (200,230,201)
    )

    # reports (bottom-right)
    rx1,ry1,rx2,ry2,rcx,rcy = entity(
        700, 290, "reports",
        ["PK  report_id","FK  target_id","FK  officer_id",
         "    payment_status","    notes","    photo_url","    submitted_at"],
        (94,53,177), (237,231,246)
    )

    # upload_batches (bottom-left)
    bx1,by1,bx2,by2,bcx,bcy = entity(
        40, 380, "upload_batches",
        ["PK  batch_id","FK  manager_id","    filename","    total_records","    created_at"],
        (245,127,23), (255,236,179)
    )

    # ── Relationships ──
    # users → targets (1:N) via assigned_officer_id
    rel_line(ux2, ucy, tx1, tcy, "1", "N", "assigns")
    # targets → reports (1:1)
    rel_line(tx2, ty2+40, rx1, rcy, "1", "1", "has")
    # users → reports (1:N) via officer_id
    rel_line(ux2, uy2-20, rx1, ry1+30, "1", "N", "submits")
    # users → upload_batches (1:N)
    rel_line(ucx, uy2, bcx, by1, "1", "N", "creates")

    img.save(os.path.join(IMGDIR, "09_erd_diagram.png"), dpi=(150,150))
    print("Saved: 09_erd_diagram.png")


# ═══════════════════════════════════════════════════════════════
# 7. DFD LEVEL 0 – CONTEXT DIAGRAM
# ═══════════════════════════════════════════════════════════════
def make_dfd_level0():
    """DFD Level 0 setelah revisi mayor Agustus 2026.

    Tiga hal yang berubah dari versi lama, dan yang pertama adalah salah fakta:
      - Penyimpanan tertulis "Supabase". Sistemnya memakai PostgreSQL di Railway;
        Supabase tidak pernah dipakai di produksi.
      - Administrator belum ada sebagai entitas — perannya baru dipisah dari
        manajer, dan dialah yang mengelola akun serta mode pemeliharaan.
      - Telegram Bot API belum digambarkan sebagai entitas luar, padahal semua
        notifikasi, penautan nomor, dan perintah bot lewat sana.
    """
    W, H = 1020, 660
    img = Image.new("RGB", (W, H), (248,250,252))
    d   = ImageDraw.Draw(img, "RGBA")

    ft = fnt(16)
    ctext(d, W//2, 22, "C3MR – DFD Level 0 (Context Diagram)", ft, (30,30,30))
    d.line([(40,36),(W-40,36)], fill=(200,210,220), width=1)

    LA = fnt(11)
    LS = fnt(10)

    def entity(x1, y1, x2, y2, title, sub, hcol, bcol):
        shadow(d, x1, y1, x2, y2, 8)
        rr(d, x1, y1, x2, y2, 8, bcol, hcol, 2)
        rr(d, x1, y1, x2, y1+26, 8, hcol)
        d.rectangle([x1, y1+14, x2, y1+26], fill=hcol)
        ctext(d, (x1+x2)//2, y1+13, title, fnt(12), (255,255,255))
        ctext(d, (x1+x2)//2, y1+44, sub, fnt(10), (50,50,50))

    def dbl_arrow(x1, y1, x2, y2, lbl_fwd, lbl_back, horiz=True):
        """Draw two parallel arrows (forward + return) with labels."""
        OFF = 10  # offset between the two arrows
        if horiz:
            # forward (top line)
            d.line([(x1, y1-OFF),(x2, y1-OFF)], fill=(60,60,60), width=2)
            if x2 > x1:
                d.polygon([(x2-8, y1-OFF-4),(x2-8, y1-OFF+4),(x2, y1-OFF)], fill=(60,60,60))
            else:
                d.polygon([(x2+8, y1-OFF-4),(x2+8, y1-OFF+4),(x2, y1-OFF)], fill=(60,60,60))
            tw, th = tsz(d, lbl_fwd, LS)
            ctext(d, (x1+x2)//2, y1-OFF-th-2, lbl_fwd, LS, (50,50,150))
            # return (bottom line, dashed)
            seg, gap, cx = 7, 4, min(x1,x2)
            while cx < max(x1,x2)-7:
                d.line([(cx, y1+OFF),(min(cx+seg, max(x1,x2)), y1+OFF)],
                       fill=(120,120,120), width=1)
                cx += seg+gap
            if x2 > x1:
                d.polygon([(x1+8, y1+OFF-3),(x1+8, y1+OFF+3),(x1, y1+OFF)], fill=(120,120,120))
            else:
                d.polygon([(x1-8, y1+OFF-3),(x1-8, y1+OFF+3),(x1, y1+OFF)], fill=(120,120,120))
            tw, th = tsz(d, lbl_back, LS)
            ctext(d, (x1+x2)//2, y1+OFF+4, lbl_back, LS, (120,120,120))
        else:  # vertical
            d.line([(x1-OFF, y1),(x1-OFF, y2)], fill=(60,60,60), width=2)
            d.polygon([(x1-OFF-4, y2-8),(x1-OFF+4, y2-8),(x1-OFF, y2)], fill=(60,60,60))
            tw, th = tsz(d, lbl_fwd, LS)
            d.text((x1-OFF-tw-4, (y1+y2)//2 - th//2), lbl_fwd, font=LS, fill=(50,50,150))
            # return dashed
            seg, gap, cy = 7, 4, min(y1,y2)
            while cy < max(y1,y2)-7:
                d.line([(x1+OFF, cy),(x1+OFF, min(cy+seg, max(y1,y2)))],
                       fill=(120,120,120), width=1)
                cy += seg+gap
            d.polygon([(x1+OFF-3, y1+8),(x1+OFF+3, y1+8),(x1+OFF, y1)], fill=(120,120,120))
            tw, th = tsz(d, lbl_back, LS)
            d.text((x1+OFF+4, (y1+y2)//2 - th//2), lbl_back, font=LS, fill=(120,120,120))

    # ── Central system box ──
    CX, CY = W//2, 330
    CW, CH = 220, 110
    shadow(d, CX-CW//2, CY-CH//2, CX+CW//2, CY+CH//2, 10)
    rr(d, CX-CW//2, CY-CH//2, CX+CW//2, CY+CH//2, 10,
       (220,235,255), (50,100,200), 2)
    ctext(d, CX, CY-22, "C3MR", fnt(18), (20,60,180))
    ctext(d, CX, CY+2, "System", fnt(14), (20,60,180))
    ctext(d, CX, CY+26, "API · Bot · Mini App", fnt(10), (60,90,160))

    LEFT, RIGHT = CX-CW//2, CX+CW//2
    TOP, BOTTOM = CY-CH//2, CY+CH//2

    # ── External entities ──
    entity(40, 265, 230, 395,
           "Field Officer", "Telegram Mini App",
           (25,118,210), (227,242,253))

    entity(790, 265, 980, 395,
           "Manager", "Web Portal + Bot",
           (21,101,192), (187,222,251))

    # Administrator: peran ketiga hasil revisi. Menu web-nya terpisah dari manajer —
    # ia mengelola akun, peran, dan mode pemeliharaan, tanpa melihat data operasional.
    entity(250, 60, 450, 175,
           "Administrator", "Web Portal",
           (94,53,177), (237,231,246))

    # Telegram Bot API: jalur keluar semua notifikasi dan jalur masuk kartu kontak
    # yang dipakai petugas untuk menautkan akunnya sendiri.
    entity(570, 60, 770, 175,
           "Telegram Bot API", "External Service",
           (0,137,123), (224,242,241))

    # Railway PostgreSQL, bukan Supabase.
    entity(410, 500, 610, 620,
           "PostgreSQL", "Railway (managed)",
           (245,127,23), (255,236,179))

    # ── Data flow arrows ──
    dbl_arrow(230, CY, LEFT, CY,
              "Visit report + photo", "Assigned tasks", horiz=True)

    dbl_arrow(RIGHT, CY, 790, CY,
              "Targets, assignment", "Dashboard, analytics", horiz=True)

    dbl_arrow(350, 175, 350, TOP,
              "Accounts & roles", "Audit log", horiz=False)

    # Ketiga notifikasi keluar dijadikan satu label, bukan digambar sebagai garis
    # terpisah: garis tambahan dari sisi kanan sistem memotong panah ini dan justru
    # membuat diagramnya lebih sulit dibaca daripada informasinya menolong.
    dbl_arrow(670, 175, 670, TOP,
              "Notifications: visit, weekly, reset code",
              "Commands, shared contact", horiz=False)

    dbl_arrow(CX, BOTTOM, CX, 500,
              "Store data", "Retrieve data", horiz=False)

    img.save(os.path.join(IMGDIR, "10_dfd_level0.png"), dpi=(150,150))
    print("Saved: 10_dfd_level0.png")


# ── Jalankan ───────────────────────────────────────────────────
# Tanpa argumen semua diagram dibuat ulang. Beri nama diagram sebagai argumen untuk
# membuat sebagian saja — penting saat hanya satu diagram yang direvisi, supaya
# gambar lain tidak ikut ditimpa render baru yang isinya belum tentu sama.
ALL = {
    "architecture": make_architecture,
    "component":    make_component,
    "sequence":     make_sequence,
    "usecase":      make_usecase,
    "activity":     make_activity,
    "erd":          make_erd,
    "dfd":          make_dfd_level0,
}

if __name__ == "__main__":
    import sys
    names = sys.argv[1:] or list(ALL)
    unknown = [n for n in names if n not in ALL]
    if unknown:
        sys.exit(f"diagram tidak dikenal: {unknown}. Pilihan: {', '.join(ALL)}")
    for n in names:
        ALL[n]()
    print(f"Selesai: {', '.join(names)} → {IMGDIR}")
