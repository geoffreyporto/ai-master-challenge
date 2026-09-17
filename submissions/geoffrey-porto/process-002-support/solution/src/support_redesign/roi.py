"""Cenário de ROI com premissas explícitas (feature cenario-roi).

Conservador de propósito: não credita à IA os erros que a triagem humana
também comete hoje (taxa desconhecida, Q-002) e desconta todo erro automático
como retrabalho.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

BANDS = ("baixa", "base", "alta")
ORIGINS = {"readme", "medido", "premissa"}


def load_assumptions(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text())


def _band(param: dict[str, Any], band: str) -> float:
    value = param["valor"]
    return float(value[band] if isinstance(value, dict) else value)


def scenario(
    assumptions: dict[str, Any], coverage: float, precision: float, band: str
) -> dict[str, float]:
    tickets_month = _band(assumptions["tickets_per_year"], band) / 12
    auto = tickets_month * coverage
    saved = auto * _band(assumptions["triage_minutes_per_ticket"], band) / 60
    misroutes = auto * (1 - precision)
    rework = misroutes * _band(assumptions["rework_minutes_per_misroute"], band) / 60
    net = saved - rework
    cost = _band(assumptions["loaded_cost_brl_per_hour"], band)
    return {
        "tickets_month": tickets_month,
        "auto_tickets_month": auto,
        "triage_hours_saved_month": saved,
        "misroutes_month": misroutes,
        "rework_hours_month": rework,
        "net_hours_month": net,
        "net_brl_month": net * cost,
        "net_brl_year": net * cost * 12,
    }


def roi(
    assumptions: dict[str, Any], coverage: float, precision: float
) -> dict[str, Any]:
    return {band: scenario(assumptions, coverage, precision, band) for band in BANDS}
