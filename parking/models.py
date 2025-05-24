from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from django.conf import settings
import uuid
# Create your models here.
class Location(models.Model):
    city = models.CharField(unique=True,max_length=100)
    state = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()

    def __str__(self):
        return f"{self.state} - {self.city}"

class ParkingLot(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    address = models.TextField()
    postal_code = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    total_spaces = models.IntegerField()
    hourly_rate = models.DecimalField(max_digits=6, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()


    def __str__(self):
        return f"{self.name} at {self.location.city}"

class ParkingSpace(models.Model):
    SPACE_TYPES = (
        ('standard', 'Standard'),
        ('handicap', 'Handicap'),
        ('premium', 'Premium'),
    )

    parking_lot = models.ForeignKey(ParkingLot, on_delete=models.CASCADE)
    space_number = models.CharField(max_length=10,db_index=True)
    space_type = models.CharField(max_length=20, choices=SPACE_TYPES)
    is_active = models.BooleanField(default=True)
    objects = models.Manager()


    class Meta:
        unique_together = ['parking_lot', 'space_number']

    def is_available(self, start_time, end_time):
        if start_time >= end_time:
            return False
        overlapping_bookings = self.booking_set.filter(
            status__in=['pending', 'active'],
            start_time__lt=end_time,
            end_time__gt=start_time
        )
        return not overlapping_bookings.exists()

    def __str__(self):
        return f"{self.parking_lot.name} - Space {self.space_number}"

class Booking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    parking_space = models.ForeignKey(ParkingSpace, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    vehicle_number = models.CharField(max_length=12)
    model = models.CharField(max_length=20)
    booking_reference = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()


    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time")
        if self.start_time < timezone.now():
            raise ValidationError("Cannot book in the past")

    def calculate_price(self):
        duration = Decimal((self.end_time - self.start_time).total_seconds() / 3600)
        hourly_rate = Decimal(self.parking_space.parking_lot.hourly_rate)
        return round(duration * hourly_rate, 2)

    @staticmethod
    def generate_booking_reference():
        return str(uuid.uuid4())[:8].upper()


    def __str__(self):
        return f"Booking {self.booking_reference}"


class StripePayment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('requires_action', 'Requires Action'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    )

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="stripe_payment")
    stripe_charge_id = models.CharField(max_length=100, unique=True,db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending',db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment for Booking {self.booking.booking_reference} - {self.status}"
