const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
let accessToken = sessionStorage.getItem("smartattend_access_token") || "";
let refreshInFlight = null;

function saveSession(result) {
  accessToken = result.access_token;
  sessionStorage.setItem("smartattend_access_token", accessToken);
  sessionStorage.setItem("smartattend_refresh_token", result.refresh_token);
  sessionStorage.setItem("smartattend_user", JSON.stringify(result.user));
  return result.user;
}

async function refreshAccessToken() {
  const refreshToken = sessionStorage.getItem("smartattend_refresh_token");
  if (!refreshToken) throw new Error("Your session has expired. Please sign in again.");
  if (!refreshInFlight) {
    refreshInFlight = fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
      .then(async (response) => {
        const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(body.detail || "Your session has expired. Please sign in again.");
        saveSession(body);
      })
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

async function request(path, options = {}) {
  const { retry = false, ...fetchOptions } = options;
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...fetchOptions,
      headers: {
        "Content-Type": "application/json",
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...(fetchOptions.headers || {}),
      },
    });
  } catch {
    throw new Error(`Cannot reach the attendance API at ${API_URL}. Check the Vercel VITE_API_URL setting and the Render CORS origin.`);
  }
  const body = await response.json().catch(() => ({}));
  if (response.status === 401 && !retry && path !== "/auth/login" && path !== "/auth/refresh") {
    try {
      await refreshAccessToken();
      return request(path, { ...fetchOptions, retry: true });
    } catch (error) {
      accessToken = "";
      ["smartattend_access_token", "smartattend_refresh_token", "smartattend_user"].forEach((key) => sessionStorage.removeItem(key));
      throw error;
    }
  }
  if (!response.ok)
    throw new Error(
      body.detail || "The server could not complete this request.",
    );
  return body;
}

export const api = {
  health: () => request("/health"),
  createSession: (data = {}) =>
    request("/sessions", {
      method: "POST",
      body: JSON.stringify({
        course_code: "CSC 421",
        course_title: "Artificial Intelligence",
        duration_minutes: 120,
        ...data,
      }),
    }),
  plannedSessions: () => request("/sessions/planned"),
  openSessions: () => request("/sessions/open"),
  currentSession: () => request("/sessions/current"),
  rotateQr: (sessionId) =>
    request(`/sessions/${sessionId}/qr`, { method: "POST" }),
  closeSession: (sessionId) =>
    request(`/sessions/${sessionId}/close`, { method: "POST" }),
  sessionAttendance: (sessionId) =>
    request(`/sessions/${sessionId}/attendance`),
  listCourses: () => request("/courses"),
  courseEnrollments: (courseId) => request(`/courses/${courseId}/enrollments`),
  addCourseEnrollment: (courseId, matricNo) =>
    request(`/courses/${courseId}/enrollments`, {
      method: "POST",
      body: JSON.stringify({ matric_no: matricNo }),
    }),
  removeCourseEnrollment: (courseId, studentId) =>
    request(`/courses/${courseId}/enrollments/${studentId}`, { method: "DELETE" }),
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
    return saveSession(result);
  },
  login: async (email, password) => {
    const result = await request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    return saveSession(result);
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
