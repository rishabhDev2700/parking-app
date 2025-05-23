from django.contrib import admin

from parking.models import Location, ParkingLot, ParkingSpace, Booking, StripePayment

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('city', 'state', 'is_active')
    search_fields = ('city','state')
    list_filter = ('is_active', 'state')

@admin.register(ParkingLot)
class ParkingLotAdmin(admin.ModelAdmin):
    list_display = ('name', 'location','address', 'total_spaces', 'hourly_rate', 'is_active')
    search_fields = ('name', 'location__name')
    list_filter = ('is_active', 'location')

@admin.register(ParkingSpace)
class ParkingSpaceAdmin(admin.ModelAdmin):
    list_display = ('space_number', 'parking_lot', 'space_type', 'is_active')
    search_fields = ('space_number', 'parking_lot__name')
    list_filter = ('space_type', 'is_active', 'parking_lot')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('booking_reference', 'user', 'parking_space', 'start_time', 'end_time', 'status')
    search_fields = ('booking_reference', 'user__email')
    list_filter = ('status', 'start_time')

@admin.register(StripePayment)
class StripePaymentAdmin(admin.ModelAdmin):
    list_display = ('stripe_charge_id', 'booking', 'status')
    search_fields = ('stripe_charge_id', 'booking__booking_reference')
    list_filter = ('status',)
