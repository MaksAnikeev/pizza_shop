import os

import requests
import environs
from flask import Flask, request
from datetime import datetime
from textwrap import dedent
import redis
from moltin import (add_item_to_cart, create_client, delete_item_from_cart,
                    fill_fieds, get_cart_params, get_entry, get_entries,
                    get_product_files, get_product_params,
                    get_products_from_cart, get_products_names,
                    get_products_params, get_products_prices, get_token,
                    get_hierarchy_children)
from pprint import pprint

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
db.set('access_token', access_token)
db.set('token_expires', token_expires)
db.set('price_list_id', price_list_id)
db.set('node_id_basic', node_id_basic)
db.set('hierarchy_id', hierarchy_id)


def check_token(token_expires):
    timestamp_now = datetime.now().timestamp()
    delta = token_expires - timestamp_now
    return delta > 0


@app.route('/', methods=['GET'])
def verify():
    """
    При верификации вебхука у Facebook он отправит запрос на этот адрес. На него нужно ответить VERIFY_TOKEN.
    """
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
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
    pprint(data)
    if data["object"] == "page":
        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:
                if messaging_event.get("message"):
                    sender_id = messaging_event["sender"]["id"]
                    recipient_id = messaging_event["recipient"]["id"]
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
    db = get_database_connection()
    access_token = db.get('access_token')
    price_list_id = db.get('price_list_id').replace(' ', '')

    elements = create_products_description(access_token, price_list_id)

    params = {"access_token": env.str("PAGE_ACCESS_TOKEN")}
    headers = {"Content-Type": "application/json"}

    json_data = {
        "recipient": {
            "id": sender_id
        },
        "message":{
            "attachment":{
              "type":"template",
              "payload":{
                "template_type":"generic",
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



def create_products_description(access_token, price_list_id):
    db = get_database_connection()
    if not db.get('node_id'):
        node_id = db.get('node_id_basic')
    else:
        node_id = db.get('node_id')
    hierarchy_id = db.get('hierarchy_id')
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
                product_price = "%.2f" % (price['attributes']['currencies']['RUB']['amount']/100)

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


def add_product_to_cart(sender_id, message_text):
    facebook_id = sender_id
    access_token = db.get('access_token')
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
        return 'START'


def show_cart(sender_id, message_text):
    facebook_id = sender_id
    access_token = db.get('access_token')

    products_in_cart_params = get_products_from_cart(access_token=access_token,
                                                     cart_name=facebook_id)

    cart_params = get_cart_params(access_token=access_token,
                                  cart_name=facebook_id)
    cart_sum_num = cart_params["data"]["meta"]["display_price"]["with_tax"]["formatted"]
    cart_sum_number = cart_sum_num.replace('.', '').\
        replace(' руб', '').replace(',00', '').replace(' ', '')
    db.set('cart_sum_num', cart_sum_number)
    cart_sum = dedent(f'''
            ИТОГО {cart_sum_num}
            ''').replace("    ", "")
    db.set('cart_sum', cart_sum)

    price_list_id = db.get('price_list_id').replace(' ', '')
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
        product_description = product_params['description']
        product_id = product_params['product_id']
        product_price = 'нет в наличие'
        for price in products_prices['data']:
            if price['attributes']['sku'] == product_sku:
                product_price = "%.2f" % (price['attributes']['currencies']['RUB']['amount']/100)

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
                            "title": "Добавить еще одну",
                            "payload": product_id
                          },
                          {
                            "type": "postback",
                            "title": "Убрать из корзины",
                            "payload": product_id
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



def handle_users_reply(sender_id, message_text):
    db = get_database_connection()
    token_expires = int(db.get('token_expires').replace(' ', ''))
    if not check_token(token_expires):
        access_token, token_expires = get_token(client_id, client_secret)
        db.set('access_token', access_token)
        db.set('token_expires', token_expires)

    states_functions = {
        'START': send_keyboard,
        'CART': show_cart,
        'DISCOUNT': send_discount,
        'ADD_TO_CART': add_product_to_cart,
    }
    recorded_state = db.get(f'facebook-{sender_id}')
    print(recorded_state)
    if not recorded_state or recorded_state not in states_functions.keys():
        user_state = "START"
        print(1)
    elif message_text == "Акции":
        user_state = "DISCOUNT"
        print(2)
    elif message_text == "Корзина":
        user_state = "CART"
        print(3)
    elif message_text == "Основное меню" or message_text == "Особые" or\
            message_text == "Острые" or message_text == "Сытные":
        user_state = "START"
        print(4)
    elif message_text == 'Добавить в корзину':
        user_state = "ADD_TO_CART"
        print(5)
    else:
        user_state = recorded_state
        print(6)
    state_handler = states_functions[user_state]
    next_state = state_handler(sender_id, message_text)
    print(states_functions[user_state])
    db.set(f'facebook-{sender_id}', next_state)
    print(7)


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
    # hierarchy_id = '5644aa5d-cf68-4dde-9fe0-3eb2c6118bc7'
    # node_id_hot = '86028403-e62b-4992-b39f-d0e08974cca8'
    # node_id_hearty = 'd3e32c20-3269-475f-85ee-d97ce96b6437'
    # node_id_special = '53911d3a-0e99-4905-bdb9-3f9bc182e4d2'
    # node_id_basic = 'b41d0763-08db-48a5-913a-a359995be831'

    # headers = {
    #     'Authorization': f'Bearer {access_token}',
    # }
    #
    # response = requests.get(
    #     f'https://api.moltin.com/pcm/hierarchies/{hierarchy_id}/children',
    #     headers=headers,
    # )
    # pprint(response.json())



