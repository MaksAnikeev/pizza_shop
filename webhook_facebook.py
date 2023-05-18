import os

import requests
import environs
from flask import Flask, request

app = Flask(__name__)
env = environs.Env()
env.read_env()

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
                    send_send_keyboard(sender_id)
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


def send_send_keyboard(sender_id):
    params = {"access_token": env.str("PAGE_ACCESS_TOKEN")}
    headers = {"Content-Type": "application/json"}
    json_data = {
        "recipient": {
            "id": sender_id
        },
        'message': {
            'attachment': {
                'type': 'template',
                'payload': {
                    'template_type': 'button',
                    'text': 'Пицца шпицца',
                    'buttons': [
                        {
                            'type': 'postback',
                            'title': 'Добавить в корзину',
                            'payload': 'DEVELOPER_DEFINED_PAYLOAD',
                        },
                        {
                            'type': 'postback',
                            'title': 'Назад',
                            'payload': 'DEVELOPER_DEFINED_PAYLOAD',
                        },
                    ],
                },
            },
        },
    }
    response = requests.post(
        "https://graph.facebook.com/v2.6/me/messages",
        params=params, headers=headers, json=json_data
    )
    response.raise_for_status()

if __name__ == '__main__':
    env = environs.Env()
    env.read_env()
    app.run(debug=True)
