from pathlib import Path

from pypdf import PdfReader


RESUME_DIRECTORY = Path(__file__).resolve().parents[2] / "resumes"


RESUME_FILES = {
    "software_engineer": "software_engineer.pdf",
    "backend_engineer": "backend_engineer.pdf",
    "frontend_engineer": "frontend_engineer.pdf",
    "fullstack_engineer": "fullstack_engineer.pdf",
    "ai_ml_engineer": "ai_ml_engineer.pdf",
    "systems_engineer": "systems_engineer.pdf",
    "production_support_engineer": "production_support_engineer.pdf",
    "devops_engineer": "devops_engineer.pdf",
}


def extract_pdf_text(pdf_path: Path) -> str:
    """
    Extract text from every page of a PDF resume.
    """

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"Resume file not found: {pdf_path}"
        )

    reader = PdfReader(str(pdf_path))

    pages = []

    for page in reader.pages:
        text = page.extract_text()

        if text:
            pages.append(text.strip())

    return "\n".join(pages).strip()


def load_resume(
    resume_name: str,
    filename: str,
) -> dict:
    """
    Load one resume and return its metadata and text.
    """

    pdf_path = RESUME_DIRECTORY / filename

    text = extract_pdf_text(pdf_path)

    return {
        "name": resume_name,
        "filename": filename,
        "path": str(pdf_path),
        "text": text,
        "characters": len(text),
        "words": len(text.split()),
    }


def load_all_resumes() -> dict[str, dict]:
    """
    Load every configured master resume.
    """

    resumes = {}

    for resume_name, filename in RESUME_FILES.items():

        resumes[resume_name] = load_resume(
            resume_name=resume_name,
            filename=filename,
        )

    return resumes
