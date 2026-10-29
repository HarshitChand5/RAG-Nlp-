import os
import re
import time
from pathlib import Path

import pymupdf
from dotenv import load_dotenv
from google import genai
from google.genai import types
from supabase import create_client

load_dotenv(Path(__file__).parent / ".env")

# ---------------- CONFIG ----------------
BUCKET = os.getenv("SUPABASE_BUCKET", "Book")
EMBED_MODEL = "gemini-embedding-001"
DIM = 768
CHAT_MODELS = [m for m in [os.getenv("CHAT_MODEL"), "gemini-3.5-flash-lite",
                           "gemini-3.1-flash-lite", "gemini-3.5-flash"] if m]
# ----------------------------------------

gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"),
                      http_options=types.HttpOptions(timeout=60000))
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

SYSTEM_PROMPT = """You are a helpful assistant that answers questions about books.
Rules:
1. Use ONLY the provided context excerpts. Do not use outside knowledge.
2. Write the answer in clear, natural language.
3. After each claim, cite its source as (Book title, Page X, Chapter Y), using the
   labels given in the context.
4. If the context does not contain the answer, reply exactly:
   "This is not covered in the uploaded books."
5. Answer in the same language as the question."""


# ---------------- helpers ----------------
def safe_name(name):
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return base or "document.pdf"


def title_from_name(name):
    stem = Path(name).stem.replace("_", " ")
    return re.sub(r"\s*\(\d+\)$", "", stem).strip() or "Untitled"


def split_text(text, size=1500, overlap=200):
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    pieces, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            cut = max(text.rfind("\n", start, end), text.rfind(". ", start, end))
            if cut > start + size // 2:
                end = cut + 1
        piece = text[start:end].strip()
        if len(piece) > 30:
            pieces.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return pieces


def _embed(texts, task):
    for attempt in range(5):
        try:
            r = gemini.models.embed_content(
                model=EMBED_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(task_type=task,
                                                output_dimensionality=DIM),
            )
            return [e.values for e in r.embeddings]
        except Exception:
            if attempt == 4:
                raise
            time.sleep(5 * (attempt + 1))


def embed_documents(texts):
    try:
        vecs = _embed(texts, "RETRIEVAL_DOCUMENT")
        if len(vecs) == len(texts):
            return vecs
    except Exception:
        pass
    return [_embed([t], "RETRIEVAL_DOCUMENT")[0] for t in texts]


# ---------------- library ----------------
def list_documents():
    return (sb.table("documents")
            .select("id,title,file_path,page_count,created_at")
            .order("created_at", desc=True).execute().data)


def bucket_pdfs():
    items = sb.storage.from_(BUCKET).list()
    return [i["name"] for i in items
            if i.get("name", "").lower().endswith(".pdf")]


def unprocessed_files():
    done = {d["file_path"] for d in list_documents()}
    return [n for n in bucket_pdfs() if n not in done]


def extract_pages(pdf_bytes, fallback_title):
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    toc = [(p, t.strip()) for lvl, t, p in doc.get_toc()
           if lvl <= 2 and t.strip()]
    toc.sort(key=lambda x: x[0])

    def chapter_for(pdf_page):
        name = fallback_title
        for p, t in toc:
            if p <= pdf_page:
                name = t
            else:
                break
        return name[:120]

    pages = []
    for i, page in enumerate(doc):
        pdf_page = i + 1
        try:
            label = (page.get_label() or "").strip()
        except Exception:
            label = ""
        printed = int(label) if label.isdigit() else pdf_page
        pages.append({
            "pdf_page": pdf_page,
            "page_number": printed,
            "chapter": chapter_for(pdf_page),
            "text": page.get_text().strip(),
        })
    return pages, len(doc)


def ingest_pdf(pdf_bytes, storage_path, title, progress=None):
    def report(frac, msg):
        if progress:
            progress(min(max(frac, 0.0), 1.0), msg)

    report(0.02, "Reading PDF...")
    pages, n_pages = extract_pages(pdf_bytes, title)
    if sum(len(p["text"]) for p in pages) < 500:
        raise ValueError("This PDF has almost no selectable text "
                         "(it is probably scanned). It needs OCR first.")

    chunks = []
    for p in pages:
        for piece in split_text(p["text"]):
            chunks.append({
                "content": piece,
                "page_number": p["page_number"],
                "pdf_page": p["pdf_page"],
                "chapter": p["chapter"],
            })
    if not chunks:
        raise ValueError("No text could be extracted from this PDF.")

    doc_id = (sb.table("documents")
              .insert({"title": title, "file_path": storage_path,
                       "page_count": n_pages})
              .execute().data[0]["id"])
    try:
        BATCH = 20
        for i in range(0, len(chunks), BATCH):
            batch = chunks[i:i + BATCH]
            vecs = embed_documents([c["content"] for c in batch])
            rows = [{**c, "document_id": doc_id, "embedding": v}
                    for c, v in zip(batch, vecs)]
            sb.table("chunks").insert(rows).execute()
            done = min(i + BATCH, len(chunks))
            report(0.1 + 0.9 * done / len(chunks),
                   f"Embedding and saving {done}/{len(chunks)} chunks")
            time.sleep(0.5)
    except Exception:
        sb.table("documents").delete().eq("id", doc_id).execute()  # clean up
        raise
    return doc_id, len(chunks), n_pages


def upload_new_pdf(file_name, pdf_bytes, progress=None):
    path = safe_name(file_name)
    if any(d["file_path"] == path for d in list_documents()):
        raise ValueError(f"'{file_name}' is already uploaded.")
    sb.storage.from_(BUCKET).upload(
        path=path, file=pdf_bytes,
        file_options={"content-type": "application/pdf", "upsert": "true"},
    )
    return ingest_pdf(pdf_bytes, path, title_from_name(file_name), progress)


def process_bucket_file(name, progress=None):
    data = sb.storage.from_(BUCKET).download(name)
    return ingest_pdf(data, name, title_from_name(name), progress)


def delete_document(doc_id, file_path):
    sb.table("documents").delete().eq("id", doc_id).execute()  # chunks cascade
    try:
        sb.storage.from_(BUCKET).remove([file_path])
    except Exception:
        pass


# ---------------- question answering ----------------
def pdf_link(file_path, pdf_page):
    try:
        res = sb.storage.from_(BUCKET).create_signed_url(file_path, 3600)
        url = res.get("signedURL") or res.get("signedUrl") or ""
        if not url:
            return None
        if url.startswith("/"):
            if not url.startswith("/storage"):
                url = "/storage/v1" + url
            url = os.getenv("SUPABASE_URL").rstrip("/") + url
        return f"{url}#page={pdf_page}"
    except Exception:
        return None


def retrieve(question, k=8, document_id=None):
    qv = _embed([question], "RETRIEVAL_QUERY")[0]
    params = {"query_embedding": qv, "match_count": k}
    if document_id:
        params["filter_document"] = document_id
    return sb.rpc("match_chunks", params).execute().data


def answer(question, document_id=None):
    rows = retrieve(question, 8, document_id)
    if not rows:
        return "No books have been uploaded yet.", [], []

    docs = {d["id"]: d for d in list_documents()}
    parts = []
    for r in rows:
        title = docs.get(r["document_id"], {}).get("title", "Unknown")
        parts.append(f"[Source: {title}, Page {r['page_number']}, "
                     f"{r['chapter']}]\n{r['content']}")
    context = "\n\n---\n\n".join(parts)

    text, last_err = None, None
    for model in CHAT_MODELS:
        try:
            resp = gemini.models.generate_content(
                model=model,
                contents=f"Context:\n{context}\n\nQuestion: {question}",
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT, temperature=0.2),
            )
            text = resp.text
            break
        except Exception as e:
            last_err = e
    if text is None:
        if last_err:
            raise last_err
        text = "The model returned no answer. Please try rephrasing."

    seen, sources = set(), []
    for r in rows:
        key = (r["document_id"], r["page_number"])
        if key in seen:
            continue
        seen.add(key)
        d = docs.get(r["document_id"], {})
        sources.append({
            "title": d.get("title", "Unknown"),
            "page": r["page_number"],
            "chapter": r["chapter"],
            "url": pdf_link(d.get("file_path", ""), r["pdf_page"])
                   if d.get("file_path") else None,
        })
    sources.sort(key=lambda s: (s["title"], s["page"]))
    return text, sources, rows
