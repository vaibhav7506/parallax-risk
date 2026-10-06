"""Owned PCG64DXSM normals and complete, scrambled Sobol finite-bit designs."""

from dataclasses import dataclass
from enum import StrEnum

import numpy as np
from scipy.special import ndtri
from scipy.stats import qmc

from parallax_risk.common.errors import SimulationError
from parallax_risk.domain.simulation.arrays import FloatArray, integer, power_of_two


class SequenceKind(StrEnum):
    PSEUDO = "pseudo"
    SOBOL = "sobol"


@dataclass(frozen=True, slots=True)
class StreamKey:
    """Order-independent SeedSequence address: root uint64 seed and uint32 path IDs."""

    seed: int
    stream: int = 0
    substream: int = 0

    def __post_init__(self) -> None:
        integer(self.seed, "seed", minimum=0, maximum=2**64 - 1)
        integer(self.stream, "stream", minimum=0, maximum=2**32 - 1)
        integer(self.substream, "substream", minimum=0, maximum=2**32 - 1)

    def generator(self) -> np.random.Generator:
        sequence = np.random.SeedSequence(self.seed, spawn_key=(self.stream, self.substream))
        return np.random.Generator(np.random.PCG64DXSM(sequence))


@dataclass(frozen=True, slots=True)
class SequenceSpec:
    key: StreamKey
    kind: SequenceKind = SequenceKind.PSEUDO
    antithetic: bool = False
    sobol_bits: int = 30

    def __post_init__(self) -> None:
        if not isinstance(self.key, StreamKey) or not isinstance(self.kind, SequenceKind):
            raise SimulationError("Explicit stream key and sequence kind are required")
        if not isinstance(self.antithetic, bool):
            raise SimulationError("Antithetic selection must be boolean")
        integer(self.sobol_bits, "Sobol bits", minimum=1, maximum=52)
        if self.kind == SequenceKind.SOBOL and self.antithetic:
            raise SimulationError("Combining Sobol with antithetic reflection is unsupported")

    @property
    def algorithm(self) -> str:
        return (
            "PCG64DXSM.standard_normal" if self.kind == SequenceKind.PSEUDO else "Sobol.LMS+shift"
        )

    @property
    def normal_transform(self) -> str:
        return (
            "numpy_ziggurat_float64" if self.kind == SequenceKind.PSEUDO else "ndtri_midpoint_grid"
        )


class NormalStream:
    """A fresh, owned sequential stream; no process-global RNG or mutable shared state.

    Draw order is path, time step, factor (flattened time/factor dimension).
    Antithetic paths are adjacent Z,-Z pairs. Sobol includes every initial point;
    batching only partitions a complete 2**m design, without skipping/thinning.
    """

    def __init__(self, spec: SequenceSpec, dimension: int, total_paths: int) -> None:
        if not isinstance(spec, SequenceSpec):
            raise SimulationError("A validated sequence specification is required")
        self.spec = spec
        self.dimension = integer(dimension, "normal dimension")
        self.total_paths = integer(total_paths, "path count")
        self.generated_paths = 0
        if spec.antithetic and total_paths % 2:
            raise SimulationError("Antithetic path count must be even")
        self._rng = spec.key.generator()
        self._sobol: qmc.Sobol | None = None
        if spec.kind == SequenceKind.SOBOL:
            if dimension > qmc.Sobol.MAXDIM:
                raise SimulationError("Sobol dimension exceeds 21201")
            if not power_of_two(total_paths) or total_paths > 2**spec.sobol_bits:
                raise SimulationError("Sobol requires 2**m paths within the specified bit depth")
            self._sobol = qmc.Sobol(d=dimension, scramble=True, bits=spec.sobol_bits, rng=self._rng)

    def draw(self, count: int) -> FloatArray:
        count = integer(count, "batch path count")
        if self.generated_paths + count > self.total_paths:
            raise SimulationError("Stream draw exceeds the configured complete design")
        if self._sobol is not None:
            if not power_of_two(count):
                raise SimulationError("Sobol batches must be powers of two")
            uniforms = self._sobol.random(count)
            # An explicit quadrature convention, not clipping: center each finite-bit bin.
            normals = np.asarray(
                ndtri(uniforms + 0.5 * 2.0**-self.spec.sobol_bits), dtype=np.float64
            )
        elif self.spec.antithetic:
            if count % 2:
                raise SimulationError("Antithetic batches must preserve whole adjacent pairs")
            base = self._rng.standard_normal((count // 2, self.dimension))
            normals = np.empty((count, self.dimension), dtype=np.float64)
            normals[0::2] = base
            normals[1::2] = -base
        else:
            normals = self._rng.standard_normal((count, self.dimension))
        if not np.all(np.isfinite(normals)):
            raise SimulationError("Normal transformation produced non-finite output")
        self.generated_paths += count
        return normals
