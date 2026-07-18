"""
CineBook — Seed 20 Real Movies Management Command
===================================================
Seeds 8 major Indian cities, theaters, screens, 20 real movies (Malayalam, Hindi, English),
and shows for now-showing films.

Usage:
    python manage.py seed_movies
    python manage.py seed_movies --clear
"""

import logging
from datetime import date, timedelta, time
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.movies.models import Genre, Movie
from apps.theaters.models import City, Theater, Screen, Seat, SeatCategory
from apps.shows.models import Show, ShowSeat

logger = logging.getLogger("management")


class Command(BaseCommand):
    help = "Seed the database with 20 real movies and showtimes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear all existing data before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write(self.style.WARNING("Clearing existing data..."))
            ShowSeat.objects.all().delete()
            Show.objects.all().delete()
            Seat.objects.all().delete()
            SeatCategory.objects.all().delete()
            Screen.objects.all().delete()
            Theater.objects.all().delete()
            City.objects.all().delete()
            Movie.objects.all().delete()
            Genre.objects.all().delete()
            User.objects.filter(is_superuser=False).exclude(username="admin").delete()
            self.stdout.write(self.style.SUCCESS("Existing data cleared."))

        self._create_users()
        cities = self._create_cities()
        genres = self._create_genres()
        theaters = self._create_theaters(cities)
        movies = self._create_movies(genres)
        self._create_shows(movies, theaters)

        self.stdout.write(self.style.SUCCESS(
            f"\n[SUCCESS] Seed complete!\n"
            f"   Cities:   {City.objects.count()}\n"
            f"   Theaters: {Theater.objects.count()}\n"
            f"   Movies:   {Movie.objects.count()}\n"
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
    # Cities
    # -------------------------------------------------------------------------
    def _create_cities(self):
        city_data = [
            ("Mumbai", "Maharashtra"),
            ("Delhi", "Delhi NCR"),
            ("Bengaluru", "Karnataka"),
            ("Chennai", "Tamil Nadu"),
            ("Hyderabad", "Telangana"),
            ("Kolkata", "West Bengal"),
            ("Pune", "Maharashtra"),
            ("Kochi", "Kerala"),
        ]
        cities = {}
        for name, state in city_data:
            c, _ = City.objects.get_or_create(name=name, defaults={"state": state, "is_active": True})
            cities[name] = c
        self.stdout.write(f"  + {len(cities)} cities ready")
        return cities

    # -------------------------------------------------------------------------
    # Genres
    # -------------------------------------------------------------------------
    def _create_genres(self):
        genre_names = [
            "Action", "Thriller", "Fantasy", "Drama", "Period Fantasy",
            "Sports Drama", "Comedy", "Romantic Comedy", "War Drama",
            "Comedy Thriller", "Superhero Action", "Animation", "Sci-Fi", "Adventure"
        ]
        genres = {}
        for name in genre_names:
            g, _ = Genre.objects.get_or_create(name=name)
            genres[name] = g
        self.stdout.write(f"  + {len(genres)} genres ready")
        return genres

    # -------------------------------------------------------------------------
    # Theaters
    # -------------------------------------------------------------------------
    def _create_theaters(self, cities):
        theater_defs = [
            {
                "name": "PVR Cinemas — Phoenix Palladium",
                "city": cities["Mumbai"],
                "address": "462, Senapati Bapat Marg, Lower Parel, Mumbai 400013",
                "amenities": ["4K LASER DOLBY 7.1", "IMAX", "Recliner", "Parking", "Food Court"],
                "screens": [
                    {"name": "Audi 1 — IMAX", "capacity": 150, "categories": [("CLASSIC", 250), ("PREMIUM", 450), ("RECLINER", 750)]},
                    {"name": "Audi 2 — PXL", "capacity": 120, "categories": [("CLASSIC", 220), ("PREMIUM", 380)]},
                ]
            },
            {
                "name": "INOX — R City Mall",
                "city": cities["Mumbai"],
                "address": "LBS Marg, Ghatkopar West, Mumbai 400086",
                "amenities": ["4DX", "LUXE", "Wheelchair Access", "Food Court"],
                "screens": [
                    {"name": "Screen 1 — 4DX", "capacity": 100, "categories": [("PREMIUM", 500), ("RECLINER", 800)]},
                    {"name": "Screen 2", "capacity": 140, "categories": [("CLASSIC", 180), ("PREMIUM", 320)]},
                ]
            },
            {
                "name": "PVR Lulu Mall — Edappally",
                "city": cities["Kochi"],
                "address": "34/1000, NH 47, Edappally, Kochi 682024",
                "amenities": ["4K LASER DOLBY 7.1", "IMAX", "Recliner", "Food Court", "Wheelchair Access"],
                "screens": [
                    {"name": "Screen 1 — IMAX", "capacity": 160, "categories": [("CLASSIC", 200), ("PREMIUM", 380), ("RECLINER", 600)]},
                    {"name": "Screen 2 — LUXE", "capacity": 110, "categories": [("CLASSIC", 170), ("PREMIUM", 300)]},
                ]
            },
            {
                "name": "PVR Forum Mall — Koramangala",
                "city": cities["Bengaluru"],
                "address": "21, Hosur Rd, Koramangala, Bengaluru 560095",
                "amenities": ["IMAX", "4K LASER DOLBY 7.1", "Recliner", "Parking"],
                "screens": [
                    {"name": "Screen 1 — IMAX", "capacity": 150, "categories": [("CLASSIC", 250), ("PREMIUM", 450), ("RECLINER", 700)]},
                ]
            },
            {
                "name": "PVR Select Citywalk — Saket",
                "city": cities["Delhi"],
                "address": "A-3, District Centre, Saket, New Delhi 110017",
                "amenities": ["IMAX", "4K LASER DOLBY 7.1", "Recliner", "Food Court"],
                "screens": [
                    {"name": "Screen 1 — IMAX", "capacity": 150, "categories": [("CLASSIC", 240), ("PREMIUM", 430), ("RECLINER", 720)]},
                    {"name": "Screen 2", "capacity": 120, "categories": [("CLASSIC", 210), ("PREMIUM", 360)]},
                ]
            },
            {
                "name": "SPI Sathyam Cinemas — Royapettah",
                "city": cities["Chennai"],
                "address": "8, Thiru Vi Ka Rd, Royapettah, Chennai 600014",
                "amenities": ["4K LASER DOLBY 7.1", "Recliner", "Food Court", "Wheelchair Access"],
                "screens": [
                    {"name": "Screen 1 — LUXE", "capacity": 160, "categories": [("CLASSIC", 190), ("PREMIUM", 340), ("RECLINER", 620)]},
                ]
            },
            {
                "name": "AMB Cinemas — Gachibowli",
                "city": cities["Hyderabad"],
                "address": "Sattva Necklace Mall, Gachibowli, Hyderabad 500032",
                "amenities": ["IMAX", "4DX", "Recliner", "Food Court"],
                "screens": [
                    {"name": "Screen 1 — IMAX", "capacity": 150, "categories": [("CLASSIC", 220), ("PREMIUM", 400), ("RECLINER", 680)]},
                ]
            },
            {
                "name": "INOX — South City Mall",
                "city": cities["Kolkata"],
                "address": "375, Prince Anwar Shah Rd, Kolkata 700068",
                "amenities": ["4K LASER DOLBY 7.1", "Recliner", "Food Court"],
                "screens": [
                    {"name": "Screen 1", "capacity": 140, "categories": [("CLASSIC", 180), ("PREMIUM", 320)]},
                ]
            },
            {
                "name": "PVR Phoenix Marketcity — Viman Nagar",
                "city": cities["Pune"],
                "address": "Phoenix Marketcity, Viman Nagar, Pune 411014",
                "amenities": ["IMAX", "4K LASER DOLBY 7.1", "Recliner", "Parking"],
                "screens": [
                    {"name": "Screen 1 — IMAX", "capacity": 150, "categories": [("CLASSIC", 210), ("PREMIUM", 380), ("RECLINER", 660)]},
                ]
            },
        ]

        theaters = []
        for t_data in theater_defs:
            theater, created = Theater.objects.get_or_create(
                name=t_data["name"],
                defaults={
                    "city": t_data["city"],
                    "address": t_data["address"],
                    "amenities": t_data["amenities"],
                },
            )

            for s_data in t_data["screens"]:
                screen, _ = Screen.objects.get_or_create(
                    theater=theater,
                    name=s_data["name"],
                    defaults={"total_capacity": s_data["capacity"]},
                )

                seat_count = 0
                for cat_name, price in s_data["categories"]:
                    cat_choice = getattr(SeatCategory.CategoryChoices, cat_name, None)
                    if not cat_choice:
                        continue

                    category, _ = SeatCategory.objects.get_or_create(
                        screen=screen,
                        category=cat_choice,
                        defaults={"price": Decimal(str(price))},
                    )

                    existing_seats = Seat.objects.filter(screen=screen).count()
                    row_labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                    seats_per_row = 10
                    count_for_cat = 40 if cat_name == "CLASSIC" else (30 if cat_name == "PREMIUM" else 10)
                    for idx in range(count_for_cat):
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

            theaters.append(theater)

        self.stdout.write(f"  + {len(theaters)} theaters ready")
        return theaters

    # -------------------------------------------------------------------------
    # Movies (20 Real Movies)
    # -------------------------------------------------------------------------
    def _create_movies(self, genres):
        today = date.today()

        movie_data = [
            # --- Malayalam (7) ---
            {
                "title": "Bazooka",
                "language": "Malayalam",
                "genres": ["Action", "Thriller"],
                "duration_minutes": 145,
                "rating": Movie.RatingChoices.UA,
                "release_date": today - timedelta(days=5),
                "is_now_showing": True,
                "description": "A high-octane action game of wits starring Mammootty. A mysterious mastermind entangles a team in a deadly subterranean puzzle.",
                "cast_info": [{"name": "Mammootty", "role": "Vinod"}, {"name": "Gautham Vasudev Menon", "role": "Benjamin"}, {"name": "Shine Tom Chacko", "role": "Luke"}],
            },
            {
                "title": "Lokah Chapter 1: Chandra",
                "language": "Malayalam",
                "genres": ["Fantasy", "Action"],
                "duration_minutes": 155,
                "rating": Movie.RatingChoices.UA,
                "release_date": today - timedelta(days=2),
                "is_now_showing": True,
                "description": "An epic mythic action fantasy about Chandra, guardian of the ancient moon realm, defending his homeland against dark cosmic forces.",
                "cast_info": [{"name": "Tovino Thomas", "role": "Chandra"}, {"name": "Kalyani Priyadarshan", "role": "Maya"}, {"name": "Naslen", "role": "Kiran"}],
            },
            {
                "title": "Hridayapoorvam",
                "language": "Malayalam",
                "genres": ["Drama"],
                "duration_minutes": 138,
                "rating": Movie.RatingChoices.U,
                "release_date": today - timedelta(days=10),
                "is_now_showing": True,
                "description": "Mohanlal delivers an emotionally captivating performance as a retired schoolteacher who embarks on a journey to reunite old friends across Kerala.",
                "cast_info": [{"name": "Mohanlal", "role": "Sathyanathan"}, {"name": "Malavika Mohanan", "role": "Aswathy"}, {"name": "Siddique", "role": "Dr. Joseph"}],
            },
            {
                "title": "Identity",
                "language": "Malayalam",
                "genres": ["Thriller"],
                "duration_minutes": 130,
                "rating": Movie.RatingChoices.UA,
                "release_date": today - timedelta(days=7),
                "is_now_showing": True,
                "description": "A gripping psychological thriller where a forensic sketch artist uncovers a serial killer who assumes the identity of his victims.",
                "cast_info": [{"name": "Tovino Thomas", "role": "Abhinav"}, {"name": "Trisha Krishnan", "role": "Rhea"}, {"name": "Vinay Rai", "role": "Inspector Vikram"}],
            },
            {
                "title": "Kalamkaval",
                "language": "Malayalam",
                "genres": ["Drama"],
                "duration_minutes": 142,
                "rating": Movie.RatingChoices.U,
                "release_date": today + timedelta(days=14),
                "is_now_showing": False,
                "description": "A heartwarming saga set in rural Palakkad about three generations of traditional farmers protecting their land against urban development.",
                "cast_info": [{"name": "Suraj Venjaramoodu", "role": "Raman"}, {"name": "Nimisha Sajayan", "role": "Lakshmi"}, {"name": "Indrans", "role": "Kuttan"}],
            },
            {
                "title": "Kathanar: The Wild Sorcerer",
                "language": "Malayalam",
                "genres": ["Period Fantasy"],
                "duration_minutes": 160,
                "rating": Movie.RatingChoices.UA,
                "release_date": today + timedelta(days=21),
                "is_now_showing": False,
                "description": "Jayasurya stars as Kadamattathu Kathanar, the legendary 9th-century priest endowed with mystical powers, battling ancient dark sorcery.",
                "cast_info": [{"name": "Jayasurya", "role": "Kathanar"}, {"name": "Anushka Shetty", "role": "Kalliyankattu Neeli"}, {"name": "Vineeth", "role": "High Priest"}],
            },
            {
                "title": "Tiki Taka",
                "language": "Malayalam",
                "genres": ["Sports Drama"],
                "duration_minutes": 135,
                "rating": Movie.RatingChoices.U,
                "release_date": today + timedelta(days=30),
                "is_now_showing": False,
                "description": "Asif Ali leads an underdog sevens football club from Malappuram to the state championship in a thrilling sports spectacle.",
                "cast_info": [{"name": "Asif Ali", "role": "Shihab"}, {"name": "Lukman Avaran", "role": "Basheer"}, {"name": "Wamiqa Gabbi", "role": "Zoya"}],
            },

            # --- Hindi (7) ---
            {
                "title": "Dhamaal 4",
                "language": "Hindi",
                "genres": ["Comedy"],
                "duration_minutes": 140,
                "rating": Movie.RatingChoices.U,
                "release_date": today - timedelta(days=3),
                "is_now_showing": True,
                "description": "The wild comedy gang is back! Roy, Manav, Adi, and Boman embark on an insane jungle treasure hunt packed with non-stop laughter.",
                "cast_info": [{"name": "Ritesh Deshmukh", "role": "Roy"}, {"name": "Arshad Warsi", "role": "Adi"}, {"name": "Javed Jaffrey", "role": "Manav"}, {"name": "Ajay Devgn", "role": "Guddu"}],
            },
            {
                "title": "Dhurandhar",
                "language": "Hindi",
                "genres": ["Action", "Thriller"],
                "duration_minutes": 150,
                "rating": Movie.RatingChoices.UA,
                "release_date": today - timedelta(days=1),
                "is_now_showing": True,
                "description": "Ranveer Singh stars as an operative infiltrating an international cartel in a gritty, high-stakes espionage action thriller.",
                "cast_info": [{"name": "Ranveer Singh", "role": "Kabir"}, {"name": "Akshaye Khanna", "role": "RAW Chief"}, {"name": "Sanjay Dutt", "role": "Iqbal"}, {"name": "R. Madhavan", "role": "NSA Agent"}],
            },
            {
                "title": "Border 2",
                "language": "Hindi",
                "genres": ["War Drama"],
                "duration_minutes": 165,
                "rating": Movie.RatingChoices.UA,
                "release_date": today + timedelta(days=15),
                "is_now_showing": False,
                "description": "The epic sequel to the legendary 1997 war film. Sunny Deol returns to lead a brave battalion defending India's western frontier.",
                "cast_info": [{"name": "Sunny Deol", "role": "Major Kuldip"}, {"name": "Varun Dhawan", "role": "Captain Arjun"}, {"name": "Diljit Dosanjh", "role": "Subedar Gurdev"}],
            },
            {
                "title": "Cocktail 2",
                "language": "Hindi",
                "genres": ["Romantic Comedy"],
                "duration_minutes": 130,
                "rating": Movie.RatingChoices.UA,
                "release_date": today + timedelta(days=25),
                "is_now_showing": False,
                "description": "A glamorous modern rom-com following three spirited friends navigating love, heartbreaks, and career ambitions in London.",
                "cast_info": [{"name": "Shahid Kapoor", "role": "Dev"}, {"name": "Kriti Sanon", "role": "Tanya"}, {"name": "Rashmika Mandanna", "role": "Sia"}],
            },
            {
                "title": "Main Vaapas Aaunga",
                "language": "Hindi",
                "genres": ["Drama"],
                "duration_minutes": 125,
                "rating": Movie.RatingChoices.U,
                "release_date": today + timedelta(days=40),
                "is_now_showing": False,
                "description": "An inspiring emotional drama about an exiled soldier returning to his ancestral Himalayan village to restore his family honor.",
                "cast_info": [{"name": "Pankaj Tripathi", "role": "Bishamber"}, {"name": "Rajkummar Rao", "role": "Suraj"}, {"name": "Bhumi Pednekar", "role": "Radha"}],
            },
            {
                "title": "Baby Do Die Do",
                "language": "Hindi",
                "genres": ["Comedy Thriller"],
                "duration_minutes": 128,
                "rating": Movie.RatingChoices.UA,
                "release_date": today + timedelta(days=12),
                "is_now_showing": False,
                "description": "A quirky dark comedy thriller where two bumbling kidnappers accidentally abduct a dangerous underworld don's pampered pet bulldog.",
                "cast_info": [{"name": "Ayushmann Khurrana", "role": "Bunty"}, {"name": "Jaideep Ahlawat", "role": "Don Gabbar"}, {"name": "Sanya Malhotra", "role": "Pinky"}],
            },
            {
                "title": "Karuppu",
                "language": "Hindi",
                "genres": ["Action"],
                "duration_minutes": 145,
                "rating": Movie.RatingChoices.A,
                "release_date": today + timedelta(days=18),
                "is_now_showing": False,
                "description": "A fierce vigilante action entertainer dubbed in Hindi. A feared shadow warrior wages war against a corrupt political syndicate.",
                "cast_info": [{"name": "Suriya", "role": "Karuppu"}, {"name": "Bobby Deol", "role": "Dharma"}, {"name": "Pooja Hegde", "role": "Anitha"}],
            },

            # --- English (6) ---
            {
                "title": "Spider-Man: Brand New Day",
                "language": "English",
                "genres": ["Superhero Action"],
                "duration_minutes": 142,
                "rating": Movie.RatingChoices.UA,
                "release_date": today - timedelta(days=4),
                "is_now_showing": True,
                "description": "Peter Parker embarks on a fresh chapter balancing college life and crime-fighting in New York City as a sinister new threat emerges.",
                "cast_info": [{"name": "Tom Holland", "role": "Peter Parker / Spider-Man"}, {"name": "Zendaya", "role": "MJ"}, {"name": "Sadie Sink", "role": "Felicia Hardy"}],
            },
            {
                "title": "Moana (2026)",
                "language": "English",
                "genres": ["Animation", "Adventure"],
                "duration_minutes": 110,
                "rating": Movie.RatingChoices.U,
                "release_date": today + timedelta(days=8),
                "is_now_showing": False,
                "description": "Moana and Maui set sail on a new epic voyage across Oceania to reunite broken island tribes and restore ancient ocean spirits.",
                "cast_info": [{"name": "Auli'i Cravalho", "role": "Moana"}, {"name": "Dwayne Johnson", "role": "Maui"}],
            },
            {
                "title": "Toy Story 5",
                "language": "English",
                "genres": ["Animation"],
                "duration_minutes": 105,
                "rating": Movie.RatingChoices.U,
                "release_date": today + timedelta(days=35),
                "is_now_showing": False,
                "description": "Woody, Buzz, and the gang confront their biggest competitor yet — electronic tech gadgets that threaten to replace classic toys.",
                "cast_info": [{"name": "Tom Hanks", "role": "Woody"}, {"name": "Tim Allen", "role": "Buzz Lightyear"}],
            },
            {
                "title": "Avatar: Fire and Ash",
                "language": "English",
                "genres": ["Sci-Fi", "Adventure"],
                "duration_minutes": 170,
                "rating": Movie.RatingChoices.UA,
                "release_date": today + timedelta(days=50),
                "is_now_showing": False,
                "description": "James Cameron's stunning third chapter introduces the Ash People, a volcanic Na'vi tribe, expanding the world of Pandora like never before.",
                "cast_info": [{"name": "Sam Worthington", "role": "Jake Sully"}, {"name": "Zoe Saldaña", "role": "Neytiri"}, {"name": "Oona Chaplin", "role": "Varang"}],
            },
            {
                "title": "The Odyssey",
                "language": "English",
                "genres": ["Adventure"],
                "duration_minutes": 155,
                "rating": Movie.RatingChoices.UA,
                "release_date": today + timedelta(days=22),
                "is_now_showing": False,
                "description": "Homer's timeless myth brought to life. King Odysseus faces mythical beasts, vengeful gods, and treacherous seas on his ten-year journey home.",
                "cast_info": [{"name": "Ralph Fiennes", "role": "Odysseus"}, {"name": "Juliette Binoche", "role": "Penelope"}],
            },
            {
                "title": "Supergirl",
                "language": "English",
                "genres": ["Superhero Action"],
                "duration_minutes": 138,
                "rating": Movie.RatingChoices.UA,
                "release_date": today + timedelta(days=28),
                "is_now_showing": False,
                "description": "Kara Zor-El travels across the cosmos on a revenge mission that forces her to discover what truly makes her a hero of tomorrow.",
                "cast_info": [{"name": "Milly Alcock", "role": "Kara Zor-El / Supergirl"}, {"name": "Matthias Schoenaerts", "role": "Krem"}],
            },
        ]

        movies = []
        for data in movie_data:
            genre_names = data.pop("genres")
            cast = data.pop("cast_info", [])
            is_showing = data.pop("is_now_showing", False)

            movie, created = Movie.objects.get_or_create(
                title=data["title"],
                defaults={
                    **data,
                    "cast_info": cast,
                    "is_active": True,
                },
            )

            for g_name in genre_names:
                if g_name in genres:
                    movie.genres.add(genres[g_name])

            movie._is_now_showing_flag = is_showing
            movies.append(movie)

        self.stdout.write(f"  + {len(movies)} movies ready")
        return movies

    # -------------------------------------------------------------------------
    # Shows
    # -------------------------------------------------------------------------
    def _create_shows(self, movies, theaters):
        screens = list(Screen.objects.select_related("theater", "theater__city").all())
        if not screens:
            return

        show_times = [time(10, 30), time(13, 45), time(17, 0), time(20, 15), time(22, 30)]
        formats = ["IMAX", "4K LASER DOLBY 7.1", "4DX", "PXL", "LUXE", "2D"]

        shows_created = 0

        for day_offset in range(4):
            show_date = date.today() + timedelta(days=day_offset)

            for s_idx, screen in enumerate(screens):
                for m_step in range(3):
                    movie = movies[(s_idx * 3 + m_step + day_offset * 5) % len(movies)]
                    t_idx = (s_idx + m_step + day_offset) % len(show_times)
                    show_time = show_times[t_idx]
                    start_dt = timezone.make_aware(
                        timezone.datetime.combine(show_date, show_time)
                    )

                    fmt = formats[(s_idx + t_idx) % len(formats)]
                    cancellation = ((s_idx + t_idx) % 2 == 0)

                        show, created = Show.objects.get_or_create(
                            movie=movie,
                            screen=screen,
                            start_time=start_dt,
                            defaults={
                                "end_time": start_dt + timedelta(minutes=movie.duration_minutes),
                                "date": show_date,
                                "language": movie.language,
                                "format": fmt,
                                "is_cancellable": cancellation,
                                "is_active": True,
                            },
                        )

                        if created:
                            shows_created += 1
                            seats = Seat.objects.filter(screen=screen)
                            show_seats = [
                                ShowSeat(show=show, seat=seat, status=ShowSeat.StatusChoices.AVAILABLE)
                                for seat in seats
                            ]
                            ShowSeat.objects.bulk_create(show_seats, ignore_conflicts=True)

        self.stdout.write(f"  + {shows_created} shows created across now-showing movies")
