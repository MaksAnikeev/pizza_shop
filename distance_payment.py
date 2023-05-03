import time

import environs
import requests
from geopy import distance
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (Filters, MessageHandler, PreCheckoutQueryHandler,
                          Updater)

from moltin import get_entry


def fetch_coordinates(api_yandex_key, address):
    base_url = "https://geocode-maps.yandex.ru/1.x"
    response = requests.get(base_url, params={
        "geocode": address,
        "apikey": api_yandex_key,
        "format": "json",
    })
    response.raise_for_status()
    found_places = response.json()['response']['GeoObjectCollection']['featureMember']

    if not found_places:
        return None

    most_relevant = found_places[0]
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
    return lon, lat


def get_user_dictance(user):
    return user['distance']


def get_min_distance(client_coordinates, pizzerias_params):
    distance_to_client = []
    for pizzeria in pizzerias_params:
        pizzeria_longitude = pizzeria['pizzeria_longitude']
        pizzeria_latitude = pizzeria['pizzeria_latitude']
        pizzeria_address = (pizzeria_longitude, pizzeria_latitude)
        client_distance = round(distance.distance(client_coordinates,
                                                  pizzeria_address).km, 2)
        client_params = {'pizzeria_address': pizzeria['pizzeria_address'],
                         'distance': client_distance,
                         'pizzeria_id': pizzeria['id']}
        distance_to_client.append(client_params)
    distance_params = min(distance_to_client, key=get_user_dictance)
    pizzeria_full_address = distance_params['pizzeria_address']
    distance_to_client = distance_params['distance']
    pizzeria_id = distance_params['pizzeria_id']
    return pizzeria_full_address, pizzeria_id, distance_to_client


def send_alarm_clock_message(context):
    job = context.job
    alarm_clock_message = 'Приятного аппетита! ' \
                          'Надеемся что пицца к вам пришла вовремя ' \
                          'и вы уже наслаждаетесь ее вкусом! \n\n' \
                          'Если это вдруг не так,' \
                          ' то свяжитесь с нами по этому телефону' \
                          ' +7 978 656 44 55 и мы вам вернем деньги.'
    keyboard = [[InlineKeyboardButton("Назад к корзине",
                                      callback_data='back_to_cart')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(
        chat_id=job.context,
        text=alarm_clock_message,
        reply_markup=reply_markup)
    return 'CART'


def one_hour_timer(update, context, access_token):
    due = 60
    keyboard = [[InlineKeyboardButton("Назад к корзине",
                                      callback_data='back_to_cart')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.delete_message(
        chat_id=update.effective_chat.id,
        message_id=context.user_data['message_id']
    )

    id = context.user_data['pizzeria_id']
    slug = 'pizzeria'

    courier_tg_id = get_entry(access_token, slug, id)['data']['telegram_id']
    client_address = context.user_data['client_address']
    context.bot.send_message(
        chat_id=courier_tg_id,
        text=f'Это видит только курьер \n'
             f'Адрес клиента: {client_address}',
    )
    context.bot.send_location(
        chat_id=courier_tg_id,
        latitude=context.user_data['client_latitude'],
        longitude=context.user_data['client_longitude'])

    timer_message = context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Оплата успешно произведена \n '
             'Мы заботимся о своих клиентах чтобы они получали свежеприготовленную пиццу.\n'
             'Если через 1 час вам не привезут пиццу, то мы вернем вам деньги',
        reply_markup=reply_markup)
    context.user_data['timer_message_id'] = timer_message.message_id
    context.job_queue.run_once(send_alarm_clock_message,
                               due,
                               context=update.effective_chat.id)


def send_payment(update, context, provider_token):
    chat_id = update.effective_chat.id
    title = "Оплата заказа в пицца-Макс"
    description = f"Стоимость заказа - {context.user_data['cart_sum_num']}руб \n" \
                  f"Стоимость доставки - {context.user_data['delivery_tax']}руб"
    payload = "Custom-Payload"
    currency = "RUB"
    price = int(context.user_data['cart_sum_num']) + int(context.user_data['delivery_tax'])
    prices = [LabeledPrice("Test", price * 10)]

    context.bot.send_invoice(
        chat_id, title, description, payload, provider_token, currency, prices)


def precheckout_callback(update, context):
    query = update.pre_checkout_query
    if query.invoice_payload != 'Custom-Payload':
        query.answer(ok=False, error_message="Something went wrong...")
    else:
        query.answer(ok=True)


def successful_payment(update, context, access_token):
    if context.user_data['delivery_choice'] == 'delivery':
        return one_hour_timer(update, context, access_token)
    else:
        message = 'Оплата успешно произведена, ждем вас за пиццей'
        keyboard = [[InlineKeyboardButton("Назад к корзине",
                                          callback_data='back_to_cart')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            reply_markup=reply_markup)
        return 'CART'
