from .models import ProductionDoc, RW
import datetime


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


def assign_positions_value(doc: ProductionDoc):
    pass