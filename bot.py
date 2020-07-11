# -*- coding: utf-8 -*-
#!/usr/bin/env python3

import random
import logging
import requests
import handlers
import failure_handlers
import gen_text_handlers
import image_handlers
from datetime import datetime
from db_models import UserState, Registration
from pony.orm import db_session, pony

try:
    import settings
except ImportError:
    exit("DO cp settings.py.default settings.py and set TOKEN")

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType


log = logging.getLogger("bot")


def configure_logging():
    """
    Конфигурирование логирования
    :return: None
    """
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    stream_handler.setLevel(logging.INFO)
    log.addHandler(stream_handler)

    file_handler = logging.FileHandler("bot.log", encoding="UTF-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%d-%m-%Y %H:%M"))
    file_handler.setLevel(logging.DEBUG)
    log.addHandler(file_handler)

    log.setLevel(logging.DEBUG)


class Bot:
    """
    Bot для vk.com
    Use python3.8
    """

    def __init__(self, group_id, token):
        """
        :param group_id: group id из группы vk
        :param token: секретный токен
        """
        self.group_id = group_id
        self.token = token

        self.vk = vk_api.VkApi(token=self.token)
        self.long_poller = VkBotLongPoll(self.vk, self.group_id)
        self.api = self.vk.get_api()

    def run(self):
        """
        Запуск бота.
        """
        for event in self.long_poller.listen():
            try:
                self.on_event(event)
            except Exception:
                log.exception("ошибка в обработке события")

    @db_session
    def on_event(self, event):
        """
        Отправляет сообщение назад, если оно текст.
        :param event: VkBotMessageEvent object
        """
        if event.type != VkBotEventType.MESSAGE_NEW:
            log.info("Неизвестное событие - %s", event.type)
            return
        user_id = event.object.peer_id
        text = event.object.text
        state = UserState.get(user_id=str(user_id))
        for intent in settings.INTENTS:
            log.debug(f'User gets {intent}')
            if any(token in text.lower() for token in intent["tokens"]):
                if intent["answer"]:
                    self.send_text(intent["answer"], user_id)
                else:
                    self.start_scenario(intent["scenario"], str(user_id), state, text)
                break
        else:
            if state is not None:
                self.continue_scenario(text=text, state=state, user_id=user_id)
            else:
                self.send_text(settings.DEFAULT_ANSWER, user_id)

    def send_text(self, text_to_send, user_id):
        """
        Отправка сообщения
        :param text_to_send: строка для отправки
        :param user_id: user_id (peer_id)
        """
        self.api.messages.send(
            message=text_to_send,
            random_id=random.randint(0, 2 ** 20),
            peer_id=user_id
        )

    def send_image(self, image, user_id):
        """
        Отправка картинки
        :param image: file like object
        :param user_id: user_id (peer_id)
        """
        upload_url = self.api.photos.getMessagesUploadServer()["upload_url"]
        upload_data = requests.post(url=upload_url, files={"photo": ("image.png", image, "image/png")}).json()
        image_data = self.api.photos.saveMessagesPhoto(**upload_data)
        owner_id = image_data[0]["owner_id"]
        media_id = image_data[0]["id"]
        attachment = f"photo{owner_id}_{media_id}"
        self.api.messages.send(
            attachment=attachment,
            random_id=random.randint(0, 2 ** 20),
            peer_id=user_id
        )

    def send_step(self, step, user_id, text, context, answer_flag):
        """
        Обработка действия перед отправкой
        :param step: шаг по сценарию
        :param user_id: user_id (peer_id)
        :param text: строка пользователя
        :param context: текущее состояние пользователя
        :param answer_flag: состояние отработки handler
        """
        if answer_flag:
            if "text" in step:
                self.send_text(step["text"].format(**context), user_id)
            if "gen_text" in step:
                gen_handle = getattr(gen_text_handlers, step['gen_text'])
                text_to_send = gen_handle(context=context)
                self.send_text(text_to_send, user_id)
            if "image" in step:
                image_handler = getattr(image_handlers, step["image"])
                image = image_handler(text, context)
                self.send_image(image, user_id)
        else:
            if "failure_handler" in step:
                failure_handler = getattr(failure_handlers, step['failure_handler'])
                self.send_text(failure_handler(text=text), user_id)
            else:
                text_to_send = step['failure_text'].format(**context)
                self.send_text(text_to_send, user_id)

    def start_scenario(self, scenario_name, user_id, state, text):
        """
        Стартует сценарий бота
        :param scenario_name: Название сценария
        :param user_id: user_id (peer_id)
        """
        scenario = settings.SCENARIOS[scenario_name]
        first_step = scenario["first_step"]
        step = scenario["steps"][first_step]
        self.send_step(step, user_id, text, context={}, answer_flag=True)
        try:
            UserState(user_id=user_id, scenario_name=scenario_name, step_name=first_step, context={})
        except pony.orm.core.CacheIndexError:
            state.delete()
            UserState(user_id=user_id, scenario_name=scenario_name, step_name=first_step, context={})

    def registration_to_bd(self, state):
        """
        Отправка данных в базу Registration
        :param state: состояние пользователя
        """
        datetime_departure = datetime.strptime(state.context["datetime_departure"], "%d-%m-%Y %H:%M:%S")
        datetime_arrival = datetime.strptime(state.context["datetime_arrival"], "%d-%m-%Y %H:%M:%S")
        Registration(
            full_name=state.context["full_name"],
            from_city=state.context["from_city"],
            to_city=state.context["to_city"],
            date_departure=datetime_departure,
            date_arrival=datetime_arrival,
            numb_places=state.context["numb_places"],
            comment=state.context["comment"],
            phone_number=state.context["phone_number"]
        )

    def positive_response_gen(self, text, state, steps, step, user_id):
        """
        Генерация ответа при полодительном ответе от пользователя
        :param state: состояние пользователя
        :param steps: шаги
        :param step: текущий шаг
        """
        next_step = steps[step["next_step"]]
        self.send_step(next_step, user_id, text, state.context, answer_flag=True)
        if next_step["next_step"]:
            state.step_name = step['next_step']
            if (state.context.get("num_flights") == 0) or (state.context.get("final_answer") is False):
                self.send_text(settings.DEFAULT_ANSWER, user_id)
                state.delete()
                log.info(f"Все данные от пользователя {state.context}")
        else:
            log.info(f"Все данные от пользователя {state.context}")
            self.registration_to_bd(state)
            state.delete()

    def negative_response_gen(self, state, step, text, user_id):
        """
        Генерация ответа при отрицательном ответе от пользователя
        :param state: состояние пользователя
        :param step: текущий шаг
        :param text: ответ от пользователя
        """
        self.send_step(step, user_id, text, state.context, answer_flag=False)
        if state.context.get("final_answer") is False:
            state.delete()

    def continue_scenario(self, text, state, user_id):
        """
        Продолжение текущего сценария
        :param text: Сообщение от пользователя
        """
        steps = settings.SCENARIOS[state.scenario_name]["steps"]
        step = steps[state.step_name]
        handler = getattr(handlers, step['handler'])
        if handler(text=text, context=state.context):
            self.positive_response_gen(text=text, state=state, steps=steps, step=step, user_id=user_id)
        else:
            self.negative_response_gen(state=state, step=step, text=text, user_id=user_id)


if __name__ == '__main__':
    configure_logging()
    bot = Bot(settings.GROUP_ID, settings.TOKEN)
    bot.run()
