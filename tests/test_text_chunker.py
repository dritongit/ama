
from services.document_loader import load_constitution
from services.text_chunker import chunk_pages


def test_constitution_chunk_structure():
    chunks = chunk_pages(load_constitution())

    constitution = [
        c for c in chunks
        if c["metadata"]["document_section"] == "constitution"
    ]

    amendments = [
        c for c in chunks
        if c["metadata"]["document_section"] == "amendments"
    ]

    assert len(chunks) == 140
    assert len(constitution) == 115
    assert len(amendments) == 25


def test_all_amendments_exist_once():
    chunks = chunk_pages(load_constitution())

    amendments = [
        c for c in chunks
        if c["metadata"]["document_section"] == "amendments"
    ]

    numbers = [
        c["metadata"]["amendment"]
        for c in amendments
    ]

    assert sorted(numbers, key=int) == [
        str(i) for i in range(1, 26)
    ]


def test_amendment_24_contains_article_162():
    chunks = chunk_pages(load_constitution())

    amendment_24 = [
        c for c in chunks
        if c["metadata"]["amendment"] == "24"
    ]

    assert len(amendment_24) == 1
    assert "Neni 162" in amendment_24[0]["text"]
    assert "Dhomat e Specializuara" in amendment_24[0]["text"]


def test_no_empty_chunks():
    chunks = chunk_pages(load_constitution())

    assert all(c["text"].strip() for c in chunks)
