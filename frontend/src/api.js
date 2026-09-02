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
  currentSession: () => request("/sessions/current"),
  rotateQr: (sessionId) =>
    request(`/sessions/${sessionId}/qr`, { method: "POST" }),
  closeSession: (sessionId) =>
    request(`/sessions/${sessionId}/close`, { method: "POST" }),
  sessionAttendance: (sessionId) =>
    request(`/sessions/${sessionId}/attendance`),
  listCourses: () => request("/courses"),
  listStudents: () => request("/students"),
  myAttendance: () => request("/students/me/attendance"),
  roster: () => request("/roster"),
  adminOverview: () => request("/admin/overview"),
  listSchedule: () => request("/schedule"),
  addSchedule: (data) =>
    request("/schedule", { method: "POST", body: JSON.stringify(data) }),
  deleteSchedule: (scheduleId) =>
    request(`/schedule/${scheduleId}`, { method: "DELETE" }),
  enrollStudent: (data) =>
    request("/students", { method: "POST", body: JSON.stringify(data) }),
  register: (data) =>
    request("/auth/register", { method: "POST", body: JSON.stringify(data) }),
  registerStudent: (data) =>
    request("/auth/register-student", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  pendingStudents: () => request("/students/pending"),
  approveStudent: (id) =>
    request(`/students/pending/${id}/approve`, { method: "POST" }),
  rejectStudent: (id, reason) =>
    request(`/students/pending/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason: reason || null }),
    }),
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
  logout: async () => {
    const refreshToken = sessionStorage.getItem("smartattend_refresh_token");
    if (refreshToken) {
      await request("/auth/logout", {
        method: "POST",
        body: JSON.stringify({ refresh_token: refreshToken }),
      }).catch(() => {});
    }
    accessToken = "";
    [
      "smartattend_access_token",
      "smartattend_refresh_token",
      "smartattend_user",
    ].forEach((key) => sessionStorage.removeItem(key));
  },
};
