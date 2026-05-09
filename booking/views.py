from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
import random
import string

# UPDATED IMPORT - Add CancellationRequest
from .models import Movie, Cinema, Screen, Showtime, Seat, Booking, SeatBooking, Payment, CancellationRequest
from .forms import SignUpForm, LoginForm

# Payment SDK Imports
from .payments import PaymentRequest, VerifyRequest, EsewaProvider
import json
import logging

logger = logging.getLogger(__name__)

# Initialize Providers (Sandbox Credentials)
import os

esewa_provider = EsewaProvider(
    secret_key=os.environ['ESEWA_SECRET_KEY'], 
    product_code=os.environ.get('ESEWA_PRODUCT_CODE', "EPAYTEST"), 
    sandbox=os.environ.get('ESEWA_SANDBOX', 'True') == 'True'
)

PROVIDERS = {
    'esewa': esewa_provider,
}

def generate_booking_reference():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

def generate_transaction_id():
    return 'TXN' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))

def home(request):
    now_showing = Movie.objects.filter(is_now_showing=True)[:6]
    coming_soon = Movie.objects.filter(is_now_showing=False, release_date__gt=timezone.now())[:6]
    
    context = {
        'now_showing': now_showing,
        'coming_soon': coming_soon,
    }
    return render(request, 'booking/home.html', context)

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('home')
    else:
        form = SignUpForm()
    
    return render(request, 'booking/signup.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    form = LoginForm(request.POST or None)

    if request.method == 'POST':

        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            try:
                user_obj = User.objects.get(email=email)

                user = authenticate(
                    request,
                    username=user_obj.username,
                    password=password
                )

                if user is not None:
                    login(request, user)
                    messages.success(request, 'Logged in successfully!')
                    return redirect('home')

                else:
                    messages.error(request, 'Invalid password')

            except User.DoesNotExist:
                messages.error(request, 'No account found with this email')

    return render(request, 'booking/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('home')

def movies_list(request):
    movies = Movie.objects.filter(is_now_showing=True)
    
    # Filter by genre
    genre = request.GET.get('genre')
    if genre:
        movies = movies.filter(genre__icontains=genre)
    
    # Filter by language
    language = request.GET.get('language')
    if language:
        movies = movies.filter(language=language)
    
    # Search
    search = request.GET.get('search')
    if search:
        movies = movies.filter(Q(title__icontains=search) | Q(description__icontains=search))
    
    context = {
        'movies': movies,
        'genres': Movie.objects.values_list('genre', flat=True).distinct(),
        'languages': Movie.objects.values_list('language', flat=True).distinct(),
    }
    return render(request, 'booking/movies.html', context)

def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    
    # Get available showtimes
    selected_date = request.GET.get('date', timezone.now().date())
    if isinstance(selected_date, str):
        selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    
    selected_cinema = request.GET.get('cinema')
    
    showtimes = Showtime.objects.filter(
        movie=movie,
        start_time__date=selected_date
    ).select_related('screen__cinema').order_by('screen__cinema__name', 'screen__cinema__location', 'start_time')
    
    if selected_cinema:
        showtimes = showtimes.filter(screen__cinema_id=selected_cinema)
    
    # Get all cinemas showing this movie
    cinemas = Cinema.objects.filter(
        screens__showtimes__movie=movie
    ).distinct()
    
    # Generate next 7 days for date selection
    dates = [(timezone.now().date() + timedelta(days=i)) for i in range(7)]
    
    context = {
        'movie': movie,
        'showtimes': showtimes,
        'cinemas': cinemas,
        'dates': dates,
        'selected_date': selected_date,
        'selected_cinema': selected_cinema,
    }
    return render(request, 'booking/movie_detail.html', context)

@login_required
def select_seats(request, showtime_id):
    # Lazy Cleanup: Release any expired bookings before showing the seat map
    Booking.expire_stale_bookings()
    
    showtime = get_object_or_404(Showtime, id=showtime_id)
    screen = showtime.screen
    seats = screen.seats.all()
    
    # Get already booked seats for this showtime
    booked_seats = SeatBooking.objects.filter(
        showtime=showtime,
        is_booked=True
    ).values_list('seat_id', flat=True)
    
    if request.method == 'POST':
        selected_seat_ids = request.POST.getlist('seats')
        
        if not selected_seat_ids:
            messages.error(request, 'Please select at least one seat!')
            return redirect('select_seats', showtime_id=showtime_id)
        
        try:
            # Sort seat IDs to ensure a deterministic locking order and prevent deadlocks
            sorted_seat_ids = sorted([int(id) for id in selected_seat_ids])
            
            with transaction.atomic():
                # ISSUE 1 & 2 FIX: Lock actual Seat rows instead of SeatBooking rows.
                # Since Seat rows are static/pre-existing, select_for_update() will 
                # reliably block other concurrent attempts to book these specific seats.
                locked_seats = Seat.objects.select_for_update().filter(
                    id__in=sorted_seat_ids,
                    screen=screen
                )
                
                # Verify that all requested seats were found and belong to this screen
                if locked_seats.count() != len(sorted_seat_ids):
                    messages.error(request, 'Invalid seat selection.')
                    return redirect('select_seats', showtime_id=showtime_id)

                # Check if any of these seats are ALREADY booked for this specific showtime.
                # No select_for_update needed here because the parent Seat rows are locked.
                already_booked_ids = SeatBooking.objects.filter(
                    showtime=showtime,
                    seat_id__in=sorted_seat_ids,
                    is_booked=True
                ).values_list('seat_id', flat=True)
                
                if already_booked_ids:
                    messages.error(request, 'One or more selected seats have just been taken. Please choose other seats.')
                    return redirect('select_seats', showtime_id=showtime_id)

                # Create booking
                total_amount = len(selected_seat_ids) * float(showtime.price)
                booking = Booking.objects.create(
                    user=request.user,
                    showtime=showtime,
                    total_amount=total_amount,
                    status='Pending',
                    booking_reference=generate_booking_reference()
                )
                
                # Add seats to booking relationship
                booking.seats.set(locked_seats)
                
                # Atomically reserve seats. 
                # We use get_or_create to handle potential existing but 'unbooked' (is_booked=False) records.
                for seat in locked_seats:
                    SeatBooking.objects.update_or_create(
                        showtime=showtime,
                        seat=seat,
                        defaults={'is_booked': True, 'booking': booking}
                    )
                
                return redirect('payment_page', booking_id=booking.id)
                
        except Exception as e:
            logger.error(f"Booking Error: {e}")
            messages.error(request, 'An error occurred while processing your booking. Please try again.')
            return redirect('select_seats', showtime_id=showtime_id)
    
    context = {
        'showtime': showtime,
        'seats': seats,
        'booked_seats': list(booked_seats),
        'screen': screen,
    }
    return render(request, 'booking/select_seats.html', context)

@login_required
def payment_page(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Check if booking is already confirmed
    if booking.status == 'Confirmed':
        return redirect('booking_confirmation', booking_id=booking.id)
    
    context = {
        'booking': booking,
    }
    return render(request, 'booking/payment.html', context)

@login_required
def process_payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        
        # Validate payment method
        if payment_method not in ['card', 'esewa']:
            messages.error(request, 'Invalid payment method!')
            return redirect('payment_page', booking_id=booking.id)
        
        # CARD PAYMENT (Simulation)
        if payment_method == 'card':
            card_number = request.POST.get('card_number')
            cardholder_name = request.POST.get('cardholder_name')
            expiry = request.POST.get('expiry')
            cvv = request.POST.get('cvv')
            
            # Basic validation
            if not all([card_number, cardholder_name, expiry, cvv]):
                messages.error(request, 'Please fill in all card details!')
                return redirect('payment_page', booking_id=booking.id)
            
            with transaction.atomic():
                # Lock the booking
                booking = Booking.objects.select_for_update().get(id=booking_id)
                
                if booking.status != 'Pending':
                    messages.error(request, 'Booking is no longer pending.')
                    return redirect('home')

                # SIMULATION: If card number starts with '0000', simulate a definitive failure
                if card_number.startswith('0000'):
                    # ISSUE 4 FIX: Immediate release
                    SeatBooking.objects.filter(booking=booking).update(is_booked=False, booking=None)
                    booking.status = 'Cancelled'
                    booking.save()
                    
                    Payment.objects.create(
                        booking=booking,
                        payment_method=payment_method,
                        amount=booking.total_amount,
                        transaction_id=generate_transaction_id(),
                        status='failed',
                        card_number=card_number[-4:],
                        cardholder_name=cardholder_name
                    )
                    messages.error(request, 'Payment failed. Your seats have been released.')
                    return redirect('home')

                # Create payment record
                payment = Payment.objects.create(
                    booking=booking,
                    payment_method=payment_method,
                    amount=booking.total_amount,
                    transaction_id=generate_transaction_id(),
                    status='completed',
                    card_number=card_number[-4:],
                    cardholder_name=cardholder_name
                )
                
                # Update booking status to Confirmed
                booking.status = 'Confirmed'
                booking.save()
            
            messages.success(request, 'Payment successful! Your booking is confirmed.')
            return redirect('booking_confirmation', booking_id=booking.id)

        # WALLET PAYMENTS (Real SDK Integration)
        provider = PROVIDERS.get(payment_method)
        if not provider:
             messages.error(request, 'Payment provider not configured.')
             return redirect('payment_page', booking_id=booking.id)

        from django.urls import reverse
        callback_url = request.build_absolute_uri(reverse('payment_callback', kwargs={'provider_id': payment_method}))
        
        # Initiate Payment
        try:
            payment_request = PaymentRequest(
                amount=float(booking.total_amount),
                order_id=booking.booking_reference,
                description=f"Booking {booking.booking_reference}",
                callback_url=callback_url,
                customer_email=request.user.email,
                customer_phone="" # Add phone if available in profile
            )
            
            response = provider.initiate_payment(payment_request)
            
            # Save a pending payment record to track this attempt
            # We use the order_id/transaction_id to match later
            # Update or create to avoid duplicates on retry
            Payment.objects.update_or_create(
                booking=booking,
                defaults={
                    'payment_method': payment_method,
                    'amount': booking.total_amount,
                    'transaction_id': response.transaction_id or generate_transaction_id(), # Use provider's ID if available
                    'status': 'pending',
                }
            )
            
            if response.is_form_post:
                # Render a template that auto-submits the form
                context = {
                    'target_url': response.target_url,
                    'form_fields': response.form_fields,
                }
                return render(request, 'booking/payment_redirect.html', context)
            else:
                # Direct redirect
                if response.target_url:
                    return redirect(response.target_url)
                else:
                     messages.error(request, 'Failed to get payment URL from provider.')
                     return redirect('payment_page', booking_id=booking.id)
                     
        except Exception as e:
            logger.error(f"Payment Initiation Error: {e}")
            messages.error(request, f"Payment error: {str(e)}")
            return redirect('payment_page', booking_id=booking.id)
            
    return redirect('payment_page', booking_id=booking.id)

@csrf_exempt
def payment_callback(request, provider_id):
    """
    Handles callback from payment providers.
    Note: @csrf_exempt is needed because some providers verify via POST from their server or client browser without CSRF token.
    However, for standard browser redirects, CSRF might be fine if cookies are present.
    Safest is `csrf_exempt` for the callback entry point.
    """
    provider = PROVIDERS.get(provider_id)
    if not provider:
        return HttpResponse("Invalid Provider", status=400)
    
    # Adapt Query Params / POST Data to VerifyRequest
    # Start with GET params
    data = request.GET.dict()
    # Merge POST data if any (e.g. eSewa might POST, ConnectIPS POSTs)
    if request.method == 'POST':
        data.update(request.POST.dict())
        
    # We need to find the booking to get expected amount
    # This is tricky because we need to parse the Order ID from the params BEFORE verification
    # But usually verification needs expected amount.
    
    # Parsing logic depends on provider
    order_id = None
    if provider_id == 'esewa':
        # eSewa: encoded 'data' contains transaction_uuid which starts with order_id
        # We handle this inside verify or pre-parse?
        # Actually EsewaProvider.verify_payment parses 'data'.
        # We can pass specific params.
        pass
    elif provider_id == 'khalti':
        # pidx is ref
        pass
    elif provider_id == 'fonepay':
         order_id = data.get("PRN")

    # To make it generic: verify_payment should optionally take expected params, 
    # OR return the parsed ID so we can validate it.
    # Our Interface: verify_payment(VerifyRequest) -> VerifyResponse
    
    # Let's try to verify without strict expectation first if possible, or fetch booking if we can extract ID.
    # For eSewa, we can't easily extract ID without decoding.
    # So `verify_payment` should do the decoding.
    
    verify_req = VerifyRequest(
        encoded_params=data,
        expected_amount=0, # Placeholder, will validate after
        expected_order_id=""
    )
    
    try:
        with transaction.atomic():
            # ISSUE 3 FIX: Acquire lock on Booking immediately. 
            # This serializes the callback and the cleanup job.
            try:
                # We use the generic provider logic to get ID, but we need the Booking first if possible
                # or find it via transaction_id.
                
                # First, we need to know WHICH booking we are talking about to lock it.
                # Since EsewaProvider.verify_payment parses the ID, let's call it first 
                # but without side effects yet.
                result = provider.verify_payment(verify_req)
                
                # Try to find booking to lock it
                booking = None
                try:
                    payment = Payment.objects.select_for_update().get(transaction_id=result.transaction_id)
                    booking = payment.booking
                except Payment.DoesNotExist:
                    booking_ref = ""
                    if provider_id == 'esewa':
                        booking_ref = result.gateway_ref.rsplit('-', 1)[0] if result.gateway_ref else ""
                    elif provider_id == 'khalti':
                        booking_ref = result.raw_response.get("purchase_order_id", "")
                    elif provider_id == 'fonepay':
                        booking_ref = result.gateway_ref
                    
                    if booking_ref:
                        booking = Booking.objects.select_for_update().get(booking_reference=booking_ref)

                if not booking:
                    return HttpResponse("Booking not found", status=404)

                if result.success:
                    # Idempotent State Transition: Only confirm if Pending
                    if booking.status == 'Pending':
                        # Update Payment record
                        Payment.objects.update_or_create(
                             booking=booking,
                             defaults={
                                 'status': 'completed',
                                 'transaction_id': result.transaction_id,
                                 'gateway_ref': result.gateway_ref,
                                 'raw_response': result.raw_response,
                                 'payment_method': provider_id,
                                 'amount': booking.total_amount
                             }
                        )
                        
                        booking.status = 'Confirmed'
                        booking.save()
                        messages.success(request, f"Payment successful via {provider_id.title()}!")
                    elif booking.status == 'Confirmed':
                        messages.info(request, "Payment already processed.")
                    else:
                        # ISSUE 3: Payment succeeded but booking was already Cancelled by cleanup!
                        # In production, this requires a manual refund flow or "resurrecting" if seats still available.
                        # For now, we keep it Cancelled and log for admin.
                        logger.error(f"Payment SUCCESS for CANCELLED booking: {booking.booking_reference}. Manual refund required.")
                        messages.warning(request, "Payment was successful, but the booking had already expired. Please contact support.")

                    return redirect('booking_confirmation', booking_id=booking.id)
                else:
                    # ISSUE 4 FIX: Immediate release on definitive failure
                    if booking.status == 'Pending':
                        # Release seats immediately
                        SeatBooking.objects.filter(booking=booking).update(is_booked=False, booking=None)
                        booking.status = 'Cancelled'
                        booking.save()
                        
                        Payment.objects.update_or_create(
                            booking=booking,
                            defaults={
                                'status': 'failed',
                                'transaction_id': result.transaction_id or generate_transaction_id(),
                                'raw_response': result.raw_response,
                                'payment_method': provider_id,
                            }
                        )
                        messages.error(request, f"Payment failed: {result.status}. Seats have been released.")
                    
                    return redirect('home')

            except Booking.DoesNotExist:
                return HttpResponse("Booking not found", status=404)
            except Exception as e:
                logger.error(f"Transaction Error: {e}")
                raise e

            
    except Exception as e:
        logger.error(f"Callback Error: {e}")
        messages.error(request, "An error occurred during payment verification.")
        return redirect('home')

from .utils import generate_qr_code

@login_required
def booking_confirmation(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Get payment details if exists
    payment = None
    try:
        payment = booking.payment
    except Payment.DoesNotExist:
        pass
    
    # Generate QR Code Data
    qr_data = f"Booking ID: {booking.booking_reference}\n"
    qr_data += f"Movie: {booking.showtime.movie.title}\n"
    qr_data += f"Time: {booking.showtime.start_time}\n"
    qr_data += f"Seats: {', '.join([str(s) for s in booking.seats.all()])}\n"
    qr_data += f"User: {booking.user.username}"
    
    qr_code = generate_qr_code(qr_data)
    
    context = {
        'booking': booking,
        'payment': payment,
        'qr_code': qr_code,
    }
    return render(request, 'booking/booking_confirmation.html', context)

@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user).order_by('-booking_date')
    
    context = {
        'bookings': bookings,
    }
    return render(request, 'booking/my_bookings.html', context)

# ============================================
# NEW CANCELLATION VIEWS
# ============================================

@login_required
def request_cancellation(request, booking_id):
    """Display the cancellation request form"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Check if can request cancellation
    if not booking.can_request_cancellation():
        messages.error(request, 'This booking cannot be cancelled or already has a pending cancellation request.')
        return redirect('my_bookings')
    
    context = {
        'booking': booking,
    }
    return render(request, 'booking/request_cancellation.html', context)

@login_required
def cancel_booking(request, booking_id):
    """Process the cancellation request"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        
        if not reason:
            messages.error(request, 'Please provide a reason for cancellation.')
            return redirect('request_cancellation', booking_id=booking.id)
        
        if len(reason) < 10:
            messages.error(request, 'Reason must be at least 10 characters long.')
            return redirect('request_cancellation', booking_id=booking.id)
        
        # Check if can request cancellation
        if not booking.can_request_cancellation():
            messages.error(request, 'This booking cannot be cancelled.')
            return redirect('my_bookings')
        
        # Prevent duplicate cancellation request
        if hasattr(booking, 'cancellation_request'):
            messages.error(request, 'A cancellation request for this booking already exists.')
            return redirect('request_cancellation', booking_id=booking.id)
        CancellationRequest.objects.create(
            booking=booking,
            reason=reason
        )
        messages.success(request, 'Cancellation request submitted successfully! Our admin will review it shortly.')
        return redirect('my_bookings')
    
    return redirect('request_cancellation', booking_id=booking.id)
    return redirect('request_cancellation', booking_id=booking.id)

# ============================================
# FOOTER PAGES
# ============================================

def cinemas_list(request):
    cinemas = Cinema.objects.all().prefetch_related('screens')
    return render(request, 'booking/cinemas.html', {'cinemas': cinemas})

def coming_soon(request):
    movies = Movie.objects.filter(is_now_showing=False, release_date__gt=timezone.now()).order_by('release_date')
    return render(request, 'booking/coming_soon.html', {'movies': movies})

