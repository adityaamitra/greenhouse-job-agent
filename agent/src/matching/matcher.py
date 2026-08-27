import re

from sentence_transformers import SentenceTransformer, util


# ============================================================
# SEMANTIC MODEL
# ============================================================

MODEL_NAME = "all-MiniLM-L6-v2"

_model = None


def get_model() -> SentenceTransformer:
    global _model

    if _model is None:
        print(f"Loading semantic model: {MODEL_NAME}")

        _model = SentenceTransformer(
            MODEL_NAME
        )

    return _model


# ============================================================
# ROLE PROFILES
# ============================================================

ROLE_ALIGNMENT = {
    "software_engineer": {
        "software_engineer": 100,
        "backend_engineer": 88,
        "fullstack_engineer": 88,
        "frontend_engineer": 80,
        "systems_engineer": 75,
        "devops_engineer": 70,
        "production_support_engineer": 65,
        "ai_ml_engineer": 65,
    },

    "backend_engineer": {
        "backend_engineer": 100,
        "software_engineer": 90,
        "systems_engineer": 80,
        "fullstack_engineer": 80,
        "devops_engineer": 75,
        "production_support_engineer": 70,
        "ai_ml_engineer": 60,
        "frontend_engineer": 45,
    },

    "frontend_engineer": {
        "frontend_engineer": 100,
        "fullstack_engineer": 92,
        "software_engineer": 85,
        "backend_engineer": 55,
        "ai_ml_engineer": 50,
        "systems_engineer": 45,
        "devops_engineer": 40,
        "production_support_engineer": 40,
    },

    "fullstack_engineer": {
        "fullstack_engineer": 100,
        "software_engineer": 92,
        "frontend_engineer": 88,
        "backend_engineer": 88,
        "ai_ml_engineer": 60,
        "systems_engineer": 55,
        "devops_engineer": 50,
        "production_support_engineer": 45,
    },

    "ai_ml_engineer": {
        "ai_ml_engineer": 100,
        "software_engineer": 82,
        "backend_engineer": 75,
        "fullstack_engineer": 65,
        "systems_engineer": 60,
        "devops_engineer": 55,
        "frontend_engineer": 50,
        "production_support_engineer": 45,
    },

    "systems_engineer": {
        "systems_engineer": 100,
        "production_support_engineer": 92,
        "devops_engineer": 90,
        "backend_engineer": 78,
        "software_engineer": 75,
        "fullstack_engineer": 55,
        "ai_ml_engineer": 50,
        "frontend_engineer": 40,
    },

    "production_support_engineer": {
        "production_support_engineer": 100,
        "systems_engineer": 95,
        "devops_engineer": 88,
        "backend_engineer": 72,
        "software_engineer": 68,
        "fullstack_engineer": 52,
        "ai_ml_engineer": 45,
        "frontend_engineer": 40,
    },

    "devops_engineer": {
        "devops_engineer": 100,
        "systems_engineer": 95,
        "production_support_engineer": 88,
        "backend_engineer": 72,
        "software_engineer": 68,
        "fullstack_engineer": 52,
        "ai_ml_engineer": 48,
        "frontend_engineer": 40,
    },
}


def infer_job_profile(title: str) -> str:
    title = title.lower()

    if any(
        phrase in title
        for phrase in [
            "machine learning",
            "ml engineer",
            "ai engineer",
            "artificial intelligence",
            "generative ai",
            "genai",
        ]
    ):
        return "ai_ml_engineer"

    if any(
        phrase in title
        for phrase in [
            "production support",
            "application support",
        ]
    ):
        return "production_support_engineer"

    if any(
        phrase in title
        for phrase in [
            "devops",
            "site reliability",
            "sre",
        ]
    ):
        return "devops_engineer"

    if any(
        phrase in title
        for phrase in [
            "full stack",
            "full-stack",
        ]
    ):
        return "fullstack_engineer"

    if any(
        phrase in title
        for phrase in [
            "frontend",
            "front-end",
        ]
    ):
        return "frontend_engineer"

    if any(
        phrase in title
        for phrase in [
            "backend",
            "back-end",
        ]
    ):
        return "backend_engineer"

    if any(
        phrase in title
        for phrase in [
            "systems engineer",
            "system engineer",
        ]
    ):
        return "systems_engineer"

    return "software_engineer"


def get_role_score(
    job_profile: str,
    resume_name: str,
) -> float:

    profile_scores = ROLE_ALIGNMENT.get(
        job_profile,
        {},
    )

    return float(
        profile_scores.get(
            resume_name,
            50,
        )
    )


# ============================================================
# SKILL EXTRACTION
# ============================================================

SKILL_PATTERNS = {
    "Python": [
        r"\bpython\b",
    ],

    "Java": [
        r"\bjava\b",
    ],

    "JavaScript": [
        r"\bjavascript\b",
        r"\bjs\b",
    ],

    "TypeScript": [
        r"\btypescript\b",
    ],

    "Go": [
        r"\bgolang\b",
        r"\bgo language\b",
    ],

    "C++": [
        r"c\+\+",
    ],

    "Ruby": [
        r"\bruby\b",
    ],

    "React": [
        r"\breact\b",
        r"\breactjs\b",
        r"\breact\.js\b",
    ],

    "Node.js": [
        r"\bnode\.?js\b",
        r"\bnodejs\b",
    ],

    "FastAPI": [
        r"\bfastapi\b",
    ],

    "Flask": [
        r"\bflask\b",
    ],

    "REST APIs": [
        r"\brest\b",
        r"\brestful\b",
        r"\brest api",
        r"\brest APIs?\b",
    ],

    "GraphQL": [
        r"\bgraphql\b",
    ],

    "SQL": [
        r"\bsql\b",
    ],

    "PL/SQL": [
        r"\bpl/sql\b",
        r"\bplsql\b",
    ],

    "Oracle": [
        r"\boracle\b",
    ],

    "PostgreSQL": [
        r"\bpostgresql\b",
        r"\bpostgres\b",
    ],

    "MySQL": [
        r"\bmysql\b",
    ],

    "MongoDB": [
        r"\bmongodb\b",
    ],

    "Redis": [
        r"\bredis\b",
    ],

    "Qdrant": [
        r"\bqdrant\b",
    ],

    "IBM MQ": [
        r"\bibm mq\b",
    ],

    "WebLogic": [
        r"\bweblogic\b",
    ],

    "Kafka": [
        r"\bkafka\b",
    ],

    "RabbitMQ": [
        r"\brabbitmq\b",
    ],

    "Linux": [
        r"\blinux\b",
        r"\bred hat\b",
        r"\bubuntu\b",
    ],

    "Bash/Shell": [
        r"\bbash\b",
        r"\bshell scripting\b",
        r"\bshell script",
    ],

    "Docker": [
        r"\bdocker\b",
        r"\bcontainerization\b",
    ],

    "Kubernetes": [
        r"\bkubernetes\b",
        r"\bk8s\b",
    ],

    "AWS": [
        r"\baws\b",
        r"\bamazon web services\b",
    ],

    "GCP": [
        r"\bgcp\b",
        r"\bgoogle cloud\b",
    ],

    "Azure": [
        r"\bazure\b",
    ],

    "CI/CD": [
        r"\bci/cd\b",
        r"\bcontinuous integration\b",
        r"\bcontinuous delivery\b",
        r"\bcontinuous deployment\b",
    ],

    "GitHub Actions": [
        r"\bgithub actions\b",
    ],

    "Git": [
        r"\bgit\b",
        r"\bgithub\b",
    ],

    "ELK Stack": [
        r"\belk\b",
        r"\belasticsearch\b",
        r"\blogstash\b",
        r"\bkibana\b",
    ],

    "PyTorch": [
        r"\bpytorch\b",
    ],

    "TensorFlow": [
        r"\btensorflow\b",
    ],

    "Scikit-learn": [
        r"\bscikit-learn\b",
        r"\bsklearn\b",
    ],

    "LLMs": [
        r"\bllm\b",
        r"\bllms\b",
        r"\blarge language model",
    ],

    "RAG": [
        r"\brag\b",
        r"\bretrieval augmented generation\b",
    ],

    "LangChain": [
        r"\blangchain\b",
    ],

    "CrewAI": [
        r"\bcrewai\b",
    ],

    "Embeddings": [
        r"\bembedding\b",
        r"\bembeddings\b",
    ],

    "Vector Search": [
        r"\bvector search\b",
        r"\bvector database\b",
        r"\bvector db\b",
    ],

    "Terraform": [
        r"\bterraform\b",
    ],

    "Ansible": [
        r"\bansible\b",
    ],

    "Jenkins": [
        r"\bjenkins\b",
    ],

    "Prometheus": [
        r"\bprometheus\b",
    ],

    "Grafana": [
        r"\bgrafana\b",
    ],

    "System Design": [
        r"\bsystem design\b",
    ],

    "Distributed Systems": [
        r"\bdistributed system",
    ],

    "Microservices": [
        r"\bmicroservice",
    ],

    "Concurrency": [
        r"\bconcurrency\b",
        r"\bconcurrent\b",
    ],

    "Incident Response": [
        r"\bincident response\b",
        r"\bincident management\b",
    ],

    "Root Cause Analysis": [
        r"\broot cause analysis\b",
        r"\brca\b",
    ],

    "Observability": [
        r"\bobservability\b",
        r"\bmonitoring\b",
        r"\balerting\b",
    ],

    "Testing": [
        r"\bpytest\b",
        r"\bunit testing\b",
        r"\bunit tests\b",
    ],

    "Security": [
        r"\bsecurity\b",
        r"\bcompliance\b",
    ],
}


def extract_skills(text: str) -> set[str]:
    if not text:
        return set()

    skills = set()

    for skill, patterns in SKILL_PATTERNS.items():

        for pattern in patterns:

            if re.search(
                pattern,
                text,
                re.IGNORECASE,
            ):
                skills.add(skill)
                break

    return skills


def calculate_skill_score(
    job_skills: set[str],
    resume_skills: set[str],
) -> tuple[float, list[str], list[str]]:

    if not job_skills:
        return (
            50.0,
            [],
            [],
        )

    matched = sorted(
        job_skills.intersection(
            resume_skills
        )
    )

    missing = sorted(
        job_skills.difference(
            resume_skills
        )
    )

    score = (
        len(matched)
        / len(job_skills)
    ) * 100

    return (
        round(score, 2),
        matched,
        missing,
    )


# ============================================================
# SEMANTIC SIMILARITY
# ============================================================

def chunk_text(
    text: str,
    chunk_size: int = 120,
    overlap: int = 25,
) -> list[str]:

    if not text:
        return []

    words = text.split()

    if len(words) <= chunk_size:
        return [text]

    chunks = []

    start = 0

    while start < len(words):

        end = start + chunk_size

        chunk = " ".join(
            words[start:end]
        )

        if chunk:
            chunks.append(chunk)

        if end >= len(words):
            break

        start += (
            chunk_size - overlap
        )

    return chunks


def semantic_scores(
    job_text: str,
    resumes: dict[str, dict],
) -> dict[str, float]:

    model = get_model()

    job_chunks = chunk_text(
        job_text
    )

    if not job_chunks:
        return {
            name: 0.0
            for name in resumes
        }

    job_embeddings = model.encode(
        job_chunks,
        convert_to_tensor=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    scores = {}

    for resume_name, resume in resumes.items():

        resume_chunks = chunk_text(
            resume["text"]
        )

        if not resume_chunks:
            scores[resume_name] = 0.0
            continue

        resume_embeddings = model.encode(
            resume_chunks,
            convert_to_tensor=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        similarity_matrix = util.cos_sim(
            job_embeddings,
            resume_embeddings,
        )

        strongest = (
            similarity_matrix
            .max(dim=1)
            .values
            .cpu()
            .tolist()
        )

        strongest.sort(
            reverse=True
        )

        strongest = strongest[
            :min(5, len(strongest))
        ]

        raw_score = (
            sum(strongest)
            / len(strongest)
        ) * 100

        scores[resume_name] = round(
            raw_score,
            2,
        )

    return scores


def normalize_semantic_score(
    raw_score: float,
) -> float:
    """
    Convert typical cosine scores into a more useful 0-100
    component score.

    Rough calibration:

        25 -> 0
        35 -> 29
        45 -> 57
        50 -> 71
        55 -> 86
        60 -> 100
    """

    normalized = (
        (raw_score - 25)
        / 35
    ) * 100

    normalized = max(
        0.0,
        min(
            normalized,
            100.0,
        ),
    )

    return round(
        normalized,
        2,
    )


# ============================================================
# FINAL SCORING
# ============================================================

def get_route(
    score: float,
) -> str:

    if score >= 85:
        return "MANUAL_PRIORITY"

    if score >= 75:
        return "AGENT_ASSIST"

    return "SKIP"


def rank_resumes(
    job_title: str,
    job_text: str,
    resumes: dict[str, dict],
) -> dict:

    job_profile = infer_job_profile(
        job_title
    )

    job_skills = extract_skills(
        job_text
    )

    semantic_raw_scores = semantic_scores(
        job_text,
        resumes,
    )

    rankings = []

    for resume_name, resume in resumes.items():

        role_score = get_role_score(
            job_profile,
            resume_name,
        )

        resume_skills = extract_skills(
            resume["text"]
        )

        (
            skill_score,
            matched_skills,
            missing_skills,
        ) = calculate_skill_score(
            job_skills,
            resume_skills,
        )

        semantic_raw = (
            semantic_raw_scores[
                resume_name
            ]
        )

        semantic_score = (
            normalize_semantic_score(
                semantic_raw
            )
        )

        final_score = (
            role_score * 0.40
            + skill_score * 0.40
            + semantic_score * 0.20
        )

        final_score = round(
            final_score,
            2,
        )

        rankings.append(
            {
                "resume_name": resume_name,
                "filename": resume["filename"],

                "role_score": role_score,
                "skill_score": skill_score,

                "semantic_raw": semantic_raw,
                "semantic_score": semantic_score,

                "final_score": final_score,

                "matched_skills": matched_skills,
                "missing_skills": missing_skills,

                "route": get_route(
                    final_score
                ),
            }
        )

    rankings.sort(
        key=lambda item: item["final_score"],
        reverse=True,
    )

    return {
        "job_profile": job_profile,
        "job_skills": sorted(job_skills),
        "rankings": rankings,
    }
