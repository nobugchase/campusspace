const pendingList = document.getElementById("pending-list");
const adminMessage = document.getElementById("admin-message");

function showAdminMessage(text, type) {
  adminMessage.className = `alert alert-${type}`;
  adminMessage.textContent = text;
}

function renderPending(booking) {
  return `
    <div class="col-12 col-md-6 col-lg-4">
      <div class="card h-100">
        <div class="card-body">
          <h2 class="h6">${escapeHtml(booking.room.name)}</h2>
          <p class="mb-1">${formatDateTime(booking.starts_at)} — ${booking.ends_at.slice(11, 16)}</p>
          <p class="mb-1 small">Заявитель: ${escapeHtml(booking.user.full_name)} (${escapeHtml(booking.user.email)})</p>
          <p class="mb-1 small text-muted">Цель: ${escapeHtml(booking.purpose || "не указана")}</p>
          <p class="small text-muted">Человек: ${booking.attendees ?? "—"}</p>
          <label class="form-label small" for="comment-${booking.id}">Комментарий</label>
          <input id="comment-${booking.id}" type="text" class="form-control form-control-sm mb-2" maxlength="200">
          <div class="d-flex gap-2">
            <button class="btn btn-success btn-sm decision-btn" data-id="${booking.id}" data-decision="approved">Одобрить</button>
            <button class="btn btn-outline-danger btn-sm decision-btn" data-id="${booking.id}" data-decision="rejected">Отклонить</button>
          </div>
        </div>
      </div>
    </div>`;
}

async function loadPending() {
  try {
    const list = await apiFetch(`/admin/bookings?admin_id=${currentUserId()}&status=pending`);
    pendingList.innerHTML = list.length
      ? list.map(renderPending).join("")
      : '<p class="text-muted">Заявок, ожидающих согласования, нет.</p>';
  } catch (error) {
    showAdminMessage(error.message + ". Выберите в шапке «Администратор Кампуса».", "danger");
  }
}

pendingList.addEventListener("click", async (e) => {
  const btn = e.target.closest(".decision-btn");
  if (!btn) return;
  const id = btn.dataset.id;
  try {
    await apiFetch(`/bookings/${id}/decision`, {
      method: "POST",
      body: JSON.stringify({
        admin_id: currentUserId(),
        decision: btn.dataset.decision,
        comment: document.getElementById(`comment-${id}`).value.trim() || null,
      }),
    });
    showAdminMessage("Решение сохранено, пользователь получил уведомление.", "success");
    await loadPending();
  } catch (error) {
    showAdminMessage(error.message, "danger");
  }
});

loadPending();