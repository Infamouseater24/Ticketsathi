from django.contrib import admin
from django.db import transaction
from django.utils import timezone
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import Cinema, Movie, Screen, Showtime, Seat, Booking, Payment, CancellationRequest, SeatBooking, MovieImage
from .forms import BulkShowtimeForm, BulkSeatForm
from datetime import datetime, timedelta

class MovieImageInline(admin.TabularInline):
    model = MovieImage
    extra = 3

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ['title_display', 'genre', 'language', 'rating', 'release_date', 'is_now_showing']
    list_filter = ['is_now_showing', 'rating', 'genre', 'language']
    search_fields = ['title', 'description']
    inlines = [MovieImageInline]
    list_editable = ['is_now_showing']
    
    def title_display(self, obj):
        return f"{obj.title} ({obj.release_date.year})"
    title_display.short_description = 'Movie'


@admin.register(Cinema)
class CinemaAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'phone']
    search_fields = ['name', 'location']


@admin.register(Screen)
class ScreenAdmin(admin.ModelAdmin):
    list_display = ['name', 'cinema', 'total_seats', 'generate_seats_link']
    list_filter = ['cinema']

    def generate_seats_link(self, obj):
        from django.utils.html import format_html
        return format_html('<a class="button" href="{}/generate-seats/">Generate Seats</a>', obj.id)
    generate_seats_link.short_description = 'Actions'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<int:screen_id>/generate-seats/', self.admin_site.admin_view(self.generate_seats_view), name='booking_screen_generate_seats'),
        ]
        return custom_urls + urls

    def generate_seats_view(self, request, screen_id):
        screen = get_object_or_404(Screen, id=screen_id)
        if request.method == 'POST':
            form = BulkSeatForm(request.POST)
            if form.is_valid():
                rows_count = form.cleaned_data['rows']
                seats_per_row = form.cleaned_data['seats_per_row']
                
                total_seats = rows_count * seats_per_row
                vip_count = int(total_seats * 0.05)
                premium_count = int(total_seats * 0.20)
                
                import string
                seats_to_create = []
                
                # We build the list of all seats first
                all_seat_coords = []
                for row_idx in range(rows_count):
                    if row_idx < 26:
                        row_label = string.ascii_uppercase[row_idx]
                    else:
                        row_label = string.ascii_uppercase[(row_idx // 26) - 1] + string.ascii_uppercase[row_idx % 26]
                    
                    for num in range(1, seats_per_row + 1):
                        all_seat_coords.append((row_label, num))
                
                # Far from screen means the last rows (e.g. Row J, K, L...)
                # We reverse the list to start from the back
                all_seat_coords.reverse()
                
                for i, (row_label, num) in enumerate(all_seat_coords):
                    if i < vip_count:
                        s_type = 'VIP'
                    elif i < (vip_count + premium_count):
                        s_type = 'Premium'
                    else:
                        s_type = 'Regular'
                    
                    seats_to_create.append(Seat(
                        screen=screen,
                        row=row_label,
                        number=num,
                        seat_type=s_type
                    ))
                
                with transaction.atomic():
                    created = Seat.objects.bulk_create(seats_to_create, ignore_conflicts=True)
                
                self.message_user(request, f"Generated {len(created)} seats. (75% Regular, 20% Premium, 5% VIP from the back)")
                return HttpResponseRedirect("../../../") # Back to screen list
        else:
            form = BulkSeatForm()

        context = self.admin_site.each_context(request)
        context.update({
            'title': f'Generate Seats for {screen.name}',
            'form': form,
            'screen': screen,
            'opts': self.model._meta,
        })
        return render(request, 'admin/bulk_add_showtimes.html', context) # Reusing the same template structure

@admin.register(Showtime)
class ShowtimeAdmin(admin.ModelAdmin):
    list_display = ['movie', 'screen', 'start_time', 'price']
    list_filter = ['movie', 'screen__cinema', 'start_time']
    date_hierarchy = 'start_time'
    list_editable = ['price']

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('bulk-add/', self.admin_site.admin_view(self.bulk_add_view), name='booking_showtime_bulk_add'),
        ]
        return custom_urls + urls

    def bulk_add_view(self, request):
        if request.method == 'POST':
            form = BulkShowtimeForm(request.POST)
            if form.is_valid():
                movie = form.cleaned_data['movie']
                screen = form.cleaned_data['screen']
                start_date = form.cleaned_data['start_date']
                end_date = form.cleaned_data['end_date']
                show_times_str = form.cleaned_data['show_times']
                price = form.cleaned_data['price']

                show_times = [t.strip() for t in show_times_str.split(',')]
                
                total_created = 0
                days_range = (end_date - start_date).days + 1
                
                for day_offset in range(days_range):
                    current_date = start_date + timedelta(days=day_offset)
                    for time_str in show_times:
                        try:
                            hour, minute = map(int, time_str.split(':'))
                            start_dt = datetime.combine(current_date, datetime.min.time().replace(hour=hour, minute=minute))
                            end_dt = start_dt + timedelta(minutes=movie.duration)
                            
                            Showtime.objects.create(
                                movie=movie,
                                screen=screen,
                                start_time=start_dt,
                                end_time=end_dt,
                                price=price
                            )
                            total_created += 1
                        except Exception as e:
                            self.message_user(request, f"Error creating showtime at {time_str} on {current_date}: {e}", level=messages.ERROR)

                self.message_user(request, f"Successfully created {total_created} showtimes.")
                return HttpResponseRedirect("../")
        else:
            form = BulkShowtimeForm()

        context = self.admin_site.each_context(request)
        context.update({
            'title': 'Bulk Add Showtimes',
            'form': form,
            'opts': self.model._meta,
        })
        return render(request, 'admin/bulk_add_showtimes.html', context)

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