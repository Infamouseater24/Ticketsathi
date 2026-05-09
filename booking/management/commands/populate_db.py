from django.core.management.base import BaseCommand
from booking.models import Cinema, Screen, Seat, Movie, Showtime
from django.utils import timezone
from datetime import timedelta, datetime
import random

class Command(BaseCommand):
    help = 'Populate database with initial data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Populating database...')

        # 1. Create Cinemas
        cinemas = [
            {'name': 'ASA Multiplex', 'location': 'Pokhara', 'address': 'Pokhara-13, Kaski', 'phone': '1234567'},
            {'name': 'ASA Multiplex', 'location': 'Kathmandu', 'address': 'Kathmandu', 'phone': '23456787'},
        ]
        
        created_cinemas = []
        for c_data in cinemas:
            cinema, created = Cinema.objects.get_or_create(
                name=c_data['name'], 
                location=c_data['location'],
                defaults=c_data
            )
            created_cinemas.append(cinema)
            if created:
                self.stdout.write(f"Created Cinema: {cinema}")

        # 2. Create Screens and Seats
        for cinema in created_cinemas:
            for i in range(1, 3):
                screen_name = f"Screen {i}"
                screen, created = Screen.objects.get_or_create(
                    cinema=cinema,
                    name=screen_name,
                    defaults={'total_seats': 50}
                )
                
                if created:
                    self.stdout.write(f"Created Screen: {screen}")
                    # Create Seats (5 rows x 10 cols)
                    rows = ['A', 'B', 'C', 'D', 'E']
                    seats_to_create = []
                    for row in rows:
                        for num in range(1, 11):
                            seat_type = 'Premium' if row in ['D', 'E'] else 'Regular'
                            seats_to_create.append(Seat(
                                screen=screen,
                                row=row,
                                number=num,
                                seat_type=seat_type
                            ))
                    Seat.objects.bulk_create(seats_to_create)
                    self.stdout.write(f"  - Added {len(seats_to_create)} seats to {screen}")

        # 3. Create Movies
        movies_data = [
            {
                'title': 'Sholay',
                'description': 'Jai and Veeru, two ex-convicts, are hired by Thakur Baldev Singh, a retired policeman, to help him nab Gabbar Singh.',
                'duration': 204,
                'genre': 'Action',
                'language': 'Hindi',
                'rating': 'PG',
                'release_date': '2025-12-15',
                'trailer_url': 'https://www.youtube.com/watch?v=zzTUvWfvlBg',
                'is_now_showing': True
            },
            {
                'title': 'Baahubali 2: The Conclusion',
                'description': 'When Shiva, the son of Bahubali, learns about his heritage, he begins to look for answers. His story is juxtaposed with past events that unfolded in the Mahishmati Kingdom.',
                'duration': 167,
                'genre': 'Action',
                'language': 'Tollywood',
                'rating': 'U',
                'release_date': '2025-12-10',
                'trailer_url': 'https://www.youtube.com/watch?v=qD-6d8Wo3do',
                'is_now_showing': True
            },
            {
                'title': 'Avengers: Endgame',
                'description': 'After the devastating events of Infinity War, the universe is in ruins. With the help of remaining allies, the Avengers assemble once more in order to reverse Thanos\' actions.',
                'duration': 181,
                'genre': 'Action',
                'language': 'English',
                'rating': 'PG',
                'release_date': '2025-12-01',
                'trailer_url': 'https://www.youtube.com/watch?v=TcMBFSGVi1c',
                'is_now_showing': True
            }
        ]

        created_movies = []
        for m_data in movies_data:
            movie, created = Movie.objects.get_or_create(
                title=m_data['title'],
                defaults=m_data
            )
            created_movies.append(movie)
            if created:
                self.stdout.write(f"Created Movie: {movie}")

        # 4. Create Showtimes
        # Schedule for next 7 days
        today = timezone.now().date()
        screens = Screen.objects.all()
        
        for day in range(7):
            current_date = today + timedelta(days=day)
            for screen in screens:
                # 3 shows per day per screen
                start_times = ['10:00', '14:00', '18:00']
                for time_str in start_times:
                    # Pick random movie
                    movie = random.choice(created_movies)
                    
                    # Parse time
                    hour, minute = map(int, time_str.split(':'))
                    start_dt = datetime.combine(current_date, datetime.min.time().replace(hour=hour, minute=minute))
                    start_dt = timezone.make_aware(start_dt)
                    end_dt = start_dt + timedelta(minutes=movie.duration)
                    
                    price = 350.00 if hour >= 18 else 250.00
                    
                    Showtime.objects.get_or_create(
                        movie=movie,
                        screen=screen,
                        start_time=start_dt,
                        defaults={
                            'end_time': end_dt,
                            'price': price
                        }
                    )
        
        self.stdout.write(self.style.SUCCESS('Database populated successfully!'))
