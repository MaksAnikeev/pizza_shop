import requests
from pprint import pprint
import json
import environs

from moltin import add_product, add_price_to_product, add_file, connect_file_to_product,\
    create_flow, add_fied_to_flow, fill_fied, get_token

if __name__ == '__main__':
    env = environs.Env()
    env.read_env()

    # url = 'https://dvmn.org/media/filer_public/90/90/9090ecbf-249f-42c7-8635-a96985268b88/addresses.json'
    # response = requests.get(url)
    # with open("pizza_address.json", 'w', encoding='utf8') as json_file:
    #     json.dump(response.json(), json_file, ensure_ascii=False)

    with open("pizza_address.json", "r") as address:
        adresses = json.loads(address.read())

    # url2 = 'https://dvmn.org/media/filer_public/a2/5a/a25a7cbd-541c-4caf-9bf9-70dcdf4a592e/menu.json'
    # response = requests.get(url2)
    # with open("pizza_menu.json", 'w', encoding='utf8') as json_file:
    #     json.dump(response.json(), json_file, ensure_ascii=False)

    with open("pizza_menu.json", "r") as menu:
        menu_items = json.loads(menu.read())

    client_id = env.str("CLIENT_ID")
    client_secret = env.str("CLIENT_SECRET")

    access_token, token_expires = get_token(client_id, client_secret)

    for pizza in menu_items:
        food_value = [f"Углеводы - {pizza['food_value']['carbohydrates']}",
                      f"Жиры - {pizza['food_value']['fats']}",
                      f"Белки - {pizza['food_value']['proteins']}",
                      f"ккал - {pizza['food_value']['kiloCalories']}",
                      f"Вес - {pizza['food_value']['weight']}"]
        food_values = '\n'.join(food_value)
        name = pizza['name']
        sku = str(pizza['id'])
        description = f'{pizza["description"]} \n {food_values}'
        # product_id = add_product(access_token, name, sku, description)

        price = pizza['price']
        usd_rate = 80
        price_list_id = '71b86c9e-cc52-4934-9f3f-7409f0831d2b'
        # add_price_to_product(access_token, price, sku, usd_rate, price_list_id)

        url = pizza['product_image']['url']
        # img_id = add_file(access_token, url)

        file_id = img_id
        # connect_file_to_product(access_token, file_id, product_id)


    flow_name = 'Pizzeria'
    flow_slug = 'pizzeria'
    flow_description = 'Адреса пиццерий'
    # flow_id = create_flow(access_token,
    #                    name=flow_name,
    #                    description=flow_description,
    #                    slug=flow_slug)

    field_name = 'Longitude'
    field_slug = 'pizzeria_longitude'
    field_type = 'float'
    field_description = 'Долгота'
    flow_required = False

    add_fied_to_flow(access_token,
                     name=field_name,
                     slug=field_slug,
                     field_type=field_type,
                     description=field_description,
                     flow_id=flow_id,
                     required=flow_required)

    # url = 'https://dvmn.org/media/filer_public/90/90/9090ecbf-249f-42c7-8635-a96985268b88/addresses.json'
    # response = requests.get(url)
    # with open("pizza_address.json", 'w', encoding='utf8') as json_file:
    #     json.dump(response.json(), json_file, ensure_ascii=False)

    with open("pizza_address.json", "r") as address:
        adresses = json.loads(address.read())

    for address in adresses:
        pizzeria_address = address['address']['full']
        alias = address['alias']
        flow_slug = 'pizzeria'
        longitude = address['coordinates']['lon'].replace(' ', '')
        latitude = address['coordinates']['lat'].replace(' ', '')
        pprint(fill_fied(
            access_token,
            address=pizzeria_address,
            flow_slug=flow_slug,
            alias=alias,
            longitude=float(longitude),
            latitude=float(latitude)))
