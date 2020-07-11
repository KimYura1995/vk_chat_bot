# -*- coding: utf-8 -*-
from generate_ticket_image import make_ticket


def make_ticket_handler(text, context):
    image = make_ticket(
        full_name=context["full_name"],
        from_city=context["from_city"],
        to_city=context["to_city"],
        date_departure=context["datetime_departure"],
        date_arrival=context["datetime_arrival"],
        phone_number=context["phone_number"]
    )
    return image