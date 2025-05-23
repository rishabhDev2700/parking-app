import time
from django.urls import reverse
import stripe
from django.conf import settings
from django.db import transaction
import uuid
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from parking.models import Booking, StripePayment, ParkingSpace

stripe.api_key = settings.STRIPE_SECRET_KEY

def notify_booking_update(space_id, lot_id, status):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"booking_updates_lot_{lot_id}",
        {
            "type": "booking_update",
            "space_id": space_id,
            "status": status,
        }
    )

class BookingService:
    @staticmethod
    @transaction.atomic
    def create_booking(request, parking_space, start_time, end_time,vehicle_model,vehicle_number):
        
        space = ParkingSpace.objects.select_for_update().get(id=parking_space.id)

        if not space.is_available(start_time, end_time):
            raise ValueError("Parking space is not available for the selected time slot")

        booking = Booking(
            user=request.user,
            parking_space=space,
            start_time=start_time,
            end_time=end_time,
            booking_reference=str(uuid.uuid4())[:8].upper(),
            model=vehicle_model,
            vehicle_number=vehicle_number,
            status="pending"
        )
        booking.total_price = booking.calculate_price()
        booking.clean()
        booking.save()

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "gbp",
                            "unit_amount": int(booking.total_price * 100),  # Stripe uses cents
                            "product_data": {
                                "name": f"Parking Space {space.space_number}",
                                "description": "Parking space booking",
                            }
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                metadata={"booking_id": str(booking.id)} ,
                success_url=request.build_absolute_uri(reverse("parking:booking_success")) + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=request.build_absolute_uri(reverse("parking:booking_failure"))+ "?session_id={CHECKOUT_SESSION_ID}",
                expires_at=int(time.time()) + 1800,
            )

            # Store the checkout session reference
            StripePayment.objects.create(
                booking=booking,
                stripe_charge_id=checkout_session.id,  # Store session ID
                amount=booking.total_price,
                status="pending",
            )
            notify_booking_update(
                space_id=space.id,
                lot_id=space.parking_lot.id,
                status="pending"
            )
            return checkout_session

        except Exception as e:
            booking.status = "cancelled"
            booking.save()
            notify_booking_update(
                space_id=space.id,
                lot_id=space.parking_lot.id,
                status="cancelled"
            )
            raise ValueError(f"Payment creation failed: {str(e)}")

  