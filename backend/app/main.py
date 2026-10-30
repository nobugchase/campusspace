from datetime import date, datetime, timedelta
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas
from .database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CampusSpace API",
    description="Система бронирования учебных пространств",
    version="0.1.0",
)

# Разрешаем фронтенду (другой порт/файл) обращаться к API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/rooms", response_model=list[schemas.RoomOut], tags=["Помещения"])
def list_rooms(
    capacity_min: int | None = Query(None, description="Минимальная вместимость"),
    equipment: list[int] = Query([], description="ID оснащения (помещение должно иметь всё перечисленное)"),
    room_type_id: int | None = None,
    building_id: int | None = None,
    search: str | None = Query(None, description="Поиск по названию"),
    db: Session = Depends(get_db),
):
    query = select(models.Room).where(models.Room.is_active.is_(True))
    if capacity_min:
        query = query.where(models.Room.capacity >= capacity_min)
    for eq_id in equipment:
        query = query.where(
            models.Room.equipment.any(models.RoomEquipment.equipment_id == eq_id)
        )
    if room_type_id:
        query = query.where(models.Room.room_type_id == room_type_id)
    if building_id:
        query = query.where(models.Room.building_id == building_id)
    if search:
        query = query.where(models.Room.name.ilike(f"%{search}%"))
    return db.scalars(query.order_by(models.Room.name)).all()


@app.get("/api/rooms/{room_id}", response_model=schemas.RoomOut, tags=["Помещения"])
def get_room(room_id: int, db: Session = Depends(get_db)):
    room = db.get(models.Room, room_id)
    if room is None or not room.is_active:
        raise HTTPException(status_code=404, detail="Помещение не найдено")
    return room


@app.get("/api/equipment", response_model=list[schemas.EquipmentOut], tags=["Справочники"])
def list_equipment(db: Session = Depends(get_db)):
    return db.scalars(select(models.Equipment).order_by(models.Equipment.name)).all()


@app.get("/api/room-types", response_model=list[schemas.RoomTypeOut], tags=["Справочники"])
def list_room_types(db: Session = Depends(get_db)):
    return db.scalars(select(models.RoomType).order_by(models.RoomType.name)).all()


@app.get("/api/buildings", response_model=list[schemas.BuildingOut], tags=["Справочники"])
def list_buildings(db: Session = Depends(get_db)):
    return db.scalars(select(models.Building).order_by(models.Building.name)).all()

ACTIVE_STATUSES = ("pending", "approved")


@app.get("/api/rooms/{room_id}/slots", response_model=list[schemas.SlotOut], tags=["Бронирование"])
def room_slots(room_id: int, day: date = Query(..., alias="date", description="Дата в формате ГГГГ-ММ-ДД"),
               db: Session = Depends(get_db)):
    """Сетка слотов по 30 минут на выбранный день."""
    room = db.get(models.Room, room_id)
    if room is None or not room.is_active:
        raise HTTPException(status_code=404, detail="Помещение не найдено")

    day_start = datetime.combine(day, room.open_time)
    day_end = datetime.combine(day, room.close_time)
    bookings = db.scalars(
        select(models.Booking).where(
            models.Booking.room_id == room_id,
            models.Booking.status.in_(ACTIVE_STATUSES),
            models.Booking.starts_at < day_end,
            models.Booking.ends_at > day_start,
        )
    ).all()

    now = datetime.now()
    slots = []
    cur = day_start
    while cur < day_end:
        nxt = cur + timedelta(minutes=30)
        status = "free"
        if cur < now:
            status = "past"
        else:
            for b in bookings:
                if b.starts_at < nxt and b.ends_at > cur:
                    status = "busy" if b.status == "approved" else "pending"
                    break
        slots.append(schemas.SlotOut(start=cur, end=nxt, status=status))
        cur = nxt
    return slots


@app.post("/api/bookings", response_model=schemas.BookingOut, status_code=201, tags=["Бронирование"])
def create_booking(data: schemas.BookingCreate, db: Session = Depends(get_db)):
    room = db.get(models.Room, data.room_id)
    if room is None or not room.is_active:
        raise HTTPException(status_code=404, detail="Помещение не найдено")
    if db.get(models.User, data.user_id) is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Время без часового пояса, например 2026-11-02T10:00:00
    starts = data.starts_at.replace(tzinfo=None)
    ends = data.ends_at.replace(tzinfo=None)

    if ends <= starts:
        raise HTTPException(status_code=400, detail="Окончание должно быть позже начала")
    for t in (starts, ends):
        if t.minute % 30 != 0 or t.second or t.microsecond:
            raise HTTPException(status_code=400, detail="Время должно быть кратно 30 минутам")
    if starts.date() != ends.date():
        raise HTTPException(status_code=400, detail="Бронь должна укладываться в один день")
    if starts < datetime.now():
        raise HTTPException(status_code=400, detail="Нельзя бронировать в прошлом")
    if starts < datetime.combine(starts.date(), room.open_time) or ends > datetime.combine(starts.date(), room.close_time):
        raise HTTPException(status_code=400, detail="Вне часов работы помещения")
    if data.attendees and data.attendees > room.capacity:
        raise HTTPException(status_code=400, detail=f"Вместимость помещения: {room.capacity}")

    conflict = db.scalars(
        select(models.Booking).where(
            models.Booking.room_id == room.id,
            models.Booking.status.in_(ACTIVE_STATUSES),
            models.Booking.starts_at < ends,
            models.Booking.ends_at > starts,
        )
    ).first()
    if conflict:
        raise HTTPException(status_code=409, detail="Это время уже занято")

    status = "pending" if room.requires_approval else "approved"
    booking = models.Booking(
        user_id=data.user_id, room_id=room.id, starts_at=starts, ends_at=ends,
        purpose=data.purpose, attendees=data.attendees, status=status,
    )
    db.add(booking)
    db.flush()

    text = ("Заявка отправлена на согласование администратору" if status == "pending"
            else "Бронирование подтверждено")
    db.add(models.Notification(
        user_id=data.user_id, booking_id=booking.id, type="status_changed",
        message=f"{room.name}, {starts:%d.%m.%Y %H:%M}-{ends:%H:%M}: {text}",
    ))
    db.commit()
    db.refresh(booking)
    return booking


@app.get("/api/bookings/my", response_model=list[schemas.BookingOut], tags=["Бронирование"])
def my_bookings(user_id: int, db: Session = Depends(get_db)):
    return db.scalars(
        select(models.Booking)
        .where(models.Booking.user_id == user_id)
        .order_by(models.Booking.starts_at.desc())
    ).all()


@app.delete("/api/bookings/{booking_id}", response_model=schemas.BookingOut, tags=["Бронирование"])
def cancel_booking(booking_id: int, user_id: int, db: Session = Depends(get_db)):
    booking = db.get(models.Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Бронь не найдена")
    if booking.user_id != user_id:
        raise HTTPException(status_code=403, detail="Это чужая бронь")
    if booking.status not in ACTIVE_STATUSES:
        raise HTTPException(status_code=400, detail="Бронь уже нельзя отменить")
    booking.status = "cancelled"
    db.add(models.Notification(
        user_id=user_id, booking_id=booking.id, type="status_changed",
        message=f"Бронь {booking.room.name} на {booking.starts_at:%d.%m.%Y %H:%M} отменена",
    ))
    db.commit()
    db.refresh(booking)
    return booking