# Create this file: booking/management/commands/release_cancelled_seats.py
# Run with: python manage.py release_cancelled_seats

from django.core.management.base import BaseCommand
from booking.models import Booking, SeatBooking

class Command(BaseCommand):
    help = 'Release seats for cancelled bookings'

    def handle(self, *args, **options):
        # Find all cancelled bookings
        cancelled_bookings = Booking.objects.filter(status='Cancelled')
        
        self.stdout.write(f"Found {cancelled_bookings.count()} cancelled bookings")
        
        total_released = 0
        for booking in cancelled_bookings:
            # Get seat IDs from this booking
            seat_ids = list(booking.seats.values_list('id', flat=True))
            
            # Find SeatBooking records that are still marked as booked
            still_booked = SeatBooking.objects.filter(
                showtime=booking.showtime,
                seat_id__in=seat_ids,
                is_booked=True
            )
            
            if still_booked.exists():
                self.stdout.write(f"\nBooking: {booking.booking_reference}")
                self.stdout.write(f"  Showtime: {booking.showtime}")
                self.stdout.write(f"  Seats still marked as booked: {still_booked.count()}")
                
                # Release them
                released = still_booked.update(is_booked=False, booking=None)
                total_released += released
                
                self.stdout.write(self.style.SUCCESS(f"  ✓ Released {released} seats"))
        
        if total_released > 0:
            self.stdout.write(self.style.SUCCESS(f"\n✅ Total seats released: {total_released}"))
        else:
            self.stdout.write(self.style.WARNING("\n⚠️  No seats needed to be released"))