
import re

ARTICLE_PATTERN = re.compile(
    r"^\s*NENI\s+(\d+)\s*$",
    re.IGNORECASE
)

TITLE_PATTERN = re.compile(
    r"^\s*\[.+\]\s*$"
)


def chunk_pages(pages):
    chunks = []

    current_article = None
    current_text = []
    start_page = None
    end_page = None
    current_chapter = None

    def save_chunk():
        if current_article and current_text:
            content = "\n".join(current_text).strip()

            if content:
                chunks.append({
                    "text": content,
                    "metadata": {
                        "article": current_article,
                        "chapter": current_chapter,
                        "page_start": start_page,
                        "page_end": end_page,
                        "source": "Kushtetuta e Republikës së Kosovës"
                    }
                })

    for page in pages:
        lines = page["content"].splitlines()
        page_number = page["page"]

        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Kapitujt
            if re.match(r"^Kapitulli\s+[IVXLCDM]+$", line, re.I):
                current_chapter = line

            # Kontrollo nëse është fillimi i një neni real
            match = ARTICLE_PATTERN.match(line)

            if match:
                next_line = (
                    lines[i + 1].strip()
                    if i + 1 < len(lines)
                    else ""
                )

                if TITLE_PATTERN.match(next_line):
                    save_chunk()

                    current_article = f"Neni {match.group(1)}"
                    current_text = [line, next_line]

                    start_page = page_number
                    end_page = page_number

                    i += 2
                    continue

            if current_article and line:
                current_text.append(line)
                end_page = page_number

            i += 1

    save_chunk()

    return chunks
