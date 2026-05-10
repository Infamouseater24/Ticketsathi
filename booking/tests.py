from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Cinema, Screen, Movie, Showtime, Seat, Booking, SeatBooking, Payment, CancellationRequest
from django.utils import timezone
from datetime import timedelta, datetime
import decimal
import os
from unittest.mock import patch

# Set dummy env vars for payment providers to avoid KeyError during test initialization
os.environ.setdefault('ESEWA_SECRET_KEY', 'dummy_key')
os.environ.setdefault('ESEWA_PRODUCT_CODE', 'EPAYTEST')
os.environ.setdefault('ESEWA_SANDBOX', 'True')

class TicketsathiTests(TestCase):
    def setUp(self):
        # 1. Create User
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='password123')
        
        # 2. Create Cinema, Screen, Movie, Showtime
        from django.core.files.uploadedfile import SimpleUploadedFile
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9'
            b'\x04\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00'
            b'\x00\x02\x02\x4c\x01\x00\x3b'
        )
        
        self.cinema = Cinema.objects.create(name="Test Cinema", location="Test Location", address="123 Test St", phone="9876543210")
        self.screen = Screen.objects.create(cinema=self.cinema, name="Screen 1", total_seats=100)
        self.movie = Movie.objects.create(
            title="Test Movie", 
            description="Test Description", 
            duration=120, 
            genre="Action", 
            language="English", 
            rating="U", 
            release_date=timezone.now().date(),
            is_now_showing=True,
            poster=SimpleUploadedFile('test_poster.gif', small_gif, content_type='image/gif')
        )
        self.showtime = Showtime.objects.create(
            movie=self.movie, 
            screen=self.screen, 
            start_time=timezone.now() + timedelta(days=1), 
            end_time=timezone.now() + timedelta(days=1, hours=2), 
            price=300.00
        )
        
        # 3. Create Seats
        self.seat1 = Seat.objects.create(screen=self.screen, row="A", number=1, seat_type="Regular")
        self.seat2 = Seat.objects.create(screen=self.screen, row="A", number=2, seat_type="Regular")

    def test_1_user_login(self):
        """Test Case: User Login (Successful authentication and redirection)"""
        response = self.client.post(reverse('login'), {
            'email': 'test@example.com',
            'password': 'password123'
        })
        # Check if redirected to home (the name is 'home' and path is '')
        self.assertRedirects(response, reverse('home'))
        # Check if user is authenticated
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_2_movie_booking(self):
        """Test Case: Movie Booking (Selected seat successfully reserved)"""
        login_success = self.client.login(username='testuser', password='password123')
        self.assertTrue(login_success)
        response = self.client.post(reverse('select_seats', args=[self.showtime.id]), {
            'seats': [self.seat1.id]
        })
        # Check if redirected to payment page
        self.assertEqual(response.status_code, 302)
        # Check if booking exists
        booking = Booking.objects.get(user=self.user, showtime=self.showtime)
        self.assertEqual(booking.status, 'Pending')
        # Check if seat is reserved in SeatBooking
        seat_booking = SeatBooking.objects.get(showtime=self.showtime, seat=self.seat1)
        self.assertTrue(seat_booking.is_booked)
        self.assertEqual(seat_booking.booking, booking)

    def test_3_payment_verification(self):
        """Test Case: Payment Verification (Booking confirmed after successful payment)"""
        # First, create a pending booking
        booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            total_amount=300.00,
            status='Pending',
            booking_reference='REF123456'
        )
        booking.seats.add(self.seat1)
        SeatBooking.objects.create(showtime=self.showtime, seat=self.seat1, booking=booking, is_booked=True)

        login_success = self.client.login(username='testuser', password='password123')
        self.assertTrue(login_success)
        
        # Simulate successful card payment
        response = self.client.post(reverse('process_payment', args=[booking.id]), {
            'payment_method': 'card',
            'card_number': '1234123412341234',
            'cardholder_name': 'Test User',
            'expiry': '12/25',
            'cvv': '123'
        })
        
        # Check if redirected to confirmation
        self.assertRedirects(response, reverse('booking_confirmation', args=[booking.id]))
        
        # Check if booking status updated
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'Confirmed')
        
        # Check if payment record created
        payment = Payment.objects.get(booking=booking)
        self.assertEqual(payment.status, 'completed')

    def test_4_qr_generation(self):
        """Test Case: QR Ticket Generation (QR-code ticket generated successfully)"""
        booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            total_amount=300.00,
            status='Confirmed',
            booking_reference='QRREF789'
        )
        booking.seats.add(self.seat1)
        
        login_success = self.client.login(username='testuser', password='password123')
        self.assertTrue(login_success)
        response = self.client.get(reverse('booking_confirmation', args=[booking.id]))
        
        self.assertEqual(response.status_code, 200)
        # Check if qr_code is in context
        self.assertIn('qr_code', response.context)
        # QR code should be a non-empty base64 string
        self.assertTrue(len(response.context['qr_code']) > 0)

    def test_5_double_booking_attempt(self):
        """Test Case: Double Booking Attempt (Duplicate booking prevented)"""
        # First user books seat1
        login_success = self.client.login(username='testuser', password='password123')
        self.assertTrue(login_success)
        self.client.post(reverse('select_seats', args=[self.showtime.id]), {'seats': [self.seat1.id]})
        
        # Create second user
        user2 = User.objects.create_user(username='user2', email='user2@example.com', password='password123')
        client2 = Client()
        login_success2 = client2.login(username='user2', password='password123')
        self.assertTrue(login_success2)
        
        # Second user tries to book the same seat
        response = client2.post(reverse('select_seats', args=[self.showtime.id]), {'seats': [self.seat1.id]}, follow=True)
        
        # Check for error message in redirected page
        self.assertContains(response, "One or more selected seats have just been taken")
        
        # Verify only one booking exists for that seat
        self.assertEqual(Booking.objects.filter(showtime=self.showtime, seats=self.seat1).count(), 1)

    def test_6_booking_cancellation(self):
        """Test Case: Booking Cancellation (Booking cancelled successfully)"""
        # Create a confirmed booking
        booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            total_amount=300.00,
            status='Confirmed',
            booking_reference='CANCELREF'
        )
        booking.seats.add(self.seat1)
        SeatBooking.objects.create(showtime=self.showtime, seat=self.seat1, booking=booking, is_booked=True)
        Payment.objects.create(booking=booking, payment_method='card', amount=300.00, transaction_id='TXN123', status='completed')

        # Request cancellation
        login_success = self.client.login(username='testuser', password='password123')
        self.assertTrue(login_success)
        response = self.client.post(reverse('cancel_booking', args=[booking.id]), {
            'reason': 'Changed my mind about this movie. (Long enough reason)'
        })
        
        # Check if cancellation request exists
        cancellation = CancellationRequest.objects.get(booking=booking)
        self.assertEqual(cancellation.status, 'Pending')
        
        # Simulate Admin approval (Manual trigger of the admin action logic)
        from .admin import CancellationRequestAdmin
        from django.contrib.admin.sites import AdminSite
        
        admin_site = AdminSite()
        request_admin = CancellationRequestAdmin(CancellationRequest, admin_site)
        
        # Use a mock request for the admin action
        factory = RequestFactory()
        admin_user = User.objects.create_superuser(username='admin', email='admin@test.com', password='password')
        request = factory.post('/admin/booking/cancellationrequest/')
        request.user = admin_user
        
        # Mock message_user to avoid session/message storage issues in RequestFactory
        with patch.object(CancellationRequestAdmin, 'message_user') as mock_message:
            # Call the action
            request_admin.approve_cancellation(request, CancellationRequest.objects.filter(id=cancellation.id))
        
        # Verify booking is cancelled and seat is released
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'Cancelled')
        
        seat_booking = SeatBooking.objects.get(showtime=self.showtime, seat=self.seat1)
        self.assertFalse(seat_booking.is_booked)
        self.assertIsNone(seat_booking.booking)

    def test_7_admin_movie_management(self):
        """Test Case: Admin Movie Management (Movie added and updated successfully)"""
        # Login as superuser
        admin_user = User.objects.create_superuser(username='admin2', email='admin2@test.com', password='password')
        self.client.login(username='admin2', password='password')
        
        # Add Movie via Admin URL
        add_url = reverse('admin:booking_movie_add')
        response = self.client.post(add_url, {
            'title': 'New Admin Movie',
            'description': 'Description',
            'duration': 150,
            'genre': 'Horror',
            'language': 'Nepali',
            'rating': 'Adult',
            'release_date': '2026-05-10',
            'is_now_showing': 'on', # Checkbox is 'on'
            'images-TOTAL_FORMS': '0',
            'images-INITIAL_FORMS': '0',
            'images-MIN_NUM_FORMS': '0',
            'images-MAX_NUM_FORMS': '1000',
        }, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Movie.objects.filter(title='New Admin Movie').exists())
        
        # Update Movie
        movie = Movie.objects.get(title='New Admin Movie')
        change_url = reverse('admin:booking_movie_change', args=[movie.id])
        response = self.client.post(change_url, {
            'title': 'Updated Admin Movie',
            'description': 'New Description',
            'duration': 150,
            'genre': 'Horror',
            'language': 'Nepali',
            'rating': 'Adult',
            'release_date': '2026-05-10',
            'is_now_showing': 'on',
            'images-TOTAL_FORMS': '0',
            'images-INITIAL_FORMS': '0',
            'images-MIN_NUM_FORMS': '0',
            'images-MAX_NUM_FORMS': '1000',
        }, follow=True)
        
        self.assertEqual(response.status_code, 200)
        movie.refresh_from_db()
        self.assertEqual(movie.title, 'Updated Admin Movie')
