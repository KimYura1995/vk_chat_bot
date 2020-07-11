# -*- coding: utf-8 -*-

import os
import requests
import csv
import settings

from datetime import datetime
from fuzzywuzzy import fuzz


def city_name_to_iata(city):
    """Конвертируем название города в код iata"""
    iata = list()
    path_name = os.path.join("resources", "apinfo.csv")
    with open(path_name, mode="r", encoding="utf8") as csv_file:
        apinfo = csv.DictReader(csv_file)
        for line in apinfo:
            if fuzz.ratio(line["city_rus"], city) >= 90:
                iata.append(line["iata_code"])
    return iata


def date_convert(date):
    """Конвертируем дату в формат YYYY-MM-DD"""
    data_date = datetime.strptime(date, "%d-%m-%Y")
    date = data_date.strftime("%Y-%m-%d")
    return date


def get_json_yandex(from_iata, to_iata, date):
    """Запрашиваем через API яндекс рейсы"""
    result_flights = list()
    for iata_city_from in from_iata:
        for iata_city_ti in to_iata:
            result = requests.get(f"https://api.rasp.yandex.net/v3.0/search/?apikey={settings.API_KEY}&format=json&"
                                  f"from={iata_city_from}&to={iata_city_ti}&lang=ru_RU&"
                                  f"page=1&date={date}&limit=5&system=iata&transport_types=plane")
            if result.status_code == 200:
                result_json = result.json()
                if result_json["pagination"]["total"] >= 1:
                    for flights in result_json["segments"]:
                        airport_from = flights["from"]["title"]
                        airport_to = flights["to"]["title"]
                        departure = flights["departure"]
                        arrival = flights["arrival"]
                        result = dict(
                            airport_from=airport_from,
                            airport_to=airport_to,
                            departure=departure,
                            arrival=arrival
                        )
                        result_flights.append(result)
    return result_flights


def forming_answer(context):
    """Формируем список из 5 рейсов"""
    from_raw = context["from_city"]
    to_raw = context["to_city"]
    date_raw = context["date"]
    from_iata = city_name_to_iata(from_raw)
    to_iata = city_name_to_iata(to_raw)
    date = date_convert(date_raw)
    result_flights = get_json_yandex(from_iata, to_iata, date)
    if len(result_flights) > 5:
        return result_flights[:5]
    else:
        return result_flights



