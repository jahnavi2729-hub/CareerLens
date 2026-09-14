"""
CareerLens API Application Entrypoint
"""

from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

BASE_DIR = Path(__file__).resolve().parent.parent.parent

try:
    from src.comparison_engine import (
        get_available_roles,
        get_market_intelligence,
        compare_resume_to_market
    )
    from src.company_hiring_intelligence import get_company_hiring_intelligence
    from src.resume_processor import (
        process_resume,
        extract_text_from_pdf,
        extract_text_from_docx
    )
    from src.career_mentor import generate_career_mentor_feedback
except ImportError:
    from comparison_engine import (
        get_available_roles,
        get_market_intelligence,
        compare_resume_to_market
    )
    from company_hiring_intelligence import get_company_hiring_intelligence
    from resume_processor import (
        process_resume,
        extract_text_from_pdf,
        extract_text_from_docx
    )
    from career_mentor import generate_career_mentor_feedback

app = FastAPI(
    title="CareerLens API",
    description="CareerLens Job Intelligence & Pipeline API",
    version="0.1.0"
)

# Allow the standalone HTML frontend (served from file:// or any local dev port)
# to call the API without CORS errors.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "CareerLens API"
    }

@app.get("/", response_class=FileResponse)
def serve_index():
    path = BASE_DIR / "careerlens.html"
    return FileResponse(path if path.exists() else "careerlens.html")

@app.get("/market.html", response_class=FileResponse)
def serve_market_page():
    path = BASE_DIR / "market.html"
    return FileResponse(path if path.exists() else "market.html")

@app.get("/career-fit.html", response_class=FileResponse)
def serve_career_fit_page():
    path = BASE_DIR / "career-fit.html"
    return FileResponse(path if path.exists() else "career-fit.html")

@app.get("/roles")
def get_roles() -> Dict[str, Any]:
    """
    Returns available target roles supported by the market dataset.
    """
    roles_data = get_available_roles()
    return {
        "total_roles": len(roles_data),
        "roles": [item["role"] for item in roles_data],
        "role_details": roles_data
    }

@app.get("/market/{role}")
def get_market_intelligence_endpoint(role: str) -> Dict[str, Any]:
    """
    Returns market demand intelligence for the requested target role.
    """
    data = get_market_intelligence(role)
    if data["posting_denominator"] == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No job postings found matching target role '{role}'"
        )
    return data

@app.get("/market/{role}/companies")
def get_market_companies_endpoint(role: str) -> Dict[str, Any]:
    """
    Returns hiring company breakdown and skill demand for the requested target role.
    """
    data = get_company_hiring_intelligence(role)
    if data["total_postings"] == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No job postings found matching target role '{role}'"
        )
    return data

@app.post("/resume/analyze")
async def analyze_resume_endpoint(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Accepts an uploaded PDF/DOCX/TXT resume file and returns the structured candidate profile.
    """
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No resume file uploaded.")

    filename = file.filename.lower()
    if not (filename.endswith(".pdf") or filename.endswith(".docx") or filename.endswith(".txt")):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Please upload a .pdf, .docx, or .txt file."
        )

    contents = await file.read()
    if not contents or len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        if filename.endswith(".pdf"):
            text = extract_text_from_pdf(contents)
        elif filename.endswith(".docx"):
            text = extract_text_from_docx(contents)
        else:
            text = contents.decode("utf-8", errors="ignore")

        profile = process_resume(text)
        return profile
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process resume file: {str(e)}")

@app.post("/career-fit")
async def calculate_career_fit_endpoint(request: Request) -> Dict[str, Any]:
    """
    Accepts resume file/candidate data plus target_role and returns Market-vs-Resume comparison.
    Supports both multipart/form-data (file upload) and application/json requests.
    """
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()
        target_role = str(form.get("target_role", "Data Engineer")).strip()
        file_obj = form.get("file")
        resume_text = form.get("resume_text")

        if file_obj and hasattr(file_obj, "filename") and file_obj.filename:
            filename = file_obj.filename.lower()
            if not (filename.endswith(".pdf") or filename.endswith(".docx") or filename.endswith(".txt")):
                raise HTTPException(
                    status_code=400,
                    detail="Unsupported file format. Please upload a .pdf, .docx, or .txt file."
                )
            contents = await file_obj.read()
            if not contents:
                raise HTTPException(status_code=400, detail="Uploaded file is empty.")

            if filename.endswith(".pdf"):
                text = extract_text_from_pdf(contents)
            elif filename.endswith(".docx"):
                text = extract_text_from_docx(contents)
            else:
                text = contents.decode("utf-8", errors="ignore")

            candidate_input = text
        elif resume_text:
            candidate_input = str(resume_text)
        else:
            raise HTTPException(
                status_code=400,
                detail="Must provide either a resume file ('file') or 'resume_text' in form data."
            )

    else:
        # Expect JSON
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body or request format.")

        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="JSON body must be an object.")

        target_role = str(body.get("target_role", "Data Engineer")).strip()
        candidate_profile = body.get("candidate_profile")
        resume_text = body.get("resume_text")

        if candidate_profile and isinstance(candidate_profile, dict):
            candidate_input = candidate_profile
        elif resume_text:
            candidate_input = str(resume_text)
        else:
            raise HTTPException(
                status_code=400,
                detail="JSON body must contain either 'candidate_profile' or 'resume_text'."
            )

    if not target_role:
        raise HTTPException(status_code=400, detail="Target role parameter cannot be empty.")

    report = compare_resume_to_market(candidate_input, target_role=target_role)
    if report.get("posting_denominator", 0) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No job postings found matching target role '{target_role}'"
        )

    report["career_mentor_feedback"] = generate_career_mentor_feedback(report)

    return report

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="127.0.0.1", port=8000, reload=True)
