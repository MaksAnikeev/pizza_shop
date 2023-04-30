import requests
from pprint import pprint
import json
import environs

from moltin import add_product, add_price_to_product, add_file, connect_file_to_product,\
    create_flow, add_fied_to_flow, fill_fied, get_token, get_entries, fill_pizzeria_fieds


def get_file(url, file_name):
    """
    Получаем файл с описанием продуктов из интернета и сохраняем его у себя в папке с проектом
    """
    response = requests.get(url)
    with open(file_name, 'w', encoding='utf8') as json_file:
        json.dump(response.json(), json_file, ensure_ascii=False)


def create_moltin_products(file_name, price_list_id):
    """
    Создаем продукты/пиццы из джейсон файла и присваиваем каждому продукту цену и картинку
    """
    with open(file_name, "r") as menu:
        menu_items = json.loads(menu.read())

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
        product_id = add_product(access_token, name, sku, description)

        price = pizza['price']
        usd_rate = 80
        add_price_to_product(access_token, price, sku, usd_rate, price_list_id)
        url = pizza['product_image']['url']
        img_id = add_file(access_token, url)

        file_id = img_id
        connect_file_to_product(access_token, file_id, product_id)


if __name__ == '__main__':
    env = environs.Env()
    env.read_env()

    url = 'https://dvmn.org/media/filer_public/a2/5a/a25a7cbd-541c-4caf-9bf9-70dcdf4a592e/menu.json'
    file_name = "pizza_menu.json"
    # get_file(url, file_name)

    client_id = env.str("CLIENT_ID")
    client_secret = env.str("CLIENT_SECRET")

    price_list_id = '71b86c9e-cc52-4934-9f3f-7409f0831d2b'

    """
    Создаем модель "Адрес клиента"
    """
    access_token, token_expires = get_token(client_id, client_secret)
    flow_name = 'Customer Address'
    flow_slug = 'customer_address'
    flow_description = 'Адреса клиента'
    # flow_id = create_flow(access_token,
    #                       name=flow_name,
    #                       description=flow_description,
    #                       slug=flow_slug)
    # ид пицеррии
    flow_id = '61e8339e-65bf-49fe-9344-eddcd681fdac'
    # ид адрес клиента
    # flow_id = '0bb5f589-bd01-479e-9c8d-2bfe4e2b2380'

    """
    Создаем поля в модели пицерий
    """
    field_name = 'Сourier'
    field_slug = 'telegram_id'
    field_type = 'integer'
    field_description = 'телеграм ид курьера'
    flow_required = True

    # add_fied_to_flow(access_token,
    #                  name=field_name,
    #                  slug=field_slug,
    #                  field_type=field_type,
    #                  description=field_description,
    #                  flow_id=flow_id,
    #                  required=flow_required)

    """
    Скачиваем по ссылке файл с адресами пиццерий
    """
    url = 'https://dvmn.org/media/filer_public/90/90/9090ecbf-249f-42c7-8635-a96985268b88/addresses.json'
    file_name = "pizza_address.json"
    # get_file(url, file_name)

    """
    Заполняем созданную модель пицерий адресами пицерий с координатами
    """
    with open("pizza_address.json", "r") as address:
        adresses = json.loads(address.read())

    for address in adresses:
        pizzeria_address = address['address']['full']
        alias = address['alias']
        flow_slug = 'pizzeria'
        longitude = address['coordinates']['lon'].replace(' ', '')
        latitude = address['coordinates']['lat'].replace(' ', '')
    #     fill_pizzeria_fieds(
    #         access_token,
    #         address=pizzeria_address,
    #         flow_slug=flow_slug,
    #         alias=alias,
    #         longitude=longitude,
    #         latitude=latitude)

    """
    Обновляем поле курьера в модели пицерии, заполняем телеграмм ид
    """
    slug = 'pizzeria'
    pizzerias = get_entries(access_token, slug)
    fied_slug = 'telegram_id'
    flow_slug = 'pizzeria'
    field_value = 704859099

    for pizzeria in pizzerias:
        entry_id = pizzeria['id']
    #     fill_fied(access_token, fied_slug, field_value, flow_slug, entry_id)