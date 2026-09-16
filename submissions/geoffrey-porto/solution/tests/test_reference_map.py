"""O mapa entre as features da referência e o que este projeto implementa.

Sem este teste, a matriz publicada em `docs/04-matriz-de-features.md` volta a
ser mantida à mão — e a envelhecer em silêncio (foi o que aconteceu: a contagem
publicada dizia 11 parciais quando a tabela tinha 8).
"""

from __future__ import annotations

import re

from churn_diag.account_panel import (
    ACCOUNT_CATEGORICAL,
    ACCOUNT_NUMERIC,
    TIMELINE_COLUMNS,
)
from churn_diag.config import SOLUTION_ROOT
from churn_diag.features import (
    DERIVED_FEATURES,
    IMPLEMENTADA,
    MEDIDA_SOB_BANDEIRA,
    REFERENCE_FEATURES,
    STATUS_EMOJI,
    reference_counts,
)
from churn_diag.risk import CAT_FEATURES, NUMERIC_FEATURES

MATRIX_DOC = SOLUTION_ROOT.parent / "docs" / "04-matriz-de-features.md"
PANEL_COLUMNS = {
    # as derivadas são anexadas depois da montagem do painel (attach_derived),
    # por isso não estão em ACCOUNT_NUMERIC — mas são colunas do painel por conta
    "conta": set(ACCOUNT_NUMERIC) | set(ACCOUNT_CATEGORICAL) | set(DERIVED_FEATURES),
    "diagnostico": set(NUMERIC_FEATURES) | set(CAT_FEATURES),
    # painel só de medição: existe para triagem, nunca para o score (AC-032)
    "triagem": set(TIMELINE_COLUMNS),
}
COM_COLUNA = (IMPLEMENTADA, MEDIDA_SOB_BANDEIRA)
# Tamanhos declarados no documento da referência (docs/referencia/).
REFERENCE_SIZES = {"feature": 20, "controle": 8, "derivada": 3}


def test_registry_covers_the_whole_reference() -> None:
    """@spec:AC-025 — 20 features, 8 controles e 3 derivadas, sem repetição."""
    sizes: dict[str, int] = {}
    for f in REFERENCE_FEATURES:
        sizes[f.group] = sizes.get(f.group, 0) + 1
    assert sizes == REFERENCE_SIZES
    names = [f.name for f in REFERENCE_FEATURES]
    assert len(names) == len(set(names))


def test_implemented_features_point_to_real_columns() -> None:
    """@spec:AC-025 — "implementada" só vale se a coluna existe no painel indicado."""
    for f in REFERENCE_FEATURES:
        if f.status not in COM_COLUNA:
            continue
        assert f.columns, f"{f.name} marcada {f.status} sem coluna"
        for panel, column in f.columns:
            assert panel in PANEL_COLUMNS, f"{f.name}: painel desconhecido {panel}"
            assert column in PANEL_COLUMNS[panel], f"{f.name}: {panel} não tem {column}"


def test_unimplemented_features_state_a_reason() -> None:
    """@spec:AC-025 — o que não existe diz por quê, e não finge ter coluna."""
    for f in REFERENCE_FEATURES:
        if f.status == IMPLEMENTADA:
            continue
        assert len(f.reason) > 20, f"{f.name} sem motivo escrito"
        if f.status == MEDIDA_SOB_BANDEIRA:
            continue  # existe, mas só no painel de triagem
        assert not f.columns, f"{f.name} não implementada mas aponta coluna"


def _matrix_rows() -> list[str]:
    """Linhas das tabelas do registro (seções 3 a 5 do documento)."""
    doc = MATRIX_DOC.read_text(encoding="utf-8")
    block = doc[doc.index("## 3. Matriz das 20 features") : doc.index("## 6. Features")]
    return [line for line in block.splitlines() if line.startswith("|")]


def test_doc_table_matches_the_registry() -> None:
    """@spec:AC-026 — cada feature aparece na tabela com o status do registro."""
    rows = _matrix_rows()
    for f in REFERENCE_FEATURES:
        matching = [r for r in rows if f"`{f.name}`" in r]
        assert len(matching) == 1, f"{f.name}: {len(matching)} linhas na tabela"
        assert STATUS_EMOJI[f.status] in matching[0], (
            f"{f.name}: status do documento difere do registro ({f.status})"
        )


def test_doc_publishes_the_registry_counts() -> None:
    """@spec:AC-026 — a contagem publicada é a do registro, não uma conta à mão."""
    doc = MATRIX_DOC.read_text(encoding="utf-8")
    line = next(
        ln for ln in doc.splitlines() if ln.startswith("Cobertura do registro:")
    )
    rotulos = "|".join(
        (
            "implementadas",
            "em quarentena",
            "excluídas por linha do tempo",
            "não implementadas",
            "medidas sob bandeira",
        )
    )
    published = [int(n) for n in re.findall(rf"(\d+)\s+(?:{rotulos})", line)]
    counts = reference_counts()
    esperado = [
        counts.get(k, 0)
        for k in (
            "implementada",
            "quarentena",
            "excluida_linha_do_tempo",
            "nao_implementada",
            "medida_sob_bandeira",
        )
    ]
    assert published == [n for n in esperado if n]
