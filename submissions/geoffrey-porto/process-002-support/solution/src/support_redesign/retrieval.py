"""Índice de tickets similares e Recall@k (feature indice-resolucao)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np


class SimilarIndex:
    """Busca por cosseno sobre embeddings normalizados — só com o treino."""

    def __init__(
        self,
        embeddings: np.ndarray,
        labels: Sequence[str],
        texts: Sequence[str],
        ids: Sequence[int],
    ) -> None:
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        self.matrix = (embeddings / np.clip(norms, 1e-12, None)).astype(np.float32)
        self.labels = np.asarray(labels)
        self.texts = list(texts)
        self.ids = np.asarray(ids)

    def search(
        self, queries: np.ndarray, k: int, batch: int = 1024
    ) -> tuple[np.ndarray, np.ndarray]:
        q = queries / np.clip(
            np.linalg.norm(queries, axis=1, keepdims=True), 1e-12, None
        )
        q = q.astype(np.float32)
        idx_out, sim_out = [], []
        for start in range(0, len(q), batch):
            sims = q[start : start + batch] @ self.matrix.T
            top = np.argpartition(-sims, k, axis=1)[:, :k]
            top_sims = np.take_along_axis(sims, top, axis=1)
            order = np.argsort(-top_sims, axis=1)
            idx_out.append(np.take_along_axis(top, order, axis=1))
            sim_out.append(np.take_along_axis(top_sims, order, axis=1))
        return np.vstack(idx_out), np.vstack(sim_out)

    def similar(self, query: np.ndarray, k: int = 5) -> list[dict[str, Any]]:
        idx, sims = self.search(query.reshape(1, -1), k)
        return [
            {
                "row_id": int(self.ids[i]),
                "fila": str(self.labels[i]),
                "similaridade": float(s),
                "texto": self.texts[i][:200],
            }
            for i, s in zip(idx[0], sims[0], strict=True)
        ]


def recall_at_k(
    index: SimilarIndex,
    queries: np.ndarray,
    query_labels: Sequence[str],
    ks: Sequence[int],
) -> dict[str, float]:
    idx, _ = index.search(queries, max(ks))
    neigh = index.labels[idx]
    truth = np.asarray(query_labels)[:, None]
    return {
        f"recall@{k}": float((neigh[:, :k] == truth).any(axis=1).mean()) for k in ks
    }


def chance_recall_at_k(
    train_labels: Sequence[str], query_labels: Sequence[str], ks: Sequence[int]
) -> dict[str, float]:
    """Acerto esperado sorteando k vizinhos com a distribuição de classes do índice."""
    values, counts = np.unique(np.asarray(train_labels), return_counts=True)
    share = dict(zip(values, counts / counts.sum(), strict=True))
    p = np.array([share[y] for y in query_labels])
    return {f"recall@{k}": float(np.mean(1 - (1 - p) ** k)) for k in ks}
