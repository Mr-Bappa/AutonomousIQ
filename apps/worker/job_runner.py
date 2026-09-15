"""Executes `approved` TransformationJobs (FR-11/FR-14/FR-15).

**Demo-level, flagged plainly:** a real worker would run the AI-proposed
transformation code in a sandboxed runtime, on the full dataset (not
just the sample), and version the output. This one does none of that --
it marks the job `running` then immediately `succeeded`, and bumps the
dataset's `version` by one as a stand-in for "a new dataset version was
produced". No actual data transformation happens. This exists so the
`pending_approval -> approved -> succeeded` status lifecycle and the
Approvals-inbox-to-execution wiring can be exercised end-to-end; the
real execution engine (sandboxed runtime, sample vs full-data toggle,
FR-15 memoization by cache_key) is unbuilt.

Run as a one-shot pass (`python -m apps.worker.job_runner`) or call
`run_pending_jobs` from a scheduler/cron -- there's no long-running
poll loop or queue consumer here, deliberately, since Phase 0 has no
message queue (Kafka is explicitly out of scope per the PRD).
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from libs.db import async_session_factory
from libs.models import Dataset, TransformationJob, TransformationJobStatus

logger = logging.getLogger("autonomousiq.worker")


async def run_pending_jobs() -> int:
    """Runs every `approved` job once. Returns how many it processed."""
    processed = 0
    async with async_session_factory() as session:
        result = await session.scalars(
            select(TransformationJob).where(
                TransformationJob.status == TransformationJobStatus.approved
            )
        )
        jobs = list(result)

        for job in jobs:
            job.status = TransformationJobStatus.running
            await session.flush()

            try:
                dataset = await session.get(Dataset, job.dataset_id)
                if dataset is not None:
                    # Stand-in for "produced a new dataset version" --
                    # no actual transformation runs (see module docstring).
                    dataset.version += 1
                job.status = TransformationJobStatus.succeeded
            except Exception:  # noqa: BLE001 -- a real runtime would classify failure modes
                logger.exception("transformation_job_failed", extra={"job_id": str(job.id)})
                job.status = TransformationJobStatus.failed

            processed += 1

        await session.commit()

    return processed


if __name__ == "__main__":
    count = asyncio.run(run_pending_jobs())
    print(f"Processed {count} approved job(s).")
