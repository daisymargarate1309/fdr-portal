import { useEffect, useState } from "react";
import { api } from "./api.js";

function useLoad(fn, deps) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const reload = () => {
    setError("");
    fn().then(setData).catch((e) => setError(e.message));
  };
  useEffect(() => {
    reload();
  }, deps);
  return { data, error, reload };
}

function Badge({ kind, children }) {
  return <span className={"badge " + String(kind).toLowerCase()}>{children}</span>;
}

function Loading({ error }) {
  if (error) return <div className="msg error">{error}</div>;
  return <p className="empty">Loading...</p>;
}

/* ---------------- Dashboard ---------------- */

export function Dashboard() {
  const { data, error } = useLoad(api.dashboard, []);
  if (!data) return <Loading error={error} />;

  return (
    <>
      <div className="cards">
        {data.cards.map((c) => (
          <div key={c.label} className={"stat " + c.css}>
            <b>{c.count}</b>
            <span>{c.label}</span>
          </div>
        ))}
      </div>

      <div className="card">
        <h2>Alerts: expiring and overdue FDRs</h2>
        {data.attention.length ? (
          <table>
            <thead>
              <tr><th>FDR</th><th>Institution</th><th>Maturity</th><th>Alert</th><th></th></tr>
            </thead>
            <tbody>
              {data.attention.map((f) => (
                <tr key={f.id}>
                  <td>{f.fdr_number}</td>
                  <td>{f.institution_code}</td>
                  <td>{f.maturity_date}</td>
                  <td className="alert">{f.alert}</td>
                  <td><a href={"#/fdrs/" + f.id}>Open</a></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="empty">No FDRs need attention.</p>
        )}
      </div>

      <div className="grid2">
        <div className="card">
          <h2>Pending verification</h2>
          {data.pending_verification.length === 0 && <p className="empty">Nothing pending.</p>}
          {data.pending_verification.map((f) => (
            <p key={f.id}>
              <a href={"#/fdrs/" + f.id}>{f.fdr_number}</a> - {f.institution_code}, {f.bank_name}
            </p>
          ))}
        </div>
        <div className="card">
          <h2>Discrepancies / flagged</h2>
          {data.flagged.length === 0 && <p className="empty">No discrepancies.</p>}
          {data.flagged.map((f) => (
            <p key={f.id}>
              <a href={"#/fdrs/" + f.id}>{f.fdr_number}</a>{" "}
              <span className="alert">
                - {f.issues.length ? f.issues.join(", ") : "flagged by officer"}
              </span>
            </p>
          ))}
        </div>
      </div>

      <div className="card">
        <h2>Pending release requests</h2>
        {data.pending_releases.length === 0 && <p className="empty">No pending requests.</p>}
        {data.pending_releases.map((r) => (
          <p key={r.id}>
            <a href={"#/fdrs/" + r.fdr_id}>{r.fdr_number}</a> - {r.institution_code}: {r.reason}
          </p>
        ))}
      </div>
    </>
  );
}

/* ---------------- FDR list ---------------- */

export function FdrList({ me }) {
  const [q, setQ] = useState("");
  const [st, setSt] = useState("");
  const [applied, setApplied] = useState({ q: "", st: "" });
  const { data, error } = useLoad(() => api.fdrs(applied.q, applied.st), [applied]);

  function search(e) {
    e.preventDefault();
    setApplied({ q, st });
  }

  return (
    <div className="card">
      <h2>FDR / Security Deposit Records</h2>
      <form className="row" onSubmit={search}>
        <input placeholder="Search FDR no, bank, institution" value={q}
          onChange={(e) => setQ(e.target.value)} />
        <select value={st} onChange={(e) => setSt(e.target.value)}>
          <option value="">All states</option>
          {(data ? data.states : []).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <button className="btn">Search</button>
        {me.is_institution && <a className="btn gray" href="#/new">+ Submit FDR</a>}
      </form>
      <br />
      {!data ? (
        <Loading error={error} />
      ) : (
        <table>
          <thead>
            <tr>
              <th>FDR No</th><th>Institution</th><th>Bank</th><th>Amount</th><th>Issued</th>
              <th>Maturity</th><th>State</th><th>Verification</th><th></th>
            </tr>
          </thead>
          <tbody>
            {data.fdrs.map((f) => (
              <tr key={f.id}>
                <td>{f.fdr_number}</td>
                <td>{f.institution_code}</td>
                <td>{f.bank_name}</td>
                <td>{f.amount}</td>
                <td>{f.issue_date}</td>
                <td>{f.maturity_date}</td>
                <td><Badge kind={f.state}>{f.state}</Badge></td>
                <td><Badge kind={f.verification}>{f.verification_label}</Badge></td>
                <td><a href={"#/fdrs/" + f.id}>Open</a></td>
              </tr>
            ))}
            {data.fdrs.length === 0 && (
              <tr><td colSpan="9" className="empty">No records found.</td></tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}

/* ---------------- FDR detail ---------------- */

export function FdrDetail({ id, me, flash }) {
  const { data: f, error, reload } = useLoad(() => api.fdr(id), [id]);
  const [remarks, setRemarks] = useState("");
  const [reason, setReason] = useState("");
  const [decisionRemarks, setDecisionRemarks] = useState("");

  async function act(fn, after) {
    try {
      const res = await fn();
      flash(res.ok === false ? "error" : "success", res.message);
      if (after) after();
      reload();
    } catch (ex) {
      flash("error", ex.message);
    }
  }

  if (!f) return <Loading error={error} />;
  const active = f.status === "ACTIVE";

  return (
    <>
      <div className="card">
        <h2>
          {f.fdr_number} <Badge kind={f.state}>{f.state}</Badge>{" "}
          <Badge kind={f.verification}>{f.verification_label}</Badge>
        </h2>
        {f.alert && <p className="alert">{f.alert}</p>}
        {f.issues.length > 0 && (
          <div className="warn">
            <b>Discrepancies detected automatically:</b>
            <ul>{f.issues.map((i) => <li key={i}>{i}</li>)}</ul>
          </div>
        )}
        <table>
          <tbody>
            <tr><th>Institution</th><td>{f.institution_name} ({f.institution_code})</td></tr>
            <tr><th>Bank</th><td>{f.bank_name}</td></tr>
            <tr><th>Amount</th><td>{f.amount}</td></tr>
            <tr><th>Issue date</th><td>{f.issue_date}</td></tr>
            <tr><th>Maturity date</th><td>{f.maturity_date} ({f.days_left} days)</td></tr>
            <tr>
              <th>Document</th>
              <td>
                {f.document_url
                  ? <a href={f.document_url} target="_blank" rel="noreferrer">View document</a>
                  : <span className="alert">Not uploaded</span>}
              </td>
            </tr>
            <tr><th>Officer remarks</th><td>{f.officer_remarks || "-"}</td></tr>
            {f.renewed_from_id && (
              <tr>
                <th>Renewal of</th>
                <td><a href={"#/fdrs/" + f.renewed_from_id}>{f.renewed_from_number}</a></td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {me.can_verify && active && (
        <div className="card">
          <h2>Scrutiny (Scrutiny Officer)</h2>
          <div className="row">
            <input placeholder="Remarks (optional)" size="40" value={remarks}
              onChange={(e) => setRemarks(e.target.value)} />
            <button className="btn green"
              onClick={() => act(() => api.verify(id, "verify", remarks), () => setRemarks(""))}>
              Mark confirmed by bank
            </button>
            <button className="btn red"
              onClick={() => act(() => api.verify(id, "flag", remarks), () => setRemarks(""))}>
              Flag for scrutiny
            </button>
          </div>
          <p>
            <button className="btn" onClick={() => act(() => api.bankVerify(id))}>
              Verify with bank (mock API)
            </button>
          </p>
        </div>
      )}

      {me.is_institution && active && (
        <div className="grid2">
          <div className="card">
            <h2>Renewal / replacement</h2>
            <p className="empty">
              Submit a renewed or replacement FDR. The old one is marked Renewed and history is kept.
            </p>
            <a className="btn" href={"#/renew/" + id}>Renew / replace this FDR</a>
          </div>
          <div className="card">
            <h2>Request release / refund</h2>
            <p>
              <textarea rows="3" style={{ width: "100%" }} placeholder="Reason for release"
                value={reason} onChange={(e) => setReason(e.target.value)} />
            </p>
            <button className="btn"
              onClick={() => act(() => api.requestRelease(id, reason), () => setReason(""))}>
              Submit request
            </button>
          </div>
        </div>
      )}

      <div className="card">
        <h2>Release / refund requests</h2>
        {f.requests.length === 0 && <p className="empty">No release requests.</p>}
        {f.requests.map((r) => (
          <div key={r.id}>
            <p>
              <Badge kind={r.status}>{r.status_label}</Badge> {r.reason}{" "}
              <span className="empty">- {r.requested_by}, {r.requested_at}</span>
            </p>
            {r.status === "PENDING" && me.can_approve && (
              <div className="row">
                <input placeholder="Remarks" size="40" value={decisionRemarks}
                  onChange={(e) => setDecisionRemarks(e.target.value)} />
                <button className="btn green"
                  onClick={() => act(() => api.decide(r.id, "approve", decisionRemarks),
                    () => setDecisionRemarks(""))}>
                  Approve release
                </button>
                <button className="btn red"
                  onClick={() => act(() => api.decide(r.id, "reject", decisionRemarks),
                    () => setDecisionRemarks(""))}>
                  Reject
                </button>
              </div>
            )}
            {r.status === "PENDING" && !me.can_approve && me.is_staff && (
              <p className="empty">Waiting for decision by the Approving Authority.</p>
            )}
            {r.remarks && r.status !== "PENDING" && (
              <p className="empty">Officer remarks: {r.remarks}</p>
            )}
          </div>
        ))}
      </div>

      <div className="card">
        <h2>History (audit trail)</h2>
        <table>
          <thead><tr><th>When</th><th>Who</th><th>Action</th><th>Detail</th></tr></thead>
          <tbody>
            {f.history.map((h, i) => (
              <tr key={i}><td>{h.when}</td><td>{h.who}</td><td>{h.action}</td><td>{h.detail}</td></tr>
            ))}
            {f.history.length === 0 && (
              <tr><td colSpan="4" className="empty">No history.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}

/* ---------------- Submit / renew form ---------------- */

function Field({ label, name, errors, defaultValue = "", ...rest }) {
  return (
    <p>
      <label>
        {label}<br />
        <input name={name} defaultValue={defaultValue} {...rest} />
      </label>
      {errors[name] && <span className="alert"> {errors[name].join(" ")}</span>}
    </p>
  );
}

function FormBody({ mode, id, defaults, flash }) {
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setErrors({});
    const formData = new FormData(e.target);
    try {
      const res = mode === "renew"
        ? await api.renewFdr(id, formData)
        : await api.createFdr(formData);
      flash("success", res.message);
      window.location.hash = "#/fdrs/" + res.id;
    } catch (ex) {
      setErrors(ex.data && ex.data.fields ? ex.data.fields : {});
      flash("error", ex.message);
    }
    setBusy(false);
  }

  return (
    <form onSubmit={submit}>
      <Field label="Fdr number" name="fdr_number" errors={errors} required />
      <Field label="Bank name" name="bank_name" errors={errors} required
        defaultValue={defaults.bank_name} />
      <Field label="Amount" name="amount" errors={errors} type="number" step="0.01" required
        defaultValue={defaults.amount} />
      <Field label="Issue date" name="issue_date" errors={errors} type="date" required />
      <Field label="Maturity date" name="maturity_date" errors={errors} type="date" required />
      <p>
        <label>
          Document<br />
          <input name="document" type="file" />
        </label>
        {errors.document && <span className="alert"> {errors.document.join(" ")}</span>}
      </p>
      <button className="btn" disabled={busy}>{busy ? "Saving..." : "Save"}</button>{" "}
      <a className="btn gray" href="#/fdrs">Cancel</a>
    </form>
  );
}

export function FdrForm({ mode, id, flash }) {
  const { data: old, error } = useLoad(
    () => (mode === "renew" ? api.fdr(id) : Promise.resolve({})),
    [mode, id]
  );
  if (!old) return <Loading error={error} />;

  return (
    <div className="card" style={{ maxWidth: 600 }}>
      <h2>{mode === "renew" ? "Renew / replace FDR " + old.fdr_number : "Submit new FDR"}</h2>
      <FormBody mode={mode} id={id} flash={flash}
        defaults={{ bank_name: old.bank_name || "", amount: old.amount || "" }} />
    </div>
  );
}

/* ---------------- Release requests, reports, audit ---------------- */

export function Releases() {
  const { data, error } = useLoad(api.releases, []);
  if (!data) return <Loading error={error} />;

  return (
    <div className="card">
      <h2>All release / refund requests</h2>
      <table>
        <thead>
          <tr><th>FDR</th><th>Institution</th><th>Reason</th><th>Requested</th><th>Status</th><th></th></tr>
        </thead>
        <tbody>
          {data.requests.map((r) => (
            <tr key={r.id}>
              <td>{r.fdr_number}</td>
              <td>{r.institution_code}</td>
              <td>{r.reason}</td>
              <td>{r.requested_at}</td>
              <td><Badge kind={r.status}>{r.status_label}</Badge></td>
              <td><a href={"#/fdrs/" + r.fdr_id}>Open</a></td>
            </tr>
          ))}
          {data.requests.length === 0 && (
            <tr><td colSpan="6" className="empty">No requests.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export function Reports() {
  const { data, error } = useLoad(api.reports, []);
  if (!data) return <Loading error={error} />;

  return (
    <div className="card">
      <h2>Management reports</h2>
      <p className="empty">
        Live reports for officials. Each report downloads as a CSV file that opens in Excel.
      </p>
      <table>
        <thead><tr><th>Report</th><th>Records</th><th></th></tr></thead>
        <tbody>
          {data.reports.map((r) => (
            <tr key={r.key}>
              <td>{r.title}</td>
              <td>{r.count}</td>
              <td>
                <a className="btn" href={"/api/reports/" + r.key + "/download/"}>Download CSV</a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Audit() {
  const { data, error } = useLoad(api.audit, []);
  if (!data) return <Loading error={error} />;

  return (
    <div className="card">
      <h2>Audit trail (latest 200)</h2>
      <table>
        <thead>
          <tr><th>When</th><th>User</th><th>FDR</th><th>Action</th><th>Detail</th></tr>
        </thead>
        <tbody>
          {data.logs.map((l, i) => (
            <tr key={i}>
              <td>{l.when}</td><td>{l.who}</td><td>{l.fdr_number}</td>
              <td>{l.action}</td><td>{l.detail}</td>
            </tr>
          ))}
          {data.logs.length === 0 && <tr><td colSpan="5" className="empty">Empty.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}