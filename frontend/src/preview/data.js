// Fictional opportunities for the isolated design preview. Never submitted to the API.
export const demoJobs = [
  {
    id: 1,
    company: "Forma",
    mark: "f",
    color: "#eee6ff",
    title: "Frontend Engineer",
    location: "Worldwide",
    region: "worldwide",
    salary: "$70k–$95k",
    type: "Full-time",
    level: "Mid-level",
    source: "Company careers",
    days: 0,
    skills: ["React", "TypeScript", "Accessibility"],
    summary:
      "Help independent teams turn ideas into beautiful digital products. You'll own the interfaces people use every day, from first sketch to thoughtful finishing touches.",
    tasks: [
      "Build accessible product experiences with React and TypeScript.",
      "Partner with design to turn research into useful, polished features.",
      "Improve performance and contribute to a shared component library.",
    ],
  },
  {
    id: 2,
    company: "Northstar",
    mark: "N",
    color: "#e5edff",
    title: "Product Engineer",
    location: "Africa & Europe",
    region: "africa",
    salary: "$60k–$85k",
    type: "Full-time",
    level: "Mid-level",
    source: "Remote board",
    days: 1,
    skills: ["React", "Next.js", "PostgreSQL"],
    summary:
      "Make everyday financial tools simpler for small businesses. Work across the product, talk to customers, and ship improvements from start to finish.",
    tasks: [
      "Own features across a Next.js application.",
      "Work with customers to understand their daily workflows.",
      "Build reliable data models and straightforward interfaces.",
    ],
  },
  {
    id: 3,
    company: "Layers",
    mark: "L",
    color: "#fce8db",
    title: "React Developer",
    location: "Worldwide",
    region: "worldwide",
    salary: "$45k–$65k",
    type: "Contract",
    level: "Junior",
    source: "Company careers",
    days: 1,
    skills: ["React", "JavaScript", "CSS"],
    summary:
      "Join a small distributed studio building useful websites for ambitious teams. You'll have room to learn, a supportive reviewer, and real ownership of your work.",
    tasks: [
      "Build responsive interfaces from design specifications.",
      "Write clear, maintainable JavaScript.",
      "Collaborate with an experienced engineer through code reviews.",
    ],
  },
  {
    id: 4,
    company: "Orbit",
    mark: "O",
    color: "#e2f1eb",
    title: "Frontend Platform Engineer",
    location: "US only",
    region: "restricted",
    salary: "$110k–$145k",
    type: "Full-time",
    level: "Senior",
    source: "Company careers",
    days: 2,
    skills: ["TypeScript", "React", "Testing"],
    summary:
      "Build the tools that help product engineers do their best work. This position requires US residency; remote does not mean worldwide for this opening.",
    tasks: [
      "Maintain a shared design system.",
      "Improve frontend build and test workflows.",
      "Mentor engineers across product teams.",
    ],
  },
  {
    id: 5,
    company: "Fieldwork",
    mark: "fw",
    color: "#f0e8db",
    title: "Web Developer",
    location: "Remote · location unspecified",
    region: "unknown",
    salary: "Not disclosed",
    type: "Contract",
    level: "Mid-level",
    source: "Remote board",
    days: 3,
    skills: ["JavaScript", "CSS", "Accessibility"],
    summary:
      "Create considered web experiences for independent brands. The sample posting does not specify eligible countries, so location should be checked before applying.",
    tasks: [
      "Develop responsive, accessible marketing websites.",
      "Collaborate directly with designers.",
      "Keep sites fast and easy to maintain.",
    ],
  },
  {
    id: 6,
    company: "Common Ground",
    mark: "cg",
    color: "#f7e4ec",
    title: "Frontend Engineer",
    location: "Worldwide",
    region: "worldwide",
    salary: "$65k–$90k",
    type: "Full-time",
    level: "Mid-level",
    source: "Remote board",
    days: 4,
    skills: ["React", "TypeScript", "Next.js"],
    summary:
      "Help remote communities feel closer. Build calm, dependable collaboration tools with a team that values focus and sustainable work.",
    tasks: [
      "Create collaborative experiences in React.",
      "Improve onboarding and product discovery.",
      "Work asynchronously with teammates around the world.",
    ],
  },
];

export const initialProfile = {
  name: "Alex",
  role: "Frontend Engineer",
  location: "Nigeria",
  level: "Mid-level",
  skills: ["React", "TypeScript", "Next.js", "CSS"],
  remote: true,
};
export const skillOptions = [
  "React",
  "TypeScript",
  "Next.js",
  "JavaScript",
  "CSS",
  "Accessibility",
  "PostgreSQL",
  "Testing",
];
export const stages = ["Applied", "Interview", "Offer", "Closed"];

export function fit(job, profile) {
  if (job.live)
    return {
      score: job.match?.score ?? 0,
      skills: job.match?.matched_skills ?? [],
      level: false,
    };
  const skills = job.skills.filter((skill) => profile.skills.includes(skill));
  const role = job.title.toLowerCase().includes(profile.role.toLowerCase());
  const level = job.level === profile.level;
  return {
    score: Math.min(
      100,
      skills.length * 20 + (role ? 25 : 10) + (level ? 15 : 0),
    ),
    skills,
    level,
  };
}

export function eligibility(job, profile) {
  if (job.live) {
    const status = job.eligibility?.status || "unknown";
    return {
      label: {
        eligible: "Location matches",
        restricted: "Location restricted",
        unknown: "Check location",
      }[status],
      tone: { eligible: "positive", restricted: "warning", unknown: "neutral" }[
        status
      ],
      detail:
        job.eligibility?.detail ||
        "Confirm country and work authorization requirements with the employer.",
    };
  }
  if (job.region === "worldwide")
    return {
      label: "Worldwide",
      tone: "positive",
      detail: "This sample posting explicitly welcomes worldwide applicants.",
    };
  if (job.region === "africa" && profile.location === "Nigeria")
    return {
      label: "Open to your location",
      tone: "positive",
      detail: "This sample posting includes applicants based in Africa.",
    };
  if (job.region === "restricted" && profile.location !== "United States")
    return {
      label: "Location restricted",
      tone: "warning",
      detail: "This sample posting requires US residency.",
    };
  if (job.region === "restricted" && profile.location === "United States")
    return {
      label: "US residents",
      tone: "positive",
      detail: "Location matches; work authorization still needs checking.",
    };
  return {
    label: "Check location",
    tone: "neutral",
    detail:
      "Confirm country and work authorization requirements with the employer.",
  };
}
