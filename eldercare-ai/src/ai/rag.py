"""Retrieval-augmented answers over a small local knowledge base (src/ai/knowledge/*.md).

Retrieval is local ML: TF-IDF vectors and cosine similarity (scikit-learn). Generation is optional:
- without Gemini: the best matching passages are shown as they are, with their source titles (extractive)
- with Gemini on: it may rephrase, but ONLY from the retrieved passages, must cite them as [1], [2], and its
  answer is rejected (and the extractive answer shown instead) if it cites nothing valid.
If nothing matches well enough the assistant says so instead of guessing.
The knowledge base is demo content written for this project: general wellbeing information, not medical advice.
"""
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

KB_DIR = Path(__file__).parent / "knowledge"
MIN_SCORE = 0.12
TOP_K = 3


@dataclass(frozen=True)
class Passage:
    doc_id: str
    title: str
    text: str
    score: float = 0.0


@lru_cache(maxsize=1)
def _index():
    passages = []
    for f in sorted(KB_DIR.glob("*.md")):
        lines = f.read_text(encoding="utf-8").strip().split("\n")
        title = lines[0].lstrip("# ").strip()
        for para in [p.strip() for p in "\n".join(lines[1:]).split("\n\n") if p.strip()]:
            passages.append(Passage(f.stem, title, para))
    # titles are added to the searchable text so a question matching a title finds its paragraphs
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
    matrix = vec.fit_transform([f"{p.title}. {p.text}" for p in passages])
    return passages, vec, matrix


def retrieve(query: str, k: int = TOP_K, min_score: float = MIN_SCORE):
    passages, vec, matrix = _index()
    sims = cosine_similarity(vec.transform([query]), matrix)[0]
    ranked = sorted(range(len(passages)), key=lambda i: -sims[i])[:k]
    return [Passage(passages[i].doc_id, passages[i].title, passages[i].text, float(sims[i]))
            for i in ranked if sims[i] >= min_score]


def extractive_answer(passages) -> str:
    top = passages[0]
    chosen = [p for p in passages if p.doc_id == top.doc_id][:2]
    body = "\n\n".join(p.text for p in chosen)
    return f"From my knowledge base ({top.title}):\n\n{body}"


def grounded_prompt(question: str, passages):
    numbered = "\n".join(f"[{i}] ({p.title}) {p.text}" for i, p in enumerate(passages, 1))
    system = ("You answer questions for an older adult using ONLY the numbered passages given. If they do not "
              "answer the question, say you do not have that information. Use at most four short, plain sentences "
              "and cite the passages you used like [1]. Never add medical advice, doses or facts that are not in the passages.")
    return system, f"Passages:\n{numbered}\n\nQuestion: {question}"


def valid_citations(answer: str, n_passages: int) -> bool:
    cited = {int(x) for x in re.findall(r"\[(\d+)\]", answer)}
    return bool(cited) and all(1 <= c <= n_passages for c in cited)
