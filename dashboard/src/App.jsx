import { useEffect, useState } from "react";
import { supabase } from "./lib/supabase";

function App() {
  const [session, setSession] = useState(null);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [applications, setApplications] = useState([]);

  const [loading, setLoading] = useState(true);
  const [loginLoading, setLoginLoading] = useState(false);

  const [error, setError] = useState("");

  useEffect(() => {
    initializeAuth();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(
      (_event, newSession) => {
        setSession(newSession);

        if (newSession) {
          loadApplications();
        } else {
          setApplications([]);
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
        await loadApplications();
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

  async function loadApplications() {
    const { data, error: queryError } = await supabase
      .from("applications")
      .select(`
        id,
        application_method,
        status,
        needs_assistance,
        applied_at,
        last_updated_at,
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

    if (queryError) {
      setError(queryError.message);
      return;
    }

    setApplications(data ?? []);
  }

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
          <h1>Greenhouse Job Agent</h1>

          <p className="subtitle">
            Sign in to your private job-search dashboard.
          </p>

          <form onSubmit={login}>
            <label>Email</label>

            <input
              type="email"
              value={email}
              onChange={(event) =>
                setEmail(event.target.value)
              }
              required
            />

            <label>Password</label>

            <input
              type="password"
              value={password}
              onChange={(event) =>
                setPassword(event.target.value)
              }
              required
            />

            {error && (
              <p className="error">{error}</p>
            )}

            <button
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

  const manualCount = applications.filter(
    (application) =>
      application.application_method === "MANUAL"
  ).length;

  const agentCount = applications.filter(
    (application) =>
      application.application_method === "AGENT"
  ).length;

  const assistanceCount = applications.filter(
    (application) =>
      application.needs_assistance
  ).length;

  const appliedCount = applications.filter(
    (application) =>
      application.status !== "PENDING"
  ).length;

  return (
    <div className="dashboard">
      <header className="header">
        <div>
          <h1>Greenhouse Job Agent</h1>

          <p>
            Private job-search command center
          </p>
        </div>

        <button
          className="logout-button"
          onClick={logout}
        >
          Sign Out
        </button>
      </header>

      <main>
        <section className="metrics">
          <div className="metric-card">
            <span>Total Applications</span>

            <strong>
              {applications.length}
            </strong>
          </div>

          <div className="metric-card">
            <span>Manual Priority</span>

            <strong>
              {manualCount}
            </strong>
          </div>

          <div className="metric-card">
            <span>Agent Apply</span>

            <strong>
              {agentCount}
            </strong>
          </div>

          <div className="metric-card">
            <span>Needs Assistance</span>

            <strong>
              {assistanceCount}
            </strong>
          </div>

          <div className="metric-card">
            <span>Progressed</span>

            <strong>
              {appliedCount}
            </strong>
          </div>
        </section>

        <section className="applications-section">
          <div className="section-heading">
            <div>
              <h2>Applications</h2>

              <p>
                Jobs discovered and tracked by
                your agent.
              </p>
            </div>
          </div>

          {error && (
            <p className="error">{error}</p>
          )}

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Role</th>
                  <th>Location</th>
                  <th>Method</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>

              <tbody>
                {applications.map(
                  (application) => (
                    <tr key={application.id}>
                      <td>
                        {application.jobs?.company ??
                          "Unknown"}
                      </td>

                      <td>
                        {application.jobs?.title ??
                          "Unknown"}
                      </td>

                      <td>
                        {application.jobs?.location ??
                          "Unknown"}
                      </td>

                      <td>
                        {application.application_method}
                      </td>

                      <td>
                        {application.status}
                      </td>

                      <td>
                        {application.jobs?.url ? (
                          <a
                            href={
                              application.jobs.url
                            }
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open Job
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
    </div>
  );
}

export default App;
