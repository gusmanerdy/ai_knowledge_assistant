from pypdf import PdfReader
import os

def ext_text(pdf_path):
    """
    Load the PDF file from selected path

    Args:
        pdf_path(string) : File Path selected from the copied path string
    Returns:
        All the text extracted from the file
    """
    #returning error if file not found
    if not os.path.exists(pdf_path):
        print(f"Error: File Not Found at {pdf_path}")
        return ""
    
    full_text="" 
    try:
        # creating a pdfreader object
        reader = PdfReader(pdf_path)

        # looping each page to extract the text
        for page in reader.pages:
            full_text += page.extract_text() + "\n"
    except Exception as e:
        print(f"An Error occured when reading the file : {e}")

    return full_text

filepath = "data/documents/A_Brief_Introduction_To_AI.pdf"
content = ext_text(filepath)
print(content)