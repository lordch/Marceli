from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('<int:month_id>/', views.month_details, name='detail'),
    path('<int:month_id>/get_documents_from_fakturownia/', views.get_documents_from_fakturownia, name='get_documents_from_fakturownia'),
    path('<int:month_id>/delete_documents/', views.delete_documents, name='delete_documents'),
    path('<int:month_id>/upload_to_odoo/', views.upload_docs_to_odoo, name='upload_docs_to_odoo'),
    path('<int:month_id>/check_production_status/', views.check_production_status, name='check_production_status'),
    path('<int:month_id>/create_and_update_rws/', views.create_and_update_rws, name='create_and_update_rws'),
    path('<int:month_id>/update_rw_value/', views.update_rw_value, name='update_rw_value'),
    path('<int:month_id>/create_pws/', views.create_pws, name='create_pws'),
    # path('<int:month_id>/check_production_status_odoo/', views.check_production_status_odoo, name='check_production_status_odoo'),
    path('invoices/<int:invoice_id>/', views.invoice_details, name='invoice_details'),
    path('prod_docs/<int:prod_doc_id>/', views.prod_doc_details, name='prod_doc_details'),
    path('prod_pos/<int:prod_pos_id>/', views.prod_pos_details, name='prod_pos_details'),

]