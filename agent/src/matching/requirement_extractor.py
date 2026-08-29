import html
import re

from bs4 import BeautifulSoup


# ============================================================
# SKILLS
# ============================================================

SKILL_PATTERNS = {
    # --------------------------------------------------------
    # LANGUAGES
    # --------------------------------------------------------

    "Python": [
        r"\bpython\b",
    ],

    "Java": [
        r"\bjava\b",
    ],

    "JavaScript": [
        r"\bjavascript\b",
    ],

    "TypeScript": [
        r"\btypescript\b",
    ],

    # Avoid generic \bgo\b because of phrases such as
    # "go to market".
    "Go": [
        r"\bgolang\b",
        r"\bgo\s+language\b",
        r"\bgo\s+programming\b",
    ],

    "C++": [
        r"c\+\+",
    ],

    "C#": [
        r"\bc#",
        r"\bc\s*sharp\b",
    ],

    "Ruby": [
        r"\bruby\b",
    ],

    "Rust": [
        r"\brust\b",
    ],

    "Kotlin": [
        r"\bkotlin\b",
    ],

    "Scala": [
        r"\bscala\b",
    ],

    # --------------------------------------------------------
    # FRONTEND
    # --------------------------------------------------------

    "React": [
        r"\breact\b",
        r"\breactjs\b",
        r"\breact\.js\b",
    ],

    "Next.js": [
        r"\bnext\.?js\b",
        r"\bnextjs\b",
    ],

    "Angular": [
        r"\bangular\b",
    ],

    "Vue": [
        r"\bvue\b",
        r"\bvue\.js\b",
        r"\bvuejs\b",
    ],

    # --------------------------------------------------------
    # BACKEND
    # --------------------------------------------------------

    "Node.js": [
        r"\bnode\.?js\b",
        r"\bnodejs\b",
    ],

    "Spring Boot": [
        r"\bspring boot\b",
    ],

    "FastAPI": [
        r"\bfastapi\b",
    ],

    "Flask": [
        r"\bflask\b",
    ],

    "Django": [
        r"\bdjango\b",
    ],

    "REST APIs": [
        r"\brest\b",
        r"\brestful\b",
        r"\brest api",
        r"\brestful api",
    ],

    "GraphQL": [
        r"\bgraphql\b",
    ],

    "gRPC": [
        r"\bgrpc\b",
    ],

    # --------------------------------------------------------
    # DATABASES
    # --------------------------------------------------------

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

    "DynamoDB": [
        r"\bdynamodb\b",
    ],

    "Cassandra": [
        r"\bcassandra\b",
    ],

    "Snowflake": [
        r"\bsnowflake\b",
    ],

    "BigQuery": [
        r"\bbigquery\b",
    ],

    "Qdrant": [
        r"\bqdrant\b",
    ],

    # --------------------------------------------------------
    # MESSAGING / MIDDLEWARE
    # --------------------------------------------------------

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

    "SQS": [
        r"\bamazon sqs\b",
        r"\baws sqs\b",
        r"\bsqs\b",
    ],

    "SNS": [
        r"\bamazon sns\b",
        r"\baws sns\b",
        r"\bsns\b",
    ],

    # --------------------------------------------------------
    # OS / SCRIPTING
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # CLOUD / DEVOPS
    # --------------------------------------------------------

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

    "Terraform": [
        r"\bterraform\b",
    ],

    "Ansible": [
        r"\bansible\b",
    ],

    "Jenkins": [
        r"\bjenkins\b",
    ],

    # --------------------------------------------------------
    # OBSERVABILITY
    # --------------------------------------------------------

    "ELK Stack": [
        r"\belk\b",
        r"\belasticsearch\b",
        r"\blogstash\b",
        r"\bkibana\b",
    ],

    "Prometheus": [
        r"\bprometheus\b",
    ],

    "Grafana": [
        r"\bgrafana\b",
    ],

    "Observability": [
        r"\bobservability\b",
        r"\bmonitoring\b",
        r"\balerting\b",
    ],

    # --------------------------------------------------------
    # ML / DATA
    # --------------------------------------------------------

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

    "Pandas": [
        r"\bpandas\b",
    ],

    "NumPy": [
        r"\bnumpy\b",
    ],

    "Spark": [
        r"\bapache spark\b",
        r"\bspark\b",
    ],

    "Databricks": [
        r"\bdatabricks\b",
    ],

    "Airflow": [
        r"\bairflow\b",
    ],

    "MLflow": [
        r"\bmlflow\b",
    ],

    "MLOps": [
        r"\bmlops\b",
        r"\bml ops\b",
    ],

    "NLP": [
        r"\bnlp\b",
        r"\bnatural language processing\b",
    ],

    "Computer Vision": [
        r"\bcomputer vision\b",
    ],

    # --------------------------------------------------------
    # GENAI
    # --------------------------------------------------------

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

    "Hugging Face": [
        r"\bhugging face\b",
        r"\bhuggingface\b",
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

    # --------------------------------------------------------
    # ENGINEERING CONCEPTS
    # --------------------------------------------------------

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

    "Testing": [
        r"\bpytest\b",
        r"\bunit testing\b",
        r"\bunit tests\b",
        r"\bautomated testing\b",
    ],

    "Security": [
        r"\bsecurity\b",
        r"\bcompliance\b",
    ],
}


# ============================================================
# SECTION HEADINGS
# ============================================================

REQUIRED_HEADINGS = [
    "minimum requirements",
    "minimum qualifications",
    "basic qualifications",
    "required qualifications",
    "required skills",
    "requirements",
    "qualifications",
    "what you'll need",
    "what you’ll need",
    "what you will need",
    "what we are looking for",
    "what we're looking for",
    "what we’re looking for",
    "what we look for",
    "what you'll bring",
    "what you’ll bring",
    "what you will bring",
    "what you bring",
    "who you are",
    "you have",
    "you should have",
    "you'll have",
    "you’ll have",
    "skills and experience",
    "experience and qualifications",
]


PREFERRED_HEADINGS = [
    "preferred qualifications",
    "preferred skills",
    "preferred experience",
    "preferred",
    "nice to have",
    "nice-to-have",
    "nice to haves",
    "bonus",
    "bonus points",
    "bonus qualifications",
    "additional qualifications",
    "ideally",
    "what would make you stand out",
]


OTHER_HEADINGS = [
    "about",
    "about us",
    "about the company",
    "about the team",
    "about the role",
    "the role",
    "what you'll do",
    "what you’ll do",
    "what you will do",
    "responsibilities",
    "your responsibilities",
    "the opportunity",
    "what you'll work on",
    "what you’ll work on",
    "benefits",
    "compensation",
    "pay",
    "salary",
]


# ============================================================
# REQUIREMENT / PREFERENCE CUES
# ============================================================

PREFERRED_WHOLE_LINE_PATTERNS = [
    (
        r"^\s*preferred"
        r"(?:\s+qualifications?|\s+skills?|\s+experience)?"
        r"\s*(?::|—|–|-)"
    ),

    r"^\s*nice[- ]to[- ]have(?:s)?\b",

    r"^\s*bonus(?:\s+points|\s+qualifications?)?\b",

    r"^\s*ideally\b",

    r"\bwould\s+be\s+(?:a\s+)?plus\b",

    r"\bconsidered\s+(?:a\s+)?plus\b",
]


# Do not use generic:
#
#     requirement
#     requirements
#     minimum
#
# because legal text such as:
#
#     requirements of the Washington Minimum Wage Act
#
# must not become an applicant requirement.

REQUIRED_LINE_PATTERNS = [
    r"\bmust\s+have\b",
    r"\bmust\s+possess\b",
    r"\bmust\s+demonstrate\b",
    r"\bmust\s+be\s+proficient\b",

    (
        r"^\s*required"
        r"(?:\s+skills?|\s+experience|\s+knowledge|"
        r"\s+qualifications?)?"
        r"\s*(?::|—|–|-)"
    ),

    r"\brequired\s+experience\b",
    r"\brequired\s+skills?\b",
    r"\brequired\s+knowledge\b",
    r"\brequired\s+proficiency\b",
    r"\brequired\s+expertise\b",

    (
        r"\b(?:experience|knowledge|proficiency|expertise)"
        r"\s+(?:is|are)\s+required\b"
    ),

    (
        r"\bat\s+least\s+"
        r"(?:one|two|three|four|five|\d+)"
        r"\s+of\b"
    ),

    r"\bproficient in\b",
    r"\bproficiency in\b",
    r"\bstrong proficiency\b",

    r"\bexperience\s+with\b",
    r"\bexperience\s+in\b",

    (
        r"\bexperience\s+working\s+"
        r"(?:fluently\s+)?with\b"
    ),

    r"\bhands[- ]on experience\b",
    r"\bstrong experience\b",

    r"\bstrong knowledge\b",
    r"\bstrong understanding\b",

    r"\bdemonstrated experience\b",
    r"\bdemonstrated knowledge\b",

    r"\bexpertise in\b",

    r"\byou have\b",
    r"\byou bring\b",
    r"\byou should have\b",

    r"\bwe are looking for\b",
    r"\bwe're looking for\b",
    r"\bwe’re looking for\b",
]


NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
}


# ============================================================
# BOILERPLATE PROTECTION
# ============================================================

BOILERPLATE_PATTERNS = [
    r"\bequal opportunity employer\b",
    r"\bequal employment opportunity\b",

    r"\bminimum wage act\b",

    r"\bapplicable federal, state, and local laws\b",

    r"\bpaid sick leave\b",

    r"\bhealth, dental, and vision\b",

    r"\bretirement benefits\b",

    r"\bparental leave\b",

    r"\bcompensation and benefits\b",

    r"\bsubject to applicable plan terms\b",

    r"\breproductive or family planning\b",

    r"\blifestyle spending accounts\b",
]


def is_boilerplate_line(
    text: str,
) -> bool:

    return any(
        re.search(
            pattern,
            text,
            re.IGNORECASE,
        )
        for pattern
        in BOILERPLATE_PATTERNS
    )


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize_whitespace(
    text: str,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def protect_sentence_abbreviations(
    text: str,
) -> str:

    replacements = {
        "e.g.": "__EG__",
        "E.g.": "__EG_CAP__",

        "i.e.": "__IE__",
        "I.e.": "__IE_CAP__",

        "U.S.": "__US__",
        "u.s.": "__us__",
    }

    protected = (
        text
    )

    for source, target in (
        replacements.items()
    ):

        protected = (
            protected.replace(
                source,
                target,
            )
        )

    return protected


def restore_sentence_abbreviations(
    text: str,
) -> str:

    replacements = {
        "__EG__": "e.g.",
        "__EG_CAP__": "E.g.",

        "__IE__": "i.e.",
        "__IE_CAP__": "I.e.",

        "__US__": "U.S.",
        "__us__": "u.s.",
    }

    restored = (
        text
    )

    for source, target in (
        replacements.items()
    ):

        restored = (
            restored.replace(
                source,
                target,
            )
        )

    return restored


def split_sentence_segments(
    line: str,
) -> list[str]:
    """
    Split one logical HTML block into sentence-level units.

    This prevents a requirement sentence and a later
    responsibility sentence inside the same <p> from receiving
    the same classification.
    """

    protected = (
        protect_sentence_abbreviations(
            line
        )
    )

    parts = re.split(
        r"(?<=[.!?])\s+(?=[A-Z0-9])",
        protected,
    )

    results = []

    for part in parts:

        restored = (
            restore_sentence_abbreviations(
                part
            )
        )

        restored = (
            normalize_whitespace(
                restored
            )
        )

        if restored:

            results.append(
                restored
            )

    return results


def extract_lines(
    content: str,
) -> list[str]:
    """
    Convert Greenhouse HTML into logical semantic lines.

    IMPORTANT:

    HTML source formatting must NOT become semantic structure.

    For example:

        <p>
            Experience working fluently with standard
            containerization technologies like
            Kubernetes, Terraform, and Docker.
        </p>

    is ONE logical paragraph.

    Source-code newlines inside a <p> or <li> are collapsed
    before sentence-level splitting.
    """

    if not content:

        return []

    decoded = (
        html.unescape(
            content
        )
    )

    soup = BeautifulSoup(
        decoded,
        "html.parser",
    )

    # --------------------------------------------------------
    # SEMANTIC HTML BLOCKS
    # --------------------------------------------------------

    block_tags = [
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "li",
    ]

    elements = (
        soup.find_all(
            block_tags
        )
    )

    lines = []

    # --------------------------------------------------------
    # STRUCTURED HTML
    # --------------------------------------------------------

    if elements:

        for element in elements:

            # Avoid duplicate extraction for nested semantic
            # blocks such as <li><p>...</p></li>.
            parent_block = (
                element.find_parent(
                    block_tags
                )
            )

            if parent_block is not None:

                continue

            block_text = (
                element.get_text(
                    separator=" ",
                    strip=True,
                )
            )

            block_text = (
                normalize_whitespace(
                    block_text
                )
            )

            if not block_text:

                continue

            segments = (
                split_sentence_segments(
                    block_text
                )
            )

            for segment in segments:

                segment = (
                    normalize_whitespace(
                        segment
                    )
                )

                if segment:

                    lines.append(
                        segment
                    )

        return lines

    # --------------------------------------------------------
    # FALLBACK FOR UNUSUAL HTML
    # --------------------------------------------------------

    fallback_text = (
        soup.get_text(
            separator=" ",
            strip=True,
        )
    )

    fallback_text = (
        normalize_whitespace(
            fallback_text
        )
    )

    if not fallback_text:

        return []

    return (
        split_sentence_segments(
            fallback_text
        )
    )


def matches_any_pattern(
    text: str,
    patterns: list[str],
) -> bool:

    return any(
        re.search(
            pattern,
            text,
            re.IGNORECASE,
        )
        for pattern
        in patterns
    )


def contains_go_skill(
    text: str,
) -> bool:
    """
    Detect Go as the programming language without treating
    normal English 'go' as Golang.
    """

    patterns = [
        r"\bgolang\b",

        r"\bgo\s+language\b",

        r"\bgo\s+programming\b",

        r"\bexperience\s+(?:with|in)\s+go\b",

        r"\bproficien(?:t|cy)\s+(?:with|in)\s+go\b",

        r"\bknowledge\s+of\s+go\b",

        r"\bexpertise\s+in\s+go\b",

        r"\busing\s+go\b",

        r"\bwritten\s+in\s+go\b",

        r"\bcode(?:base)?\s+(?:written\s+)?in\s+go\b",

        (
            r"\b(?:python|java|ruby|rust|c\+\+|"
            r"javascript|typescript|kotlin|scala)"
            r"\s*(?:,|/|\bor\b)\s*go\b"
        ),

        (
            r"\bgo\s*(?:,|/|\bor\b)\s*"
            r"(?:python|java|ruby|rust|c\+\+|"
            r"javascript|typescript|kotlin|scala)\b"
        ),
    ]

    return any(
        re.search(
            pattern,
            text,
            re.IGNORECASE,
        )
        for pattern
        in patterns
    )


def extract_skills(
    text: str,
) -> set[str]:

    skills = set()

    if not text:

        return skills

    for skill, patterns in (
        SKILL_PATTERNS.items()
    ):

        for pattern in patterns:

            if re.search(
                pattern,
                text,
                re.IGNORECASE,
            ):

                skills.add(
                    skill
                )

                break

    if contains_go_skill(
        text
    ):

        skills.add(
            "Go"
        )

    return skills


def normalize_heading(
    text: str,
) -> str:

    normalized = (
        text
        .lower()
        .strip()
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    )

    return (
        normalized
        .rstrip(":")
        .strip()
    )


# ============================================================
# HEADING DETECTION
# ============================================================

def heading_type(
    line: str,
) -> str | None:

    normalized = (
        normalize_heading(
            line
        )
    )

    if len(
        normalized
    ) > 100:

        return None

    if normalized in REQUIRED_HEADINGS:

        return (
            "required"
        )

    if normalized in PREFERRED_HEADINGS:

        return (
            "preferred"
        )

    if normalized in OTHER_HEADINGS:

        return (
            "general"
        )

    return None


def detect_inline_heading(
    line: str,
) -> tuple[
    str | None,
    str,
]:

    heading_groups = [
        (
            "required",
            REQUIRED_HEADINGS,
        ),

        (
            "preferred",
            PREFERRED_HEADINGS,
        ),

        (
            "general",
            OTHER_HEADINGS,
        ),
    ]

    for section, headings in (
        heading_groups
    ):

        for heading in sorted(
            headings,
            key=len,
            reverse=True,
        ):

            pattern = (
                r"^\s*"
                + re.escape(
                    heading
                )
                + r"\s*(?::|—|–|-)\s*(.+)$"
            )

            match = re.match(
                pattern,
                line,
                re.IGNORECASE,
            )

            if match:

                return (
                    section,
                    match
                    .group(1)
                    .strip(),
                )

    return (
        None,
        line,
    )


# ============================================================
# LINE CLASSIFICATION
# ============================================================

def classify_requirement_line(
    line: str,
    current_section: str,
) -> tuple[
    str,
    str,
]:

    # Legal, benefits and compensation boilerplate should
    # remain general even when words such as "compliance" or
    # "requirements" appear.

    if is_boilerplate_line(
        line
    ):

        return (
            "general",
            "boilerplate",
        )

    if matches_any_pattern(
        line,
        PREFERRED_WHOLE_LINE_PATTERNS,
    ):

        return (
            "preferred",
            "preferred_language",
        )

    if current_section == "preferred":

        return (
            "preferred",
            "preferred_section",
        )

    if current_section == "required":

        return (
            "required",
            "required_section",
        )

    if matches_any_pattern(
        line,
        REQUIRED_LINE_PATTERNS,
    ):

        return (
            "required",
            "requirement_language",
        )

    return (
        "general",
        "general_context",
    )


def is_continuation_line(
    line: str,
) -> bool:

    normalized = (
        line
        .strip()
        .lower()
    )

    continuation_patterns = [
        r"^and\b",
        r"^or\b",
        r"^and/or\b",
        r"^as\s+well\s+as\b",
        r"^plus\b",
        r"^including\b",
        r"^such\s+as\b",
        r"^\(",
        r"^[,;/]",
    ]

    return (
        matches_any_pattern(
            normalized,
            continuation_patterns,
        )
    )


# ============================================================
# MINIMUM-MATCH CONTEXT
# ============================================================

def extract_minimum_match_count(
    text: str,
) -> int | None:

    match = re.search(
        (
            r"\bat\s+least\s+"
            r"(one|two|three|four|five|\d+)"
            r"\s+of\b"
        ),
        text,
        re.IGNORECASE,
    )

    if not match:

        return None

    raw_value = (
        match
        .group(1)
        .lower()
    )

    if raw_value.isdigit():

        value = (
            int(
                raw_value
            )
        )

    else:

        value = (
            NUMBER_WORDS.get(
                raw_value
            )
        )

    if value is None:

        return None

    return max(
        1,
        value,
    )


# ============================================================
# TARGETED "X PREFERRED"
# ============================================================

def extract_preferred_skill_subset(
    line: str,
    skills: set[str],
) -> set[str]:
    """
    Example:

        deep understanding of distributed systems and
        cloud platforms (AWS preferred)

    Only AWS becomes preferred.
    """

    preferred = set()

    for skill in skills:

        if skill == "Go":

            continue

        patterns = (
            SKILL_PATTERNS.get(
                skill,
                [],
            )
        )

        for pattern in patterns:

            for match in re.finditer(
                pattern,
                line,
                re.IGNORECASE,
            ):

                following = (
                    line[
                        match.end():
                        match.end() + 50
                    ]
                )

                if re.search(
                    r"^\s*(?:is\s+)?preferred\b",
                    following,
                    re.IGNORECASE,
                ):

                    preferred.add(
                        skill
                    )

                    break

            if skill in preferred:

                break

    if "Go" in skills:

        for match in re.finditer(
            r"\bgo\b",
            line,
            re.IGNORECASE,
        ):

            following = (
                line[
                    match.end():
                    match.end() + 50
                ]
            )

            if re.search(
                r"^\s*(?:is\s+)?preferred\b",
                following,
                re.IGNORECASE,
            ):

                preferred.add(
                    "Go"
                )

                break

    return preferred


# ============================================================
# REQUIREMENT GROUP HELPERS
# ============================================================

def make_requirement_group(
    *,
    section: str,
    skills: set[str] | list[str],
    text: str,
    min_matches: int = 1,
    kind: str = "alternative",
) -> dict:

    unique_skills = sorted(
        set(
            skills
        )
    )

    if not unique_skills:

        raise ValueError(
            "Requirement group must contain at least one skill."
        )

    min_matches = max(
        1,
        min(
            int(
                min_matches
            ),
            len(
                unique_skills
            ),
        ),
    )

    return {
        "section": (
            section
        ),

        "skills": (
            unique_skills
        ),

        "min_matches": (
            min_matches
        ),

        "kind": (
            kind
        ),

        "text": (
            text
        ),
    }


def requirement_group_key(
    group: dict,
) -> tuple:

    return (
        group.get(
            "section"
        ),

        tuple(
            sorted(
                group.get(
                    "skills",
                    [],
                )
            )
        ),

        int(
            group.get(
                "min_matches",
                1,
            )
        ),

        group.get(
            "kind",
            "alternative",
        ),
    )


# ============================================================
# PARENTHETICAL EXAMPLES
# ============================================================

def extract_parenthetical_example_groups(
    line: str,
    skills: set[str],
    section: str,
) -> tuple[
    list[dict],
    set[str],
    set[str],
]:

    groups = []

    consumed = set()

    non_scoring_examples = set()

    for match in re.finditer(
        r"\(([^()]*)\)",
        line,
    ):

        segment = (
            match.group(1)
        )

        segment_skills = (
            extract_skills(
                segment
            )
            .intersection(
                skills
            )
        )

        if not segment_skills:

            continue

        has_example_marker = (
            re.search(
                r"\be\.g\.\s*,?",
                segment,
                re.IGNORECASE,
            )
            is not None

            or re.search(
                r"\bfor example\b",
                segment,
                re.IGNORECASE,
            )
            is not None
        )

        looks_like_list = (
            len(
                segment_skills
            )
            >= 2

            and (
                "," in segment

                or "/" in segment

                or re.search(
                    r"\bor\b",
                    segment,
                    re.IGNORECASE,
                )
                is not None
            )
        )

        if looks_like_list:

            groups.append(
                make_requirement_group(
                    section=(
                        section
                    ),

                    skills=(
                        segment_skills
                    ),

                    text=(
                        line
                    ),

                    min_matches=1,

                    kind=(
                        "example_group"
                    ),
                )
            )

            consumed.update(
                segment_skills
            )

        elif has_example_marker:

            consumed.update(
                segment_skills
            )

            non_scoring_examples.update(
                segment_skills
            )

    return (
        groups,
        consumed,
        non_scoring_examples,
    )


# ============================================================
# INLINE EXAMPLES
# ============================================================

def find_inline_example_marker(
    line: str,
):

    marker = re.search(
        r"\b(?:such as|for example|including)\b",
        line,
        re.IGNORECASE,
    )

    if marker:

        return marker

    return re.search(
        (
            r"\b(?:frameworks?|technologies|tools?|languages?|"
            r"platforms?|providers?|databases?|services?)"
            r"\s+like\b"
        ),
        line,
        re.IGNORECASE,
    )


def extract_inline_example_group(
    line: str,
    skills: set[str],
    section: str,
) -> tuple[
    list[dict],
    set[str],
    set[str],
]:

    marker = (
        find_inline_example_marker(
            line
        )
    )

    if not marker:

        return (
            [],
            set(),
            set(),
        )

    tail = (
        line[
            marker.end():
        ]
    )

    tail_skills = (
        extract_skills(
            tail
        )
        .intersection(
            skills
        )
    )

    if len(
        tail_skills
    ) >= 2:

        return (
            [
                make_requirement_group(
                    section=(
                        section
                    ),

                    skills=(
                        tail_skills
                    ),

                    text=(
                        line
                    ),

                    min_matches=1,

                    kind=(
                        "example_group"
                    ),
                )
            ],

            set(
                tail_skills
            ),

            set(),
        )

    if len(
        tail_skills
    ) == 1:

        return (
            [],

            set(
                tail_skills
            ),

            set(
                tail_skills
            ),
        )

    return (
        [],
        set(),
        set(),
    )


# ============================================================
# REQUIREMENT STRUCTURE
# ============================================================

def parse_requirement_structure(
    line: str,
    skills: set[str],
    section: str,
    forced_min_matches: int | None = None,
) -> tuple[
    set[str],
    list[dict],
    set[str],
]:
    """
    Supports:

        Java OR Go

        SQL AND
        (Python OR JavaScript OR TypeScript)

        at least two of:
        Ruby, Node.js, Python, Next.js

        cloud providers:
        AWS, Azure, GCP
    """

    skills = set(
        skills
    )

    if not skills:

        return (
            set(),
            [],
            set(),
        )

    # ========================================================
    # FORCED MINIMUM COUNT FROM PREVIOUS LINE
    # ========================================================

    if (
        forced_min_matches is not None
        and len(
            skills
        )
        >= 2
    ):

        return (
            set(),

            [
                make_requirement_group(
                    section=(
                        section
                    ),

                    skills=(
                        skills
                    ),

                    text=(
                        line
                    ),

                    min_matches=(
                        forced_min_matches
                    ),

                    kind=(
                        "minimum_count"
                    ),
                )
            ],

            set(),
        )

    # ========================================================
    # MINIMUM COUNT ON SAME LINE
    # ========================================================

    minimum_count = (
        extract_minimum_match_count(
            line
        )
    )

    if (
        minimum_count is not None
        and len(
            skills
        )
        >= 2
    ):

        return (
            set(),

            [
                make_requirement_group(
                    section=(
                        section
                    ),

                    skills=(
                        skills
                    ),

                    text=(
                        line
                    ),

                    min_matches=(
                        minimum_count
                    ),

                    kind=(
                        "minimum_count"
                    ),
                )
            ],

            set(),
        )

    # ========================================================
    # EXPLICIT ONE-OF LANGUAGE
    # ========================================================

    if (
        len(
            skills
        )
        >= 2

        and re.search(
            r"\b(?:one\s+of|any\s+of|either)\b",
            line,
            re.IGNORECASE,
        )
    ):

        return (
            set(),

            [
                make_requirement_group(
                    section=(
                        section
                    ),

                    skills=(
                        skills
                    ),

                    text=(
                        line
                    ),

                    min_matches=1,

                    kind=(
                        "alternative"
                    ),
                )
            ],

            set(),
        )

    groups = []

    consumed = set()

    non_scoring_examples = set()

    # ========================================================
    # PARENTHETICAL EXAMPLES
    # ========================================================

    (
        parenthetical_groups,
        parenthetical_consumed,
        parenthetical_non_scoring,
    ) = extract_parenthetical_example_groups(
        line,
        skills,
        section,
    )

    groups.extend(
        parenthetical_groups
    )

    consumed.update(
        parenthetical_consumed
    )

    non_scoring_examples.update(
        parenthetical_non_scoring
    )

    # ========================================================
    # INLINE EXAMPLES
    # ========================================================

    (
        inline_groups,
        inline_consumed,
        inline_non_scoring,
    ) = extract_inline_example_group(
        line,
        skills - consumed,
        section,
    )

    groups.extend(
        inline_groups
    )

    consumed.update(
        inline_consumed
    )

    non_scoring_examples.update(
        inline_non_scoring
    )

    # ========================================================
    # EXPLICIT OR CLAUSES
    # ========================================================

    if re.search(
        r"\bor\b|\band/or\b",
        line,
        re.IGNORECASE,
    ):

        clauses = re.split(
            r"\s*,?\s+\band\b\s+",
            line,
            flags=re.IGNORECASE,
        )

        for clause in clauses:

            if not re.search(
                r"\bor\b|\band/or\b",
                clause,
                re.IGNORECASE,
            ):

                continue

            clause_skills = (
                extract_skills(
                    clause
                )
                .intersection(
                    skills
                    - consumed
                )
            )

            if len(
                clause_skills
            ) < 2:

                continue

            group = (
                make_requirement_group(
                    section=(
                        section
                    ),

                    skills=(
                        clause_skills
                    ),

                    text=(
                        line
                    ),

                    min_matches=1,

                    kind=(
                        "alternative"
                    ),
                )
            )

            key = (
                requirement_group_key(
                    group
                )
            )

            if not any(
                requirement_group_key(
                    existing
                )
                == key
                for existing
                in groups
            ):

                groups.append(
                    group
                )

            consumed.update(
                clause_skills
            )

    standalone = (
        skills
        - consumed
    )

    return (
        standalone,
        groups,
        non_scoring_examples,
    )


# ============================================================
# MAIN REQUIREMENT EXTRACTION
# ============================================================

def extract_requirements(
    content: str,
) -> dict:
    """
    Requirement Extractor V3.3.

    Features:

        - semantic HTML block extraction
        - sentence-level classification
        - heading awareness
        - wrapped continuation support
        - legal / benefits boilerplate protection
        - targeted "AWS preferred"
        - OR groups
        - example groups
        - "at least N of" groups
    """

    lines = (
        extract_lines(
            content
        )
    )

    current_section = (
        "general"
    )

    required_skills = set()

    preferred_skills = set()

    general_skills = set()

    requirement_groups = []

    evidence = []

    recognized_headings = []

    requirement_language_lines = 0

    preferred_language_lines = 0

    previous_effective_section = None

    pending_min_matches = None

    pending_min_section = None

    # ========================================================
    # PROCESS
    # ========================================================

    for original_line in lines:

        line = (
            original_line
        )

        # ----------------------------------------------------
        # STANDALONE HEADING
        # ----------------------------------------------------

        detected_heading = (
            heading_type(
                line
            )
        )

        if detected_heading:

            current_section = (
                detected_heading
            )

            previous_effective_section = (
                None
            )

            pending_min_matches = (
                None
            )

            pending_min_section = (
                None
            )

            recognized_headings.append(
                {
                    "section": (
                        detected_heading
                    ),

                    "text": (
                        line
                    ),
                }
            )

            continue

        # ----------------------------------------------------
        # INLINE HEADING
        # ----------------------------------------------------

        (
            inline_section,
            remainder,
        ) = detect_inline_heading(
            line
        )

        if inline_section:

            current_section = (
                inline_section
            )

            previous_effective_section = (
                None
            )

            pending_min_matches = (
                None
            )

            pending_min_section = (
                None
            )

            recognized_headings.append(
                {
                    "section": (
                        inline_section
                    ),

                    "text": (
                        line
                    ),
                }
            )

            line = (
                remainder
            )

            if not line:

                continue

        # ----------------------------------------------------
        # CLASSIFY BEFORE SKILL EXTRACTION
        # ----------------------------------------------------

        (
            effective_section,
            classification_reason,
        ) = classify_requirement_line(
            line,
            current_section,
        )

        # ----------------------------------------------------
        # CONTINUATION
        # ----------------------------------------------------

        if (
            effective_section
            == "general"

            and classification_reason
            != "boilerplate"

            and previous_effective_section
            in {
                "required",
                "preferred",
            }

            and is_continuation_line(
                line
            )
        ):

            effective_section = (
                previous_effective_section
            )

            classification_reason = (
                "continuation_line"
            )

        # ----------------------------------------------------
        # MINIMUM COUNT
        # ----------------------------------------------------

        minimum_count = (
            extract_minimum_match_count(
                line
            )
        )

        if minimum_count is not None:

            pending_min_matches = (
                minimum_count
            )

            pending_min_section = (
                effective_section
            )

        # ----------------------------------------------------
        # SAVE CONTEXT
        # ----------------------------------------------------

        previous_effective_section = (
            effective_section
        )

        # ----------------------------------------------------
        # SKILLS
        # ----------------------------------------------------

        skills = (
            extract_skills(
                line
            )
        )

        if not skills:

            continue

        # ----------------------------------------------------
        # COUNTERS
        # ----------------------------------------------------

        if (
            classification_reason
            == "requirement_language"
        ):

            requirement_language_lines += 1

        if (
            classification_reason
            == "preferred_language"
        ):

            preferred_language_lines += 1

        # ----------------------------------------------------
        # PENDING MINIMUM GROUP
        # ----------------------------------------------------

        forced_min_matches = None

        if pending_min_matches is not None:

            if minimum_count is None:

                forced_min_matches = (
                    pending_min_matches
                )

                if pending_min_section in {
                    "required",
                    "preferred",
                }:

                    effective_section = (
                        pending_min_section
                    )

                    classification_reason = (
                        "minimum_count_continuation"
                    )

            pending_min_matches = (
                None
            )

            pending_min_section = (
                None
            )

        # ----------------------------------------------------
        # TARGETED PREFERENCE
        # ----------------------------------------------------

        preferred_overrides = (
            extract_preferred_skill_subset(
                line,
                skills,
            )
        )

        base_skills = (
            set(
                skills
            )
            - preferred_overrides
        )

        preferred_skills.update(
            preferred_overrides
        )

        # ----------------------------------------------------
        # REQUIREMENT STRUCTURE
        # ----------------------------------------------------

        (
            standalone_skills,
            groups,
            non_scoring_examples,
        ) = parse_requirement_structure(
            line,
            base_skills,
            effective_section,
            forced_min_matches=(
                forced_min_matches
            ),
        )

        general_skills.update(
            non_scoring_examples
        )

        # ----------------------------------------------------
        # GROUP DEDUPLICATION
        # ----------------------------------------------------

        existing_group_keys = {
            requirement_group_key(
                group
            )
            for group
            in requirement_groups
        }

        for group in groups:

            key = (
                requirement_group_key(
                    group
                )
            )

            if key not in (
                existing_group_keys
            ):

                requirement_groups.append(
                    group
                )

                existing_group_keys.add(
                    key
                )

        # ----------------------------------------------------
        # STANDALONE SKILLS
        # ----------------------------------------------------

        if (
            effective_section
            == "required"
        ):

            required_skills.update(
                standalone_skills
            )

        elif (
            effective_section
            == "preferred"
        ):

            preferred_skills.update(
                standalone_skills
            )

        else:

            general_skills.update(
                standalone_skills
            )

        # ----------------------------------------------------
        # EVIDENCE
        # ----------------------------------------------------

        evidence.append(
            {
                "section": (
                    effective_section
                ),

                "skills": sorted(
                    skills
                ),

                "standalone_skills": sorted(
                    standalone_skills
                ),

                "preferred_overrides": sorted(
                    preferred_overrides
                ),

                "non_scoring_examples": sorted(
                    non_scoring_examples
                ),

                "groups": [
                    {
                        "skills": (
                            group[
                                "skills"
                            ]
                        ),

                        "min_matches": (
                            group[
                                "min_matches"
                            ]
                        ),

                        "kind": (
                            group[
                                "kind"
                            ]
                        ),
                    }
                    for group
                    in groups
                ],

                "alternative": bool(
                    groups
                ),

                "classification_reason": (
                    classification_reason
                ),

                "text": (
                    line
                ),
            }
        )

    # ========================================================
    # PRECEDENCE
    # ========================================================

    preferred_skills -= (
        required_skills
    )

    general_skills -= (
        required_skills
    )

    general_skills -= (
        preferred_skills
    )

    # ========================================================
    # REMOVE GROUP MEMBERS FROM STANDALONE SETS
    # ========================================================

    for group in (
        requirement_groups
    ):

        group_skills = set(
            group.get(
                "skills",
                [],
            )
        )

        section = (
            group.get(
                "section"
            )
        )

        if section == "required":

            required_skills -= (
                group_skills
            )

            preferred_skills -= (
                group_skills
            )

            general_skills -= (
                group_skills
            )

        elif section == "preferred":

            preferred_skills -= (
                group_skills
            )

            general_skills -= (
                group_skills
            )

    # ========================================================
    # DIAGNOSTICS
    # ========================================================

    extraction_stats = {
        "line_count": (
            len(
                lines
            )
        ),

        "recognized_heading_count": (
            len(
                recognized_headings
            )
        ),

        "required_skill_count": (
            len(
                required_skills
            )
        ),

        "preferred_skill_count": (
            len(
                preferred_skills
            )
        ),

        "general_skill_count": (
            len(
                general_skills
            )
        ),

        "required_group_count": sum(
            1
            for group
            in requirement_groups
            if (
                group.get(
                    "section"
                )
                == "required"
            )
        ),

        "preferred_group_count": sum(
            1
            for group
            in requirement_groups
            if (
                group.get(
                    "section"
                )
                == "preferred"
            )
        ),

        "general_group_count": sum(
            1
            for group
            in requirement_groups
            if (
                group.get(
                    "section"
                )
                == "general"
            )
        ),

        "requirement_language_lines": (
            requirement_language_lines
        ),

        "preferred_language_lines": (
            preferred_language_lines
        ),
    }

    # ========================================================
    # RESULT
    # ========================================================

    return {
        "required_skills": sorted(
            required_skills
        ),

        "preferred_skills": sorted(
            preferred_skills
        ),

        "general_skills": sorted(
            general_skills
        ),

        # Canonical V3 format.
        "requirement_groups": (
            requirement_groups
        ),

        # Backward-compatible alias.
        "alternative_groups": (
            requirement_groups
        ),

        "evidence": (
            evidence
        ),

        "recognized_headings": (
            recognized_headings
        ),

        "extraction_stats": (
            extraction_stats
        ),
    }
