"""Tests for the deterministic keyword scoring engine.

Pure functions: no database or network involved.
"""

from __future__ import annotations

from matching.scorer import (
    PREFERENCE_WEIGHT,
    ROLE_WEIGHT,
    SKILL_FULL_AT,
    SKILL_WEIGHT,
    JobProfile,
    score_job,
)

PROFILE = JobProfile(
    roles=("Frontend Developer", "Frontend Engineer", "React Developer", "Software Engineer"),
    skills=(
        "React",
        "Next.js",
        "JavaScript",
        "TypeScript",
        "Tailwind CSS",
        "HTML",
        "CSS",
        "Supabase",
        "Git",
        "REST APIs",
    ),
    preferences=("Remote", "Junior / Entry-level", "Internship", "Full-time"),
)

ALL_SKILLS_TEXT = (
    "React, Next.js, JavaScript, TypeScript, Tailwind CSS, HTML, CSS, Supabase, Git and REST APIs."
)


def _job(title: str, description: str = "", location: str = "") -> dict:
    return {"title": title, "location": location, "description": description}


def test_weights_sum_to_100():
    assert ROLE_WEIGHT + SKILL_WEIGHT + PREFERENCE_WEIGHT == 100


def test_full_match_scores_100():
    score = score_job(
        _job(
            title="Frontend Engineer",
            location="Remote",
            description=(
                f"{ALL_SKILLS_TEXT} A junior full-time internship position "
                "for someone who loves the web."
            ),
        ),
        PROFILE,
    )
    assert score.score == 100
    assert score.role_points == ROLE_WEIGHT
    assert score.skill_points == SKILL_WEIGHT
    assert score.preference_points == PREFERENCE_WEIGHT


def test_no_match_scores_zero():
    score = score_job(_job(title="Accountant", description="Excel and tax filing."), PROFILE)
    assert score.score == 0


def test_role_points_require_title_match():
    score = score_job(_job(title="Backend Engineer", description=ALL_SKILLS_TEXT), PROFILE)
    assert score.role_points == 0
    assert score.skill_points == SKILL_WEIGHT


def test_skills_score_scales_up_to_full_credit():
    score = score_job(_job(title="Frontend Developer", description="React and Git only."), PROFILE)
    assert score.role_points == ROLE_WEIGHT
    assert score.skill_points == round(SKILL_WEIGHT * 2 / SKILL_FULL_AT)


def test_skills_reach_full_credit_at_threshold():
    description = ", ".join(PROFILE.skills[:SKILL_FULL_AT])
    score = score_job(_job(title="Frontend Developer", description=description), PROFILE)
    assert score.skill_points == SKILL_WEIGHT


def test_preferences_score_is_proportional():
    score = score_job(
        _job(title="Frontend Developer", description=ALL_SKILLS_TEXT, location="Remote"),
        PROFILE,
    )
    assert score.preference_points == 5  # 1 of 4 preferences (Remote) -> 5 points


def test_matching_is_case_insensitive():
    score = score_job(_job(title="frontend engineer", description="react and javascript"), PROFILE)
    assert score.role_points == ROLE_WEIGHT
    assert "React" in score.matched_skills


def test_word_boundaries_prevent_partial_matches():
    score = score_job(
        _job(title="Frontend Developer", description="digital reactor footage"), PROFILE
    )
    assert "Git" not in score.matched_skills
    assert "React" not in score.matched_skills


def test_role_matches_with_modifiers():
    score = score_job(_job(title="Senior Frontend Engineer"), PROFILE)
    assert "Frontend Engineer" in score.matched_roles


def test_nextjs_variants():
    for text in ("Next.js", "next js", "next-js"):
        score = score_job(_job(title="React Developer", description=text), PROFILE)
        assert "Next.js" in score.matched_skills


def test_synonym_preference_any_term_matches():
    for text in ("junior role", "entry level role", "entry-level role"):
        score = score_job(
            _job(title="Frontend Developer", location="Remote", description=text), PROFILE
        )
        assert "Junior / Entry-level" in score.matched_preferences


def test_missing_skills_are_the_complement():
    score = score_job(_job(title="Frontend Developer", description="React only."), PROFILE)
    assert score.matched_skills == ("React",)
    assert set(score.missing_skills) == set(PROFILE.skills) - {"React"}


def test_empty_profile_scores_zero():
    score = score_job(_job(title="Frontend Engineer", description=ALL_SKILLS_TEXT), JobProfile())
    assert score.score == 0
    assert score.missing_skills == ()
