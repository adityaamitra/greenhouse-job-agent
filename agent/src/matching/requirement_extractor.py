import html
import re

from bs4 import BeautifulSoup


# ============================================================
# SKILLS
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
    ],

    "TypeScript": [
        r"\btypescript\b",
    ],

    "Go": [
        r"\bgolang\b",
        r"\bgo\b",
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


# ============================================================
# SECTION HEADINGS
# ============================================================

REQUIRED_HEADINGS = [
    "minimum requirements",
    "minimum qualifications",
    "required qualifications",
    "requirements",
    "what you'll need",
    "what you’ll need",
    "what we are looking for",
    "what we're looking for",
    "what we’re looking for",
    "who you are",
    "you have",
]


PREFERRED_HEADINGS = [
    "preferred qualifications",
    "preferred",
    "nice to have",
    "nice-to-have",
    "bonus",
    "additional qualifications",
    "ideally",
]


OTHER_HEADINGS = [
    "about",
    "about the team",
    "about the role",
    "what you'll do",
    "what you’ll do",
    "responsibilities",
    "the opportunity",
    "benefits",
    "compensation",
    "pay",
]


# ============================================================
# TEXT HELPERS
# ============================================================

def extract_lines(content: str) -> list[str]:
    if not content:
        return []

    decoded = html.unescape(content)

    soup = BeautifulSoup(
        decoded,
        "html.parser",
    )

    text = soup.get_text(
        separator="\n",
        strip=True,
    )

    lines = []

    for raw_line in text.splitlines():

        line = re.sub(
            r"\s+",
            " ",
            raw_line,
        ).strip()

        if line:
            lines.append(line)

    return lines


def extract_skills(text: str) -> set[str]:
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


def normalize_heading(text: str) -> str:
    return (
        text.lower()
        .strip()
        .rstrip(":")
    )


def heading_type(line: str) -> str | None:
    normalized = normalize_heading(line)

    if len(normalized) > 80:
        return None

    for heading in REQUIRED_HEADINGS:

        if normalized == heading:
            return "required"

    for heading in PREFERRED_HEADINGS:

        if normalized == heading:
            return "preferred"

    for heading in OTHER_HEADINGS:

        if normalized == heading:
            return "general"

    return None


# ============================================================
# ALTERNATIVE REQUIREMENTS
# ============================================================

def detect_alternative_group(
    line: str,
    skills: set[str],
) -> list[str] | None:
    """
    Detect cases where matching any ONE skill satisfies the
    requirement.

    Examples:

        Go, Java, C++, or similar
        languages like Go, Java, C/C++
        Python, Ruby, etc.
        experience with Java or Go
    """

    if len(skills) < 2:
        return None

    normalized = line.lower()

    alternative_markers = [
        " or ",
        "and/or",
        "one of",
        "such as",
        " like ",
        "for example",
        "e.g.",
        "etc.",
        "etc ",
        "similar",
    ]

    if any(
        marker in normalized
        for marker in alternative_markers
    ):
        return sorted(skills)

    return None


# ============================================================
# REQUIREMENT EXTRACTION
# ============================================================

def extract_requirements(content: str) -> dict:
    """
    Extract required, preferred, and general skills.

    Skills belonging to an alternative group are stored as one
    grouped requirement instead of independent mandatory skills.
    """

    lines = extract_lines(content)

    current_section = "general"

    required_skills = set()
    preferred_skills = set()
    general_skills = set()

    alternative_groups = []

    evidence = []

    for line in lines:

        detected_heading = heading_type(line)

        if detected_heading:
            current_section = detected_heading
            continue

        skills = extract_skills(line)

        if not skills:
            continue

        alternative_group = detect_alternative_group(
            line,
            skills,
        )

        # ----------------------------------------------------
        # ALTERNATIVE REQUIREMENT
        # ----------------------------------------------------

        if alternative_group:

            alternative_groups.append(
                {
                    "section": current_section,
                    "skills": alternative_group,
                    "text": line,
                }
            )

            # Don't count every member as a separate mandatory
            # requirement.
            evidence.append(
                {
                    "section": current_section,
                    "skills": sorted(skills),
                    "alternative": True,
                    "text": line,
                }
            )

            continue

        # ----------------------------------------------------
        # NORMAL REQUIREMENT
        # ----------------------------------------------------

        if current_section == "required":

            required_skills.update(
                skills
            )

        elif current_section == "preferred":

            preferred_skills.update(
                skills
            )

        else:

            general_skills.update(
                skills
            )

        evidence.append(
            {
                "section": current_section,
                "skills": sorted(skills),
                "alternative": False,
                "text": line,
            }
        )

    # Required takes precedence.
    preferred_skills -= required_skills

    general_skills -= required_skills
    general_skills -= preferred_skills

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

        "alternative_groups": (
            alternative_groups
        ),

        "evidence": evidence,
    }
