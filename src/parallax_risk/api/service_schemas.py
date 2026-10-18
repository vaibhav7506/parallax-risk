"""Pydantic envelopes for nominal schema-1 commands; domain constructors validate economics."""

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StrictBool, StrictInt, StrictStr

from parallax_risk.application.governance_reports import ReportKind


class Boundary(BaseModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", allow_inf_nan=False, hide_input_in_errors=True
    )


class ObjectInput(Boundary):
    key: StrictStr = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    data: dict[str, JsonValue]


class JobInput(Boundary):
    model_id: StrictStr = Field(min_length=1, max_length=128)
    version_id: StrictStr = Field(min_length=1, max_length=128)
    is_synthetic: StrictBool
    calibration_job: StrictStr | None = None
    payload: dict[str, JsonValue]


class GovernanceInput(Boundary):
    document: dict[str, JsonValue]
    expected_revision: StrictInt = Field(ge=0)
    reason: StrictStr = Field(min_length=1, max_length=2048)


class ReportInput(Boundary):
    key: StrictStr = Field(min_length=1, max_length=128)
    kind: ReportKind
    source_job: StrictStr | None = None
    governance_keys: tuple[tuple[StrictStr, StrictStr], ...] = ()
    interpretation: StrictStr = Field(min_length=1, max_length=8192)
    governance_synthetic: StrictBool | None = None


class DataResponse(Boundary):
    data: JsonValue


class Problem(Boundary):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str
    correlation_id: str
