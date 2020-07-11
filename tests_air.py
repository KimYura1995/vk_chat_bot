# -*- coding: utf-8 -*-
import os
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch, Mock, ANY
from pony.orm import db_session, rollback

import settings
from bot import Bot
from generate_ticket_image import make_ticket
from vk_api.bot_longpoll import VkBotMessageEvent


def isolate_db(test_func):
    def wrapper(*args, **kwargs):
        with db_session:
            test_func(*args, **kwargs)
            rollback()

    return wrapper


class Test1(TestCase):
    RAW_EVENT = {
        'type': 'message_new',
        'object': {'date': 1592323311, 'from_id': 375367380, 'id': 46, 'out': 0, 'peer_id': 375367380,
                   'text': 'Проверка теста', 'conversation_message_id': 46, 'fwd_messages': [],
                   'important': False, 'random_id': 0, 'attachments': [], 'is_hidden': False},
        'group_id': 196289557, 'event_id': 'cc4b935106f2496310b3e590c81e4807da8227e7'}

    STRING_FLIGHTS = "Выберите понравившийся рейс и введите его цифру:" \
                     "\n1. Москва (Шереметьево) 20-07-2020 18:40:00  ---->  Владивосток (Кневичи) 21-07-2020 16:55:00" \
                     "\n2. Москва (Шереметьево) 20-07-2020 21:25:00  ---->  Владивосток (Кневичи) 21-07-2020 19:45:00" \
                     "\n3. Москва (Шереметьево) 20-07-2020 21:25:00  ---->  Владивосток (Кневичи) 21-07-2020 19:45:00" \
                     "\n4. Москва (Шереметьево) 20-07-2020 23:35:00  ---->  Владивосток (Кневичи) 21-07-2020 22:05:00"

    LIST_FLIGHTS = [
        {'airport_from': 'Шереметьево', 'airport_to': 'Кневичи', 'departure': '2020-07-20T15:40:00+03:00',
         'arrival': '2020-07-21T06:55:00+10:00'},
        {'airport_from': 'Шереметьево', 'airport_to': 'Кневичи', 'departure': '2020-07-20T18:25:00+03:00',
         'arrival': '2020-07-21T09:45:00+10:00'},
        {'airport_from': 'Шереметьево', 'airport_to': 'Кневичи', 'departure': '2020-07-20T18:25:00+03:00',
         'arrival': '2020-07-21T09:45:00+10:00'},
        {'airport_from': 'Шереметьево', 'airport_to': 'Кневичи', 'departure': '2020-07-20T20:35:00+03:00',
         'arrival': '2020-07-21T12:05:00+10:00'}
    ]

    INPUTS = [
        "Проверка",
        "Помощь",
        "Билет",
        "Масква",
        "Москва",
        "Владивостак",
        "Владивосток",
        "20-07-2020",
        "1",
        "Иванов Иван Иванович",
        "1",
        "Комментарий",
        "Да",
        "+7(999)9999999"
    ]

    ANSWER = [
        settings.DEFAULT_ANSWER,
        settings.INTENTS[1]["answer"],
        settings.SCENARIOS["ticket_order"]["steps"]["step1"]["text"],
        "Возможно вы имели ввиду:\n-Маиквак\n-Маса\n-Маскара\n-Массава\n-Москва",
        settings.SCENARIOS["ticket_order"]["steps"]["step2"]["text"],
        "Возможно вы имели ввиду:\n-Владивосток",
        settings.SCENARIOS["ticket_order"]["steps"]["step3"]["text"],
        STRING_FLIGHTS,
        settings.SCENARIOS["ticket_order"]["steps"]["step5"]["text"],
        settings.SCENARIOS["ticket_order"]["steps"]["step6"]["text"],
        settings.SCENARIOS["ticket_order"]["steps"]["step7"]["text"],
        settings.SCENARIOS["ticket_order"]["steps"]["step8"]["text"].format(
            full_name="Иванов Иван Иванович",
            from_city="Москва",
            to_city="Владивосток",
            date="20-07-2020",
            choice_flight="Москва (Шереметьево) 20-07-2020 18:40:00  ---->  Владивосток (Кневичи) 21-07-2020 16:55:00",
            numb_places="1",
            comment="Комментарий"
        ),
        settings.SCENARIOS["ticket_order"]["steps"]["step9"]["text"],
        settings.SCENARIOS["ticket_order"]["steps"]["step10"]["text"]
    ]

    def test_run(self):
        """
        Тестирование функции run
        """
        count = 5
        obj = {"a": 1}
        events = [obj] * count  # [{}, {}, ...]
        long_poller_mock = Mock(return_value=events)
        long_poller_mock_listen_mock = Mock()
        long_poller_mock_listen_mock.listen = long_poller_mock

        with patch("bot.vk_api.VkApi"):
            with patch("bot.VkBotLongPoll", return_value=long_poller_mock_listen_mock):
                bot = Bot("", "")
                bot.on_event = Mock()
                bot.send_image = Mock()
                bot.run()

                bot.on_event.assert_called()
                bot.on_event.assert_any_call(obj)
                assert bot.on_event.call_count == count

    @isolate_db
    def test_on_event(self):
        """
        Тестирование осноной функции on_event
        """
        send_mock = Mock()
        api_mock = Mock()
        api_mock.messages.send = send_mock

        events = []
        for input_text in self.INPUTS:
            event = deepcopy(self.RAW_EVENT)
            event["object"]["text"] = input_text
            events.append(VkBotMessageEvent(event))

        long_poller_mock = Mock()
        long_poller_mock.listen = Mock(return_value=events)

        with patch("bot.VkBotLongPoll", return_value=long_poller_mock):
            with patch("api_yandex.forming_answer", return_value=self.LIST_FLIGHTS):
                bot = Bot("", "")
                bot.api = api_mock
                bot.send_image = Mock()
                bot.run()
        assert send_mock.call_count == len(self.INPUTS)

        real_outputs = []
        for call in send_mock.call_args_list:
            args, kwargs = call
            real_outputs.append(kwargs["message"])
        assert real_outputs == self.ANSWER

    def test_ticket_generation(self):
        """
         Тестирование функции генерации билета gen_ticket
        """
        path_name_avatar_example = os.path.join("resources_tests", "test_avatar.png")
        with open(path_name_avatar_example, "rb") as expected_avatar:
            avatar_mock = Mock()
            avatar_mock.content = expected_avatar.read()

        with patch("requests.get", return_value=avatar_mock):
            ticket_file = make_ticket(
                full_name="Иванов Иван Иванович",
                from_city="Москва",
                to_city="Владивосток",
                date_departure="10-07-2020 10:00:00",
                date_arrival="10-07-2020 12:00:00",
                phone_number="89096785031"
            )
            path_name_ticket_example = os.path.join("resources_tests", "ticket_sample.png")
            with open(path_name_ticket_example, "rb") as expected_file:
                expected_bytes = expected_file.read()
            assert ticket_file.read() == expected_bytes
