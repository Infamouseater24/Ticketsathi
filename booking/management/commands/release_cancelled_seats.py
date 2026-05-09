# Create this file: booking/management/commands/release_cancelled_seats.py
# Run with: python manage.py release_cancelled_seats

from django.core.management.base import BaseCommand
from django.db import transaction
from booking.models import Booking, SeatBooking

class Command(BaseCommand):
    help = 'Release seats for cancelled or expired pending bookings'

    def handle(self, *args, **options):
        # 1. Expire stale pending bookings (using expires_at field)
        # ISSUE 5 & 6: Production-grade cleanup using explicit timestamps
        expired_count = Booking.expire_stale_bookings()
        if expired_count > 0:
            self.stdout.write(self.style.SUCCESS(f"SUCCESS: Expired {expired_count} stale pending bookings"))
        
        # 2. Find all cancelled bookings that still have locked seats
        # This handles cases where a booking was cancelled but seats weren't released (e.g. crash)
        cancelled_bookings = Booking.objects.filter(status='Cancelled')
        
        total_released = 0
        with transaction.atomic():
            for booking in cancelled_bookings:
                # Find SeatBooking records that are still marked as booked for this booking
                still_booked = SeatBooking.objects.filter(
                    booking=booking,
                    is_booked=True
                )
                
                if still_booked.exists():
                    released = still_booked.update(is_booked=False, booking=None)
                    total_released += released
                    self.stdout.write(f"Released {released} seats for booking {booking.booking_reference}")
        
        if total_released > 0:
            self.stdout.write(self.style.SUCCESS(f"SUCCESS: Total additional seats released: {total_released}"))
        elif expired_count == 0:
            self.stdout.write(self.style.WARNING("No seats needed to be released"))

