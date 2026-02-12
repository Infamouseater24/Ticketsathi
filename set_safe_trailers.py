import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cinema_booking.settings')
django.setup()
from booking.models import Movie

# Use Big Buck Bunny for all trailers to test connectivity/embedding logic
# If this works, the previous error was definitely copyright blocking on localhost.
SAFE_TRAILER = "https://www.youtube.com/watch?v=YE7VzlLtp-4"

print("Setting all trailers to Big Buck Bunny (Safe Test)...")
for m in Movie.objects.all():
    m.trailer_url = SAFE_TRAILER
    m.save()
    print(f"Updated {m.title}")

print("Done.")
