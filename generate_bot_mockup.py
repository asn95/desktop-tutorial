"""
Generate a realistic Telegram Manager Bot chat mockup.
"""
from PIL import Image, ImageDraw, ImageFont
import math

# ── Fonts ──────────────────────────────────────────────────────────
FONT_PATH      = "/System/Library/Fonts/SFNS.ttf"
FONT_MONO      = "/System/Library/Fonts/SFNSMono.ttf"
ARIAL          = "/Library/Fonts/Arial Unicode.ttf"

def load(size, bold=False):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except:
        try:
            return ImageFont.truetype(ARIAL, size)
        except:
            return ImageFont.load_default()

# ── Colors ─────────────────────────────────────────────────────────
TG_BLUE        = (33,  150, 243)   # header blue
TG_BG          = (230, 235, 240)   # chat background
BUBBLE_IN      = (255, 255, 255)   # incoming bubble (bot)
BUBBLE_OUT     = (220, 248, 198)   # outgoing bubble (user) – WhatsApp green style
                                   # Telegram uses a blue gradient; simplified here
BUBBLE_OUT_TG  = (219, 234, 254)   # Telegram blue outgoing
TEXT_DARK      = (33,  33,  33)
TEXT_GREY      = (140, 140, 140)
TEXT_BLUE      = (33,  150, 243)
TEXT_GREEN     = (39,  174,  96)
TEXT_ORANGE    = (230, 126,  34)
DIVIDER        = (200, 210, 220)
WHITE          = (255, 255, 255)
SHADOW         = (180, 190, 200, 80)

# ── Canvas ─────────────────────────────────────────────────────────
W, H = 540, 920
img  = Image.new("RGB", (W, H), TG_BG)
d    = ImageDraw.Draw(img, "RGBA")

# ── Helpers ────────────────────────────────────────────────────────
def rounded_rect(draw, xy, radius, fill, outline=None, outline_width=1):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill,
                            outline=outline, width=outline_width)

def text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]

def incoming_bubble(draw, y, lines, time_str, accent=None, title=None, margin=16, bw=380):
    """Draw a white incoming bubble on the left side."""
    f_body  = load(15)
    f_small = load(12)
    f_title = load(15)

    # measure total height
    pad = 12
    total_h = pad
    if title:
        total_h += 20
    for color, text in lines:
        tw, th = text_size(draw, text, f_body)
        total_h += th + 4
    total_h += 20 + pad  # time row

    x1, y1 = margin, y
    x2, y2 = x1 + bw, y1 + total_h

    # shadow
    draw.rounded_rectangle([x1+2, y1+2, x2+2, y2+2], radius=12,
                            fill=(180, 190, 200, 60))
    # bubble
    rounded_rect(draw, [x1, y1, x2, y2], 12, BUBBLE_IN)

    # accent bar
    if accent:
        draw.rounded_rectangle([x1+1, y1+1, x1+4, y2-1], radius=2, fill=accent)

    cy = y1 + pad
    if title:
        draw.text((x1 + pad, cy), title, font=f_title, fill=TEXT_BLUE)
        cy += 22

    for color, text in lines:
        draw.text((x1 + pad, cy), text, font=f_body, fill=color)
        _, th = text_size(draw, text, f_body)
        cy += th + 4

    # time
    draw.text((x2 - pad - 35, y2 - 18), time_str, font=f_small, fill=TEXT_GREY)
    return y2 + 10

def outgoing_bubble(draw, y, text, time_str, margin=16, bw=320):
    """Draw a blue outgoing bubble on the right side."""
    f_body  = load(15)
    f_small = load(12)
    pad = 12

    tw, th = text_size(draw, text, f_body)
    total_h = pad + th + 20 + pad

    x2 = W - margin
    x1 = x2 - bw
    y1, y2 = y, y + total_h

    rounded_rect(draw, [x1, y1, x2, y2], 12, BUBBLE_OUT_TG)
    draw.text((x1 + pad, y1 + pad), text, font=f_body, fill=TEXT_DARK)
    draw.text((x2 - pad - 35, y2 - 18), time_str, font=f_small, fill=TEXT_GREY)
    return y2 + 10

def date_chip(draw, y, label):
    f = load(12)
    tw, th = text_size(draw, label, f)
    cx = W // 2
    x1, y1 = cx - tw//2 - 10, y
    x2, y2 = cx + tw//2 + 10, y + th + 8
    rounded_rect(draw, [x1, y1, x2, y2], 10, (190, 205, 220))
    draw.text((cx - tw//2, y1 + 4), label, font=f, fill=WHITE)
    return y2 + 12

# ── Header ─────────────────────────────────────────────────────────
HEADER_H = 64
d.rectangle([0, 0, W, HEADER_H], fill=TG_BLUE)

# Avatar circle
d.ellipse([14, 12, 50, 48], fill=WHITE)
d.ellipse([17, 15, 47, 45], fill=(100, 181, 246))
# Bot icon letter
f_av = load(18)
tw, th = text_size(d, "B", f_av)
d.text((32 - tw//2, 30 - th//2 - 1), "B", font=f_av, fill=WHITE)

# Name & subtitle
f_name = load(17)
f_sub  = load(13)
d.text((62, 12), "C3MR Manager Bot", font=f_name, fill=WHITE)
d.text((62, 34), "bot", font=f_sub, fill=(200, 230, 255))

# Back arrow (simple <)
f_arrow = load(20)
d.text((0, 18), "  ‹", font=f_arrow, fill=WHITE)

# Three-dot menu
for i in range(3):
    cx = W - 22 + 0
    cy = 28 + (i - 1) * 7
    d.ellipse([cx-2, cy-2, cx+2, cy+2], fill=WHITE)

# ── Chat content ───────────────────────────────────────────────────
cy = HEADER_H + 12

cy = date_chip(d, cy, "Today")

# --- Notification 1 ---
cy = incoming_bubble(d, cy,
    lines=[
        (TEXT_DARK,   "New Report Submitted"),
        (TEXT_DARK,   "Customer  :  Siti Aminah"),
        (TEXT_GREEN,  "Status      :  Paid"),
        (TEXT_DARK,   "Officer     :  Auza Rahman"),
    ],
    time_str="10:32",
    accent=TEXT_GREEN,
    title="[C3MR]  New Report"
)

# --- Notification 2 ---
cy = incoming_bubble(d, cy,
    lines=[
        (TEXT_DARK,   "New Report Submitted"),
        (TEXT_DARK,   "Customer  :  Ahmad Wijaya"),
        (TEXT_ORANGE, "Status      :  Promise to Pay"),
        (TEXT_DARK,   "Officer     :  Rashad Abdul Faqih"),
    ],
    time_str="11:15",
    accent=TEXT_ORANGE,
    title="[C3MR]  New Report"
)

# --- User sends /summary ---
cy = outgoing_bubble(d, cy, "/summary", "11:20")

# --- Bot replies with summary ---
cy = incoming_bubble(d, cy,
    lines=[
        (TEXT_BLUE,   "Daily Summary Report"),
        (TEXT_DARK,   "Total Targets   :  150"),
        (TEXT_GREEN,  "Completed       :  45   (30%)"),
        (TEXT_ORANGE, "In Progress     :  60   (40%)"),
        (TEXT_DARK,   "Pending         :  45   (30%)"),
    ],
    time_str="11:20",
    accent=TEXT_BLUE,
    title="[C3MR]  Summary"
)

# ── Bottom bar ─────────────────────────────────────────────────────
BAR_Y = H - 56
d.rectangle([0, BAR_Y, W, H], fill=WHITE)
d.line([0, BAR_Y, W, BAR_Y], fill=DIVIDER, width=1)

# Input field
rounded_rect(d, [12, BAR_Y + 10, W - 56, H - 10], 20, (240, 243, 246))
f_hint = load(14)
d.text((28, BAR_Y + 18), "Message...", font=f_hint, fill=TEXT_GREY)

# Send button circle
d.ellipse([W - 50, BAR_Y + 8, W - 10, H - 8], fill=TG_BLUE)
f_send = load(18)
tw, th = text_size(d, "➤", f_send)
d.text((W - 30 - tw//2 - 2, BAR_Y + 28 - th//2), "➤", font=f_send, fill=WHITE)

# ── Save ───────────────────────────────────────────────────────────
out = "/Users/auzasyamil/Documents/Capstone/capstone1/uml/images/06_mockup_manager_bot.png"
img.save(out, dpi=(150, 150))
print(f"Saved: {out}")
