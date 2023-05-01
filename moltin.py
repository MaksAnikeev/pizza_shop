from pprint import pprint

import requests
from telegram import InlineKeyboardButton


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


def get_products_params(access_token):
    """
    Получить параметры всех продуктов
    """
    headers = {
            'Authorization': f'Bearer {access_token}',
        }
    response = requests.get('https://api.moltin.com/pcm/products',
                            headers=headers)
    response.raise_for_status()
    return response.json()


def get_product_params(access_token, product_id):
    """
    Получить параметры конкретного продукта по ИД
    """
    headers = {
            'Authorization': f'Bearer {access_token}',
        }
    params = {
        'include': 'prices',
    }
    response = requests.get(f'https://api.moltin.com/pcm/products/{product_id}',
                            headers=headers,
                            params=params)
    response.raise_for_status()
    return response.json()


def get_products_prices(access_token, price_list_id):
    """
    Получить цены по всем продуктам в заданном прайс листе
    """
    headers = {
            'Authorization': f'Bearer {access_token}',
        }
    response = requests.get(f'https://api.moltin.com/pcm/pricebooks/{price_list_id}/prices',
                            headers=headers)
    response.raise_for_status()
    return response.json()


def get_product_files(access_token, file_id):
    """
    Получить файл/картинку из базы по ид файла
    """
    headers = {
            'Authorization': f'Bearer {access_token}',
        }
    response = requests.get(f'https://api.moltin.com/v2/files/{file_id}',
                            headers=headers)
    response.raise_for_status()
    return response.json()


def create_client(access_token, client_name, email):
    """
    Создать клиента в базе по е-мейлу
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    json_data = {
        'data': {
            'type': 'customer',
            'name': client_name,
            'email': email,
        },
    }
    response = requests.post('https://api.moltin.com/v2/customers',
                             headers=headers,
                             json=json_data)
    return response


def get_products_names(products_params):
    """
    Получить название продуктов и сформировать их в список
    для отрисовки клавиатуры в ТГ
    """
    keyboard_products = [InlineKeyboardButton("Назад", callback_data='back_list_product'),
                          InlineKeyboardButton("Вперед", callback_data='next_list_product'),
                         InlineKeyboardButton("Главное меню", callback_data='main_menu')]
    for product in products_params:
        button_name = product['attributes']['name']
        button_id = product['id']
        button = InlineKeyboardButton(button_name, callback_data=button_id)
        keyboard_products.insert(0, button)
    return keyboard_products


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
    response.raise_for_status()
    return response


def get_products_from_cart(access_token, cart_name):
    """
    Получить все продукты из корзины для вывода в ТГ
    """
    headers = {
            'Authorization': f'Bearer {access_token}',
        }
    response = requests.get(f'https://api.moltin.com/v2/carts/{cart_name}/items',
                            headers=headers)
    response.raise_for_status()
    return response.json()


def get_cart_params(access_token, cart_name):
    """
    Получить параметры корзины
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/carts/{cart_name}',
                            headers=headers)
    response.raise_for_status()
    return response.json()


def delete_item_from_cart(access_token, cart_name, product_id):
    """
    Удалить продукт из корзины
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.delete(f'https://api.moltin.com/v2/carts/{cart_name}/items/{product_id}',
                               headers=headers)
    response.raise_for_status()
    return response


def add_product(access_token, name, sku, description):
    """
    Добавить продукт в магазин
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    json_data = {
        'data': {
            'type': 'product',
            'attributes': {
                'name': name,
                'commodity_type': 'physical',
                'sku': sku,
                'description': description,
                'status': 'live',

            },
        },
    }
    response = requests.post('https://api.moltin.com/pcm/products',
                             headers=headers,
                             json=json_data)
    response.raise_for_status()
    product_id = response.json()['data']['id']
    return product_id


def add_price_to_product(access_token, price, sku, usd_rate, price_list_id):
    """
    Добавить продукту цену в указанный прайс лист
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    data = {
        "type": "product-price",
        "attributes": {
            "sku": sku,
            "currencies": {
                "RUB": {
                    "amount": price * 100,
                    "includes_tax": False,
                },
                "USD": {
                    "amount": int(price * 100 / usd_rate),
                    "includes_tax": False,
                }
            }
        }
    }
    response = requests.post(f'https://api.moltin.com/pcm/pricebooks/{price_list_id}/prices',
                             headers=headers,
                             json={"data": data})
    response.raise_for_status()
    return response.json()


def add_file(access_token, url):
    """
    Добавить файлы/картинки в магазин
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    files = {
        'file_location': (None, url),
    }
    response = requests.post('https://api.moltin.com/v2/files',
                             headers=headers,
                             files=files)
    response.raise_for_status()
    img_id = response.json()['data']['id']
    return img_id


def connect_file_to_product(access_token, file_id, product_id):
    """
    Связать файлы/картинки с продуктом
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    json_data = {
        'data': {
            'type': 'file',
            'id': file_id,
        },
    }
    response = requests.post(
        f'https://api.moltin.com/pcm/products/{product_id}/relationships/main_image',
        headers=headers,
        json=json_data,
    )
    response.raise_for_status()
    return response.json()


def create_flow(access_token, name, description, slug):
    """
    Создать новую модель в магазин
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    json_data = {
        'data': {
            'type': 'flow',
            'name': name,
            'slug': slug,
            'description': description,
            'enabled': True,
        },
    }
    response = requests.post('https://api.moltin.com/v2/flows',
                             headers=headers,
                             json=json_data)
    response.raise_for_status()
    flow_id = response.json()['data']['id']
    return flow_id


def add_fied_to_flow(access_token, name, slug, field_type, description, flow_id, required):
    """
    Добавить поля в модель
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    json_data = {
        'data': {
            'type': 'field',
            'name': name,
            'slug': slug,
            'field_type': field_type,
            'description': description,
            'required': required,
            'default': 0,
            'enabled': True,
            'relationships': {
                'flow': {
                    'data': {
                        'type': 'flow',
                        'id': flow_id,
                    },
                },
            },
        },
    }
    response = requests.post('https://api.moltin.com/v2/fields',
                             headers=headers,
                             json=json_data)
    response.raise_for_status()
    return response.json()


def fill_pizzeria_fieds(access_token, address, flow_slug,
                        alias=None,
                        longitude=None,
                        latitude=None):
    """
    Заполнить поля в модели
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    json_data = {
        'data': {
            'type': 'entry',
            'pizzeria_address': address,
            'pizzeria_alias': alias,
            'pizzeria_longitude': longitude,
            'pizzeria_latitude': latitude
            },
        }

    response = requests.post(f'https://api.moltin.com/v2/flows/{flow_slug}/entries',
                             headers=headers,
                             json=json_data)
    response.raise_for_status()
    return response.json()


def fill_fieds(access_token, flow_slug,
               first_field, first_value,
               second_field, second_value,
               third_field, third_value,):
    """
    Заполнить поля в модели
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    json_data = {
        'data': {
            'type': 'entry',
            f'{first_field}': first_value,
            f'{second_field}': second_value,
            f'{third_field}': third_value,
            },
        }

    response = requests.post(f'https://api.moltin.com/v2/flows/{flow_slug}/entries',
                             headers=headers,
                             json=json_data)
    response.raise_for_status()
    entry_id = response.json()['data']['id']
    return entry_id


def fill_fied(access_token, fied_slug, field_value, flow_slug, entry_id):
    """
    Обновить поле в модели
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    json_data = {
        'data': {
            'id': entry_id,
            'type': 'entry',
            f'{fied_slug}': field_value,
            },
        }

    response = requests.put(f'https://api.moltin.com/v2/flows/{flow_slug}/entries/{entry_id}',
                            headers=headers,
                            json=json_data)
    pprint(response.json())
    response.raise_for_status()
    return response.json()


def get_entries(access_token, slug):
    """
   Получить объекты модели из магазина
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/flows/{slug}/entries',
                            headers=headers)
    return response.json()['data']


def get_entrie(access_token, slug, id):
    """
       Получить один объект модели из магазина
    """
    headers = {
            'Authorization': f'Bearer {access_token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/flows/{slug}/entries/{id}',
                            headers=headers)
    response.raise_for_status()
    return response.json()
