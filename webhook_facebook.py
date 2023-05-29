import json
from datetime import datetime
from textwrap import dedent

import environs
import redis
import requests
from flask import Flask, request

from moltin import (add_item_to_cart, delete_item_from_cart, get_cart_params,
                    get_hierarchy_children, get_product_files,
                    get_product_params, get_products_from_cart,
                    get_products_prices, get_token)


app = Flask(__name__)

_database = None

env = environs.Env()
env.read_env()
client_id = env.str("CLIENT_ID")
client_secret = env.str("CLIENT_SECRET")
price_list_id = env.str("PRICE_LIST_ID")
node_id_basic = env.str("NODE_ID_BASIC")
node_id_hot = env.str("NODE_ID_HOT")
node_id_hearty = env.str("NODE_ID_HEARTY")
node_id_special = env.str("NODE_ID_SPETIAL")

hierarchy_id = env.str("HIERARCHY_ID")

access_token, token_expires = get_token(client_id, client_secret)


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


db = get_database_connection()


def check_token(token_expires):
    timestamp_now = datetime.now().timestamp()
    delta = token_expires - timestamp_now
    return delta > 0


@app.route('/', methods=['GET'])
def verify():
    """
    При верификации вебхука у Facebook он отправит запрос на этот адрес.
    На него нужно ответить VERIFY_TOKEN.
    """
    if request.args.get("hub.mode") == "subscribe" and\
            request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == env.str("VERIFY_TOKEN"):
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello Maks", 200


@app.route('/', methods=['POST'])
def webhook():
    """
    Основной вебхук, на который будут приходить сообщения от Facebook.
    """
    data = request.get_json()
    if data["object"] == "page":
        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:
                if messaging_event.get("message"):
                    sender_id = messaging_event["sender"]["id"]
                    message_text = messaging_event["message"]["text"]
                    handle_users_reply(sender_id, message_text)
                if messaging_event.get('postback'):
                    sender_id = messaging_event["sender"]["id"]
                    message_text = messaging_event['postback']['title']
                    if message_text == "Основное меню" or message_text == "Особые" or \
                            message_text == "Острые" or message_text == "Сытные":
                        db.set('node_id', messaging_event['postback']['payload'])
                    db.set('payload', messaging_event['postback']['payload'])
                    handle_users_reply(sender_id, message_text)
    return "ok", 200


def send_message(sender_id, message_text):
    params = {"access_token": env.str("PAGE_ACCESS_TOKEN")}
    headers = {"Content-Type": "application/json"}
    request_content = {
        "recipient": {
            "id": sender_id
        },
        "message": {
            "text": message_text
        }
    }
    response = requests.post(
        "https://graph.facebook.com/v2.6/me/messages",
        params=params, headers=headers, json=request_content
    )
    response.raise_for_status()
    return 'START'


def send_discount(sender_id, message_text):
    params = {"access_token": env.str("PAGE_ACCESS_TOKEN")}
    headers = {"Content-Type": "application/json"}
    request_content = {
        "recipient": {
            "id": sender_id
        },
        "message": {
            "text": 'тут будет описание акций'
        }
    }
    response = requests.post(
        "https://graph.facebook.com/v2.6/me/messages",
        params=params, headers=headers, json=request_content
    )
    response.raise_for_status()
    return 'START'


def send_keyboard(sender_id, message_text):
    global access_token

    if not db.get('node_id'):
        node_id = node_id_basic
        db.set('node_id', node_id)
    else:
        node_id = db.get('node_id')

    elements = get_keyboard_elements(access_token, price_list_id,
                                     node_id, message_text)

    params = {"access_token": env.str("PAGE_ACCESS_TOKEN")}
    headers = {"Content-Type": "application/json"}

    json_data = {
        "recipient": {
            "id": sender_id
        },
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": elements
                },
            },
        }
    }
    response = requests.post(
        "https://graph.facebook.com/v2.6/me/messages",
        params=params, headers=headers, json=json_data
    )
    response.raise_for_status()
    return "START"


def create_products_description(access_token, price_list_id, node_id):
    products_params = get_hierarchy_children(access_token, hierarchy_id,
                                             node_id=node_id)['data']
    products_prices = get_products_prices(
        access_token,
        price_list_id=price_list_id
    )
    keyboard_elements = [{"title": 'Меню',
                          "image_url": 'https://media-cdn.tripadvisor.com/media/photo-s/1b/5d/8e/89/caption.jpg',
                          "subtitle": 'Здесь вы можете выбрать один из вариантов',
                          "buttons": [
                              {
                                  "type": "postback",
                                  "title": "Корзина",
                                  "payload": "cart"
                              },
                              {
                                  "type": "postback",
                                  "title": "Акции",
                                  "payload": "discount"
                              },
                              {
                                  "type": "postback",
                                  "title": "Сделать заказ",
                                  "payload": "order"
                              }]}]
    for product_params in products_params:
        product_name = product_params['attributes']['name']
        product_description = product_params['attributes']['description']
        product_sku = product_params['attributes']['sku']
        product_id = product_params['id']
        product_price = 'нет в наличие'
        for price in products_prices['data']:
            if price['attributes']['sku'] == product_sku:
                product_price = "%.2f" % (price['attributes']['currencies']['RUB']['amount'] / 100)

        product_info = get_product_params(access_token, product_id)['data']

        if product_info['relationships']['main_image']['data']:
            product_file_id = product_info['relationships']['main_image']['data']['id']
            product_image_params = get_product_files(access_token,
                                                     file_id=product_file_id)
            product_image_url = product_image_params['data']['link']['href']
        else:
            product_image_url = 'https://golden-sun.ru/image/catalog/programs/brazilskaya-popka-kupon-aktsiya-skidka-deshevo-kiev.jpg'

        keyboard_element = {
            "title": product_name,
            "image_url": product_image_url,
            "subtitle": f'Цена {product_price} \n{product_description}',
            "buttons": [
                {
                    "type": "postback",
                    "title": "Добавить в корзину",
                    "payload": product_id
                }
            ]}
        keyboard_elements.append(keyboard_element)

    category_page = {"title": 'Не нашли нужную пиццу',
                     "image_url": 'https://primepizza.ru/uploads/position/large_0c07c6fd5c4dcadddaf4a2f1a2c218760b20c396.jpg',
                     "subtitle": 'Оставшиеся пиццы можно посмотреть выбрав одну'
                                 'из следующих категорий',
                     "buttons": [
                         {
                             "type": "postback",
                             "title": "Сытные",
                             "payload": node_id_hearty
                         },
                         {
                             "type": "postback",
                             "title": "Острые",
                             "payload": node_id_hot
                         },
                         {
                             "type": "postback",
                             "title": "Особые",
                             "payload": node_id_special
                         }]}
    keyboard_elements.append(category_page)
    main_meny_page = {"title": 'Если хотите вернуться к основному меню пицц',
                      "image_url": 'https://primepizza.ru/uploads/position/large_0c07c6fd5c4dcadddaf4a2f1a2c218760b20c396.jpg',
                      "buttons": [
                          {
                              "type": "postback",
                              "title": "Основное меню",
                              "payload": node_id_basic
                          }
                      ]}
    keyboard_elements.append(main_meny_page)
    return keyboard_elements


def get_keyboard_elements(access_token, price_list_id, node_id, message_text):
    if not db.get("keyboard_elements_main"):
        keyboard_elements = create_products_description(access_token,
                                                        price_list_id,
                                                        node_id)
        keyboard_elements_str = json.dumps(keyboard_elements)
        db.set("keyboard_elements_main", keyboard_elements_str)

        store_dt = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S.%f')
        db.set("keyboard_elements_main_time", store_dt)
        return keyboard_elements
    else:
        if message_text == "Основное меню":
            cached_keyboard_elements_str = db.get("keyboard_elements_main")
            cached_keyboard_elements = json.loads(cached_keyboard_elements_str)

            time_diff = datetime.now() - datetime.strptime(db.get("keyboard_elements_main_time"),
                                                           '%Y-%m-%d %H:%M:%S.%f')
            if time_diff.seconds / 60 > 20:
                keyboard_elements = create_products_description(access_token,
                                                                price_list_id,
                                                                node_id)
                keyboard_elements_str = json.dumps(keyboard_elements)
                db.set("keyboard_elements_main", keyboard_elements_str)
                store_dt = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S.%f')
                db.set("keyboard_elements_main_time", store_dt)
            else:
                keyboard_elements = cached_keyboard_elements
            return keyboard_elements

        elif message_text == "Особые":
            if not db.get("keyboard_elements_special"):
                keyboard_elements = create_products_description(access_token,
                                                                price_list_id,
                                                                node_id)
                keyboard_elements_str = json.dumps(keyboard_elements)
                db.set("keyboard_elements_special", keyboard_elements_str)
                store_dt = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S.%f')
                db.set("keyboard_elements_special_time", store_dt)
                return keyboard_elements
            cached_keyboard_elements_str = db.get("keyboard_elements_special")
            cached_keyboard_elements = json.loads(cached_keyboard_elements_str)

            time_diff = datetime.now() - datetime.strptime(db.get("keyboard_elements_special_time"),
                                                           '%Y-%m-%d %H:%M:%S.%f')
            if time_diff.seconds / 60 > 20:
                keyboard_elements = create_products_description(access_token,
                                                                price_list_id,
                                                                node_id)
                keyboard_elements_str = json.dumps(keyboard_elements)
                db.set("keyboard_elements_special", keyboard_elements_str)
                store_dt = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S.%f')
                db.set("keyboard_elements_special_time", store_dt)
            else:
                keyboard_elements = cached_keyboard_elements
            return keyboard_elements

        elif message_text == "Острые":
            if not db.get("keyboard_elements_hot"):
                keyboard_elements = create_products_description(access_token,
                                                                price_list_id,
                                                                node_id)
                keyboard_elements_str = json.dumps(keyboard_elements)
                db.set("keyboard_elements_hot", keyboard_elements_str)

                store_dt = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S.%f')
                db.set("keyboard_elements_hot_time", store_dt)
                return keyboard_elements
            cached_keyboard_elements_str = db.get("keyboard_elements_hot")
            cached_keyboard_elements = json.loads(cached_keyboard_elements_str)
            time_diff = datetime.now() - datetime.strptime(db.get("keyboard_elements_hot_time"),
                                                           '%Y-%m-%d %H:%M:%S.%f')
            if time_diff.seconds / 60 > 20:
                keyboard_elements = create_products_description(access_token,
                                                                price_list_id,
                                                                node_id)
                keyboard_elements_str = json.dumps(keyboard_elements)
                db.set("keyboard_elements_hot", keyboard_elements_str)
                store_dt = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S.%f')
                db.set("keyboard_elements_hot_time", store_dt)
            else:
                keyboard_elements = cached_keyboard_elements
            return keyboard_elements

        elif message_text == "Сытные":
            if not db.get("keyboard_elements_hearty"):
                keyboard_elements = create_products_description(access_token,
                                                                price_list_id,
                                                                node_id)
                keyboard_elements_str = json.dumps(keyboard_elements)
                db.set("keyboard_elements_hearty", keyboard_elements_str)
                store_dt = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S.%f')
                db.set("keyboard_elements_hearty_time", store_dt)
                return keyboard_elements
            cached_keyboard_elements_str = db.get("keyboard_elements_hearty")
            cached_keyboard_elements = json.loads(cached_keyboard_elements_str)
            time_diff = datetime.now() - datetime.strptime(db.get("keyboard_elements_hot_time"),
                                                           '%Y-%m-%d %H:%M:%S.%f')
            if time_diff.seconds / 60 > 20:
                keyboard_elements = create_products_description(access_token,
                                                                price_list_id,
                                                                node_id)
                keyboard_elements_str = json.dumps(keyboard_elements)
                db.set("keyboard_elements_hearty", keyboard_elements_str)
                store_dt = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S.%f')
                db.set("keyboard_elements_hearty_time", store_dt)
            else:
                keyboard_elements = cached_keyboard_elements
            return keyboard_elements
        else:
            cached_keyboard_elements_str = db.get("keyboard_elements_main")
            cached_keyboard_elements = json.loads(cached_keyboard_elements_str)
            time_diff = datetime.now() - datetime.strptime(db.get("keyboard_elements_main_time"),
                                                           '%Y-%m-%d %H:%M:%S.%f')
            if time_diff.seconds / 60 > 20:
                keyboard_elements = create_products_description(access_token,
                                                                price_list_id,
                                                                node_id)
                keyboard_elements_str = json.dumps(keyboard_elements)
                db.set("keyboard_elements_main", keyboard_elements_str)
                store_dt = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S.%f')
                db.set("keyboard_elements_main_time", store_dt)
            else:
                keyboard_elements = cached_keyboard_elements
            return keyboard_elements


def add_product_to_cart(sender_id, message_text):
    global access_token
    facebook_id = sender_id
    product_id = db.get('payload')

    response = add_item_to_cart(access_token=access_token,
                                product_id=product_id,
                                quantity=1,
                                cart_name=facebook_id)

    if response.ok:
        params = {"access_token": env.str("PAGE_ACCESS_TOKEN")}
        headers = {"Content-Type": "application/json"}
        request_content = {
            "recipient": {
                "id": sender_id
            },
            "message": {
                "text": 'Выбранный вами продукт успешно добавлен в вашу корзину'
            }
        }
        response = requests.post(
            "https://graph.facebook.com/v2.6/me/messages",
            params=params, headers=headers, json=request_content
        )
        response.raise_for_status()
        if message_text == 'Добавить еще одну':
            return show_cart(sender_id, message_text)
        return 'START'


def show_cart(sender_id, message_text):
    global access_token
    facebook_id = sender_id

    products_in_cart_params = get_products_from_cart(access_token=access_token,
                                                     cart_name=facebook_id)

    cart_params = get_cart_params(access_token=access_token,
                                  cart_name=facebook_id)
    cart_sum_num = cart_params["data"]["meta"]["display_price"]["with_tax"]["formatted"]
    cart_sum_number = cart_sum_num.replace('.', ''). \
        replace(' руб', '').replace(',00', '').replace(' ', '')
    db.set('cart_sum_num', cart_sum_number)
    cart_sum = dedent(f'''
            ИТОГО {cart_sum_num}
            ''').replace("    ", "")
    db.set('cart_sum', cart_sum)

    products_prices = get_products_prices(
        access_token,
        price_list_id=price_list_id)

    keyboard_elements = [{"title": 'Корзина',
                          "image_url": 'https://www.umi-cms.ru/images/cms/data/articles/korzina-internet-magazina.jpg',
                          "subtitle": f'Ваш заказ на сумму {cart_sum_num}',
                          "buttons": [
                              {
                                  "type": "postback",
                                  "title": "Самовывоз",
                                  "payload": "pickup"
                              },
                              {
                                  "type": "postback",
                                  "title": "Доставка",
                                  "payload": "delivery"
                              },
                              {
                                  "type": "postback",
                                  "title": "Основное меню",
                                  "payload": node_id_basic
                              }]}]

    for product_params in products_in_cart_params['data']:
        product_name = product_params['name']
        product_sku = product_params['sku']
        product_quantity = product_params['quantity']
        product_description = product_params['description']
        product_id = product_params['product_id']
        product_delete_id = product_params['id']
        product_price = 'нет в наличие'
        for price in products_prices['data']:
            if price['attributes']['sku'] == product_sku:
                product_price = "%.2f" % (price['attributes']['currencies']['RUB']['amount'] / 100)

        product_info = get_product_params(access_token, product_id)['data']

        if product_info['relationships']['main_image']['data']:
            product_file_id = product_info['relationships']['main_image']['data']['id']
            product_image_params = get_product_files(access_token,
                                                     file_id=product_file_id)
            product_image_url = product_image_params['data']['link']['href']
        else:
            product_image_url = 'https://golden-sun.ru/image/catalog/programs/brazilskaya-popka-kupon-aktsiya-skidka-deshevo-kiev.jpg'

        keyboard_element = {
            "title": product_name,
            "image_url": product_image_url,
            "subtitle": f'Цена за одну {product_price} '
                        f'\n Количество {product_quantity}'
                        f' \n{product_description}',
            "buttons": [
                {
                    "type": "postback",
                    "title": "Добавить еще одну",
                    "payload": product_id
                },
                {
                    "type": "postback",
                    "title": "Убрать из корзины",
                    "payload": product_delete_id
                }
            ]}
        keyboard_elements.append(keyboard_element)

    params = {"access_token": env.str("PAGE_ACCESS_TOKEN")}
    headers = {"Content-Type": "application/json"}

    json_data = {
        "recipient": {
            "id": sender_id
        },
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": keyboard_elements
                },
            },
        }
    }
    response = requests.post(
        "https://graph.facebook.com/v2.6/me/messages",
        params=params, headers=headers, json=json_data
    )
    response.raise_for_status()
    return "CART"


def delete_product_from_cart(sender_id, message_text):
    global access_token
    facebook_id = sender_id
    product_id = db.get('payload')

    delete_item_from_cart(access_token=access_token,
                          cart_name=facebook_id,
                          product_id=product_id)
    return show_cart(sender_id, message_text)


def handle_users_reply(sender_id, message_text):
    global token_expires
    global access_token
    if not check_token(token_expires):
        access_token, token_expires = get_token(client_id, client_secret)

    states_functions = {
        'START': send_keyboard,
        'CART': show_cart,
        'DISCOUNT': send_discount,
        'ADD_TO_CART': add_product_to_cart,
        'DEL_FROM_CART': delete_product_from_cart,
    }
    recorded_state = db.get(f'facebook-{sender_id}')
    if not recorded_state or recorded_state not in states_functions.keys():
        user_state = "START"
    elif message_text == "Акции":
        user_state = "DISCOUNT"
    elif message_text == "Корзина":
        user_state = "CART"
    elif message_text == "Основное меню" or message_text == "Особые" or \
            message_text == "Острые" or message_text == "Сытные":
        user_state = "START"
    elif message_text == 'Добавить в корзину' or\
            message_text == 'Добавить еще одну':
        user_state = "ADD_TO_CART"
    elif message_text == 'Убрать из корзины':
        user_state = "DEL_FROM_CART"
    else:
        user_state = "START"
    state_handler = states_functions[user_state]
    next_state = state_handler(sender_id, message_text)
    db.set(f'facebook-{sender_id}', next_state)


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


if __name__ == '__main__':
    app.run(debug=True)
