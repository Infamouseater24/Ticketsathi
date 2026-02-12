import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cinema_booking.settings')
django.setup()
from booking.models import Movie

# Known working trailers
TRAILERS = {
    "Sholay": "https://www.youtube.com/watch?v=uK7Y4f4hSpE",
    "Avengers: Endgame": "https://www.youtube.com/watch?v=TcMBFSGVi1c",
    "Bahubali": "https://www.youtube.com/watch?v=sOEg_YZQsTI",
    "KGF Chapter 2": "https://www.youtube.com/watch?v=JKa05nyUmuQ",
    "RRR": "https://www.youtube.com/watch?v=NgBoMJy386M",
    "Inception": "https://www.youtube.com/watch?v=YoHD9XEInc0",
    "Interstellar": "https://www.youtube.com/watch?v=zSWdZVtXT7E",
    "The Dark Knight": "https://www.youtube.com/watch?v=EXeTwQWrcwY",
    "Parasite": "https://www.youtube.com/watch?v=5xH0HfJHsaY",
    "Joker": "https://www.youtube.com/watch?v=zAGVQLHvwOY"
}

print("Updating trailers...")
for title, url in TRAILERS.items():
    try:
        movie = Movie.objects.get(title__icontains=title)
        movie.trailer_url = url
        movie.save()
        print(f"Updated {movie.title} -> {url}")
    except Movie.DoesNotExist:
        pass
    except Movie.MultipleObjectsReturned:
        # Update the first one
        movie = Movie.objects.filter(title__icontains=title).first()
        if movie:
            movie.trailer_url = url
            movie.save()
            print(f"Updated {movie.title} (first match) -> {url}")

print("Done.")
