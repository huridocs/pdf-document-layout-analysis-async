from domain.ExtractionData import ExtractionData


def get_paragraphs(mongodb_client, tenant, pdf_file_name):
    suggestions_filter = {"tenant": tenant, "file_name": pdf_file_name}
    pdf_paragraph_db = mongodb_client["pdf_paragraph"]
    extraction_data_dict = pdf_paragraph_db.paragraphs.find_one(suggestions_filter)
    pdf_paragraph_db.paragraphs.delete_many(suggestions_filter)

    extraction_data = ExtractionData(**extraction_data_dict)
    return extraction_data.model_dump_json()
