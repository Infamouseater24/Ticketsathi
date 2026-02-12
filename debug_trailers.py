import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cinema_booking.settings')
django.setup()
from booking.models import Movie

print(f"{'TITLE':<30} | {'URL':<50} | {'ID':<15}")
print("-" * 100)
for m in Movie.objects.all():
    id = m.get_trailer_id()
    print(f"{m.title:<30} | {m.trailer_url[:50]:<50} | {id if id else 'None':<15}")
