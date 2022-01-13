import requests
import json
import datetime
from .models import Product, RW
from .logic import format_date
import environ

env = environ.Env()
environ.Env.read_env()

API_TOKEN = env('API_TOKEN')
INVOICES_ENDPOINT = "https://marcelipl.fakturownia.pl/invoices.json"
WAREHOUSE_DOC_ENDPOINT = "https://marcelipl.fakturownia.pl/warehouse_documents.json"
WAREHOUSE_ACTIONS_ENDPOINT = "https://marcelipl.fakturownia.pl/warehouse_actions.json"


def request_invoices(date_from: datetime, date_to:datetime) -> dict:
    INVOICE_API_PARAMETERS = {
        "include_positions": "true",
        "period": "more",
        "date_from": format_date(date_from),
        "date_to": format_date(date_to),
        "per_page": 200,
        "api_token": API_TOKEN,
        "kind": "vat",
    }
    endpoint = INVOICES_ENDPOINT
    parameters = INVOICE_API_PARAMETERS
    response = requests.get(endpoint, parameters)
    document_list = response.json()
    return document_list


def request_rws(date_from: datetime, date_to:datetime) -> dict:
    WH_DOC_API_PARAMETERS = {
        "period": "more",
        "date_from": format_date(date_from),
        "date_to": format_date(date_to),
        "per_page": 500,
        "api_token": API_TOKEN,
        "kind": "rw",
    }
    endpoint = WAREHOUSE_DOC_ENDPOINT
    parameters = WH_DOC_API_PARAMETERS
    response = requests.get(endpoint, parameters)
    print(response.json())
    document_list = response.json()
    return document_list


def get_product_balance(product: Product):
    parameters = {
        "api_token": API_TOKEN,
        "product_id": product.fakturownia_id,
        "warehouse_id": 6033,
    }
    response = requests.get(WAREHOUSE_ACTIONS_ENDPOINT, parameters)
    wh_actions = response.json()
    balance = sum([float(action['quantity']) for action in wh_actions])
    return balance


def create_fakturownia_rw(rw: RW):
    headers = {
            'accept': "application/json",
            'content-type': "application/json",
        }

    parameters = {
        "api_token" : API_TOKEN,
        'warehouse_document':
            {"kind": "rw",
             "number": rw.number,
             "warehouse_id": 6032,
             "issue_date": rw.issue_date,
             'client_id': 1184961,
             'seller_person': 'Michał Chełmiński',
             'buyer_person': 'Iwona Burakiewicz',
             'description': rw.description
             }
    }

    response = requests.post(WAREHOUSE_DOC_ENDPOINT, headers=headers, data=json.dumps(parameters))
    return response.json()['id']


def update_fakturownia_rw(rw: RW):
    headers = {
            'accept': "application/json",
            'content-type': "application/json",
        }
    endpoint = f"https://marcelipl.fakturownia.pl/warehouse_documents/{str(rw.fakturownia_id)}.json"

    parameters = {
        "api_token" : API_TOKEN,
        'warehouse_document': {
            "number": rw.number,
            "issue_date": rw.issue_date
        }
    }

    response = requests.put(endpoint, headers=headers, data=json.dumps(parameters))
    print(response.json())


def get_fakturownia_rw_value(rw: RW):
    endpoint = f"https://marcelipl.fakturownia.pl/warehouse_documents/{rw.fakturownia_id}.json"
    response = requests.get(endpoint, {"api_token": API_TOKEN})
    value = 0
    if response.status_code == 404:
        print("RW not found!")
    else:
        f_rw = response.json()
        try:
            actions = f_rw['warehouse_actions']
            value = sum(float(action['total_purchase_price_net']) for action in actions)
        except KeyError:
            try:
                value = float(f_rw['purchase_price_net'])
            except TypeError:
                value = 0
    return value
