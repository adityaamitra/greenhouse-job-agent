from dataclasses import asdict, dataclass
import re


ACTION_PROFILE_VALUE = "PROFILE_VALUE"
ACTION_FIXED_ANSWER = "FIXED_ANSWER"
ACTION_RESUME_FILE = "RESUME_FILE"
ACTION_NEEDS_ASSISTANCE = "NEEDS_ASSISTANCE"
ACTION_IGNORE = "IGNORE"


FIXED_ANSWERS = {
    "WORK_AUTHORIZED_US": "Yes",
    "SPONSORSHIP_NOW": "No",
    "SPONSORSHIP_FUTURE": "Yes",
    "SPONSORSHIP_NOW_OR_FUTURE": "Yes",
    "WORK_AUTH_WITHOUT_SPONSORSHIP_NOW": "Yes",
    "WORK_AUTH_WITHOUT_SPONSORSHIP_FUTURE": "No",
}


@dataclass(frozen=True)
class FieldDecision:
    category: str
    action: str
    reason: str
    answer_key: str | None = None
    fixed_answer: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_text(value: str | None) -> str:
    text = value or ""
    text = (
        text
        .replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _has_word(text: str, word: str) -> bool:
    return bool(re.search(rf"\b{re.escape(word)}\b", text))


def _fixed(*, category: str, answer_key: str, reason: str) -> FieldDecision:
    return FieldDecision(
        category=category,
        action=ACTION_FIXED_ANSWER,
        reason=reason,
        answer_key=answer_key,
        fixed_answer=FIXED_ANSWERS[answer_key],
    )


def _profile(*, category: str, answer_key: str, reason: str) -> FieldDecision:
    return FieldDecision(
        category=category,
        action=ACTION_PROFILE_VALUE,
        reason=reason,
        answer_key=answer_key,
    )


def _assistance(*, category: str, reason: str) -> FieldDecision:
    return FieldDecision(
        category=category,
        action=ACTION_NEEDS_ASSISTANCE,
        reason=reason,
    )


def _primary_is_generic(
    *,
    label: str,
    name: str,
    placeholder: str,
) -> bool:
    """
    Decide whether surrounding DOM context is needed.

    Real Greenhouse custom controls sometimes expose generic
    labels such as "Attach" or no label at all. For clearly
    labeled applicant questions (LinkedIn, How did you hear,
    sponsorship, etc.), nearby context must NOT override the
    field's own label.
    """

    primary = " ".join(
        part
        for part in (
            label,
            name,
            placeholder,
        )
        if part
    ).strip()

    if not primary:
        return True

    generic_values = {
        "attach",
        "upload",
        "select",
        "choose",
        "yes",
        "no",
        "search",
        "input",
        "field",
    }

    return primary in generic_values


def classify_field(
    *,
    label: str | None,
    field_type: str | None = None,
    name: str | None = None,
    placeholder: str | None = None,
    context_text: str | None = None,
) -> FieldDecision:
    """
    Conservatively classify one application-form field.

    Unknown/custom questions always route to NEEDS_ASSISTANCE.
    No personal facts are inferred.
    """

    normalized_label = normalize_text(label)
    normalized_name = normalize_text(name)
    normalized_placeholder = normalize_text(placeholder)
    normalized_context = normalize_text(context_text)
    field_type_text = normalize_text(field_type)

    primary = " ".join(
        part
        for part in (
            normalized_label,
            normalized_name,
            normalized_placeholder,
        )
        if part
    )

    combined = " ".join(
        part
        for part in (
            primary,
            normalized_context,
        )
        if part
    )

    use_context = _primary_is_generic(
        label=normalized_label,
        name=normalized_name,
        placeholder=normalized_placeholder,
    )

    semantic_text = (
        combined
        if use_context
        else primary
    )

    # --------------------------------------------------------
    # Technical controls
    # --------------------------------------------------------

    if (
        field_type_text in {
            "hidden",
            "submit",
            "button",
            "reset",
            "image",
        }
        or _contains_any(
            semantic_text,
            (
                "g-recaptcha-response",
                "recaptcha",
                "hcaptcha",
                "h-captcha",
                "cf-turnstile",
                "turnstile-response",
            ),
        )
    ):
        return FieldDecision(
            category="TECHNICAL_CONTROL",
            action=ACTION_IGNORE,
            reason="Technical/browser-verification control.",
        )

    # --------------------------------------------------------
    # File uploads
    # --------------------------------------------------------

    if field_type_text == "file":
        resume_signal = _contains_any(
            combined,
            (
                "resume",
                "résumé",
                "curriculum vitae",
                "resume/cv",
                "cv/resume",
            ),
        )

        cover_letter_signal = (
            "cover letter" in combined
        )

        if resume_signal and not cover_letter_signal:
            return FieldDecision(
                category="RESUME",
                action=ACTION_RESUME_FILE,
                reason=(
                    "Resume upload can use the resume already "
                    "selected by the V2.1 matcher."
                ),
                answer_key="SELECTED_RESUME_FILE",
            )

        if cover_letter_signal and not resume_signal:
            return _assistance(
                category="COVER_LETTER_UPLOAD",
                reason=(
                    "Cover-letter content is intentionally "
                    "human-reviewed."
                ),
            )

        return _assistance(
            category="UNKNOWN_FILE_UPLOAD",
            reason=(
                "File-upload purpose is not confidently "
                "recognized."
            ),
        )

    # --------------------------------------------------------
    # Work authorization / sponsorship
    # --------------------------------------------------------

    mentions_authorization = _contains_any(
        semantic_text,
        (
            "authorized to work",
            "authorised to work",
            "legal authorization",
            "legally authorized",
            "legally authorised",
            "work authorization",
            "work authorisation",
            "eligible to work legally",
            "legally eligible to work",
            "eligible to work in the united states",
            "eligible to work in the u.s.",
            "eligible to work in the us",
        ),
    )

    mentions_sponsorship = _contains_any(
        semantic_text,
        (
            "sponsor",
            "sponsorship",
            "visa support",
            "immigration support",
        ),
    )

    future_language = _contains_any(
        semantic_text,
        (
            "in the future",
            "in future",
            "future require",
            "at any time",
            "eventually",
            "later require",
            "continue working",
        ),
    )

    current_language = _contains_any(
        semantic_text,
        (
            "currently",
            "right now",
            "at this time",
            "to begin",
            "to start",
            "to commence",
            "at the start",
            "upon hire",
            "initially",
        ),
    )

    now_or_future_language = (
        _contains_any(
            semantic_text,
            (
                "now or in the future",
                "now or future",
                "now or at any time in the future",
                "currently or in the future",
                "currently or at any time",
                "now and in the future",
                "now and future",
            ),
        )
        or (
            _has_word(
                semantic_text,
                "now",
            )
            and _has_word(
                semantic_text,
                "future",
            )
        )
    )

    without_sponsorship = _contains_any(
        semantic_text,
        (
            "without sponsorship",
            "without employer sponsorship",
            "without visa sponsorship",
            "without requiring sponsorship",
        ),
    )

    if (
        mentions_authorization
        and mentions_sponsorship
        and without_sponsorship
        and (future_language or now_or_future_language)
    ):
        return _fixed(
            category="WORK_AUTH_WITHOUT_SPONSORSHIP_FUTURE",
            answer_key="WORK_AUTH_WITHOUT_SPONSORSHIP_FUTURE",
            reason=(
                "Question requires continuing work authorization "
                "without future sponsorship."
            ),
        )

    if (
        mentions_authorization
        and mentions_sponsorship
        and without_sponsorship
        and current_language
        and not future_language
    ):
        return _fixed(
            category="WORK_AUTH_WITHOUT_SPONSORSHIP_NOW",
            answer_key="WORK_AUTH_WITHOUT_SPONSORSHIP_NOW",
            reason=(
                "Question is explicitly limited to current/start "
                "work authorization."
            ),
        )

    if (
        mentions_authorization
        and mentions_sponsorship
        and without_sponsorship
    ):
        return _assistance(
            category="WORK_AUTH_SPONSORSHIP_AMBIGUOUS",
            reason=(
                "Question mixes work authorization and sponsorship "
                "without a clear time horizon."
            ),
        )

    if mentions_sponsorship:
        if now_or_future_language:
            return _fixed(
                category="SPONSORSHIP_NOW_OR_FUTURE",
                answer_key="SPONSORSHIP_NOW_OR_FUTURE",
                reason=(
                    "Question asks whether sponsorship is needed "
                    "now OR in the future."
                ),
            )

        if future_language and not current_language:
            return _fixed(
                category="SPONSORSHIP_FUTURE",
                answer_key="SPONSORSHIP_FUTURE",
                reason="Question explicitly asks about future sponsorship.",
            )

        if current_language and not future_language:
            return _fixed(
                category="SPONSORSHIP_NOW",
                answer_key="SPONSORSHIP_NOW",
                reason="Question explicitly asks about current/start sponsorship.",
            )

        return _assistance(
            category="SPONSORSHIP_AMBIGUOUS",
            reason=(
                "Sponsorship is mentioned without enough temporal "
                "wording to choose a safe answer."
            ),
        )

    if mentions_authorization:
        return _fixed(
            category="WORK_AUTHORIZATION_US",
            answer_key="WORK_AUTHORIZED_US",
            reason=(
                "Direct U.S. work-authorization question without "
                "sponsorship wording."
            ),
        )

    # --------------------------------------------------------
    # High-risk legal / eligibility questions
    # --------------------------------------------------------

    if _contains_any(
        semantic_text,
        (
            "security clearance",
            "secret clearance",
            "ts/sci",
            "top secret",
            "clearance level",
        ),
    ):
        return _assistance(
            category="SECURITY_CLEARANCE",
            reason="Security-clearance facts require explicit confirmation.",
        )

    citizenship_or_export_control = (
        _contains_any(
            semantic_text,
            (
                "u.s. citizen",
                "us citizen",
                "united states citizen",
                "citizenship",
                "export control",
                "export-controlled",
            ),
        )
        or _has_word(
            semantic_text,
            "itar",
        )
    )

    if citizenship_or_export_control:
        return _assistance(
            category="CITIZENSHIP_OR_EXPORT_CONTROL",
            reason=(
                "Citizenship/export-control questions must not "
                "be inferred."
            ),
        )

    if _contains_any(
        semantic_text,
        (
            "non-compete",
            "noncompete",
            "non-solicitation",
            "nonsolicitation",
            "former employer",
            "third party agreement",
            "third-party agreement",
        ),
    ):
        return _assistance(
            category="EMPLOYMENT_RESTRICTION",
            reason=(
                "Employment-agreement restrictions require an "
                "explicit user-confirmed answer."
            ),
        )

    # --------------------------------------------------------
    # Demographic / EEO
    # --------------------------------------------------------

    if _contains_any(
        semantic_text,
        (
            "race",
            "ethnicity",
            "gender",
            "sex",
            "veteran",
            "disability",
            "sexual orientation",
            "transgender",
            "pronouns",
            "self-identify",
            "self identify",
            "i identify as",
            "demographic",
            "hispanic",
            "latino",
            "latina",
            "latinx",
            "lgbtq",
            "lgbtq+",
            "lgbt",
            "queer",
            "military status",
        ),
    ):
        return _assistance(
            category="VOLUNTARY_DEMOGRAPHIC",
            reason="Demographic/EEO answers must never be inferred.",
        )

    # --------------------------------------------------------
    # Standard profile fields
    # --------------------------------------------------------

    if _contains_any(
        primary,
        (
            "preferred first name",
            "preferred name",
        ),
    ):
        return _profile(
            category="PREFERRED_FIRST_NAME",
            answer_key="PREFERRED_FIRST_NAME",
            reason=(
                "Separate preferred-name profile field; it should "
                "not silently reuse legal first name."
            ),
        )

    if _contains_any(
        primary,
        (
            "first name",
            "given name",
        ),
    ):
        return _profile(
            category="FIRST_NAME",
            answer_key="FIRST_NAME",
            reason="Standard applicant profile field.",
        )

    if _contains_any(
        primary,
        (
            "last name",
            "surname",
            "family name",
        ),
    ):
        return _profile(
            category="LAST_NAME",
            answer_key="LAST_NAME",
            reason="Standard applicant profile field.",
        )

    if (
        "full name" in primary
        or (
            normalized_label == "name"
            and field_type_text not in {
                "radio",
                "checkbox",
            }
        )
    ):
        return _profile(
            category="FULL_NAME",
            answer_key="FULL_NAME",
            reason="Standard applicant profile field.",
        )

    if (
        field_type_text == "email"
        or "email" in primary
        or "e-mail" in primary
    ):
        return _profile(
            category="EMAIL",
            answer_key="EMAIL",
            reason="Standard applicant profile field.",
        )

    if (
        field_type_text == "tel"
        or _contains_any(
            primary,
            (
                "phone",
                "mobile",
                "telephone",
            ),
        )
    ):
        return _profile(
            category="PHONE",
            answer_key="PHONE",
            reason="Standard applicant profile field.",
        )

    if "linkedin" in primary:
        return _profile(
            category="LINKEDIN",
            answer_key="LINKEDIN_URL",
            reason="Standard professional-profile field.",
        )

    if "github" in primary:
        return _profile(
            category="GITHUB",
            answer_key="GITHUB_URL",
            reason="Standard professional-profile field.",
        )

    if _contains_any(
        primary,
        (
            "portfolio",
            "personal website",
            "website url",
            "website",
        ),
    ):
        return _profile(
            category="PORTFOLIO",
            answer_key="PORTFOLIO_URL",
            reason="Standard professional-profile field.",
        )

    if normalized_label in {
        "school",
        "school*",
    }:
        return _profile(
            category="EDUCATION_SCHOOL",
            answer_key="EDUCATION_SCHOOL",
            reason="Structured education field.",
        )

    if normalized_label in {
        "degree",
        "degree*",
    }:
        return _profile(
            category="EDUCATION_DEGREE",
            answer_key="EDUCATION_DEGREE",
            reason="Structured education field.",
        )

    if normalized_label in {
        "discipline",
        "discipline*",
        "field of study",
        "field of study*",
    }:
        return _profile(
            category="EDUCATION_DISCIPLINE",
            answer_key="EDUCATION_DISCIPLINE",
            reason="Structured education field.",
        )

    if _contains_any(
        primary,
        (
            "preferred office location",
            "preferred office",
        ),
    ):
        return _assistance(
            category="OFFICE_PREFERENCE",
            reason=(
                "Preferred office is a job-specific preference "
                "and must not reuse the applicant's current address."
            ),
        )

    if _contains_any(
        primary,
        (
            "currently located in the us",
            "currently located in the u.s.",
            "currently based in the us",
            "currently based in the u.s.",
        ),
    ):
        return _profile(
            category="CURRENT_US_LOCATION",
            answer_key="CURRENT_US_LOCATION",
            reason=(
                "Current-country/location fact should come from "
                "explicit applicant profile configuration."
            ),
        )

    if _contains_any(
        primary,
        (
            "street address",
            "address line 1",
            "address line1",
            "address 1",
        ),
    ):
        return _profile(
            category="STREET_ADDRESS",
            answer_key="STREET_ADDRESS",
            reason="Structured street-address profile field.",
        )

    if _contains_any(
        primary,
        (
            "postal code",
            "zip code",
            "zipcode",
        ),
    ):
        return _profile(
            category="POSTAL_CODE",
            answer_key="POSTAL_CODE",
            reason="Structured postal-code profile field.",
        )

    if (
        _has_word(
            primary,
            "country",
        )
        and not _contains_any(
            primary,
            (
                "country code",
                "country calling code",
            ),
        )
    ):
        return _profile(
            category="COUNTRY",
            answer_key="COUNTRY",
            reason="Structured country profile field.",
        )

    if (
        _contains_any(
            primary,
            (
                "location (city)",
                "current city",
                "city of residence",
            ),
        )
        or _has_word(
            primary,
            "city",
        )
    ):
        return _profile(
            category="CITY",
            answer_key="CITY",
            reason="Structured city profile field.",
        )

    if (
        _has_word(
            primary,
            "state",
        )
        or _has_word(
            primary,
            "province",
        )
    ):
        return _profile(
            category="STATE_OR_PROVINCE",
            answer_key="STATE_OR_PROVINCE",
            reason="Structured state/province profile field.",
        )

    if _has_word(
        primary,
        "location",
    ):
        return _profile(
            category="LOCATION_FREEFORM",
            answer_key="LOCATION_FREEFORM",
            reason=(
                "Generic location field; future filling must use "
                "an explicitly configured free-form location."
            ),
        )

    # --------------------------------------------------------
    # Other questions requiring human input
    # --------------------------------------------------------

    if _contains_any(
        semantic_text,
        (
            "salary",
            "compensation",
            "desired pay",
            "expected pay",
            "pay expectation",
        ),
    ):
        return _assistance(
            category="COMPENSATION_EXPECTATION",
            reason="Compensation expectations are not safe to invent.",
        )

    if _contains_any(
        semantic_text,
        (
            "why do you want",
            "why are you interested",
            "why this company",
            "why this role",
            "tell us why",
            "cover letter",
            "additional information",
        ),
    ):
        return _assistance(
            category="FREEFORM_APPLICATION_QUESTION",
            reason="Free-form answers are human-reviewed in Browser Agent V1.",
        )

    if _contains_any(
        semantic_text,
        (
            "how did you hear",
            "how did you find",
            "source of application",
        ),
    ):
        return _assistance(
            category="APPLICATION_SOURCE",
            reason=(
                "Application-source questions require a truthful "
                "per-application answer."
            ),
        )

    if _contains_any(
        semantic_text,
        (
            "total years of experience",
            "years of experience you have",
            "relevant years of experience",
        ),
    ):
        return _assistance(
            category="EXPERIENCE_SELF_REPORT",
            reason=(
                "Self-reported relevant experience can vary by role "
                "and should be resolved from explicit profile evidence."
            ),
        )

    if _contains_any(
        semantic_text,
        (
            "do you know anyone",
            "know anyone currently at",
            "employee referral",
            "referred by",
        ),
    ):
        return _assistance(
            category="REFERRAL_RELATIONSHIP",
            reason=(
                "Referral/relationship questions require a truthful "
                "per-company answer."
            ),
        )

    if _contains_any(
        semantic_text,
        (
            "have you used robinhood",
            "have you used our product",
            "have you used our products",
        ),
    ):
        return _assistance(
            category="PRODUCT_USAGE",
            reason=(
                "Product-usage questions require an explicit "
                "user-confirmed answer."
            ),
        )

    if _contains_any(
        semantic_text,
        (
            "ever worked for robinhood",
            "previously worked for",
            "worked for us as an employee",
            "worked for us as an intern",
            "worked for us as a contractor",
        ),
    ):
        return _assistance(
            category="PRIOR_COMPANY_EMPLOYMENT",
            reason=(
                "Prior-company-employment questions require an "
                "explicit truthful answer."
            ),
        )

    if _contains_any(
        semantic_text,
        (
            "hybrid policy",
            "willing to work from the office",
            "able to work from the office",
            "office(s) listed",
        ),
    ):
        return _assistance(
            category="WORK_LOCATION_COMMITMENT",
            reason=(
                "Hybrid/office attendance is a job-specific "
                "commitment and should be explicitly confirmed."
            ),
        )

    if _contains_any(
        semantic_text,
        (
            "18 years",
            "18 or older",
            "age of 18",
            "minimum age",
        ),
    ):
        return _assistance(
            category="AGE_CONFIRMATION",
            reason="Age-related facts require explicit confirmation.",
        )

    if _contains_any(
        semantic_text,
        (
            "relocate",
            "relocation",
            "willing to move",
        ),
    ):
        return _assistance(
            category="RELOCATION",
            reason="Relocation preferences require explicit profile data.",
        )

    if _contains_any(
        semantic_text,
        (
            "terms",
            "privacy policy",
            "privacy notice",
            "acknowledge",
            "certify",
            "attest",
            "consent",
        ),
    ):
        return _assistance(
            category="ACKNOWLEDGEMENT",
            reason=(
                "Legal acknowledgements/consent should not be "
                "accepted automatically."
            ),
        )

    return _assistance(
        category="UNKNOWN_CUSTOM_FIELD",
        reason=(
            "Field is not recognized with enough confidence to "
            "answer automatically."
        ),
    )
