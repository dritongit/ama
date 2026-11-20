import re
from services.embeddings import embed_query
from services.vector_store import get_client, COLLECTION_NAME

# Regex për me kap referencat
NENI_PATTERN = re.compile(r'neni\s+(\d+)', re.IGNORECASE)
AMENDAMENTI_PATTERN = re.compile(r'amendament\w*\s+(\d+)', re.IGNORECASE)

def parse_reference(query: str):
    """Kthen ('neni', 162) ose ('amendament', 24) ose None"""
    m = AMENDAMENTI_PATTERN.search(query)
    if m:
        return ("amendament", int(m.group(1)))
    
    m = NENI_PATTERN.search(query)
    if m:
        return ("neni", int(m.group(1)))
    
    return None

def get_by_reference(ref_type: str, number: int):
    """Lookup ekzakt, pa embeddings."""
    client = get_client()
    collection = client.get_collection(name=COLLECTION_NAME)

    if ref_type == "amendament":
        # amendment osht STRING "24" në Chroma
        results = collection.get(
            where={"amendment": str(number)}
        )
        formatted = []
        for doc, meta in zip(results["documents"], results["metadatas"]):
            formatted.append({
                "text": doc,
                "metadata": meta,
                "distance": 0.0,
                "score": 1.0,
                "method": "exact"
            })
        return formatted

    else:  # neni
        # 1. Provo si nen normal i Kushtetutës
        results = collection.get(
            where={"article": f"Neni {number}"}
        )
        if results["ids"]:
            formatted = []
            for doc, meta in zip(results["documents"], results["metadatas"]):
                formatted.append({
                    "text": doc,
                    "metadata": meta,
                    "distance": 0.0,
                    "score": 1.0,
                    "method": "exact"
                })
            return formatted

        # 2. Nëse nuk osht nen normal, mundet me qenë brenda një amendamenti
        # p.sh. Neni 162 osht brenda Amendamentit 24
        # Merr krejt amendamentet dhe filtro në Python
        all_amendments = collection.get(
            where={"document_section": "amendments"}
        )
        target = f"Neni {number}"
        # Edhe variantet: "Nenit 162", "nenit 162"
        variants = [f"Neni {number}", f"Nenit {number}", f"nenit {number}", f"neni {number}"]

        formatted = []
        for doc, meta in zip(all_amendments["documents"], all_amendments["metadatas"]):
            if any(v in doc for v in variants):
                formatted.append({
                    "text": doc,
                    "metadata": meta,
                    "distance": 0.0,
                    "score": 1.0,
                    "method": "exact-in-amendment"
                })
        return formatted

def semantic_search(query: str, n_results: int = 5):
    query_embedding = embed_query(query)
    client = get_client()
    collection = client.get_collection(name=COLLECTION_NAME)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]

    formatted = []
    for doc, meta, dist in zip(docs, metas, distances):
        formatted.append({
            "text": doc,
            "metadata": meta,
            "distance": dist,
            "score": dist,  # për L2, sa ma e vogël distanca, aq ma mirë
            "method": "semantic"
        })
    return formatted

def retrieve(query: str, n_results: int = 5):
    ref = parse_reference(query)
    if ref:
        ref_type, number = ref
        exact = get_by_reference(ref_type, number)
        if exact:
            print(f"[HYBRID] U gjet referencë ekzakte: {ref_type} {number}")
            # Kthe edhe 2 rezultate semantike si kontekst shtesë, por ekzaktin të parin
            extra = semantic_search(query, n_results=2)
            # Mos e përsërit ekzaktin
            exact_texts = {r["text"] for r in exact}
            extra = [r for r in extra if r["text"] not in exact_texts]
            return exact + extra
        else:
            print(f"[HYBRID] Referenca {ref_type} {number} nuk u gjet ekzakt, po bie në semantic...")

    return semantic_search(query, n_results=n_results)

def format_citation(result: dict) -> str:
    meta = result["metadata"]
    if meta.get("document_section") == "amendments":
        return f"Amendamenti {meta.get('amendment')}"
    else:
        article = meta.get("article") or "?"
        return str(article)  # tashmë osht "Neni 23", mos e shto prap

if __name__ == "__main__":
    queries = [
        "Qka thotë Neni 162?",
        "Amendamenti 24",
        "Të drejtat e njeriut",
        "Presidenti i Republikës së Kosovës",
    ]
    for q in queries:
        print(f"\n{'='*60}")
        print(f"PYETJA: {q}")
        print(f"{'='*60}")
        results = retrieve(q, n_results=3)
        for i, r in enumerate(results, 1):
            print(f"\n[{i}] {format_citation(r)} | method: {r['method']} | dist: {r['distance']:.3f}")
            print(r["text"][:500] + "...")