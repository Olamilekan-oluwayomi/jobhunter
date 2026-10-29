import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  ArrowDownWideNarrow,
  ArrowRight,
  ArrowUpRight,
  Bookmark,
  BriefcaseBusiness,
  Check,
  CheckCheck,
  ChevronRight,
  Compass,
  Globe2,
  LayoutGrid,
  List,
  MapPin,
  Moon,
  Search,
  Settings2,
  SlidersHorizontal,
  Sparkles,
  Sun,
  Target,
  X,
} from "lucide-react";
import {
  demoJobs,
  eligibility,
  fit,
  initialProfile,
  skillOptions,
  stages,
} from "./data";
import "./preview.css";

const STORAGE_KEY = "jobhunter-design-preview-v1";
const navigation = [
  { key: "discover", label: "For you", icon: Sparkles },
  { key: "explore", label: "Explore jobs", icon: Compass },
  { key: "saved", label: "Saved jobs", icon: Bookmark },
  { key: "applications", label: "Applications", icon: BriefcaseBusiness },
  { key: "profile", label: "My preferences", icon: Settings2 },
];
function initialState(live = false) {
  const fallback = {
    saved: live ? [] : [2, 6],
    applications: [
      {
        jobId: 3,
        stage: "Applied",
        notes: "Prepare a few examples of responsive layouts.",
      },
    ],
    profile: live
      ? { ...initialProfile, name: "", skills: [] }
      : initialProfile,
    dark: false,
  };
  try {
    if (live)
      return {
        ...fallback,
        dark:
          JSON.parse(localStorage.getItem("jobhunter-theme-v1"))?.dark === true,
      };
    const value = JSON.parse(
      localStorage.getItem(live ? "jobhunter-preferences-v1" : STORAGE_KEY),
    );
    if (
      value &&
      Array.isArray(value.saved) &&
      Array.isArray(value.applications) &&
      Array.isArray(value.profile?.skills) &&
      typeof value.profile.name === "string"
    )
      return value;
  } catch {
    /* Storage can be disabled; the preview still works in memory. */
  }
  return fallback;
}

function Logo({ job }) {
  return (
    <span
      className="jh-company-mark"
      style={{ background: job.color }}
      aria-hidden="true"
    >
      {job.mark}
    </span>
  );
}

function JobCard({ job, profile, saved, onSave, onOpen }) {
  const match = fit(job, profile);
  const location = eligibility(job, profile);
  return (
    <article className="jh-job-card">
      <div className="jh-card-top">
        <Logo job={job} />
        <span className="jh-company-name">
          {job.company}
          <small>
            {job.days == null
              ? "Date not listed"
              : job.days === 0
                ? "Today"
                : `${job.days}d ago`}{" "}
            · {job.live ? job.source : "Sample opening"}
          </small>
        </span>
        <button
          className={`jh-icon-button ${saved ? "is-saved" : ""}`}
          aria-label={`${saved ? "Unsave" : "Save"} ${job.title} at ${job.company}`}
          aria-pressed={saved}
          onClick={() => onSave(job.id)}
        >
          <Bookmark size={19} fill={saved ? "currentColor" : "none"} />
        </button>
      </div>
      <button className="jh-job-title" onClick={() => onOpen(job)}>
        {job.title}
        <ArrowUpRight size={18} />
      </button>
      <div className="jh-job-meta">
        <span>
          <Globe2 size={14} />
          {job.location}
        </span>
        <span>{job.type}</span>
      </div>
      <div className="jh-skill-list">
        {job.skills.map((skill) => (
          <span
            key={skill}
            className={match.skills.includes(skill) ? "is-match" : ""}
          >
            {skill}
          </span>
        ))}
      </div>
      <div className="jh-card-bottom">
        <strong>
          {job.salary}
          <small>
            {!job.live && job.salary !== "Not disclosed" && "/ year"}
          </small>
        </strong>
        <span className={`jh-eligibility ${location.tone}`}>
          {location.label}
        </span>
      </div>
      <div className="jh-card-foot">
        <span>
          <span className="jh-fit-dot" />
          {match.score >= 70 ? "Strong skill fit" : "Worth a look"}{" "}
          <b>{match.score}/100</b>
        </span>
        <button onClick={() => onOpen(job)}>
          View role <ArrowRight size={14} />
        </button>
      </div>
    </article>
  );
}

function Detail({
  job,
  profile,
  saved,
  application,
  onClose,
  onSave,
  onApply,
}) {
  const dialog = useRef(null);
  const closeButton = useRef(null);
  useEffect(() => {
    const returnFocus = document.activeElement;
    const node = dialog.current;
    node.showModal();
    closeButton.current.focus();
    return () => {
      node.close();
      if (returnFocus instanceof HTMLElement) returnFocus.focus();
    };
  }, []);
  const match = fit(job, profile);
  const location = eligibility(job, profile);
  return (
    <dialog
      className="jh-detail"
      ref={dialog}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === dialog.current) onClose();
      }}
      aria-labelledby="detail-title"
    >
      <div className="jh-detail-inner">
        <header className="jh-detail-top">
          <span>
            ROLE DETAILS{" "}
            {!job.live && <span className="jh-demo-small">SAMPLE</span>}
          </span>
          <button
            ref={closeButton}
            className="jh-icon-button"
            onClick={onClose}
            aria-label="Close job details"
          >
            <X size={21} />
          </button>
        </header>
        <div className="jh-detail-body">
          <Logo job={job} />
          <p className="jh-eyebrow">{job.company}</p>
          <h2 id="detail-title">{job.title}</h2>
          <div className="jh-job-meta">
            <span>
              <MapPin size={15} />
              {job.location}
            </span>
            <span>{job.type}</span>
          </div>
          <div className="jh-detail-facts">
            <div>
              <small>COMPENSATION</small>
              <strong>{job.salary}</strong>
            </div>
            <div>
              <small>EXPERIENCE</small>
              <strong>{job.level}</strong>
            </div>
          </div>
          <section className="jh-fit-box">
            <div>
              <Sparkles size={18} />
              <h3>Why this could fit</h3>
              <b>{match.score}/100</b>
            </div>
            <p>
              {match.skills.length
                ? `Matches your skills in ${match.skills.join(", ")}.`
                : "No listed skills match your current preferences."}{" "}
              {match.level
                ? "The experience level matches your preference."
                : "Check the experience requirements."}
            </p>
            <small>
              {job.live
                ? "Profile keyword score; this is not a hiring probability."
                : "Illustrative keyword score, not a hiring probability."}
            </small>
          </section>
          <section className={`jh-location-note ${location.tone}`}>
            <Globe2 size={19} />
            <div>
              <strong>{location.label}</strong>
              <p>
                {job.live
                  ? location.detail.replace("sample ", "")
                  : location.detail}
              </p>
            </div>
          </section>
          <h3>About the role</h3>
          <p>{job.summary}</p>
          {job.tasks.length > 0 && <h3>What you'll work on</h3>}
          <ul>
            {job.tasks.map((task) => (
              <li key={task}>{task}</li>
            ))}
          </ul>
          <h3>Skills & tools</h3>
          <div className="jh-skill-list">
            {job.skills.map((skill) => (
              <span key={skill}>{skill}</span>
            ))}
          </div>
          <p className="jh-disclaimer">
            {job.live ? (
              "Apply on the employer's website, then record your application here."
            ) : (
              <>
                This is a fictional opening for the design preview. No
                application is sent. Recording an application below only updates
                this browser's preview.
              </>
            )}
          </p>
        </div>
        <footer className="jh-detail-actions">
          {job.live && (
            <a
              className="jh-button primary"
              href={job.url}
              target="_blank"
              rel="noreferrer"
            >
              Apply <ArrowUpRight size={16} />
            </a>
          )}
          <button
            className="jh-button secondary"
            onClick={() => onSave(job.id)}
          >
            <Bookmark size={17} />
            {saved ? "Saved" : "Save role"}
          </button>
          <button
            className="jh-button primary"
            disabled={Boolean(application)}
            onClick={() => onApply(job.id)}
          >
            {application
              ? "Application recorded"
              : job.live
                ? "I've applied"
                : "Record sample application"}
            <Check size={17} />
          </button>
        </footer>
      </div>
    </dialog>
  );
}

function Profile({ profile, onSave, live = false }) {
  const [draft, setDraft] = useState(profile);
  const change = (key, value) =>
    setDraft((previous) => ({ ...previous, [key]: value }));
  return (
    <form
      className="jh-profile"
      onSubmit={(event) => {
        event.preventDefault();
        onSave(draft);
      }}
    >
      <section className="jh-panel">
        <div className="jh-section-heading">
          <span className="jh-number">01</span>
          <div>
            <h2>A little about you</h2>
            <p>Make your search feel more like you.</p>
          </div>
        </div>
        <div className="jh-form-grid">
          <label>
            First name
            <input
              required
              maxLength={40}
              value={draft.name}
              onChange={(event) => change("name", event.target.value)}
            />
          </label>
          <label>
            Where are you based?
            <select
              required
              value={draft.location}
              onChange={(event) => change("location", event.target.value)}
            >
              <option value="">Choose your location</option>
              <option>Nigeria</option>
              <option>United States</option>
              <option>United Kingdom</option>
              <option>Other</option>
            </select>
          </label>
          <label>
            Target role
            <select
              value={draft.role}
              onChange={(event) => change("role", event.target.value)}
            >
              <option value="">Choose a target role</option>
              <option>Frontend Engineer</option>
              <option>Product Engineer</option>
              <option>React Developer</option>
              <option>Web Developer</option>
            </select>
          </label>
          <label>
            Experience level
            <select
              value={draft.level}
              onChange={(event) => change("level", event.target.value)}
            >
              <option>Not specified</option>
              <option>Junior</option>
              <option>Mid-level</option>
              <option>Senior</option>
            </select>
          </label>
        </div>
      </section>
      <section className="jh-panel">
        <div className="jh-section-heading">
          <span className="jh-number">02</span>
          <div>
            <h2>Your strengths</h2>
            <p>Select the skills you want to use in your next role.</p>
          </div>
        </div>
        <div className="jh-skill-picker">
          {skillOptions.map((skill) => (
            <button
              key={skill}
              type="button"
              aria-pressed={draft.skills.includes(skill)}
              onClick={() =>
                change(
                  "skills",
                  draft.skills.includes(skill)
                    ? draft.skills.filter((item) => item !== skill)
                    : [...draft.skills, skill],
                )
              }
            >
              {draft.skills.includes(skill) && <Check size={15} />}
              {skill}
            </button>
          ))}
        </div>
      </section>
      <div className="jh-profile-footer">
        <p>
          {live
            ? "Preferences are saved to your account."
            : "Preferences stay in this browser."}
        </p>
        <button className="jh-button primary" type="submit">
          Save preferences <ArrowRight size={17} />
        </button>
      </div>
    </form>
  );
}

export default function Preview({ workspace }) {
  const live = Boolean(workspace);
  const [params, setParams] = useSearchParams();
  const page = navigation.some((item) => item.key === params.get("view"))
    ? params.get("view")
    : "discover";
  const [localState, setState] = useState(() =>
    initialState(Boolean(workspace)),
  );
  const state = workspace
    ? {
        ...localState,
        profile: workspace.profile,
        saved: workspace.saved,
        applications: workspace.applications,
      }
    : localState;
  const jobs = workspace?.jobs ?? demoJobs;
  const [selected, setSelected] = useState(null);
  const [notice, setNotice] = useState("");
  const [boardView, setBoardView] = useState("board");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [storageWarning, setStorageWarning] = useState(false);
  const query = params.get("q") || "";
  const type = params.get("type") || "all";
  const locationFilter = params.get("location") || "all";
  const sort = params.get("sort") || "match";
  useEffect(() => {
    try {
      localStorage.setItem(
        workspace ? "jobhunter-theme-v1" : STORAGE_KEY,
        JSON.stringify(workspace ? { dark: localState.dark } : localState),
      );
    } catch {
      setStorageWarning(true);
    }
  }, [localState, workspace]);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(""), 3500);
    return () => clearTimeout(timer);
  }, [notice]);
  useEffect(() => {
    const previous = document.title;
    document.title = live ? "Jobhunter" : "Jobhunter — Design preview";
    return () => {
      document.title = previous;
    };
  }, [live]);
  const updateParam = (key, value) =>
    setParams(
      (previous) => {
        const next = new URLSearchParams(previous);
        if (key !== "page") next.delete("page");
        if (value) next.set(key, value);
        else next.delete(key);
        return next;
      },
      { replace: true },
    );
  const navigate = (key) => {
    selection.current += 1;
    setParams({ view: key });
    setSelected(null);
    window.scrollTo({ top: 0 });
  };
  const toggleSave = (id) => {
    if (workspace) {
      workspace.toggleSave(id);
      return;
    }
    const saved = state.saved.includes(id);
    setState((previous) => ({
      ...previous,
      saved: saved
        ? previous.saved.filter((item) => item !== id)
        : [...previous.saved, id],
    }));
    setNotice(saved ? "Removed from saved jobs" : "Added to your saved jobs");
  };
  const recordApplication = (id) => {
    if (workspace) {
      workspace.recordApplication(id);
      return;
    }
    setState((previous) =>
      previous.applications.some((item) => item.jobId === id)
        ? previous
        : {
            ...previous,
            applications: [
              ...previous.applications,
              { jobId: id, stage: "Applied", notes: "" },
            ],
          },
    );
    setNotice("Sample application recorded. Nothing was submitted.");
  };
  const updateApplication = (id, values) => {
    if (workspace) {
      workspace.updateApplication(id, values);
      return;
    }
    setState((previous) => ({
      ...previous,
      applications: previous.applications.map((item) =>
        item.jobId === id ? { ...item, ...values } : item,
      ),
    }));
  };
  const filtered = workspace
    ? jobs.filter((job) => workspace.resultIds.includes(job.id))
    : jobs
        .filter(
          (job) =>
            (page !== "saved" || state.saved.includes(job.id)) &&
            (!query ||
              `${job.title} ${job.company} ${job.skills.join(" ")}`
                .toLowerCase()
                .includes(query.toLowerCase())) &&
            (type === "all" || job.type === type) &&
            (locationFilter === "all" ||
              eligibility(job, state.profile).tone === "positive"),
        )
        .sort((a, b) =>
          sort === "newest"
            ? a.days - b.days
            : fit(b, state.profile).score - fit(a, state.profile).score,
        );
  const currentTitle = navigation.find((item) => item.key === page).label;
  const activeApplications = state.applications.filter(
    (item) => item.stage !== "Closed",
  );
  const firstName = state.profile.name.trim() || "there";
  const selection = useRef(0);
  const openSelected = async (job) => {
    const version = ++selection.current;
    setSelected(job);
    if (!workspace) return;
    try {
      const detail = await workspace.openJob(job.id);
      if (version === selection.current) setSelected(detail);
    } catch {
      if (version === selection.current)
        setNotice("Could not load role details. Try opening the role again.");
    }
  };

  return (
    <div className={`jh-preview ${state.dark ? "jh-dark" : ""}`}>
      <a className="jh-skip" href="#preview-main">
        Skip to content
      </a>
      <aside className="jh-sidebar">
        <button
          className="jh-brand"
          onClick={() => navigate("discover")}
          aria-label="Jobhunter home"
        >
          <span>
            <Target size={23} strokeWidth={2.5} />
          </span>
          jobhunter<span className="jh-brand-dot">.</span>
        </button>
        <p className="jh-nav-caption">YOUR WORKSPACE</p>
        <nav aria-label="Workspace">
          {navigation.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              className={page === key ? "active" : ""}
              onClick={() => navigate(key)}
              aria-current={page === key ? "page" : undefined}
            >
              <Icon size={19} />
              <span>{label}</span>
              {key === "saved" && state.saved.length > 0 && (
                <b>{state.saved.length}</b>
              )}
            </button>
          ))}
        </nav>
        <div className="jh-sidebar-bottom">
          <div className="jh-small-note">
            <span className="jh-orbit-icon">
              <Compass size={24} />
            </span>
            <strong>A little focus. A big step.</strong>
            <p>Your next opportunity starts with one good match.</p>
            <button onClick={() => navigate("explore")}>
              Explore opportunities <ArrowUpRight size={15} />
            </button>
          </div>
          <button className="jh-account" onClick={() => navigate("profile")}>
            <span>{firstName.slice(0, 1).toUpperCase()}</span>
            <div>
              <strong>{firstName}</strong>
              <small>{workspace ? "Your workspace" : "Preview profile"}</small>
            </div>
            <Settings2 size={17} />
          </button>
        </div>
      </aside>
      <div className="jh-main-shell">
        <header className="jh-topbar">
          <div>
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>{currentTitle}</strong>
          </div>
          <div className="jh-topbar-actions">
            {workspace && (
              <button
                className="jh-button secondary"
                onClick={workspace.signOut}
              >
                Sign out
              </button>
            )}
            <span className="jh-preview-badge">
              <span />
              {workspace ? "Live jobs" : "Design preview"}
            </span>
            <button
              className="jh-icon-button"
              aria-label={`Switch to ${state.dark ? "light" : "dark"} theme`}
              onClick={() =>
                setState((previous) => ({ ...previous, dark: !previous.dark }))
              }
            >
              {state.dark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            {!workspace && (
              <Link className="jh-exit" to="/">
                Live app <ArrowUpRight size={14} />
              </Link>
            )}
            {workspace?.canScrape && (
              <button
                className="jh-button secondary"
                disabled={workspace.scraping}
                onClick={workspace.scrape}
              >
                {workspace.scraping ? "Finding jobs…" : "Find new jobs"}
              </button>
            )}
          </div>
        </header>
        <main id="preview-main" className="jh-main" tabIndex={-1}>
          {!workspace && (
            <div className="jh-sample-notice">
              <span>PREVIEW</span>Fictional jobs and a sample profile. Changes
              are saved only in this browser.
            </div>
          )}
          {workspace?.error && (
            <div role="alert" className="jh-panel">
              {workspace.error}
              <button className="jh-button secondary" onClick={workspace.retry}>
                Retry
              </button>
            </div>
          )}
          {workspace?.loading && <p role="status">Loading your workspace…</p>}
          {storageWarning && (
            <p role="alert" className="jh-storage-warning">
              Browser storage is unavailable. Changes will last only for this
              visit.
            </p>
          )}
          <div className="jh-page-heading">
            <div>
              <p className="jh-eyebrow">
                {page === "discover"
                  ? `YOUR NEXT CHAPTER, ${firstName.toUpperCase()}`
                  : "MAKE YOUR NEXT MOVE"}
              </p>
              <h1>
                {page === "discover" ? (
                  <>
                    Good work starts
                    <br className="jh-mobile-break" /> with the right fit.
                  </>
                ) : page === "explore" ? (
                  "A world of possibilities."
                ) : page === "saved" ? (
                  "Worth coming back to."
                ) : page === "applications" ? (
                  "Every step, in one place."
                ) : (
                  "A search shaped around you."
                )}
              </h1>
              <p>
                {page === "discover"
                  ? "Discover remote roles that align with your skills and ambitions."
                  : page === "explore"
                    ? "Find your next opportunity. Keep the ones that feel right."
                    : page === "saved"
                      ? "Your shortlist of opportunities worth a closer look."
                      : page === "applications"
                        ? "From first application to next chapter. Keep your momentum."
                        : "Tell us what matters. We'll help you find a better fit."}
              </p>
            </div>
            {page === "discover" && (
              <button
                className="jh-button secondary"
                onClick={() => navigate("profile")}
              >
                <SlidersHorizontal size={16} />
                Your preferences
              </button>
            )}
          </div>

          {page === "discover" && (
            <section
              className="jh-intro-grid"
              aria-label="Your search overview"
            >
              <div className="jh-feature">
                <div className="jh-feature-copy">
                  <span className="jh-label">
                    <span />
                    CURATED FOR YOUR NEXT MOVE
                  </span>
                  <h2>
                    Your skills.
                    <br />
                    New possibilities.
                  </h2>
                  <p>
                    {state.profile.role} · {state.profile.location}
                    <br />
                    {state.profile.skills.slice(0, 3).join(" / ") ||
                      "Add your skills to personalize your matches"}
                  </p>
                  <button onClick={() => navigate("explore")}>
                    Explore your matches <ArrowRight size={16} />
                  </button>
                </div>
                <div className="jh-illustration" aria-hidden="true">
                  <div className="jh-orbit orbit-one" />
                  <div className="jh-orbit orbit-two" />
                  <div className="jh-graphic-card graphic-back">
                    <span>THE NEXT CHAPTER</span>
                    <div />
                    <div />
                  </div>
                  <div className="jh-graphic-card graphic-front">
                    <span className="jh-graphic-icon">
                      <Sparkles size={23} />
                    </span>
                    <strong>
                      Made for
                      <br />
                      your next move.
                    </strong>
                    <span className="jh-graphic-line">
                      <i />
                      <i />
                      <i />
                    </span>
                  </div>
                  <div className="jh-floating-check">
                    <Check size={22} strokeWidth={3} />
                  </div>
                </div>
              </div>
              <div className="jh-momentum">
                <div className="jh-momentum-heading">
                  <span className="jh-label">YOUR MOMENTUM</span>
                  <Target size={19} />
                </div>
                <h3>Small steps add up.</h3>
                <p>A clear view of your search.</p>
                <div className="jh-stat-row">
                  <button onClick={() => navigate("saved")}>
                    <b>{state.saved.length.toString().padStart(2, "0")}</b>
                    <span>
                      Saved roles <ArrowUpRight size={13} />
                    </span>
                  </button>
                  <button onClick={() => navigate("applications")}>
                    <b>
                      {(workspace
                        ? workspace.activeCount
                        : activeApplications.length
                      )
                        .toString()
                        .padStart(2, "0")}
                    </b>
                    <span>
                      In progress <ArrowUpRight size={13} />
                    </span>
                  </button>
                </div>
                <div className="jh-momentum-foot">
                  <CheckCheck size={16} />
                  <span>One thoughtful application beats a rushed one.</span>
                </div>
              </div>
            </section>
          )}

          {page === "profile" ? (
            <Profile
              live={live}
              profile={state.profile}
              onSave={(profile) => {
                if (workspace) {
                  workspace.saveProfile(profile);
                  return;
                }
                setState((previous) => ({ ...previous, profile }));
                setNotice("Preferences saved. Your matches have been updated.");
              }}
            />
          ) : page === "applications" ? (
            <>
              <div className="jh-section-bar">
                <div>
                  <h2>
                    Application tracker{" "}
                    <span>
                      {workspace
                        ? workspace.applicationCount
                        : state.applications.length}
                    </span>
                  </h2>
                  <p>Update a status as your conversation moves forward.</p>
                </div>
                <div className="jh-view-toggle" aria-label="Application view">
                  <button
                    aria-label="Board view"
                    aria-pressed={boardView === "board"}
                    onClick={() => setBoardView("board")}
                  >
                    <LayoutGrid size={17} />
                  </button>
                  <button
                    aria-label="List view"
                    aria-pressed={boardView === "list"}
                    onClick={() => setBoardView("list")}
                  >
                    <List size={18} />
                  </button>
                </div>
              </div>
              <div
                className={`jh-pipeline ${boardView === "list" ? "jh-pipeline-list" : ""}`}
              >
                {stages.map((stage) => (
                  <section className="jh-stage" key={stage}>
                    <h3>
                      <span className={`jh-stage-dot ${stage.toLowerCase()}`} />
                      {stage}
                      <b>
                        {
                          state.applications.filter(
                            (item) => item.stage === stage,
                          ).length
                        }
                      </b>
                    </h3>
                    {state.applications
                      .filter((item) => item.stage === stage)
                      .map((item) => {
                        const job = jobs.find(
                          (entry) => entry.id === item.jobId,
                        );
                        if (!job) return null;
                        return (
                          <article className="jh-application" key={item.jobId}>
                            <div className="jh-application-company">
                              <Logo job={job} />
                              <span>{job.company}</span>
                            </div>
                            <button
                              className="jh-job-title"
                              onClick={() => openSelected(job)}
                            >
                              {job.title}
                            </button>
                            <p>{job.location}</p>
                            <label>
                              Status
                              <select
                                aria-label={`Status for ${job.title} at ${job.company}`}
                                value={item.stage}
                                onChange={(event) => {
                                  updateApplication(item.jobId, {
                                    stage: event.target.value,
                                  });
                                  if (!workspace)
                                    setNotice(`Moved to ${event.target.value}`);
                                }}
                              >
                                {stages.map((value) => (
                                  <option key={value}>{value}</option>
                                ))}
                              </select>
                            </label>
                            <label>
                              Notes
                              <textarea
                                maxLength={2000}
                                value={item.notes}
                                placeholder="Add a next step or a reminder…"
                                onChange={(event) =>
                                  workspace
                                    ? workspace.draftNote(
                                        item.jobId,
                                        event.target.value,
                                      )
                                    : updateApplication(item.jobId, {
                                        notes: event.target.value,
                                      })
                                }
                                onBlur={(event) => {
                                  if (workspace)
                                    updateApplication(item.jobId, {
                                      notes: event.target.value,
                                    });
                                }}
                              />
                            </label>
                          </article>
                        );
                      })}
                    {!state.applications.some(
                      (item) => item.stage === stage,
                    ) && (
                      <div className="jh-stage-empty">
                        {stage === "Offer"
                          ? "Room for good news."
                          : stage === "Applied"
                            ? "Your next step starts here."
                            : "Nothing here yet."}
                      </div>
                    )}
                  </section>
                ))}
              </div>
            </>
          ) : (
            <>
              <div className="jh-section-bar">
                <div>
                  <h2>
                    {page === "discover"
                      ? "Your opportunity shortlist"
                      : page === "saved"
                        ? "Saved opportunities"
                        : "Explore opportunities"}
                    <span>{workspace ? workspace.total : filtered.length}</span>
                  </h2>
                  <p>
                    {page === "discover"
                      ? "A few good places to start. Ranked by your preferences."
                      : workspace
                        ? "Openings from your connected job sources."
                        : "All openings shown here are fictional examples."}
                  </p>
                </div>
                <label className="jh-sort">
                  <ArrowDownWideNarrow size={16} />
                  <select
                    aria-label="Sort jobs"
                    value={sort}
                    onChange={(event) =>
                      updateParam("sort", event.target.value)
                    }
                  >
                    <option value="match">Best fit first</option>
                    <option value="newest">Newest first</option>
                  </select>
                </label>
              </div>
              <div className="jh-filter-bar">
                <label className="jh-search">
                  <Search size={19} />
                  <input
                    aria-label="Search jobs"
                    placeholder="Search roles, companies or skills"
                    value={query}
                    onChange={(event) => updateParam("q", event.target.value)}
                  />
                  {query && (
                    <button
                      aria-label="Clear search"
                      onClick={() => updateParam("q", "")}
                    >
                      <X size={16} />
                    </button>
                  )}
                </label>
                <button
                  className={`jh-button secondary jh-filter-toggle ${filtersOpen ? "selected" : ""}`}
                  aria-expanded={filtersOpen}
                  onClick={() => setFiltersOpen(!filtersOpen)}
                >
                  <SlidersHorizontal size={16} />
                  Filters
                  {(type !== "all" || locationFilter !== "all") && (
                    <span className="jh-filter-count">
                      {Number(type !== "all") +
                        Number(locationFilter !== "all")}
                    </span>
                  )}
                </button>
                <span className="jh-remote-tag">
                  <Globe2 size={14} />
                  Remote opportunities
                </span>
              </div>
              {filtersOpen && (
                <div className="jh-filter-options">
                  <label>
                    Employment type
                    <select
                      value={type}
                      onChange={(event) =>
                        updateParam("type", event.target.value)
                      }
                    >
                      <option value="all">All types</option>
                      <option>Full-time</option>
                      <option>Contract</option>
                    </select>
                  </label>
                  <label>
                    Location eligibility
                    <select
                      value={locationFilter}
                      onChange={(event) =>
                        updateParam("location", event.target.value)
                      }
                    >
                      <option value="all">Include uncertain locations</option>
                      <option value="eligible">Matches my location</option>
                    </select>
                  </label>
                  <button
                    onClick={() => {
                      setParams({ view: page });
                    }}
                  >
                    Reset filters
                  </button>
                </div>
              )}
              {filtered.length ? (
                <div className="jh-job-grid">
                  {filtered.map((job) => (
                    <JobCard
                      key={job.id}
                      job={job}
                      profile={state.profile}
                      saved={state.saved.includes(job.id)}
                      onSave={toggleSave}
                      onOpen={openSelected}
                    />
                  ))}
                </div>
              ) : (
                <div className="jh-empty">
                  <Search size={30} />
                  <h2>
                    {page === "saved" && !state.saved.length
                      ? "Your shortlist starts here."
                      : "Let's widen the search."}
                  </h2>
                  <p>
                    {page === "saved" && !state.saved.length
                      ? "Save a role that catches your eye. You'll find it here."
                      : "Try a different skill or clear your filters to see more opportunities."}
                  </p>
                  <button
                    className="jh-button primary"
                    onClick={() =>
                      page === "saved" && !state.saved.length
                        ? navigate("explore")
                        : setParams({ view: page })
                    }
                  >
                    {page === "saved" && !state.saved.length
                      ? "Explore roles"
                      : "Clear filters"}
                    <ArrowRight size={16} />
                  </button>
                </div>
              )}
              <div className="jh-end-note">
                <span />A more thoughtful search. A better next step.
                <span />
              </div>
            </>
          )}
          {workspace && page !== "profile" && (
            <nav className="jh-pagination" aria-label="Results pages">
              <button
                className="jh-button secondary"
                disabled={workspace.page <= 1 || workspace.loading}
                onClick={() => updateParam("page", String(workspace.page - 1))}
              >
                Previous
              </button>
              <span>
                Page {workspace.page} of{" "}
                {Math.max(1, Math.ceil(workspace.total / workspace.pageSize))}
              </span>
              <button
                className="jh-button secondary"
                disabled={
                  workspace.page * workspace.pageSize >= workspace.total ||
                  workspace.loading
                }
                onClick={() => updateParam("page", String(workspace.page + 1))}
              >
                Next
              </button>
            </nav>
          )}
        </main>
        <footer className="jh-footer">
          <span>Built around your next chapter.</span>
          <span>
            {workspace
              ? "Jobhunter · Your next chapter"
              : "Jobhunter · Interactive design preview"}
          </span>
        </footer>
      </div>
      <nav className="jh-mobile-nav" aria-label="Mobile workspace">
        {navigation.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            aria-current={page === key ? "page" : undefined}
            className={page === key ? "active" : ""}
            onClick={() => navigate(key)}
          >
            <Icon size={19} />
            <span>
              {label === "My preferences"
                ? "Profile"
                : label === "Explore jobs"
                  ? "Explore"
                  : label === "Saved jobs"
                    ? "Saved"
                    : label}
            </span>
          </button>
        ))}
      </nav>
      {notice && (
        <div className="jh-toast" role="status">
          <Check size={18} />
          <span>{notice}</span>
          <button
            onClick={() => setNotice("")}
            aria-label="Dismiss notification"
          >
            <X size={15} />
          </button>
        </div>
      )}
      {selected && (
        <Detail
          job={selected}
          profile={state.profile}
          saved={state.saved.includes(selected.id)}
          application={state.applications.find(
            (item) => item.jobId === selected.id,
          )}
          onClose={() => {
            selection.current += 1;
            setSelected(null);
          }}
          onSave={toggleSave}
          onApply={recordApplication}
        />
      )}
    </div>
  );
}
