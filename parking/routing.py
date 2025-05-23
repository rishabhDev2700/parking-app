from django.urls import re_path
from parking.consumers import BookingStatusConsumer
websocket_urlpatterns = [
    re_path(r"ws/bookings/(?P<lot_id>\d+)/$", BookingStatusConsumer.as_asgi()),
]