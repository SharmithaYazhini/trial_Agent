import csv
import fitz  # PyMuPDF

class Document:
    def __init__(self, page_content, metadata):
        self.page_content = page_content
        self.metadata = metadata

def process_entire_document_for_splits(doc):
    all_documents = []
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        text_blocks = page.get_text("dict")["blocks"]
        labeled_page_number = None
        page_header = []
        page_chunks = []

        for block in text_blocks:
            if block['type'] == 0:  # text block
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        font = span["font"]
                        size = span["size"]

                        if font == "Archer-Bold" and size == 8.0:
                            page_header.append(text)
                        if font == "Archer-Bold" and size == 10.0 and text.isdigit():
                            labeled_page_number = text

                        current_heading_level = None
                        if font == "Archer-MediumItalic" and size == 38.0:
                            current_heading_level = 1
                        elif font == "Archer-SemiboldItalic" and size == 12.0:
                            current_heading_level = 2
                        elif font == "Archer-Bold" and size == 9.5:
                            current_heading_level = 3
                        elif font == "Frutiger-Italic" and size == 9.5:
                            current_heading_level = 4
                        
                        if current_heading_level:
                            page_chunks.append(f"Heading {current_heading_level}: {text}")
                        else:
                            page_chunks.append(f"Normal Text: {text}")

        if labeled_page_number:
            full_page_header = " ".join(page_header)
            page_content = " ".join(page_chunks)
            metadata = {"labeled_page_number": labeled_page_number, "page_header": full_page_header}
            document = Document(page_content, metadata)
            all_documents.append(document)
    return all_documents

# Load the PDF document
data = fitz.open("English_COG_Family_Handbook.pdf")

# Process the document and create splits
document_splits = process_entire_document_for_splits(data)

def save_documents_to_csv(documents, csv_filename):
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Page Content', 'Labeled Page Number', 'Page Header']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for document in documents:
            row = {
                'Page Content': document.page_content,
                'Labeled Page Number': document.metadata.get('labeled_page_number', ''),
                'Page Header': document.metadata.get('page_header', '')
            }
            writer.writerow(row)

# Specify the filename for the CSV file
csv_filename = "English_COG_Family_Handbook.csv"
save_documents_to_csv(document_splits, csv_filename)

print(f"Document splits have been successfully saved to {csv_filename}.")
