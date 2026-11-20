import os
import pymupdf

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    BASE_DIR,
    "documents",
    "KushtetutaeRepublikesseKosoves.pdf"
)

def load_constitution():
    document = pymupdf.open(PDF_PATH)

    pages = []

    for page_number, page in enumerate(document, start=1):
        text = page.get_text("text")

        if text.strip():
            pages.append({
                "page": page_number,
                "content": text
            })

    document.close()
    return pages
