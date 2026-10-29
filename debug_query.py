import rag

print("=== 1) Documents in database ===")
docs = rag.list_documents()
for d in docs:
    print(" -", d["title"], "| pages:", d["page_count"], "| id:", d["id"][:8])
if not docs:
    raise SystemExit("No documents found. Process a file in the app first.")

print("\n=== 2) Chunk count ===")
res = rag.sb.table("chunks").select("id", count="exact").limit(1).execute()
print("Total chunks:", res.count)
if not res.count:
    raise SystemExit("0 chunks saved. Processing did not store any text.")

print("\n=== 3) Sample chunk ===")
s = rag.sb.table("chunks").select("page_number,chapter,content").limit(1).execute().data[0]
print("Page:", s["page_number"], "| Chapter:", s["chapter"])
print(s["content"][:200])

QUESTION = "What is RAG?"

print("\n=== 4) Embed the question ===")
try:
    v = rag._embed([QUESTION], "RETRIEVAL_QUERY")[0]
    print("OK, vector length:", len(v))
except Exception as e:
    raise SystemExit(f"FAILED at embedding: {e}")

print("\n=== 5) Search in Supabase (match_chunks) ===")
try:
    rows = rag.sb.rpc("match_chunks", {"query_embedding": v, "match_count": 5}).execute().data
    print("Rows returned:", len(rows))
    for r in rows:
        print(f"  page {r['page_number']} | similarity {r['similarity']:.3f}")
except Exception as e:
    raise SystemExit(f"FAILED at search: {e}")

print("\n=== 6) Gemini answer ===")
for m in rag.CHAT_MODELS:
    try:
        resp = rag.gemini.models.generate_content(model=m, contents="Reply with one word: ready")
        print(f"  {m}: OK ->", resp.text)
    except Exception as e:
        print(f"  {m}: FAILED -> {str(e)[:200]}")

print("\n=== 7) Full answer() call ===")
try:
    text, sources, _ = rag.answer(QUESTION)
    print("ANSWER:", text)
    print("SOURCES:", len(sources))
except Exception as e:
    print(f"FAILED in answer(): {e}")