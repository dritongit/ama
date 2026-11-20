import chromadb
from services.document_loader import load_constitution
from services.text_chunker import chunk_pages
from services.embeddings import embed_texts

COLLECTION_NAME = "kosovo_constitution"
CHROMA_PATH = "data/chroma_db"

def get_client():
    return chromadb.PersistentClient(path=CHROMA_PATH)

def _sanitize_metadata(metadata: dict) -> dict:
    clean = {}
    for k, v in metadata.items():
        if v is None:
            clean[k] = ""
        elif isinstance(v, bool):
            clean[k] = v
        elif isinstance(v, (int, float, str)):
            clean[k] = v
        else:
            # list, dict, etj -> ktheje në string
            clean[k] = str(v)
    return clean

def build_index():
    chunks = chunk_pages(load_constitution())
    
    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)

    client = get_client()
    # Fshije koleksionin e vjetër nëse ekziston, për rebuild të pastër
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(name=COLLECTION_NAME)

    metadatas = [_sanitize_metadata(c["metadata"]) for c in chunks]

    collection.add(
        ids=[f"chunk_{i}" for i in range(len(chunks))],
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas
    )
    print(f"Indexed {len(chunks)} chunks")
    return collection

def search(query_embedding: list[float], n_results: int = 5):
    client = get_client()
    collection = client.get_collection(name=COLLECTION_NAME)
    return collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )

if __name__ == "__main__":
    build_index()