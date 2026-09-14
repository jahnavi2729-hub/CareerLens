"""
CareerLens Resume Processor Module
----------------------------------
Consolidated, production-ready local resume processing pipeline.
Extracts structured Candidate Profiles from raw resume text or local files (.pdf, .docx, .txt).

Features:
- Local text extraction for PDF and DOCX files (pypdf, python-docx)
- Clean preprocessing fixing whitespace collapsing and punctuation issues
- Canonical skill extraction (AI/ML, Data Engineering, Software, Cloud, DevOps, Business, HR, Finance, etc.)
- Section segmentation (Summary, Experience, Education, Projects, Certifications, Skills)
- Experience years calculation and work history entry parsing
- Education degree and domain classification
- Job title / target role identification
- Certifications and projects extraction
- ZERO external API calls (100% local processing)
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# Attempt imports of local file text extraction libraries
try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


# =============================================================================
# 1. TEXT CLEANING & PREPROCESSING
# =============================================================================

def clean_resume_text(raw_text: str) -> str:
    """
    Cleans raw resume text by stripping HTML tags, normalizing whitespace,
    and fixing formatting while preserving word boundaries and key symbols (+, #, ., -, /).
    Fixes the issue in legacy scripts where characters were stripped without replacing with spaces.
    """
    if not raw_text or not isinstance(raw_text, str):
        return ""

    text = str(raw_text)

    # Strip HTML tags & entities if HTML is passed
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-zA-Z0-9#]+;", " ", text)

    # Normalize line breaks and tabs to single spaces or newlines
    text = re.sub(r"[\r\n\t]+", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    # Strip leading/trailing space from each line
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines)


def _normalize_for_matching(text: str) -> str:
    """
    Lowercase and normalize spaces for case-insensitive regex matching.
    """
    cleaned = clean_resume_text(text)
    return cleaned.lower()


# =============================================================================
# 2. LOCAL FILE TEXT EXTRACTION (PDF, DOCX, TXT)
# =============================================================================

def extract_text_from_pdf(file_path_or_bytes: Union[str, Path, bytes]) -> str:
    """Extract text from a PDF file locally using pypdf."""
    if not HAS_PYPDF:
        raise RuntimeError("pypdf is not installed. Install pypdf to extract text from PDF files.")

    import io
    if isinstance(file_path_or_bytes, (str, Path)):
        reader = pypdf.PdfReader(str(file_path_or_bytes))
    else:
        reader = pypdf.PdfReader(io.BytesIO(file_path_or_bytes))

    text_parts = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_text_from_docx(file_path_or_bytes: Union[str, Path, bytes]) -> str:
    """Extract text from a DOCX file locally using python-docx."""
    if not HAS_DOCX:
        raise RuntimeError("python-docx is not installed. Install python-docx to extract text from DOCX files.")

    import io
    if isinstance(file_path_or_bytes, (str, Path)):
        doc = docx.Document(str(file_path_or_bytes))
    else:
        doc = docx.Document(io.BytesIO(file_path_or_bytes))

    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    # Also extract table text if present
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                paragraphs.append(row_text)

    return "\n".join(paragraphs)


def extract_text_from_file(file_path: Union[str, Path]) -> str:
    """
    Extract text from a local resume file (.pdf, .docx, .txt).
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Resume file not found: {file_path}")

    ext = path.suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(path)
    elif ext in [".docx", ".doc"]:
        return extract_text_from_docx(path)
    elif ext in [".txt", ".html", ".htm", ".csv"]:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    else:
        raise ValueError(f"Unsupported file format '{ext}'. Supported: .pdf, .docx, .txt, .html")


# =============================================================================
# 3. PATTERNS & REGEX DEFINITIONS
# =============================================================================

def _make_patterns(*patterns: str) -> List[re.Pattern]:
    return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]


SKILL_PATTERNS: List[tuple] = [
    # AI, ML & Data Science
    ("Artificial Intelligence", _make_patterns(r"\bartificial\s*intelligence\b", r"(?<![A-Za-z0-9])ai(?![A-Za-z0-9])")),
    ("Generative AI", _make_patterns(r"\bgenerative\s*ai\b", r"\bgen\s*ai\b", r"\bgenai\b")),
    ("LLM", _make_patterns(r"\blarge\s*language\s*models?\b", r"\bllms?\b")),
    ("Machine Learning", _make_patterns(r"\b(machine\s*learning|machine-learning|ml)\b")),
    ("Deep Learning", _make_patterns(r"\b(deep\s*learning|deep-learning|neural\s*networks?)\b")),
    ("NLP", _make_patterns(r"\b(natural\s*language\s*processing|nlp|text\s*mining)\b")),
    ("Computer Vision", _make_patterns(r"\bcomputer\s*vision\b", r"\bopencv\b")),
    ("Data Science", _make_patterns(r"\bdata\s*science\b")),
    ("Data Analysis", _make_patterns(r"\bdata\s*analysis\b", r"\banalytics\b", r"\bmis\s*reporting\b")),
    ("ETL & Data Pipelines", _make_patterns(r"\betl\b", r"\bdata\s*pipelines?\b", r"\bdata\s*warehousing\b")),
    ("Data Modeling", _make_patterns(r"\bdata\s*model(?:ing|ling)\b")),
    ("Statistics", _make_patterns(r"\bstatistics\b", r"\bstatistical\b", r"\bprobability\b")),
    ("Pandas", _make_patterns(r"\bpandas\b")),
    ("NumPy", _make_patterns(r"\bnumpy\b")),
    ("Matplotlib", _make_patterns(r"\bmatplotlib\b")),
    ("Seaborn", _make_patterns(r"\bseaborn\b")),
    ("Scikit-learn", _make_patterns(r"\bscikit(?:-|\s*)learn\b", r"\bsklearn\b")),
    ("TensorFlow", _make_patterns(r"\btensorflow\b")),
    ("PyTorch", _make_patterns(r"\bpytorch\b")),
    ("Power BI", _make_patterns(r"\b(power\s*bi|powerbi)\b")),
    ("Tableau", _make_patterns(r"\btableau\b")),
    ("Excel", _make_patterns(r"\bexcel\b", r"\badvanced\s*excel\b", r"\bpivot\s*tables?\b", r"\bvlookup\b")),
    ("Spark", _make_patterns(r"\bspark\b", r"\bpyspark\b")),
    ("Hadoop", _make_patterns(r"\bhadoop\b")),
    ("Airflow", _make_patterns(r"\bairflow\b")),

    # Software Engineering & Programming Languages
    ("Python", _make_patterns(r"\bpython\b", r"\bpy\b")),
    ("Java", _make_patterns(r"\bjava\b", r"\bjdk\b", r"\bspring\s*boot\b")),
    ("C", _make_patterns(
        r"\b(?:embedded\s*c|ansi\s*c|c\s*programming|c\s*language)\b",
        r"\b(?:c\s*[\/,]\s*c\+\+|c\s*\&\s*c\+\+|c\s*[\/,]\s*c#|c\s*[\/,]\s*java|python\s*[\/,]\s*c)\b",
        r"\b(?:languages?|programming|coding|skills)\s*[\/:-]\s*c\b",
        r"\bC\b(?=\s*[\/,]\s*(?:C\+\+|C#|Java|Python|Assembly|Rust|Go)\b)",
        r"\b(?:C\+\+|Java|Python|Assembly|Rust|Go)\s*[\/,]\s*C\b"
    )),
    ("C++", _make_patterns(r"(?:\bc\+\+|\bc\s*\+\s*\+)")),
    ("C#", _make_patterns(r"\b(c#|c\s*sharp|\.net)\b")),
    ("JavaScript", _make_patterns(r"\bjavascript\b", r"\bjs\b", r"\becmascript\b")),
    ("TypeScript", _make_patterns(r"\btypescript\b", r"\bts\b")),
    ("Go", _make_patterns(r"\bgolang\b", r"\bgo\b")),
    ("Rust", _make_patterns(r"\brust\b")),
    ("PHP", _make_patterns(r"\bphp\b", r"\blaravel\b")),
    ("R", _make_patterns(r"(?<![A-Za-z0-9])r(?![A-Za-z0-9])", r"\brstudio\b")),
    ("Kotlin", _make_patterns(r"\bkotlin\b")),
    ("Swift", _make_patterns(r"\bswift\s*(?:ui|language|ios|developer|app)?\b(?![\s\-]*(?:resolution|response|action|delivery|process|turnaround))")),
    ("HTML", _make_patterns(r"\bhtml5?\b")),
    ("CSS", _make_patterns(r"\bcss3?\b")),
    ("Bootstrap", _make_patterns(r"\bbootstrap\b", r"\btailwind\b")),
    ("React", _make_patterns(r"\breact\b", r"\breactjs\b", r"\bnext\.?js\b")),
    ("Angular", _make_patterns(r"\bangular\b")),
    ("Vue", _make_patterns(r"\bvue\b", r"\bvuejs\b")),
    ("Node.js", _make_patterns(r"\bnode(?:\.js|js)?\b", r"\bexpress(?:\.js)?\b")),
    ("REST API", _make_patterns(r"\brest\s*api\b", r"\brestful\b", r"\bapis?\b")),
    ("GraphQL", _make_patterns(r"\bgraphql\b")),
    ("Microservices", _make_patterns(r"\bmicroservices?\b")),
    ("Software Architecture", _make_patterns(r"\bsoftware\s*architecture\b", r"\bsystem\s*architecture\b")),
    ("System Design", _make_patterns(r"\bsystem\s*design\b", r"\bscalable\s*systems?\b")),
    ("Data Structures", _make_patterns(r"\bdata\s*structures?\b", r"\bdsa\b")),
    ("Algorithms", _make_patterns(r"\balgorithms?\b")),

    # Databases
    ("SQL", _make_patterns(r"(?<![A-Za-z0-9])sql(?![A-Za-z0-9])")),
    ("MySQL", _make_patterns(r"\bmysql\b")),
    ("PostgreSQL", _make_patterns(r"\bpostgres(?:ql)?\b")),
    ("MongoDB", _make_patterns(r"\bmongodb\b", r"\bnosql\b")),
    ("Oracle", _make_patterns(r"\boracle\b")),
    ("Redis", _make_patterns(r"\bredis\b")),

    # Cloud, DevOps & Infrastructure
    ("DevOps", _make_patterns(r"\bdevops\b")),
    ("Cloud Computing", _make_patterns(r"\bcloud\s*computing\b", r"\bcloud\s*infrastructure\b")),
    ("AWS", _make_patterns(r"\baws\b", r"\bamazon\s*web\s*services\b")),
    ("Azure", _make_patterns(r"\bazure\b")),
    ("GCP", _make_patterns(r"\bgcp\b", r"\bgoogle\s*cloud\b")),
    ("Docker", _make_patterns(r"\bdocker\b", r"\bcontaineri[sz]ation\b")),
    ("Kubernetes", _make_patterns(r"\bkubernetes\b", r"\bk8s\b")),
    ("CI/CD", _make_patterns(r"\bci/cd\b", r"\bcontinuous\s*integration\b", r"\bcontinuous\s*delivery\b")),
    ("Git", _make_patterns(r"\bgit\b", r"\bgithub\b", r"\bgitlab\b")),
    ("Linux", _make_patterns(r"\blinux\b", r"\bubuntu\b", r"\bshell\s*scripting\b")),
    ("Cyber Security", _make_patterns(r"\bcyber\s*security\b", r"\binformation\s*security\b", r"\bvapt\b")),
    ("Networking", _make_patterns(r"\bnetworking\b", r"\btcp/ip\b", r"\brouting\b")),

    # Business, Finance, Management & HR
    ("Sales", _make_patterns(r"\bsales\b", r"\blead\s*generation\b", r"\bbusiness\s*development\b")),
    ("Operations", _make_patterns(r"\boperations?\b", r"\bprocess\s*improvement\b", r"\bsupply\s*chain\b", r"\blogistics\b")),
    ("Project Management", _make_patterns(r"\bproject\s*management\b", r"\bproject\s*coordination\b", r"\bagile\b", r"\bscrum\b")),
    ("Jira", _make_patterns(r"\bjira\b", r"\bconfluence\b")),
    ("Product Management", _make_patterns(r"\bproduct\s*management\b", r"\bproduct\s*roadmap\b")),
    ("Business Analysis", _make_patterns(r"\bbusiness\s*analysis\b", r"\brequirement\s*gathering\b", r"\bstakeholder\s*management\b")),
    ("Accounting", _make_patterns(r"\baccounting\b", r"\baccounts?\b", r"\bjournal\s*entries\b", r"\bledger\b")),
    ("Finance", _make_patterns(r"\bfinance\b", r"\bfinancial\b", r"\binvestment\b", r"\bportfolio\b")),
    ("Financial Analysis", _make_patterns(r"\bfinancial\s*analysis\b", r"\bfinancial\s*model(?:ing|ling)\b", r"\bratio\s*analysis\b")),
    ("Taxation", _make_patterns(r"\btax(?:ation)?\b", r"\bgst\b", r"\btds\b", r"\bincome\s*tax\b")),
    ("Audit", _make_patterns(r"\baudit(?:ing)?\b", r"\binternal\s*controls?\b")),
    ("Tally", _make_patterns(r"\btally\b", r"\btally\s*erp\b", r"\btally\s*prime\b")),
    ("SAP", _make_patterns(r"\bsap\b", r"\bsap\s*fico\b")),
    ("CRM", _make_patterns(r"\bcrm\b", r"\bsalesforce\b", r"\bhubspot\b")),
    ("Marketing", _make_patterns(r"\bmarketing\b", r"\bdigital\s*marketing\b", r"\bbrand\s*management\b")),
    ("SEO", _make_patterns(r"\bseo\b", r"\bsearch\s*engine\s*optimization\b")),
    ("Content Strategy", _make_patterns(r"\bcontent\s*strategy\b", r"\bcopywriting\b", r"\bsocial\s*media\b")),
    ("Market Research", _make_patterns(r"\bmarket\s*research\b", r"\bconsumer\s*research\b")),
    ("HR", _make_patterns(r"\bhr\b", r"\bhuman\s*resources\b", r"\bhrm\b")),
    ("Recruitment", _make_patterns(r"\brecruit(?:ment|ing)\b", r"\btalent\s*acquisition\b", r"\bsourcing\b")),
    ("Payroll", _make_patterns(r"\bpayroll\b", r"\bcompensation\b", r"\bbenefits\b")),
    ("Employee Relations", _make_patterns(r"\bemployee\s*relations\b", r"\bperformance\s*management\b")),
    ("Communication", _make_patterns(r"\bcommunication(?:s)?\b", r"\bpresentation\s*skills?\b", r"\bpublic\s*speaking\b")),
    ("Leadership", _make_patterns(r"\bleadership\b", r"\bteam\s*lead\b", r"\bpeople\s*management\b")),
    ("Problem Solving", _make_patterns(r"\bproblem\s*solving\b", r"\banalytical\s*thinking\b", r"\bcritical\s*thinking\b")),

    # Customer Support & Healthcare Operations
    ("Customer Support", _make_patterns(r"\bcustomer\s*support\b", r"\bcustomer\s*service\b", r"\bclient\s*support\b")),
    ("BPO / Voice Process", _make_patterns(r"\bbpo\b", r"\bvoice\s*process\b", r"\bcall\s*center\b")),
    ("Medical Billing & Claims", _make_patterns(r"\bmedical\s*claims?\b", r"\bmedical\s*billing\b", r"\bicd-9\b", r"\bcpt\b", r"\brcm\b")),

    # Engineering, Healthcare, Design
    ("AutoCAD", _make_patterns(r"\bauto\s*cad\b", r"\bautocad\b")),
    ("SolidWorks", _make_patterns(r"\bsolidworks\b", r"\bsolid\s*works\b")),
    ("CATIA", _make_patterns(r"\bcatia\b")),
    ("ANSYS", _make_patterns(r"\bansys\b", r"\bfea\b", r"\bfinite\s*element\b")),
    ("Manufacturing", _make_patterns(r"\bmanufacturing\b", r"\bproduction\b", r"\bquality\s*control\b")),
    ("Civil Engineering", _make_patterns(r"\bcivil\s*engineering\b", r"\bconstruction\b", r"\bstructural\s*design\b")),
    ("Embedded Systems", _make_patterns(r"\bembedded\s*systems?\b", r"\bmicrocontrollers?\b", r"\barduino\b")),
    ("VLSI", _make_patterns(r"\bvlsi\b", r"\bverilog\b", r"\bvhdl\b")),
    ("MATLAB", _make_patterns(r"\bmatlab\b", r"\bsimulink\b")),
    ("Clinical Care", _make_patterns(r"\bclinical\b", r"\bpatient\s*care\b", r"\bnursing\b")),
    ("Pharmacology", _make_patterns(r"\bpharmacology\b", r"\bpharmacy\b")),
    ("Compliance", _make_patterns(r"\bcompliance\b", r"\bregulatory\b")),
    ("UI/UX Design", _make_patterns(r"\bui/ux\b", r"\buser\s*experience\b", r"\buser\s*interface\b")),
    ("Figma", _make_patterns(r"\bfigma\b")),
    ("Adobe Creative Suite", _make_patterns(r"\bphotoshop\b", r"\billustrator\b", r"\badobe\b")),
]


EDUCATION_PATTERNS: Dict[str, List[re.Pattern]] = {
    "B.Tech / B.E.": _make_patterns(
        r"\bb\.?\s*tech\b",
        r"\bbachelor\s*of\s*technology\b",
        r"\bbachelor\s*of\s*engineering\b",
        r"\b(b\.e\.|b\.e|b\.\s*e\.|b\.\s*e)\b",
        r"\bb\.?\s*eng\.?\b"
    ),
    "M.Tech / M.E.": _make_patterns(
        r"\bm\.?\s*tech\b",
        r"\bmaster\s*of\s*technology\b",
        r"\bmaster\s*of\s*engineering\b",
        r"\b(m\.e\.|m\.e|m\.\s*e\.|m\.\s*e)\b",
        r"\bm\.?\s*eng\.?\b"
    ),
    "B.Sc": _make_patterns(r"\bb\.?\s*sc\b", r"\bbachelor\s*of\s*science\b"),
    "M.Sc": _make_patterns(r"\bm\.?\s*sc\b", r"\bmaster\s*of\s*science\b"),
    "B.Com": _make_patterns(r"\bb\.?\s*com\b", r"\bbachelor\s*of\s*commerce\b"),
    "M.Com": _make_patterns(r"\bm\.?\s*com\b", r"\bmaster\s*of\s*commerce\b"),
    "BBA": _make_patterns(r"\bbba\b", r"\bbachelor\s*of\s*business\s*administration\b"),
    "MBA / PGDM": _make_patterns(r"\bmba\b", r"\bmaster\s*of\s*business\s*administration\b", r"\bpgdm\b"),
    "Ph.D": _make_patterns(r"\bph\.?d\b", r"\bdoctor\s*of\s*philosophy\b"),
    "LLB / Law": _make_patterns(r"\bllb\b", r"\bbb\.?\s*llb\b", r"\blaw\s*degree\b"),
    "MBBS": _make_patterns(r"\bmbbs\b"),
    "B.Pharm": _make_patterns(r"\bb\.?\s*pharm\b", r"\bbachelor\s*of\s*pharmacy\b"),
    "B.Arch": _make_patterns(r"\bb\.?\s*arch\b", r"\bbachelor\s*of\s*architecture\b"),
    "B.Des": _make_patterns(r"\bb\.?\s*des\b", r"\bbachelor\s*of\s*design\b"),
    "High School / College Prep": _make_patterns(r"\bhigh\s*school\b", r"\bdiploma\b", r"\bcollege\s*prep\b"),
}


DOMAIN_PATTERNS: Dict[str, List[re.Pattern]] = {
    "Data Engineering & Science": _make_patterns(r"\bdata\s*science\b", r"\bdata\s*engineer\b", r"\banalytics\b", r"\bmachine\s*learning\b"),
    "Software Engineering": _make_patterns(r"\bcomputer\s*science\b", r"\bsoftware\s*engineer\b", r"\binformation\s*technology\b", r"\bweb\s*development\b"),
    "DevOps & Cloud": _make_patterns(r"\bdevops\b", r"\bcloud\b", r"\baws\b", r"\bazure\b", r"\bsysadmin\b"),
    "Finance & Accounting": _make_patterns(r"\bfinance\b", r"\baccounting\b", r"\btax\b", r"\baudit\b", r"\bbanking\b"),
    "Marketing & Sales": _make_patterns(r"\bmarketing\b", r"\bsales\b", r"\bseo\b", r"\bbrand\b", r"\bbusiness\s*development\b"),
    "Human Resources": _make_patterns(r"\bhuman\s*resources\b", r"\bhr\b", r"\brecruitment\b", r"\bpayroll\b"),
    "Operations & Management": _make_patterns(r"\boperations\b", r"\bproject\s*management\b", r"\bproduct\s*management\b", r"\bsupply\s*chain\b"),
    "Customer Support & BPO": _make_patterns(r"\bcustomer\s*service\b", r"\bcustomer\s*support\b", r"\bbpo\b", r"\bcall\s*center\b"),
    "Healthcare & Medical Claims": _make_patterns(r"\bhealthcare\b", r"\bmedical\b", r"\bclinical\b", r"\bpatient\s*care\b", r"\bmedical\s*claims\b"),
    "Engineering & Design": _make_patterns(r"\bmechanical\b", r"\bcivil\b", r"\belectronics\b", r"\bui/ux\b", r"\bautocad\b"),
}


JOB_TITLE_PATTERNS: List[tuple] = [
    ("Data Engineer", _make_patterns(r"\bdata\s*engineer\b", r"\betl\s*developer\b", r"\bbig\s*data\s*engineer\b")),
    ("Data Scientist", _make_patterns(r"\bdata\s*scientist\b", r"\bmachine\s*learning\s*engineer\b", r"\bml\s*engineer\b")),
    ("Data Analyst", _make_patterns(r"\bdata\s*analyst\b", r"\bbusiness\s*intelligence\s*analyst\b", r"\bbi\s*developer\b")),
    ("Software Engineer", _make_patterns(r"\bsoftware\s*engineer\b", r"\bsoftware\s*developer\b", r"\bpython\s*developer\b", r"\bjava\s*developer\b")),
    ("Frontend Developer", _make_patterns(r"\bfrontend\s*developer\b", r"\bweb\s*developer\b", r"\breact\s*developer\b")),
    ("Backend Developer", _make_patterns(r"\bbackend\s*developer\b", r"\bnode\s*developer\b")),
    ("Full Stack Developer", _make_patterns(r"\bfull\s*stack\s*developer\b", r"\bfullstack\s*engineer\b")),
    ("DevOps Engineer", _make_patterns(r"\bdevops\s*engineer\b", r"\bcloud\s*engineer\b", r"\bsite\s*reliability\s*engineer\b", r"\bsre\b")),
    ("HR Administrator / Specialist", _make_patterns(r"\bhr\s*administrator\b", r"\bhr\s*specialist\b", r"\bhr\s*manager\b", r"\bhr\s*director\b")),
    ("Marketing Associate / Specialist", _make_patterns(r"\bmarketing\s*associate\b", r"\bmarketing\s*specialist\b", r"\bmarketing\s*manager\b")),
    ("Project Manager", _make_patterns(r"\bproject\s*manager\b", r"\bscrum\b", r"\bproject\s*coordinator\b")),
    ("Product Manager", _make_patterns(r"\bproduct\s*manager\b", r"\bproduct\s*owner\b")),
    ("Business Analyst", _make_patterns(r"\bbusiness\s*analyst\b", r"\bsystems?\s*analyst\b")),
    ("Financial Analyst / Accountant", _make_patterns(r"\bfinancial\s*analyst\b", r"\baccountant\b", r"\baccounts\s*executive\b")),
    ("Customer Service Manager / Agent", _make_patterns(r"\bcustomer\s*service\s*manager\b", r"\bcustomer\s*support\s*executive\b", r"\bcall\s*center\s*agent\b")),
    ("Medical Claims Analyst", _make_patterns(r"\bmedical\s*claims?\s*analyst\b", r"\bmedical\s*billing\s*specialist\b")),
]


# =============================================================================
# 4. SECTION & FEATURE EXTRACTION LOGIC
# =============================================================================

SECTION_HEADERS: Dict[str, re.Pattern] = {
    "summary": re.compile(r"\b(summary|professional\s*summary|profile|executive\s*summary|highlights|about\s*me)\b", re.IGNORECASE),
    "experience": re.compile(r"\b(experience|work\s*history|professional\s*experience|employment\s*history|work\s*experience|career\s*history|internships?|internship\s*experience)\b", re.IGNORECASE),
    "education": re.compile(r"\b(education|academic\s*background|educational\s*qualifications|academic\s*qualifications|qualifications)\b", re.IGNORECASE),
    "projects": re.compile(r"\b(projects|key\s*projects|academic\s*projects|personal\s*projects)\b", re.IGNORECASE),
    "certifications": re.compile(r"\b(certifications|accomplishments|licenses|training|certifications?\s*&\s*licenses|awards)\b", re.IGNORECASE),
    "skills": re.compile(r"\b(skills|technical\s*skills|skill\s*highlights|core\s*competencies|technologies)\b", re.IGNORECASE),
}


def extract_sections(raw_text: str) -> Dict[str, str]:
    """
    Parses resume text into logical sections: summary, experience, education, projects, certifications, skills.
    """
    cleaned = clean_resume_text(raw_text)
    lines = cleaned.split("\n")

    sections: Dict[str, List[str]] = {
        "summary": [],
        "experience": [],
        "education": [],
        "projects": [],
        "certifications": [],
        "skills": [],
        "other": []
    }

    current_section = "other"

    for line in lines:
        stripped = line.strip()
        # Check if line matches a known section header (usually short lines or title case)
        matched_header = None
        if len(stripped) < 40:
            for sec_name, sec_pattern in SECTION_HEADERS.items():
                if sec_pattern.search(stripped):
                    matched_header = sec_name
                    break

        if matched_header:
            current_section = matched_header
        else:
            sections[current_section].append(stripped)

    return {sec: "\n".join(content_lines).strip() for sec, content_lines in sections.items()}


def extract_skills_from_text(raw_text: str) -> List[str]:
    """Extract canonical skills from text using compiled pattern matching."""
    if not raw_text or not isinstance(raw_text, str):
        return []

    text = str(raw_text)
    detected_skills = []
    for skill_name, patterns in SKILL_PATTERNS:
        if any(pattern.search(text) for pattern in patterns):
            if skill_name not in detected_skills:
                detected_skills.append(skill_name)
    return detected_skills


def extract_experience_years(raw_text: str, sections: Optional[Dict[str, str]] = None) -> int:
    """
    Calculates years of professional experience from:
      1. Explicit claims (e.g. "8+ years", "5 yrs experience") found in
         professional sections (experience + summary).
      2. Date ranges (e.g. "2017 - 2021", "Jan 2020 to Present") found ONLY
         in the experience and summary sections.

    When `sections` is supplied (the parsed section dict from extract_sections),
    date-range parsing is restricted to professional text so that education
    degree ranges, project durations, and certification dates are never
    mis-counted as work experience.

    When `sections` is None (legacy / direct call), the original full-text
    scan is used as a fallback.

    Parameters:
        raw_text  : The full cleaned resume text (used as fallback).
        sections  : Optional dict returned by extract_sections().

    Returns:
        int: Estimated years of professional experience (0 if none detected).
    """
    # Build the professional text corpus to search:
    #   • If sections are available, restrict to experience + summary only.
    #   • Otherwise fall back to the full text (backward-compatible).
    if sections is not None:
        exp_section   = sections.get("experience", "")
        summ_section  = sections.get("summary", "")
        # Concatenate professional sections only; education/projects/certs excluded.
        professional_text = "\n".join(filter(None, [summ_section, exp_section]))
    else:
        professional_text = raw_text

    # When sections provided but both experience and summary are empty, the
    # resume has no parseable section headers (e.g. dense single-paragraph
    # prose resumes).  Fall back to full-text so those resumes still get a
    # result, but ONLY for the explicit-years strategy (Strategy 1) where
    # false positives are much less likely.  Date-range scanning stays
    # restricted to professional_text to avoid education/project pollution.
    use_full_text_for_explicit = sections is not None and not professional_text.strip()
    full_norm_text = _normalize_for_matching(raw_text) if use_full_text_for_explicit else None

    norm_text = _normalize_for_matching(professional_text) if professional_text.strip() else ""

    exp_years: List[int] = []

    # ── Strategy 1: Explicit year claims ──────────────────────────────────────
    # Matches: "8+ years", "5 yrs", "3 years of experience".
    # Scoped to professional text to avoid matching "4-year degree" in education.
    # For headerless resumes (no section markers found), scans the full text.
    scan_text_s1 = full_norm_text if use_full_text_for_explicit else norm_text
    for match in re.finditer(r"\b(\d{1,2})(?:\+)?\s*(?:years?|yrs?)\b", scan_text_s1):
        try:
            val = int(match.group(1))
            if 1 <= val <= 50:           # Exclude 0 (noise) and unrealistic values
                exp_years.append(val)
        except ValueError:
            pass

    # ── Strategy 2: Date-range calculation ────────────────────────────────────
    # Matches: "2017 - 2021", "Jan 2020 to Present", "01/2014 - Current", etc.
    # Only runs on professional_text so education / project dates are excluded.
    current_year = 2026
    date_range_pattern = re.compile(
        r"\b(?:0?[1-9]|1[0-2]|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)?[\/\s,-]*"
        r"(19\d{2}|20\d{2})\s*(?:to|-|–|—|\buntil\b)\s*"
        r"(?:present|current|now|(?:0?[1-9]|1[0-2]|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)?[\/\s,-]*(19\d{2}|20\d{2}))\b",
        re.IGNORECASE
    )

    for match in date_range_pattern.finditer(norm_text):
        start_yr  = int(match.group(1))
        end_group = match.group(2)
        end_yr    = int(end_group) if end_group else current_year

        if 1970 <= start_yr <= current_year and start_yr <= end_yr <= current_year:
            span = end_yr - start_yr
            if 0 < span <= 50:
                exp_years.append(span)

    return max(exp_years) if exp_years else 0


def extract_education(raw_text: str) -> List[str]:
    """Extracts degree names / educational qualifications from resume text."""
    text = str(raw_text or "")
    detected = []
    for degree_name, patterns in EDUCATION_PATTERNS.items():
        if any(pattern.search(text) for pattern in patterns):
            if degree_name not in detected:
                detected.append(degree_name)
    return detected


def extract_job_titles(raw_text: str) -> List[str]:
    """Extracts recognized job titles / roles from resume text."""
    text = str(raw_text or "")
    detected = []
    for title_name, patterns in JOB_TITLE_PATTERNS:
        if any(pattern.search(text) for pattern in patterns):
            if title_name not in detected:
                detected.append(title_name)
    return detected


def extract_certifications(raw_text: str, sections: Optional[Dict[str, str]] = None) -> List[str]:
    """Extracts certification entries from text and certification section."""
    certs = []
    text = str(raw_text or "")

    # Regex patterns for certifications
    cert_patterns = [
        r"\b([A-Za-z0-9\s\-]+(?:\s+Certification|\s+Certificate|\s+Certified))\b",
        r"\b(Certified\s+[A-Za-z0-9\s\-]+)\b",
        r"\b(AWS\s+Certified[A-Za-z0-9\s\-]*)\b",
        r"\b(PMP|Scrum\s*Master|ITIL|CISSP|CISA)\b"
    ]

    for pat in cert_patterns:
        for match in re.finditer(pat, text, re.IGNORECASE):
            cert_str = match.group(1).strip()
            if 3 < len(cert_str) < 60 and cert_str not in certs:
                certs.append(cert_str)

    # Also extract lines from section if available
    if sections and sections.get("certifications"):
        cert_section_lines = [line.strip() for line in sections["certifications"].split("\n") if line.strip()]
        for line in cert_section_lines:
            if len(line) < 100 and line not in certs:
                certs.append(line)

    return certs[:10]  # Return top 10 unique certifications


def extract_projects(sections: Dict[str, str]) -> List[str]:
    """Extracts project entries from the Projects section if present."""
    proj_text = sections.get("projects", "")
    if not proj_text:
        return []

    lines = [line.strip() for line in proj_text.split("\n") if line.strip()]
    return lines[:10]


# =============================================================================
# 5. MAIN RESUME PROCESSOR PIPELINE
# =============================================================================

def process_resume(resume_input: Union[str, Path, bytes], is_file_path: bool = False) -> Dict[str, Any]:
    """
    Main entry point for processing a candidate resume locally.

    Parameters:
        resume_input (str, Path, bytes): Raw resume text OR local file path/bytes.
        is_file_path (bool): Set to True if resume_input is a path to a PDF/DOCX/TXT file.

    Returns:
        Structured Candidate Profile dictionary containing:
        - candidate_name (Optional str)
        - job_titles (List[str])
        - skills (List[str])
        - skill_count (int)
        - experience_years (int)
        - experience_summary (List[str])
        - education (List[str])
        - domains (List[str])
        - projects (List[str])
        - certifications (List[str])
        - summary (str)
        - profile_text (str)
    """
    if is_file_path or (isinstance(resume_input, (Path, str)) and os.path.exists(str(resume_input))):
        raw_text = extract_text_from_file(resume_input)
    elif isinstance(resume_input, bytes):
        raw_text = resume_input.decode("utf-8", errors="ignore")
    else:
        raw_text = str(resume_input or "")

    cleaned_text = clean_resume_text(raw_text)
    sections = extract_sections(cleaned_text)

    # Core extraction components
    skills = extract_skills_from_text(cleaned_text)
    education = extract_education(cleaned_text)
    job_titles = extract_job_titles(cleaned_text)
    exp_years = extract_experience_years(cleaned_text, sections=sections)
    certs = extract_certifications(cleaned_text, sections=sections)
    projects = extract_projects(sections)

    # Domain classification based on detected skills, education, and text
    domains = []
    for domain_name, patterns in DOMAIN_PATTERNS.items():
        if any(pattern.search(cleaned_text) for pattern in patterns):
            domains.append(domain_name)

    # Extract top experience bullet points/lines from experience section
    exp_lines = [line.strip() for line in sections.get("experience", "").split("\n") if line.strip()]

    # Extract candidate summary if available
    summary_text = sections.get("summary", "").strip()

    return {
        "job_titles": job_titles,
        "skills": skills,
        "skill_count": len(skills),
        "experience_years": exp_years,
        "experience_summary": exp_lines[:15],
        "education": education,
        "domains": domains,
        "projects": projects,
        "certifications": certs,
        "summary": summary_text,
        "profile_text": cleaned_text,
    }


if __name__ == "__main__":
    # Self-test on a sample candidate resume text
    sample_resume = """
    JOHN DOE
    Senior Data Engineer | Python & AWS Specialist
    San Francisco, CA | john.doe@example.com

    PROFESSIONAL SUMMARY
    Dedicated Data Engineer with 8+ years of experience building scalable ETL data pipelines,
    cloud data warehouses, and machine learning systems. Experienced in AWS, Python, Spark, and SQL.

    TECHNICAL SKILLS
    Languages: Python, SQL, Java, C++
    Data Engineering: PySpark, Apache Airflow, ETL, PostgreSQL, MongoDB, Snowflake, Redshift
    Cloud & DevOps: AWS (S3, Lambda, Glue), Docker, Kubernetes, CI/CD, Git, Linux
    Machine Learning: Pandas, NumPy, Scikit-learn, TensorFlow

    EXPERIENCE
    Lead Data Engineer | Tech Corp | 2021 - Present
    - Designed and implemented continuous ETL data pipelines processing 10TB daily using PySpark and Airflow.
    - Automated AWS Glue infrastructure with Terraform and Docker containers.

    Data Engineer | Data Analytics Inc | 2017 - 2021
    - Built data warehouse models in PostgreSQL and Redshift.
    - Created executive dashboards in Tableau and Power BI for financial analysis.

    EDUCATION
    Bachelor of Technology in Computer Science | B.Tech | 2013 - 2017

    CERTIFICATIONS
    AWS Certified Solutions Architect
    Certified Kubernetes Administrator (CKA)
    """

    profile = process_resume(sample_resume)
    import json
    print("Extracted Candidate Profile:")
    print(json.dumps({k: v for k, v in profile.items() if k != "profile_text"}, indent=2))
