"""
CineBook — Seed Data Management Command
=========================================
Creates a complete realistic dataset for development testing:
- 2 theaters, 4 screens
- 6 movies (mix of genres, languages, ratings)
- Seat categories and seats for each screen
- Shows for the next 7 days
- 1 superuser admin (admin/admin123)
- 1 regular test user (testuser/testpass123)

Usage:
    python manage.py seed_data
    python manage.py seed_data --clear   # Wipe and re-seed
"""

import logging
from datetime import date, timedelta, time
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.movies.models import Genre, Movie
from apps.theaters.models import Theater, Screen, Seat, SeatCategory
from apps.shows.models import Show, ShowSeat

logger = logging.getLogger("management")


class Command(BaseCommand):
    help = "Seed the database with realistic test data for development."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear all existing data before seeding (dangerous in production).",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write(self.style.WARNING("Clearing all data..."))
            ShowSeat.objects.all().delete()
            Show.objects.all().delete()
            Seat.objects.all().delete()
            SeatCategory.objects.all().delete()
            Screen.objects.all().delete()
            Theater.objects.all().delete()
            Movie.objects.all().delete()
            Genre.objects.all().delete()
            User.objects.filter(is_superuser=False).exclude(username="admin").delete()
            self.stdout.write(self.style.SUCCESS("Data cleared."))

        self._create_users()
        genres = self._create_genres()
        movies = self._create_movies(genres)
        theaters = self._create_theaters()
        self._create_shows(movies, theaters)

        self.stdout.write(self.style.SUCCESS(
            f"\n[SUCCESS] Seed complete!\n"
            f"   Movies:   {Movie.objects.count()}\n"
            f"   Theaters: {Theater.objects.count()}\n"
            f"   Screens:  {Screen.objects.count()}\n"
            f"   Shows:    {Show.objects.count()}\n"
            f"   Seats:    {ShowSeat.objects.count()}\n"
            f"\n   Admin login: admin / admin123\n"
            f"   Test user:   testuser / testpass123\n"
        ))

    # -------------------------------------------------------------------------
    # Users
    # -------------------------------------------------------------------------
    def _create_users(self):
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@cinebook.dev", "admin123")
            self.stdout.write("  + Superuser 'admin' created")

        if not User.objects.filter(username="testuser").exists():
            User.objects.create_user("testuser", "test@cinebook.dev", "testpass123",
                                     first_name="Test", last_name="User")
            self.stdout.write("  + Test user 'testuser' created")

    # -------------------------------------------------------------------------
    # Genres
    # -------------------------------------------------------------------------
    def _create_genres(self):
        genre_names = ["Action", "Drama", "Comedy", "Thriller", "Romance",
                       "Sci-Fi", "Horror", "Animation", "Documentary", "Adventure"]
        genres = {}
        for name in genre_names:
            g, _ = Genre.objects.get_or_create(name=name)
            genres[name] = g
        self.stdout.write(f"  + {len(genres)} genres ready")
        return genres

    # -------------------------------------------------------------------------
    # Movies
    # -------------------------------------------------------------------------
    def _create_movies(self, genres):
        movie_data = [
            {
                "title": "Galactic Frontier",
                "description": "A crew of intrepid astronauts ventures beyond the known universe to discover what lies at the edge of existence — and brings back something that should have been left behind.",
                "duration_minutes": 148,
                "language": "English",
                "release_date": date.today() - timedelta(days=7),
                "rating": Movie.RatingChoices.UA,
                "genres": ["Sci-Fi", "Adventure", "Thriller"],
                "trailer_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "cast_info": [
                    {"name": "Alex Rivera", "role": "Commander"},
                    {"name": "Priya Singh", "role": "Chief Scientist"},
                    {"name": "Marcus Chen", "role": "Engineer"},
                ],
            },
            {
                "title": "Dil Ke Raste",
                "description": "A poignant love story set against the backdrop of modern Mumbai — where two strangers from opposite worlds find themselves irrevocably intertwined.",
                "duration_minutes": 155,
                "language": "Hindi",
                "release_date": date.today() - timedelta(days=3),
                "rating": Movie.RatingChoices.U,
                "genres": ["Romance", "Drama"],
                "cast_info": [
                    {"name": "Rahul Sharma", "role": "Lead"},
                    {"name": "Ananya Kapoor", "role": "Lead"},
                ],
            },
            {
                "title": "The Last Detective",
                "description": "A world-weary detective takes on one final case that forces him to confront the city's most dangerous criminal organisation — and his own dark past.",
                "duration_minutes": 132,
                "language": "English",
                "release_date": date.today() - timedelta(days=14),
                "rating": Movie.RatingChoices.A,
                "genres": ["Thriller", "Action", "Drama"],
                "cast_info": [
                    {"name": "James Hartley", "role": "Detective Cole"},
                    {"name": "Sofia Martinez", "role": "DA Wheeler"},
                ],
            },
            {
                "title": "Sundari Unnaval",
                "description": "A spirited young woman in Chennai navigates family expectations, friendship, and unexpected love in this heartwarming comedy.",
                "duration_minutes": 140,
                "language": "Tamil",
                "release_date": date.today() - timedelta(days=1),
                "rating": Movie.RatingChoices.U,
                "genres": ["Comedy", "Romance"],
                "cast_info": [
                    {"name": "Kavitha Rajan", "role": "Sundari"},
                    {"name": "Vijay Kumar", "role": "Arjun"},
                ],
            },
            {
                "title": "Iron Shadows",
                "description": "A superhero origin story unlike any other — what happens when the most powerful being on Earth decides the system itself must burn.",
                "duration_minutes": 162,
                "language": "English",
                "release_date": date.today(),
                "rating": Movie.RatingChoices.UA,
                "genres": ["Action", "Sci-Fi", "Adventure"],
                "cast_info": [
                    {"name": "Tyler Brooks", "role": "Iron Shadow"},
                    {"name": "Mei Lin", "role": "Director Chen"},
                ],
            },
            {
                "title": "Khwaab",
                "description": "An aspiring musician from a small town risks everything to make his dream a reality in the cutthroat world of Bollywood.",
                "duration_minutes": 145,
                "language": "Hindi",
                "release_date": date.today() - timedelta(days=5),
                "rating": Movie.RatingChoices.U,
                "genres": ["Drama", "Romance"],
                "cast_info": [
                    {"name": "Rohan Verma", "role": "Arjun"},
                    {"name": "Nisha Patel", "role": "Meera"},
                ],
            },
        ]

        movies = []
        for data in movie_data:
            genre_names = data.pop("genres")
            cast = data.pop("cast_info", [])
            trailer = data.pop("trailer_url", None)

            movie, created = Movie.objects.get_or_create(
                title=data["title"],
                defaults={
                    **data,
                    "cast_info": cast,
                    "trailer_url": trailer or "",
                    "is_active": True,
                },
            )

            # Set genres
            for g_name in genre_names:
                if g_name in genres:
                    movie.genres.add(genres[g_name])

            if created:
                self.stdout.write(f"  + Movie: {movie.title}")
            movies.append(movie)

        return movies

    # -------------------------------------------------------------------------
    # Theaters
    # -------------------------------------------------------------------------
    def _create_theaters(self):
        theater_data = [
            {
                "name": "PVR Cinemas — Phoenix",
                "city": "Mumbai",
                "address": "Phoenix Mall, Lower Parel, Mumbai 400013",
                "screens": [
                    {"name": "Audi 1 — IMAX", "capacity": 200, "categories": [
                        ("CLASSIC", Decimal("250.00"), 120),
                        ("PREMIUM", Decimal("450.00"), 60),
                        ("RECLINER", Decimal("750.00"), 20),
                    ]},
                    {"name": "Audi 2 — Gold", "capacity": 120, "categories": [
                        ("CLASSIC", Decimal("200.00"), 80),
                        ("PREMIUM", Decimal("380.00"), 40),
                    ]},
                ]
            },
            {
                "name": "INOX — Megaplex",
                "city": "Mumbai",
                "address": "R City Mall, Ghatkopar, Mumbai 400086",
                "screens": [
                    {"name": "Screen 1", "capacity": 150, "categories": [
                        ("CLASSIC", Decimal("180.00"), 100),
                        ("PREMIUM", Decimal("320.00"), 50),
                    ]},
                    {"name": "Screen 2 — 4DX", "capacity": 80, "categories": [
                        ("PREMIUM", Decimal("500.00"), 50),
                        ("RECLINER", Decimal("800.00"), 30),
                    ]},
                ]
            },
        ]

        theaters = []
        for t_data in theater_data:
            theater, created = Theater.objects.get_or_create(
                name=t_data["name"],
                defaults={
                    "city": t_data["city"],
                    "address": t_data["address"],
                },
            )

            for s_data in t_data["screens"]:
                screen, _ = Screen.objects.get_or_create(
                    theater=theater,
                    name=s_data["name"],
                    defaults={"total_capacity": s_data["capacity"]},
                )

                # Create seat categories and seats
                seat_count = 0
                for cat_name, price, count in s_data["categories"]:
                    cat_choice = getattr(SeatCategory.CategoryChoices, cat_name, None)
                    if not cat_choice:
                        continue

                    category, _ = SeatCategory.objects.get_or_create(
                        screen=screen,
                        category=cat_choice,
                        defaults={"price": price},
                    )

                    # Each category gets its own unique rows to avoid (screen, row, seat_num) collision
                    existing_seats = Seat.objects.filter(screen=screen).count()
                    row_labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                    seats_per_row = 10
                    for idx in range(count):
                        global_idx = existing_seats + idx
                        row = row_labels[(global_idx // seats_per_row) % len(row_labels)]
                        seat_num = (global_idx % seats_per_row) + 1
                        Seat.objects.get_or_create(
                            screen=screen,
                            row_label=row,
                            seat_number=seat_num,
                            defaults={"category": category},
                        )
                        seat_count += 1

            if created:
                self.stdout.write(f"  + Theater: {theater.name} ({theater.city})")
            theaters.append(theater)

        return theaters

    # -------------------------------------------------------------------------
    # Shows
    # -------------------------------------------------------------------------
    def _create_shows(self, movies, theaters):
        screens = list(Screen.objects.select_related("theater").all())
        show_times = [time(10, 30), time(13, 0), time(16, 0), time(19, 0), time(22, 0)]

        shows_created = 0
        for day_offset in range(7):
            show_date = date.today() + timedelta(days=day_offset)

            for i, movie in enumerate(movies):
                # Assign each movie to a screen rotation
                screen = screens[i % len(screens)]

                # Pick 2 showtimes per movie per day
                for t_idx in [i % len(show_times), (i + 2) % len(show_times)]:
                    show_time = show_times[t_idx]
                    start_dt = timezone.make_aware(
                        timezone.datetime.combine(show_date, show_time)
                    )
                    end_dt = start_dt + timedelta(minutes=movie.duration_minutes + 15)

                    show, created = Show.objects.get_or_create(
                        movie=movie,
                        screen=screen,
                        start_time=start_dt,
                        defaults={
                            "end_time": end_dt,
                            "date": show_date,
                            "language": movie.language,
                            "is_active": True,
                        },
                    )

                    if created:
                        shows_created += 1
                        # Create ShowSeat records for each seat in the screen
                        seats = Seat.objects.filter(screen=screen)
                        show_seats = [
                            ShowSeat(show=show, seat=seat, status=ShowSeat.StatusChoices.AVAILABLE)
                            for seat in seats
                        ]
                        ShowSeat.objects.bulk_create(show_seats, ignore_conflicts=True)

        self.stdout.write(f"  + Created {shows_created} new shows")
