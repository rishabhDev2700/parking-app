from django.urls import path
from parking import views

app_name="parking"
# urls.py
urlpatterns = [
    path('', views.home, name='home'),
    path("locations/", views.location_list, name="location_list"),
    path("locations/<int:location_id>/",views.locations_lots_list,name="lots_list"),
    path("locations/<int:lot_id>/spaces/",views.parking_space_by_lot,name="parking_space_by_lots"),
    path("booking/create/",views.create_booking,name="create_booking"),
    path('booking/summary/', views.booking_summary, name='booking_summary'),
    path("booking-success/", views.booking_success, name="booking_success"),
    path("booking-failure/", views.booking_failure, name="booking_failure"),
    path('booking/<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('booking/<int:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('my-bookings/', views.user_bookings, name='user_bookings'),
    path("webhook/", views.stripe_webhook, name="stripe-webhook"),
]
