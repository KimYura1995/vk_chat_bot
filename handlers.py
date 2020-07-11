# -*- coding: utf-8 -*-

import re
import csv
import os

from api_yandex import forming_answer
from datetime import datetime


re_name_city = re.compile(r'\w{3,}')
re_choice = re.compile(r"[1-5]")
re_number_of_places = re.compile(r"[1-5]")
re_info = re.compile(r"Да|Нет")
re_phone_number = re.compile(r"^((8|\+7)[\- ]?)?(\(?\d{3}\)?[\- ]?)?[\d\- ]{7,10}$")
re_full_name = re.compile(r"[А-Я]\w*\s[А-Я]\w*\s[А-Я]\w*")


def get_city_csv(text):
    path_name = os.path.join("resources", "apinfo.csv")
    with open(path_name, mode="r", encoding="utf8") as apinfo:
        apinfo_reader = csv.DictReader(apinfo, delimiter=",")
        for line in apinfo_reader:
            if line["city_rus"] == text:
                return True
        else:
            return False


def handle_city_name_from(text, context):
    """
    Обработка орфографии названия города отбытия
    """
    if get_city_csv(text):
        context["from_city"] = text
        return True
    else:
        return False


def handle_city_name_to(text, context):
    """
    Обработка орфографии названия города прибытия
    """
    if get_city_csv(text):
        context["to_city"] = text
        return True
    else:
        return False


def processing_data(func):
    def surrogate(*args, **kwargs):
        result_handler = func(*args, **kwargs)
        if result_handler:
            result_flights = forming_answer(kwargs["context"])
            kwargs["context"]["flights"] = result_flights
            kwargs["context"]["num_flights"] = len(result_flights)
        return result_handler

    return surrogate


@processing_data
def handle_date(text, context):
    """
    Проверка на правильность даты
    """
    try:
        valid_date = datetime.strptime(text, "%d-%m-%Y")
    except ValueError:
        return False
    if valid_date.date() >= datetime.today().date():
        context["date"] = text
        return True
    else:
        return False


def handle_choice(text, context):
    """
    Проверка выбора пользователя
    """
    match = re.match(re_choice, text)
    if match:
        numb_choice = int(text)
        max_numb_choice = context["num_flights"]
        if numb_choice <= max_numb_choice:
            context["choice"] = text
            context["choice_flight"] = context["flights_string"][numb_choice - 1]
            choise_flight = context["flights_string"][numb_choice - 1].split()
            datetime_departure = f"{choise_flight[2]} {choise_flight[3]}"
            datetime_arrival = f"{choise_flight[7]} {choise_flight[8]}"
            context["datetime_departure"] = datetime_departure
            context["datetime_arrival"] = datetime_arrival
        else:
            return False
        return True
    else:
        return False


def handle_number_of_places(text, context):
    """
    Проверка кол-ва мест
    """
    match = re.match(re_number_of_places, text)
    if match:
        context["numb_places"] = text
        return True
    else:
        return False


def handle_comment(text, context):
    """
    Обработка комментария пользователя
    """
    context["comment"] = text
    return True


def handle_check_info(text, context):
    """
    Проверка ответа да или нет
    """
    answer_user = text.capitalize()
    match = re.search(re_info, answer_user)
    match = match[0] if match else None
    if match:
        if match == "Да":
            context["final_answer"] = True
            return True
        else:
            context["final_answer"] = False
            return False
    else:
        return False


def handle_phone_number(text, context):
    """
    Проверка номера телефона
    """
    match = re.match(re_phone_number, text)
    if match:
        context["phone_number"] = text
        return True
    else:
        return False


def handle_full_name(text, context):
    """
    Проверка ФИО
    """
    match = re.match(re_full_name, text)
    if match:
        context["full_name"] = text
        return True
    else:
        return False
