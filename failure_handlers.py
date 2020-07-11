# -*- coding: utf-8 -*-

from fuzzywuzzy import fuzz
import os
import csv


def failure_city_name(text):
    """
    Выдает название городов похожих на введенное пользователем, в случае орфографической ошибки
    """
    user_word = text.capitalize()
    options = set()
    failure_text = "Возможно вы имели ввиду:"
    path_name = os.path.join("resources", "apinfo.csv")
    with open(path_name, mode="r", encoding="utf8") as apinfo:
        apinfo_reader = csv.DictReader(apinfo, delimiter=",")
        for line in apinfo_reader:
            city = line["city_rus"]
            comparison = fuzz.ratio(city, user_word)
            if comparison >= 75:
                options.add(city)
    if options:
        for city in sorted(options):
            failure_text += f"\n-{city}"
    else:
        failure_text = "К сожалению я не знаю такого города."

    return failure_text
