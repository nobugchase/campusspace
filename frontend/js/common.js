const API = "/api";

const STATUS_LABELS = {
  pending: { text: "Ожидает согласования", cls: "bg-warning text-dark" },
  approved: { text: "Подтверждена", cls: "bg-success" },
  rejected: { text: "Отклонена", cls: "bg-danger" },
  cancelled: { text: "Отменена", cls: "bg-secondary" },
  completed: { text: "Завершена", cls: "bg-secondary" },
};

function getAuth() {
  try {
    return JSON.parse(localStorage.getItem("auth"));
  } catch {
    return null;
  }
}

function currentUser() {
  const auth = getAuth();
  return auth ? auth.user : null;
}

function currentUserId() {
  const user = currentUser();
  return user ? user.id : null;
}

function logout() {
  localStorage.removeItem("auth");
  location.href = "login.html";
}

// Все страницы, кроме входа, требуют авторизации
if (!getAuth() && !location.pathname.endsWith("login.html")) {
  location.replace("login.html");
}

async function apiFetch(path, options = {}) {
  const auth = getAuth();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (auth) headers.Authorization = `Bearer ${auth.token}`;

  const response = await fetch(API + path, { ...options, headers });
  const data = await response.json().catch(() => null);

  if (response.status === 401 && !path.startsWith("/auth/")) {
    logout();
  }
  if (!response.ok) {
    const detail = data && typeof data.detail === "string" ? data.detail : "Ошибка запроса";
    throw new Error(detail);
  }
  return data;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

function formatDateTime(iso) {
  const d = new Date(iso);
  return d.toLocaleString("ru-RU", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function formatTimeRange(startIso, endIso) {
  return `${startIso.slice(11, 16)}–${endIso.slice(11, 16)}`;
}

function initUserMenu() {
  const user = currentUser();
  const select = document.getElementById("user-select");
  if (select) {
    const menu = document.createElement("div");
    menu.className = "d-flex align-items-center gap-2 text-white";
    menu.innerHTML = user
      ? `<span class="small">${escapeHtml(user.full_name)}</span>
         <button type="button" id="logout-btn" class="btn btn-sm btn-outline-light">Выйти</button>`
      : "";
    select.replaceWith(menu);
    const logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) logoutBtn.addEventListener("click", logout);
  }
  // Ссылка «Заявки» только для администратора
  const nav = document.querySelector(".navbar-nav");
  if (nav && user && user.role === "admin") {
    nav.insertAdjacentHTML(
      "beforeend",
      '<li class="nav-item"><a class="nav-link" href="admin.html">Заявки</a></li>'
    );
  }
}

document.addEventListener("DOMContentLoaded", initUserMenu);