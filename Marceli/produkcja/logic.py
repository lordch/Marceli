from .models import ProductionDoc, RW
from .odoo import Odoo
import datetime

odoo = Odoo()

def format_date(date: datetime.date) -> str:
    return date.strftime("%Y-%m-%d")


def generate_rw_numbers_dates(docs: list[ProductionDoc]):
    for n, doc in enumerate(docs):
        year = str(doc.month.year)[2:]
        month = str(doc.month.month).zfill(2)
        num = str(n+1).zfill(2)
        doc.number = f"{year}/{month}/{num}"

        sale_date = doc.first_sale_date
        if sale_date.day > 7:
            doc.rw_date = sale_date - datetime.timedelta(days=7)
        else:
            doc.rw_date = sale_date.replace(day=1)
        doc.save()

        if doc.rw:
            rw = doc.rw
            rw.number = doc.number
            rw.issue_date = format_date(doc.rw_date)
            rw.save()


def create_new_django_rw(doc: ProductionDoc):
    description = f"Wydanie surowców do {doc.order_name}"
    doc.rw = RW.objects.create(
            number=doc.number,
            issue_date=format_date(doc.rw_date),
            description=description,
            month=doc.month,
        )
    doc.save()


def assign_raw_materials_to_positions(doc: ProductionDoc):
    value_left = doc.rw.value
    positions = doc.produced_positions
    if value_left and positions:
        last_position = positions[-1]
        for position in positions:
            if position == last_position:
                value = value_left
            else:
                value = round(float(position.sales_fraction) * float(doc.rw.value), 2)
                value_left -= value
                position.raw_materials_value = value
                position.save()
            if value:
                odoo.update_position(position, {'x_studio_raw_materials_value': value})
