"""Job matching — deterministic keyword scoring against a candidate profile.

Public API:

- ``JobProfile`` / ``JobScore`` / ``score_job`` — pure scoring primitives
- ``rank_jobs`` — score the whole database and persist the results
"""

from matching.scorer import JobProfile, JobScore, score_job
from matching.service import RankedJob, RankingResult, rank_jobs

__all__ = [
    "JobProfile",
    "JobScore",
    "RankedJob",
    "RankingResult",
    "rank_jobs",
    "score_job",
]
