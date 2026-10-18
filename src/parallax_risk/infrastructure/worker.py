"""Bounded local asynchronous executor for durable PostgreSQL claims.

Threads share validated stateless numerical engines; there is no global RNG.
Failed persistence halts that worker, retains uncertainty, and never retries a
possibly committed run automatically. Distributed implementations can use the port.
"""

from datetime import UTC, datetime
from threading import Event, Thread
from uuid import uuid4

from parallax_risk.application.service import RiskService
from parallax_risk.common.errors import ConfigurationError, InfrastructureError, ParallaxError
from parallax_risk.common.logging import WorkflowLogger


class ThreadExecutor:
    def __init__(self, service: RiskService, logger: WorkflowLogger, workers: int = 1) -> None:
        if type(workers) is not int or not 1 <= workers <= 4:
            raise ConfigurationError("Local executor requires 1–4 workers")
        self.service, self.logger, self.count = service, logger, workers
        self.stop = Event()
        self.threads: list[Thread] = []

    @property
    def healthy(self) -> bool:
        return len(self.threads) == self.count and all(t.is_alive() for t in self.threads)

    def start(self) -> None:
        if self.threads or self.stop.is_set():
            raise ConfigurationError("Executor cannot be started twice")
        self.service.jobs.ready()
        for _ in range(self.count):
            thread = Thread(target=self._loop, args=(uuid4().hex,), name="parallax-risk-compute")
            self.threads.append(thread)
            thread.start()

    def close(self) -> None:
        self.stop.set()
        for thread in self.threads:
            thread.join()

    def _loop(self, claim: str) -> None:
        while not self.stop.is_set():
            try:
                job = self.service.jobs.claim_next(claim, datetime.now(UTC))
            except Exception as error:
                self.logger.event(
                    "worker_claim_failed", outcome="halted", error_type=type(error).__name__
                )
                return
            if job is None:
                self.stop.wait(0.1)
                continue
            result, code = None, None
            try:
                result = self.service.compute(job, datetime.now(UTC))
            except InfrastructureError as error:
                self.logger.event(
                    "worker_persistence_uncertain",
                    run_id=job.correlation_id,
                    outcome="halted",
                    error_type=type(error).__name__,
                )
                return
            except ParallaxError as error:
                code = "calculation_rejected"
                self.logger.event(
                    "calculation_rejected",
                    run_id=job.correlation_id,
                    outcome="failed",
                    error_type=type(error).__name__,
                )
            except Exception as error:
                code = "internal_calculation_failure"
                self.logger.event(
                    "calculation_failed",
                    run_id=job.correlation_id,
                    outcome="failed",
                    error_type=type(error).__name__,
                )
            try:
                self.service.jobs.finish(job, result, code, datetime.now(UTC))
            except Exception as error:
                self.logger.event(
                    "worker_completion_uncertain",
                    run_id=job.correlation_id,
                    outcome="halted",
                    error_type=type(error).__name__,
                )
                return
            self.logger.event(
                "job_completed",
                run_id=job.correlation_id,
                outcome="succeeded" if code is None else "failed",
            )
