
import re


ARTICLE_PATTERN = re.compile(
    r"^\s*NENI\s+(\d+)\s*\*{0,2}\s*$",
    re.IGNORECASE
)

def normalize_amendment(value):
    if value.isdigit():
        return str(int(value))

    roman_values = {
        "I": 1,
        "V": 5,
        "X": 10,
        "L": 50,
        "C": 100,
        "D": 500,
        "M": 1000
    }

    total = 0
    previous = 0

    for char in reversed(value.upper()):
        current = roman_values[char]

        if current < previous:
            total -= current
        else:
            total += current

        previous = current

    return str(total)

TITLE_PATTERN = re.compile(r"^\s*\[.+\]\s*$")

AMENDMENT_PATTERN = re.compile(
    r"^\s*Amendamenti\s+(?:nr\.\s*)?([IVXLCDM]+|\d+)\s*:?\s*$",
    re.IGNORECASE
)

ANNEX_PATTERN = re.compile(
    r"^\s*Aneks\s*:",
    re.IGNORECASE
)


def chunk_pages(pages):
    chunks = []

    current_article = None
    current_text = []
    current_chapter = None
    current_amendment = None
    document_section = "constitution"

    start_page = None
    end_page = None

    def save_chunk():
        nonlocal current_article, current_text

        if current_text:
            content = "\n".join(current_text).strip()

            if content:
                chunks.append({
                    "text": content,
                    "metadata": {
                        "article": current_article,
                        "amendment": current_amendment,
                        "document_section": document_section,
                        "chapter": current_chapter,
                        "page_start": start_page,
                        "page_end": end_page,
                        "source": "Kushtetuta e Republikës së Kosovës"
                    }
                })

        current_article = None
        current_text = []

    for page in pages:
        lines = page["content"].splitlines()
        page_number = page["page"]

        i = 0

        while i < len(lines):
            line = lines[i].strip()

            if not line:
                i += 1
                continue

            if re.match(
                r"^Kapitulli\s+[IVXLCDM]+$",
                line,
                re.IGNORECASE
            ):
                current_chapter = line

            if ANNEX_PATTERN.match(line):
                save_chunk()
                document_section = "amendments"
                current_amendment = None
                i += 1
                continue

            amendment_match = AMENDMENT_PATTERN.match(line)

            if amendment_match and document_section == "amendments":
                amendment_number = normalize_amendment(
                    amendment_match.group(1)
                )

                # Same amendment written in Roman and Arabic numbers
                if current_text and current_amendment == amendment_number:
                    current_text.append(line)
                    end_page = page_number
                    i += 1
                    continue

                save_chunk()

                current_amendment = amendment_number

                start_page = page_number
                end_page = page_number

                current_text = [line]
                i += 1
                continue

            article_match = ARTICLE_PATTERN.match(line)

            # Articles introduced inside amendments belong
            # to the current amendment, not separate chunks.
            if article_match and document_section == "amendments":
                if current_text:
                    current_text.append(line)
                    end_page = page_number

                i += 1
                continue

            if article_match:
                next_line = (
                    lines[i + 1].strip()
                    if i + 1 < len(lines)
                    else ""
                )

                if TITLE_PATTERN.match(next_line):
                    save_chunk()

                    current_article = f"Neni {article_match.group(1)}"

                    start_page = page_number
                    end_page = page_number

                    current_text = [line, next_line]

                    i += 2
                    continue

            if current_text:
                current_text.append(line)
                end_page = page_number

            i += 1

    save_chunk()

    return chunks
