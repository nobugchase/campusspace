const roomId = new URLSearchParams(location.search).get("id");
const dateInput = document.getElementById("booking-date");
const slotGrid = document.getElementById("slot-grid");
const bookingForm = document.getElementById("booking-form");
const bookingError = document.getElementById("booking-error");

let room = null;
let slots = [];
let selStart = null;
let selEnd = null;

function showRoomError(message) {
  const box = document.getElementById("room-error");
  box.textContent = message;
  box.classList.remove("d-none");
}

function renderRoomInfo() {
  const photo = room.photos.length ? room.photos[0].url : "https://picsum.photos/seed/none/800/500";
  const equipment = room.equipment
    .map((re) => `<li>${escapeHtml(re.equipment.name)}${re.quantity > 1 ? ` — ${re.quantity} шт.` : ""}</li>`)
    .join("");
  const access = room.access_rules
    .map((a) => `<li><strong>${escapeHtml(a.title)}:</strong> ${escapeHtml(a.description)}</li>`)
    .join("");
  const approval = room.requires_approval
    ? '<div class="alert alert-warning py-2">Для этого помещения нужно согласование администратора.</div>'
    : '<div class="alert alert-success py-2">Бронь подтверждается автоматически.</div>';

  document.getElementById("room-info").innerHTML = `
    <div class="card">
      <img src="${escapeHtml(photo)}" class="card-img-top room-main-photo" alt="Фото: ${escapeHtml(room.name)}">
      <div class="card-body">
        <h1 class="h4">${escapeHtml(room.name)}</h1>
        <p class="text-muted">${escapeHtml(room.building.name)}, ${escapeHtml(room.building.address)}<br>
          ${escapeHtml(room.room_type.name)} · этаж ${room.floor ?? "—"} · вместимость ${room.capacity} чел.<br>
          Часы работы: ${room.open_time.slice(0, 5)}–${room.close_time.slice(0, 5)}</p>
        <p>${escapeHtml(room.description)}</p>
        ${approval}
        <h2 class="h6">Оснащение</h2>
        <ul>${equipment || "<li>Нет данных</li>"}</ul>
        <h2 class="h6">Условия доступа</h2>
        <ul>${access || "<li>Без ограничений</li>"}</ul>
      </div>
    </div>`;
  document.title = `CampusSpace — ${room.name}`;
  document.getElementById("booking-attendees").max = room.capacity;
}

function renderSlots() {
  slotGrid.innerHTML = slots
    .map((slot, i) => {
      const selected = selStart !== null && i >= Math.min(selStart, selEnd) && i <= Math.max(selStart, selEnd);
      let cls = "btn-outline-success";
      let disabled = "";
      if (slot.status === "busy") { cls = "btn-danger"; disabled = "disabled"; }
      else if (slot.status === "pending") { cls = "btn-warning"; disabled = "disabled"; }
      else if (slot.status === "past") { cls = "btn-secondary"; disabled = "disabled"; }
      else if (selected) { cls = "btn-success"; }
      return `<button type="button" class="btn btn-sm slot-btn ${cls}" data-index="${i}" ${disabled}>${slot.start.slice(11, 16)}</button>`;
    })
    .join("");
}

function updateSummary() {
  if (selStart === null) {
    bookingForm.classList.add("d-none");
    return;
  }
  const a = Math.min(selStart, selEnd);
  const b = Math.max(selStart, selEnd);
  document.getElementById("selection-summary").textContent =
    `${dateInput.value}, ${formatTimeRange(slots[a].start, slots[b].end)}`;
  bookingForm.classList.remove("d-none");
}

function onSlotClick(index) {
  if (selStart === null || selStart !== selEnd) {
    selStart = selEnd = index;
  } else {
    const a = Math.min(selStart, index);
    const b = Math.max(selStart, index);
    const allFree = slots.slice(a, b + 1).every((s) => s.status === "free");
    if (allFree) { selStart = a; selEnd = b; } else { selStart = selEnd = index; }
  }
  renderSlots();
  updateSummary();
}

async function loadSlots() {
  selStart = selEnd = null;
  bookingError.classList.add("d-none");
  updateSummary();
  slotGrid.innerHTML = '<span class="text-muted">Загрузка...</span>';
  try {
    slots = await apiFetch(`/rooms/${roomId}/slots?date=${dateInput.value}`);
    renderSlots();
  } catch (error) {
    slotGrid.innerHTML = `<span class="text-danger">${escapeHtml(error.message)}</span>`;
  }
}

slotGrid.addEventListener("click", (e) => {
  const btn = e.target.closest(".slot-btn");
  if (btn && !btn.disabled) onSlotClick(Number(btn.dataset.index));
});

dateInput.addEventListener("change", loadSlots);

bookingForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  bookingError.classList.add("d-none");
  const a = Math.min(selStart, selEnd);
  const b = Math.max(selStart, selEnd);
  const payload = {
    user_id: currentUserId(),
    room_id: Number(roomId),
    starts_at: slots[a].start,
    ends_at: slots[b].end,
    purpose: document.getElementById("booking-purpose").value.trim(),
    attendees: Number(document.getElementById("booking-attendees").value),
  };
    if (document.getElementById("repeat-toggle").checked) {
    await createRecurring(a, b);
    return;
  }
  try {
    const booking = await apiFetch("/bookings", { method: "POST", body: JSON.stringify(payload) });
    const statusInfo = STATUS_LABELS[booking.status];
    document.getElementById("confirm-body").innerHTML = `
      <p class="mb-1"><strong>${escapeHtml(booking.room.name)}</strong></p>
      <p class="mb-1">${formatDateTime(booking.starts_at)} — ${booking.ends_at.slice(11, 16)}</p>
      <p>Статус: <span class="badge ${statusInfo.cls}">${statusInfo.text}</span></p>`;
    new bootstrap.Modal(document.getElementById("confirm-modal")).show();
    bookingForm.reset();
    await loadSlots();
  } catch (error) {
    bookingError.textContent = error.message;
    bookingError.classList.remove("d-none");
  }
});

async function init() {
  if (!roomId) { showRoomError("Не указано помещение."); return; }
  const today = new Date().toLocaleDateString("sv-SE"); // формат ГГГГ-ММ-ДД
  dateInput.min = today;
  dateInput.value = today;
  try {
    room = await apiFetch(`/rooms/${roomId}`);
    renderRoomInfo();
    await loadSlots();
    await loadReviews();
  } catch (error) {
    showRoomError(error.message);
  }
}

const scoreSelects = document.querySelectorAll(".score-select");
scoreSelects.forEach((select) => {
  select.innerHTML = [5, 4, 3, 2, 1].map((n) => `<option value="${n}">${n}</option>`).join("");
});

async function loadReviews() {
  const data = await apiFetch(`/rooms/${roomId}/reviews`);
  const s = data.summary;
  document.getElementById("rating-summary").textContent = s.count
    ? `★ ${s.average} (отзывов: ${s.count}) · чистота ${s.cleanliness}, оснащение ${s.equipment}, комфорт ${s.comfort}`
    : "пока нет оценок";
  document.getElementById("reviews-list").innerHTML = data.items.length
    ? data.items
        .map(
          (r) => `<div class="list-group-item">
            <div class="d-flex justify-content-between">
              <strong>${escapeHtml(r.user.full_name)}</strong>
              <span class="text-muted small">${formatDateTime(r.created_at)}</span>
            </div>
            <div class="small">Чистота ${r.cleanliness} · Оснащение ${r.equipment_score} · Комфорт ${r.comfort}</div>
            ${r.comment ? `<div>${escapeHtml(r.comment)}</div>` : ""}
          </div>`
        )
        .join("")
    : '<div class="list-group-item text-muted">Отзывов пока нет.</div>';
}

document.getElementById("review-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const box = document.getElementById("review-message");
  try {
    await apiFetch("/reviews", {
      method: "POST",
      body: JSON.stringify({
        user_id: currentUserId(),
        room_id: Number(roomId),
        cleanliness: Number(document.getElementById("score-cleanliness").value),
        equipment_score: Number(document.getElementById("score-equipment").value),
        comfort: Number(document.getElementById("score-comfort").value),
        comment: document.getElementById("review-comment").value.trim() || null,
      }),
    });
    box.className = "alert alert-success";
    box.textContent = "Спасибо, отзыв добавлен.";
    document.getElementById("review-comment").value = "";
    await loadReviews();
  } catch (error) {
    box.className = "alert alert-danger";
    box.textContent = error.message;
  }
});
const WEEKDAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];
const repeatToggle = document.getElementById("repeat-toggle");
const repeatFrequency = document.getElementById("repeat-frequency");
const repeatWeekdays = document.getElementById("repeat-weekdays");

repeatWeekdays.innerHTML = WEEKDAY_NAMES.map(
  (name, i) => `
    <div class="form-check">
      <input class="form-check-input weekday-check" type="checkbox" value="${i + 1}" id="wd-${i + 1}">
      <label class="form-check-label" for="wd-${i + 1}">${name}</label>
    </div>`
).join("");

function syncRepeat() {
  const on = repeatToggle.checked;
  document.getElementById("repeat-options").classList.toggle("d-none", !on);
  repeatWeekdays.classList.toggle("d-none", repeatFrequency.value === "daily");
  if (on && !document.querySelector(".weekday-check:checked")) {
    const js = new Date(dateInput.value + "T00:00:00").getDay(); // 0 = воскресенье
    document.getElementById(`wd-${js === 0 ? 7 : js}`).checked = true;
  }
}
repeatToggle.addEventListener("change", syncRepeat);
repeatFrequency.addEventListener("change", syncRepeat);

async function createRecurring(a, b) {
  const until = document.getElementById("repeat-until").value;
  if (!until) {
    bookingError.textContent = "Укажите дату, до которой повторять бронь";
    bookingError.classList.remove("d-none");
    return;
  }
  const payload = {
    user_id: currentUserId(),
    room_id: Number(roomId),
    frequency: repeatFrequency.value,
    weekdays: [...document.querySelectorAll(".weekday-check:checked")].map((c) => Number(c.value)),
    start_time: slots[a].start.slice(11, 19),
    end_time: slots[b].end.slice(11, 19),
    start_date: dateInput.value,
    end_date: until,
    purpose: document.getElementById("booking-purpose").value.trim(),
    attendees: Number(document.getElementById("booking-attendees").value),
  };
  try {
    const result = await apiFetch("/recurring", { method: "POST", body: JSON.stringify(payload) });
    const skipped = result.skipped.length
      ? `<p class="small text-muted mb-0">Пропущено: ${result.skipped.map(escapeHtml).join("; ")}</p>`
      : "";
    document.getElementById("confirm-body").innerHTML = `
      <p class="mb-1"><strong>${escapeHtml(result.rule.room.name)}</strong></p>
      <p class="mb-1">Создано броней в серии: ${result.created}</p>
      ${skipped}`;
    new bootstrap.Modal(document.getElementById("confirm-modal")).show();
    bookingForm.reset();
    syncRepeat();
    await loadSlots();
  } catch (error) {
    bookingError.textContent = error.message;
    bookingError.classList.remove("d-none");
  }
}
init();