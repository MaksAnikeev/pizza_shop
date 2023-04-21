import requests
from telegram import InlineKeyboardButton
import requests
import environs
from pprint import pprint

env = environs.Env()
env.read_env()


client_id = env.str("CLIENT_ID")
client_secret = env.str("CLIENT_SECRET")

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

access_token, token_expires = get_token(client_id, client_secret)

print(access_token)


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


product_id = 'd2e8df81-cf59-4675-94d6-2dd721f295b5'
quantity = 2
cart_name = 704859099
# pprint(add_item_to_cart(access_token, product_id, quantity, cart_name))
headers = {
        'Authorization': f'Bearer {access_token}'
    }
requests.delete('https://api.moltin.com/v2/carts/704859099', headers=headers)