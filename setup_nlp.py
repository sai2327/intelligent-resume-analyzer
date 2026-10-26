"""
One-time environment setup script for the NLP pipeline.

Downloads all NLTK corpora and the spaCy English model required by the
Resume Analyzer. Run this once after installing requirements.txt:

    .venv\\Scripts\\python.exe setup_nlp.py
"""

import subprocess
import sys

import nltk

NLTK_RESOURCES = ["punkt", "punkt_tab", "stopwords", "wordnet", "omw-1.4"]
SPACY_MODEL = "en_core_web_sm"


def download_nltk_resources() -> list:
    failed = []
    for resource in NLTK_RESOURCES:
        print(f"[nltk] downloading '{resource}' ...")
        try:
            ok = nltk.download(resource, quiet=False)
        except Exception as exc:  # pragma: no cover - network/environment issues
            print(f"[nltk] ERROR downloading '{resource}': {exc}")
            ok = False
        if not ok:
            failed.append(resource)
    return failed


def download_spacy_model() -> bool:
    print(f"[spacy] downloading '{SPACY_MODEL}' model ...")
    try:
        subprocess.run(
            [sys.executable, "-m", "spacy", "download", SPACY_MODEL],
            check=True,
        )
        return True
    except subprocess.CalledProcessError as exc:
        print(f"[spacy] ERROR downloading '{SPACY_MODEL}': {exc}")
        return False


def main() -> None:
    failed_nltk = download_nltk_resources()
    spacy_ok = download_spacy_model()

    print("\n" + "=" * 60)
    if not failed_nltk:
        print("All NLTK resources downloaded successfully.")
    else:
        print(f"WARNING: failed NLTK resources: {failed_nltk}")

    if spacy_ok:
        print(f"spaCy model '{SPACY_MODEL}' downloaded successfully.")
    else:
        print(
            f"WARNING: spaCy model '{SPACY_MODEL}' could not be downloaded. "
            "Name extraction will fall back to regex-only heuristics."
        )
    print("=" * 60)


if __name__ == "__main__":
    main()
