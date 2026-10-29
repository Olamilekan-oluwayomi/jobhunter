import { expect, it } from "vitest";
import { fit, eligibility } from "./data";

it("uses backend evidence and scores for live jobs", () => {
  const job = {
    live: true,
    title: "C developer",
    skills: [],
    match: { score: 23, matched_skills: ["C"] },
    eligibility: { status: "restricted", detail: "US residents only" },
  };
  expect(fit(job, { role: "C developer", skills: ["C"] })).toMatchObject({
    score: 23,
    skills: ["C"],
  });
  expect(eligibility(job, {})).toEqual({
    label: "Location restricted",
    tone: "warning",
    detail: "US residents only",
  });
});
