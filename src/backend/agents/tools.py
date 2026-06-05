import io
import httpx
import pypdf
from langchain_core.tools import tool


@tool
def read_pdf(file_path: str) -> str:
    """Extract text from a PDF file given its local path."""
    with open(file_path, "rb") as f:
        reader = pypdf.PdfReader(f)
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)


@tool
def read_website(url: str) -> str:
    """Convert a URL to clean markdown via Jina Reader."""
    resp = httpx.get(f"https://r.jina.ai/{url}", timeout=30)
    resp.raise_for_status()
    return resp.text


@tool
def read_ocr(file_path: str) -> str:
    """Extract text from an image file using EasyOCR."""
    import easyocr
    reader = easyocr.Reader(["en"], verbose=False)
    results = reader.readtext(file_path, detail=0)
    return "\n".join(results)
