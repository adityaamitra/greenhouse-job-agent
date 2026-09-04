# Applicant Profile V1

Create your private file:

```bash
cp config/applicant_profile.example.json config/applicant_profile.json
```

Fill `config/applicant_profile.json` with your own deterministic applicant facts.

**Do not commit the private file.** Add this line to the repository `.gitignore` if it is not already present:

```gitignore
agent/config/applicant_profile.json
```

If your `.gitignore` is inside `agent/` rather than the repository root, use:

```gitignore
config/applicant_profile.json
```

The resolver does not open a browser, fill fields, upload files, or submit an application.
