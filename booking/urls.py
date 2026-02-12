from django.urls import path
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    # Home
    path('', views.home, name='home'),
    
    # Authentication
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Movies
    path('movies/', views.movies_list, name='movies'),
    path('movie/<int:movie_id>/', views.movie_detail, name='movie_detail'),
    
    # Booking
    path('select-seats/<int:showtime_id>/', views.select_seats, name='select_seats'),
    path('payment/<int:booking_id>/', views.payment_page, name='payment_page'),
    path('process-payment/<int:booking_id>/', views.process_payment, name='process_payment'),
    path('booking-confirmation/<int:booking_id>/', views.booking_confirmation, name='booking_confirmation'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    
    path('request-cancellation/<int:booking_id>/', views.request_cancellation, name='request_cancellation'),
    path('cancel-booking/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    
    # Payment Callback
    path('payment/callback/<str:provider_id>/', views.payment_callback, name='payment_callback'),
    
    # Footer Pages
    path('cinemas/', views.cinemas_list, name='cinemas_list'),
    path('coming-soon/', views.coming_soon, name='coming_soon'),
    path('offers/', TemplateView.as_view(template_name='booking/offers.html'), name='offers'),
    path('help/', TemplateView.as_view(template_name='booking/help.html'), name='help'),
    path('terms/', TemplateView.as_view(template_name='booking/terms.html'), name='terms'),
    path('privacy/', TemplateView.as_view(template_name='booking/privacy.html'), name='privacy'),
    path('faq/', TemplateView.as_view(template_name='booking/faq.html'), name='faq'),
]