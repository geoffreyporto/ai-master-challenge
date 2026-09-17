"""Leitura dos dois datasets e split determinístico do Dataset 2."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.model_selection import train_test_split

from support_redesign.config import D1_FILE, D2_FILE, SEED, SPLIT_FRACTIONS


def load_d1(data_dir: Path) -> pl.DataFrame:
    return pl.read_csv(data_dir / D1_FILE).with_columns(
        pl.col("First Response Time").str.to_datetime(strict=False),
        pl.col("Time to Resolution").str.to_datetime(strict=False),
    )


def load_d2(data_dir: Path) -> pl.DataFrame:
    return pl.read_csv(data_dir / D2_FILE).with_row_index("row_id")


@dataclass(frozen=True)
class Split:
    train: pl.DataFrame
    val: pl.DataFrame
    test: pl.DataFrame


def split_d2(d2: pl.DataFrame, seed: int = SEED) -> Split:
    """70/10/20 estratificado por Topic_group."""
    _, val_frac, test_frac = SPLIT_FRACTIONS
    idx = np.arange(d2.height)
    labels = d2["Topic_group"].to_numpy()
    rest, test = train_test_split(
        idx, test_size=test_frac, stratify=labels, random_state=seed
    )
    train, val = train_test_split(
        rest,
        test_size=val_frac / (1 - test_frac),
        stratify=labels[rest],
        random_state=seed,
    )
    return Split(d2[np.sort(train)], d2[np.sort(val)], d2[np.sort(test)])
