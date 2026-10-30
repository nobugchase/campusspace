from datetime import time

from pydantic import BaseModel, ConfigDict


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class BuildingOut(ORM):
    id: int
    name: str
    address: str
    latitude: float | None
    longitude: float | None


class RoomTypeOut(ORM):
    id: int
    name: str


class EquipmentOut(ORM):
    id: int
    name: str
    icon: str | None


class RoomEquipmentOut(ORM):
    quantity: int
    equipment: EquipmentOut


class PhotoOut(ORM):
    id: int
    url: str
    is_main: bool


class AccessRuleOut(ORM):
    id: int
    title: str
    description: str


class RoomOut(ORM):
    id: int
    number: str
    name: str
    floor: int | None
    capacity: int
    description: str | None
    requires_approval: bool
    open_time: time
    close_time: time
    building: BuildingOut
    room_type: RoomTypeOut
    photos: list[PhotoOut]
    equipment: list[RoomEquipmentOut]
    access_rules: list[AccessRuleOut]