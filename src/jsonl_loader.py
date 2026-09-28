import json
from langchain_core.documents import Document


def load_jsonl_file(file_path):

    documents = []

    with open(file_path, "r", encoding="utf-8") as file:

        for line in file:

            if not line.strip():
                continue

            data = json.loads(line)

            document = Document(
                page_content=data["text"],
                metadata=data.get("metadata", {})
            )

            documents.append(document)

    return documents