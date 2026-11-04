const activeList = document.getElementById("active-list");
const historyList = document.getElementById("history-list");
const cabinetMessage = document.getElementById("cabinet-message");

function showMessage(text, type) {
  cabinetMessage.className = `alert alert-${type}`;
  cabinetMessage.textContent = text;
}

function renderBooking(booking, canCancel) {
  const statusInfo = STATUS_LABELS[booking.status] || { text: booking.status, cls: "bg-secondary" };
  const cancelBtn = canCancel
    ? `<button class="btn btn-sm btn-outline-danger cancel-btn" data-id="${booking.id}">Отменить</button>`
    : "";
  return `
    <div class="col-12 col-md-6 col-lg-4">
      <div class="card h-100">
        <div class="card-body">
          <h3 class="h6">${escapeHtml(booking.room.name)}</h3>
          <p class="mb-1">${formatDateTime(booking.starts_at)} — ${booking.ends_at.slice(11, 16)}</p>
          <p class="mb-1 text-muted small">${escapeHtml(booking.purpose || "Без описания")}</p>
          <span class="badge ${statusInfo.cls} mb-2">${statusInfo.text}</span>
          <div>${cancelBtn}</div>
        </div>
      </div>
    </div>`;
}

async function loadBookings() {
  try {
    const bookings = await apiFetch(`/bookings/my?user_id=${currentUserId()}`);
    const now = new Date();
    const active = bookings.filter(
      (b) => ["pending", "approved"].includes(b.status) && new Date(b.ends_at) > now
    );
    const history = bookings.filter((b) => !active.includes(b));
    activeList.innerHTML = active.length
      ? active.map((b) => renderBooking(b, true)).join("")
      : '<p class="text-muted">Активных бронирований нет. <a href="index.html">Найти помещение</a></p>';
    historyList.innerHTML = history.length
      ? history.map((b) => renderBooking(b, false)).join("")
      : '<p class="text-muted">История пуста.</p>';
  } catch (error) {
    showMessage("Не удалось загрузить бронирования: " + error.message, "danger");
  }
}

activeList.addEventListener("click", async (e) => {
  const btn = e.target.closest(".cancel-btn");
  if (!btn) return;
  if (!confirm("Отменить бронирование?")) return;
  try {
    await apiFetch(`/bookings/${btn.dataset.id}?user_id=${currentUserId()}`, { method: "DELETE" });
    showMessage("Бронирование отменено.", "success");
    await loadBookings();
  } catch (error) {
    showMessage(error.message, "danger");
  }
});

loadBookings();