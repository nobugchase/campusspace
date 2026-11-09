from pathlib import Path

from fastapi.staticfiles import StaticFiles
from datetime import date, datetime, timedelta
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, update
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
def require_admin(db: Session, user_id: int):
    user = db.get(models.User, user_id)
    if user is None or user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Нужны права администратора")
    return user


@app.get("/api/admin/bookings", response_model=list[schemas.BookingAdminOut], tags=["Администратор"])
def admin_bookings(admin_id: int, status: str = "pending", db: Session = Depends(get_db)):
    require_admin(db, admin_id)
    return db.scalars(
        select(models.Booking)
        .where(models.Booking.status == status)
        .order_by(models.Booking.starts_at)
    ).all()


@app.post("/api/bookings/{booking_id}/decision", response_model=schemas.BookingAdminOut, tags=["Администратор"])
def decide_booking(booking_id: int, data: schemas.DecisionIn, db: Session = Depends(get_db)):
    require_admin(db, data.admin_id)
    if data.decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Решение: approved или rejected")
    booking = db.get(models.Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Бронь не найдена")
    if booking.status != "pending":
        raise HTTPException(status_code=400, detail="Заявка уже обработана")

    booking.status = data.decision
    db.add(models.Approval(
        booking_id=booking.id, admin_id=data.admin_id,
        decision=data.decision, comment=data.comment,
    ))
    verdict = "подтверждена" if data.decision == "approved" else "отклонена"
    message = f"Заявка на {booking.room.name}, {booking.starts_at:%d.%m.%Y %H:%M}, {verdict}"
    if data.comment:
        message += f". Комментарий: {data.comment}"
    db.add(models.Notification(
        user_id=booking.user_id, booking_id=booking.id,
        type="status_changed", message=message[:255],
    ))
    db.commit()
    db.refresh(booking)
    return booking

@app.get("/api/notifications", response_model=list[schemas.NotificationOut], tags=["Уведомления"])
def list_notifications(user_id: int, db: Session = Depends(get_db)):
    return db.scalars(
        select(models.Notification)
        .where(models.Notification.user_id == user_id)
        .order_by(models.Notification.created_at.desc())
        .limit(50)
    ).all()


@app.post("/api/notifications/read-all", tags=["Уведомления"])
def read_all_notifications(user_id: int, db: Session = Depends(get_db)):
    db.execute(
        update(models.Notification)
        .where(models.Notification.user_id == user_id, models.Notification.is_read.is_(False))
        .values(is_read=True)
    )
    db.commit()
    return {"ok": True}

def build_summary(room_id, count, c, e, k):
    values = [v for v in (c, e, k) if v is not None]
    return schemas.RatingSummary(
        room_id=room_id,
        count=count or 0,
        average=round(sum(values) / len(values), 1) if values else None,
        cleanliness=round(c, 1) if c is not None else None,
        equipment=round(e, 1) if e is not None else None,
        comfort=round(k, 1) if k is not None else None,
    )


@app.get("/api/ratings", response_model=list[schemas.RatingSummary], tags=["Отзывы"])
def all_ratings(db: Session = Depends(get_db)):
    rows = db.execute(
        select(
            models.Review.room_id,
            func.count(models.Review.id),
            func.avg(models.Review.cleanliness),
            func.avg(models.Review.equipment_score),
            func.avg(models.Review.comfort),
        ).group_by(models.Review.room_id)
    ).all()
    return [build_summary(*row) for row in rows]


@app.get("/api/rooms/{room_id}/reviews", response_model=schemas.RoomReviewsOut, tags=["Отзывы"])
def room_reviews(room_id: int, db: Session = Depends(get_db)):
    if db.get(models.Room, room_id) is None:
        raise HTTPException(status_code=404, detail="Помещение не найдено")
    row = db.execute(
        select(
            func.count(models.Review.id),
            func.avg(models.Review.cleanliness),
            func.avg(models.Review.equipment_score),
            func.avg(models.Review.comfort),
        ).where(models.Review.room_id == room_id)
    ).one()
    items = db.scalars(
        select(models.Review)
        .where(models.Review.room_id == room_id)
        .order_by(models.Review.created_at.desc())
    ).all()
    return schemas.RoomReviewsOut(summary=build_summary(room_id, *row), items=items)


@app.post("/api/reviews", response_model=schemas.ReviewOut, status_code=201, tags=["Отзывы"])
def create_review(data: schemas.ReviewCreate, db: Session = Depends(get_db)):
    if db.get(models.Room, data.room_id) is None:
        raise HTTPException(status_code=404, detail="Помещение не найдено")
    if db.get(models.User, data.user_id) is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    for score in (data.cleanliness, data.equipment_score, data.comfort):
        if not 1 <= score <= 5:
            raise HTTPException(status_code=400, detail="Оценки должны быть от 1 до 5")

    reviewed_ids = select(models.Review.booking_id).where(
        models.Review.user_id == data.user_id, models.Review.booking_id.is_not(None)
    )
    booking = db.scalars(
        select(models.Booking).where(
            models.Booking.user_id == data.user_id,
            models.Booking.room_id == data.room_id,
            models.Booking.status == "approved",
            models.Booking.id.not_in(reviewed_ids),
        )
    ).first()
    if booking is None:
        raise HTTPException(
            status_code=400,
            detail="Отзыв можно оставить после подтверждённой брони этого помещения (по одному отзыву на бронь)",
        )

    review = models.Review(
        user_id=data.user_id, room_id=data.room_id, booking_id=booking.id,
        cleanliness=data.cleanliness, equipment_score=data.equipment_score,
        comfort=data.comfort, comment=(data.comment or None),
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review

@app.post("/api/recurring", response_model=schemas.RecurringResult, status_code=201,
          tags=["Повторяющиеся брони"])
def create_recurring(data: schemas.RecurringCreate, db: Session = Depends(get_db)):
    room = db.get(models.Room, data.room_id)
    if room is None or not room.is_active:
        raise HTTPException(status_code=404, detail="Помещение не найдено")
    if db.get(models.User, data.user_id) is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if data.frequency not in ("daily", "weekly"):
        raise HTTPException(status_code=400, detail="Периодичность: daily или weekly")
    if data.frequency == "weekly" and not data.weekdays:
        raise HTTPException(status_code=400, detail="Выберите дни недели")
    if any(d < 1 or d > 7 for d in data.weekdays):
        raise HTTPException(status_code=400, detail="Дни недели: числа от 1 до 7")
    for t in (data.start_time, data.end_time):
        if t.minute % 30 != 0 or t.second:
            raise HTTPException(status_code=400, detail="Время должно быть кратно 30 минутам")
    if data.end_time <= data.start_time:
        raise HTTPException(status_code=400, detail="Окончание должно быть позже начала")
    if data.start_time < room.open_time or data.end_time > room.close_time:
        raise HTTPException(status_code=400, detail="Вне часов работы помещения")
    if data.end_date < data.start_date:
        raise HTTPException(status_code=400, detail="Дата окончания раньше даты начала")
    if (data.end_date - data.start_date).days > 92:
        raise HTTPException(status_code=400, detail="Серия не может быть длиннее 3 месяцев")
    if data.attendees and data.attendees > room.capacity:
        raise HTTPException(status_code=400, detail=f"Вместимость помещения: {room.capacity}")

    weekdays = sorted(set(data.weekdays))
    rule = models.RecurringRule(
        user_id=data.user_id, room_id=room.id, frequency=data.frequency,
        weekdays=",".join(map(str, weekdays)) if data.frequency == "weekly" else None,
        start_time=data.start_time, end_time=data.end_time,
        start_date=data.start_date, end_date=data.end_date,
    )
    db.add(rule)
    db.flush()

    status = "pending" if room.requires_approval else "approved"
    now = datetime.now()
    created = 0
    skipped = []
    day = data.start_date
    while day <= data.end_date:
        if data.frequency == "daily" or day.isoweekday() in weekdays:
            starts = datetime.combine(day, data.start_time)
            ends = datetime.combine(day, data.end_time)
            if starts < now:
                skipped.append(f"{day:%d.%m.%Y}: время уже прошло")
            else:
                conflict = db.scalars(
                    select(models.Booking).where(
                        models.Booking.room_id == room.id,
                        models.Booking.status.in_(ACTIVE_STATUSES),
                        models.Booking.starts_at < ends,
                        models.Booking.ends_at > starts,
                    )
                ).first()
                if conflict:
                    skipped.append(f"{day:%d.%m.%Y}: время занято")
                else:
                    db.add(models.Booking(
                        user_id=data.user_id, room_id=room.id, recurring_id=rule.id,
                        starts_at=starts, ends_at=ends, purpose=data.purpose,
                        attendees=data.attendees, status=status,
                    ))
                    created += 1
        day += timedelta(days=1)

    if created == 0:
        db.rollback()
        reason = "; ".join(skipped[:3]) or "в выбранный период нет подходящих дней"
        raise HTTPException(status_code=400, detail="Не создано ни одной брони: " + reason)

    text = "отправлена на согласование" if status == "pending" else "подтверждена"
    db.add(models.Notification(
        user_id=data.user_id, type="status_changed",
        message=f"Серия бронирований {room.name} ({created} шт.) {text}",
    ))
    db.commit()
    db.refresh(rule)
    return schemas.RecurringResult(rule=rule, created=created, skipped=skipped)


@app.get("/api/recurring/my", response_model=list[schemas.RecurringOut], tags=["Повторяющиеся брони"])
def my_recurring(user_id: int, db: Session = Depends(get_db)):
    return db.scalars(
        select(models.RecurringRule)
        .where(models.RecurringRule.user_id == user_id, models.RecurringRule.is_active.is_(True))
        .order_by(models.RecurringRule.id.desc())
    ).all()


@app.delete("/api/recurring/{rule_id}", tags=["Повторяющиеся брони"])
def cancel_recurring(rule_id: int, user_id: int, db: Session = Depends(get_db)):
    rule = db.get(models.RecurringRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Серия не найдена")
    if rule.user_id != user_id:
        raise HTTPException(status_code=403, detail="Это чужая серия")
    rule.is_active = False
    future = db.scalars(
        select(models.Booking).where(
            models.Booking.recurring_id == rule.id,
            models.Booking.status.in_(ACTIVE_STATUSES),
            models.Booking.starts_at > datetime.now(),
        )
    ).all()
    for booking in future:
        booking.status = "cancelled"
    db.add(models.Notification(
        user_id=user_id, type="status_changed",
        message=f"Серия бронирований {rule.room.name} отменена (отменено броней: {len(future)})",
    ))
    db.commit()
    return {"cancelled": len(future)}

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")