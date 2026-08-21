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


# A handful of real, verified ATS boards to pull by default (roles relevant to
# the sample profile). Users can POST their own list to /discovery/run.
DEFAULT_SOURCES: list[dict[str, str]] = [
    {"type": "greenhouse", "token": "anthropic"},
    {"type": "ashby", "token": "openai"},
    {"type": "greenhouse", "token": "stripe"},
    {"type": "greenhouse", "token": "databricks"},
]

__all__ = ["JobSource", "build_source", "DEFAULT_SOURCES",
           "GreenhouseSource", "LeverSource", "AshbySource"]
