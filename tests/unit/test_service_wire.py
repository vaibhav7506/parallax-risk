"""Nominal schema security, financial input contracts and bounded service work."""

import io
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal

import jsonschema
import pytest

from parallax_risk.application.service_examples import commands
from parallax_risk.application.wire import decode, document, parse, value
from parallax_risk.application.wire_schema import schema
from parallax_risk.application.workflows import COMMANDS, Operation, WorkLimits
from parallax_risk.common.enums import Currency
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.logging import create_logger
from parallax_risk.common.money import Money
from parallax_risk.infrastructure.service_composition import make_workflows


@dataclass(frozen=True)
class Types:
    flag: bool
    count: int
    number: float
    decimal: Decimal
    day: date
    instant: datetime
    binary: bytes
    constant: Literal["yes", 2]
    union: Money | str | None
    fixed: tuple[int, str]
    many: tuple[float, ...]


TYPES = Types(
    True,
    2,
    0.1,
    Decimal("1.2"),
    date(2025, 1, 1),
    datetime(2025, 1, 1, tzinfo=UTC),
    b"\x00\xff",
    "yes",
    Money(Decimal("1"), Currency.USD),
    (2, "x"),
    (0.1, 0.2),
)


def test_wire_nominal_roundtrip_and_schema_all_real_commands():
    for op, command in commands(2).items():
        payload = value(command)
        jsonschema.Draft202012Validator(schema(COMMANDS[op])).validate(payload)
        assert decode(payload, COMMANDS[op]) == command
        assert document(command).hash == document(decode(payload, COMMANDS[op])).hash
    for union in (TYPES.union, "plain", None):
        item = replace(TYPES, union=union)
        assert decode(value(item), Types) == item


@pytest.mark.parametrize(
    "field,bad",
    [
        ("flag", 1),
        ("count", True),
        ("number", True),
        ("number", "0.1"),
        ("number", float("inf")),
        ("decimal", 1.2),
        ("decimal", "nan"),
        ("decimal", "garbage"),
        ("day", "2025-1-1"),
        ("day", "2025-01-01T00:00:00"),
        ("instant", "2025-01-01T00:00:00"),
        ("binary", {"base64": "!!!"}),
        ("binary", {"base64": "AA==", "extra": 1}),
        ("constant", True),
        ("constant", "no"),
        ("fixed", [2]),
        ("fixed", [2, "x", 3]),
        ("many", {}),
        ("many", [True]),
        ("union", {"__type__": "os.system", "args": "whoami"}),
        ("__type__", "os.system"),
        ("unknown", 1),
    ],
)
def test_typed_wire_rejects_untrusted_shapes_and_coercion(field, bad):
    payload = value(TYPES)
    payload[field] = bad
    with pytest.raises(DomainValidationError):
        decode(payload, Types)


@pytest.mark.parametrize("text", ['{"a":1,"a":2}', "NaN", "Infinity", "1e400", "{", "[[[0]]]"])
def test_strict_json_rejects_duplicates_nonfinite_invalid_and_depth(text):
    with pytest.raises(DomainValidationError):
        parse(text, maximum_depth=2)


def test_structural_limits_unsupported_encoding_and_missing_fields():
    with pytest.raises(DomainValidationError):
        parse("[1,2,3]", maximum_nodes=3)
    payload = value(TYPES)
    del payload["flag"]
    with pytest.raises(DomainValidationError):
        decode(payload, Types)
    for item in (set(), float("nan"), Decimal("Infinity")):
        with pytest.raises(DomainValidationError):
            value(item)


@pytest.mark.parametrize("operation", list(Operation))
def test_all_workflow_engines_execute_real_synthetic_inputs(operation):
    command = commands(2)[operation]
    workflows = make_workflows(create_logger(stream=io.StringIO()))
    result = workflows.execute(workflows.prepare(operation, value(command)))
    assert document(result).hash


def test_work_limits_reject_before_financial_computation():
    cases = commands(2)
    for limits, command in (
        (WorkLimits(maximum_paths=1), cases[Operation.SIMULATION]),
        (WorkLimits(maximum_steps=2), cases[Operation.EXPOSURE]),
        (WorkLimits(maximum_work=1), cases[Operation.CAPITAL]),
        (WorkLimits(maximum_output_bytes=1), cases[Operation.SIMULATION]),
    ):
        with pytest.raises(DomainValidationError):
            limits.validate(command)
    for bad in (True, 0, -1):
        with pytest.raises(DomainValidationError):
            WorkLimits(maximum_paths=bad)


@pytest.mark.parametrize(
    "operation,changes",
    [
        (Operation.UNCERTAINTY, {"replicates": 1001}),
        (Operation.CONVERGENCE, {"cases": ()}),
    ],
)
def test_work_budget_invalid_campaigns(operation, changes):
    case = commands(2)[operation]
    if operation == Operation.CONVERGENCE:
        changes = {"cases": case.cases * 9}
    with pytest.raises(DomainValidationError):
        WorkLimits().validate(replace(case, **changes))


def test_search_stress_mutation_and_calibration_budget_limits():
    cases = commands(2)
    search = cases[Operation.ADVERSARIAL]
    stress = cases[Operation.STRESS]
    mutation = cases[Operation.MUTATION]
    calibration = cases[Operation.CALIBRATION]
    for command in (
        replace(search, specification=replace(search.specification, maximum_evaluations=65)),
        replace(stress, scenarios=stress.scenarios * 17),
        replace(mutation, mutations=mutation.mutations * 3),
        replace(calibration, settings=replace(calibration.settings, max_evaluations=1001)),
    ):
        with pytest.raises(DomainValidationError):
            WorkLimits().validate(command)
