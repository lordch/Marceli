import datetime

from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


class FakturowniaModel(models.Model):
    f_model_name = None


class Month(models.Model):
    month_ago = datetime.datetime.today() - datetime.timedelta(days=30)
    default_year = month_ago.year
    default_month = month_ago.month
    year = models.IntegerField(default=default_year, validators=[MaxValueValidator(2099), MinValueValidator(2021)])
    month = models.IntegerField(default=default_month, validators=[MaxValueValidator(12), MinValueValidator(1)])
    odoo_id = models.IntegerField(unique=True, null=True)

    @property
    def date_from(self):
        return datetime.date(self.year, self.month, 1)

    @property
    def date_to(self):
        if self.month == 12:
            next_month = 1
            next_year = self.year + 1
        else:
            next_month = self.month + 1
            next_year = self.year
        next_month_start = datetime.date(next_year, next_month, 1)
        return next_month_start - datetime.timedelta(days=1)

    @property
    def production_docs(self):
        return sorted(self.productiondoc_set.all(), key=lambda x: x.first_sale_date)

    @property
    def produced_docs(self):
        return [doc for doc in self.production_docs if not doc.do_not_produce]

    def __str__(self):
        return  str(self.month).zfill(2) + "." + str(self.year)


class Invoice(models.Model):
    fakturownia_id = models.IntegerField(unique=True)
    date = models.DateField()
    month = models.ForeignKey(Month, on_delete=models.CASCADE)
    number = models.CharField(max_length=12)
    order_id = models.CharField(max_length=8)
    buyer = models.CharField(max_length=32)
    warehouse_id = models.IntegerField()
    value = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    exchange_rate = models.DecimalField(max_digits=8, decimal_places=4)



    @property
    def link(self):
        return "https://marcelipl.fakturownia.pl/invoices/" + str(self.fakturownia_id)

    def __str__(self):
        return self.number
    # positions


class Product(models.Model):
    name = models.CharField(max_length=64)
    fakturownia_id = models.IntegerField(unique=True)


    @property
    def link(self):
        return "https://marcelipl.fakturownia.pl/products/" + str(self.fakturownia_id)

    def __str__(self):
        return self.name


class RW(models.Model):
    fakturownia_id = models.IntegerField(unique=True, null=True)
    number = models.CharField(max_length=10)
    issue_date = models.CharField(max_length=10)
    description = models.CharField(max_length=128, null=True)
    month = models.ForeignKey(Month, on_delete=models.CASCADE, null=True)
    odoo_id = models.IntegerField(unique=True, null=True)
    value = models.DecimalField(max_digits=12, decimal_places=2, null=True)

    @property
    def link(self):
        return "https://marcelipl.fakturownia.pl/warehouse_documents/" + str(self.fakturownia_id)

    def __str__(self):
        return self.number


class ProductionDoc(models.Model):
    month = models.ForeignKey(Month, on_delete=models.CASCADE)
    order_number = models.CharField(max_length=8)
    order_name = models.CharField(max_length=64, null=True)
    rw = models.ForeignKey(RW, on_delete=models.SET_NULL, null=True)
    odoo_id = models.IntegerField(unique=True, null=True)
    do_not_produce = models.BooleanField(default=False)
    number = models.CharField(max_length=8, null=True)
    rw_date = models.DateField(null=True)
    pw_fakturownia_id = models.IntegerField(unique=True, null=True)
    pw_fakturownia_json = models.JSONField(null=True)

    @property
    def production_positions(self):
        return self.productionposition_set.all()

    @property
    def produced_positions(self):
        return [pos for pos in self.production_positions if not pos.do_not_produce]

    @property
    def first_sale_date(self):
        try:
            return min(pos.first_sale_date for pos in self.production_positions)
        except TypeError:
            return ""
        except ValueError:
            return ""

    @property
    def sale_value(self):
        return sum([position.value_pln for position in self.produced_positions])

    @property
    def sale_value_display(self):
        return str(round(self.sale_value, 2)) + " zł"


    @property
    def currency(self):
        if self.production_positions:
            return self.production_positions[0].currency

    @property
    def odoo_link(self):
        return f"https://marceli2.odoo.com/web?debug=#id={self.odoo_id}&action=1242&model=x_production_docs&view_type=form&menu_id=459"


    def set_do_not_produce(self):
        self.do_not_produce = all(position.do_not_produce for position in self.production_positions)
        self.save()

    def __str__(self):
        if self.order_name:
            return self.order_name
        else:
            return self.order_number + " - " + self.month.__str__()


class ProductionPosition(models.Model):
    f_model_name = "warehouse_actions"


    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    production_doc = models.ForeignKey(ProductionDoc, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    raw_materials_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    final_quantity = models.IntegerField(null=True)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    do_not_produce = models.BooleanField(default=False)
    odoo_id = models.IntegerField(unique=True, null=True)

    @property
    def invoice_positions(self):
        return self.invoiceposition_set.all()

    @property
    def quantity(self):
        return sum(pos.quantity for pos in self.invoice_positions)

    @property
    def sales_value(self):
        return sum(pos.total_price for pos in self.invoice_positions)

    @property
    def first_sale_date(self):
        try:
            return min(pos.invoice.date for pos in self.invoice_positions)
        except TypeError:
            return ""
        except ValueError:
            return ""

    @property
    def prod_quantity(self):
        balance = int(self.balance)
        if balance < 0:
            return balance * -1
        else:
            return 0

    def set_do_not_produce(self):
        name = self.product.name.lower()
        transport = "transport" in name
        advance = "rozliczenie" in name or "zaliczk" in name
        balance = self.balance >= 0
        self.do_not_produce = transport or advance or balance
        self.save()

    @property
    def sales_fraction(self):
        if self.production_doc.sale_value:
            return self.value_pln / self.production_doc.sale_value
        else:
            return 0

    @property
    def sales_fraction_display(self):
        return round(self.sales_fraction, 2)

    @property
    def currency(self):
        if self.invoice_positions:
            return self.invoice_positions[0].currency

    @property
    def exchange_rate(self):
        if self.invoice_positions:
            return self.invoice_positions[0].exchange_rate
        else:
            return 1

    @property
    def value_pln(self):
        return self.sales_value * self.exchange_rate\


    @property
    def value_pln_display(self):
        return str(round(self.value_pln, 2)) + " zł"

    @property
    def unit_price_float(self):
        return float(self.unit_price)
    
    def __str__(self):
        return self.product.name


class InvoicePosition(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=15, decimal_places=2)
    price = models.DecimalField(max_digits=15, decimal_places=2)
    total_price = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    production_position = models.ForeignKey(ProductionPosition, null=True, on_delete=models.CASCADE)

    @property
    def currency(self):
        return self.invoice.currency

    @property
    def exchange_rate(self):
        return self.invoice.exchange_rate

    def __str__(self):
        return self.product.name




