import { useState } from "react";
import { login, register } from "../api/auth";
import "../preview/preview.css";

export default function SignIn({ onSuccess }) {
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return (
    <main className="jh-auth">
      <form
        className="jh-auth-card"
        onSubmit={async (event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          setBusy(true);
          setError("");
          try {
            const user = await (creating ? register : login)({
              email: form.get("email"),
              password: form.get("password"),
            });
            onSuccess(user);
          } catch (failure) {
            setError(
              typeof failure.response?.data?.detail === "string"
                ? failure.response.data.detail
                : "Could not sign in. Please try again.",
            );
          } finally {
            setBusy(false);
          }
        }}
      >
        <span className="jh-label">JOBHUNTER</span>
        <h1>{creating ? "Create your workspace" : "Welcome back"}</h1>
        <p>Keep your shortlist, preferences and applications together.</p>
        <label>
          Email
          <input
            name="email"
            type="email"
            autoComplete="email"
            required
            maxLength={254}
          />
        </label>
        <label>
          Password
          <input
            name="password"
            type="password"
            autoComplete={creating ? "new-password" : "current-password"}
            required
            minLength={12}
            maxLength={128}
          />
        </label>
        <small>Use at least 12 characters.</small>
        {error && <p role="alert">{error}</p>}
        <button className="jh-button primary" disabled={busy}>
          {busy ? "Please wait…" : creating ? "Create account" : "Sign in"}
        </button>
        <button
          type="button"
          className="jh-button secondary"
          disabled={busy}
          onClick={() => {
            setCreating(!creating);
            setError("");
          }}
        >
          {creating ? "Already have an account? Sign in" : "Create an account"}
        </button>
      </form>
    </main>
  );
}
