"""URL routing for the Tastyz Bakery app."""

from django.urls import path, re_path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("products/", views.products, name="products"),
    path("order/", views.place_order, name="place_order"),
    path("order/success/<int:pk>/", views.order_success, name="order_success"),
    path("chat/", views.chat, name="chat"),
    path("api/chat/", views.chat_api, name="chat_api"),
    path("api/orchestrator/", views.chat_orchestrator_api, name="chat_orchestrator_api"),
    path("recommend/", views.recommend, name="recommend"),
    # Settings
    path("settings/", views.settings_page, name="settings_page"),
    path("api/settings/models/", views.settings_get_models, name="settings_get_models"),
    path("api/settings/save/", views.settings_save, name="settings_save"),
    path("api/settings/cache/clear-expired/", views.settings_clear_expired_cache, name="settings_clear_expired_cache"),
    path("api/settings/cache/clear-all/", views.settings_clear_all_cache, name="settings_clear_all_cache"),
    path("api/settings/finetune/start/", views.settings_start_finetune, name="settings_start_finetune"),
    path("api/settings/finetune/export/", views.settings_export_training, name="settings_export_training"),
    # Feedback
    path("api/feedback/", views.submit_feedback, name="submit_feedback"),
    # Webhooks
    path("api/webhook/flutterwave/", views.flutterwave_webhook, name="flutterwave_webhook"),
    # Payment Status Check
    path("api/check-payment/<str:transaction_id>/", views.check_payment_status, name="check_payment_status"),
    # Invoice
    path("invoice/<int:pk>/", views.invoice_detail, name="invoice_detail"),
    # Media serving
    re_path(r'^media/(?P<path>.*)$', views.serve_media, name='serve_media'),
]
