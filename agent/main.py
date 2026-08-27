from src.matching.resume_loader import load_all_resumes


def format_resume_name(name: str) -> str:
    """
    Convert:
        backend_engineer
    into:
        Backend Engineer
    """

    return name.replace("_", " ").title()


def main():

    print()
    print("=" * 70)
    print("MASTER RESUME LOADER TEST")
    print("=" * 70)

    try:
        resumes = load_all_resumes()

    except FileNotFoundError as error:
        print()
        print("ERROR")
        print(error)
        print()
        print(
            "Make sure all 8 PDFs exist inside the "
            "agent/resumes directory."
        )
        return

    print()
    print(f"Resumes loaded successfully: {len(resumes)}")
    print()

    for index, (name, resume) in enumerate(
        resumes.items(),
        start=1,
    ):

        print(f"{index}. {format_resume_name(name)}")
        print(f"   File: {resume['filename']}")
        print(f"   Characters extracted: {resume['characters']}")
        print(f"   Words extracted: {resume['words']}")

        # Print a small preview so we can verify that
        # actual resume text was extracted.
        preview = resume["text"][:160].replace("\n", " ")

        print(f"   Preview: {preview}...")
        print()

    print("=" * 70)
    print("RESUME LOADER TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
