import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

try:
    sb.table("documents").select("id").limit(1).execute()
    print("documents table: OK")
except Exception as e:
    print("documents table: MISSING ->", e)

try:
    sb.table("chunks").select("document_id,pdf_page").limit(1).execute()
    print("chunks table (new version): OK")
except Exception as e:
    print("chunks table: OLD VERSION ->", e)