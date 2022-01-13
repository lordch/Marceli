from django.contrib import admin
from .models import Month, RW, Invoice, Product, InvoicePosition, ProductionPosition, ProductionDoc

admin.site.register(Month)
admin.site.register(Invoice)
admin.site.register(Product)
admin.site.register(InvoicePosition)
admin.site.register(ProductionPosition)
admin.site.register(ProductionDoc)
admin.site.register(RW)
