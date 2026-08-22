"""Job sources — pluggable adapters + the source registry."""
from __future__ import annotations

from app.sources.ashby import AshbySource
from app.sources.base import JobSource
from app.sources.greenhouse import GreenhouseSource
from app.sources.lever import LeverSource

_BUILDERS = {
    "greenhouse": GreenhouseSource,
    "lever": LeverSource,
    "ashby": AshbySource,
}


def build_source(source_type: str, token: str) -> JobSource:
    try:
        return _BUILDERS[source_type](token)
    except KeyError as e:
        raise ValueError(
            f"Unknown source type '{source_type}'. Supported: {', '.join(_BUILDERS)}"
        ) from e


# A curated set of real ATS boards for well-known SF Bay Area tech employers.
# Discovery reports results per source, so a board that has moved off this ATS
# (and 404s) is surfaced as an error rather than breaking the run. Users can
# still POST their own list to /discovery/run.
DEFAULT_SOURCES: list[dict[str, str]] = [
    {"type": "greenhouse", "token": "anthropic"},
    {"type": "ashby", "token": "openai"},
    {"type": "greenhouse", "token": "stripe"},
    {"type": "greenhouse", "token": "databricks"},
    {"type": "greenhouse", "token": "airbnb"},
    {"type": "greenhouse", "token": "coinbase"},
    {"type": "greenhouse", "token": "dropbox"},
    {"type": "greenhouse", "token": "instacart"},
    {"type": "greenhouse", "token": "doordashusa"},
    {"type": "greenhouse", "token": "brex"},
    {"type": "greenhouse", "token": "samsara"},
    {"type": "greenhouse", "token": "robinhood"},
    {"type": "greenhouse", "token": "gitlab"},
    {"type": "ashby", "token": "ramp"},
]

__all__ = ["JobSource", "build_source", "DEFAULT_SOURCES",
           "GreenhouseSource", "LeverSource", "AshbySource"]
