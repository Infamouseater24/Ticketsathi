from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class Cinema(models.Model):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    
    def __str__(self):
        return f"{self.name} - {self.location}"

class MovieImage(models.Model):
    movie = models.ForeignKey('Movie', on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='movie_gallery/')
    caption = models.CharField(max_length=200, blank=True)
    
    def __str__(self):
        return f"Image for {self.movie.title}"

class Movie(models.Model):
    RATING_CHOICES = [
        ('U', 'Universal'),
        ('PG', 'Parental Guidance'),
        ('Adult', 'Adult'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    duration = models.IntegerField(help_text="Duration in minutes")
    genre = models.CharField(max_length=100)
    language = models.CharField(max_length=50)
    rating = models.CharField(max_length=10, choices=RATING_CHOICES)
    release_date = models.DateField()
    poster = models.ImageField(upload_to='movie_posters/', blank=True, null=True)
    trailer_url = models.URLField(blank=True, null=True)
    banner = models.ImageField(upload_to='movie_banners/', blank=True, null=True, help_text="Wide image for hero section/backdrop (1920x600 recommended)")
    is_now_showing = models.BooleanField(default=True)
    
    def __str__(self):
        return self.title

    def get_trailer_id(self):
        """Extracts YouTube ID from URL"""
        if not self.trailer_url:
            return None
        import re
        # Robust RegEx to find YouTube ID
        regex = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
        match = re.search(regex, self.trailer_url)
        if match:
            return match.group(1)
        return None

class Screen(models.Model):
    cinema = models.ForeignKey(Cinema, on_delete=models.CASCADE, related_name='screens')
    name = models.CharField(max_length=50)
    total_seats = models.IntegerField()
    
    def __str__(self):
        return f"{self.cinema.name} - {self.name}"

class Showtime(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='showtimes')
    screen = models.ForeignKey(Screen, on_delete=models.CASCADE, related_name='showtimes')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    
    class Meta:
        ordering = ['start_time']
    
    def __str__(self):
        return f"{self.movie.title} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"

class Seat(models.Model):
    SEAT_TYPE_CHOICES = [
        ('Regular', 'Regular'),
        ('Premium', 'Premium'),
        ('VIP', 'VIP'),
    ]
    
    screen = models.ForeignKey(Screen, on_delete=models.CASCADE, related_name='seats')
    row = models.CharField(max_length=2)
    number = models.IntegerField()
    seat_type = models.CharField(max_length=20, choices=SEAT_TYPE_CHOICES, default='Regular')
    
    class Meta:
        unique_together = ['screen', 'row', 'number']
        ordering = ['row', 'number']
    
    def __str__(self):
        return f"{self.row}{self.number}"

class Booking(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    showtime = models.ForeignKey(Showtime, on_delete=models.CASCADE, related_name='bookings')
    seats = models.ManyToManyField(Seat)
    booking_date = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending', db_index=True)
    booking_reference = models.CharField(max_length=20, unique=True)

    def save(self, *args, **kwargs):
        if not self.id and not self.expires_at:
            from django.utils import timezone
            from datetime import timedelta
            self.expires_at = timezone.now() + timedelta(minutes=15)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.booking_reference} - {self.user.username}"
    
    def can_request_cancellation(self):
        """Check if booking can be cancelled"""
        if self.status == 'Cancelled':
            return False
        # Check if there's already a pending cancellation request
        try:
            if self.cancellation_request.status == 'Pending':
                return False
        except:
            pass
        return True

    @classmethod
    def expire_stale_bookings(cls):
        """
        Releases seats for bookings that have passed their 'expires_at' time.
        Uses select_for_update to prevent races with payment callbacks.
        """
        from django.utils import timezone
        from django.db import transaction

        now = timezone.now()
        # Find bookings that are Pending and expired
        expired_bookings = cls.objects.filter(
            status='Pending',
            expires_at__lt=now
        )
        
        count = 0
        # Process in a transaction with locking
        with transaction.atomic():
            # We lock the bookings to ensure the callback doesn't try to confirm them at the same time
            # Using .select_for_update() on the queryset
            locked_bookings = expired_bookings.select_for_update(skip_locked=True)
            
            for booking in locked_bookings:
                # Release the SeatBooking records
                from .models import SeatBooking
                SeatBooking.objects.filter(booking=booking).update(is_booked=False, booking=None)
                
                # Mark booking as Cancelled
                booking.status = 'Cancelled'
                booking.save()
                count += 1
        
        return count

class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('card', 'Credit/Debit Card'),
        ('esewa', 'eSewa'),
        ('khalti', 'Khalti'),
        ('fonepay', 'FonePay'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    transaction_id = models.CharField(max_length=100, unique=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # Card payment fields (optional)
    card_number = models.CharField(max_length=4, blank=True, null=True)
    cardholder_name = models.CharField(max_length=100, blank=True, null=True)
    
    # Refund fields
    refund_date = models.DateTimeField(null=True, blank=True)
    refund_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    # Gateway fields
    gateway_ref = models.CharField(max_length=100, blank=True, null=True, help_text="Reference ID from the payment gateway")
    raw_response = models.JSONField(blank=True, null=True, help_text="Raw response from the payment gateway")
    
    def __str__(self):
        return f"Payment {self.transaction_id} - {self.booking.booking_reference}"

class CancellationRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='cancellation_request')
    reason = models.TextField(help_text="Reason for cancellation")
    request_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    # Admin response
    admin_response = models.TextField(blank=True, null=True, help_text="Admin's response/notes")
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_cancellations')
    review_date = models.DateTimeField(null=True, blank=True)
    # Refund details
    refund_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    refund_processed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-request_date']

    def save(self, *args, **kwargs):
        # If status is being set to Approved, update booking status to Cancelled
        if self.pk is not None:
            old = CancellationRequest.objects.get(pk=self.pk)
            if old.status != 'Approved' and self.status == 'Approved':
                self.booking.status = 'Cancelled'
                self.booking.save()
        elif self.status == 'Approved':
            self.booking.status = 'Cancelled'
            self.booking.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Cancellation Request - {self.booking.booking_reference} ({self.status})"

class SeatBooking(models.Model):
    """Tracks which seats are booked for each showtime"""
    showtime = models.ForeignKey(Showtime, on_delete=models.CASCADE)
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, null=True, blank=True)
    is_booked = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['showtime', 'seat']
    
    def __str__(self):
        return f"{self.showtime} - {self.seat}"