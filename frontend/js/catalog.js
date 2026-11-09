let ratingsMap = {};
const roomsList = document.getElementById("rooms-list");
const roomsMessage = document.getElementById("rooms-message");

async function loadFilters() {
  const [types, buildings, equipment] = await Promise.all([
    apiFetch("/room-types"),
    apiFetch("/buildings"),
    apiFetch("/equipment"),
  ]);
  document.getElementById("filter-type").innerHTML +=
    types.map((t) => `<option value="${t.id}">${escapeHtml(t.name)}</option>`).join("");
  document.getElementById("filter-building").innerHTML +=
    buildings.map((b) => `<option value="${b.id}">${escapeHtml(b.name)}</option>`).join("");
  document.getElementById("filter-equipment").innerHTML = equipment
    .map(
      (e) => `
      <div class="form-check">
        <input class="form-check-input equipment-check" type="checkbox" value="${e.id}" id="eq-${e.id}">
        <label class="form-check-label" for="eq-${e.id}">${escapeHtml(e.name)}</label>
      </div>`
    )
    .join("");
}

function buildQuery() {
  const params = new URLSearchParams();
  const search = document.getElementById("filter-search").value.trim();
  const capacity = document.getElementById("filter-capacity").value;
  const type = document.getElementById("filter-type").value;
  const building = document.getElementById("filter-building").value;
  if (search) params.append("search", search);
  if (capacity) params.append("capacity_min", capacity);
  if (type) params.append("room_type_id", type);
  if (building) params.append("building_id", building);
  document.querySelectorAll(".equipment-check:checked").forEach((c) => params.append("equipment", c.value));
  return params.toString();
}

function renderRoom(room) {
  const photo = room.photos.length ? room.photos[0].url : "https://picsum.photos/seed/none/800/500";
  const badges = room.equipment
    .map((re) => `<span class="badge text-bg-light border">${escapeHtml(re.equipment.name)}</span>`)
    .join(" ");
  const approval = room.requires_approval
    ? '<span class="badge bg-warning text-dark">Нужно согласование</span>'
    : '<span class="badge bg-success">Мгновенная бронь</span>';
  const rating = ratingsMap[room.id];
  const ratingText = rating
    ? `<span class="badge text-bg-warning">★ ${rating.average} (${rating.count})</span>`
    : '<span class="text-muted small">Нет оценок</span>';  
  return `
    <div class="col-12 col-md-6 col-lg-4">
      <div class="card room-card h-100">
        <img src="${escapeHtml(photo)}" class="card-img-top room-card-photo" alt="Фото: ${escapeHtml(room.name)}">
        <div class="card-body d-flex flex-column">
          <h2 class="h5 card-title">${escapeHtml(room.name)}</h2>
          <p class="text-muted small mb-2">
            ${escapeHtml(room.building.name)} · ${escapeHtml(room.room_type.name)} · до ${room.capacity} чел.
          </p>
          <div class="mb-2">${approval} ${ratingText}</div>
          <div class="d-flex flex-wrap gap-1 mb-3">${badges}</div>
          <a href="room.html?id=${room.id}" class="btn btn-primary mt-auto">Календарь и бронирование</a>
        </div>
      </div>
    </div>`;
}

async function loadRooms() {
  roomsMessage.textContent = "Загрузка...";
  try {
    const query = buildQuery();
    const [rooms, ratings] = await Promise.all([
      apiFetch("/rooms" + (query ? "?" + query : "")),
      apiFetch("/ratings"),
    ]);
    ratingsMap = Object.fromEntries(ratings.map((r) => [r.room_id, r]));
    roomsList.innerHTML = rooms.map(renderRoom).join("");
    roomsMessage.textContent = rooms.length ? `Найдено помещений: ${rooms.length}` : "Ничего не найдено. Измените фильтры.";
  } catch (error) {
    roomsMessage.textContent = "Не удалось загрузить помещения: " + error.message;
  }
}

document.getElementById("filter-form").addEventListener("submit", (e) => {
  e.preventDefault();
  loadRooms();
});
document.getElementById("filter-form").addEventListener("reset", () => {
  setTimeout(loadRooms, 0);
});

loadFilters().then(loadRooms).catch((e) => {
  roomsMessage.textContent = "Ошибка загрузки: " + e.message;
});