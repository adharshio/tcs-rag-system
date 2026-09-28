from src.jsonl_loader import load_jsonl_file
from src.chunker import split_documents


file_path = "data/company_faqs/company_faqs.jsonl"

print("Loading company FAQs...")

documents = load_jsonl_file(file_path)

print("Documents loaded!")
print("Number of documents:", len(documents))


print("\nSplitting documents...")

chunks = split_documents(documents)

print("Number of chunks:", len(chunks))


for i, chunk in enumerate(chunks[:5]):

    print("\n==============================")
    print("CHUNK", i + 1)
    print("==============================")

    print("Text:")
    print(chunk.page_content)

    print("\nMetadata:")
    print(chunk.metadata)