import xmlrpc.client
from .models import ProductionDoc, Month, ProductionPosition, RW
from .logic import format_date
import environ

env = environ.Env()
environ.Env.read_env()

url, db, username  = 'https://marceli2.odoo.com', 'marceli2', 'michal@marceli.eu',
password = env('PASSWORD')

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))


def create_production(month: Month):
    month_odoo_id = models.execute_kw(db, uid, password, 'x_production', 'create', [{'x_name': month.__str__()}])
    for rw in month.rw_set.all():
        rw.odoo_id = create_odoo_rw(rw)
        rw.save()

    for doc in month.production_docs:
        doc.odoo_id = create_production_doc(doc, month_odoo_id)
        doc.save()
        for position in doc.production_positions:
            create_production_position(doc.odoo_id, position)


def create_odoo_rw(rw: RW):
    fields = {
        'x_name': "RW " + rw.number,
        'x_number': rw.number,
        'x_date': rw.issue_date,
        'x_description': rw.description,
        'x_link_url': rw.link,
        'x_fakturownia_id': rw.fakturownia_id
    }
    return models.execute_kw(db, uid, password, 'x_rw', 'create', [fields])


def create_production_doc(prod_doc: ProductionDoc, month: int):
    fields = {
        'x_name': prod_doc.order_number,
        'x_order_number': prod_doc.order_number,
        'x_first_sale_date': format_date(prod_doc.first_sale_date),
        'x_studio_production_month': month,
        'x_dont_produce': prod_doc.do_not_produce,
    }
    if prod_doc.rw and prod_doc.rw.odoo_id:
        fields['x_rw'] = prod_doc.rw.odoo_id

    return models.execute_kw(db, uid, password, 'x_production_docs', 'create', [fields])


def create_production_position(prod_doc_id, prod_pos: ProductionPosition):
    fields = {
        'x_name': prod_pos.product.name,
        'x_production_doc': prod_doc_id,
        'x_product_id': prod_pos.product.fakturownia_id,
        'x_quantity': float(prod_pos.quantity),
        'x_link_url': prod_pos.product.link,
        'x_studio_value': float(prod_pos.sales_value),
        'x_studio_balance': float(prod_pos.balance),
        "x_studio_produced_quantity": prod_pos.prod_quantity,
        'x_dont_produce': prod_pos.do_not_produce,
    }
    return models.execute_kw(db, uid, password, 'x_production_positions', 'create', [fields])


def update_production_status(prod_doc: ProductionDoc):
    docs = models.execute_kw(
        db, uid, password, 'x_production_docs', 'search_read', [[['id', '=', prod_doc.odoo_id]]], {'fields': ["x_dont_produce", 'x_studio_order_name']}
    )
    odoo_doc = docs[0]
    prod_doc.do_not_produce = odoo_doc['x_dont_produce']
    prod_doc.order_name = odoo_doc['x_studio_order_name']
    prod_doc.save()

def update_odoo_pd(doc: ProductionDoc, pd_fields:dict):
    models.execute_kw(db, uid, password, 'x_production_docs', 'write', [[doc.odoo_id], pd_fields])

def update_odoo_rw(rw: RW, rw_fields:dict):
    models.execute_kw(db, uid, password, 'x_rw', 'write', [[rw.odoo_id], rw_fields])