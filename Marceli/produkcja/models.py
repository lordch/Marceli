import datetime

from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


class Month(models.Model):
    month_ago = datetime.datetime.today() - datetime.timedelta(days=30)
    default_year = month_ago.year
    default_month = month_ago.month
    year = models.IntegerField(default=default_year, validators=[MaxValueValidator(2099), MinValueValidator(2021)])
    month = models.IntegerField(default=default_month, validators=[MaxValueValidator(12), MinValueValidator(1)])

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
        return

    def set_do_not_produce(self):
        self.do_not_produce = all(position.do_not_produce for position in self.production_positions)
        self.save()

    def __str__(self):
        return self.order_number + " - " + self.month.__str__()


class ProductionPosition(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    production_doc = models.ForeignKey(ProductionDoc, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    raw_materials_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    do_not_produce = models.BooleanField(default=False)


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
        pass




    def __str__(self):
        return self.product.name


class InvoicePosition(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=15, decimal_places=2)
    price = models.DecimalField(max_digits=15, decimal_places=2)
    total_price = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    production_position = models.ForeignKey(ProductionPosition, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return self.product.name




