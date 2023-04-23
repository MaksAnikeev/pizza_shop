import requests
from telegram import InlineKeyboardButton
import requests
import environs
from pprint import pprint
from geopy import distance

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

address = 'Москва, Старый Арбат, 4'
api_yandex_key = env('API_YANDEX_KEY')
lon, lat = fetch_coordinates(api_yandex_key, address)
client_coordinates = (lon, lat)

def get_entries(access_token, slug):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/flows/{slug}/entries', headers=headers)
    return response.json()['data']

slug = 'pizzeria'

pizzerias_params = get_entries(access_token, slug)

def get_min_distance(client_coordinates, pizzerias_params):
    distance_to_client = {}
    for pizzeria in pizzerias_params:
        pizzeria_longitude = pizzeria['pizzeria_longitude']
        pizzeria_latitude = pizzeria['pizzeria_latitude']
        pizzeria_address = (pizzeria_longitude, pizzeria_latitude)
        client_distance = round(distance.distance(client_coordinates, pizzeria_address).km, 2)
        pizzeria_full_address = pizzeria['pizzeria_address']
        distance_to_client[pizzeria_full_address] = client_distance
    pprint(distance_to_client)
    min_distance = dict([min(distance_to_client.items(), key=lambda item:item[1])])
    for key, value in min_distance.items():
        pizzeria_full_address = key
        distance_to_client = value
    return pizzeria_full_address, distance_to_client

pizzeria_full_address, distance_to_client = get_min_distance(client_coordinates, pizzerias_params)
# print(distance_to_client)
