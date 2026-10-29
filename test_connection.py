import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from supabase import create_client

load_dotenv()

gemini_key = os.getenv("GEMINI_API_KEY")
sb_url = os.getenv("SUPABASE_URL")
sb_key = os.getenv("SUPABASE_SERVICE_KEY")

# 0) Check that .env was read
print("GEMINI_API_KEY found:      ", bool(gemini_key))
print("SUPABASE_URL found:        ", bool(sb_url))
print("SUPABASE_SERVICE_KEY found:", bool(sb_key))
if not (gemini_key and sb_url and sb_key):
    raise SystemExit("\nOne or more values are missing. Re-check your .env file.")

# 1) Gemini: embeddings
client = genai.Client(api_key=gemini_key)
try:
    r = client.models.embed_content(
        model="gemini-embedding-001",
        contents="hello world",
        config=types.EmbedContentConfig(output_dimensionality=768),
    )
    print("\n[1] Gemini embeddings OK. Vector length:", len(r.embeddings[0].values))
except Exception as e:
    print("\n[1] Gemini embeddings FAILED:", e)

# 2) Gemini: answer generation
CHAT_MODEL = "gemini-3.8-flash"
try:
    resp = client.models.generate_content(model=CHAT_MODEL, contents="Reply with the single word: ready")
    print(f"[2] Gemini chat OK ({CHAT_MODEL}). Reply:", resp.text.strip())
except Exception as e:
    print(f"[2] Gemini chat FAILED with model {CHAT_MODEL}:", e)
    print("    Available models that support generateContent:")
    try:
        for m in client.models.list():
            if "generateContent" in (m.supported_actions or []):
                print("     -", m.name)
    except Exception as e2:
        print("    Could not list models:", e2)

# 3) Supabase: database
sb = create_client(sb_url, sb_key)
try:
    res = sb.table("chunks").select("id", count="exact").limit(1).execute()
    print("[3] Supabase database OK. Rows in chunks:", res.count)
except Exception as e:
    print("[3] Supabase database FAILED:", e)

# 4) Supabase: storage bucket
try:
    buckets = [b.name for b in sb.storage.list_buckets()]
    print("[4] Supabase storage OK. Buckets:", buckets)
except Exception as e:
    print("[4] Supabase storage FAILED:", e)
