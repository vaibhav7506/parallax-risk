"""Finite binary64 arrays; published path buffers are backed by immutable bytes."""

import hashlib
import math
from dataclasses import dataclass
from typing import Self

import numpy as np
from numpy.typing import NDArray

from parallax_risk.common.errors import SimulationError

type FloatArray = NDArray[np.float64]


def integer(value: int, name: str, *, minimum: int = 1, maximum: int = 2**63 - 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise SimulationError(f"{name} must be an integer in [{minimum}, {maximum}]")
    return value


def power_of_two(value: int) -> bool:
    return value > 0 and value & (value - 1) == 0


def finite_array(value: FloatArray, *, ndim: int, name: str) -> FloatArray:
    if not isinstance(value, np.ndarray) or value.dtype != np.dtype(np.float64):
        raise SimulationError(f"{name} must be a binary64 ndarray")
    if value.ndim != ndim or any(size == 0 for size in value.shape):
        raise SimulationError(f"{name} has invalid dimensionality or an empty axis")
    if not np.all(np.isfinite(value)):
        raise SimulationError(f"{name} must contain only finite values")
    return value


@dataclass(frozen=True, slots=True)
class FrozenArray:
    """Little-endian C-order float64 buffer; ndarray views cannot become writable."""

    payload: bytes
    shape: tuple[int, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.payload, bytes)
            or not isinstance(self.shape, tuple)
            or not self.shape
        ):
            raise SimulationError("Frozen arrays require immutable bytes and a nonempty shape")
        for size in self.shape:
            integer(size, "axis size")
        if len(self.payload) != 8 * math.prod(self.shape):
            raise SimulationError("Frozen array buffer length does not match its shape")
        if not np.all(np.isfinite(self.array)):
            raise SimulationError("Frozen array buffer contains non-finite values")

    @classmethod
    def from_array(cls, value: FloatArray) -> Self:
        if not isinstance(value, np.ndarray):
            raise SimulationError("Published arrays require a binary64 ndarray")
        finite_array(value, ndim=value.ndim, name="published array")
        return cls(value.astype("<f8", copy=False).tobytes(order="C"), value.shape)

    @property
    def array(self) -> FloatArray:
        return np.frombuffer(self.payload, dtype="<f8").reshape(self.shape)

    @property
    def nbytes(self) -> int:
        return len(self.payload)

    @property
    def hash(self) -> str:
        """Buffer fingerprint, explicitly separate from canonical JSON metadata hashes."""
        shape = ",".join(map(str, self.shape)).encode("ascii")
        return hashlib.sha256(b"parallax-f64-le-c-v1:" + shape + b":" + self.payload).hexdigest()
