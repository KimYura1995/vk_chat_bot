# -*- coding: utf-8 -*-

from datetime import datetime


def date_convert(date):
    """Конвертируем дату в формат YYYY-MM-DD"""
    data_date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S%z")
    utc_offset = data_date.utcoffset()
    data_date = data_date.replace(tzinfo=None) + utc_offset
    date = data_date.strftime("%d-%m-%Y %H:%M:%S")
    return date


def flight_message_handler(context):
    """
    Формируем сообщение с имеющимися рейсами
    """
    flight_string_list = list()
    flights = context["flights"]
    text_to_send = "Выберите понравившийся рейс и введите его цифру:"
    for num, flight in enumerate(flights):
        date_departure = date_convert(flight['departure'])
        date_arrival = date_convert(flight['arrival'])
        string_flight = f"{context['from_city']} ({flight['airport_from']}) {date_departure}  ---->  " \
                        f"{context['to_city']} ({flight['airport_to']}) {date_arrival}"
        string_flight_iter = f"\n{num + 1}. " + string_flight
        text_to_send += string_flight_iter
        flight_string_list.append(string_flight)
    context["flights_string"] = flight_string_list
    return text_to_send
