import streamlit as st
from pypdf import PdfReader
import io
import math
import pandas as pd
from PIL import Image
import fitz  # PyMuPDF

st.set_page_config(
    page_title="GolanCopy — מחשבון מטרים",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

col1, col2, col3 = st.columns([0.5, 2, 0.5])
with col2:
    try:
        st.image("logo.png", use_container_width=True)
    except:
        pass

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap');
:root {
    --ink: #0a0a0f; --paper: #f5f2eb; --blueprint: #1a3a5c;
    --cyan: #00b4d8; --amber: #f4a261; --grid: rgba(26,58,92,0.08); --success: #2a9d8f;
}
html, body, [class*="css"] { font-family:'Syne',sans-serif; background-color:var(--paper); color:var(--ink); }
.stApp {
    background-color:var(--paper);
    background-image: linear-gradient(var(--grid) 1px,transparent 1px), linear-gradient(90deg,var(--grid) 1px,transparent 1px);
    background-size:28px 28px;
}
.main-header { background:var(--blueprint); color:white; padding:2rem 3rem; margin:-1rem -1rem 2rem -1rem; border-bottom:4px solid var(--cyan); }
.main-header h1 { font-family:'Space Mono',monospace; font-size:2rem; font-weight:700; margin:0; }
.main-header p  { font-size:0.9rem; opacity:0.75; margin:0.3rem 0 0; letter-spacing:0.05em; }
.card { background:white; border:1.5px solid rgba(26,58,92,0.15); border-radius:4px; padding:1.5rem; margin-bottom:1rem; box-shadow:3px 3px 0 rgba(26,58,92,0.08); }
.big-result { background:var(--blueprint); color:white; border-radius:6px; padding:1.4rem 1.8rem; margin:0.5rem 0; border-left:6px solid var(--cyan); font-family:'Space Mono',monospace; }
.big-result .label { font-size:0.7rem; letter-spacing:0.15em; text-transform:uppercase; opacity:0.65; }
.big-result .value { font-size:2.8rem; font-weight:800; line-height:1.1; }
.big-result .sub   { font-size:0.8rem; opacity:0.65; margin-top:0.3rem; line-height:1.6; }
.section-label { font-family:'Space Mono',monospace; font-size:0.7rem; letter-spacing:0.15em; text-transform:uppercase; color:var(--blueprint); opacity:0.6; margin-bottom:0.5rem; border-bottom:1px dashed rgba(26,58,92,0.2); padding-bottom:0.3rem; }
.tag { display:inline-block; border-radius:2px; padding:0.1rem 0.55rem; font-size:0.72rem; font-family:'Space Mono',monospace; font-weight:700; letter-spacing:0.04em; }
.t60 { background:rgba(42,157,143,0.12); color:#2a9d8f; border:1px solid #2a9d8f; }
.t91 { background:rgba(244,162,97,0.12);  color:#f4a261; border:1px solid #f4a261; }
.tA4 { background:rgba(114,9,183,0.10);   color:#7209b7; border:1px solid #7209b7; }
.tA3 { background:rgba(247,37,133,0.10);  color:#f72585; border:1px solid #f72585; }
.color-dot   { display:inline-block; width:9px; height:9px; border-radius:50%; background:#e76f51; margin-left:4px; vertical-align:middle; }
.bw-dot      { display:inline-block; width:9px; height:9px; border-radius:50%; background:#aaa; margin-left:4px; vertical-align:middle; }
div[data-testid="stFileUploader"] { border:2px dashed rgba(26,58,92,0.25)!important; border-radius:6px!important; background:rgba(255,255,255,0.6)!important; }
.stButton > button { background:var(--blueprint)!important; color:white!important; border:none!important; border-radius:3px!important; font-family:'Space Mono',monospace!important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>📐 GolanCopy — מחשבון מטרים</h1>
    <p>חישוב כמות נייר לצורך הצעות מחיר · ללא הפקת PDF</p>
    <p>GolanCopy@gmail.com · מג'דל שמס</p>
</div>
""", unsafe_allow_html=True)

# ─── Constants ────────────────────────────────────────────────────────────────
PTS_PER_CM = 72 / 2.54
SIZES = {
    "A0": (84.1, 118.9),
    "A1": (59.4,  84.1),
    "A2": (42.0,  59.4),
    "A3": (29.7,  42.0),
    "A4": (21.0,  29.7),
}
TOL_CM     = 0.5
FLAT_SIZES = {"A4", "A3"}

def pts_to_cm(p): return p / PTS_PER_CM

def detect_size(w_cm, h_cm):
    for name, (sw, sh) in SIZES.items():
        if (abs(w_cm-sw)<TOL_CM and abs(h_cm-sh)<TOL_CM) or \
           (abs(w_cm-sh)<TOL_CM and abs(h_cm-sw)<TOL_CM):
            return name
    return "Custom"

def round_up_50cm(cm):
    return math.ceil(cm / 50.0) * 50.0

def assign_roll(w_cm, h_cm):
    short   = min(w_cm, h_cm)
    long_   = max(w_cm, h_cm)
    rotated = (w_cm > h_cm)
    if short <= 60.0:
        return 60, long_, rotated
    else:
        return 91, long_, rotated

def is_color_page(pdf_bytes: bytes, page_index: int) -> bool:
    """
    Render the page at low res and check if any pixel has
    a significant color saturation (not gray/black/white).
    Returns True if the page contains color.
    """
    try:
        doc  = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[page_index]
        # render at 72 dpi (fast)
        mat  = fitz.Matrix(0.5, 0.5)
        pix  = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        doc.close()

        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        # Convert to HSV and check saturation
        hsv = img.convert("HSV")
        import numpy as np
        arr = np.array(hsv)
        saturation = arr[:, :, 1]   # channel 1 = saturation (0-255)
        # If more than 0.5% of pixels have saturation > 30 → color page
        color_pixels = (saturation > 30).sum()
        total_pixels = saturation.size
        return (color_pixels / total_pixels) > 0.005
    except Exception:
        return False   # default to BW if detection fails

def analyze_pdfs(files_data, detect_color=True):
    roll60, roll91, a4_list, a3_list = [], [], [], []

    for filename, raw_bytes in files_data:
        reader    = PdfReader(io.BytesIO(raw_bytes))
        num_pages = len(reader.pages)

        for i, page in enumerate(reader.pages):
            box  = page.mediabox
            w_cm = pts_to_cm(float(box.width))
            h_cm = pts_to_cm(float(box.height))
            name = filename if num_pages == 1 else f"{filename} (p{i+1})"
            size = detect_size(w_cm, h_cm)

            color = is_color_page(raw_bytes, i) if detect_color else False

            item = dict(name=name, w_cm=round(w_cm,1), h_cm=round(h_cm,1),
                        size=size, rotated=False, roll=None,
                        length_cm=None, rounded_cm=None, color=color)

            if size in FLAT_SIZES:
                (a4_list if size == "A4" else a3_list).append(item)
                continue

            roll_w, length, rotated = assign_roll(w_cm, h_cm)
            item.update(rotated=rotated, roll=roll_w,
                        length_cm=round(length,1),
                        rounded_cm=round_up_50cm(length))
            (roll60 if roll_w == 60 else roll91).append(item)

    return roll60, roll91, a4_list, a3_list


def color_summary(items):
    c = sum(1 for i in items if i['color'])
    b = len(items) - c
    return c, b

def roll_color_summary(items):
    c = sum(1 for i in items if i['color'])
    b = len(items) - c
    c_m = sum(i['rounded_cm'] for i in items if     i['color']) / 100
    b_m = sum(i['rounded_cm'] for i in items if not i['color']) / 100
    return c, b, c_m, b_m


# ─── UI ───────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">העלאת קבצים</div>', unsafe_allow_html=True)

col_up, col_opt = st.columns([3, 1])
with col_up:
    uploaded_files = st.file_uploader(
        "גרור לכאן קובצי PDF",
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
with col_opt:
    detect_color_opt = st.toggle("🎨 זיהוי צבע/שחור-לבן", value=True,
                                  help="מנתח כל דף ובודק אם יש בו צבע. מאט מעט את הניתוח.")

if uploaded_files:
    st.markdown("---")
    files_data = [(f.name, f.read()) for f in uploaded_files]

    with st.spinner("מנתח מידות וצבעים..." if detect_color_opt else "מנתח מידות..."):
        roll60, roll91, a4_list, a3_list = analyze_pdfs(files_data, detect_color=detect_color_opt)

    total60_raw     = sum(i['length_cm']  for i in roll60)
    total60_rounded = sum(i['rounded_cm'] for i in roll60)
    total91_raw     = sum(i['length_cm']  for i in roll91)
    total91_rounded = sum(i['rounded_cm'] for i in roll91)

    # ── תוצאות ראשיות ────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">📐 כמות נייר נדרשת</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        if roll60:
            sizes_str = ", ".join(dict.fromkeys(i['size'] for i in roll60))
            col_n, bw_n, col_m, bw_m = roll_color_summary(roll60)
            color_line = f"🎨 צבעוני: {col_n} דף ({col_m:.1f} מ') · ⬛ שח\"ל: {bw_n} דף ({bw_m:.1f} מ')" if detect_color_opt else ""
            st.markdown(f"""
            <div class="big-result">
                <div class="label"><span class="tag t60">גליל 60 ס"מ</span></div>
                <div class="value">{total60_rounded/100:.1f} מ'</div>
                <div class="sub">
                    {len(roll60)} דפים · גלם: {total60_raw/100:.2f} מ'<br>
                    גדלים: {sizes_str}<br>
                    {color_line}
                </div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="card" style="text-align:center;opacity:.5;padding:2rem">אין דפים לגליל 60 ס"מ</div>', unsafe_allow_html=True)

    with c2:
        if roll91:
            sizes_str = ", ".join(dict.fromkeys(i['size'] for i in roll91))
            col_n, bw_n, col_m, bw_m = roll_color_summary(roll91)
            color_line = f"🎨 צבעוני: {col_n} דף ({col_m:.1f} מ') · ⬛ שח\"ל: {bw_n} דף ({bw_m:.1f} מ')" if detect_color_opt else ""
            st.markdown(f"""
            <div class="big-result" style="border-left-color:#f4a261;">
                <div class="label"><span class="tag t91">גליל 91 ס"מ</span></div>
                <div class="value">{total91_rounded/100:.1f} מ'</div>
                <div class="sub">
                    {len(roll91)} דפים · גלם: {total91_raw/100:.2f} מ'<br>
                    גדלים: {sizes_str}<br>
                    {color_line}
                </div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="card" style="text-align:center;opacity:.5;padding:2rem">אין דפים לגליל 91 ס"מ</div>', unsafe_allow_html=True)

    with c3:
        if a3_list:
            col_n, bw_n = color_summary(a3_list)
            color_line = f"🎨 {col_n} צבעוני · ⬛ {bw_n} שח\"ל" if detect_color_opt else f"{len(a3_list)} דפים"
            st.markdown(f"""
            <div class="big-result" style="border-left-color:#f72585;">
                <div class="label"><span class="tag tA3">A3 — שטוח</span></div>
                <div class="value">{len(a3_list)}</div>
                <div class="sub">דפים · 29.7 × 42 ס"מ<br>{color_line}</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="card" style="text-align:center;opacity:.5;padding:2rem">אין דפי A3</div>', unsafe_allow_html=True)

    with c4:
        if a4_list:
            col_n, bw_n = color_summary(a4_list)
            color_line = f"🎨 {col_n} צבעוני · ⬛ {bw_n} שח\"ל" if detect_color_opt else f"{len(a4_list)} דפים"
            st.markdown(f"""
            <div class="big-result" style="border-left-color:#7209b7;">
                <div class="label"><span class="tag tA4">A4 — שטוח</span></div>
                <div class="value">{len(a4_list)}</div>
                <div class="sub">דפים · 21 × 29.7 ס"מ<br>{color_line}</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="card" style="text-align:center;opacity:.5;padding:2rem">אין דפי A4</div>', unsafe_allow_html=True)

    # ── טבלת כל הדפים ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="section-label">📋 סיכום כל הדפים</div>', unsafe_allow_html=True)

    all_rows = []
    for item in roll60 + roll91:
        row = {
            'קובץ':           item['name'],
            'גודל':           item['size'],
            'רוחב (ס"מ)':     item['w_cm'],
            'גובה (ס"מ)':     item['h_cm'],
            'גליל':           f"{item['roll']} ס\"מ",
            'אורך על הגליל':  f"{item['length_cm']:.1f} ס\"מ",
            'מעוגל (50 ס"מ)': f"{item['rounded_cm']:.0f} ס\"מ",
            'מסובב':          '✓' if item['rotated'] else '–',
        }
        if detect_color_opt:
            row['צבע'] = '🎨 צבעוני' if item['color'] else '⬛ שח"ל'
        all_rows.append(row)

    for item in a3_list:
        row = {'קובץ': item['name'], 'גודל': 'A3',
               'רוחב (ס"מ)': item['w_cm'], 'גובה (ס"מ)': item['h_cm'],
               'גליל': 'שטוח', 'אורך על הגליל': '–', 'מעוגל (50 ס"מ)': '–', 'מסובב': '–'}
        if detect_color_opt:
            row['צבע'] = '🎨 צבעוני' if item['color'] else '⬛ שח"ל'
        all_rows.append(row)

    for item in a4_list:
        row = {'קובץ': item['name'], 'גודל': 'A4',
               'רוחב (ס"מ)': item['w_cm'], 'גובה (ס"מ)': item['h_cm'],
               'גליל': 'שטוח', 'אורך על הגליל': '–', 'מעוגל (50 ס"מ)': '–', 'מסובב': '–'}
        if detect_color_opt:
            row['צבע'] = '🎨 צבעוני' if item['color'] else '⬛ שח"ל'
        all_rows.append(row)

    if all_rows:
        st.dataframe(pd.DataFrame(all_rows), use_container_width=True, hide_index=True)

    # ── פירוט ────────────────────────────────────────────────────────────────
    with st.expander("📏 פירוט חישוב לפי גליל"):
        if roll60:
            st.markdown("#### גליל 60 ס\"מ")
            for item in roll60:
                c_tag = "🎨" if item['color'] else "⬛"
                st.write(f"• {c_tag} **{item['name']}** ({item['size']}) — {item['length_cm']:.1f} ס\"מ → מעוגל: **{item['rounded_cm']:.0f} ס\"מ**")
            st.success(f"סה\"כ גלם: {total60_raw:.1f} ס\"מ = **{total60_raw/100:.2f} מ'**   |   מעוגל: {total60_rounded:.0f} ס\"מ = **{total60_rounded/100:.1f} מ'**")
        if roll91:
            st.markdown("#### גליל 91 ס\"מ")
            for item in roll91:
                c_tag = "🎨" if item['color'] else "⬛"
                st.write(f"• {c_tag} **{item['name']}** ({item['size']}) — {item['length_cm']:.1f} ס\"מ → מעוגל: **{item['rounded_cm']:.0f} ס\"מ**")
            st.success(f"סה\"כ גלם: {total91_raw:.1f} ס\"מ = **{total91_raw/100:.2f} מ'**   |   מעוגל: {total91_rounded:.0f} ס\"מ = **{total91_rounded/100:.1f} מ'**")

    with st.expander("📖 מפתח גדלים וגלילים"):
        st.markdown("""
| גודל | מידות (ס"מ)    | הצד הקצר | גליל       |
|------|----------------|----------|------------|
| A0   | 84.1 × 118.9   | 84.1 ס"מ | **91 ס"מ** |
| A1   | 59.4 × 84.1    | 59.4 ס"מ | **91 ס"מ** |
| A2   | 42.0 × 59.4    | 42.0 ס"מ | **60 ס"מ** |
| A3   | 29.7 × 42.0    | —        | **שטוח**   |
| A4   | 21.0 × 29.7    | —        | **שטוח**   |

> הגיון המיון: הצד **הקצר** של הדף קובע את הגליל. אם הצד הקצר ≤ 60 ס"מ → גליל 60. אחרת → גליל 91.
        """)

else:
    st.markdown("""
    <div class="card" style="text-align:center; padding:3rem 2rem; opacity:.7">
        <div style="font-size:3rem">📐</div>
        <div style="font-family:'Space Mono',monospace; font-size:.9rem; margin-top:.8rem">
            העלה קבצי PDF כדי לחשב כמה מטרים תצטרך
        </div>
        <div style="font-size:.8rem; margin-top:.5rem; opacity:.6; line-height:2">
            A0, A1 → גליל 91 ס"מ &nbsp;|&nbsp; A2 → גליל 60 ס"מ<br>
            A3, A4 → הדפסה שטוחה (נספרים בנפרד)<br>
            🎨 זיהוי אוטומטי צבעוני / שחור-לבן לכל דף
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center; margin-top:3rem; font-family:'Space Mono',monospace;
     font-size:.75rem; opacity:.5; letter-spacing:.1em">
    העתקות הגולן · מג'דל שמס · קצרין
</div>
""", unsafe_allow_html=True)
