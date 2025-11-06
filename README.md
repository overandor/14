# Repository Factory

A minimal Flask application for spinning up pre-initialized Git repositories with standardized launch metadata.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Navigate to `http://localhost:8000` and submit the form to generate repositories. The app initializes Git, writes a README with launch destinations, and seeds a `.gitignore` for each repository.

## Configuration

- **Count** – number of repositories to create in a single run (bounded by form controls).
- **Prefix** – base name; sequential strategy appends a numeric suffix, random strategy appends an 8-character hash.
- **Naming Strategy** – sequential or random.
- **Start Index** – first index for sequential naming.

Repositories are emitted under `generated_repos/`. Each includes:

- `README.md` with launch links for Google Colab, Hugging Face Spaces, Replicate, Modal, Vercel, Render, and Netlify.
- `.gitignore` with Python and editor defaults.
- A fresh Git repository initialized via `git init`.

## Testing

```bash
pip install -r requirements-dev.txt
pytest
```
