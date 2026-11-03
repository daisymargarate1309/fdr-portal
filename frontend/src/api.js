function getCookie(name) {
  const match = document.cookie.match(new RegExp("(^|; )" + name + "=([^;]*)"));
  return match ? decodeURIComponent(match[2]) : "";
}

async function request(path, options = {}) {
  const method = options.method || "GET";
  const headers = {};
  if (method !== "GET") headers["X-CSRFToken"] = getCookie("csrftoken");
  let body = options.body;
  if (body && !(body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(body);
  }
  const res = await fetch(path, { method, headers, body, credentials: "same-origin" });
  let data = null;
  try {
    data = await res.json();
  } catch (e) {
    data = null;
  }
  if (!res.ok) {
    const err = new Error((data && data.error) || "Request failed (" + res.status + ")");
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

export const api = {
  session: () => request("/api/session/"),
  login: (username, password) =>
    request("/api/login/", { method: "POST", body: { username, password } }),
  logout: () => request("/api/logout/", { method: "POST" }),
  dashboard: () => request("/api/dashboard/"),
  fdrs: (q, state) =>
    request("/api/fdrs/?q=" + encodeURIComponent(q || "") + "&state=" + encodeURIComponent(state || "")),
  fdr: (id) => request("/api/fdrs/" + id + "/"),
  createFdr: (formData) => request("/api/fdrs/new/", { method: "POST", body: formData }),
  renewFdr: (id, formData) =>
    request("/api/fdrs/" + id + "/renew/", { method: "POST", body: formData }),
  verify: (id, action, remarks) =>
    request("/api/fdrs/" + id + "/verify/", { method: "POST", body: { action, remarks } }),
  bankVerify: (id) => request("/api/fdrs/" + id + "/bank-verify/", { method: "POST" }),
  requestRelease: (id, reason) =>
    request("/api/fdrs/" + id + "/release/", { method: "POST", body: { reason } }),
  releases: () => request("/api/releases/"),
  decide: (id, decision, remarks) =>
    request("/api/releases/" + id + "/decide/", { method: "POST", body: { decision, remarks } }),
  reports: () => request("/api/reports/"),
  audit: () => request("/api/audit/"),
};