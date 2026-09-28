from langchain_core.documents import Document


def load_text_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        text = file.read()

    document = Document(
        page_content=text,
        metadata={
            "source": file_path,
            "type": "placement_policy"
        }
    )

    return [document]