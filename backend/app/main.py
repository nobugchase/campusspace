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