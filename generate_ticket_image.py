# -*- coding: utf-8 -*-

import os
import requests

from PIL import Image, ImageFont, ImageDraw
from datetime import datetime
from io import BytesIO


def make_ticket(full_name, from_city, to_city, date_departure, date_arrival, phone_number):
    """Печать информации в билет"""
    path_template = os.path.join("resources", "ticket_template.png")
    path_font = os.path.join("resources", "Calibri.ttf")

    full_name = full_name.upper()
    surname, name, patronymic = full_name.split()
    name_for_ticket = f"{surname} {name[0]}.{patronymic[0]}."
    from_city = from_city.upper()
    to_city = to_city.upper()
    datetime_departure = datetime.strptime(date_departure, "%d-%m-%Y %H:%M:%S")
    datetime_arrival = datetime.strptime(date_arrival, "%d-%m-%Y %H:%M:%S")
    date = datetime_departure.strftime("%d.%m")
    time_departure = datetime_departure.strftime("%H:%M")
    time_arrival = datetime_arrival.strftime("%H:%M")

    ticket_template = Image.open(path_template)
    x_template, y_template = ticket_template.size[0], ticket_template.size[1]
    font_size = int(y_template / 25.0625)
    font_size_bold = int(y_template / 20.0425)
    font = ImageFont.truetype(path_font, size=font_size)
    font_bold = ImageFont.truetype(path_font, size=font_size_bold)
    draw = ImageDraw.Draw(ticket_template)

    # Координаты
    # Координаты задаю, относительно размеров исходного билета, на случай, если изменится размер
    x_text_column_01 = int(x_template / 14.608)
    x_text_column_02 = int(x_template / 2.341)
    x_text_column_03 = int(x_template / 1.701)
    y_text_row_fio = int(y_template / 3.132)
    y_text_row_from_ = int(y_template / 2.005)
    y_text_row_to = int(y_template / 1.517)
    y_text_row_date = y_text_row_to
    y_text_row_time_departure = y_text_row_to
    y_text_row_time_arrival = int(y_template / 1.217)
    x_avatar = int(x_template / 1.513)
    y_avatar = int(y_template / 6.075)
    avatar_size = 100

    # Рисование текста
    draw.text((x_text_column_01, y_text_row_fio), name_for_ticket, font=font, fill=(0, 0, 0))
    draw.text((x_text_column_01, y_text_row_from_), from_city, font=font, fill=(0, 0, 0))
    draw.text((x_text_column_01, y_text_row_to), to_city, font=font, fill=(0, 0, 0))
    draw.text((x_text_column_02, y_text_row_date), date, font=font, fill=(0, 0, 0))
    draw.text((x_text_column_03, y_text_row_time_departure), time_departure, font=font, fill=(0, 0, 0))
    draw.text((x_text_column_03, y_text_row_time_arrival), time_arrival, font=font_bold, fill=(0, 0, 0))

    # Рисуем аватар
    response = requests.get(url=f"https://api.adorable.io/avatars/{avatar_size}/{phone_number}")
    avatar_file = BytesIO(response.content)
    avatar = Image.open(avatar_file)
    ticket_template.paste(avatar, (x_avatar, y_avatar))

    temp_file = BytesIO()
    ticket_template.save(temp_file, "png")
    temp_file.seek(0)
    with open("resources_tests/ticket_sample.png", "wb") as asdas:
        ticket_template.save(asdas, "png")
    return temp_file