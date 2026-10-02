"""External-resource ports; no ORM types leak into application contracts."""

from typing import Protocol


class ConnectivityProbe(Protocol):
    """Lifecycle-owned dependency probe, injected into service boundaries."""

    def check(self) -> None:
        """Raise InfrastructureError when the dependency cannot be reached."""
        ...

    def close(self) -> None:
        """Release owned resources."""
        ...
