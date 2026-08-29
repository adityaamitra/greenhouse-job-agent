from sentence_transformers import (
    SentenceTransformer,
    util,
)

from src.matching.requirement_extractor import (
    extract_requirements,
    extract_skills,
)

from src.matching.profile_classifier import (
    classify_job_profile,
)


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_NAME = (
    "all-MiniLM-L6-v2"
)

APPLICANT_YEARS_EXPERIENCE = (
    3
)


# ============================================================
# MANUAL PRIORITY
# ============================================================

MANUAL_PRIORITY_THRESHOLD = (
    85.0
)

MANUAL_MIN_CONFIDENCE = (
    75.0
)


# ============================================================
# FINAL JOB-FIT WEIGHTS
# ============================================================
#
# IMPORTANT:
#
# Role alignment is intentionally NOT part of job fit.
#
# It is used only for resume selection.
#
#
# Job fit:
#
#   Required coverage     45%
#   Preferred coverage    10%
#   Semantic similarity   30%
#   Experience            15%
#
#
# Missing components:
#
#   - contribute no points
#   - contribute no denominator
#   - reduce evidence confidence
#
# ============================================================

FIT_WEIGHTS = {
    "required": 45.0,
    "preferred": 10.0,
    "semantic": 30.0,
    "experience": 15.0,
}


# ============================================================
# RESUME-SELECTION WEIGHTS
# ============================================================
#
# Resume selection:
#
#   Role alignment        55%
#   Semantic similarity   25%
#   Required coverage     20%
#
#
# If required-skill evidence is unavailable, that component
# is excluded and Role + Semantic are renormalized.
#
# ============================================================

RESUME_SELECTION_WEIGHTS = {
    "role": 55.0,
    "semantic": 25.0,
    "required": 20.0,
}


_model = None


# ============================================================
# SEMANTIC MODEL
# ============================================================

def get_model() -> SentenceTransformer:

    global _model

    if _model is None:

        print(
            f"Loading semantic model: "
            f"{MODEL_NAME}",
            flush=True,
        )

        _model = (
            SentenceTransformer(
                MODEL_NAME
            )
        )

        print(
            f"Semantic model device: "
            f"{_model.device}",
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


# ============================================================
# PROFILE
# ============================================================

def infer_job_profile(
    title: str,
) -> str:

    return (
        classify_job_profile(
            title
        )
    )


def get_role_score(
    job_profile: str,
    resume_name: str,
) -> float:

    return float(
        ROLE_ALIGNMENT
        .get(
            job_profile,
            {},
        )
        .get(
            resume_name,
            50,
        )
    )


# ============================================================
# CHUNKING
# ============================================================

def chunk_text(
    text: str,
    chunk_size: int = 120,
    overlap: int = 25,
) -> list[str]:

    if not text:

        return []

    words = (
        text.split()
    )

    if len(
        words
    ) <= chunk_size:

        return [
            text
        ]

    chunks = []

    start = 0

    while start < len(
        words
    ):

        end = (
            start
            + chunk_size
        )

        chunk = (
            " ".join(
                words[
                    start:end
                ]
            )
        )

        if chunk:

            chunks.append(
                chunk
            )

        if end >= len(
            words
        ):

            break

        start += (
            chunk_size
            - overlap
        )

    return (
        chunks
    )


# ============================================================
# RESUME CACHE
# ============================================================

def prepare_resume_cache(
    resumes: dict[str, dict],
) -> dict[str, dict]:

    model = (
        get_model()
    )

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

        text = (
            resume[
                "text"
            ]
        )

        chunks = (
            chunk_text(
                text
            )
        )

        embeddings = (
            model.encode(
                chunks,
                convert_to_tensor=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        )

        skills = (
            extract_skills(
                text
            )
        )

        cache[
            resume_name
        ] = {
            "filename": (
                resume[
                    "filename"
                ]
            ),

            "text": (
                text
            ),

            "chunks": (
                chunks
            ),

            "embeddings": (
                embeddings
            ),

            "skills": (
                skills
            ),
        }

    print(
        "Resume cache ready.",
        flush=True,
    )

    return (
        cache
    )


# ============================================================
# REQUIREMENT GROUP MATCHING
# ============================================================

def group_is_satisfied(
    group_skills: list[str],
    resume_skills: set[str],
    min_matches: int = 1,
) -> tuple[
    bool,
    list[str],
    int,
]:

    unique_skills = sorted(
        set(
            group_skills
        )
    )

    matching_options = sorted(
        set(
            unique_skills
        )
        .intersection(
            resume_skills
        )
    )

    required_matches = max(
        1,
        min(
            int(
                min_matches
            ),
            len(
                unique_skills
            )
            if unique_skills
            else 1,
        ),
    )

    satisfied = (
        len(
            matching_options
        )
        >= required_matches
    )

    return (
        satisfied,
        matching_options,
        required_matches,
    )


# ============================================================
# REQUIREMENT SCORE
# ============================================================

def calculate_requirement_score(
    normal_skills: list[str],
    requirement_groups: list[dict],
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

    satisfied_count = (
        len(
            matched
        )
    )

    total_count = (
        len(
            normal_set
        )
    )

    group_results = []

    for group in (
        requirement_groups
    ):

        if (
            group.get(
                "section"
            )
            != section
        ):

            continue

        skills = (
            group.get(
                "skills",
                [],
            )
        )

        min_matches = (
            group.get(
                "min_matches",
                1,
            )
        )

        (
            satisfied,
            matching_options,
            required_matches,
        ) = group_is_satisfied(
            skills,
            resume_skills,
            min_matches,
        )

        total_count += (
            1
        )

        if satisfied:

            satisfied_count += (
                1
            )

        group_results.append(
            {
                "skills": (
                    skills
                ),

                "min_matches": (
                    required_matches
                ),

                "matched_count": (
                    len(
                        matching_options
                    )
                ),

                "satisfied": (
                    satisfied
                ),

                "matching_options": (
                    matching_options
                ),

                "missing_options": sorted(
                    set(
                        skills
                    )
                    - set(
                        matching_options
                    )
                ),

                "kind": (
                    group.get(
                        "kind",
                        "alternative",
                    )
                ),

                "text": (
                    group.get(
                        "text",
                        "",
                    )
                ),
            }
        )

    # --------------------------------------------------------
    # BACKWARD-COMPATIBLE RAW SCORE
    # --------------------------------------------------------
    #
    # We still return 100 here for an empty component because
    # existing callers expect a numeric score.
    #
    # The final V2.1 scoring model DOES NOT use that 100 when
    # no evidence exists. Availability is checked separately
    # and the missing component is excluded.
    # --------------------------------------------------------

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
    ) * 100.0

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
# REQUIREMENT UNIT COUNTS
# ============================================================

def count_requirement_units(
    normal_skills: list[str],
    requirement_groups: list[dict],
    section: str,
) -> int:

    return (
        len(
            set(
                normal_skills
            )
        )

        + sum(
            1

            for group
            in requirement_groups

            if (
                group.get(
                    "section"
                )
                == section
            )
        )
    )


def count_satisfied_groups(
    group_results: list[dict],
) -> int:

    return sum(
        1

        for group
        in group_results

        if (
            group.get(
                "satisfied",
                False,
            )
        )
    )


# ============================================================
# EXPERIENCE
# ============================================================

def get_required_experience_min(
    experience_mentions: list[dict],
):

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

        return (
            None
        )

    return max(
        mention.get(
            "min_years",
            0,
        )

        for mention
        in relevant_mentions
    )


def calculate_experience_score(
    experience_mentions: list[dict],
) -> float:

    required_minimum = (
        get_required_experience_min(
            experience_mentions
        )
    )

    # Raw compatibility score.
    #
    # Availability is handled separately during final scoring.

    if required_minimum is None:

        return (
            100.0
        )

    if (
        APPLICANT_YEARS_EXPERIENCE
        >= required_minimum
    ):

        return (
            100.0
        )

    difference = (
        required_minimum
        - APPLICANT_YEARS_EXPERIENCE
    )

    if difference <= 1:

        return (
            65.0
        )

    return (
        0.0
    )


# ============================================================
# SEMANTIC SCORE
# ============================================================

def calculate_semantic_score(
    job_text: str,
    resume_embeddings,
) -> float:

    model = (
        get_model()
    )

    job_chunks = (
        chunk_text(
            job_text
        )
    )

    if not job_chunks:

        return (
            0.0
        )

    job_embeddings = (
        model.encode(
            job_chunks,
            convert_to_tensor=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
    )

    matrix = (
        util.cos_sim(
            job_embeddings,
            resume_embeddings,
        )
    )

    strongest = (
        matrix
        .max(
            dim=1
        )
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
            len(
                strongest
            ),
        )
    ]

    raw_score = (
        sum(
            strongest
        )
        / len(
            strongest
        )
    ) * 100.0

    return round(
        raw_score,
        2,
    )


def normalize_semantic_score(
    raw_score: float,
) -> float:

    normalized = (
        (
            raw_score
            - 25.0
        )
        / 35.0
    ) * 100.0

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
# DYNAMIC WEIGHTED SCORE
# ============================================================

def calculate_dynamic_weighted_score(
    *,
    scores: dict,
    availability: dict,
    weights: dict,
) -> dict:
    """
    Evidence-normalized weighted score.

    Missing components are excluded rather than scored as
    perfect, zero, or neutral.

    Example:

        Required   = 100 @ 45
        Preferred  = unavailable
        Semantic   = 70  @ 30
        Experience = 100 @ 15

    active weight = 90

    final =
        (
            100*45
            + 70*30
            + 100*15
        )
        / 90
    """

    weighted_sum = (
        0.0
    )

    active_weight = (
        0.0
    )

    details = {}

    for component, weight in (
        weights.items()
    ):

        available = bool(
            availability.get(
                component,
                False,
            )
        )

        raw_score = float(
            scores.get(
                component,
                0.0,
            )
        )

        if available:

            weighted_value = (
                raw_score
                * weight
            )

            weighted_sum += (
                weighted_value
            )

            active_weight += (
                weight
            )

        else:

            weighted_value = (
                None
            )

        details[
            component
        ] = {
            "score": (
                raw_score
                if available
                else None
            ),

            "available": (
                available
            ),

            "weight": (
                float(
                    weight
                )
            ),

            "weighted_value": (
                weighted_value
            ),
        }

    if active_weight <= 0:

        final_score = (
            0.0
        )

    else:

        final_score = (
            weighted_sum
            / active_weight
        )

    total_weight = (
        sum(
            weights.values()
        )
    )

    if total_weight <= 0:

        confidence = (
            0.0
        )

    else:

        confidence = (
            active_weight
            / total_weight
            * 100.0
        )

    # Contribution in final 100-point score after
    # renormalization.

    contributions = {}

    for component, detail in (
        details.items()
    ):

        if (
            not detail[
                "available"
            ]
            or active_weight <= 0
        ):

            contributions[
                component
            ] = (
                0.0
            )

            continue

        contribution = (
            detail[
                "score"
            ]
            * detail[
                "weight"
            ]
            / active_weight
        )

        contributions[
            component
        ] = round(
            contribution,
            2,
        )

    return {
        "score": round(
            final_score,
            2,
        ),

        "confidence": round(
            confidence,
            2,
        ),

        "active_weight": round(
            active_weight,
            2,
        ),

        "total_weight": round(
            total_weight,
            2,
        ),

        "weighted_sum": round(
            weighted_sum,
            2,
        ),

        "components": (
            details
        ),

        "contributions": (
            contributions
        ),
    }


# ============================================================
# COMPONENT AVAILABILITY
# ============================================================

def get_component_availability(
    *,
    required_units: int,
    preferred_units: int,
    required_experience_min,
) -> dict:

    return {
        "required": (
            required_units
            > 0
        ),

        "preferred": (
            preferred_units
            > 0
        ),

        # Semantic similarity is available for every ranked
        # job/resume pair.
        "semantic": (
            True
        ),

        "experience": (
            required_experience_min
            is not None
        ),
    }


# ============================================================
# RESUME-SELECTION SCORE
# ============================================================

def calculate_resume_selection_score(
    *,
    role_score: float,
    semantic_score: float,
    required_score: float,
    required_available: bool,
) -> float:

    scores = {
        "role": (
            role_score
        ),

        "semantic": (
            semantic_score
        ),

        "required": (
            required_score
        ),
    }

    availability = {
        "role": (
            True
        ),

        "semantic": (
            True
        ),

        "required": (
            required_available
        ),
    }

    result = (
        calculate_dynamic_weighted_score(
            scores=(
                scores
            ),

            availability=(
                availability
            ),

            weights=(
                RESUME_SELECTION_WEIGHTS
            ),
        )
    )

    return (
        result[
            "score"
        ]
    )


# ============================================================
# FINAL JOB-FIT SCORE
# ============================================================

def calculate_job_fit_score(
    *,
    required_score: float,
    preferred_score: float,
    semantic_score: float,
    experience_score: float,
    required_available: bool,
    preferred_available: bool,
    experience_available: bool,
) -> dict:

    scores = {
        "required": (
            required_score
        ),

        "preferred": (
            preferred_score
        ),

        "semantic": (
            semantic_score
        ),

        "experience": (
            experience_score
        ),
    }

    availability = {
        "required": (
            required_available
        ),

        "preferred": (
            preferred_available
        ),

        "semantic": (
            True
        ),

        "experience": (
            experience_available
        ),
    }

    return (
        calculate_dynamic_weighted_score(
            scores=(
                scores
            ),

            availability=(
                availability
            ),

            weights=(
                FIT_WEIGHTS
            ),
        )
    )


# ============================================================
# ROUTING
# ============================================================

def get_route(
    final_score: float,
    confidence: float = 100.0,
    required_evidence: bool = True,
) -> str:
    """
    Manual Priority requires ALL THREE:

        fit >= 85
        confidence >= 75%
        required-skill evidence exists

    Otherwise the job remains eligible for AGENT_APPLY.
    """

    if (
        final_score
        >= MANUAL_PRIORITY_THRESHOLD

        and confidence
        >= MANUAL_MIN_CONFIDENCE

        and required_evidence
    ):

        return (
            "MANUAL_PRIORITY"
        )

    return (
        "AGENT_APPLY"
    )


def get_score_band(
    final_score: float,
) -> str:

    if final_score >= 90:

        return (
            "VERY_STRONG"
        )

    if final_score >= 85:

        return (
            "STRONG"
        )

    if final_score >= 75:

        return (
            "MODERATE"
        )

    if final_score >= 60:

        return (
            "WEAK"
        )

    return (
        "VERY_WEAK"
    )


# ============================================================
# EXPLANATION
# ============================================================

def build_score_explanation(
    *,
    final_score: float,
    confidence: float,
    selection_score: float,
    job_profile: str,
    resume_name: str,
    role_score: float,
    required_score: float,
    preferred_score: float,
    semantic_raw: float,
    semantic_score: float,
    experience_score: float,
    requirements: dict,
    experience_mentions: list[dict],
    matched_required: list[str],
    missing_required: list[str],
    required_groups: list[dict],
    matched_preferred: list[str],
    missing_preferred: list[str],
    preferred_groups: list[dict],
    fit_result: dict,
) -> dict:

    requirement_groups = (
        requirements.get(
            "requirement_groups"
        )
        or requirements.get(
            "alternative_groups",
            [],
        )
    )

    required_units = (
        count_requirement_units(
            requirements.get(
                "required_skills",
                [],
            ),
            requirement_groups,
            "required",
        )
    )

    preferred_units = (
        count_requirement_units(
            requirements.get(
                "preferred_skills",
                [],
            ),
            requirement_groups,
            "preferred",
        )
    )

    required_satisfied = (
        len(
            matched_required
        )
        + count_satisfied_groups(
            required_groups
        )
    )

    preferred_satisfied = (
        len(
            matched_preferred
        )
        + count_satisfied_groups(
            preferred_groups
        )
    )

    required_minimum = (
        get_required_experience_min(
            experience_mentions
        )
    )

    availability = (
        fit_result[
            "components"
        ]
    )

    required_available = (
        availability[
            "required"
        ][
            "available"
        ]
    )

    preferred_available = (
        availability[
            "preferred"
        ][
            "available"
        ]
    )

    experience_available = (
        availability[
            "experience"
        ][
            "available"
        ]
    )

    score_gate = (
        final_score
        >= MANUAL_PRIORITY_THRESHOLD
    )

    confidence_gate = (
        confidence
        >= MANUAL_MIN_CONFIDENCE
    )

    required_evidence_gate = (
        required_available
    )

    manual_ready = (
        score_gate
        and confidence_gate
        and required_evidence_gate
    )

    gate_failures = []

    if not score_gate:

        gate_failures.append(
            (
                f"fit below "
                f"{MANUAL_PRIORITY_THRESHOLD:.0f}"
            )
        )

    if not confidence_gate:

        gate_failures.append(
            (
                f"confidence below "
                f"{MANUAL_MIN_CONFIDENCE:.0f}%"
            )
        )

    if not required_evidence_gate:

        gate_failures.append(
            "no required-skill evidence"
        )

    unsatisfied_required_groups = [
        group

        for group
        in required_groups

        if not group.get(
            "satisfied",
            False,
        )
    ]

    unsatisfied_preferred_groups = [
        group

        for group
        in preferred_groups

        if not group.get(
            "satisfied",
            False,
        )
    ]

    warnings = []

    if not required_available:

        warnings.append(
            (
                "No required skill units were extracted; "
                "the required component is excluded from "
                "job-fit scoring and confidence is reduced."
            )
        )

    if not preferred_available:

        warnings.append(
            (
                "No preferred skill units were extracted; "
                "the preferred component is excluded from "
                "job-fit scoring and confidence is reduced."
            )
        )

    if not experience_available:

        warnings.append(
            (
                "No required experience minimum was extracted; "
                "the experience component is excluded from "
                "job-fit scoring and confidence is reduced."
            )
        )

    if (
        required_available
        and required_score < 60
    ):

        warnings.append(
            (
                "Required-skill coverage is below 60%."
            )
        )

    if experience_score == 65:

        warnings.append(
            (
                "Experience score is reduced because the "
                "minimum requirement is one year above "
                "the configured applicant experience."
            )
        )

    if (
        experience_available
        and experience_score == 0
    ):

        warnings.append(
            (
                "Experience component scored 0."
            )
        )

    if (
        final_score
        >= MANUAL_PRIORITY_THRESHOLD
        and not manual_ready
    ):

        warnings.append(
            (
                "Fit score is above the manual threshold, "
                "but the evidence gates prevent "
                "Manual Priority routing."
            )
        )

    contributions = (
        fit_result[
            "contributions"
        ]
    )

    # Preserve a familiar structure for main.py while making
    # role contribution explicitly zero in final job fit.

    weighted_contributions = {
        "role": (
            0.0
        ),

        "required": (
            contributions.get(
                "required",
                0.0,
            )
        ),

        "preferred": (
            contributions.get(
                "preferred",
                0.0,
            )
        ),

        "semantic": (
            contributions.get(
                "semantic",
                0.0,
            )
        ),

        "experience": (
            contributions.get(
                "experience",
                0.0,
            )
        ),
    }

    return {
        "job_profile": (
            job_profile
        ),

        "resume_name": (
            resume_name
        ),

        "score_band": (
            get_score_band(
                final_score
            )
        ),

        # ----------------------------------------------------
        # RESUME SELECTION
        # ----------------------------------------------------

        "resume_selection_score": (
            selection_score
        ),

        "resume_selection_weights": {
            "role": (
                RESUME_SELECTION_WEIGHTS[
                    "role"
                ]
            ),

            "semantic": (
                RESUME_SELECTION_WEIGHTS[
                    "semantic"
                ]
            ),

            "required": (
                RESUME_SELECTION_WEIGHTS[
                    "required"
                ]
            ),
        },

        # ----------------------------------------------------
        # JOB FIT
        # ----------------------------------------------------

        "manual_threshold": (
            MANUAL_PRIORITY_THRESHOLD
        ),

        "minimum_confidence": (
            MANUAL_MIN_CONFIDENCE
        ),

        "threshold_distance": round(
            final_score
            - MANUAL_PRIORITY_THRESHOLD,
            2,
        ),

        "confidence": (
            confidence
        ),

        "active_weight": (
            fit_result[
                "active_weight"
            ]
        ),

        "total_weight": (
            fit_result[
                "total_weight"
            ]
        ),

        "weights": {
            "role": 0.0,
            "required": (
                FIT_WEIGHTS[
                    "required"
                ]
            ),
            "preferred": (
                FIT_WEIGHTS[
                    "preferred"
                ]
            ),
            "semantic": (
                FIT_WEIGHTS[
                    "semantic"
                ]
            ),
            "experience": (
                FIT_WEIGHTS[
                    "experience"
                ]
            ),
        },

        "weighted_contributions": (
            weighted_contributions
        ),

        "weighted_total": (
            final_score
        ),

        "component_availability": {
            "required": (
                required_available
            ),

            "preferred": (
                preferred_available
            ),

            "semantic": (
                True
            ),

            "experience": (
                experience_available
            ),
        },

        # ----------------------------------------------------
        # MANUAL GATES
        # ----------------------------------------------------

        "score_gate": (
            score_gate
        ),

        "confidence_gate": (
            confidence_gate
        ),

        "required_evidence_gate": (
            required_evidence_gate
        ),

        "manual_ready": (
            manual_ready
        ),

        "gate_failures": (
            gate_failures
        ),

        # ----------------------------------------------------
        # REQUIREMENTS
        # ----------------------------------------------------

        "required_units": (
            required_units
        ),

        "required_satisfied": (
            required_satisfied
        ),

        "preferred_units": (
            preferred_units
        ),

        "preferred_satisfied": (
            preferred_satisfied
        ),

        "required_minimum_years": (
            required_minimum
        ),

        "applicant_years": (
            APPLICANT_YEARS_EXPERIENCE
        ),

        "semantic_raw": (
            semantic_raw
        ),

        "semantic_normalized": (
            semantic_score
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

        "unsatisfied_required_groups": (
            unsatisfied_required_groups
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

        "unsatisfied_preferred_groups": (
            unsatisfied_preferred_groups
        ),

        "warnings": (
            warnings
        ),
    }


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
    """
    V2.1 production matcher.

    Two distinct decisions are made:

    1. Resume selection
       Which of the 8 master resumes best represents the
       applicant for this job?

    2. Job fit
       How strong is the applicant/job match based only on
       available evidence?

    rankings[0] is the resume selected by the resume-selection
    score, NOT simply the candidate with the largest job-fit
    score.
    """

    job_profile = (
        infer_job_profile(
            job_title
        )
    )

    requirements = (
        extract_requirements(
            job_content
        )
    )

    requirement_groups = (
        requirements.get(
            "requirement_groups"
        )
        or requirements.get(
            "alternative_groups",
            [],
        )
    )

    required_units = (
        count_requirement_units(
            requirements.get(
                "required_skills",
                [],
            ),
            requirement_groups,
            "required",
        )
    )

    preferred_units = (
        count_requirement_units(
            requirements.get(
                "preferred_skills",
                [],
            ),
            requirement_groups,
            "preferred",
        )
    )

    required_experience_min = (
        get_required_experience_min(
            experience_mentions
        )
    )

    component_availability = (
        get_component_availability(
            required_units=(
                required_units
            ),

            preferred_units=(
                preferred_units
            ),

            required_experience_min=(
                required_experience_min
            ),
        )
    )

    experience_score = (
        calculate_experience_score(
            experience_mentions
        )
    )

    rankings = []

    # ========================================================
    # SCORE EACH RESUME
    # ========================================================

    for (
        resume_name,
        resume,
    ) in resume_cache.items():

        role_score = (
            get_role_score(
                job_profile,
                resume_name,
            )
        )

        resume_skills = (
            resume[
                "skills"
            ]
        )

        # ----------------------------------------------------
        # REQUIRED
        # ----------------------------------------------------

        (
            required_score,
            matched_required,
            missing_required,
            required_groups,
        ) = calculate_requirement_score(
            requirements.get(
                "required_skills",
                [],
            ),
            requirement_groups,
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
            requirements.get(
                "preferred_skills",
                [],
            ),
            requirement_groups,
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

        # ====================================================
        # RESUME SELECTION
        # ====================================================

        selection_score = (
            calculate_resume_selection_score(
                role_score=(
                    role_score
                ),

                semantic_score=(
                    semantic_score
                ),

                required_score=(
                    required_score
                ),

                required_available=(
                    component_availability[
                        "required"
                    ]
                ),
            )
        )

        # ====================================================
        # JOB FIT
        # ====================================================

        fit_result = (
            calculate_job_fit_score(
                required_score=(
                    required_score
                ),

                preferred_score=(
                    preferred_score
                ),

                semantic_score=(
                    semantic_score
                ),

                experience_score=(
                    experience_score
                ),

                required_available=(
                    component_availability[
                        "required"
                    ]
                ),

                preferred_available=(
                    component_availability[
                        "preferred"
                    ]
                ),

                experience_available=(
                    component_availability[
                        "experience"
                    ]
                ),
            )
        )

        final_score = (
            fit_result[
                "score"
            ]
        )

        confidence = (
            fit_result[
                "confidence"
            ]
        )

        route = (
            get_route(
                final_score,
                confidence,
                component_availability[
                    "required"
                ],
            )
        )

        explanation = (
            build_score_explanation(
                final_score=(
                    final_score
                ),

                confidence=(
                    confidence
                ),

                selection_score=(
                    selection_score
                ),

                job_profile=(
                    job_profile
                ),

                resume_name=(
                    resume_name
                ),

                role_score=(
                    role_score
                ),

                required_score=(
                    required_score
                ),

                preferred_score=(
                    preferred_score
                ),

                semantic_raw=(
                    semantic_raw
                ),

                semantic_score=(
                    semantic_score
                ),

                experience_score=(
                    experience_score
                ),

                requirements=(
                    requirements
                ),

                experience_mentions=(
                    experience_mentions
                ),

                matched_required=(
                    matched_required
                ),

                missing_required=(
                    missing_required
                ),

                required_groups=(
                    required_groups
                ),

                matched_preferred=(
                    matched_preferred
                ),

                missing_preferred=(
                    missing_preferred
                ),

                preferred_groups=(
                    preferred_groups
                ),

                fit_result=(
                    fit_result
                ),
            )
        )

        rankings.append(
            {
                "resume_name": (
                    resume_name
                ),

                "filename": (
                    resume[
                        "filename"
                    ]
                ),

                # --------------------------------------------
                # RESUME SELECTION
                # --------------------------------------------

                "selection_score": (
                    selection_score
                ),

                "role_score": (
                    role_score
                ),

                # --------------------------------------------
                # FIT COMPONENTS
                # --------------------------------------------

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

                # --------------------------------------------
                # FINAL FIT
                # --------------------------------------------

                "final_score": (
                    final_score
                ),

                "confidence": (
                    confidence
                ),

                "route": (
                    route
                ),

                # --------------------------------------------
                # REQUIREMENT DETAILS
                # --------------------------------------------

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

                "explanation": (
                    explanation
                ),
            }
        )

    # ========================================================
    # IMPORTANT:
    #
    # Sort by RESUME-SELECTION score.
    #
    # rankings[0] therefore means:
    #
    #     best resume to use for this job
    #
    # not:
    #
    #     resume that happens to maximize the fit formula
    #
    # ========================================================

    rankings.sort(
        key=lambda item: (
            item[
                "selection_score"
            ],
            item[
                "final_score"
            ],
        ),
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

        "component_availability": (
            component_availability
        ),

        "rankings": (
            rankings
        ),
    }
