from datetime import datetime
from decimal import Decimal
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from parking.models import Booking, Location, ParkingLot, ParkingSpace, StripePayment
from django.db.models import Count, Q
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import stripe
from config import settings
from parking.services import BookingService, notify_booking_update


@login_required
def home(request):
    """Dashboard view showing user's bookings and available parking spaces"""
    active_bookings = Booking.objects.filter(
        user=request.user, status__in=["active"], end_time__gte=timezone.now()
    ).select_related(
        "parking_space",
        "parking_space__parking_lot",
        "parking_space__parking_lot__location",
    )

    available_lots = ParkingLot.objects.filter(
        is_active=True, parkingspace__is_active=True
    ).annotate(
        available_spaces=Count("parkingspace", filter=Q(parkingspace__is_active=True))
    )
    return render(
        request,
        "parking/home.html",
        {
            "active_bookings": active_bookings,
            "available_lots": available_lots,
        },
    )


def location_list(request):
    locations = Location.objects.filter(is_active=True)
    return render(request, "parking/location_list.html", {"locations": locations})


def locations_lots_list(request, location_id):
    location = get_object_or_404(Location, pk=location_id)
    lots = ParkingLot.objects.filter(is_active=True, location=location)
    return render(
        request,
        "parking/location_list.html",
        {"location": location, "parkinglots": lots},
    )


def parking_space_by_lot(request, lot_id):
    parking_lot = get_object_or_404(ParkingLot, pk=lot_id)

    start_time = request.GET.get("start_time")
    end_time = request.GET.get("end_time")

    parking_spaces = ParkingSpace.objects.filter(
        parking_lot=parking_lot, is_active=True
    )
    available_parking_spaces = []
    if start_time and end_time:
        try:
            start_datetime = datetime.fromisoformat(start_time)
            end_datetime = datetime.fromisoformat(end_time)

            current_timezone = timezone.get_current_timezone()
            start_datetime = timezone.make_aware(start_datetime, current_timezone)
            end_datetime = timezone.make_aware(end_datetime, current_timezone)

            unavailable_spaces = parking_spaces.filter(
                booking__status__in=["pending", "active"],
                booking__start_time__lt=end_datetime,
                booking__end_time__gt=start_datetime,
            )

            available_parking_spaces = parking_spaces.exclude(id__in=unavailable_spaces)
        except ValueError:
            messages.error(request, "Invalid date format")

    return render(
        request,
        "parking/parking_lots.html",
        {
            "location": parking_lot.location,
            "parking_lot": parking_lot,
            "available_parking_spaces": available_parking_spaces,
            "start_time": start_time,
            "end_time": end_time,
        },
    )


def booking_summary(request):
    space_id = request.GET.get("space_id")
    start_time = request.GET.get("start_time")
    end_time = request.GET.get("end_time")

    parking_space = get_object_or_404(ParkingSpace, id=space_id)

    start_time_naive = parse_datetime(start_time)
    end_time_naive = parse_datetime(end_time)

    start_time_aware = timezone.make_aware(
        start_time_naive, timezone.get_current_timezone()
    )
    end_time_aware = timezone.make_aware(
        end_time_naive, timezone.get_current_timezone()
    )

    start_time_display = timezone.localtime(start_time_aware).strftime("%Y-%m-%d %H:%M")
    end_time_display = timezone.localtime(end_time_aware).strftime("%Y-%m-%d %H:%M")
    duration = end_time_aware - start_time_aware
    duration_hours = duration.total_seconds() / 3600
    extras = 1
    if parking_space.space_type == "premium":
        extras = 1.5
    print(f"extras:{extras}")
    total_price = (
        parking_space.parking_lot.hourly_rate
        * Decimal(duration_hours)
        * Decimal(extras)
    )
    print(total_price)
    return render(
        request,
        "parking/booking_summary.html",
        {
            "start_time": start_time_display,
            "end_time": end_time_display,
            "parking_space": parking_space,
            "total_price": total_price,
        },
    )


stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def create_booking(request):

    if request.method == "POST":
        space_id = request.POST.get("space_id")
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time")
        vehicle_model = request.POST.get("vehicle_model")
        vehicle_number = request.POST.get("vehicle_number")
        try:
            start_time = timezone.make_aware(
                parse_datetime(start_time), timezone.get_current_timezone()
            )
            end_time = timezone.make_aware(
                parse_datetime(end_time), timezone.get_current_timezone()
            )

            if not start_time or not end_time:
                return JsonResponse({"error": "Invalid date format"}, status=400)

            parking_space = ParkingSpace.objects.get(id=space_id)
            if not parking_space.is_available(start_time, end_time):
                return JsonResponse(
                    {"error": "Parking space is not available"}, status=400
                )
            session = BookingService.create_booking(
                request,
                parking_space,
                start_time,
                end_time,
                vehicle_model,
                vehicle_number,
            )
            return redirect(session.url)

        except ParkingSpace.DoesNotExist:
            return JsonResponse({"error": "Invalid parking space"}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def booking_success(request):
    session_id = request.GET.get("session_id")
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            booking_id = session.get("metadata", {}).get("booking_id")
            if booking_id:
                booking = get_object_or_404(Booking, id=booking_id)
                booking.status = "active"
                booking.save()
                payment = StripePayment.objects.filter(booking=booking).first()
                if payment:
                    payment.status = "succeeded"
                    payment.save()
                messages.success(request, "Slot booked Successfully")
                notify_booking_update(
                    space_id=booking.parking_space.id,
                    lot_id=booking.parking_space.parking_lot.id,
                    status="active",
                )
        except stripe.error.StripeError as e:
            print(e)
    return render(request, "parking/booking_success.html")


@login_required
def booking_failure(request):
    session_id = request.GET.get("session_id")
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            booking_id = session.get("metadata", {}).get("booking_id")
            if booking_id:
                with transaction.atomic():
                    booking = get_object_or_404(Booking, id=booking_id)
                    if booking.status != "cancelled":
                        booking.status = "cancelled"
                        booking.save()
                    payment = StripePayment.objects.filter(booking=booking).first()
                    notify_booking_update(
                        space_id=booking.parking_space.id,
                        lot_id=booking.parking_space.parking_lot.id,
                        status="cancelled",
                    )
                    if payment:
                        payment.status = "failed"
                        payment.save()
                messages.error(request, "Slot not booked!")
        except stripe.error.StripeError as e:
            print(e)
    return render(request, "parking/booking_failure.html")


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    event = None

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return JsonResponse({"error": "Invalid payload"}, status=400)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({"error": "Invalid signature"}, status=400)
    session = event["data"]["object"]
    booking_id = session.get("metadata", {}).get("booking_id")
    if event["type"] == "checkout.session.completed":
        if booking_id:
            try:
                booking = Booking.objects.get(id=booking_id)
                booking.status = "active"
                booking.save()

            except Booking.DoesNotExist:
                return JsonResponse({"error": "Booking not found"}, status=404)
    elif event["type"] in [
        "payment_intent.payment_failed",
        "checkout.session.expired",
        "charge.failed",
        "checkout.session.async_payment_failed",
    ]:
        if booking_id:
            try:
                booking = Booking.objects.get(id=booking_id)
                booking.status = "cancelled"
                booking.save()
            except Exception as e:
                print(e)
    return JsonResponse({"status": "success"}, status=200)


@login_required
def booking_detail(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    return render(request, "parking/booking_detail.html", {"booking": booking})


@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if booking.status in ["cancelled", "completed"]:
        messages.info(request, "Booking cannot be cancelled.")
        return redirect("parking:booking_detail", booking_id=booking.id)

    with transaction.atomic():
        booking.status = "cancelled"
        booking.save()

        try:
            payment = StripePayment.objects.get(booking=booking)
            checkout_session = stripe.checkout.Session.retrieve(
                payment.stripe_charge_id
            )
            payment_intent = stripe.PaymentIntent.retrieve(
                checkout_session.payment_intent
            )
            charge_id = payment_intent["latest_charge"]
            refund_amount = int(payment.amount * Decimal("0.5") * 100)
            stripe.Refund.create(
                charge=charge_id,
                amount=refund_amount,
            )

            payment.status = "refunded"
            payment.save()

            messages.success(request, "Booking cancelled. 50% refund issued.")
            notify_booking_update(
                space_id=booking.parking_space.id,
                lot_id=booking.parking_space.parking_lot.id,
                status="cancelled",
            )
        except Exception as e:
            messages.warning(request, f"Booking cancelled but refund failed: {str(e)}")
            StripePayment.objects.filter(booking=booking).update(status="cancelled")

    return redirect("parking:booking_detail", booking_id=booking.id)


@login_required
def user_bookings(request):
    now = timezone.now()
    bookings = (
        Booking.objects.filter(user=request.user)
        .select_related("parking_space__parking_lot__location")
        .order_by("-start_time")
    )

    grouped = {"active": [], "past": [], "cancelled": []}

    for booking in bookings:
        if booking.status == "cancelled":
            grouped["cancelled"].append(booking)
        elif booking.end_time < now or booking.status == "completed":
            grouped["past"].append(booking)
        else:
            grouped["active"].append(booking)

    return render(request, "parking/user_bookings.html", {"grouped_bookings": grouped})
