import argparse
from textwrap import dedent

import environs
import redis
import requests
import time
from geopy import distance
from datetime import datetime
from more_itertools import chunked
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import (CallbackQueryHandler, CommandHandler, Filters,
                          MessageHandler, Updater)
from moltin import (get_token, get_product_params,
                    get_products_prices, get_product_files, create_client,
                    get_products_names, get_products_params, add_item_to_cart,
                    get_products_from_cart, get_cart_params, delete_item_from_cart,
                    get_entries, fill_fieds, get_entrie)
from pprint import pprint

_database = None


def check_token(token_expires):
    timestamp_now = datetime.now().timestamp()
    delta = token_expires - timestamp_now
    if delta > 0:
        return True


def start(update, context):
    if not update.callback_query:
        context.user_data['tg_id'] = update.message.from_user.id

    keyboard = [[InlineKeyboardButton("Магазин", callback_data='store'),
                 InlineKeyboardButton("Моя корзина", callback_data='cart')]]

    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        update.message.reply_text('Привет! Сделай выбор:', reply_markup=reply_markup)
        return 'MAIN_MENU'
    except:
        query = update.callback_query
        context.bot.edit_message_text(text='Привет! Сделай выбор:',
                                      chat_id=query.message.chat_id,
                                      message_id=query.message.message_id,
                                      reply_markup=reply_markup)
        return 'MAIN_MENU'


def send_products_keyboard(update, context):
    query = update.callback_query
    access_token = dispatcher.bot_data['access_token']
    products_params = get_products_params(access_token)
    products_names = get_products_names(products_params)
    keyboard = list(chunked(products_names, 2))
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        context.bot.edit_message_text(
            text='Выбери товар из магазина:',
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            reply_markup=reply_markup
        )
        return "PRODUCT"
    except:
        context.bot.send_message(
            text='Выбери товар из магазина:',
            chat_id=query.message.chat_id,
            reply_markup=reply_markup
        )

        context.bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id
        )
        return "PRODUCT"


def send_product_description(update, context):
    query = update.callback_query
    if query.data == 'main_menu':
        return start(update, context)

    keyboard = [[InlineKeyboardButton("1шт", callback_data='1pc'),
                 InlineKeyboardButton("2шт", callback_data='2pc'),
                 InlineKeyboardButton("4шт", callback_data='4pc')],
                [InlineKeyboardButton("Назад", callback_data='back')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    product_id = query.data
    context.user_data['product_id'] = product_id

    access_token = dispatcher.bot_data['access_token']
    product_params = get_product_params(access_token, product_id)
    product_name = product_params['data']['attributes']['name']
    product_description = product_params['data']['attributes']['description']
    product_sku = product_params['data']['attributes']['sku']

    context.user_data['product_name'] = product_name
    price_list_id = dispatcher.bot_data['price_list_id']

    products_prices = get_products_prices(
        access_token,
        price_list_id=price_list_id
    )

    for price in products_prices['data']:
        if price['attributes']['sku'] == product_sku:
            product_price = "%.2f" % (price['attributes']['currencies']['RUB']['amount']/100)

    product_message = dedent(f"""\
                            <b>Вы выбрали продукт:</b>
                            {product_name}
                            <b>Описание:</b>
                            {product_description}
                            <b>Цена в за единицу товара:</b>
                            {product_price}руб
                            """).replace("    ", "")
    try:
        product_file_id = product_params['data']['relationships']['main_image']['data']['id']
        access_token = dispatcher.bot_data['access_token']
        product_image_params = get_product_files(access_token,
                                                 file_id=product_file_id)
        product_image_url = product_image_params['data']['link']['href']
        product_image = requests.get(product_image_url)
        product_image.raise_for_status()

        query.message.reply_photo(
            product_image.content,
            caption=product_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML)

        context.bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id
        )
        return "ADD_CART"

    except:
        context.bot.edit_message_text(
            text=product_message,
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML)
        return "ADD_CART"


def add_product_to_cart(update, context):
    query = update.callback_query
    if query.data == 'back':
        return send_products_keyboard(update, context)

    tg_id = context.user_data['tg_id']
    access_token = dispatcher.bot_data['access_token']
    product_id = context.user_data['product_id']
    product_quantity = int(query.data.replace('pc', ''))

    keyboard = [[InlineKeyboardButton("Назад", callback_data='back')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    response = add_item_to_cart(access_token=access_token,
                                product_id=product_id,
                                quantity=product_quantity,
                                cart_name=tg_id)

    if response.ok:
        product_name = context.user_data['product_name']
        add_cart_message = dedent(
            f"""\
            <b>Выбранный вами продукт:</b>
            {product_name}
             <b>В количестве:</b>
            {product_quantity}шт
            <b>Успешно добавлен в вашу корзину</b>
            """).replace("    ", "")
        try:
            context.bot.edit_message_text(
                text=add_cart_message,
                chat_id=query.message.chat_id,
                message_id=query.message.message_id,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            return "STORE"
        except:
            context.bot.send_message(
                text=add_cart_message,
                chat_id=query.message.chat_id,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )

            context.bot.delete_message(
                chat_id=query.message.chat_id,
                message_id=query.message.message_id
            )
            return "STORE"


def show_cart(update, context):
    query = update.callback_query
    tg_id = context.user_data['tg_id']
    access_token = dispatcher.bot_data['access_token']

    products_in_cart_params = get_products_from_cart(access_token=access_token,
                                                     cart_name=tg_id)
    cart_products = [dedent(f'''
        {count + 1}. {product["name"]}
        ЦЕНА ЗА ЕДИНИЦУ: {"%.2f" % (product["unit_price"]["amount"]/100)} {product["unit_price"]["currency"]}
        КОЛИЧЕСТВО: {product["quantity"]} шт
        СУММА: {"%.2f" % (product["value"]["amount"]/100)} {product["value"]["currency"]}
        ''').replace("    ", "")
        for count, product in enumerate(products_in_cart_params['data'])
        ]

    cart_params = get_cart_params(access_token=access_token,
                                  cart_name=tg_id)
    cart_sum = dedent(f'''
            ИТОГО {cart_params["data"]["meta"]["display_price"]["with_tax"]["formatted"]}
            ''').replace("    ", "")
    context.user_data['cart_sum'] = cart_sum
    cart_products.append(cart_sum)

    products_in_cart = ' '.join(cart_products)

    keyboard = [
        [InlineKeyboardButton("Оплатить", callback_data='payment')],
        [InlineKeyboardButton("Главное меню", callback_data='main_menu')]
    ]
    for product in products_in_cart_params['data']:
        button_name = f'Убрать из корзины {product["name"]}'
        button_id = product['id']
        button = [InlineKeyboardButton(button_name,
                                       callback_data=f'delete {button_id}')]
        keyboard.insert(0, button)
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.edit_message_text(
        text=products_in_cart,
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup)
    return 'CART'


def delete_product_from_cart(update, context):
    product_id = context.user_data['delete_product_id']
    access_token = dispatcher.bot_data['access_token']
    tg_id = context.user_data['tg_id']

    delete_item_from_cart(access_token=access_token,
                       cart_name=tg_id,
                       product_id=product_id)

    return show_cart(update, context)


def ask_email(update, context):
    query = update.callback_query
    cart_sum = context.user_data['cart_sum']
    payment_message = f'Сумма заказа составляет {cart_sum}\n'\
                      f'Напишите ваш емейл. ' \
                      f'С вами свяжется наш специалист для уточнения вопроса оплаты'

    keyboard = [[InlineKeyboardButton("Назад к корзине",
                                      callback_data='back_to_cart')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.edit_message_text(
        text=payment_message,
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup)
    return 'GET_EMAIL'


def get_email(update, context):
    query = update.callback_query
    if query and query.data == 'back_to_cart':
        return show_cart(update, context)

    access_token = dispatcher.bot_data['access_token']

    email = update.message.text
    keyboard = [[InlineKeyboardButton("Назад к корзине",
                                      callback_data='back_to_cart')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    user_fullname = str(update.message.from_user['first_name']) + ' ' + str(
        update.message.from_user['last_name'])

    response = create_client(
        access_token=access_token,
        client_name=user_fullname,
        email=email
    )
    if response.ok or response.json()['errors'][0]['title'] == 'Duplicate email':
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'Вы нам прислали {email}\n'
                 f'В ближайшее время с вами свяжется наш специалист\n'
                 f'Пришлите нам ваш адрес текстом или геолокацию, для определения куда вам доставить пиццу',
            reply_markup=reply_markup
        )
        query = update.callback_query
        if query and query.data == 'back_to_cart':
            return show_cart(update, context)
        return 'GET_ADDRESS'

    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Вы ввели некорректный e-mail, попробуйте еще раз',
            reply_markup=reply_markup
        )


def get_address(update, context):
    query = update.callback_query
    if query:
        return handle_button(update, context)

    access_token = dispatcher.bot_data['access_token']
    address = update.message.text
    context.user_data['client_address'] = address
    try:
        try:
            message = update.message
            lat = message.location.latitude
            lon = message.location.longitude
            client_coordinates = (lon, lat)
        except:
            lon, lat = fetch_coordinates(api_yandex_key, address)
            client_coordinates = (lon, lat)

        keyboard = [
            [InlineKeyboardButton("Доставка", callback_data='delivery'),
             InlineKeyboardButton("Самовывоз", callback_data='pickup')],
            [InlineKeyboardButton("Назад к корзине",
                                          callback_data='back_to_cart')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        flow_slug = 'customer_address'
        first_field = 'client_id'
        first_value = context.user_data['tg_id']
        second_field = 'client_longitude'
        second_value = lon
        third_field = 'client_latitude'
        third_value = lat
        entry_client_id = fill_fieds(access_token, flow_slug,
                   first_field, first_value,
                   second_field, second_value,
                   third_field, third_value, )
        context.user_data['entry_client_id'] = entry_client_id

        slug = 'pizzeria'
        pizzerias_params = get_entries(access_token, slug)
        pizzeria_address, pizzeria_id, distance_to_client = get_min_distance(client_coordinates, pizzerias_params)
        context.user_data['pizzeria_address'] = pizzeria_address
        context.user_data['pizzeria_id'] = pizzeria_id

        if distance_to_client <= 0.5:
            message = f'Можете забрать пиццу из нашей пицерии неподалеку. Она всего в ' \
                      f'{distance_to_client*1000}м от вас, адрес {pizzeria_address} \n\n' \
                      f'А можем и бесплатно доставить, нам не сложно'
        elif distance_to_client <= 5:
            message = f'Ваша пицца будет готовится по адресу: {pizzeria_address}. \n' \
                      f'Придется к вам ехать на самокате, доставка будет 100р'
        elif distance_to_client <= 20:
            message = f'Ваша пицца будет готовится по адресу: {pizzeria_address}. \n' \
                      f'Придется к вам ехать на машине, доставка будет 300р'
        elif distance_to_client > 20:
            message = f'Ваша пицца будет готовится по адресу: {pizzeria_address}. \n' \
                      f'Вы находитесь на расстоянии {distance_to_client}км. \n Так далеко мы не возим.' \
                      f'Можете забрать самовывозом.'

        delivery_massage = context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message,
                reply_markup=reply_markup
            )
        context.user_data['delivery_massage'] = delivery_massage.message_id
        return 'CART'
    except:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Вы ввели некорректный адрес, попробуйте ввести заново или прислать геопозицию',
        )


def send_pickup_message(update, context):
    keyboard = [[InlineKeyboardButton("Назад к корзине",
                              callback_data='back_to_cart')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    pizzeria_address = context.user_data['pizzeria_address']
    message = f'Ваша пицца будет готова через 20 минут.\n' \
              f'Вы можете забрать ее по адресу {pizzeria_address} \n'
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=reply_markup
    )
    return 'CART'


def send_delivery_message(update, context):
    entry_client_id = context.user_data['entry_client_id']
    pizzeria_address = context.user_data['pizzeria_address']
    access_token = dispatcher.bot_data['access_token']

    slug = 'customer_address'
    id = entry_client_id
    client_params = get_entrie(access_token, slug, id)
    context.user_data['client_longitude'] = client_params['data']['client_longitude']
    context.user_data['client_latitude'] = client_params['data']['client_latitude']

    message = f'Ваша пицца готовится по адресу {pizzeria_address}\n' \
              f'Курьер привезет ваш заказ через 60 минут \n'
    ready_message = context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
    )
    context.user_data['message_id'] = ready_message.message_id

    context.bot.delete_message(
        chat_id=update.effective_chat.id,
        message_id=context.user_data['delivery_massage']
    )

    return one_hour_timer(update, context)


def handle_button(update, context):
    query = update.callback_query
    if query.data == 'store':
        return send_products_keyboard(update, context)

    elif query.data == 'cart':
        return show_cart(update, context)

    elif query.data == 'main_menu':
        return start(update, context)

    elif query.data == 'back_to_cart':
        return show_cart(update, context)

    elif query.data == 'pickup':
        return send_pickup_message(update, context)

    elif query.data == 'delivery':
        return send_delivery_message(update, context)

    elif 'delete' in query.data:
        product_id = query.data.replace('delete ', '')
        context.user_data['delete_product_id'] = product_id
        return delete_product_from_cart(update, context)

    elif 'payment' in query.data:
        return ask_email(update, context)

    elif context.user_data['timer_message_id']:
        context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=context.user_data['timer_message_id']
        )


def handle_users_reply(update, context):
    db = get_database_connection()
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return

    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id)
    token_expires = dispatcher.bot_data['token_expires']
    if not check_token(token_expires):
        access_token, token_expires = get_token(client_id, client_secret)
        dispatcher.bot_data['access_token'] = access_token
        dispatcher.bot_data['token_expires'] = token_expires
    states_functions = {
        'START': start,
        'MAIN_MENU': handle_button,
        'STORE': send_products_keyboard,
        "PRODUCT": send_product_description,
        'CART': handle_button,
        "ADD_CART": add_product_to_cart,
        'GET_EMAIL': get_email,
        'GET_ADDRESS': get_address
    }
    state_handler = states_functions[user_state]
    try:
        next_state = state_handler(update, context)
        db.set(chat_id, next_state)
    except Exception as err:
        print(err)


def get_database_connection():
    global _database
    if _database is None:
        database_password = env.str("DATABASE_PASSWORD")
        database_host = env.str("DATABASE_HOST")
        database_port = env.str("DATABASE_PORT")
        _database = redis.StrictRedis(host=database_host,
                                      port=database_port,
                                      password=database_password,
                                      charset="utf-8",
                                      decode_responses=True)
    return _database


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
        client_distance = round(distance.distance(client_coordinates, pizzeria_address).km, 2)
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
    alarm_clock_message = 'Приятного аппетита! Надеемся что пицца к вам пришла вовремя ' \
                          'и вы уже наслаждаетесь ее вкусом! \n\n' \
                          'Если это вдруг не так, то свяжитесь с нами по этому телефону +7 978 656 44 55' \
                          'и мы вам вернем деньги.'
    keyboard = [[InlineKeyboardButton("Назад к корзине",
                                      callback_data='back_to_cart')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(
        chat_id=job.context,
        text=alarm_clock_message,
        reply_markup=reply_markup)
    return 'CART'


def one_hour_timer(update, context):
    time.sleep(10)
    due = 20
    keyboard = [[InlineKeyboardButton("Назад к корзине",
                                      callback_data='back_to_cart')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.delete_message(
        chat_id=update.effective_chat.id,
        message_id=context.user_data['message_id']
    )

    id = context.user_data['pizzeria_id']
    slug = 'pizzeria'
    courier_tg_id = get_entrie(access_token, slug, id)['data']['telegram_id']
    client_address = context.user_data['client_address']
    context.bot.send_message(
        chat_id=courier_tg_id,
        text=f'Аддрес клиента: {client_address}',
    )
    context.bot.send_location(
        chat_id=courier_tg_id,
        latitude=context.user_data['client_longitude'],
        longitude=context.user_data['client_longitude'])

    timer_message = context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Мы заботимся о своих клиентах чтобы они получали свежеприготовленную пиццу.\n'
                                  'Если через 1 час вам не привезут пиццу, то мы вернем вам деньги',
        reply_markup=reply_markup)
    context.user_data['timer_message_id'] = timer_message.message_id
    context.job_queue.run_once(send_alarm_clock_message, due, context=update.effective_chat.id)
    return 'CART'


if __name__ == '__main__':
    env = environs.Env()
    env.read_env()

    token = env.str("TG_BOT_TOKEN")
    updater = Updater(token)
    dispatcher = updater.dispatcher

    client_id = env.str("CLIENT_ID")
    client_secret = env.str("CLIENT_SECRET")
    price_list_id = env.str("PRICE_LIST_ID")
    api_yandex_key = env('API_YANDEX_KEY')
    access_token, token_expires = get_token(client_id, client_secret)
    dispatcher.bot_data['access_token'] = access_token
    dispatcher.bot_data['token_expires'] = token_expires
    dispatcher.bot_data['price_list_id'] = price_list_id

    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.location, get_address))
    updater.dispatcher.add_handler(CallbackQueryHandler(handle_button))

    updater.start_polling()
    updater.idle()
