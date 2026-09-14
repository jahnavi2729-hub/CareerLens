"""
CareerLens Resume Skill Extractor Module
----------------------------------------
Adapts canonical skill extraction logic with enhanced patterns including:
- Software, Data Science, AI/ML (Generative AI, LLM, Computer Vision, Deep Learning)
- Cloud, DevOps, Software Architecture, Automation
- Operations, Customer Support, BPO, Healthcare RCM
- Finance, HR, Sales, Management
Extracts canonical skill profiles from candidate resumes and job texts.
"""

import re
from typing import Dict, List, Any


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").lower()).strip()


def _make_patterns(*patterns: str) -> List[re.Pattern]:
    return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]


SKILL_PATTERNS = [
    # AI, Machine Learning & Data Science
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

    # Software Engineering & Web Development
    ("Python", _make_patterns(r"\bpython\b", r"\bpy\b")),
    ("Java", _make_patterns(r"\bjava\b", r"\bjdk\b", r"\bspring\s*boot\b")),
    ("C", _make_patterns(r"(?<![A-Za-z0-9#+])c(?![A-Za-z0-9#+])")),
    ("C++", _make_patterns(r"(?:\bc\+\+|\bc\s*\+\s*\+)")),
    ("C#", _make_patterns(r"\b(c#|c\s*sharp|\.net)\b")),
    ("JavaScript", _make_patterns(r"\bjavascript\b", r"\bjs\b", r"\becmascript\b")),
    ("TypeScript", _make_patterns(r"\btypescript\b", r"\bts\b")),
    ("Go", _make_patterns(r"\bgolang\b", r"\bgo\b")),
    ("Rust", _make_patterns(r"\brust\b")),
    ("PHP", _make_patterns(r"\bphp\b", r"\blaravel\b")),
    ("R", _make_patterns(r"(?<![A-Za-z0-9])r(?![A-Za-z0-9])", r"\brstudio\b")),
    ("Kotlin", _make_patterns(r"\bkotlin\b")),
    ("Swift", _make_patterns(r"\bswift\b")),
    ("HTML", _make_patterns(r"\bhtml5?\b")),
    ("CSS", _make_patterns(r"\bcss3?\b")),
    ("Bootstrap", _make_patterns(r"\bbootstrap\b", r"\btailwind\b")),
    ("React", _make_patterns(r"\breact\b", r"\breactjs\b", r"\bnext\.?js\b")),
    ("Angular", _make_patterns(r"\bangular\b")),
    ("Vue", _make_patterns(r"\bvue\b", r"\bvuejs\b")),
    ("Node.js", _make_patterns(r"\bnode(?:\.js|js)?\b", r"\bexpress(?:\.js)?\b")),
    ("REST API", _make_patterns(r"\brest\s*api\b", r"\brestful\b")),
    ("GraphQL", _make_patterns(r"\bgraphql\b")),
    ("Microservices", _make_patterns(r"\bmicroservices?\b")),
    ("Software Architecture", _make_patterns(r"\bsoftware\s*architecture\b", r"\bsystem\s*architecture\b", r"\bsolutions?\s*architecture\b")),
    ("System Design", _make_patterns(r"\bsystem\s*design\b", r"\bscalable\s*systems?\b")),
    ("Data Structures", _make_patterns(r"\bdata\s*structures?\b", r"\bdsa\b")),
    ("Algorithms", _make_patterns(r"\balgorithms?\b")),
    ("Debugging & Support", _make_patterns(r"\bdebugging\b", r"\btroubleshooting\b")),

    # Databases
    ("SQL", _make_patterns(r"(?<![A-Za-z0-9])sql(?![A-Za-z0-9])")),
    ("MySQL", _make_patterns(r"\bmysql\b")),
    ("PostgreSQL", _make_patterns(r"\bpostgres(?:ql)?\b")),
    ("MongoDB", _make_patterns(r"\bmongodb\b", r"\bnosql\b")),
    ("Oracle", _make_patterns(r"\boracle\b")),
    ("Redis", _make_patterns(r"\bredis\b")),

    # Cloud, DevOps & Infrastructure
    ("DevOps", _make_patterns(r"\bdevops\b")),
    ("Cloud Computing", _make_patterns(r"\bcloud\s*computing\b", r"\bcloud\s*infrastructure\b", r"\bcloud\s*solutions?\b")),
    ("AWS", _make_patterns(r"\baws\b", r"\bamazon\s*web\s*services\b")),
    ("Azure", _make_patterns(r"\bazure\b")),
    ("GCP", _make_patterns(r"\bgcp\b", r"\bgoogle\s*cloud\b")),
    ("Docker", _make_patterns(r"\bdocker\b", r"\bcontaineri[sz]ation\b")),
    ("Kubernetes", _make_patterns(r"\bkubernetes\b", r"\bk8s\b")),
    ("CI/CD", _make_patterns(r"\bci/cd\b", r"\bcontinuous\s*integration\b", r"\bcontinuous\s*delivery\b")),
    ("Automation Testing / QA", _make_patterns(r"\bautomation\s*testing\b", r"\btest\s*automation\b", r"\bqa\s*automation\b", r"\bselenium\b")),
    ("Git", _make_patterns(r"\bgit\b", r"\bgithub\b", r"\bgitlab\b")),
    ("Linux", _make_patterns(r"\blinux\b", r"\bubuntu\b", r"\bshell\s*scripting\b")),
    ("Cyber Security", _make_patterns(r"\bcyber\s*security\b", r"\binformation\s*security\b", r"\bvapt\b")),
    ("Networking", _make_patterns(r"\bnetworking\b", r"\btcp/ip\b", r"\brouting\b")),

    # Business, Finance, Management & HR
    ("Sales", _make_patterns(r"\bsales\b", r"\blead\s*generation\b", r"\bbusiness\s*development\b")),
    ("Operations", _make_patterns(r"\boperations?\b", r"\bprocess\s*improvement\b", r"\bsupply\s*chain\b", r"\blogistics\b")),
    ("Project Management", _make_patterns(r"\bproject\s*management\b", r"\bproject\s*coordination\b", r"\bagile\b", r"\bscrum\b")),
    ("Jira / Agile Tools", _make_patterns(r"\bjira\b", r"\bconfluence\b")),
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

    # Customer Support, BPO & Healthcare Operations
    ("Customer Support", _make_patterns(r"\bcustomer\s*support\b", r"\bcustomer\s*service\b", r"\bclient\s*support\b")),
    ("BPO / Voice Process", _make_patterns(r"\bbpo\b", r"\bvoice\s*process\b", r"\binternational\s*voice\s*process\b", r"\bcall\s*center\b")),
    ("Healthcare RCM / Billing", _make_patterns(r"\bus\s*healthcare\b", r"\bdenial\s*management\b", r"\bar\s*calling\b", r"\brcm\b", r"\brevenue\s*cycle\b")),

    # Engineering, Healthcare, Design
    ("AutoCAD", _make_patterns(r"\bauto\s*cad\b", r"\bautocad\b")),
    ("SolidWorks", _make_patterns(r"\bsolidworks\b", r"\bsolid\s*works\b")),
    ("CATIA", _make_patterns(r"\bcatia\b")),
    ("ANSYS", _make_patterns(r"\bansys\b", r"\bfea\b", r"\bfinite\s*element\b")),
    ("Manufacturing", _make_patterns(r"\bmanufacturing\b", r"\bproduction\b", r"\bquality\s*control\b")),
    ("Civil Engineering", _make_patterns(r"\bcivil\s*engineering\b", r"\bconstruction\b", r"\bstructural\s*design\b")),
    ("Structural Analysis", _make_patterns(r"\bstructural\s*analysis\b", r"\brcc\b", r"\bstaad\b")),
    ("Embedded Systems", _make_patterns(r"\bembedded\s*systems?\b", r"\bmicrocontrollers?\b", r"\barduino\b")),
    ("VLSI", _make_patterns(r"\bvlsi\b", r"\bverilog\b", r"\bvhdl\b")),
    ("MATLAB", _make_patterns(r"\bmatlab\b", r"\bsimulink\b")),
    ("Clinical Care", _make_patterns(r"\bclinical\b", r"\bpatient\s*care\b", r"\bnursing\b")),
    ("Pharmacology", _make_patterns(r"\bpharmacology\b", r"\bpharmacy\b", r"\bpharmacovigilance\b")),
    ("Compliance", _make_patterns(r"\bcompliance\b", r"\bregulatory\b", r"\bdue\s*diligence\b")),
    ("UI/UX Design", _make_patterns(r"\bui/ux\b", r"\buser\s*experience\b", r"\buser\s*interface\b")),
    ("Figma", _make_patterns(r"\bfigma\b")),
    ("Adobe Creative Suite", _make_patterns(r"\bphotoshop\b", r"\billustrator\b", r"\badobe\b")),
]


EDUCATION_PATTERNS = {
    "B.Tech": _make_patterns(r"\bb\.?\s*tech\b", r"\bbachelor\s*of\s*technology\b", r"\bbe\b", r"\bb\.?\s*e\.?\b"),
    "B.Sc": _make_patterns(r"\bb\.?\s*sc\b", r"\bbachelor\s*of\s*science\b"),
    "B.Com": _make_patterns(r"\bb\.?\s*com\b", r"\bbachelor\s*of\s*commerce\b"),
    "BBA": _make_patterns(r"\bbba\b", r"\bbachelor\s*of\s*business\s*administration\b"),
    "MBA": _make_patterns(r"\bmba\b", r"\bmaster\s*of\s*business\s*administration\b", r"\bpgdm\b"),
    "M.Com": _make_patterns(r"\bm\.?\s*com\b", r"\bmaster\s*of\s*commerce\b"),
    "M.Tech": _make_patterns(r"\bm\.?\s*tech\b", r"\bmaster\s*of\s*technology\b"),
    "LLB": _make_patterns(r"\bllb\b", r"\bbb\.?\s*llb\b", r"\blaw\b"),
    "MBBS": _make_patterns(r"\bmbbs\b"),
    "B.Pharm": _make_patterns(r"\bb\.?\s*pharm\b", r"\bbachelor\s*of\s*pharmacy\b"),
}


def extract_skills_from_text(raw_text: str) -> List[str]:
    """
    Extracts canonical skill names from unformatted resume or job text.
    """
    if not raw_text or not isinstance(raw_text, str):
        return []
    text = str(raw_text)
    detected_skills = []
    for skill_name, patterns in SKILL_PATTERNS:
        if any(pattern.search(text) for pattern in patterns):
            if skill_name not in detected_skills:
                detected_skills.append(skill_name)
    return detected_skills


def extract_resume_profile(resume_text: str) -> Dict[str, Any]:
    """
    Extracts full structured profile (skills, degree, experience years) from resume text.
    """
    raw_text = str(resume_text or "")
    norm_text = _normalize_text(raw_text)

    skills = extract_skills_from_text(raw_text)

    # Degree detection
    education = []
    for deg, patterns in EDUCATION_PATTERNS.items():
        if any(p.search(raw_text) for p in patterns):
            education.append(deg)

    # Experience years detection
    exp_years = []
    for match in re.finditer(r"\b(\d{1,2})(?:\+)?\s*(?:years?|yrs?)\b", norm_text):
        try:
            exp_years.append(int(match.group(1)))
        except ValueError:
            pass

    return {
        "skills": skills,
        "skill_count": len(skills),
        "education": education,
        "experience_years": max(exp_years) if exp_years else 0,
    }
