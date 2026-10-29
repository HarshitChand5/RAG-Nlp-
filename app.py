import streamlit as st
import rag

st.set_page_config(page_title="Ask the Book", page_icon="📖", layout="wide")

# ---- theme placeholder: this block will be styled to match the client's reference UI ----
st.markdown("""
<style>
.block-container { padding-top: 2rem; }
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
    st.markdown("**Sources**")
    for s in sources:
        line = f"- **{s['title']}** · Page {s['page']} · {s['chapter']}"
        if s.get("url"):
            line += f" · [Open PDF]({s['url']})"
        st.markdown(line)


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
st.title("📖 Ask the Book")
st.caption("Ask in natural language. Every answer comes with book, page and chapter citations.")

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