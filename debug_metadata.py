from services.vector_store import get_client, COLLECTION_NAME

client = get_client()
collection = client.get_collection(name=COLLECTION_NAME)

# Merr 5 chunk-a të parë nga Kushtetuta + krejt amendamentet
all_data = collection.get(limit=200)

print("=== SHEQERAT E METADATA-VE ===")
for doc, meta in zip(all_data["documents"][:3], all_data["metadatas"][:3]):
    print("\n--- CHUNK KUSHTETUTË ---")
    print("METADATA:", meta)
    print("TEXT fillimi:", doc[:200])

print("\n\n=== AMENDAMENTET ===")
for doc, meta in zip(all_data["documents"], all_data["metadatas"]):
    if meta.get("document_section") == "amendments":
        print(f"\nMETADATA: {meta}")
        print("TEXT fillimi:", doc[:150])