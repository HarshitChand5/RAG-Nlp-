import html
import re
import streamlit as st
import rag

st.set_page_config(page_title="Ask the Book", page_icon=":material/menu_book:", layout="wide")

MAX_SOURCES = 5  # max citations shown under an answer

AVATARS = {"user": ":material/person:", "assistant": ":material/auto_stories:"}

# ---------------- text cleanup helpers ----------------
EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF"
    "\U0001F1E6-\U0001F1FF\uFE0F\u200d]+"
)
# "(Book Title, Page 3, PART 2: ...)"  ->  "[p.3]"
CITE_RE = re.compile(r"\s*\((?:[^()]*?),\s*Page\s+(\d+)(?:,[^()]*)?\)", re.IGNORECASE)
DUP_CITE_RE = re.compile(r"(\[p\.\d+\])(?:\s*\1)+")


def strip_emoji(text):
    text = EMOJI_RE.sub("", str(text))
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def clean_answer(text):
    text = strip_emoji(text)
    text = CITE_RE.sub(lambda m: f" [p.{m.group(1)}]", text)
    text = DUP_CITE_RE.sub(r"\1", text)
    return text


# ---------------- theme ----------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
  --blue: #1f4bff;
  --blue-dark: #1238d6;
  --yellow: #ffd45c;
  --ink: #0f1b3d;
  --muted: #5b6685;
  --line: rgba(110,130,220,0.22);
  --page: #fbfcff;
  color-scheme: light;
}

html, body, [class*="css"], .stApp, .stMarkdown, button, input, textarea {
  font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif !important;
}

.stApp {
  background:
    radial-gradient(900px 380px at 50% -6%, rgba(255, 205, 110, 0.38), transparent 62%),
    radial-gradient(700px 360px at 12% 8%, rgba(120, 150, 255, 0.16), transparent 60%),
    var(--page);
  color: var(--ink);
}
.stApp p, .stApp li, .stApp label, .stApp span, .stApp h1, .stApp h2, .stApp h3, .stApp h4 { color: var(--ink); }

header[data-testid="stHeader"] { background: transparent; }
.stDeployButton, [data-testid="stAppDeployButton"], [data-testid="stDecoration"],
[data-testid="stMainMenu"], #MainMenu { display: none !important; }
footer { visibility: hidden; }

/* sidebar open/close buttons must stay visible */
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] { display: flex !important; visibility: visible !important; opacity: 1 !important; }
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="collapsedControl"] button {
  background: #fff !important; border: 1px solid var(--line) !important;
  border-radius: 12px !important; box-shadow: 0 4px 12px rgba(40,60,140,0.12);
}
[data-testid="stExpandSidebarButton"] *, [data-testid="stSidebarCollapsedControl"] *,
[data-testid="collapsedControl"] *, [data-testid="stSidebarCollapseButton"] * {
  color: var(--blue) !important; fill: var(--blue) !important;
}

.block-container { padding-top: 0.6rem; padding-bottom: 8rem; max-width: 1100px; }

/* ---------- navbar ---------- */
.nav {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 26px; margin: 0 0 26px 0;
  background: linear-gradient(180deg, rgba(186,194,228,0.85), rgba(212,212,224,0.65));
  border-radius: 0 0 22px 22px;
  box-shadow: 0 8px 24px rgba(40, 60, 140, 0.10);
}
.brand { display: flex; align-items: center; gap: 10px; }
.brand-name { font-size: 1.55rem; font-weight: 800; color: var(--blue) !important; letter-spacing: -0.03em; }
.brand-sub { font-size: 0.62rem; color: var(--muted) !important; margin-top: -4px; letter-spacing: 0.04em; }
.pill {
  display: flex; align-items: center; gap: 8px;
  background: linear-gradient(180deg, #ffe07a, #f8c42e);
  color: #3a2a00 !important; font-weight: 700; font-size: 0.95rem;
  padding: 9px 20px; border-radius: 999px;
  box-shadow: 0 4px 14px rgba(248, 196, 46, 0.45);
}
.pill svg { stroke: #3a2a00; }

/* ---------- hero ---------- */
.hero { text-align: center; padding: 6px 0 4px 0; }
.hero-tag { font-size: 1.05rem; font-weight: 500; color: var(--ink); margin-bottom: 6px; }
.hero-title {
  font-size: clamp(2.2rem, 5.6vw, 4.2rem); font-weight: 800; line-height: 1.08;
  letter-spacing: -0.04em; margin: 0 0 6px 0;
  background: linear-gradient(180deg, #1f4bff 0%, #1238d6 100%);
  -webkit-background-clip: text; background-clip: text;
  color: transparent !important; -webkit-text-fill-color: transparent;
}

/* ---------- feature cards ---------- */
.fan { display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; margin: 30px 0 8px 0; }
.fcard {
  width: 255px; padding: 20px 20px 22px 20px; border-radius: 26px;
  background: linear-gradient(160deg, rgba(255,255,255,0.97), rgba(226,234,250,0.85));
  border: 1px solid var(--line);
  box-shadow: 0 18px 40px rgba(40, 60, 140, 0.12);
  transition: transform .2s ease, box-shadow .2s ease;
}
.fcard:nth-child(1) { transform: rotate(-2deg) translateY(8px); }
.fcard:nth-child(2) { transform: translateY(-2px); }
.fcard:nth-child(3) { transform: rotate(2deg) translateY(8px); }
.fcard:hover { transform: translateY(-6px) rotate(0deg); box-shadow: 0 24px 48px rgba(40,60,140,0.18); }
.fcard h4 { margin: 0 0 8px 0; font-size: 1.1rem; font-weight: 800; color: var(--ink); letter-spacing: -0.02em; }
.fcard p { margin: 0; font-size: 0.9rem; color: var(--muted) !important; line-height: 1.45; }
.fcard .chip { margin-top: 14px; font-size: 0.7rem; letter-spacing: 0.12em; color: #8794bb; font-weight: 700; }

/* ---------- chat ---------- */
[data-testid="stChatMessage"] {
  background: rgba(255,255,255,0.90); border: 1px solid var(--line);
  border-radius: 20px; padding: 14px 18px; margin-bottom: 12px;
  box-shadow: 0 8px 22px rgba(40,60,140,0.07);
}
[data-testid="stChatMessage"] * { color: var(--ink); }
[data-testid="stChatMessageAvatarUser"], [data-testid="stChatMessageAvatarAssistant"] {
  background: var(--blue) !important; border-radius: 12px;
}
[data-testid="stChatMessageAvatarUser"] { background: #5b6685 !important; }
[data-testid="stChatMessageAvatarUser"] *, [data-testid="stChatMessageAvatarAssistant"] * {
  color: #fff !important; fill: #fff !important;
}

/* ---------- bottom chat bar ---------- */
[data-testid="stBottom"], [data-testid="stBottom"] > div, [data-testid="stBottomBlockContainer"] {
  background: transparent !important;
}
[data-testid="stBottom"] {
  background: linear-gradient(to top, var(--page) 72%, rgba(251,252,255,0)) !important;
  padding-top: 18px;
}
[data-testid="stChatInput"] {
  background: #fff !important;
  border: 1.5px solid rgba(31,75,255,0.30) !important;
  border-radius: 999px !important;
  box-shadow: 0 10px 28px rgba(31,75,255,0.12);
}
[data-testid="stChatInput"] > div, [data-testid="stChatInput"] textarea {
  background: #fff !important; color: var(--ink) !important; font-size: 1rem; border-radius: 999px;
}
[data-testid="stChatInput"] textarea::placeholder { color: var(--muted) !important; opacity: 1; }
[data-testid="stChatInput"] button { background: var(--blue) !important; border-radius: 999px; }
[data-testid="stChatInput"] button svg { fill: #fff !important; color: #fff !important; }

/* ---------- sources ---------- */
.src-label { font-weight: 800; color: var(--blue) !important; margin: 12px 0 8px 0; letter-spacing: -0.01em; }
.src-card {
  background: linear-gradient(160deg, #ffffff, #eef2ff);
  border: 1px solid var(--line); border-radius: 16px;
  padding: 12px 14px; margin-bottom: 10px;
  box-shadow: 0 6px 16px rgba(40,60,140,0.08);
}
.src-title { font-weight: 700; font-size: 0.9rem; color: var(--ink) !important; margin-bottom: 8px; }
.src-rows { display: flex; flex-wrap: wrap; gap: 8px; }
.src-row {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 6px 12px; border-radius: 999px; text-decoration: none !important;
  background: #fff; border: 1px solid var(--line);
  font-size: 0.8rem; transition: border-color .15s ease, background .15s ease;
}
a.src-row:hover { border-color: var(--blue); background: #f3f6ff; }
.src-row .pg { font-weight: 800; color: var(--blue) !important; }
.src-row .ch { color: var(--muted) !important; }
.src-row .go { color: var(--blue) !important; font-weight: 700; }

/* ---------- buttons ---------- */
.stButton > button[kind="primary"], button[data-testid="stBaseButton-primary"] {
  background: linear-gradient(90deg, #1f4bff 0%, #1f4bff 62%, #f6c453 130%) !important;
  color: #fff !important; border: none !important; border-radius: 14px; font-weight: 700;
  box-shadow: 0 8px 20px rgba(31,75,255,0.30);
}
.stButton > button[kind="primary"] * { color: #fff !important; }
.stButton > button[kind="secondary"], button[data-testid="stBaseButton-secondary"] {
  background: #fff !important; color: var(--ink) !important;
  border: 1px solid var(--line) !important; border-radius: 14px; font-weight: 600;
}
.stButton > button[kind="secondary"] *, button[data-testid="stBaseButton-secondary"] * { color: var(--ink) !important; }
.stButton > button[kind="secondary"]:hover { border-color: var(--blue) !important; }
.stButton > button[kind="secondary"]:hover * { color: var(--blue) !important; }
.stButton > button:disabled { opacity: 0.5; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #eef2ff, #fbfcff);
  border-right: 1px solid var(--line);
}
[data-testid="stSidebarHeader"] { min-height: 0; height: 2.6rem; padding-bottom: 0; }
[data-testid="stSidebarUserContent"] { padding-top: 0.4rem; }
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
  color: var(--blue) !important; font-weight: 800; letter-spacing: -0.02em;
}
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p,
[data-testid="stWidgetLabel"] p { color: var(--ink) !important; font-weight: 600; }

/* ---------- file uploader ---------- */
[data-testid="stFileUploaderDropzone"] {
  background: #fff !important; border: 1.5px dashed rgba(31,75,255,0.40) !important; border-radius: 16px;
}
[data-testid="stFileUploaderDropzone"] * { color: var(--muted) !important; }
[data-testid="stFileUploaderDropzone"] button {
  background: #fff !important; color: var(--blue) !important;
  border: 1px solid rgba(31,75,255,0.40) !important; border-radius: 12px; font-weight: 700;
}
[data-testid="stFileUploaderDropzone"] button * { color: var(--blue) !important; }
[data-testid="stFileUploaderFile"] * { color: var(--ink) !important; }

/* ---------- selectbox ---------- */
[data-baseweb="select"] > div { background: #fff !important; border: 1px solid var(--line) !important; border-radius: 12px !important; }
[data-baseweb="select"] * { color: var(--ink) !important; }
[data-baseweb="select"] svg { fill: var(--ink) !important; }
[data-baseweb="popover"], [data-baseweb="popover"] ul, [data-baseweb="menu"] { background: #fff !important; }
[data-baseweb="popover"] li, [data-baseweb="popover"] li * { color: var(--ink) !important; background: #fff; }
[data-baseweb="popover"] li:hover, [data-baseweb="popover"] li[aria-selected="true"] { background: #eef2ff !important; }

/* ---------- expander ---------- */
[data-testid="stExpander"] { background: rgba(255,255,255,0.85); border: 1px solid var(--line) !important; border-radius: 14px; }
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary * { color: var(--ink) !important; font-weight: 600; }
[data-testid="stExpander"] details { background: transparent; }

/* ---------- misc ---------- */
[data-testid="stCheckbox"] label * { color: var(--ink) !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * { color: var(--muted) !important; }
[data-testid="stAlert"] * { color: var(--ink) !important; }
</style>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "flash" not in st.session_state:
    st.session_state.flash = []

try:
    docs = rag.list_documents()
    pending = rag.unprocessed_files()
except Exception as e:
    st.error(f"Could not connect to Supabase: {e}")
    st.stop()


def render_sources(sources):
    """One card per book, with a chip per cited page."""
    # keep only the top MAX_SOURCES unique pages (sources arrive in relevance order)
    top, seen_pages = [], set()
    for s in sources:
        key = (s["title"], s["page"])
        if key in seen_pages:
            continue
        seen_pages.add(key)
        top.append(s)
        if len(top) == MAX_SOURCES:
            break

    groups = {}
    for s in top:
        groups.setdefault(s["title"], []).append(s)

    cards = []
    for title, items in groups.items():
        seen, rows = set(), []
        for s in sorted(items, key=lambda x: int(x["page"])):
            key = (s["page"], s.get("url"))
            if key in seen:
                continue
            seen.add(key)
            chapter = html.escape(strip_emoji(s["chapter"]))
            inner = (f'<span class="pg">Page {s["page"]}</span>'
                     f'<span class="ch">{chapter}</span>')
            url = s.get("url")
            if url:
                href = url if "#" in url else f'{url}#page={s["page"]}'
                rows.append(f'<a class="src-row" href="{html.escape(href)}" target="_blank">'
                            f'{inner}<span class="go">↗</span></a>')
            else:
                rows.append(f'<span class="src-row">{inner}</span>')
        cards.append(f'<div class="src-card"><div class="src-title">{html.escape(strip_emoji(title))}</div>'
                     f'<div class="src-rows">{"".join(rows)}</div></div>')
    st.markdown('<div class="src-label">Sources</div>' + "".join(cards), unsafe_allow_html=True)


# ---------------- navbar + hero ----------------
n_books = len(docs)
book_text = f"{n_books} book{'s' if n_books != 1 else ''}"
st.markdown(f"""
<div class="nav">
  <div class="brand">
    <svg width="38" height="38" viewBox="0 0 38 38" fill="none">
      <rect width="38" height="38" rx="11" fill="#1f4bff"/>
      <path d="M19 12.5c-2.4-1.7-5.4-2.2-8.5-1.7v14.2c3.1-.5 6.1 0 8.5 1.7 2.4-1.7 5.4-2.2 8.5-1.7V10.8c-3.1-.5-6.1 0-8.5 1.7z"
            stroke="#fff" stroke-width="2" stroke-linejoin="round" fill="none"/>
      <path d="M19 12.5v14.2" stroke="#ffd45c" stroke-width="2" stroke-linecap="round"/>
    </svg>
    <div><div class="brand-name">Ask the Book</div><div class="brand-sub">AI ANSWERS WITH CITATIONS</div></div>
  </div>
  <div class="pill">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
    </svg>{book_text}
  </div>
</div>
<div class="hero">
  <div class="hero-tag">Revolutionize how you read with AI-powered answers</div>
  <div class="hero-title">Ask Your Books.<br>Get Cited Answers.</div>
</div>
""", unsafe_allow_html=True)

# placeholder so the cards disappear as soon as the first question is asked
intro_slot = st.empty()
if not st.session_state.messages:
    intro_slot.markdown("""
    <div class="fan">
      <div class="fcard"><h4>Natural-Language Answers</h4>
        <p>Ask in plain words and get a clear, grounded answer written from your own books.</p>
        <div class="chip">ANSWERS AI</div></div>
      <div class="fcard"><h4>Page-Level Citations</h4>
        <p>Every answer shows the book, page number and chapter it was taken from.</p>
        <div class="chip">CITATIONS</div></div>
      <div class="fcard"><h4>Open the Source PDF</h4>
        <p>Jump straight to the exact page in the original PDF stored in Supabase.</p>
        <div class="chip">SOURCE</div></div>
    </div>
    """, unsafe_allow_html=True)

# ---------------- sidebar ----------------
st.sidebar.header("Library")

for kind, msg in st.session_state.flash:
    (st.sidebar.success if kind == "ok" else st.sidebar.error)(msg)
st.session_state.flash = []

uploaded = st.sidebar.file_uploader("Upload PDF(s)", type=["pdf"],
                                    accept_multiple_files=True)
if st.sidebar.button("Upload & process", type="primary", disabled=not uploaded):
    for f in uploaded:
        bar = st.sidebar.progress(0.0, text=f.name)
        try:
            _, n_chunks, n_pages = rag.upload_new_pdf(
                f.name, f.getvalue(),
                progress=lambda frac, msg, bar=bar: bar.progress(frac, text=msg))
            st.session_state.flash.append(
                ("ok", f"{f.name}: {n_pages} pages, {n_chunks} chunks saved."))
        except Exception as e:
            st.session_state.flash.append(("err", f"{f.name}: {e}"))
    st.rerun()

if pending:
    st.sidebar.warning(f"{len(pending)} file(s) already in Supabase are not processed yet:")
    for n in pending:
        st.sidebar.caption(n)
    if st.sidebar.button("Process these files"):
        for n in pending:
            bar = st.sidebar.progress(0.0, text=n)
            try:
                _, n_chunks, n_pages = rag.process_bucket_file(
                    n,
                    progress=lambda frac, msg, bar=bar: bar.progress(frac, text=msg))
                st.session_state.flash.append(
                    ("ok", f"{n}: {n_pages} pages, {n_chunks} chunks saved."))
            except Exception as e:
                st.session_state.flash.append(("err", f"{n}: {e}"))
        st.rerun()

options = {"All books": None}
for d in docs:
    label = d["title"] if d["title"] not in options else f"{d['title']} ({d['id'][:4]})"
    options[label] = d["id"]
choice = st.sidebar.selectbox("Search in", list(options.keys()))
selected_id = options[choice]

with st.sidebar.expander("Delete a book"):
    if docs:
        target = st.selectbox("Book", docs, format_func=lambda d: d["title"], key="del_book")
        confirm = st.checkbox("Yes, delete it permanently")
        if st.button("Delete", disabled=not confirm):
            rag.delete_document(target["id"], target["file_path"])
            st.session_state.flash.append(("ok", f"Deleted: {target['title']}"))
            st.rerun()
    else:
        st.caption("No books yet.")

if st.sidebar.button("Clear chat"):
    st.session_state.messages = []
    st.rerun()

# ---------------- main chat ----------------
if not docs:
    st.info("Upload a PDF from the sidebar to get started.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar=AVATARS[msg["role"]]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            render_sources(msg["sources"])

prompt = st.chat_input("Ask a question about your books", disabled=not docs)
if prompt:
    intro_slot.empty()
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=AVATARS["user"]):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar=AVATARS["assistant"]):
        with st.spinner("Searching the books..."):
            try:
                text, sources, rows = rag.answer(prompt, selected_id)
                text = clean_answer(text)
            except Exception as e:
                text, sources, rows = f"Something went wrong: {e}", [], []
        st.markdown(text)
        if sources:
            render_sources(sources)
        if rows:
            with st.expander("Show retrieved passages"):
                for r in rows:
                    st.caption(f"Page {r['page_number']} · {strip_emoji(r['chapter'])} · "
                               f"similarity {r['similarity']:.2f}")
                    st.write(strip_emoji(r["content"]))

    st.session_state.messages.append(
        {"role": "assistant", "content": text, "sources": sources})