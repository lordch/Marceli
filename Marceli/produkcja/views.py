import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.template import loader
from django.core.exceptions import ObjectDoesNotExist
from .models import Month, Invoice, Product, InvoicePosition, ProductionDoc, ProductionPosition, RW
from .fakturownia import request_invoices, request_rws, get_product_balance, create_fakturownia_rw, update_fakturownia_rw, get_fakturownia_rw_value
from .odoo import create_production, update_production_status, create_odoo_rw, update_odoo_pd, update_odoo_rw
from .logic import generate_rw_numbers_dates, create_new_django_rw


def index(request):
    months = Month.objects.all()
    template = loader.get_template('index.html')
    context = {
        'months': months,
    }
    return HttpResponse(template.render(context, request))


def month_details(request, month_id):
    month = get_object_or_404(Month, pk=month_id)
    return render(request, 'month_details.html', {'month': month})


def invoice_details(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    return render(request, 'invoice.html', {'invoice': invoice})


def prod_doc_details(request, prod_doc_id):
    prod_doc = get_object_or_404(ProductionDoc, pk=prod_doc_id)
    return render(request, 'production_doc.html', {'prod_doc': prod_doc})


def prod_pos_details(request, prod_pos_id):
    prod_pos = get_object_or_404(ProductionPosition, pk=prod_pos_id)
    return render(request, 'production_position.html', {'prod_pos': prod_pos})


def get_invoices(request, month_id):
    month = Month.objects.get(pk=month_id)
    # fetch invoices from fakturownia for given month
    documents = request_invoices(month.date_from, month.date_to)

    # create invoices in the db
    for document in documents:
        i = Invoice(
            fakturownia_id=document['id'],
            date=datetime.datetime.strptime(document['issue_date'], "%Y-%m-%d"),
            month=month,
            number=document['number'],
            order_id=document['oid'],
            buyer=document['buyer_name'],
            warehouse_id=document['warehouse_id'],
            value=document['price_net'],
            currency=document['currency'],
            exchange_rate=document['exchange_rate'],
        )
        i.save()

        # create invoice positions
        for position in document['positions']:
            try:
                product = Product.objects.get(fakturownia_id=position['product_id'])
            except ObjectDoesNotExist:
                product = Product.objects.create(name=position['name'], fakturownia_id=position['product_id'])

            discount = position['discount']
            if discount is None:
                discount = 0
            else:
                discount = float(discount)

            InvoicePosition.objects.create(
                product=product,
                invoice=i,
                quantity=position['quantity'],
                price=position['price_net'],
                total_price=float(position['total_price_net']) - discount,
            )

    # create production docs for sales from product warehouse
    invoices = month.invoice_set.all()
    for invoice in invoices:
        if invoice.warehouse_id == 6033:
            try:
                production_doc = ProductionDoc.objects.get(month=month, order_number=invoice.order_id)
            except ObjectDoesNotExist:
                production_doc = ProductionDoc.objects.create(month=month, order_number=invoice.order_id)

            # crate production positions and connect them with invoice positions
            for position in invoice.invoiceposition_set.all():
                try:
                    production_position = ProductionPosition.objects.get(production_doc=production_doc,
                                                                         product=position.product)
                except ObjectDoesNotExist:
                    production_position = ProductionPosition.objects.create(production_doc=production_doc,
                                                                            product=position.product)
                production_position.balance = get_product_balance(production_position.product)
                production_position.save()
                production_position.set_do_not_produce()

                # connect invoice position with production position
                position.production_position = production_position
                position.save()


    print(" about to request RWS")
    rws = request_rws(month.date_from, month.date_to)
    for rw in rws:
        r = RW.objects.create(
            fakturownia_id=rw['id'],
            number=rw['number'],
            issue_date=rw['issue_date'],
            description=rw['description'],
            month=month,
        )
        for doc in month.production_docs:
            if doc.order_number in r.description:
                doc.rw = r
                doc.save()
                break

    for doc in month.production_docs:
        doc.set_do_not_produce()

    return redirect('detail', month_id=month_id)


def delete_invoices(request, month_id):
    month = Month.objects.get(pk=month_id)
    Invoice.objects.filter(month=month).delete()
    ProductionDoc.objects.filter(month=month).delete()
    RW.objects.filter(month=month).delete()
    return redirect('detail', month_id=month_id)


def upload_docs_to_odoo(request, month_id):
    month = Month.objects.get(pk=month_id)
    create_production(month)
    return redirect('detail', month_id=month_id)


def check_production_status(request, month_id):
    month = Month.objects.get(pk=month_id)

    for pd in month.production_docs:
        update_production_status(pd)

    produced_pds = [pd for pd in month.production_docs if not pd.do_not_produce]
    generate_rw_numbers_dates(produced_pds)


    for doc in produced_pds:
        if not doc.rw:

            create_new_django_rw(doc)

            doc.rw.fakturownia_id = create_fakturownia_rw(doc.rw)
            doc.rw.save()

            doc.rw.odoo_id = create_odoo_rw(doc.rw)
            doc.rw.save()

            pd_fields = {'x_rw': doc.rw.odoo_id}
            update_odoo_pd(doc, pd_fields)

        else:
            rw = doc.rw
            fields = {
                'x_name': "RW " + rw.number,
                'x_number': rw.number,
                'x_date': rw.issue_date,
            }
            update_odoo_rw(rw, fields)
            # update_fakturownia_rw(rw)

    return redirect('detail', month_id=month_id)


def update_rw_value(request, month_id):
    month = Month.objects.get(pk=month_id)
    print("url's workin")
    produced_pds = [pd for pd in month.production_docs if not pd.do_not_produce]
    for doc in produced_pds:
        rw = doc.rw
        rw.value = get_fakturownia_rw_value(rw)
        rw.save()

    return redirect('detail', month_id=month_id)
