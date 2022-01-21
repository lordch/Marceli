import xmlrpc.client
from .models import ProductionDoc, Month, ProductionPosition, RW
import environ
import datetime

env = environ.Env()
environ.Env.read_env()

def format_date(date: datetime.date) -> str:
    return date.strftime("%Y-%m-%d")

class Odoo:
    def __init__(self):

        self.url = env('URL')
        self.db = env('DB')
        self.username = env('ODOO_USERNAME')
        self.password = env('PASSWORD')

        self.common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(self.url))
        self.uid = self.common.authenticate(self.db, self.username, self.password, {})
        self.models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(self.url))

    # # CREATE
    def create(self, odoo_model: str, fields: dict):
        return self.models.execute_kw(self.db, self.uid, self.password, odoo_model, 'create', [fields])

    # create / Month
    def create_production(self, month: Month):
        fields = {'x_name': month.__str__()}
        month.odoo_id = self.create('x_production', fields)
        month.save()
        for rw in month.rw_set.all():
            rw.odoo_id = self.create_rw(rw)
            rw.save()

        for doc in month.production_docs:
            doc.odoo_id = self.create_production_doc(doc, month.odoo_id)
            doc.save()
            for position in doc.production_positions:
                position.odoo_id = self.create_production_position(doc.odoo_id, position)
                position.save()

    # create / RW
    def create_rw(self, rw: RW):
        fields = {
            'x_name': "RW " + rw.number,
            'x_number': rw.number,
            'x_date': rw.issue_date,
            'x_description': rw.description,
            'x_link_url': rw.link,
            'x_fakturownia_id': rw.fakturownia_id
        }
        return self.create("x_rw", fields)

    # create / prod doc
    def create_production_doc(self, prod_doc: ProductionDoc, month: int):
        fields = {
            'x_name': prod_doc.order_number,
            'x_order_number': prod_doc.order_number,
            'x_first_sale_date': format_date(prod_doc.first_sale_date),
            'x_studio_production_month': month,
            'x_dont_produce': prod_doc.do_not_produce,
        }
        if prod_doc.rw and prod_doc.rw.odoo_id:
            fields['x_rw'] = prod_doc.rw.odoo_id

        return self.create('x_production_docs', fields)

    # create / prod pos
    def create_production_position(self, prod_doc_id, prod_pos: ProductionPosition):
        fields = {
            'x_name': prod_pos.product.name,
            'x_production_doc': prod_doc_id,
            'x_product_id': prod_pos.product.fakturownia_id,
            'x_quantity': float(prod_pos.quantity),
            'x_link_url': prod_pos.product.link,
            'x_studio_value': float(prod_pos.value_pln),
            'x_studio_balance': float(prod_pos.balance),
            "x_studio_produced_quantity": prod_pos.prod_quantity,
            'x_dont_produce': prod_pos.do_not_produce,
        }
        return self.create('x_production_positions', fields)

    # # GET
    def get(self, odoo_model:str, odoo_id: int, fields:list):
        return self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            odoo_model,
            'search_read',
            [[['id', '=', odoo_id]]],
            {'fields': fields}
        )

    # get / prod doc
    def get_production_status(self, prod_doc: ProductionDoc):
        fields = ["x_dont_produce", 'x_studio_order_name']
        docs = self.get("x_production_docs", prod_doc.odoo_id, fields)
        odoo_doc = docs[0]
        prod_doc.do_not_produce = odoo_doc['x_dont_produce']
        prod_doc.order_name = odoo_doc['x_studio_order_name']
        prod_doc.save()

    # get / prod position
    def get_production_position_status(self, position: ProductionPosition):
        fields = [
            "x_dont_produce",
            'x_studio_produced_quantity',
            'x_studio_raw_materials_value',
            'x_studio_unit_price',
        ]
        response = self.get('x_production_positions', position.odoo_id, fields)
        odoo_position = response[0]
        print(odoo_position)
        position.final_quantity = odoo_position['x_studio_produced_quantity']
        position.do_not_produce = odoo_position['x_dont_produce']
        position.raw_materials_value = odoo_position['x_studio_raw_materials_value']
        position.unit_price = odoo_position['x_studio_unit_price']
        position.save()


    def update(self, odoo_model: str, odoo_id: int, fields:dict):
        self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            odoo_model,
            'write',
            [[odoo_id], fields]
        )

    # update / prod doc
    def update_pd(self, doc: ProductionDoc, pd_fields:dict):
        self.update("x_production_docs", doc.odoo_id, pd_fields)

    # update / RW
    def update_rw(self, rw: RW, rw_fields: dict):
        print(f"Updating rw {rw}, odoo id: {rw.odoo_id}, fields: {rw_fields}")
        self.update("x_rw", rw.odoo_id, rw_fields)

    # update / prod pos
    def update_position(self, position: ProductionPosition, fields: dict):
        print(f"Updating position {position} odoo id: {position.odoo_id}, fields: {fields}")
        self.update("x_production_positions", position.odoo_id, fields)
