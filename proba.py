import requests
from pprint import  pprint
import json
import environs
from datetime import datetime

env = environs.Env()
env.read_env()

# url = 'https://dvmn.org/media/filer_public/90/90/9090ecbf-249f-42c7-8635-a96985268b88/addresses.json'
# response = requests.get(url)
#
# with open("pizza_address.json", 'w', encoding='utf8') as json_file:
#     json.dump(response.json(), json_file, ensure_ascii=False)
#
# with open("pizza_address.json", "r") as address:
#         pprint(json.loads(address.read()))


# url2 = 'https://dvmn.org/media/filer_public/a2/5a/a25a7cbd-541c-4caf-9bf9-70dcdf4a592e/menu.json'
# response = requests.get(url2)
#
# with open("pizza_menu.json", 'w', encoding='utf8') as json_file:
#     json.dump(response.json(), json_file, ensure_ascii=False)

with open("pizza_menu.json", "r") as menu:
        menu_items = json.loads(menu.read())

# client_id = env.str("CLIENT_ID")
# client_secret = env.str("CLIENT_SECRET")
#
# data = {
#         'client_id': client_id,
#         'client_secret': client_secret,
#         'grant_type': 'client_credentials',
#     }
# response = requests.post('https://api.moltin.com/oauth/access_token', data=data)
# pprint(response.json())

access_token = env.str("ACCESS_TOKEN")

for pizza in menu_items:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        food_value = [f"Углеводы - {pizza['food_value']['carbohydrates']}",
                      f"Жиры - {pizza['food_value']['fats']}",
                      f"Белки - {pizza['food_value']['proteins']}",
                      f"ккал - {pizza['food_value']['kiloCalories']}",
                      f"Вес - {pizza['food_value']['weight']}"]
        food_values = '\n'.join(food_value)
        json_data = {
                'data': {
                    'type': 'product',
                    'attributes': {
                        'name': pizza['name'],
                        'commodity_type': 'physical',
                        'sku': str(pizza['id']),
                        'description': f'{pizza["description"]} \n {food_values}',
                        'status': 'live',

                        },
                    },
                }
        response = requests.post('https://api.moltin.com/pcm/products', headers=headers, json=json_data)
        product_id = response.json()['data']['id']

        usd_rate = 80
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        data = {
            "type": "product-price",
            "attributes": {
                "sku": str(pizza['id']),
                "currencies": {
                    "RUB": {
                        "amount": pizza['price']*100,
                        "includes_tax": False,
                            },
                    "USD": {
                        "amount": int(pizza['price']*100/usd_rate),
                        "includes_tax": False,
                            }
                        }
                    }
                }
        price_list_id = '71b86c9e-cc52-4934-9f3f-7409f0831d2b'
        response = requests.post(f'https://api.moltin.com/pcm/pricebooks/{price_list_id}/prices',
                                 headers=headers,
                                 json={"data": data})

        headers = {
            'Authorization': f'Bearer {access_token}',
        }
        files = {
            'file_location': (None, pizza['product_image']['url']),
        }
        response = requests.post('https://api.moltin.com/v2/files', headers=headers, files=files)
        response.raise_for_status()
        img_id = response.json()['data']['id']

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }

        json_data = {
            'data': {
                'type': 'file',
                'id': img_id,
            },
        }
        response = requests.post(
            f'https://api.moltin.com/pcm/products/{product_id}/relationships/main_image',
            headers=headers,
            json=json_data,
        )
        response.raise_for_status()