import html
import streamlit as st
import rag

st.set_page_config(page_title="Ask the Book", page_icon="📖", layout="wide")

# ---------------- Dumroo-style theme ----------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
  --blue: #1f4bff;
  --blue-dark: #1238d6;
  --yellow: #ffd45c;
  --ink: #0f1b3d;
  --muted: #5b6685;
}

html, body, [class*="css"], .stApp, .stMarkdown, button, input, textarea {
  font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif !important;
}

.stApp {
  background:
    radial-gradient(900px 380px at 50% -6%, rgba(255, 205, 110, 0.38), transparent 62%),
    radial-gradient(700px 360px at 12% 8%, rgba(120, 150, 255, 0.16), transparent 60%),
    #fbfcff;
  color: var(--ink);
}

header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 0.6rem; max-width: 1100px; }

/* ---------- navbar ---------- */
.nav {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 26px; margin: 0 0 26px 0;
  background: linear-gradient(180deg, rgba(186,194,228,0.85), rgba(212,212,224,0.65));
  border-radius: 0 0 22px 22px;
  box-shadow: 0 8px 24px rgba(40, 60, 140, 0.10);
}
.brand { display: flex; align-items: center; gap: 10px; }
.brand-name { font-size: 1.55rem; font-weight: 800; color: var(--blue); letter-spacing: -0.03em; }
.brand-sub { font-size: 0.62rem; color: var(--muted); margin-top: -4px; letter-spacing: 0.04em; }
.pill {
  background: linear-gradient(180deg, #ffe07a, #f8c42e);
  color: #3a2a00; font-weight: 700; font-size: 0.95rem;
  padding: 9px 22px; border-radius: 999px;
  box-shadow: 0 4px 14px rgba(248, 196, 46, 0.45);
}

/* ---------- hero ---------- */
.hero { text-align: center; padding: 6px 0 4px 0; }
.hero-tag { font-size: 1.05rem; font-weight: 500; color: var(--ink); margin-bottom: 6px; }
.hero-title {
  font-size: clamp(2.4rem, 6.4vw, 4.8rem); font-weight: 800; line-height: 1.04;
  letter-spacing: -0.055em; margin: 0 0 6px 0;
  background: linear-gradient(180deg, #1f4bff 0%, #1238d6 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}

/* ---------- tilted cards ---------- */
.fan { display: flex; justify-content: center; gap: 18px; margin: 26px 0 8px 0; perspective: 900px; }
.fcard {
  width: 255px; padding: 20px 20px 22px 20px; border-radius: 26px;
  background: linear-gradient(160deg, rgba(255,255,255,0.95), rgba(226,234,250,0.85));
  border: 1px solid rgba(110, 130, 220, 0.16);
  box-shadow: 0 18px 40px rgba(40, 60, 140, 0.13);
}
.fcard:nth-child(1) { transform: rotate(-5deg) translateY(14px); }
.fcard:nth-child(2) { transform: translateY(-4px); }
.fcard:nth-child(3) { transform: rotate(5deg) translateY(14px); }
.fcard h4 { margin: 0 0 8px 0; font-size: 1.12rem; font-weight: 800; color: var(--ink); letter-spacing: -0.02em; }
.fcard p { margin: 0; font-size: 0.9rem; color: var(--muted); line-height: 1.45; }
.fcard .chip { margin-top: 14px; font-size: 0.7rem; letter-spacing: 0.12em; color: #9aa6c8; font-weight: 700; }

/* ---------- chat ---------- */
[data-testid="stChatMessage"] {
  background: rgba(255,255,255,0.82); border: 1px solid rgba(110,130,220,0.16);
  border-radius: 20px; padding: 14px 18px; margin-bottom: 12px;
  box-shadow: 0 8px 22px rgba(40,60,140,0.07);
}
[data-testid="stChatInput"] {
  border-radius: 999px; border: 1.5px solid rgba(31,75,255,0.30);
  background: rgba(255,255,255,0.95); box-shadow: 0 10px 28px rgba(31,75,255,0.12);
}
[data-testid="stChatInput"] textarea { font-size: 1rem; }

/* ---------- sources ---------- */
.src-label { font-weight: 800; color: var(--blue); margin: 10px 0 6px 0; letter-spacing: -0.01em; }
.src-wrap { display: flex; flex-wrap: wrap; gap: 10px; }
.src-card {
  background: linear-gradient(160deg, #ffffff, #e9efff);
  border: 1px solid rgba(110,130,220,0.20); border-radius: 16px;
  padding: 10px 14px; min-width: 190px; max-width: 320px;
  box-shadow: 0 6px 16px rgba(40,60,140,0.08);
}
.src-title { font-weight: 700; font-size: 0.86rem; color: var(--ink); }
.src-meta { font-size: 0.8rem; color: var(--muted); margin: 2px 0 4px 0; }
.src-card a { font-size: 0.82rem; font-weight: 700; color: var(--blue); text-decoration: none; }

/* ---------- buttons ---------- */
.stButton > button[kind="primary"], button[data-testid="stBaseButton-primary"] {
  background: linear-gradient(90deg, #1f4bff 0%, #1f4bff 62%, #f6c453 130%);
  color: #fff; border: none; border-radius: 14px; font-weight: 700;
  box-shadow: 0 8px 20px rgba(31,75,255,0.30);
}
.stButton > button[kind="secondary"], button[data-testid="stBaseButton-secondary"] {
  border-radius: 14px; border: 1px solid rgba(110,130,220,0.30); font-weight: 600;
}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(238,242,255,0.95), rgba(251,252,255,0.95));
  border-right: 1px solid rgba(110,130,220,0.16);
}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
  color: var(--blue); font-weight: 800; letter-spacing: -0.02em;
}
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
    cards = []
    for s in sources:
        link = ""
        if s.get("url"):
            link = f'<a href="{html.escape(s["url"])}" target="_blank">Open PDF ↗</a>'
        cards.append(
            f'<div class="src-card"><div class="src-title">{html.escape(s["title"])}</div>'
            f'<div class="src-meta">Page {s["page"]} · {html.escape(str(s["chapter"]))}</div>{link}</div>'
        )
    st.markdown('<div class="src-label">Sources</div><div class="src-wrap">'
                + "".join(cards) + "</div>", unsafe_allow_html=True)


# ---------------- navbar + hero ----------------
n_books = len(docs)
book_text = f"📚 {n_books} book{'s' if n_books != 1 else ''}"
st.markdown(f"""
<div class="nav">
  <div class="brand">
    <svg width="34" height="34" viewBox="0 0 34 34" fill="none">
      <path d="M6 20c0-8 10-10 10-2s10 6 10-3" stroke="#f5a623" stroke-width="3.4" stroke-linecap="round"/>
      <path d="M9 26c4 4 12 4 16-2" stroke="#f5a623" stroke-width="3.4" stroke-linecap="round"/>
    </svg>
    <div><div class="brand-name">Ask the Book</div><div class="brand-sub">AI ANSWERS WITH CITATIONS</div></div>
  </div>
  <div class="pill">{book_text}</div>
</div>
<div class="hero">
  <div class="hero-tag">Revolutionize how you read with AI-powered answers</div>
  <div class="hero-title">Ask Your Books.<br>Get Cited Answers.</div>
</div>
""", unsafe_allow_html=True)

if not st.session_state.messages:
    st.markdown("""
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
st.sidebar.header("📚 Library")

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
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            render_sources(msg["sources"])

prompt = st.chat_input("Ask a question about your books", disabled=not docs)
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching the books..."):
            try:
                text, sources, rows = rag.answer(prompt, selected_id)
            except Exception as e:
                text, sources, rows = f"Something went wrong: {e}", [], []
        st.markdown(text)
        if sources:
            render_sources(sources)
        if rows:
            with st.expander("Show retrieved passages"):
                for r in rows:
                    st.caption(f"Page {r['page_number']} · {r['chapter']} · "
                               f"similarity {r['similarity']:.2f}")
                    st.write(r["content"])

    st.session_state.messages.append(
        {"role": "assistant", "content": text, "sources": sources})