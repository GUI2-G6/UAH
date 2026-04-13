from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from app.core.config import settings
from app.providers.adzuna import AdzunaJobProvider
from app.providers.arbeitnow import ArbeitnowJobProvider
from app.providers.base import JobProvider
from app.providers.careerjet import CareerjetJobProvider
from app.providers.findwork import FindworkJobProvider
from app.providers.jooble import JoobleJobProvider
from app.providers.the_muse import TheMuseJobProvider

SweepMode = Literal["category", "global", "matrix", "disabled"]
ProviderState = Literal["active", "dormant"]


@dataclass(frozen=True)
class ProviderAttribution:
    """Frontend attribution details for one provider."""

    label: str
    url: str
    required: bool
    logo_url: str | None = None
    salary_label: str | None = None
    salary_url: str | None = None


@dataclass(frozen=True)
class ProviderDefinition:
    """Registry entry describing one upstream jobs provider."""

    name: str
    adapter_cls: type[JobProvider]
    default_state: ProviderState
    sweep_mode: SweepMode
    scheduled_interval_minutes: int | None
    attribution: ProviderAttribution
    daily_request_budget: int | None = None
    enable_in_thin_sync: bool = True


@dataclass(frozen=True)
class ProviderControls:
    """Resolved enable/disable flags for one provider."""

    ingest_enabled: bool
    display_enabled: bool
    scheduled_enabled: bool
    status: str


PROVIDER_ATTRIBUTION: dict[str, dict[str, str | bool | None]] = {
    "the_muse": {
        "label": "The Muse",
        "url": "https://www.themuse.com",
        "required": True,
        "logo_url": None,
    },
    "adzuna": {
        "label": "Jobs by Adzuna",
        "url": "https://www.adzuna.co.uk",
        "required": True,
        "logo_url": "https://www.adzuna.co.uk/press.html",
        "salary_label": "Adzuna Jobsworth",
        "salary_url": "https://www.adzuna.co.uk/jobs/salary-predictor.html",
    },
    "arbeitnow": {
        "label": "Arbeitnow",
        "url": "https://www.arbeitnow.com",
        "required": False,
        "logo_url": None,
    },
    "findwork": {
        "label": "Findwork",
        "url": "https://findwork.dev",
        "required": False,
        "logo_url": None,
    },
    "jooble": {
        "label": "Jooble",
        "url": "https://jooble.org",
        "required": False,
        "logo_url": None,
    },
    "careerjet": {
        "label": "Careerjet",
        "url": "https://www.careerjet.com",
        "required": False,
        "logo_url": None,
    },
}

_PROVIDER_DEFINITIONS: dict[str, ProviderDefinition] = {
    # TODO: Register future providers here and extend the env control defaults at the same time.
    "the_muse": ProviderDefinition(
        name="the_muse",
        adapter_cls=TheMuseJobProvider,
        default_state="active",
        sweep_mode="category",
        scheduled_interval_minutes=None,
        attribution=ProviderAttribution(**PROVIDER_ATTRIBUTION["the_muse"]),
    ),
    "arbeitnow": ProviderDefinition(
        name="arbeitnow",
        adapter_cls=ArbeitnowJobProvider,
        default_state="active",
        sweep_mode="global",
        scheduled_interval_minutes=120,
        attribution=ProviderAttribution(**PROVIDER_ATTRIBUTION["arbeitnow"]),
    ),
    "findwork": ProviderDefinition(
        name="findwork",
        adapter_cls=FindworkJobProvider,
        default_state="dormant",
        sweep_mode="global",
        scheduled_interval_minutes=240,
        attribution=ProviderAttribution(**PROVIDER_ATTRIBUTION["findwork"]),
    ),
    "jooble": ProviderDefinition(
        name="jooble",
        adapter_cls=JoobleJobProvider,
        default_state="dormant",
        sweep_mode="matrix",
        scheduled_interval_minutes=360,
        attribution=ProviderAttribution(**PROVIDER_ATTRIBUTION["jooble"]),
    ),
    "adzuna": ProviderDefinition(
        name="adzuna",
        adapter_cls=AdzunaJobProvider,
        default_state="dormant",
        sweep_mode="category",
        scheduled_interval_minutes=720,
        attribution=ProviderAttribution(**PROVIDER_ATTRIBUTION["adzuna"]),
        daily_request_budget=max(int(settings.ADZUNA_DAILY_REQUEST_BUDGET), 1),
    ),
    "careerjet": ProviderDefinition(
        name="careerjet",
        adapter_cls=CareerjetJobProvider,
        default_state="dormant",
        sweep_mode="disabled",
        scheduled_interval_minutes=None,
        attribution=ProviderAttribution(**PROVIDER_ATTRIBUTION["careerjet"]),
        enable_in_thin_sync=False,
    ),
}


def _default_controls(definition: ProviderDefinition) -> ProviderControls:
    ingest_enabled = definition.default_state == "active"
    display_enabled = definition.default_state == "active"
    scheduled_enabled = ingest_enabled and definition.sweep_mode != "disabled"
    return ProviderControls(
        ingest_enabled=ingest_enabled,
        display_enabled=display_enabled,
        scheduled_enabled=scheduled_enabled,
        status="active" if ingest_enabled or display_enabled or scheduled_enabled else "dormant",
    )


def _resolve_status(*, ingest_enabled: bool, display_enabled: bool, scheduled_enabled: bool, default_state: ProviderState) -> str:
    if ingest_enabled and display_enabled and (scheduled_enabled or default_state == "dormant"):
        return "active"
    if not ingest_enabled and not display_enabled and not scheduled_enabled:
        return "dormant"
    return "partial"


def get_provider_catalog() -> dict[str, ProviderDefinition]:
    """Return the full provider registry keyed by provider slug."""
    return dict(_PROVIDER_DEFINITIONS)


def get_provider_definition(provider_name: str) -> ProviderDefinition:
    """Return one provider definition by its stable slug."""
    normalized = (provider_name or "").strip().lower()
    definition = _PROVIDER_DEFINITIONS.get(normalized)
    if definition is None:
        raise ValueError(f"Unsupported job provider '{provider_name}'")
    return definition


def get_provider_controls(provider_name: str) -> ProviderControls:
    """Resolve ingest/display/schedule controls for one provider."""
    definition = get_provider_definition(provider_name)
    defaults = _default_controls(definition)
    configured = settings.JOB_PROVIDER_CONTROLS.get(definition.name, {})

    ingest_enabled = bool(configured.get("ingest_enabled", defaults.ingest_enabled))
    display_enabled = bool(configured.get("display_enabled", defaults.display_enabled))
    scheduled_enabled = bool(configured.get("scheduled_enabled", defaults.scheduled_enabled))

    # Backward compatibility: legacy scheduled provider list can explicitly opt providers in.
    if definition.name in settings.JOB_SYNC_ENABLED_PROVIDERS and definition.sweep_mode != "disabled":
        scheduled_enabled = True

    if not ingest_enabled:
        scheduled_enabled = False

    return ProviderControls(
        ingest_enabled=ingest_enabled,
        display_enabled=display_enabled,
        scheduled_enabled=scheduled_enabled,
        status=_resolve_status(
            ingest_enabled=ingest_enabled,
            display_enabled=display_enabled,
            scheduled_enabled=scheduled_enabled,
            default_state=definition.default_state,
        ),
    )


def list_provider_statuses() -> list[dict[str, object]]:
    """Return provider metadata plus resolved status flags for API consumers."""
    statuses: list[dict[str, object]] = []
    for definition in _PROVIDER_DEFINITIONS.values():
        controls = get_provider_controls(definition.name)
        statuses.append(
            {
                "provider": definition.name,
                "default_state": definition.default_state,
                "sweep_mode": definition.sweep_mode,
                "scheduled_interval_minutes": definition.scheduled_interval_minutes,
                "ingest_enabled": controls.ingest_enabled,
                "display_enabled": controls.display_enabled,
                "scheduled_enabled": controls.scheduled_enabled,
                "status": controls.status,
                "attribution": asdict(definition.attribution),
            }
        )
    return statuses


def list_enabled_provider_names(*, control_name: Literal["ingest", "display", "scheduled"]) -> list[str]:
    """Return provider slugs that are enabled for the requested control plane."""
    enabled: list[str] = []
    for definition in _PROVIDER_DEFINITIONS.values():
        controls = get_provider_controls(definition.name)
        if control_name == "ingest" and controls.ingest_enabled:
            enabled.append(definition.name)
        elif control_name == "display" and controls.display_enabled:
            enabled.append(definition.name)
        elif control_name == "scheduled" and controls.scheduled_enabled:
            enabled.append(definition.name)
    return enabled


def list_thin_sync_provider_names() -> list[str]:
    """Return providers that should participate in thin-result sync triggers."""
    providers: list[str] = []
    for definition in _PROVIDER_DEFINITIONS.values():
        controls = get_provider_controls(definition.name)
        if not controls.ingest_enabled or not controls.scheduled_enabled or not definition.enable_in_thin_sync:
            continue
        if definition.sweep_mode == "disabled":
            continue
        providers.append(definition.name)
    return providers


def get_adapter(provider_name: str) -> JobProvider:
    """Return a provider adapter instance for the requested provider."""
    definition = get_provider_definition(provider_name)
    return definition.adapter_cls()
