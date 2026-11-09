const API = "/api";

// Пока без авторизации: пользователь выбирается в шапке
const USERS = [
  { id: 2, name: "Студент Тестовый" },
  { id: 3, name: "Преподаватель Тестовый" },
  { id: 1, name: "Администратор Кампуса" },
];

const STATUS_LABELS = {
  pending: { text: "Ожидает согласования", cls: "bg-warning text-dark" },
  approved: { text: "Подтверждена", cls: "bg-success" },
  rejected: { text: "Отклонена", cls: "bg-danger" },
  cancelled: { text: "Отменена", cls: "bg-secondary" },
  completed: { text: "Завершена", cls: "bg-secondary" },
};

function currentUserId() {
  return Number(localStorage.getItem("userId")) || 2;
}

async function apiFetch(path, options = {}) {
  const response = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => null);
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

function initUserSwitcher() {
  const select = document.getElementById("user-select");
  if (!select) return;
  select.innerHTML = USERS.map(
    (u) => `<option value="${u.id}">${escapeHtml(u.name)}</option>`
  ).join("");
  select.value = String(currentUserId());
  select.addEventListener("change", () => {
    localStorage.setItem("userId", select.value);
    location.reload();
  });
}

document.addEventListener("DOMContentLoaded", initUserSwitcher);

// Ссылка «Заявки» видна только администратору (id = 1)
document.addEventListener("DOMContentLoaded", () => {
  const nav = document.querySelector(".navbar-nav");
  if (nav && currentUserId() === 1) {
    nav.insertAdjacentHTML(
      "beforeend",
      '<li class="nav-item"><a class="nav-link" href="admin.html">Заявки</a></li>'
    );
  }
});