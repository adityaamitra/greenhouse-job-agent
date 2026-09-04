import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { supabase } from "./lib/supabase";


const MANUAL_THRESHOLD = 85;
const CONFIDENCE_THRESHOLD = 75;

const APPLICATION_STATUSES = [
  "PENDING",
  "IN_PROGRESS",
  "APPLIED",
  "OA",
  "RECRUITER_SCREEN",
  "INTERVIEW",
  "TECHNICAL_INTERVIEW",
  "FINAL_INTERVIEW",
  "OFFER",
  "REJECTED",
  "WITHDRAWN",
];

const INTERVIEW_STATUSES = [
  "RECRUITER_SCREEN",
  "INTERVIEW",
  "TECHNICAL_INTERVIEW",
  "FINAL_INTERVIEW",
];

const FIT_COMPONENTS = [
  ["required", "Required", "required_score"],
  ["preferred", "Preferred", "preferred_score"],
  ["semantic", "Semantic", "semantic_score"],
  ["experience", "Experience", "experience_score"],
];


const BROWSER_POLICY_ANSWER_KEYS = new Set([
  "WORK_AUTHORIZED_US",
  "SPONSORSHIP_NOW",
  "SPONSORSHIP_FUTURE",
  "SPONSORSHIP_NOW_OR_FUTURE",
  "WORK_AUTH_WITHOUT_SPONSORSHIP_NOW",
  "WORK_AUTH_WITHOUT_SPONSORSHIP_FUTURE",
]);


function prettyName(value) {
  if (!value) {
    return "-";
  }

  return String(value)
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (letter) =>
      letter.toUpperCase()
    );
}


function numberOrNull(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const parsed = Number(value);

  return Number.isFinite(parsed)
    ? parsed
    : null;
}


function formatNumber(value, digits = 2) {
  const parsed = numberOrNull(value);

  return parsed === null
    ? "-"
    : parsed.toFixed(digits);
}


function getExplanation(evaluation) {
  const explanation = evaluation?.explanation;

  if (
    explanation &&
    typeof explanation === "object" &&
    !Array.isArray(explanation)
  ) {
    return explanation;
  }

  return {};
}


function getAvailability(evaluation) {
  return (
    getExplanation(evaluation)
      .component_availability ?? {}
  );
}


function componentAvailable(
  evaluation,
  component
) {
  const availability =
    getAvailability(evaluation);

  if (
    Object.prototype.hasOwnProperty.call(
      availability,
      component
    )
  ) {
    return Boolean(
      availability[component]
    );
  }

  // Semantic matching exists for every V2.1 scored row.
  if (
    component === "semantic" &&
    evaluation?.semantic_score !== null &&
    evaluation?.semantic_score !== undefined
  ) {
    return true;
  }

  return false;
}


function hasV21Evidence(evaluation) {
  return Boolean(
    evaluation &&
    evaluation.confidence !== null &&
    evaluation.confidence !== undefined &&
    Object.keys(
      getExplanation(evaluation)
    ).length > 0
  );
}


function jobIsActive(application) {
  // Treat missing lifecycle metadata as active so older rows
  // remain usable if the dashboard is opened before a refresh.
  return application?.jobs?.is_active !== false;
}


function objectOrNull(value) {
  if (
    value &&
    typeof value === "object" &&
    !Array.isArray(value)
  ) {
    return value;
  }

  return null;
}


function getBrowserHandoff(application) {
  const request = application?.browser_assistance;

  if (
    !request ||
    request.source !== "BROWSER" ||
    request.resolved === true ||
    Number(request.handoff_version) !== 1
  ) {
    return null;
  }

  return objectOrNull(request.handoff);
}


function safeHandoffItems(value) {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter(
    (item) =>
      item &&
      typeof item === "object" &&
      !Array.isArray(item)
  );
}


function safeHandoffCount(value, fallback) {
  const parsed = numberOrNull(value);

  if (parsed === null || parsed < 0) {
    return fallback;
  }

  return Math.round(parsed);
}


function safePolicyDisplayAnswer(item) {
  if (
    !item ||
    !BROWSER_POLICY_ANSWER_KEYS.has(
      item.answer_key
    )
  ) {
    return null;
  }

  const answer = String(
    item.display_answer ?? ""
  );

  return ["Yes", "No", "True", "False"].includes(
    answer
  )
    ? answer
    : null;
}


function ScoreBadge({ score }) {
  const numericScore = numberOrNull(score);

  if (numericScore === null) {
    return (
      <span className="score-badge">
        -
      </span>
    );
  }

  let className = "score-badge";

  if (numericScore >= MANUAL_THRESHOLD) {
    className += " score-high";
  } else if (numericScore >= 75) {
    className += " score-medium";
  } else {
    className += " score-low";
  }

  return (
    <span className={className}>
      {numericScore.toFixed(2)}
    </span>
  );
}


function ConfidenceBadge({ confidence }) {
  const value = numberOrNull(confidence);

  if (value === null) {
    return (
      <span className="confidence-badge neutral">
        -
      </span>
    );
  }

  let className = "confidence-badge";

  if (value >= CONFIDENCE_THRESHOLD) {
    className += " high";
  } else if (value >= 60) {
    className += " medium";
  } else {
    className += " low";
  }

  return (
    <span className={className}>
      {value.toFixed(0)}%
    </span>
  );
}


function RouteBadge({ route }) {
  if (!route) {
    return null;
  }

  const className =
    route === "MANUAL_PRIORITY"
      ? "route-badge manual"
      : "route-badge agent";

  return (
    <span className={className}>
      {route === "MANUAL_PRIORITY"
        ? "Manual Priority"
        : "Agent Apply"}
    </span>
  );
}


function JobStateBadge({ isActive }) {
  return (
    <span
      className={
        isActive
          ? "job-state-badge open"
          : "job-state-badge closed"
      }
    >
      {isActive ? "Open" : "Closed"}
    </span>
  );
}


function App() {
  const [session, setSession] = useState(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [applications, setApplications] =
    useState([]);
  const [latestRun, setLatestRun] =
    useState(null);
  const [runHistory, setRunHistory] =
    useState([]);
  const [browserRuns, setBrowserRuns] =
    useState([]);
  const [activeTab, setActiveTab] =
    useState("overview");
  const [loading, setLoading] =
    useState(true);
  const [dashboardLoading, setDashboardLoading] =
    useState(false);
  const [loginLoading, setLoginLoading] =
    useState(false);
  const [error, setError] = useState("");
  const [updatingId, setUpdatingId] =
    useState(null);


  useEffect(() => {
    initializeAuth();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(
      (_event, newSession) => {
        setSession(newSession);

        if (newSession) {
          loadDashboard();
        } else {
          setApplications([]);
          setLatestRun(null);
          setRunHistory([]);
          setBrowserRuns([]);
        }
      }
    );

    return () => {
      subscription.unsubscribe();
    };
  }, []);


  async function initializeAuth() {
    try {
      const {
        data: { session: currentSession },
      } = await supabase.auth.getSession();

      setSession(currentSession);

      if (currentSession) {
        await loadDashboard();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }


  async function login(event) {
    event.preventDefault();

    setError("");
    setLoginLoading(true);

    try {
      const { error: loginError } =
        await supabase.auth.signInWithPassword({
          email,
          password,
        });

      if (loginError) {
        throw loginError;
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoginLoading(false);
    }
  }


  async function logout() {
    await supabase.auth.signOut();
  }


  async function loadDashboard() {
    setError("");
    setDashboardLoading(true);

    try {
      const {
        data: applicationData,
        error: applicationError,
      } = await supabase
        .from("applications")
        .select(`
          id,
          job_id,
          application_method,
          status,
          needs_assistance,
          assistance_reason,
          applied_at,
          last_updated_at,
          created_at,
          jobs (
            id,
            company,
            title,
            location,
            url,
            detected_profile,
            is_active,
            last_seen_at
          )
        `)
        .order("created_at", {
          ascending: false,
        });

      if (applicationError) {
        throw applicationError;
      }

      const {
        data: evaluationData,
        error: evaluationError,
      } = await supabase
        .from("job_evaluations")
        .select(`
          job_id,
          score,
          selection_score,
          confidence,
          route,
          selected_resume,
          selected_resume_file,
          role_score,
          required_score,
          preferred_score,
          semantic_score,
          experience_score,
          explanation,
          created_at
        `)
        .order("created_at", {
          ascending: false,
        });

      if (evaluationError) {
        throw evaluationError;
      }

      const latestEvaluationByJob = {};

      for (const evaluation of evaluationData ?? []) {
        if (
          !latestEvaluationByJob[
            evaluation.job_id
          ]
        ) {
          latestEvaluationByJob[
            evaluation.job_id
          ] = evaluation;
        }
      }

      const {
        data: browserAssistanceData,
        error: browserAssistanceError,
      } = await supabase
        .from("assistance_requests")
        .select(`
          id,
          application_id,
          question,
          reason,
          resolved,
          source,
          handoff_version,
          handoff,
          updated_at
        `)
        .eq("source", "BROWSER")
        .eq("resolved", false)
        .order("updated_at", {
          ascending: false,
        });

      if (browserAssistanceError) {
        throw browserAssistanceError;
      }

      const latestBrowserAssistanceByApplication = {};

      for (
        const request of browserAssistanceData ?? []
      ) {
        if (
          !latestBrowserAssistanceByApplication[
            request.application_id
          ]
        ) {
          latestBrowserAssistanceByApplication[
            request.application_id
          ] = request;
        }
      }

      const mergedApplications = (
        applicationData ?? []
      ).map((application) => ({
        ...application,
        evaluation:
          latestEvaluationByJob[
            application.job_id
          ] ?? null,
        browser_assistance:
          latestBrowserAssistanceByApplication[
            application.id
          ] ?? null,
      }));

      setApplications(
        mergedApplications
      );

      const {
        data: runData,
        error: runError,
      } = await supabase
        .from("agent_runs")
        .select(`
          id,
          board_token,
          started_at,
          completed_at,
          jobs_discovered,
          target_role_jobs,
          us_compatible_jobs,
          jobs_eligible,
          manual_priority_count,
          agent_apply_count,
          experience_rejected_count,
          unknown_location_count,
          fetch_seconds,
          filtering_seconds,
          resume_cache_seconds,
          scoring_seconds,
          total_seconds
        `)
        .order("started_at", {
          ascending: false,
        })
        .limit(30);

      if (runError) {
        throw runError;
      }

      setLatestRun(
        runData?.[0] ?? null
      );

      setRunHistory(
        [...(runData ?? [])].reverse()
      );

      const {
        data: browserRunData,
        error: browserRunError,
      } = await supabase
        .from("browser_queue_runs")
        .select(`
          id,
          run_key,
          runner_version,
          status,
          persist_handoffs,
          board_token_filter,
          queue_order,
          queue_limit,
          include_in_progress,
          started_at,
          completed_at,
          total_seconds,
          selected_count,
          completed_count,
          needs_assistance_count,
          ready_no_submit_count,
          blocked_count,
          error_count,
          challenge_count,
          browser_modified_count,
          submitted_count,
          submit_clicked_by_agent,
          application_submitted
        `)
        .order("started_at", {
          ascending: false,
        })
        .limit(30);

      if (browserRunError) {
        throw browserRunError;
      }

      setBrowserRuns(
        browserRunData ?? []
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setDashboardLoading(false);
    }
  }


  async function updateStatus(
    applicationId,
    status
  ) {
    setUpdatingId(applicationId);
    setError("");

    try {
      const updatePayload = {
        status,
        last_updated_at:
          new Date().toISOString(),
      };

      if (status === "APPLIED") {
        updatePayload.applied_at =
          new Date().toISOString();
      }

      const {
        error: updateError,
      } = await supabase
        .from("applications")
        .update(updatePayload)
        .eq("id", applicationId);

      if (updateError) {
        throw updateError;
      }

      setApplications(
        (currentApplications) =>
          currentApplications.map(
            (application) => {
              if (
                application.id !==
                applicationId
              ) {
                return application;
              }

              return {
                ...application,
                status,
                last_updated_at:
                  updatePayload
                    .last_updated_at,
                applied_at:
                  updatePayload
                    .applied_at ??
                  application.applied_at,
              };
            }
          )
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setUpdatingId(null);
    }
  }


  const latestBrowserRun =
    browserRuns[
      0
    ] ?? null;

  const browserRunStats = useMemo(
    () => {
      const recent = browserRuns;

      return {
        runs: recent.length,
        selected: recent.reduce(
          (sum, run) =>
            sum +
            Number(
              run.selected_count ?? 0
            ),
          0
        ),
        completed: recent.reduce(
          (sum, run) =>
            sum +
            Number(
              run.completed_count ?? 0
            ),
          0
        ),
        challenges: recent.reduce(
          (sum, run) =>
            sum +
            Number(
              run.challenge_count ?? 0
            ),
          0
        ),
        assistance: recent.reduce(
          (sum, run) =>
            sum +
            Number(
              run.needs_assistance_count ?? 0
            ),
          0
        ),
        readyNoSubmit: recent.reduce(
          (sum, run) =>
            sum +
            Number(
              run.ready_no_submit_count ?? 0
            ),
          0
        ),
        failures: recent.reduce(
          (sum, run) =>
            sum +
            Number(
              run.blocked_count ?? 0
            ) +
            Number(
              run.error_count ?? 0
            ),
          0
        ),
      };
    },
    [browserRuns]
  );


  const manualApplications = useMemo(
    () =>
      applications
        .filter(
          (application) =>
            application.evaluation
              ?.route ===
              "MANUAL_PRIORITY" &&
            application.status ===
              "PENDING" &&
            !application.needs_assistance &&
            jobIsActive(application)
        )
        .sort(
          (a, b) =>
            Number(
              b.evaluation?.score ?? 0
            ) -
            Number(
              a.evaluation?.score ?? 0
            )
        ),
    [applications]
  );


  const assistanceApplications = useMemo(
    () =>
      applications.filter(
        (application) =>
          application.needs_assistance &&
          jobIsActive(application)
      ),
    [applications]
  );


  const agentApplications = useMemo(
    () =>
      applications.filter(
        (application) =>
          application.evaluation
            ?.route === "AGENT_APPLY" &&
          !application.needs_assistance &&
          jobIsActive(application)
      ),
    [applications]
  );


  const lowConfidenceApplications = useMemo(
    () =>
      applications
        .filter((application) => {
          const confidence =
            numberOrNull(
              application.evaluation
                ?.confidence
            );

          return (
            jobIsActive(application) &&
            confidence !== null &&
            confidence <
              CONFIDENCE_THRESHOLD
          );
        })
        .sort(
          (a, b) =>
            Number(
              a.evaluation?.confidence ?? 0
            ) -
            Number(
              b.evaluation?.confidence ?? 0
            )
        ),
    [applications]
  );


  const closedApplications = useMemo(
    () =>
      applications.filter(
        (application) =>
          !jobIsActive(application)
      ),
    [applications]
  );


  const progressedApplications = useMemo(
    () =>
      applications.filter(
        (application) =>
          ![
            "PENDING",
            "IN_PROGRESS",
          ].includes(
            application.status
          )
      ),
    [applications]
  );


  const evidenceStats = useMemo(() => {
    const evaluations = applications
      .filter(jobIsActive)
      .map(
        (application) =>
          application.evaluation
      )
      .filter(Boolean);

    const v21Evaluations = evaluations.filter(
      hasV21Evidence
    );

    const requiredEvidence =
      v21Evaluations.filter(
        (evaluation) =>
          Boolean(
            getExplanation(evaluation)
              .required_evidence_gate
          )
      ).length;

    const manualReady =
      v21Evaluations.filter(
        (evaluation) =>
          Boolean(
            getExplanation(evaluation)
              .manual_ready
          )
      ).length;

    const averageConfidence =
      v21Evaluations.length > 0
        ? v21Evaluations.reduce(
            (total, evaluation) =>
              total +
              Number(
                evaluation.confidence ?? 0
              ),
            0
          ) / v21Evaluations.length
        : 0;

    const averageFit =
      v21Evaluations.length > 0
        ? v21Evaluations.reduce(
            (total, evaluation) =>
              total +
              Number(
                evaluation.score ?? 0
              ),
            0
          ) / v21Evaluations.length
        : 0;

    return {
      total: v21Evaluations.length,
      requiredEvidence,
      manualReady,
      averageConfidence,
      averageFit,
    };
  }, [applications]);


  const analytics = useMemo(() => {
    const total = applications.length;

    const applied = applications.filter(
      (application) =>
        application.status === "APPLIED"
    ).length;

    const interviews = applications.filter(
      (application) =>
        INTERVIEW_STATUSES.includes(
          application.status
        )
    ).length;

    const offers = applications.filter(
      (application) =>
        application.status === "OFFER"
    ).length;

    const rejected = applications.filter(
      (application) =>
        application.status === "REJECTED"
    ).length;

    const manual = applications.filter(
      (application) =>
        application.application_method ===
        "MANUAL"
    );

    const agent = applications.filter(
      (application) =>
        application.application_method ===
        "AGENT"
    );

    function positiveOutcomes(rows) {
      return rows.filter(
        (application) =>
          [
            "OA",
            ...INTERVIEW_STATUSES,
            "OFFER",
          ].includes(
            application.status
          )
      ).length;
    }

    const resumeCounts = {};

    for (const application of applications) {
      const resume =
        application.evaluation
          ?.selected_resume;

      if (!resume) {
        continue;
      }

      resumeCounts[resume] =
        (resumeCounts[resume] ?? 0) + 1;
    }

    const resumeUsage =
      Object.entries(resumeCounts)
        .map(([resume, count]) => ({
          resume: prettyName(resume),
          count,
        }))
        .sort(
          (a, b) => b.count - a.count
        );

    const runChartData =
      runHistory.map((run, index) => ({
        name: `Run ${index + 1}`,
        discovered:
          run.jobs_discovered,
        eligible:
          run.jobs_eligible,
        manual:
          run.manual_priority_count,
        agent:
          run.agent_apply_count,
      }));

    return {
      total,
      applied,
      interviews,
      offers,
      rejected,
      manualCount: manual.length,
      agentCount: agent.length,
      manualPositive:
        positiveOutcomes(manual),
      agentPositive:
        positiveOutcomes(agent),
      resumeUsage,
      runChartData,
    };
  }, [applications, runHistory]);


  if (loading) {
    return (
      <div className="page-center">
        <p>Loading...</p>
      </div>
    );
  }


  if (!session) {
    return (
      <div className="page-center">
        <div className="login-card">
          <div className="brand-mark">
            GH
          </div>

          <h1>
            Greenhouse Job Agent
          </h1>

          <p className="subtitle">
            Sign in to your private
            job-search dashboard.
          </p>

          <form onSubmit={login}>
            <label>Email</label>

            <input
              type="email"
              value={email}
              onChange={(event) =>
                setEmail(
                  event.target.value
                )
              }
              required
            />

            <label>Password</label>

            <input
              type="password"
              value={password}
              onChange={(event) =>
                setPassword(
                  event.target.value
                )
              }
              required
            />

            {error && (
              <p className="error">
                {error}
              </p>
            )}

            <button
              className="primary-button"
              type="submit"
              disabled={loginLoading}
            >
              {loginLoading
                ? "Signing in..."
                : "Sign In"}
            </button>
          </form>
        </div>
      </div>
    );
  }


  return (
    <div className="dashboard">
      <header className="header">
        <div>
          <div className="header-title-row">
            <h1>
              Greenhouse Job Agent
            </h1>
            <span className="model-badge">
              Scoring V2.1
            </span>
          </div>

          <p>
            Evidence-aware job-search command center
          </p>
        </div>

        <div className="header-actions">
          <button
            className="refresh-button"
            onClick={loadDashboard}
            disabled={dashboardLoading}
          >
            {dashboardLoading
              ? "Refreshing..."
              : "Refresh"}
          </button>

          <button
            className="logout-button"
            onClick={logout}
          >
            Sign Out
          </button>
        </div>
      </header>


      <nav className="tabs">
        <Tab
          label="Overview"
          active={
            activeTab === "overview"
          }
          onClick={() =>
            setActiveTab("overview")
          }
        />

        <Tab
          label="Action Required"
          active={
            activeTab === "action"
          }
          count={
            manualApplications.length +
            assistanceApplications.length
          }
          onClick={() =>
            setActiveTab("action")
          }
        />

        <Tab
          label="Applications"
          active={
            activeTab === "applications"
          }
          onClick={() =>
            setActiveTab("applications")
          }
        />

        <Tab
          label="Agent Activity"
          active={
            activeTab === "agent"
          }
          onClick={() =>
            setActiveTab("agent")
          }
        />

        <Tab
          label="Browser Runs"
          active={
            activeTab === "browser"
          }
          count={
            browserRuns.length
          }
          onClick={() =>
            setActiveTab("browser")
          }
        />

        <Tab
          label="Analytics"
          active={
            activeTab === "analytics"
          }
          onClick={() =>
            setActiveTab("analytics")
          }
        />
      </nav>


      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}


      {activeTab === "overview" && (
        <main>
          <section className="metrics metrics-six">
            <MetricCard
              label="Tracked Jobs"
              value={applications.length}
              hint={
                `${closedApplications.length} closed opening${
                  closedApplications.length === 1 ? "" : "s"
                } preserved in history`
              }
            />

            <MetricCard
              label="Manual Priority"
              value={manualApplications.length}
            />

            <MetricCard
              label="Agent Queue"
              value={
                agentApplications.filter(
                  (application) =>
                    application.status ===
                    "PENDING"
                ).length
              }
            />

            <MetricCard
              label="Needs Assistance"
              value={
                assistanceApplications.length
              }
            />

            <MetricCard
              label="Low Confidence"
              value={
                lowConfidenceApplications.length
              }
              hint={`<${CONFIDENCE_THRESHOLD}% evidence`}
            />

            <MetricCard
              label="Progressed"
              value={
                progressedApplications.length
              }
            />
          </section>


          <section className="two-column">
            <div className="panel">
              <div className="panel-heading">
                <div>
                  <h2>
                    Highest Priority
                  </h2>
                  <p>
                    Open jobs that pass all V2.1 Manual Priority gates.
                  </p>
                </div>
              </div>

              {manualApplications
                .slice(0, 5)
                .map((application) => (
                  <PriorityRow
                    key={application.id}
                    application={application}
                  />
                ))}

              {manualApplications.length === 0 && (
                <EmptyState
                  text="No manual applications waiting."
                />
              )}
            </div>


            <div className="panel">
              <div className="panel-heading">
                <div>
                  <h2>
                    Latest Agent Run
                  </h2>
                  <p>
                    Most recent scan statistics.
                  </p>
                </div>
              </div>

              {latestRun ? (
                <div className="run-grid">
                  <RunStat
                    label="Discovered"
                    value={
                      latestRun.jobs_discovered
                    }
                  />

                  <RunStat
                    label="Eligible"
                    value={
                      latestRun.jobs_eligible
                    }
                  />

                  <RunStat
                    label="Manual"
                    value={
                      latestRun.manual_priority_count
                    }
                  />

                  <RunStat
                    label="Agent"
                    value={
                      latestRun.agent_apply_count
                    }
                  />

                  <RunStat
                    label="Exp. Filtered"
                    value={
                      latestRun.experience_rejected_count
                    }
                  />

                  <RunStat
                    label="Runtime"
                    value={
                      latestRun.total_seconds
                        ? `${Number(
                            latestRun.total_seconds
                          ).toFixed(1)}s`
                        : "-"
                    }
                  />
                </div>
              ) : (
                <EmptyState
                  text="No agent runs found."
                />
              )}
            </div>
          </section>


          <section className="panel panel-spacing">
            <div className="panel-heading">
              <div>
                <h2>
                  V2.1 Evidence Health
                </h2>
                <p>
                  Coverage and confidence of the latest evaluation stored for each tracked job.
                </p>
              </div>
            </div>

            <div className="evidence-health-grid">
              <HealthStat
                label="V2.1 evaluations"
                value={evidenceStats.total}
              />

              <HealthStat
                label="Avg. fit"
                value={
                  evidenceStats.total
                    ? evidenceStats.averageFit.toFixed(1)
                    : "-"
                }
                suffix={
                  evidenceStats.total ? "/100" : ""
                }
              />

              <HealthStat
                label="Avg. confidence"
                value={
                  evidenceStats.total
                    ? evidenceStats.averageConfidence.toFixed(0)
                    : "-"
                }
                suffix={
                  evidenceStats.total ? "%" : ""
                }
              />

              <HealthStat
                label="Required evidence"
                value={evidenceStats.requiredEvidence}
              />

              <HealthStat
                label="Manual-ready"
                value={evidenceStats.manualReady}
              />

              <HealthStat
                label="Low confidence"
                value={
                  lowConfidenceApplications.length
                }
              />
            </div>
          </section>
        </main>
      )}


      {activeTab === "action" && (
        <main>
          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>
                  Manual Priority
                </h2>
                <p>
                  Fit ≥ {MANUAL_THRESHOLD}, confidence ≥ {CONFIDENCE_THRESHOLD}%, and required evidence present.
                </p>
              </div>

              <span className="count-badge">
                {manualApplications.length}
              </span>
            </div>

            {manualApplications.map(
              (application) => (
                <ActionCard
                  key={application.id}
                  application={application}
                  updateStatus={updateStatus}
                  updatingId={updatingId}
                  showEvidence
                />
              )
            )}

            {manualApplications.length === 0 && (
              <EmptyState
                text="No manual applications require attention."
              />
            )}
          </section>


          <section className="panel panel-spacing">
            <div className="panel-heading">
              <div>
                <h2>
                  Needs Assistance
                </h2>
                <p>
                  Eligibility or application questions that require human input.
                </p>
              </div>

              <span className="count-badge">
                {assistanceApplications.length}
              </span>
            </div>

            {assistanceApplications.map(
              (application) => (
                <ActionCard
                  key={application.id}
                  application={application}
                  updateStatus={updateStatus}
                  updatingId={updatingId}
                  showEvidence={false}
                  showAssistanceHandoff
                />
              )
            )}

            {assistanceApplications.length === 0 && (
              <EmptyState
                text="The agent does not currently need your help."
              />
            )}
          </section>
        </main>
      )}


      {activeTab === "applications" && (
        <main>
          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>
                  Application Tracker
                </h2>
                <p>
                  All application history, including jobs that have closed.
                </p>
              </div>

              <span className="count-badge">
                {applications.length}
              </span>
            </div>

            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Company</th>
                    <th>Role</th>
                    <th>Opening</th>
                    <th>Fit</th>
                    <th>Confidence</th>
                    <th>Selection</th>
                    <th>Resume</th>
                    <th>Method</th>
                    <th>Status</th>
                    <th>Job</th>
                  </tr>
                </thead>

                <tbody>
                  {applications.map(
                    (application) => (
                      <tr
                        key={application.id}
                        className={
                          jobIsActive(application)
                            ? ""
                            : "closed-job-row"
                        }
                      >
                        <td>
                          {application.jobs
                            ?.company ?? "-"}
                        </td>

                        <td>
                          <div className="role-cell">
                            <strong>
                              {application.jobs
                                ?.title ?? "-"}
                            </strong>

                            <span>
                              {application.jobs
                                ?.location ?? "-"}
                            </span>

                            {application.evaluation
                              ?.route && (
                              <RouteBadge
                                route={
                                  application
                                    .evaluation
                                    .route
                                }
                              />
                            )}
                          </div>
                        </td>

                        <td>
                          <JobStateBadge
                            isActive={
                              jobIsActive(application)
                            }
                          />
                        </td>

                        <td>
                          <ScoreBadge
                            score={
                              application
                                .evaluation
                                ?.score
                            }
                          />
                        </td>

                        <td>
                          <ConfidenceBadge
                            confidence={
                              application
                                .evaluation
                                ?.confidence
                            }
                          />
                        </td>

                        <td className="numeric-cell">
                          {formatNumber(
                            application
                              .evaluation
                              ?.selection_score
                          )}
                        </td>

                        <td>
                          {prettyName(
                            application
                              .evaluation
                              ?.selected_resume
                          )}
                        </td>

                        <td>
                          <MethodBadge
                            method={
                              application
                                .application_method
                            }
                          />
                        </td>

                        <td>
                          <select
                            className="status-select"
                            value={application.status}
                            disabled={
                              updatingId ===
                              application.id
                            }
                            onChange={(event) =>
                              updateStatus(
                                application.id,
                                event.target.value
                              )
                            }
                          >
                            {APPLICATION_STATUSES.map(
                              (status) => (
                                <option
                                  key={status}
                                  value={status}
                                >
                                  {prettyName(status)}
                                </option>
                              )
                            )}
                          </select>
                        </td>

                        <td>
                          {application.jobs?.url ? (
                            <a
                              className="job-link"
                              href={
                                application.jobs.url
                              }
                              target="_blank"
                              rel="noreferrer"
                            >
                              Open ↗
                            </a>
                          ) : (
                            "-"
                          )}
                        </td>
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </main>
      )}


      {activeTab === "agent" && (
        <main>
          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>
                  Agent Activity
                </h2>
                <p>
                  Latest discovery, filtering, scoring, and evidence quality.
                </p>
              </div>
            </div>

            {latestRun ? (
              <>
                <div className="activity-grid">
                  <RunStat
                    label="Jobs scanned"
                    value={latestRun.jobs_discovered}
                  />

                  <RunStat
                    label="Target roles"
                    value={latestRun.target_role_jobs}
                  />

                  <RunStat
                    label="US compatible"
                    value={latestRun.us_compatible_jobs}
                  />

                  <RunStat
                    label="Eligible"
                    value={latestRun.jobs_eligible}
                  />

                  <RunStat
                    label="Manual Priority"
                    value={latestRun.manual_priority_count}
                  />

                  <RunStat
                    label="Agent Apply"
                    value={latestRun.agent_apply_count}
                  />
                </div>

                <div className="timing-panel">
                  <h3>
                    Performance
                  </h3>

                  <TimingRow
                    label="Fetch"
                    value={latestRun.fetch_seconds}
                  />

                  <TimingRow
                    label="Filtering"
                    value={latestRun.filtering_seconds}
                  />

                  <TimingRow
                    label="Resume cache"
                    value={latestRun.resume_cache_seconds}
                  />

                  <TimingRow
                    label="Scoring"
                    value={latestRun.scoring_seconds}
                  />

                  <TimingRow
                    label="Total"
                    value={latestRun.total_seconds}
                  />
                </div>
              </>
            ) : (
              <EmptyState
                text="No agent run information found."
              />
            )}
          </section>


          <section className="panel panel-spacing">
            <div className="panel-heading">
              <div>
                <h2>
                  Low-Confidence Review
                </h2>
                <p>
                  Scored jobs with less than {CONFIDENCE_THRESHOLD}% evidence coverage. These stay out of Manual Priority unless the evidence gates pass.
                </p>
              </div>

              <span className="count-badge">
                {lowConfidenceApplications.length}
              </span>
            </div>

            {lowConfidenceApplications
              .slice(0, 20)
              .map((application) => (
                <EvidenceReviewRow
                  key={application.id}
                  application={application}
                />
              ))}

            {lowConfidenceApplications.length === 0 && (
              <EmptyState
                text="No low-confidence scored jobs."
              />
            )}
          </section>
        </main>
      )}


      {activeTab === "browser" && (
        <main>
          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>
                  Browser Queue Runs
                </h2>
                <p>
                  Sanitized Browser Agent queue history. Submission remains hard-blocked.
                </p>
              </div>

              <span className="count-badge">
                {browserRuns.length}
              </span>
            </div>

            {latestBrowserRun ? (
              <>
                <div className="browser-run-hero">
                  <div>
                    <span className="browser-run-kicker">
                      Latest Browser Queue Run
                    </span>

                    <strong>
                      {formatBrowserRunTime(
                        latestBrowserRun.started_at
                      )}
                    </strong>

                    <small>
                      {latestBrowserRun.board_token_filter
                        ? `Board: ${latestBrowserRun.board_token_filter}`
                        : "All configured boards"}
                      {" · "}
                      {latestBrowserRun.persist_handoffs
                        ? "Persisted"
                        : "Dry run"}
                    </small>
                  </div>

                  <BrowserRunHealthBadge
                    run={latestBrowserRun}
                  />
                </div>

                <div className="activity-grid browser-run-stats">
                  <RunStat
                    label="Selected"
                    value={
                      latestBrowserRun.selected_count
                    }
                  />

                  <RunStat
                    label="Completed"
                    value={
                      latestBrowserRun.completed_count
                    }
                  />

                  <RunStat
                    label="CAPTCHA"
                    value={
                      latestBrowserRun.challenge_count
                    }
                  />

                  <RunStat
                    label="Needs Assistance"
                    value={
                      latestBrowserRun.needs_assistance_count
                    }
                  />

                  <RunStat
                    label="Ready / No Submit"
                    value={
                      latestBrowserRun.ready_no_submit_count
                    }
                  />

                  <RunStat
                    label="Blocked + Errors"
                    value={
                      Number(
                        latestBrowserRun.blocked_count ?? 0
                      ) +
                      Number(
                        latestBrowserRun.error_count ?? 0
                      )
                    }
                  />
                </div>

                <div className="browser-safety-strip">
                  <span>
                    Browser modified:{" "}
                    <strong>
                      {latestBrowserRun.browser_modified_count ?? 0}
                    </strong>
                  </span>

                  <span>
                    Runtime:{" "}
                    <strong>
                      {formatNumber(
                        latestBrowserRun.total_seconds,
                        2
                      )}s
                    </strong>
                  </span>

                  <span className="browser-submit-zero">
                    Submissions:{" "}
                    <strong>
                      {latestBrowserRun.submitted_count ?? 0}
                    </strong>
                  </span>
                </div>
              </>
            ) : (
              <EmptyState
                text="No persisted Browser Queue runs yet."
              />
            )}
          </section>


          <section className="metrics metrics-six panel-spacing browser-history-summary">
            <MetricCard
              label="Recent Runs"
              value={
                browserRunStats.runs
              }
            />

            <MetricCard
              label="Jobs Selected"
              value={
                browserRunStats.selected
              }
            />

            <MetricCard
              label="Completed"
              value={
                browserRunStats.completed
              }
            />

            <MetricCard
              label="CAPTCHA Handoffs"
              value={
                browserRunStats.challenges
              }
            />

            <MetricCard
              label="Needs Assistance"
              value={
                browserRunStats.assistance
              }
            />

            <MetricCard
              label="Ready / No Submit"
              value={
                browserRunStats.readyNoSubmit
              }
              hint={
                `${browserRunStats.failures} blocked/error`
              }
            />
          </section>


          <section className="panel panel-spacing">
            <div className="panel-heading">
              <div>
                <h2>
                  Recent Queue History
                </h2>
                <p>
                  Up to 30 owner-scoped Browser Queue runs from Supabase.
                </p>
              </div>
            </div>

            {browserRuns.length > 0 ? (
              <div className="table-wrapper">
                <table className="browser-runs-table">
                  <thead>
                    <tr>
                      <th>Started</th>
                      <th>Scope</th>
                      <th>Mode</th>
                      <th>Selected</th>
                      <th>Completed</th>
                      <th>CAPTCHA</th>
                      <th>Assistance</th>
                      <th>Ready</th>
                      <th>Blocked</th>
                      <th>Errors</th>
                      <th>Runtime</th>
                      <th>Submit</th>
                    </tr>
                  </thead>

                  <tbody>
                    {browserRuns.map(
                      (run) => (
                        <tr
                          key={run.id}
                        >
                          <td>
                            <div className="browser-run-time-cell">
                              <strong>
                                {formatBrowserRunTime(
                                  run.started_at
                                )}
                              </strong>

                              <BrowserRunHealthBadge
                                run={run}
                                compact
                              />
                            </div>
                          </td>

                          <td>
                            {run.board_token_filter
                              ?? "All boards"}
                          </td>

                          <td>
                            {run.persist_handoffs
                              ? "Persisted"
                              : "Dry run"}
                          </td>

                          <td className="numeric-cell">
                            {run.selected_count ?? 0}
                          </td>

                          <td className="numeric-cell">
                            {run.completed_count ?? 0}
                          </td>

                          <td className="numeric-cell">
                            {run.challenge_count ?? 0}
                          </td>

                          <td className="numeric-cell">
                            {run.needs_assistance_count ?? 0}
                          </td>

                          <td className="numeric-cell">
                            {run.ready_no_submit_count ?? 0}
                          </td>

                          <td className="numeric-cell">
                            {run.blocked_count ?? 0}
                          </td>

                          <td className="numeric-cell">
                            {run.error_count ?? 0}
                          </td>

                          <td className="numeric-cell">
                            {formatNumber(
                              run.total_seconds,
                              2
                            )}s
                          </td>

                          <td>
                            <span className="browser-submit-badge">
                              {run.submitted_count ?? 0}
                            </span>
                          </td>
                        </tr>
                      )
                    )}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState
                text="Run the Browser Queue with --persist to create history."
              />
            )}
          </section>
        </main>
      )}


      {activeTab === "analytics" && (
        <main>
          <section className="metrics analytics-metrics metrics-six">
            <MetricCard
              label="Tracked Jobs"
              value={analytics.total}
              hint={`${closedApplications.length} closed`}
            />

            <MetricCard
              label="Applied"
              value={analytics.applied}
            />

            <MetricCard
              label="Interview Pipeline"
              value={analytics.interviews}
            />

            <MetricCard
              label="Offers"
              value={analytics.offers}
            />

            <MetricCard
              label="Avg. V2.1 Fit"
              value={
                evidenceStats.total
                  ? evidenceStats.averageFit.toFixed(1)
                  : "-"
              }
            />

            <MetricCard
              label="Avg. Confidence"
              value={
                evidenceStats.total
                  ? `${evidenceStats.averageConfidence.toFixed(0)}%`
                  : "-"
              }
            />
          </section>


          <section className="analytics-grid">
            <div className="panel chart-panel">
              <div className="panel-heading">
                <div>
                  <h2>
                    Job Discovery History
                  </h2>
                  <p>
                    Eligible and discovered jobs across agent runs.
                  </p>
                </div>
              </div>

              {analytics.runChartData.length > 0 ? (
                <div className="chart-container">
                  <ResponsiveContainer
                    width="100%"
                    height="100%"
                  >
                    <LineChart
                      data={analytics.runChartData}
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="#2b3038"
                      />

                      <XAxis
                        dataKey="name"
                        stroke="#929aa9"
                      />

                      <YAxis
                        stroke="#929aa9"
                      />

                      <Tooltip />
                      <Legend />

                      <Line
                        type="monotone"
                        dataKey="discovered"
                        stroke="currentColor"
                        strokeWidth={2}
                      />

                      <Line
                        type="monotone"
                        dataKey="eligible"
                        stroke="currentColor"
                        strokeWidth={2}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <EmptyState
                  text="No run history available."
                />
              )}
            </div>


            <div className="panel">
              <div className="panel-heading">
                <div>
                  <h2>
                    Manual vs Agent
                  </h2>
                  <p>
                    Current application routing and outcomes.
                  </p>
                </div>
              </div>

              <div className="comparison-grid">
                <ComparisonCard
                  label="Manual"
                  total={analytics.manualCount}
                  positive={analytics.manualPositive}
                />

                <ComparisonCard
                  label="Agent"
                  total={analytics.agentCount}
                  positive={analytics.agentPositive}
                />
              </div>
            </div>
          </section>


          <section className="analytics-grid analytics-spacing">
            <div className="panel chart-panel">
              <div className="panel-heading">
                <div>
                  <h2>
                    Queue History
                  </h2>
                  <p>
                    Manual-priority versus agent-apply volume.
                  </p>
                </div>
              </div>

              {analytics.runChartData.length > 0 ? (
                <div className="chart-container">
                  <ResponsiveContainer
                    width="100%"
                    height="100%"
                  >
                    <BarChart
                      data={analytics.runChartData}
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="#2b3038"
                      />

                      <XAxis
                        dataKey="name"
                        stroke="#929aa9"
                      />

                      <YAxis
                        stroke="#929aa9"
                      />

                      <Tooltip />
                      <Legend />

                      <Bar
                        dataKey="manual"
                        fill="currentColor"
                      />

                      <Bar
                        dataKey="agent"
                        fill="currentColor"
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <EmptyState
                  text="No queue history available."
                />
              )}
            </div>


            <div className="panel">
              <div className="panel-heading">
                <div>
                  <h2>
                    Resume Usage
                  </h2>
                  <p>
                    Which master resumes are being selected.
                  </p>
                </div>
              </div>

              {analytics.resumeUsage.map(
                (item) => (
                  <div
                    className="resume-usage-row"
                    key={item.resume}
                  >
                    <span>
                      {item.resume}
                    </span>

                    <strong>
                      {item.count}
                    </strong>
                  </div>
                )
              )}

              {analytics.resumeUsage.length === 0 && (
                <EmptyState
                  text="No resume usage data yet."
                />
              )}
            </div>
          </section>
        </main>
      )}
    </div>
  );
}


function Tab({
  label,
  active,
  count,
  onClick,
}) {
  return (
    <button
      className={
        active
          ? "tab active"
          : "tab"
      }
      onClick={onClick}
    >
      {label}

      {count > 0 && (
        <span className="tab-count">
          {count}
        </span>
      )}
    </button>
  );
}


function formatBrowserRunTime(
  value
) {
  if (!value) {
    return "-";
  }

  const parsed = new Date(
    value
  );

  if (
    Number.isNaN(
      parsed.getTime()
    )
  ) {
    return String(value);
  }

  return parsed.toLocaleString();
}


function BrowserRunHealthBadge({
  run,
  compact = false,
}) {
  const submitted =
    Number(
      run?.submitted_count ?? 0
    );

  const failures =
    Number(
      run?.blocked_count ?? 0
    ) +
    Number(
      run?.error_count ?? 0
    );

  const assistance =
    Number(
      run?.needs_assistance_count ?? 0
    );

  let label = "Clean";
  let className =
    "browser-run-health clean";

  if (submitted > 0) {
    label = "Safety violation";
    className =
      "browser-run-health danger";
  } else if (failures > 0) {
    label = "Blocked / error";
    className =
      "browser-run-health warning";
  } else if (assistance > 0) {
    label = "Assistance";
    className =
      "browser-run-health assistance";
  }

  if (compact) {
    className += " compact";
  }

  return (
    <span className={className}>
      {label}
    </span>
  );
}


function MetricCard({
  label,
  value,
  hint,
}) {
  return (
    <div className="metric-card">
      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>

      {hint && (
        <small>
          {hint}
        </small>
      )}
    </div>
  );
}


function HealthStat({
  label,
  value,
  suffix = "",
}) {
  return (
    <div className="health-stat">
      <span>
        {label}
      </span>

      <strong>
        {value}{suffix}
      </strong>
    </div>
  );
}


function RunStat({
  label,
  value,
}) {
  return (
    <div className="run-stat">
      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>
    </div>
  );
}


function TimingRow({
  label,
  value,
}) {
  return (
    <div className="timing-row">
      <span>
        {label}
      </span>

      <strong>
        {value !== null &&
        value !== undefined
          ? `${Number(value).toFixed(2)}s`
          : "-"}
      </strong>
    </div>
  );
}


function PriorityRow({
  application,
}) {
  const evaluation =
    application.evaluation;

  return (
    <div className="priority-row v21-priority-row">
      <ScoreBadge
        score={evaluation?.score}
      />

      <div className="priority-main">
        <strong>
          {application.jobs?.title}
        </strong>

        <span>
          {application.jobs?.company}
          {" · "}
          {application.jobs?.location}
        </span>

        <div className="priority-meta">
          <ConfidenceBadge
            confidence={evaluation?.confidence}
          />

          <span>
            Selection {formatNumber(
              evaluation?.selection_score
            )}
          </span>

          <span>
            {prettyName(
              evaluation?.selected_resume
            )}
          </span>
        </div>
      </div>

      <a
        href={application.jobs?.url}
        target="_blank"
        rel="noreferrer"
        className="job-link"
      >
        Apply ↗
      </a>
    </div>
  );
}


function ActionCard({
  application,
  updateStatus,
  updatingId,
  showEvidence,
  showAssistanceHandoff = false,
}) {
  const evaluation =
    application.evaluation;

  const browserHandoff =
    showAssistanceHandoff
      ? getBrowserHandoff(application)
      : null;

  return (
    <div className="action-card action-card-v21">
      <div className="action-score-stack">
        <ScoreBadge
          score={evaluation?.score}
        />

        <ConfidenceBadge
          confidence={evaluation?.confidence}
        />
      </div>

      <div className="action-main">
        <div className="action-title-line">
          <h3>
            {application.jobs?.title}
          </h3>

          {evaluation?.route && (
            <RouteBadge
              route={evaluation.route}
            />
          )}
        </div>

        <p>
          {application.jobs?.company}
          {" · "}
          {application.jobs?.location}
        </p>

        <div className="action-meta">
          <span>
            Resume:{" "}
            <strong>
              {prettyName(
                evaluation?.selected_resume
              )}
            </strong>
          </span>

          <span>
            Selection:{" "}
            <strong>
              {formatNumber(
                evaluation?.selection_score
              )}
            </strong>
          </span>

          <span>
            Method:{" "}
            <strong>
              {application.application_method}
            </strong>
          </span>
        </div>

        {showEvidence && (
          <FitBreakdown
            evaluation={evaluation}
          />
        )}

        {application.assistance_reason &&
          !browserHandoff && (
          <div className="assistance-message">
            {application.assistance_reason}
          </div>
        )}

        {browserHandoff && (
          <BrowserAssistanceHandoff
            application={application}
            handoff={browserHandoff}
          />
        )}
      </div>

      <div className="action-buttons">
        <a
          href={application.jobs?.url}
          target="_blank"
          rel="noreferrer"
          className="primary-link"
        >
          Open Application
        </a>

        {application.status === "PENDING" && (
          <button
            className="secondary-button"
            disabled={
              updatingId === application.id
            }
            onClick={() =>
              updateStatus(
                application.id,
                "APPLIED"
              )
            }
          >
            Mark Applied
          </button>
        )}
      </div>
    </div>
  );
}


function BrowserAssistanceHandoff({
  application,
  handoff,
}) {
  const summary =
    objectOrNull(handoff.summary) ?? {};

  const challenge =
    objectOrNull(handoff.challenge) ?? {};

  const readyItems =
    safeHandoffItems(
      handoff.deterministic_ready
    );

  const humanItems =
    safeHandoffItems(
      handoff.human_assistance
    );

  const routeReasons =
    Array.isArray(handoff.route_reasons)
      ? handoff.route_reasons.filter(
          (reason) =>
            typeof reason === "string" &&
            reason.trim()
        )
      : [];

  const challengeReasons =
    Array.isArray(challenge.reasons)
      ? challenge.reasons.filter(
          (reason) =>
            typeof reason === "string" &&
            reason.trim()
        )
      : [];

  const readyCount =
    safeHandoffCount(
      summary.ready_count,
      readyItems.length
    );

  const requiredHumanCount =
    safeHandoffCount(
      summary.required_human_count,
      humanItems.filter(
        (item) => item.required
      ).length
    );

  const challengeDetected =
    challenge.detected === true ||
    summary.challenge_detected === true;

  const selectedResume =
    typeof handoff.selected_resume === "string" &&
    handoff.selected_resume.trim()
      ? handoff.selected_resume
      : (
          application.evaluation
            ?.selected_resume_file ??
          application.evaluation
            ?.selected_resume ??
          "-"
        );

  const routeMismatch =
    application.evaluation?.route &&
    application.evaluation.route !==
      "AGENT_APPLY";

  return (
    <div className="browser-handoff">
      <div className="browser-handoff-header">
        <div>
          <strong>
            Browser assistance handoff
          </strong>

          <span>
            Deterministic answers are ready;
            human-only fields remain untouched.
          </span>
        </div>

        <div className="handoff-badges">
          <span className="handoff-badge browser">
            Browser V1
          </span>

          {challengeDetected && (
            <span className="handoff-badge challenge">
              CAPTCHA
            </span>
          )}

          <span className="handoff-badge ready">
            {readyCount} ready
          </span>

          <span className="handoff-badge review">
            {requiredHumanCount} need review
          </span>

          {routeMismatch && (
            <span className="handoff-badge warning">
              Route mismatch
            </span>
          )}
        </div>
      </div>

      <div className="handoff-resume">
        <span>
          Selected resume
        </span>

        <strong>
          {selectedResume}
        </strong>
      </div>

      {routeMismatch && (
        <div className="handoff-routing-note">
          Latest matcher route is{" "}
          <strong>
            {prettyName(
              application.evaluation?.route
            )}
          </strong>
          . Browser handoffs are only persisted
          for Agent Apply jobs under the current
          route guard.
        </div>
      )}

      <details className="handoff-details">
        <summary>
          Review application handoff
        </summary>

        <div className="handoff-detail-grid">
          <section className="handoff-section">
            <h4>
              Why assistance is needed
            </h4>

            {routeReasons.length > 0 ? (
              <ul>
                {routeReasons.map(
                  (reason, index) => (
                    <li key={`${reason}-${index}`}>
                      {reason}
                    </li>
                  )
                )}
              </ul>
            ) : (
              <p>
                {application.assistance_reason ??
                  "Human review is required."}
              </p>
            )}

            {challengeReasons.length > 0 && (
              <div className="handoff-technical">
                <span>
                  Challenge signal
                </span>

                {challengeReasons.map(
                  (reason, index) => (
                    <code
                      key={`${reason}-${index}`}
                    >
                      {reason}
                    </code>
                  )
                )}
              </div>
            )}
          </section>

          <section className="handoff-section">
            <h4>
              Ready from profile / policy
            </h4>

            {readyItems.length > 0 ? (
              <ul className="handoff-item-list">
                {readyItems.map(
                  (item, index) => {
                    const displayAnswer =
                      safePolicyDisplayAnswer(
                        item
                      );

                    return (
                      <li
                        key={
                          item.answer_key ??
                          `${item.label}-${index}`
                        }
                      >
                        <div>
                          <strong>
                            {item.label ?? "Ready field"}
                          </strong>

                          <small>
                            {prettyName(
                              item.category
                            )}
                          </small>
                        </div>

                        <span className="handoff-ready-value">
                          {displayAnswer ??
                            "Ready"}
                        </span>
                      </li>
                    );
                  }
                )}
              </ul>
            ) : (
              <p>
                No deterministic fields are stored
                in this handoff.
              </p>
            )}
          </section>

          <section className="handoff-section handoff-section-wide">
            <h4>
              Human review needed
            </h4>

            {humanItems.length > 0 ? (
              <ul className="handoff-item-list human">
                {humanItems.map(
                  (item, index) => (
                    <li
                      key={
                        item.answer_key ??
                        `${item.label}-${index}`
                      }
                    >
                      <div>
                        <strong>
                          {item.label ??
                            "Application question"}
                        </strong>

                        <small>
                          {prettyName(
                            item.category
                          )}
                        </small>
                      </div>

                      <span
                        className={
                          item.required
                            ? "handoff-field-badge required"
                            : "handoff-field-badge optional"
                        }
                      >
                        {item.required
                          ? "Required"
                          : "Optional"}
                      </span>
                    </li>
                  )
                )}
              </ul>
            ) : (
              <p>
                No human-review fields are stored
                in this handoff.
              </p>
            )}
          </section>
        </div>
      </details>
    </div>
  );
}


function FitBreakdown({ evaluation }) {
  if (!hasV21Evidence(evaluation)) {
    return (
      <div className="legacy-evaluation-note">
        V2.1 evidence details are not available for this older evaluation.
      </div>
    );
  }

  const explanation =
    getExplanation(evaluation);

  const contributions =
    explanation.weighted_contributions ?? {};

  const gateFailures =
    explanation.gate_failures ?? [];

  return (
    <div className="fit-breakdown">
      <div className="fit-breakdown-header">
        <span>
          Evidence {formatNumber(
            explanation.active_weight,
            0
          )}/{formatNumber(
            explanation.total_weight,
            0
          )}
        </span>

        <span>
          Required evidence:{" "}
          <strong>
            {explanation.required_evidence_gate
              ? "Yes"
              : "No"}
          </strong>
        </span>
      </div>

      <div className="component-grid">
        {FIT_COMPONENTS.map(
          ([component, label, scoreKey]) => {
            const available =
              componentAvailable(
                evaluation,
                component
              );

            return (
              <div
                className={
                  available
                    ? "component-card"
                    : "component-card missing"
                }
                key={component}
              >
                <span>
                  {label}
                </span>

                <strong>
                  {available
                    ? formatNumber(
                        evaluation?.[scoreKey]
                      )
                    : "N/A"}
                </strong>

                <small>
                  {available
                    ? `${formatNumber(
                        contributions[
                          component
                        ] ?? 0
                      )} pts`
                    : "missing evidence"}
                </small>
              </div>
            );
          }
        )}
      </div>

      <div className="gate-row">
        <GatePill
          label={`Fit ≥ ${MANUAL_THRESHOLD}`}
          passed={
            Boolean(
              explanation.score_gate
            )
          }
        />

        <GatePill
          label={`Confidence ≥ ${CONFIDENCE_THRESHOLD}%`}
          passed={
            Boolean(
              explanation.confidence_gate
            )
          }
        />

        <GatePill
          label="Required evidence"
          passed={
            Boolean(
              explanation.required_evidence_gate
            )
          }
        />
      </div>

      {gateFailures.length > 0 && (
        <div className="gate-failure-text">
          Manual gate: {gateFailures.join("; ")}
        </div>
      )}
    </div>
  );
}


function GatePill({
  label,
  passed,
}) {
  return (
    <span
      className={
        passed
          ? "gate-pill pass"
          : "gate-pill fail"
      }
    >
      {passed ? "✓" : "×"} {label}
    </span>
  );
}


function EvidenceReviewRow({
  application,
}) {
  const evaluation =
    application.evaluation;

  const explanation =
    getExplanation(evaluation);

  const availability =
    getAvailability(evaluation);

  const missing = [
    "required",
    "preferred",
    "experience",
  ].filter(
    (component) =>
      !availability[component]
  );

  return (
    <div className="evidence-review-row">
      <div className="evidence-review-score">
        <ScoreBadge
          score={evaluation?.score}
        />

        <ConfidenceBadge
          confidence={evaluation?.confidence}
        />
      </div>

      <div className="evidence-review-main">
        <strong>
          {application.jobs?.title}
        </strong>

        <span>
          {application.jobs?.company}
          {" · "}
          {application.jobs?.location}
        </span>

        <small>
          Missing: {missing.length
            ? missing
                .map(prettyName)
                .join(", ")
            : "None"}
        </small>

        {(explanation.gate_failures ?? [])
          .length > 0 && (
          <small className="review-reason">
            {(explanation.gate_failures ?? [])
              .join("; ")}
          </small>
        )}
      </div>

      <a
        href={application.jobs?.url}
        target="_blank"
        rel="noreferrer"
        className="job-link"
      >
        Open ↗
      </a>
    </div>
  );
}


function MethodBadge({ method }) {
  const className =
    method === "MANUAL"
      ? "method-badge manual"
      : "method-badge agent";

  return (
    <span className={className}>
      {method ?? "-"}
    </span>
  );
}


function ComparisonCard({
  label,
  total,
  positive,
}) {
  const rate =
    total > 0
      ? (
          (positive / total) *
          100
        ).toFixed(1)
      : "0.0";

  return (
    <div className="comparison-card">
      <span>
        {label}
      </span>

      <strong>
        {total}
      </strong>

      <p>
        Positive outcomes:{" "}
        {positive}
      </p>

      <p>
        Progress rate:{" "}
        {rate}%
      </p>
    </div>
  );
}


function EmptyState({ text }) {
  return (
    <div className="empty-state">
      {text}
    </div>
  );
}


export default App;

