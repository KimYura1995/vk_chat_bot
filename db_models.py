# -*- coding: utf-8 -*-

from datetime import datetime

from pony.orm import Database, Required, Json, Optional

from settings import DB_CONFIG


db = Database()
db.bind(**DB_CONFIG)


class UserState(db.Entity):
    """Состояние пользовтеля внутри сценария"""
    user_id = Required(str, unique=True)
    scenario_name = Required(str)
    step_name = Required(str)
    context = Required(Json)


class Registration(db.Entity):
    """База клиентов"""
    full_name = Required(str)
    from_city = Required(str)
    to_city = Required(str)
    date_departure = Required(datetime, precision=6)
    date_arrival = Required(datetime, precision=6)
    numb_places = Required(int)
    comment = Optional(str)
    phone_number = Required(str)


db.generate_mapping(create_tables=True)