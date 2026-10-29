import pymupdf

doc = pymupdf.open("book.pdf")
print("Total pages:", len(doc))

# Table of contents / bookmarks (useful for chapter names)
toc = doc.get_toc()
print("\nBookmarks found:", len(toc))
for level, title, page in toc[:40]:
    print(f"  level {level} | PDF page {page} | {title}")

# Sample some pages
for idx in [0, 5, 15, 40, 100, 200]:
    if idx < len(doc):
        page = doc[idx]
        text = page.get_text().strip()
        print(f"\n===== PDF page {idx + 1} (label: {page.get_label()!r}) =====")
        print(text[:400] if text else "[NO TEXT ON THIS PAGE]")