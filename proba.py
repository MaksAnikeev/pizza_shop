import environs
import redis
import requests
from geopy import distance
from datetime import datetime
from more_itertools import chunked
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, LabeledPrice, ShippingOption
from telegram.ext import (CallbackQueryHandler, CommandHandler, Filters,
                          MessageHandler, Updater, CommandHandler, PreCheckoutQueryHandler, ShippingQueryHandler,)
from moltin import (get_token, get_product_params,
                    get_products_prices, get_product_files, create_client,
                    get_products_names, get_products_params, add_item_to_cart,
                    get_products_from_cart, get_cart_params, delete_item_from_cart,
                    get_entries, fill_fieds, get_entrie)
from pprint import pprint


_database = None

# env = environs.Env()
# env.read_env()
# client_id = env.str("CLIENT_ID")
# client_secret = env.str("CLIENT_SECRET")


def get_token(client_id, client_secret):
    """
    Получить токен с Moltin и время начала его действия
    """
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
    }
    response = requests.post('https://api.moltin.com/oauth/access_token',
                             data=data)
    response.raise_for_status()
    token_params = response.json()
    access_token = token_params['access_token']
    token_expires = token_params['expires']
    return access_token, token_expires

# access_token, token_expires = get_token(client_id, client_secret)

# print(access_token)


def add_item_to_cart(access_token, product_id, quantity, cart_name):
    """
    Добавить продукт в корзину
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    json_data = {
        'data': {
            'type': 'cart_item',
            'id': product_id,
            "quantity": quantity,
        }
    }
    response = requests.post(f'https://api.moltin.com/v2/carts/{cart_name}/items',
                             headers=headers,
                             json=json_data)
    return response.json()


def create_cart(access_token, name):
    """
    Создание пользовательской корзины
    """
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.get(f'https://api.moltin.com/v2/carts/{name}', headers=headers)
    response.raise_for_status()
    return response.json()

# name = 704859099
# pprint(create_cart(access_token, name))


# product_id = 'd2e8df81-cf59-4675-94d6-2dd721f295b5'
# quantity = 2
# cart_name = 704859099
# # pprint(add_item_to_cart(access_token, product_id, quantity, cart_name))
# headers = {
#         'Authorization': f'Bearer {access_token}'
#     }
# requests.delete('https://api.moltin.com/v2/carts/704859099', headers=headers)

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

# address = 'Москва, Старый Арбат, 4'
# api_yandex_key = env('API_YANDEX_KEY')
# lon, lat = fetch_coordinates(api_yandex_key, address)
# client_coordinates = (lon, lat)

def get_entries(access_token, slug):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/flows/{slug}/entries', headers=headers)
    return response.json()['data']

slug = 'pizzeria'

# pizzerias_params = get_entries(access_token, slug)
# pprint(pizzerias_params)

def get_user_dictance(user):
    return user['distance']

def get_min_distance(client_coordinates, pizzerias_params):
    distance_to_client = []
    for pizzeria in pizzerias_params:
        pizzeria_longitude = pizzeria['pizzeria_longitude']
        pizzeria_latitude = pizzeria['pizzeria_latitude']
        pizzeria_address = (pizzeria_longitude, pizzeria_latitude)
        client_distance = round(distance.distance(client_coordinates, pizzeria_address).km, 2)
        client_params = {'pizzeria_address': pizzeria['pizzeria_address'],
                         'distance': client_distance,
                         'pizzeria_id': pizzeria['id']}
        distance_to_client.append(client_params)
    # pprint(distance_to_client)
    distance_params = min(distance_to_client, key=get_user_dictance)
    pizzeria_full_address = distance_params['pizzeria_address']
    distance_to_client = distance_params['distance']
    pizzeria_id = distance_params['pizzeria_id']
    return pizzeria_full_address, pizzeria_id, distance_to_client

# pizzeria_full_address, pizzeria_id, distance_to_client = get_min_distance(client_coordinates, pizzerias_params)
# print(pizzeria_full_address, pizzeria_id, distance_to_client)

flow_slug = 'customer_address'
first_field = 'client_id'
first_value = 705948833
second_field = 'client_longitude'
second_value = 50.74653
third_field = 'client_latitude'
third_value = 35.977373

# print(fill_fieds(access_token, flow_slug,
#                    first_field, first_value,
#                    second_field, second_value,
#                    third_field, third_value))



# def callback_alarm(context, job):
#     context.bot.send_message(chat_id=job.context, text='BEEP')
#
# def timer(update, context, job_queue):
#     due = 6
#     context.bot.send_message(chat_id=update.effective_chat.id,
#                          text='Setting a timer for 1 minute!')
#     job_queue.run_once(callback_alarm, due, context=update.effective_chat.id)
#
#
# if __name__ == '__main__':
#     env = environs.Env()
#     env.read_env()
#
#     token = env.str("TG_BOT_TOKEN")
#     updater = Updater(token)
#     dispatcher = updater.dispatcher
#
#     dispatcher.add_handler(CommandHandler('timer', timer, pass_job_queue=True))
#
#     updater.start_polling()
#     updater.idle()


# def start(update, context):
#     context.bot.send_message(chat_id=update.effective_chat.id,
#                          text='Начали')
#     return timer(update, context)
#
#
# def callback_alarm(context):
#     job = context.job
#     context.bot.send_message(chat_id=job.context, text='BEEP')
#
# def timer(update, context):
#     due = 6
#     context.bot.delete_message(
#         chat_id=update.message.chat_id,
#         message_id=update.message.message_id+1
#     )
#     context.bot.send_message(chat_id=update.effective_chat.id,
#                          text='Setting a timer for 1 minute!')
#     context.job_queue.run_once(callback_alarm, due, context=update.effective_chat.id)


# def start_with_shipping_callback(update, bot):
#     chat_id = update.message.chat_id
#     title = "Покупка пиццы"
#     description = "Вы выбрали все пиццы"
#     payload = "Custom-Payload"
#     start_parameter = "test-payment"
#     currency = "USD"
#     price = 1
#     prices = [LabeledPrice("Test", price * 100)]
#     print([p.to_dict() for p in prices])
#     provider_token = env.str("PAYMENT_TRANZZO_TOKEN")
#
#     bot.send_invoice(chat_id, title, description, payload,
#                     provider_token, start_parameter, currency, prices,
#                     )
#
#
# if __name__ == '__main__':
#     env = environs.Env()
#     env.read_env()
#
#     provider_token = env.str("PAYMENT_TRANZZO_TOKEN")
#     token = env.str("TG_BOT_TOKEN")
#     bot = Bot(token)
#     updater = Updater(token)
#     dispatcher = updater.dispatcher
#
#     # print(LabeledPrice("Test", 5 * 100).to_dict())
#
#     dispatcher.add_handler(CommandHandler('start', start_with_shipping_callback))
#
#     updater.start_polling()
#     updater.idle()

# import environs
# import requests
# from telegram import Bot, LabeledPrice, ShippingOption
# from telegram.ext import (Updater, CommandHandler, PreCheckoutQueryHandler, ShippingQueryHandler,)
#
#
# env = environs.Env()
# env.read_env()
#
# token = env.str("TG_BOT_TOKEN")
# bot = Bot(token=token)
# updater = Updater(token=token, use_context=True)
# dispatcher = updater.dispatcher
#
# def start_callback(update, context):
#     msg = "Use /shipping to get an invoice for shipping-payment, "
#     msg += "or /noshipping for an invoice without shipping."
#     update.message.reply_text(msg)
#
# def start_without_shipping_callback(update, context):
#     chat_id = update.message.chat_id
#     title = "Payment Example"
#     description = "Payment Example using python-telegram-bot"
#     payload = "Custom-Payload"
#     provider_token = env.str("PAYMENT_TRANZZO_TOKEN")
#     start_parameter = "test-payment"
#     currency = "USD"
#     price = 1
#     prices = [LabeledPrice("Test", price * 100)]
#     # print(prices_label[0].to_dict())
#
#     context.bot.send_invoice(chat_id, title, description, payload,
#                             provider_token, start_parameter, currency, prices)
#
#
# dp = updater.dispatcher
# dp.add_handler(CommandHandler("start", start_callback))
# dp.add_handler(CommandHandler("noshipping", start_without_shipping_callback))
#
# updater.start_polling()
# updater.idle()
import logging

from telegram import LabeledPrice, ShippingOption, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    PreCheckoutQueryHandler,
    ShippingQueryHandler,
    CallbackContext,
)

# Enable logging
# logging.basicConfig(
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
# )
#
# logger = logging.getLogger(__name__)


def start_callback(update, context):
    msg = (
        "Use /shipping to get an invoice for shipping-payment, or /noshipping for an "
        "invoice without shipping."
    )
    update.message.reply_text(msg)


def start_with_shipping_callback(update, context):
    chat_id = update.message.chat_id
    title = "Заказ в пицерии Макс "
    description = "Ваш заказ 100 пицц разных вкусов"
    payload = "Custom-Payload"
    currency = "RUB"
    price = 1234
    prices = [LabeledPrice("Test", price * 100)]
    context.bot.send_invoice(
        chat_id,
        title,
        description,
        payload,
        provider_token,
        currency,
        prices,
        need_name=True,
        need_phone_number=True,
        need_email=True,
        need_shipping_address=True,
        is_flexible=True,
    )


def start_without_shipping_callback(update, context):
    chat_id = update.message.chat_id
    title = "Payment Example"
    description = "Payment Example using python-telegram-bot"
    payload = "Custom-Payload"
    currency = "RUB"
    price = 123
    prices = [LabeledPrice("Test", price * 100)]

    context.bot.send_invoice(
        chat_id, title, description, payload, provider_token, currency, prices
    )


def shipping_callback(update: Update, context: CallbackContext) -> None:
    """Answers the ShippingQuery with ShippingOptions"""
    query = update.shipping_query
    # check the payload, is this from your bot?
    if query.invoice_payload != 'Custom-Payload':
        # answer False pre_checkout_query
        query.answer(ok=False, error_message="Something went wrong...")
        return

    # First option has a single LabeledPrice
    options = [ShippingOption('1', 'Shipping Option A', [LabeledPrice('A', 100)])]
    # second option has an array of LabeledPrice objects
    price_list = [LabeledPrice('B1', 150), LabeledPrice('B2', 200)]
    options.append(ShippingOption('2', 'Shipping Option B', price_list))
    query.answer(ok=True, shipping_options=options)


# after (optional) shipping, it's the pre-checkout
def precheckout_callback(update: Update, context: CallbackContext) -> None:
    """Answers the PreQecheckoutQuery"""
    query = update.pre_checkout_query
    # check the payload, is this from your bot?
    if query.invoice_payload != 'Custom-Payload':
        # answer False pre_checkout_query
        query.answer(ok=False, error_message="Something went wrong...")
    else:
        query.answer(ok=True)


# finally, after contacting the payment provider...
def successful_payment_callback(update: Update, context: CallbackContext) -> None:
    """Confirms the successful payment."""
    # do something after successfully receiving payment?
    update.message.reply_text("Thank you for your payment!")


if __name__ == '__main__':
    env = environs.Env()
    env.read_env()
    provider_token = env.str("PAYMENT_UKASSA_TOKEN")
    token = env.str("TG_BOT_TOKEN")
    updater = Updater(token)
    dispatcher = updater.dispatcher

    # simple start function
    dispatcher.add_handler(CommandHandler("start", start_callback))

    # Add command handler to start the payment invoice
    dispatcher.add_handler(CommandHandler("shipping", start_with_shipping_callback))
    dispatcher.add_handler(CommandHandler("noshipping", start_without_shipping_callback))

    # Optional handler if your product requires shipping
    dispatcher.add_handler(ShippingQueryHandler(shipping_callback))

    # Pre-checkout handler to final check
    dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))

    # Success! Notify your user!
    dispatcher.add_handler(MessageHandler(Filters.successful_payment, successful_payment_callback))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
