from django.urls import re_path
from .websocket_consumer import SalesBotConsumer

websocket_urlpatterns = [
    re_path(r"ws/sales-bot/$", SalesBotConsumer.as_asgi())
]
