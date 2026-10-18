"""Authentication port and explicit research-service permissions; no HTTP dependency."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from parallax_risk.common.errors import ParallaxError
from parallax_risk.common.identifiers import Identifier


class ServiceError(ParallaxError):
    """Public fixed error code/status, without input values or credentials."""

    def __init__(self, status: int, code: str) -> None:
        super().__init__(code)
        self.status = status
        self.code = code


class Role(StrEnum):
    READER = "reader"
    ANALYST = "analyst"
    VALIDATOR = "validator"
    APPROVER = "approver"
    OPERATOR = "operator"


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    roles: frozenset[Role]

    def __post_init__(self) -> None:
        Identifier(self.subject)
        if (
            not isinstance(self.roles, frozenset)
            or not self.roles
            or any(not isinstance(r, Role) for r in self.roles)
        ):
            raise ServiceError(401, "invalid_principal")

    def require(self, role: Role) -> None:
        if role not in self.roles:
            raise ServiceError(403, "role_required")


class Authenticator(Protocol):
    def authenticate(self, token: str | None) -> Principal:
        """Authenticate a credential without logging or returning its secret."""
        ...
