const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
let accessToken = sessionStorage.getItem("smartattend_access_token") || "";

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...(options.headers || {}),
    },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok)
    throw new Error(
      body.detail || "The server could not complete this request.",
    );
  return body;
}

export const api = {
  health: () => request("/health"),
  createSession: () =>
    request("/sessions", {
      method: "POST",
      body: JSON.stringify({
        course_code: "CSC 421",
        course_title: "Artificial Intelligence",
        duration_minutes: 120,
      }),
    }),
  openSessions: () => request("/sessions/open"),
  rotateQr: (sessionId) =>
    request(`/sessions/${sessionId}/qr`, { method: "POST" }),
  closeSession: (sessionId) =>
    request(`/sessions/${sessionId}/close`, { method: "POST" }),
  sessionAttendance: (sessionId) =>
    request(`/sessions/${sessionId}/attendance`),
  enrollStudent: (data) =>
    request("/students", { method: "POST", body: JSON.stringify(data) }),
  checkIn: (data) =>
    request("/attendance/checkin", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  demoLogin: async (role) => {
    const result = await request(`/auth/demo/${role.toLowerCase()}`, {
      method: "POST",
    });
    accessToken = result.access_token;
    sessionStorage.setItem("smartattend_access_token", accessToken);
    sessionStorage.setItem("smartattend_user", JSON.stringify(result.user));
    return result.user;
  },
  login: async (email, password) => {
    const result = await request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    accessToken = result.access_token;
    sessionStorage.setItem("smartattend_access_token", accessToken);
    sessionStorage.setItem("smartattend_refresh_token", result.refresh_token);
    sessionStorage.setItem("smartattend_user", JSON.stringify(result.user));
    return result.user;
  },
  logout: () => {
    accessToken = "";
    [
      "smartattend_access_token",
      "smartattend_refresh_token",
      "smartattend_user",
    ].forEach((key) => sessionStorage.removeItem(key));
  },
};
