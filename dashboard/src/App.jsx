import { useEffect, useMemo, useState } from "react";
import { supabase } from "./lib/supabase";


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


function prettyName(value) {
  if (!value) {
    return "-";
  }

  return value
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (letter) =>
      letter.toUpperCase()
    );
}


function ScoreBadge({ score }) {
  if (score === null || score === undefined) {
    return <span className="score-badge">-</span>;
  }

  let className = "score-badge";

  if (score >= 85) {
    className += " score-high";
  } else if (score >= 75) {
    className += " score-medium";
  } else {
    className += " score-low";
  }

  return (
    <span className={className}>
      {Number(score).toFixed(2)}
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

  const [activeTab, setActiveTab] =
    useState("overview");

  const [loading, setLoading] =
    useState(true);

  const [loginLoading, setLoginLoading] =
    useState(false);

  const [error, setError] =
    useState("");

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

    try {
      // ------------------------------------------------------
      // APPLICATIONS + JOBS
      // ------------------------------------------------------

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
            detected_profile
          )
        `)
        .order("created_at", {
          ascending: false,
        });

      if (applicationError) {
        throw applicationError;
      }

      // ------------------------------------------------------
      // EVALUATIONS
      //
      // There can eventually be multiple evaluations for a
      // job across multiple agent runs.
      //
      // We order newest-first and retain only the newest one.
      // ------------------------------------------------------

      const {
        data: evaluationData,
        error: evaluationError,
      } = await supabase
        .from("job_evaluations")
        .select(`
          job_id,
          score,
          route,
          selected_resume,
          role_score,
          required_score,
          preferred_score,
          semantic_score,
          experience_score,
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

      const mergedApplications = (
        applicationData ?? []
      ).map((application) => ({
        ...application,

        evaluation:
          latestEvaluationByJob[
            application.job_id
          ] ?? null,
      }));

      setApplications(
        mergedApplications
      );

      // ------------------------------------------------------
      // LATEST AGENT RUN
      // ------------------------------------------------------

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
        .limit(1);

      if (runError) {
        throw runError;
      }

      setLatestRun(
        runData?.[0] ?? null
      );
    } catch (err) {
      setError(err.message);
    }
  }


  async function updateStatus(
    applicationId,
    status
  ) {
    setUpdatingId(
      applicationId
    );

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


  const manualApplications =
    useMemo(
      () =>
        applications
          .filter(
            (application) =>
              application
                .evaluation
                ?.route ===
                "MANUAL_PRIORITY" &&
              application.status ===
                "PENDING"
          )
          .sort(
            (a, b) =>
              Number(
                b.evaluation?.score ??
                  0
              ) -
              Number(
                a.evaluation?.score ??
                  0
              )
          ),
      [applications]
    );


  const assistanceApplications =
    useMemo(
      () =>
        applications.filter(
          (application) =>
            application.needs_assistance
        ),
      [applications]
    );


  const agentApplications =
    useMemo(
      () =>
        applications.filter(
          (application) =>
            application
              .evaluation
              ?.route ===
            "AGENT_APPLY"
        ),
      [applications]
    );


  const progressedApplications =
    useMemo(
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

            <label>
              Email
            </label>

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

            <label>
              Password
            </label>

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

      {/* ================================================== */}
      {/* HEADER */}
      {/* ================================================== */}

      <header className="header">

        <div>
          <h1>
            Greenhouse Job Agent
          </h1>

          <p>
            AI-assisted job-search
            command center
          </p>
        </div>

        <button
          className="logout-button"
          onClick={logout}
        >
          Sign Out
        </button>

      </header>


      {/* ================================================== */}
      {/* NAVIGATION */}
      {/* ================================================== */}

      <nav className="tabs">

        <button
          className={
            activeTab === "overview"
              ? "tab active"
              : "tab"
          }
          onClick={() =>
            setActiveTab(
              "overview"
            )
          }
        >
          Overview
        </button>

        <button
          className={
            activeTab === "action"
              ? "tab active"
              : "tab"
          }
          onClick={() =>
            setActiveTab(
              "action"
            )
          }
        >
          Action Required

          {manualApplications.length +
            assistanceApplications.length >
            0 && (
            <span className="tab-count">
              {manualApplications.length +
                assistanceApplications.length}
            </span>
          )}
        </button>

        <button
          className={
            activeTab ===
            "applications"
              ? "tab active"
              : "tab"
          }
          onClick={() =>
            setActiveTab(
              "applications"
            )
          }
        >
          Applications
        </button>

        <button
          className={
            activeTab === "agent"
              ? "tab active"
              : "tab"
          }
          onClick={() =>
            setActiveTab(
              "agent"
            )
          }
        >
          Agent Activity
        </button>

      </nav>


      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}


      {/* ================================================== */}
      {/* OVERVIEW */}
      {/* ================================================== */}

      {activeTab === "overview" && (
        <main>

          <section className="metrics">

            <MetricCard
              label="Tracked Jobs"
              value={
                applications.length
              }
            />

            <MetricCard
              label="Manual Priority"
              value={
                manualApplications
                  .length
              }
            />

            <MetricCard
              label="Agent Queue"
              value={
                agentApplications
                  .filter(
                    (application) =>
                      application.status ===
                      "PENDING"
                  )
                  .length
              }
            />

            <MetricCard
              label="Needs Assistance"
              value={
                assistanceApplications
                  .length
              }
            />

            <MetricCard
              label="Progressed"
              value={
                progressedApplications
                  .length
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
                    Strongest matches for
                    you to apply manually.
                  </p>
                </div>
              </div>

              {manualApplications
                .slice(0, 5)
                .map(
                  (application) => (
                    <PriorityRow
                      key={
                        application.id
                      }
                      application={
                        application
                      }
                    />
                  )
                )}

              {manualApplications
                .length === 0 && (
                <EmptyState
                  text={
                    "No manual applications waiting."
                  }
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
                    Most recent job scan
                    statistics.
                  </p>
                </div>
              </div>

              {latestRun ? (
                <div className="run-grid">

                  <RunStat
                    label="Discovered"
                    value={
                      latestRun
                        .jobs_discovered
                    }
                  />

                  <RunStat
                    label="Eligible"
                    value={
                      latestRun
                        .jobs_eligible
                    }
                  />

                  <RunStat
                    label="Manual"
                    value={
                      latestRun
                        .manual_priority_count
                    }
                  />

                  <RunStat
                    label="Agent"
                    value={
                      latestRun
                        .agent_apply_count
                    }
                  />

                  <RunStat
                    label="Rejected"
                    value={
                      latestRun
                        .experience_rejected_count
                    }
                  />

                  <RunStat
                    label="Runtime"
                    value={
                      latestRun
                        .total_seconds
                        ? `${Number(
                            latestRun
                              .total_seconds
                          ).toFixed(
                            1
                          )}s`
                        : "-"
                    }
                  />

                </div>
              ) : (
                <EmptyState
                  text={
                    "No agent runs found."
                  }
                />
              )}

            </div>

          </section>

        </main>
      )}


      {/* ================================================== */}
      {/* ACTION REQUIRED */}
      {/* ================================================== */}

      {activeTab === "action" && (
        <main>

          <section className="panel">

            <div className="panel-heading">
              <div>
                <h2>
                  Manual Priority
                </h2>

                <p>
                  85+ matches waiting for
                  you.
                </p>
              </div>

              <span className="count-badge">
                {
                  manualApplications
                    .length
                }
              </span>
            </div>

            {manualApplications.map(
              (application) => (
                <ActionCard
                  key={
                    application.id
                  }
                  application={
                    application
                  }
                  updateStatus={
                    updateStatus
                  }
                  updatingId={
                    updatingId
                  }
                />
              )
            )}

            {manualApplications
              .length === 0 && (
              <EmptyState
                text={
                  "No manual applications require attention."
                }
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
                  Applications paused for
                  your input.
                </p>
              </div>

              <span className="count-badge">
                {
                  assistanceApplications
                    .length
                }
              </span>
            </div>

            {assistanceApplications.map(
              (application) => (
                <ActionCard
                  key={
                    application.id
                  }
                  application={
                    application
                  }
                  updateStatus={
                    updateStatus
                  }
                  updatingId={
                    updatingId
                  }
                />
              )
            )}

            {assistanceApplications
              .length === 0 && (
              <EmptyState
                text={
                  "The agent does not currently need your help."
                }
              />
            )}

          </section>

        </main>
      )}


      {/* ================================================== */}
      {/* APPLICATIONS */}
      {/* ================================================== */}

      {activeTab ===
        "applications" && (
        <main>

          <section className="panel">

            <div className="panel-heading">
              <div>
                <h2>
                  Application Tracker
                </h2>

                <p>
                  Track every application
                  through the recruiting
                  pipeline.
                </p>
              </div>

              <span className="count-badge">
                {
                  applications.length
                }
              </span>
            </div>

            <div className="table-wrapper">

              <table>

                <thead>
                  <tr>
                    <th>
                      Company
                    </th>

                    <th>
                      Role
                    </th>

                    <th>
                      Score
                    </th>

                    <th>
                      Resume
                    </th>

                    <th>
                      Method
                    </th>

                    <th>
                      Status
                    </th>

                    <th>
                      Job
                    </th>
                  </tr>
                </thead>

                <tbody>

                  {applications.map(
                    (application) => (
                      <tr
                        key={
                          application.id
                        }
                      >

                        <td>
                          {
                            application
                              .jobs
                              ?.company ??
                            "-"
                          }
                        </td>

                        <td>
                          <div className="role-cell">

                            <strong>
                              {
                                application
                                  .jobs
                                  ?.title ??
                                "-"
                              }
                            </strong>

                            <span>
                              {
                                application
                                  .jobs
                                  ?.location ??
                                "-"
                              }
                            </span>

                          </div>
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
                            value={
                              application
                                .status
                            }
                            disabled={
                              updatingId ===
                              application.id
                            }
                            onChange={(
                              event
                            ) =>
                              updateStatus(
                                application.id,
                                event.target
                                  .value
                              )
                            }
                          >

                            {APPLICATION_STATUSES.map(
                              (
                                status
                              ) => (
                                <option
                                  key={
                                    status
                                  }
                                  value={
                                    status
                                  }
                                >
                                  {
                                    prettyName(
                                      status
                                    )
                                  }
                                </option>
                              )
                            )}

                          </select>

                        </td>

                        <td>

                          {application
                            .jobs
                            ?.url ? (
                            <a
                              className="job-link"
                              href={
                                application
                                  .jobs
                                  .url
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


      {/* ================================================== */}
      {/* AGENT ACTIVITY */}
      {/* ================================================== */}

      {activeTab === "agent" && (
        <main>

          <section className="panel">

            <div className="panel-heading">
              <div>
                <h2>
                  Agent Activity
                </h2>

                <p>
                  Latest discovery and
                  scoring performance.
                </p>
              </div>
            </div>

            {latestRun ? (
              <>

                <div className="activity-grid">

                  <RunStat
                    label="Jobs scanned"
                    value={
                      latestRun
                        .jobs_discovered
                    }
                  />

                  <RunStat
                    label="Target roles"
                    value={
                      latestRun
                        .target_role_jobs
                    }
                  />

                  <RunStat
                    label="US compatible"
                    value={
                      latestRun
                        .us_compatible_jobs
                    }
                  />

                  <RunStat
                    label="Eligible"
                    value={
                      latestRun
                        .jobs_eligible
                    }
                  />

                  <RunStat
                    label="Manual Priority"
                    value={
                      latestRun
                        .manual_priority_count
                    }
                  />

                  <RunStat
                    label="Agent Apply"
                    value={
                      latestRun
                        .agent_apply_count
                    }
                  />

                </div>


                <div className="timing-panel">

                  <h3>
                    Performance
                  </h3>

                  <TimingRow
                    label="Fetch"
                    value={
                      latestRun
                        .fetch_seconds
                    }
                  />

                  <TimingRow
                    label="Filtering"
                    value={
                      latestRun
                        .filtering_seconds
                    }
                  />

                  <TimingRow
                    label="Resume cache"
                    value={
                      latestRun
                        .resume_cache_seconds
                    }
                  />

                  <TimingRow
                    label="Scoring"
                    value={
                      latestRun
                        .scoring_seconds
                    }
                  />

                  <TimingRow
                    label="Total"
                    value={
                      latestRun
                        .total_seconds
                    }
                  />

                </div>

              </>
            ) : (
              <EmptyState
                text={
                  "No agent run information found."
                }
              />
            )}

          </section>

        </main>
      )}

    </div>
  );
}


function MetricCard({
  label,
  value,
}) {
  return (
    <div className="metric-card">

      <span>
        {label}
      </span>

      <strong>
        {value}
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
          ? `${Number(
              value
            ).toFixed(2)}s`
          : "-"}
      </strong>

    </div>
  );
}


function PriorityRow({
  application,
}) {
  return (
    <div className="priority-row">

      <ScoreBadge
        score={
          application
            .evaluation
            ?.score
        }
      />

      <div className="priority-main">

        <strong>
          {
            application.jobs
              ?.title
          }
        </strong>

        <span>
          {
            application.jobs
              ?.company
          }
          {" · "}
          {
            application.jobs
              ?.location
          }
        </span>

      </div>

      <span className="priority-resume">
        {prettyName(
          application
            .evaluation
            ?.selected_resume
        )}
      </span>

      <a
        href={
          application.jobs?.url
        }
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
}) {
  return (
    <div className="action-card">

      <div className="action-score">

        <ScoreBadge
          score={
            application
              .evaluation
              ?.score
          }
        />

      </div>

      <div className="action-main">

        <h3>
          {
            application.jobs
              ?.title
          }
        </h3>

        <p>
          {
            application.jobs
              ?.company
          }
          {" · "}
          {
            application.jobs
              ?.location
          }
        </p>

        <div className="action-meta">

          <span>
            Resume:
            {" "}
            <strong>
              {prettyName(
                application
                  .evaluation
                  ?.selected_resume
              )}
            </strong>
          </span>

          <span>
            Method:
            {" "}
            <strong>
              {
                application
                  .application_method
              }
            </strong>
          </span>

        </div>

        {application
          .assistance_reason && (
          <div className="assistance-message">
            {
              application
                .assistance_reason
            }
          </div>
        )}

      </div>


      <div className="action-buttons">

        <a
          href={
            application.jobs?.url
          }
          target="_blank"
          rel="noreferrer"
          className="primary-link"
        >
          Open Application
        </a>

        {application.status ===
          "PENDING" && (
          <button
            className="secondary-button"
            disabled={
              updatingId ===
              application.id
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


function MethodBadge({
  method,
}) {
  const className =
    method === "MANUAL"
      ? "method-badge manual"
      : "method-badge agent";

  return (
    <span className={className}>
      {method}
    </span>
  );
}


function EmptyState({
  text,
}) {
  return (
    <div className="empty-state">
      {text}
    </div>
  );
}


export default App;
