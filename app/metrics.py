"""Prometheus-метрики для мониторинга активности турниров."""

from __future__ import annotations

_DISABLED_REASON = "metrics temporarily disabled"


def start_metrics_server(port: int) -> None:
    """Отключено: endpoint метрик временно не запускается."""
    _ = (port, _DISABLED_REASON)


def record_status(status: str) -> None:
    """Отключено: статусные метрики временно не собираются."""
    _ = (status, _DISABLED_REASON)


def record_tournament_created(creator_alias: str | None) -> None:
    """Отключено: метрики созданных турниров временно не собираются."""
    _ = (creator_alias, _DISABLED_REASON)


def record_tournament_finished(creator_alias: str | None, *, forced: bool) -> None:
    """Отключено: метрики завершенных турниров временно не собираются."""
    _ = (creator_alias, forced, _DISABLED_REASON)
