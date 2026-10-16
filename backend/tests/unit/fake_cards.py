"""Fakes for the fault-card tests: a bag-of-words embedder (shared words give a graded cosine) and an in-memory
card store with the same `nearest` / `save` interface as clients.firestore.CardStore."""

import hashlib
import math

from models.fault_card import FaultCard

DIM = 768


def embed(texts: list[str], task_type: str) -> list[list[float]]:
    vectors = []
    for text in texts:
        v = [0.0] * DIM
        for word in text.lower().split():
            v[int(hashlib.sha256(word.encode()).hexdigest(), 16) % DIM] += 1.0
        vectors.append(v)
    return vectors


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)) or 1.0)


class FakeCardStore:
    def __init__(self) -> None:
        self.cards: dict[str, tuple[FaultCard, list[float]]] = {}
        self.queries: list[tuple[str, int]] = []

    def nearest(self, brand: str, vector: list[float], limit: int) -> list[tuple[FaultCard, float]]:
        self.queries.append((brand, limit))
        hits = [(card, cosine(v, vector)) for card, v in self.cards.values() if card.brand == brand]
        return sorted(hits, key=lambda hit: hit[1], reverse=True)[:limit]

    def save(self, card: FaultCard, vector: list[float]) -> None:
        self.cards[card.id] = (card, vector)
