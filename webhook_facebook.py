import os

import requests
import environs
from flask import Flask, request
from datetime import datetime
from moltin import (add_item_to_cart, create_client, delete_item_from_cart,
                    fill_fieds, get_cart_params, get_entry, get_entries,
                    get_product_files, get_product_params,
                    get_products_from_cart, get_products_names,
                    get_products_params, get_products_prices, get_token)
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

    products_params = get_products_params(access_token)['data'][0:5]
    products_prices = get_products_prices(
        access_token,
        price_list_id=price_list_id
    )
    keyboard_elements = []
    for product_params in products_params:
        product_name = product_params['attributes']['name']
        product_description = product_params['attributes']['description']
        product_sku = product_params['attributes']['sku']

        for price in products_prices['data']:
            if price['attributes']['sku'] == product_sku:
                product_price = "%.2f" % (price['attributes']['currencies']['RUB']['amount']/100)


        if product_params['relationships']['main_image']['data']:
            product_file_id = product_params['relationships']['main_image']['data']['id']
            product_image_params = get_product_files(access_token,
                                                     file_id=product_file_id)
            product_image_url = product_image_params['data']['link']['href']
        else:
            product_image_url = 'https://............jpg'

        keyboard_element = {
                        "title": product_name,
                        "image_url": product_image_url,
                        "subtitle": f'Цена {product_price} \n{product_description}',
                        "default_action": {
                          "type": "web_url",
                          "url": 'https://cdn.shopiv=1606125995',
                          "webview_height_ratio": "tall"
                        },
                        "buttons": [
                          {
                            "type": "postback",
                            "title": "Добавить в корзину",
                            "payload": product_sku
                          },
                          {
                            "type": "postback",
                            "title": "Корзина",
                            "payload": "DEVELOPER_DEFINED_PAYLOAD"
                          }]}
        keyboard_elements.append(keyboard_element)
    return keyboard_elements


if __name__ == '__main__':
    # env = environs.Env()
    # env.read_env()
    app.run(debug=True)

    # client_id = env.str("CLIENT_ID")
    # client_secret = env.str("CLIENT_SECRET")
    # price_list_id = env.str("PRICE_LIST_ID")
    # access_token, token_expires = get_token(client_id, client_secret)
