import os

import requests
import environs
from flask import Flask, request
from datetime import datetime
from moltin import (add_item_to_cart, create_client, delete_item_from_cart,
                    fill_fieds, get_cart_params, get_entry, get_entries,
                    get_product_files, get_product_params,
                    get_products_from_cart, get_products_names,
                    get_products_params, get_products_prices, get_token,
                    get_hierarchy_children)
from pprint import pprint

app = Flask(__name__)
env = environs.Env()
env.read_env()
client_id = env.str("CLIENT_ID")
client_secret = env.str("CLIENT_SECRET")

access_token, token_expires = get_token(client_id, client_secret)


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
    if data["object"] == "page":
        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:
                if messaging_event.get("message"):
                    sender_id = messaging_event["sender"]["id"]
                    recipient_id = messaging_event["recipient"]["id"]
                    message_text = messaging_event["message"]["text"]
                    # send_message(sender_id, message_text)
                    send_keyboard(sender_id, access_token, token_expires)
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


def send_keyboard(sender_id, access_token, token_expires):
    price_list_id = env.str("PRICE_LIST_ID")
    elements = create_products_description(access_token, token_expires, price_list_id)

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


def create_products_description(access_token, token_expires, price_list_id):
    if not check_token(token_expires):
        access_token, token_expires = get_token(client_id, client_secret)

    node_id_basic = env.str("BASIC_NODE_ID")
    hierarchy_id = env.str("HIERARCHY_ID")
    products_params = get_hierarchy_children(access_token, hierarchy_id,
                                  node_id=node_id_basic)['data']
    products_prices = get_products_prices(
        access_token,
        price_list_id=price_list_id
    )
    keyboard_elements = [{"title": 'Меню',
                        "image_url": 'https://media-cdn.tripadvisor.com/media/photo-s/1b/5d/8e/89/caption.jpg',
                        "subtitle": 'Здесь вы можете выбрать один из вариантов',
                        # "default_action": {
                        #   "type": "web_url",
                        #   "url": 'https://cdn.shopify.com/s/files/1/1661/9575/products/669A6046_2048x.jpg?v=1606125995',
                        #   "webview_height_ratio": "tall"
                        # },
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
                            "payload": product_sku
                          }
                          ]}
        keyboard_elements.append(keyboard_element)
    return keyboard_elements


if __name__ == '__main__':
    app.run(debug=True)
    # hierarchy_id = '5644aa5d-cf68-4dde-9fe0-3eb2c6118bc7'
    # node_id_hot = '86028403-e62b-4992-b39f-d0e08974cca8'
    # node_id_hearty = 'd3e32c20-3269-475f-85ee-d97ce96b6437'
    # node_id_basic = 'b41d0763-08db-48a5-913a-a359995be831'



