from sentence_transformers import SentenceTransformer, util

from src.matching.requirement_extractor import (
    extract_requirements,
    extract_skills,
)


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_NAME = "all-MiniLM-L6-v2"

APPLICANT_YEARS_EXPERIENCE = 3

_model = None


# ============================================================
# SEMANTIC MODEL
# ============================================================

def get_model() -> SentenceTransformer:
    """
    Load the local semantic model once.
    """

    global _model

    if _model is None:

        print(
            f"Loading semantic model: {MODEL_NAME}",
            flush=True,
        )

        _model = SentenceTransformer(
            MODEL_NAME
        )

        print(
            f"Semantic model device: {_model.device}",
            flush=True,
        )

    return _model


# ============================================================
# ROLE ALIGNMENT
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

    normalized = title.lower()

    if any(
        phrase in normalized
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
        phrase in normalized
        for phrase in [
            "production support",
            "application support",
        ]
    ):
        return "production_support_engineer"

    if any(
        phrase in normalized
        for phrase in [
            "devops",
            "site reliability",
            "sre",
        ]
    ):
        return "devops_engineer"

    if any(
        phrase in normalized
        for phrase in [
            "full stack",
            "full-stack",
        ]
    ):
        return "fullstack_engineer"

    if any(
        phrase in normalized
        for phrase in [
            "frontend",
            "front-end",
        ]
    ):
        return "frontend_engineer"

    if any(
        phrase in normalized
        for phrase in [
            "backend",
            "back-end",
        ]
    ):
        return "backend_engineer"

    if any(
        phrase in normalized
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

    return float(
        ROLE_ALIGNMENT
        .get(job_profile, {})
        .get(resume_name, 50)
    )


# ============================================================
# TEXT CHUNKING
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


# ============================================================
# RESUME CACHE
# ============================================================

def prepare_resume_cache(
    resumes: dict[str, dict],
) -> dict[str, dict]:
    """
    Prepare each resume ONCE.

    We cache:
        - extracted skills
        - chunks
        - semantic embeddings

    This prevents re-encoding the same resumes for every job.
    """

    model = get_model()

    cache = {}

    print()
    print(
        "Preparing resume semantic cache...",
        flush=True,
    )

    for index, (
        resume_name,
        resume,
    ) in enumerate(
        resumes.items(),
        start=1,
    ):

        print(
            f"  [{index}/{len(resumes)}] "
            f"{resume_name}",
            flush=True,
        )

        text = resume[
            "text"
        ]

        chunks = chunk_text(
            text
        )

        embeddings = model.encode(
            chunks,
            convert_to_tensor=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        skills = extract_skills(
            text
        )

        cache[
            resume_name
        ] = {
            "filename": resume[
                "filename"
            ],

            "text": text,

            "chunks": chunks,

            "embeddings": embeddings,

            "skills": skills,
        }

    print(
        "Resume cache ready.",
        flush=True,
    )

    return cache


# ============================================================
# REQUIREMENT SCORING
# ============================================================

def group_is_satisfied(
    group_skills: list[str],
    resume_skills: set[str],
) -> tuple[bool, list[str]]:

    matches = sorted(
        set(
            group_skills
        ).intersection(
            resume_skills
        )
    )

    return (
        bool(matches),
        matches,
    )


def calculate_requirement_score(
    normal_skills: list[str],
    alternative_groups: list[dict],
    resume_skills: set[str],
    section: str,
) -> tuple[
    float,
    list[str],
    list[str],
    list[dict],
]:

    normal_set = set(
        normal_skills
    )

    matched = sorted(
        normal_set.intersection(
            resume_skills
        )
    )

    missing = sorted(
        normal_set.difference(
            resume_skills
        )
    )

    satisfied_count = len(
        matched
    )

    total_count = len(
        normal_set
    )

    group_results = []

    for group in alternative_groups:

        if group.get(
            "section"
        ) != section:

            continue

        skills = group.get(
            "skills",
            [],
        )

        (
            satisfied,
            matching_options,
        ) = group_is_satisfied(
            skills,
            resume_skills,
        )

        total_count += 1

        if satisfied:
            satisfied_count += 1

        group_results.append(
            {
                "skills": skills,

                "satisfied": (
                    satisfied
                ),

                "matching_options": (
                    matching_options
                ),

                "text": group.get(
                    "text",
                    "",
                ),
            }
        )

    if total_count == 0:

        return (
            100.0,
            matched,
            missing,
            group_results,
        )

    score = (
        satisfied_count
        / total_count
    ) * 100

    return (
        round(
            score,
            2,
        ),
        matched,
        missing,
        group_results,
    )


# ============================================================
# EXPERIENCE SCORE
# ============================================================

def calculate_experience_score(
    experience_mentions: list[dict],
) -> float:

    relevant_mentions = [
        mention
        for mention
        in experience_mentions
        if not mention.get(
            "preferred",
            False,
        )
    ]

    if not relevant_mentions:

        return 100.0

    required_minimum = max(
        mention.get(
            "min_years",
            0,
        )
        for mention
        in relevant_mentions
    )

    if (
        APPLICANT_YEARS_EXPERIENCE
        >= required_minimum
    ):
        return 100.0

    difference = (
        required_minimum
        - APPLICANT_YEARS_EXPERIENCE
    )

    if difference <= 1:
        return 65.0

    return 0.0


# ============================================================
# SEMANTIC SCORE
# ============================================================

def calculate_semantic_score(
    job_text: str,
    resume_embeddings,
) -> float:
    """
    Encode ONLY the job.

    Resume embeddings are already cached.
    """

    model = get_model()

    job_chunks = chunk_text(
        job_text
    )

    if not job_chunks:
        return 0.0

    job_embeddings = model.encode(
        job_chunks,
        convert_to_tensor=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    matrix = util.cos_sim(
        job_embeddings,
        resume_embeddings,
    )

    strongest = (
        matrix
        .max(dim=1)
        .values
        .cpu()
        .tolist()
    )

    strongest.sort(
        reverse=True
    )

    strongest = strongest[
        :min(
            5,
            len(strongest),
        )
    ]

    raw_score = (
        sum(strongest)
        / len(strongest)
    ) * 100

    return round(
        raw_score,
        2,
    )


def normalize_semantic_score(
    raw_score: float,
) -> float:

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
# ROUTING
# ============================================================

def get_route(
    final_score: float,
) -> str:

    if final_score >= 85:
        return "MANUAL_PRIORITY"

    return "AGENT_APPLY"


# ============================================================
# FINAL MATCHER
# ============================================================

def rank_resumes(
    job_title: str,
    job_content: str,
    job_text: str,
    experience_mentions: list[dict],
    resume_cache: dict[str, dict],
) -> dict:

    job_profile = infer_job_profile(
        job_title
    )

    requirements = extract_requirements(
        job_content
    )

    experience_score = (
        calculate_experience_score(
            experience_mentions
        )
    )

    rankings = []

    for (
        resume_name,
        resume,
    ) in resume_cache.items():

        # ----------------------------------------------------
        # ROLE
        # ----------------------------------------------------

        role_score = get_role_score(
            job_profile,
            resume_name,
        )

        resume_skills = resume[
            "skills"
        ]

        # ----------------------------------------------------
        # REQUIRED
        # ----------------------------------------------------

        (
            required_score,
            matched_required,
            missing_required,
            required_groups,
        ) = calculate_requirement_score(
            requirements[
                "required_skills"
            ],
            requirements[
                "alternative_groups"
            ],
            resume_skills,
            "required",
        )

        # ----------------------------------------------------
        # PREFERRED
        # ----------------------------------------------------

        (
            preferred_score,
            matched_preferred,
            missing_preferred,
            preferred_groups,
        ) = calculate_requirement_score(
            requirements[
                "preferred_skills"
            ],
            requirements[
                "alternative_groups"
            ],
            resume_skills,
            "preferred",
        )

        # ----------------------------------------------------
        # SEMANTIC
        # ----------------------------------------------------

        semantic_raw = (
            calculate_semantic_score(
                job_text,
                resume[
                    "embeddings"
                ],
            )
        )

        semantic_score = (
            normalize_semantic_score(
                semantic_raw
            )
        )

        # ----------------------------------------------------
        # FINAL
        # ----------------------------------------------------

        final_score = (
            role_score * 0.25
            + required_score * 0.35
            + preferred_score * 0.10
            + semantic_score * 0.20
            + experience_score * 0.10
        )

        final_score = round(
            final_score,
            2,
        )

        rankings.append(
            {
                "resume_name": (
                    resume_name
                ),

                "filename": resume[
                    "filename"
                ],

                "role_score": (
                    role_score
                ),

                "required_score": (
                    required_score
                ),

                "preferred_score": (
                    preferred_score
                ),

                "semantic_raw": (
                    semantic_raw
                ),

                "semantic_score": (
                    semantic_score
                ),

                "experience_score": (
                    experience_score
                ),

                "final_score": (
                    final_score
                ),

                "route": get_route(
                    final_score
                ),

                "matched_required": (
                    matched_required
                ),

                "missing_required": (
                    missing_required
                ),

                "required_groups": (
                    required_groups
                ),

                "matched_preferred": (
                    matched_preferred
                ),

                "missing_preferred": (
                    missing_preferred
                ),

                "preferred_groups": (
                    preferred_groups
                ),
            }
        )

    rankings.sort(
        key=lambda item: item[
            "final_score"
        ],
        reverse=True,
    )

    return {
        "job_profile": (
            job_profile
        ),

        "requirements": (
            requirements
        ),

        "experience_score": (
            experience_score
        ),

        "rankings": rankings,
    }
