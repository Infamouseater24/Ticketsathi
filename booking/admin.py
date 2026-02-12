from django.contrib import admin
from django.utils import timezone
from .models import Cinema, Movie, Screen, Showtime, Seat, Booking, Payment, CancellationRequest, SeatBooking

@admin.register(Cinema)
class CinemaAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'phone']
    search_fields = ['name', 'location']

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ['title_display', 'genre', 'language', 'rating', 'release_date', 'is_now_showing']
    list_filter = ['is_now_showing', 'rating', 'genre', 'language']
    search_fields = ['title', 'description']
    list_editable = ['is_now_showing']
    
    def title_display(self, obj):
        return f"{obj.title} ({obj.release_date.year})"
    title_display.short_description = 'Movie'

@admin.register(Screen)
class ScreenAdmin(admin.ModelAdmin):
    list_display = ['name', 'cinema', 'total_seats']
    list_filter = ['cinema']

@admin.register(Showtime)
class ShowtimeAdmin(admin.ModelAdmin):
    list_display = ['movie', 'screen', 'start_time', 'price']
    list_filter = ['movie', 'screen__cinema', 'start_time']
    date_hierarchy = 'start_time'
    list_editable = ['price']

@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ['screen', 'row', 'number', 'seat_type']
    list_filter = ['screen', 'seat_type']

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['booking_reference', 'user', 'showtime', 'total_amount', 'status', 'booking_date']
    list_filter = ['status', 'booking_date']
    search_fields = ['booking_reference', 'user__username']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'booking', 'payment_method', 'amount', 'status', 'payment_date']
    list_filter = ['status', 'payment_method', 'payment_date']
    search_fields = ['transaction_id', 'booking__booking_reference']
    readonly_fields = ['transaction_id', 'payment_date']

@admin.register(SeatBooking)
class SeatBookingAdmin(admin.ModelAdmin):
    list_display = ['showtime', 'seat', 'booking', 'is_booked']
    list_filter = ['is_booked', 'showtime']
    search_fields = ['booking__booking_reference', 'seat__row']

@admin.register(CancellationRequest)
class CancellationRequestAdmin(admin.ModelAdmin):
    list_display = ['booking', 'status', 'request_date', 'reviewed_by', 'review_date']
    list_filter = ['status', 'request_date', 'refund_processed']
    search_fields = ['booking__booking_reference', 'booking__user__username', 'reason']
    readonly_fields = ['booking', 'reason', 'request_date']
    
    fieldsets = (
        ('Request Information', {
            'fields': ('booking', 'reason', 'request_date', 'status')
        }),
        ('Admin Review', {
            'fields': ('admin_response', 'reviewed_by', 'review_date')
        }),
        ('Refund Information', {
            'fields': ('refund_amount', 'refund_processed')
        }),
    )
    
    actions = ['approve_cancellation', 'reject_cancellation']
    
    def approve_cancellation(self, request, queryset):
        """Approve selected cancellation requests and release seats"""
        count = 0
        total_seats_released = 0
        
        for cancellation in queryset.filter(status='Pending'):
            booking = cancellation.booking
            
            # Update cancellation request
            cancellation.status = 'Approved'
            cancellation.reviewed_by = request.user
            cancellation.review_date = timezone.now()
            cancellation.refund_amount = booking.total_amount
            cancellation.save()
            
            # Update booking status
            booking.status = 'Cancelled'
            booking.save()
            
            # FIXED: Release seats - use booking reference directly
            # Delete or set is_booked to False for all SeatBooking entries related to this booking
            seat_bookings = SeatBooking.objects.filter(booking=booking)
            
            print(f"[ADMIN ACTION] Found {seat_bookings.count()} seat bookings for {booking.booking_reference}")
            
            # Method 1: Set is_booked to False and clear the booking reference
            released = seat_bookings.update(is_booked=False, booking=None)
            
            # Alternative Method 2: Delete the SeatBooking entries entirely (uncomment if preferred)
            # released = seat_bookings.count()
            # seat_bookings.delete()
            
            total_seats_released += released
            
            # Debug output
            print(f"[ADMIN ACTION] Approved cancellation for booking: {booking.booking_reference}")
            print(f"[ADMIN ACTION] Released {released} seats for showtime: {booking.showtime}")
            print(f"[ADMIN ACTION] Seat IDs released: {list(booking.seats.values_list('id', flat=True))}")
            
            # Verify seats are released
            remaining_bookings = SeatBooking.objects.filter(
                showtime=booking.showtime,
                seat__in=booking.seats.all(),
                is_booked=True
            )
            if remaining_bookings.exists():
                print(f"[WARNING] Some seats still marked as booked: {list(remaining_bookings.values_list('seat_id', flat=True))}")
            else:
                print(f"[SUCCESS] All seats successfully released!")
            
            # Update payment status
            try:
                payment = booking.payment
                payment.status = 'refunded'
                payment.refund_date = timezone.now()
                payment.refund_amount = booking.total_amount
                payment.save()
                cancellation.refund_processed = True
                cancellation.save()
            except Payment.DoesNotExist:
                print(f"[ADMIN ACTION] No payment found for booking {booking.booking_reference}")
                pass
            
            count += 1
        
        message = f"✅ {count} cancellation(s) approved successfully. {total_seats_released} seat(s) released and available for booking."
        self.message_user(request, message)
        
    approve_cancellation.short_description = "✅ Approve selected cancellations"
    
    def reject_cancellation(self, request, queryset):
        """Reject selected cancellation requests"""
        count = 0
        for cancellation in queryset.filter(status='Pending'):
            cancellation.status = 'Rejected'
            cancellation.reviewed_by = request.user
            cancellation.review_date = timezone.now()
            cancellation.save()
            count += 1
            
            print(f"[ADMIN ACTION] Rejected cancellation for booking: {cancellation.booking.booking_reference}")
        
        self.message_user(request, f"❌ {count} cancellation(s) rejected.")
        
    reject_cancellation.short_description = "❌ Reject selected cancellations"