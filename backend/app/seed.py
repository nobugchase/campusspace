from datetime import time

from . import models as m
from .database import Base, SessionLocal, engine


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if db.query(m.Role).first():
        print("База уже заполнена")
        return

    roles = {n: m.Role(name=n) for n in ("student", "teacher", "admin")}
    db.add_all(roles.values())
    db.flush()

    # Пароли пока заглушки, настоящее хеширование добавим на шаге авторизации
    db.add_all([
        m.User(role_id=roles["admin"].id, full_name="Администратор Кампуса",
               email="admin@campus.local", password_hash="TODO"),
        m.User(role_id=roles["student"].id, full_name="Студент Тестовый",
               email="student@campus.local", password_hash="TODO", faculty="Информатика"),
        m.User(role_id=roles["teacher"].id, full_name="Преподаватель Тестовый",
               email="teacher@campus.local", password_hash="TODO", faculty="Информатика"),
    ])

    main_b = m.Building(name="Главный корпус", address="ул. Университетская, 1",
                        latitude=59.3293, longitude=18.0686)
    it_b = m.Building(name="Корпус информатики", address="ул. Научная, 5",
                      latitude=59.3326, longitude=18.0649)
    db.add_all([main_b, it_b])

    types = {n: m.RoomType(name=n) for n in
             ("Аудитория", "Переговорная", "Коворкинг", "Компьютерный класс")}
    db.add_all(types.values())

    eq = {n: m.Equipment(name=n, icon=i) for n, i in [
        ("Проектор", "projector"), ("Маркерная доска", "board"), ("ПК", "pc"),
        ("Экран", "screen"), ("Кондиционер", "ac"), ("Розетки у каждого места", "plug"),
    ]}
    db.add_all(eq.values())
    db.flush()

    def add_room(building, rtype, number, name, floor, capacity, approval, equipment, desc, access):
        room = m.Room(
            building_id=building.id, room_type_id=types[rtype].id, number=number,
            name=name, floor=floor, capacity=capacity, description=desc,
            requires_approval=approval, open_time=time(8, 0), close_time=time(21, 0),
        )
        db.add(room)
        db.flush()
        for eq_name, qty in equipment:
            db.add(m.RoomEquipment(room_id=room.id, equipment_id=eq[eq_name].id, quantity=qty))
        db.add(m.RoomPhoto(room_id=room.id, is_main=True, sort_order=0,
                           url=f"https://picsum.photos/seed/campus{number}/800/500"))
        db.add(m.AccessRule(room_id=room.id, title=access[0], description=access[1]))

    add_room(main_b, "Аудитория", "101", "Большая аудитория 101", 1, 120, False,
             [("Проектор", 1), ("Экран", 1), ("Маркерная доска", 2)],
             "Лекционная аудитория с амфитеатром.", ("Свободный вход", "Вход по студенческому билету"))
    add_room(main_b, "Аудитория", "205", "Аудитория 205", 2, 40, False,
             [("Проектор", 1), ("Маркерная доска", 1), ("Кондиционер", 1)],
             "Аудитория для семинаров.", ("Свободный вход", "Вход по студенческому билету"))
    add_room(main_b, "Переговорная", "310", "Переговорная 310", 3, 8, False,
             [("Маркерная доска", 1), ("Экран", 1), ("Розетки у каждого места", 8)],
             "Небольшая комната для проектных встреч.", ("Ключ на вахте", "Ключ выдаётся по брони"))
    add_room(main_b, "Коворкинг", "K1", "Коворкинг «Атриум»", 1, 25, False,
             [("Розетки у каждого места", 25), ("Кондиционер", 1)],
             "Открытое пространство для самостоятельной работы.", ("Свободный вход", "Вход по студенческому билету"))
    add_room(it_b, "Компьютерный класс", "C12", "Компьютерный класс C12", 1, 20, False,
             [("ПК", 20), ("Проектор", 1), ("Маркерная доска", 1)],
             "20 рабочих мест с ПК.", ("Пропуск", "Нужен пропуск корпуса информатики"))
    add_room(it_b, "Компьютерный класс", "C14", "Лаборатория C14 (спец.)", 1, 12, True,
             [("ПК", 12), ("Экран", 1)],
             "Специализированная лаборатория, бронь по согласованию с администратором.",
             ("Только по согласованию", "Доступ после одобрения заявки"))
    add_room(it_b, "Переговорная", "2A", "Переговорная 2A", 2, 6, False,
             [("Экран", 1), ("Маркерная доска", 1)],
             "Тихая комната для небольших встреч.", ("Ключ на вахте", "Ключ выдаётся по брони"))

    db.commit()
    print("Тестовые данные добавлены")


if __name__ == "__main__":
    run()