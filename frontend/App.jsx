import { useEffect, useState } from "react";
import { api } from "./api.js";
import {
  Audit, Dashboard, FdrDetail, FdrForm, FdrList, Releases, Reports,
} from "./pages.jsx";

function useRoute() {
  const [hash, setHash] = useState(window.location.hash || "#/");
  useEffect(() => {
    const onChange = () => setHash(window.location.hash || "#/");
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return hash.replace(/^#/, "") || "/";
}

function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    setError("");
    try {
      onLogin(await api.login(username, password));
    } catch (ex) {
      setError(ex.message);
    }
  }

  return (
    <div className="card" style={{ maxWidth: 400, margin: "40px auto" }}>
      <h2>Login</h2>
      {error && <div className="msg error">{error}</div>}
      <form onSubmit={submit}>
        <p>
          <input placeholder="Username" value={username} autoFocus style={{ width: "100%" }}
            onChange={(e) => setUsername(e.target.value)} />
        </p>
        <p>
          <input placeholder="Password" type="password" value={password} style={{ width: "100%" }}
            onChange={(e) => setPassword(e.target.value)} />
        </p>
        <button className="btn">Login</button>
      </form>
      <p className="empty">
        Demo: scrutiny / scrutiny123 | approver / approver123 | officer / officer123 | inst1 / inst123
      </p>
    </div>
  );
}

function Page({ path, me, flash }) {
  let m;
  if (path === "/") return <Dashboard />;
  if (path === "/fdrs") return <FdrList me={me} />;
  if (path === "/new") return <FdrForm mode="new" flash={flash} />;
  if ((m = path.match(/^\/fdrs\/(\d+)$/))) {
    return <FdrDetail key={m[1]} id={m[1]} me={me} flash={flash} />;
  }
  if ((m = path.match(/^\/renew\/(\d+)$/))) {
    return <FdrForm key={m[1]} mode="renew" id={m[1]} flash={flash} />;
  }
  if (path === "/releases") return <Releases />;
  if (path === "/reports") return <Reports />;
  if (path === "/audit") return <Audit />;
  return <p className="empty">Page not found.</p>;
}

export default function App() {
  const [me, setMe] = useState(null);
  const [msg, setMsg] = useState(null);
  const path = useRoute();

  useEffect(() => {
    api.session().then(setMe).catch(() => setMe({ authenticated: false }));
  }, []);

  // A message set just before navigating survives one route change, then disappears.
  useEffect(() => {
    setMsg((m) => (m && m.fresh ? { ...m, fresh: false } : null));
  }, [path]);

  const flash = (type, text) => {
    setMsg({ type, text, fresh: true });
    window.scrollTo(0, 0);
  };

  async function logout() {
    await api.logout();
    setMsg(null);
    window.location.hash = "#/";
    setMe(await api.session().catch(() => ({ authenticated: false })));
  }

  if (me === null) return <p style={{ padding: 24 }}>Loading...</p>;

  return (
    <>
      <header>
        <h1>AICTE Security Deposit / FDR Portal</h1>
        {me.authenticated && (
          <>
            <a href="#/">Dashboard</a>
            <a href="#/fdrs">FDR Records</a>
            {me.is_institution && <a href="#/new">Submit FDR</a>}
            {me.is_staff && <a href="#/releases">Release Requests</a>}
            {me.is_staff && <a href="#/reports">Reports</a>}
            {me.is_staff && <a href="#/audit">Audit Trail</a>}
            {me.is_superuser && <a href="http://127.0.0.1:8000/admin/">Admin</a>}
            <span style={{ fontSize: 13 }}>{me.username}</span>
            <span className="role">{me.role}</span>
            <button onClick={logout}>Logout</button>
          </>
        )}
      </header>
      <main>
        {msg && <div className={"msg " + msg.type}>{msg.text}</div>}
        {me.authenticated ? (
          <Page path={path} me={me} flash={flash} />
        ) : (
          <Login onLogin={setMe} />
        )}
      </main>
    </>
  );
}