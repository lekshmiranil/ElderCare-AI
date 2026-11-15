"""Local machine-learning classifiers (scikit-learn). No network, no API.

Method: TF-IDF features (word 1-2 grams + character 2-4 grams, so small typos and
voice-transcript errors still match) feeding a multinomial logistic regression.
They train from the small datasets in data/training.py in well under a second
when first used, so no model files are stored. random_state is fixed: results are repeatable.
"""
import re
from functools import lru_cache

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from .data.training import INTENTS, URGENCY


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9' -]", " ", (text or "").lower())).strip()


def _build() -> Pipeline:
    return Pipeline([
        ("features", FeatureUnion([
            ("word", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True)),
        ])),
        ("clf", LogisticRegression(C=20, max_iter=2000, random_state=0)),
    ])


class TextClassifier:
    def __init__(self, examples: dict):
        texts, labels = [], []
        for label, items in examples.items():
            texts += [normalize(t) for t in items]
            labels += [label] * len(items)
        self.model = _build().fit(texts, labels)
        self.labels = list(self.model.classes_)

    def predict(self, text: str):
        """Return (label, confidence, {label: probability})."""
        probs = self.model.predict_proba([normalize(text)])[0]
        scores = {l: float(p) for l, p in zip(self.labels, probs)}
        best = max(scores, key=scores.get)
        return best, scores[best], scores


def _urgency_examples() -> dict:
    routine = [u for k, items in INTENTS.items() if k not in ("medical_advice", "feeling") for u in items]
    routine += URGENCY["routine_extra"]
    # Feelings like "i am tired" are routine; they are included so the model does not over-trigger.
    routine += INTENTS["feeling"]
    return {"emergency": URGENCY["emergency"], "urgent": URGENCY["urgent"], "routine": routine}


@lru_cache(maxsize=1)
def intent_classifier() -> TextClassifier:
    return TextClassifier(INTENTS)


@lru_cache(maxsize=1)
def urgency_classifier() -> TextClassifier:
    return TextClassifier(_urgency_examples())
