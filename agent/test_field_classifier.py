from src.browser.field_classifier import (
    ACTION_FIXED_ANSWER,
    ACTION_IGNORE,
    ACTION_NEEDS_ASSISTANCE,
    ACTION_PROFILE_VALUE,
    ACTION_RESUME_FILE,
    classify_field,
)


TESTS = [
    ("First name", "First Name", "text",
     "FIRST_NAME", ACTION_PROFILE_VALUE, None),

    ("Preferred first name", "Preferred First Name", "text",
     "PREFERRED_FIRST_NAME", ACTION_PROFILE_VALUE, None),

    ("Last name", "Last Name", "text",
     "LAST_NAME", ACTION_PROFILE_VALUE, None),

    ("Email", "Email", "text",
     "EMAIL", ACTION_PROFILE_VALUE, None),

    ("Phone", "Phone", "tel",
     "PHONE", ACTION_PROFILE_VALUE, None),

    ("Resume upload", "Attach", "file",
     "RESUME", ACTION_RESUME_FILE, None,
     "Resume/CV Attach"),

    ("Cover letter", "Attach", "file",
     "COVER_LETTER_UPLOAD", ACTION_NEEDS_ASSISTANCE, None,
     "Cover Letter Attach"),

    (
        "Chime work authorization wording",
        "Are you currently eligible to work legally in the United States of America?",
        "text",
        "WORK_AUTHORIZATION_US",
        ACTION_FIXED_ANSWER,
        "Yes",
    ),

    (
        "Current sponsorship",
        "Do you currently require sponsorship to start employment?",
        "text",
        "SPONSORSHIP_NOW",
        ACTION_FIXED_ANSWER,
        "No",
    ),

    (
        "Future sponsorship",
        "Will you require sponsorship in the future?",
        "text",
        "SPONSORSHIP_FUTURE",
        ACTION_FIXED_ANSWER,
        "Yes",
    ),

    (
        "Now or future sponsorship",
        "Do you now or in the future require immigration support or visa sponsorship?",
        "text",
        "SPONSORSHIP_NOW_OR_FUTURE",
        ACTION_FIXED_ANSWER,
        "Yes",
    ),

    (
        "Former employer agreement",
        "Are you subject to a non-compete agreement with a former employer?",
        "text",
        "EMPLOYMENT_RESTRICTION",
        ACTION_NEEDS_ASSISTANCE,
        None,
    ),

    (
        "How did you hear",
        "How did you hear about this job?",
        "text",
        "APPLICATION_SOURCE",
        ACTION_NEEDS_ASSISTANCE,
        None,
    ),

    (
        "Demographic",
        "I identify as:",
        "text",
        "VOLUNTARY_DEMOGRAPHIC",
        ACTION_NEEDS_ASSISTANCE,
        None,
    ),

    (
        "LinkedIn ignores neighboring sponsorship context",
        "LinkedIn Profile*",
        "text",
        "LINKEDIN",
        ACTION_PROFILE_VALUE,
        None,
        (
            "LinkedIn Profile* Do you now or in the future "
            "require immigration support or visa sponsorship?"
        ),
    ),

    (
        "Application source ignores neighboring sponsorship context",
        "How did you hear about this job?*",
        "text",
        "APPLICATION_SOURCE",
        ACTION_NEEDS_ASSISTANCE,
        None,
        (
            "How did you hear about this job?* "
            "Do you now or in the future require visa sponsorship?"
        ),
    ),

    (
        "Robinhood now-or-future parenthetical sponsorship",
        "Will you now (or in the future) require visa sponsorship in order to work in the US?",
        "text",
        "SPONSORSHIP_NOW_OR_FUTURE",
        ACTION_FIXED_ANSWER,
        "Yes",
    ),

    (
        "Military status is demographic, not ITAR",
        "What is your military status?",
        "text",
        "VOLUNTARY_DEMOGRAPHIC",
        ACTION_NEEDS_ASSISTANCE,
        None,
    ),

    (
        "Hispanic Latino is demographic",
        "Are you Hispanic/Latino?",
        "text",
        "VOLUNTARY_DEMOGRAPHIC",
        ACTION_NEEDS_ASSISTANCE,
        None,
    ),

    (
        "LGBTQ is demographic",
        "Do you identify as part of the LGBTQ+ community?",
        "text",
        "VOLUNTARY_DEMOGRAPHIC",
        ACTION_NEEDS_ASSISTANCE,
        None,
    ),

    (
        "Country is precise",
        "Country*",
        "text",
        "COUNTRY",
        ACTION_PROFILE_VALUE,
        None,
    ),

    (
        "Location City is precise",
        "Location (City)*",
        "text",
        "CITY",
        ACTION_PROFILE_VALUE,
        None,
    ),

    (
        "State is precise",
        "State",
        "text",
        "STATE_OR_PROVINCE",
        ACTION_PROFILE_VALUE,
        None,
    ),

    (
        "Postal code is precise",
        "Zip Code",
        "text",
        "POSTAL_CODE",
        ACTION_PROFILE_VALUE,
        None,
    ),

    (
        "Street address is precise",
        "Street Address",
        "text",
        "STREET_ADDRESS",
        ACTION_PROFILE_VALUE,
        None,
    ),

    (
        "Preferred office location is not current address",
        "What is your preferred office location?",
        "text",
        "OFFICE_PREFERENCE",
        ACTION_NEEDS_ASSISTANCE,
        None,
    ),

    (
        "Current US location",
        "Are you currently located in the US?",
        "text",
        "CURRENT_US_LOCATION",
        ACTION_PROFILE_VALUE,
        None,
    ),

    (
        "Education school",
        "School",
        "text",
        "EDUCATION_SCHOOL",
        ACTION_PROFILE_VALUE,
        None,
    ),

    (
        "Education degree",
        "Degree",
        "text",
        "EDUCATION_DEGREE",
        ACTION_PROFILE_VALUE,
        None,
    ),

    (
        "Education discipline",
        "Discipline",
        "text",
        "EDUCATION_DISCIPLINE",
        ACTION_PROFILE_VALUE,
        None,
    ),

    (
        "Relevant experience self report",
        "Please input the total years of experience you have that are relevant for this role.",
        "text",
        "EXPERIENCE_SELF_REPORT",
        ACTION_NEEDS_ASSISTANCE,
        None,
    ),

    (
        "Referral relationship",
        "Do you know anyone currently at Glean?",
        "text",
        "REFERRAL_RELATIONSHIP",
        ACTION_NEEDS_ASSISTANCE,
        None,
    ),

    (
        "Hybrid work commitment",
        "Are you willing and able to commit to the hybrid policy if hired?",
        "text",
        "WORK_LOCATION_COMMITMENT",
        ACTION_NEEDS_ASSISTANCE,
        None,
    ),

    (
        "reCAPTCHA",
        "g-recaptcha-response",
        "textarea",
        "TECHNICAL_CONTROL",
        ACTION_IGNORE,
        None,
    ),

    (
        "Unknown",
        "Describe your favorite technical problem.",
        "textarea",
        "UNKNOWN_CUSTOM_FIELD",
        ACTION_NEEDS_ASSISTANCE,
        None,
    ),
]


def main():
    print()
    print("=" * 90)
    print("BROWSER FIELD CLASSIFIER V1.5 TEST")
    print("=" * 90)
    print()

    passed = 0

    for index, test in enumerate(TESTS, start=1):
        (
            name,
            label,
            field_type,
            expected_category,
            expected_action,
            expected_answer,
            *rest,
        ) = test

        context_text = (
            rest[0]
            if rest
            else None
        )

        decision = classify_field(
            label=label,
            field_type=field_type,
            context_text=context_text,
        )

        ok = (
            decision.category == expected_category
            and decision.action == expected_action
            and decision.fixed_answer == expected_answer
        )

        print(
            f"{index:02}. "
            f"{'✅ PASS' if ok else '❌ FAIL'} — "
            f"{name}"
        )

        if ok:
            passed += 1
        else:
            print(
                f"    Expected: {expected_category} / "
                f"{expected_action} / {expected_answer}"
            )
            print(
                f"    Actual:   {decision.category} / "
                f"{decision.action} / {decision.fixed_answer}"
            )

    failed = len(TESTS) - passed

    print()
    print("=" * 90)
    print(f"Passed: {passed}/{len(TESTS)}")
    print(f"Failed: {failed}/{len(TESTS)}")
    print()

    if failed:
        raise SystemExit(1)

    print(
        "✅ BROWSER FIELD CLASSIFIER "
        "V1.5 TEST PASSED"
    )
    print("=" * 90)


if __name__ == "__main__":
    main()
