from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Booking
from parking.services import notify_booking_update

@shared_task
def cleanup_pending_bookings():
    cutoff = timezone.now() - timedelta(minutes=5)
    print(cutoff)
    stale_bookings = Booking.objects.filter(status='pending', created_at__lt=cutoff)
    print(stale_bookings)
    for booking in stale_bookings:
        booking.status = 'cancelled'
        booking.save()
        notify_booking_update(booking.parking_space.id,booking.parking_space.parking_lot.id,status="cancelled")
