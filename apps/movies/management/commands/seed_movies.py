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

from apps.movies.models import Genre, Movie, CastMember
from apps.theaters.models import City, Theater, Screen, Seat, SeatCategory
from apps.shows.models import Show, ShowSeat

logger = logging.getLogger("management")


# -----------------------------------------------------------------------------
# Baked poster / trailer / cast data (exported from the local dev DB).
# -----------------------------------------------------------------------------
# This data was set by hand in the local SQLite DB across earlier sessions and
# was never captured into any command that runs on Render. It is baked in here
# so that _apply_media_and_cast() can upsert it on EVERY deploy — including when
# the structural seed is skipped via --skip-if-seeded on an already-seeded live
# DB (which is exactly the situation on Render). Keyed by Movie.title.
#
# Idempotent: poster_url / trailer_youtube_url are written only when changed;
# cast uses update_or_create keyed on (movie, name). Safe to re-run every deploy.
# backdrop_url is intentionally NOT set here — sync_backdrops owns that field.
MEDIA_AND_CAST = {
    # --- Malayalam ---
    "Bazooka": {
        "poster_url": "/static/img/posters/Bazooka.jpg",
        "trailer_youtube_url": "https://youtu.be/LkKChCQnjB4?si=-5IVHCCR2_zAsDDw",
        "cast": [
            {"name": "Mammootty", "character_name": "Vinod", "photo_url": "/static/img/cast/Mammootty.jpg", "tmdb_person_id": 86127, "order": 0},
            {"name": "Gautham Vasudev Menon", "character_name": "Benjamin", "photo_url": "/static/img/cast/Gautham_Vasudev_Menon.jpg", "tmdb_person_id": 111409, "order": 1},
            {"name": "Shine Tom Chacko", "character_name": "Luke", "photo_url": "/static/img/cast/Shine_Tom_Chacko.jpg", "tmdb_person_id": 1478791, "order": 2},
        ],
    },
    "Lokah Chapter 1: Chandra": {
        "poster_url": "/static/img/posters/lokha.jpg",
        "trailer_youtube_url": "https://youtu.be/64XHtNWTB5o?si=YdTNdJqs4FEeAwnO",
        "cast": [
            {"name": "Tovino Thomas", "character_name": "Chandra", "photo_url": "/static/img/cast/Tovino_Thomas.jpg", "tmdb_person_id": 1086277, "order": 0},
            {"name": "Kalyani Priyadarshan", "character_name": "Maya", "photo_url": "/static/img/cast/Kalyani_Priyadarshan.jpg", "tmdb_person_id": 1982260, "order": 1},
            {"name": "Naslen", "character_name": "Kiran", "photo_url": "/static/img/cast/Naslen.jpg", "tmdb_person_id": 2987110, "order": 2},
        ],
    },
    "Hridayapoorvam": {
        "poster_url": "/static/img/posters/Hridayapoorvam.jpg",
        "trailer_youtube_url": "https://youtu.be/B4-Xhaajyok?si=1EsMC8Mgk7_UJBuv",
        "cast": [
            {"name": "Mohanlal", "character_name": "Sathyanathan", "photo_url": "/static/img/cast/Mohanlal.jpg", "tmdb_person_id": 129671, "order": 0},
            {"name": "Malavika Mohanan", "character_name": "Aswathy", "photo_url": "/static/img/cast/Malavika_Mohanan.jpg", "tmdb_person_id": 139121, "order": 1},
            {"name": "Siddique", "character_name": "Dr. Joseph", "photo_url": "/static/img/cast/Siddique.jpg", "tmdb_person_id": 111221, "order": 2},
        ],
    },
    "Identity": {
        "poster_url": "/static/img/posters/identity.jpg",
        "trailer_youtube_url": "https://youtu.be/6LSqReemlTk?si=goXqmcdNVrswr8uJ",
        "cast": [
            {"name": "Tovino Thomas", "character_name": "Abhinav", "photo_url": "/static/img/cast/Tovino_Thomas.jpg", "tmdb_person_id": 1086277, "order": 0},
            {"name": "Trisha Krishnan", "character_name": "Rhea", "photo_url": "/static/img/cast/Trisha_Krishnan.jpg", "tmdb_person_id": 86455, "order": 1},
            {"name": "Vinay Rai", "character_name": "Inspector Vikram", "photo_url": "/static/img/cast/Vinay_Rai.jpg", "tmdb_person_id": 112344, "order": 2},
        ],
    },
    "Kalamkaval": {
        "poster_url": "/static/img/posters/KalamKaval.jpg",
        "trailer_youtube_url": "https://youtu.be/LvUnF8oApaM?si=v3JmQyp5IRf32zT1",
        "cast": [
            {"name": "Suraj Venjaramoodu", "character_name": "Raman", "photo_url": "/static/img/cast/Suraj_Venjaramoodu.jpg", "tmdb_person_id": 112111, "order": 0},
            {"name": "Nimisha Sajayan", "character_name": "Lakshmi", "photo_url": "/static/img/cast/Nimisha_Sajayan.jpg", "tmdb_person_id": 189111, "order": 1},
        ],
    },
    "Kathanar: The Wild Sorcerer": {
        "poster_url": "/static/img/posters/Kathanar.jpg",
        "trailer_youtube_url": "https://youtu.be/VRPF2tXQ06c?si=iWdE410oOzZ3tYx2",
        "cast": [
            {"name": "Jayasurya", "character_name": "Kathanar", "photo_url": "/static/img/cast/Jayasurya.jpg", "tmdb_person_id": 114411, "order": 0},
            {"name": "Anushka Shetty", "character_name": "Kalliyankattu Neeli", "photo_url": "/static/img/cast/Anushka_Shetty.jpg", "tmdb_person_id": 112999, "order": 1},
        ],
    },
    "Tiki Taka": {
        "poster_url": "/static/img/posters/Tiki_Taka.jpg",
        "trailer_youtube_url": "https://youtu.be/6Scfiq7H5ng?si=RUBE2VzM7kUOY2nT",
        "cast": [
            {"name": "Asif Ali", "character_name": "Shihab", "photo_url": "/static/img/cast/Asif_Ali.jpg", "tmdb_person_id": 118811, "order": 0},
            {"name": "Lukman Avaran", "character_name": "Basheer", "photo_url": "/static/img/cast/Lukman_Avaran.jpg", "tmdb_person_id": 218811, "order": 1},
        ],
    },

    # --- Hindi ---
    "Dhamaal 4": {
        "poster_url": "/static/img/posters/Dhamaal_4.jpg",
        "trailer_youtube_url": "https://youtu.be/IG-eByZdz6Y?si=wVY-kF7XOmhWIjGa",
        "cast": [
            {"name": "Ritesh Deshmukh", "character_name": "Roy", "photo_url": "/static/img/cast/Ritesh_Deshmukh.jpg", "tmdb_person_id": 85210, "order": 0},
            {"name": "Arshad Warsi", "character_name": "Adi", "photo_url": "/static/img/cast/Arshad_Warsi.jpg", "tmdb_person_id": 85211, "order": 1},
            {"name": "Ajay Devgn", "character_name": "Guddu", "photo_url": "/static/img/cast/Ajay_Devgn.jpg", "tmdb_person_id": 85212, "order": 2},
        ],
    },
    "Dhurandhar": {
        "poster_url": "/static/img/posters/Dhurandar.jpg",
        "trailer_youtube_url": "https://youtu.be/NHk7scrb_9I?si=U0xc7QPhNuHdmQ1h",
        "cast": [
            {"name": "Ranveer Singh", "character_name": "Kabir", "photo_url": "/static/img/cast/Ranveer_Singh.jpg", "tmdb_person_id": 111888, "order": 0},
            {"name": "Akshaye Khanna", "character_name": "RAW Chief", "photo_url": "/static/img/cast/Akshaye_Khanna.jpg", "tmdb_person_id": 85220, "order": 1},
        ],
    },
    "Border 2": {
        "poster_url": "/static/img/posters/Border_2.jpg",
        "trailer_youtube_url": "https://youtu.be/ysi8h4UfaZE?si=0qYoD6dBWoR4qAlS",
        "cast": [
            {"name": "Sunny Deol", "character_name": "Major Kuldip", "photo_url": "/static/img/cast/Sunny_Deol.jpg", "tmdb_person_id": 85230, "order": 0},
            {"name": "Varun Dhawan", "character_name": "Captain Arjun", "photo_url": "/static/img/cast/Varun_Dhawan.jpg", "tmdb_person_id": 111999, "order": 1},
        ],
    },
    "Cocktail 2": {
        "poster_url": "/static/img/posters/cock_tail_2.jpg",
        "trailer_youtube_url": "https://youtu.be/XXxUqLHq1xg?si=wall7vSQXn2vXPIP",
        "cast": [
            {"name": "Shahid Kapoor", "character_name": "Dev", "photo_url": "/static/img/cast/Shahid_Kapoor.jpg", "tmdb_person_id": 85240, "order": 0},
            {"name": "Kriti Sanon", "character_name": "Tanya", "photo_url": "/static/img/cast/Kriti_Sanon.jpg", "tmdb_person_id": 133221, "order": 1},
        ],
    },
    "Main Vaapas Aaunga": {
        "poster_url": "/static/img/posters/Main_Vaapas_Aaunga.jpg",
        "trailer_youtube_url": "https://youtu.be/PRUTWluKRW8?si=IZQh0j13gITGdoIw",
        "cast": [
            {"name": "Pankaj Tripathi", "character_name": "Bishamber", "photo_url": "/static/img/cast/Pankaj_Tripathi.jpg", "tmdb_person_id": 189999, "order": 0},
            {"name": "Rajkummar Rao", "character_name": "Suraj", "photo_url": "/static/img/cast/Rajkummar_Rao.jpg", "tmdb_person_id": 118822, "order": 1},
        ],
    },
    "Baby Do Die Do": {
        "poster_url": "/static/img/posters/Baby_Do_Die_Do.jpg",
        "trailer_youtube_url": "https://youtu.be/2rQCZKoaEhc?si=ocI8_HZVtFHzINtg",
        "cast": [
            {"name": "Ayushmann Khurrana", "character_name": "Bunty", "photo_url": "/static/img/cast/Ayushmann_Khurrana.jpg", "tmdb_person_id": 119911, "order": 0},
            {"name": "Jaideep Ahlawat", "character_name": "Don Gabbar", "photo_url": "/static/img/cast/Jaideep_Ahlawat.jpg", "tmdb_person_id": 189911, "order": 1},
        ],
    },
    "Karuppu": {
        "poster_url": "/static/img/posters/Karuppu.jpg",
        "trailer_youtube_url": "https://youtu.be/JpVl_-1YgIo?si=Xfwlzh_HbBlIbnef",
        "cast": [
            {"name": "Suriya", "character_name": "Karuppu", "photo_url": "/static/img/cast/Suriya.jpg", "tmdb_person_id": 85250, "order": 0},
            {"name": "Bobby Deol", "character_name": "Dharma", "photo_url": "/static/img/cast/Bobby_Deol.jpg", "tmdb_person_id": 85251, "order": 1},
        ],
    },

    # --- English ---
    "Spider-Man: Brand New Day": {
        "poster_url": "/static/img/posters/spider_man_brand_new_day.jpg",
        "trailer_youtube_url": "https://youtu.be/8TZMtslA3UY?si=WaIrIRv04zpZhg3b",
        "cast": [
            {"name": "Tom Holland", "character_name": "Peter Parker / Spider-Man", "photo_url": "/static/img/cast/Tom_Holland.jpg", "tmdb_person_id": 1136406, "order": 0},
            {"name": "Zendaya", "character_name": "MJ", "photo_url": "/static/img/cast/Zendaya.jpg", "tmdb_person_id": 505710, "order": 1},
            {"name": "Benedict Cumberbatch", "character_name": "Doctor Strange", "photo_url": "/static/img/cast/Benedict_Cumberbatch.jpg", "tmdb_person_id": 71580, "order": 2},
            {"name": "Jacob Batalon", "character_name": "Ned Leeds", "photo_url": "/static/img/cast/Jacob_Batalon.jpg", "tmdb_person_id": 1649152, "order": 3},
        ],
    },
    "Moana (2026)": {
        "poster_url": "/static/img/posters/Moana_(2026).jpg",
        "trailer_youtube_url": "https://youtu.be/hDZ7y8RP5HE?si=_dh2EHXiKECFmPWY",
        "cast": [
            {"name": "Auli'i Cravalho", "character_name": "Moana", "photo_url": "/static/img/cast/Auli_i_Cravalho.jpg", "tmdb_person_id": 1564846, "order": 0},
            {"name": "Dwayne Johnson", "character_name": "Maui", "photo_url": "/static/img/cast/Dwayne_Johnson.jpg", "tmdb_person_id": 1892, "order": 1},
        ],
    },
    "Toy Story 5": {
        "poster_url": "/static/img/posters/Toy_Story_5.jpg",
        "trailer_youtube_url": "https://youtu.be/c51ND9Hdbw0?si=w_ckYGMuYhHD61On",
        "cast": [
            {"name": "Tom Hanks", "character_name": "Woody", "photo_url": "/static/img/cast/Tom_Hanks.jpg", "tmdb_person_id": 31, "order": 0},
            {"name": "Tim Allen", "character_name": "Buzz Lightyear", "photo_url": "/static/img/cast/Tim_Allen.jpg", "tmdb_person_id": 12898, "order": 1},
        ],
    },
    "Avatar: Fire and Ash": {
        "poster_url": "/static/img/posters/Avatar_Fire_and_Ash.jpg",
        "trailer_youtube_url": "https://youtu.be/nb_fFj_0rq8?si=LADy-De-2Lcr-MvW",
        "cast": [
            {"name": "Sam Worthington", "character_name": "Jake Sully", "photo_url": "/static/img/cast/Sam_Worthington.jpg", "tmdb_person_id": 65731, "order": 0},
            {"name": "Zoe Saldaña", "character_name": "Neytiri", "photo_url": "/static/img/cast/Zoe_Salda_a.jpg", "tmdb_person_id": 8691, "order": 1},
            {"name": "Sigourney Weaver", "character_name": "Kiri", "photo_url": "/static/img/cast/Sigourney_Weaver.jpg", "tmdb_person_id": 10205, "order": 2},
        ],
    },
    "The Odyssey": {
        "poster_url": "/static/img/posters/The_odysseys.jpg",
        "trailer_youtube_url": "https://youtu.be/Mzw2ttJD2qQ?si=gldeuQESTNh9Q3Rm",
        "cast": [
            {"name": "Ralph Fiennes", "character_name": "Odysseus", "photo_url": "/static/img/cast/Ralph_Fiennes.jpg", "tmdb_person_id": 11288, "order": 0},
            {"name": "Juliette Binoche", "character_name": "Penelope", "photo_url": "/static/img/cast/Juliette_Binoche.jpg", "tmdb_person_id": 1039, "order": 1},
        ],
    },
    "Supergirl": {
        "poster_url": "/static/img/posters/Super_girl.jpg",
        "trailer_youtube_url": "https://youtu.be/s1-pfiVMKAs?si=OUk8890q7ZmnDo1P",
        "cast": [
            {"name": "Milly Alcock", "character_name": "Kara Zor-El / Supergirl", "photo_url": "/static/img/cast/Milly_Alcock.jpg", "tmdb_person_id": 1392137, "order": 0},
            {"name": "Matthias Schoenaerts", "character_name": "Krem", "photo_url": "/static/img/cast/Matthias_Schoenaerts.jpg", "tmdb_person_id": 54633, "order": 1},
        ],
    },
}


class Command(BaseCommand):
    help = "Seed the database with 20 real movies and showtimes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear all existing data before seeding.",
        )
        parser.add_argument(
            "--skip-if-seeded",
            action="store_true",
            help=(
                "No-op if the database already contains movies. Used on deploy "
                "(build.sh) so the seed runs once on an empty DB and is safely "
                "skipped on every subsequent deploy."
            ),
        )

    def handle(self, *args, **options):
        if options["skip_if_seeded"] and Movie.objects.exists():
            self.stdout.write(self.style.NOTICE(
                f"Database already seeded ({Movie.objects.count()} movies present) "
                f"- skipping structural seed."
            ))
            # The structural seed (cities/theaters/movies/shows) is skipped, but
            # poster/trailer/cast data must STILL be applied every deploy: on the
            # live Render DB the movies already exist, so this early-return path
            # is the only one that runs there. Idempotent upsert, safe to repeat.
            self._apply_media_and_cast()
            return

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
        self._apply_media_and_cast()

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
        # Fixed past date so ALL 20 movies qualify as "now showing" for demo.
        past = date(2026, 1, 1)

        movie_data = [
            # --- Malayalam (7) ---
            {
                "title": "Bazooka",
                "language": "Malayalam",
                "genres": ["Action", "Thriller"],
                "duration_minutes": 145,
                "rating": Movie.RatingChoices.UA,
                "release_date": past,
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
                "release_date": past,
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
                "release_date": past,
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
                "release_date": past,
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
                "release_date": past,
                "is_now_showing": True,
                "description": "A heartwarming saga set in rural Palakkad about three generations of traditional farmers protecting their land against urban development.",
                "cast_info": [{"name": "Suraj Venjaramoodu", "role": "Raman"}, {"name": "Nimisha Sajayan", "role": "Lakshmi"}, {"name": "Indrans", "role": "Kuttan"}],
            },
            {
                "title": "Kathanar: The Wild Sorcerer",
                "language": "Malayalam",
                "genres": ["Period Fantasy"],
                "duration_minutes": 160,
                "rating": Movie.RatingChoices.UA,
                "release_date": past,
                "is_now_showing": True,
                "description": "Jayasurya stars as Kadamattathu Kathanar, the legendary 9th-century priest endowed with mystical powers, battling ancient dark sorcery.",
                "cast_info": [{"name": "Jayasurya", "role": "Kathanar"}, {"name": "Anushka Shetty", "role": "Kalliyankattu Neeli"}, {"name": "Vineeth", "role": "High Priest"}],
            },
            {
                "title": "Tiki Taka",
                "language": "Malayalam",
                "genres": ["Sports Drama"],
                "duration_minutes": 135,
                "rating": Movie.RatingChoices.U,
                "release_date": past,
                "is_now_showing": True,
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
                "release_date": past,
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
                "release_date": past,
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
                "release_date": past,
                "is_now_showing": True,
                "description": "The epic sequel to the legendary 1997 war film. Sunny Deol returns to lead a brave battalion defending India's western frontier.",
                "cast_info": [{"name": "Sunny Deol", "role": "Major Kuldip"}, {"name": "Varun Dhawan", "role": "Captain Arjun"}, {"name": "Diljit Dosanjh", "role": "Subedar Gurdev"}],
            },
            {
                "title": "Cocktail 2",
                "language": "Hindi",
                "genres": ["Romantic Comedy"],
                "duration_minutes": 130,
                "rating": Movie.RatingChoices.UA,
                "release_date": past,
                "is_now_showing": True,
                "description": "A glamorous modern rom-com following three spirited friends navigating love, heartbreaks, and career ambitions in London.",
                "cast_info": [{"name": "Shahid Kapoor", "role": "Dev"}, {"name": "Kriti Sanon", "role": "Tanya"}, {"name": "Rashmika Mandanna", "role": "Sia"}],
            },
            {
                "title": "Main Vaapas Aaunga",
                "language": "Hindi",
                "genres": ["Drama"],
                "duration_minutes": 125,
                "rating": Movie.RatingChoices.U,
                "release_date": past,
                "is_now_showing": True,
                "description": "An inspiring emotional drama about an exiled soldier returning to his ancestral Himalayan village to restore his family honor.",
                "cast_info": [{"name": "Pankaj Tripathi", "role": "Bishamber"}, {"name": "Rajkummar Rao", "role": "Suraj"}, {"name": "Bhumi Pednekar", "role": "Radha"}],
            },
            {
                "title": "Baby Do Die Do",
                "language": "Hindi",
                "genres": ["Comedy Thriller"],
                "duration_minutes": 128,
                "rating": Movie.RatingChoices.UA,
                "release_date": past,
                "is_now_showing": True,
                "description": "A quirky dark comedy thriller where two bumbling kidnappers accidentally abduct a dangerous underworld don's pampered pet bulldog.",
                "cast_info": [{"name": "Ayushmann Khurrana", "role": "Bunty"}, {"name": "Jaideep Ahlawat", "role": "Don Gabbar"}, {"name": "Sanya Malhotra", "role": "Pinky"}],
            },
            {
                "title": "Karuppu",
                "language": "Hindi",
                "genres": ["Action"],
                "duration_minutes": 145,
                "rating": Movie.RatingChoices.A,
                "release_date": past,
                "is_now_showing": True,
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
                "release_date": past,
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
                "release_date": past,
                "is_now_showing": True,
                "description": "Moana and Maui set sail on a new epic voyage across Oceania to reunite broken island tribes and restore ancient ocean spirits.",
                "cast_info": [{"name": "Auli'i Cravalho", "role": "Moana"}, {"name": "Dwayne Johnson", "role": "Maui"}],
            },
            {
                "title": "Toy Story 5",
                "language": "English",
                "genres": ["Animation"],
                "duration_minutes": 105,
                "rating": Movie.RatingChoices.U,
                "release_date": past,
                "is_now_showing": True,
                "description": "Woody, Buzz, and the gang confront their biggest competitor yet — electronic tech gadgets that threaten to replace classic toys.",
                "cast_info": [{"name": "Tom Hanks", "role": "Woody"}, {"name": "Tim Allen", "role": "Buzz Lightyear"}],
            },
            {
                "title": "Avatar: Fire and Ash",
                "language": "English",
                "genres": ["Sci-Fi", "Adventure"],
                "duration_minutes": 170,
                "rating": Movie.RatingChoices.UA,
                "release_date": past,
                "is_now_showing": True,
                "description": "James Cameron's stunning third chapter introduces the Ash People, a volcanic Na'vi tribe, expanding the world of Pandora like never before.",
                "cast_info": [{"name": "Sam Worthington", "role": "Jake Sully"}, {"name": "Zoe Saldaña", "role": "Neytiri"}, {"name": "Oona Chaplin", "role": "Varang"}],
            },
            {
                "title": "The Odyssey",
                "language": "English",
                "genres": ["Adventure"],
                "duration_minutes": 155,
                "rating": Movie.RatingChoices.UA,
                "release_date": past,
                "is_now_showing": True,
                "description": "Homer's timeless myth brought to life. King Odysseus faces mythical beasts, vengeful gods, and treacherous seas on his ten-year journey home.",
                "cast_info": [{"name": "Ralph Fiennes", "role": "Odysseus"}, {"name": "Juliette Binoche", "role": "Penelope"}],
            },
            {
                "title": "Supergirl",
                "language": "English",
                "genres": ["Superhero Action"],
                "duration_minutes": 138,
                "rating": Movie.RatingChoices.UA,
                "release_date": past,
                "is_now_showing": True,
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
    # Media + Cast (poster_url / trailer_youtube_url / CastMember)
    # -------------------------------------------------------------------------
    def _apply_media_and_cast(self):
        """
        Upsert baked poster/trailer URLs and structured CastMember rows.

        Runs on EVERY deploy, on both the full-seed path and the
        --skip-if-seeded early-return path, because the live Render DB is
        already seeded and only the early-return path executes there. Fully
        idempotent:
          - poster_url / trailer_youtube_url written only when the value differs
          - CastMember via update_or_create keyed on (movie, name)
        backdrop_url is deliberately left to sync_backdrops.
        """
        movies_updated = 0
        posters_set = 0
        trailers_set = 0
        cast_upserts = 0
        cast_created = 0
        missing_titles = []

        for title, media in MEDIA_AND_CAST.items():
            movie = Movie.objects.filter(title=title).first()
            if not movie:
                missing_titles.append(title)
                continue

            # --- poster / trailer (only save when something actually changed) ---
            changed_fields = []
            poster = media.get("poster_url") or ""
            trailer = media.get("trailer_youtube_url") or ""

            if poster and movie.poster_url != poster:
                movie.poster_url = poster
                changed_fields.append("poster_url")
            if trailer and movie.trailer_youtube_url != trailer:
                movie.trailer_youtube_url = trailer
                changed_fields.append("trailer_youtube_url")

            if changed_fields:
                movie.save(update_fields=changed_fields)
                movies_updated += 1
            if poster:
                posters_set += 1
            if trailer:
                trailers_set += 1

            # --- cast (idempotent upsert keyed on movie + actor name) ---
            for member in media.get("cast", []):
                _, created = CastMember.objects.update_or_create(
                    movie=movie,
                    name=member["name"],
                    defaults={
                        "character_name": member.get("character_name", ""),
                        "photo_url": member.get("photo_url"),
                        "tmdb_person_id": member.get("tmdb_person_id"),
                        "order": member.get("order", 0),
                    },
                )
                cast_upserts += 1
                if created:
                    cast_created += 1

        self.stdout.write(self.style.SUCCESS(
            f"  + media/cast applied: {posters_set} posters, {trailers_set} trailers, "
            f"{cast_upserts} cast rows ({cast_created} new); {movies_updated} movies updated"
        ))
        if missing_titles:
            self.stdout.write(self.style.WARNING(
                f"  ! {len(missing_titles)} MEDIA_AND_CAST titles matched no Movie: "
                f"{', '.join(repr(t) for t in missing_titles)}"
            ))

    # -------------------------------------------------------------------------
    # Shows
    # -------------------------------------------------------------------------
    def _create_shows(self, movies, theaters):
        screens = list(Screen.objects.select_related("theater", "theater__city").all())
        if not screens:
            return

        # BookMyShow-style: every movie plays at every screen, 2-3 times/day, 7 days
        all_slots = [time(10, 0), time(13, 15), time(16, 30), time(19, 45), time(22, 30)]
        formats_map = {
            "IMAX": "IMAX", "4DX": "4DX", "PXL": "PXL",
            "LUXE": "LUXE", "DOLBY": "4K LASER DOLBY 7.1",
        }

        def screen_format(name):
            for key, fmt in formats_map.items():
                if key in name.upper():
                    return fmt
            return "2D"

        shows_created = 0

        for m_idx, movie in enumerate(movies):
            for day_offset in range(7):
                show_date = date.today() + timedelta(days=day_offset)

                for s_idx, screen in enumerate(screens):
                    fmt = screen_format(screen.name)
                    base = (m_idx + s_idx + day_offset) % len(all_slots)
                    num_slots = 3 if (m_idx + s_idx) % 3 != 0 else 2

                    for i in range(num_slots):
                        si = (base + i * 2) % len(all_slots)
                        show_time = all_slots[si]
                        start_dt = timezone.make_aware(
                            timezone.datetime.combine(show_date, show_time)
                        )
                        cancellation = (m_idx + s_idx + day_offset) % 2 == 0

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

        self.stdout.write(f"  + {shows_created} shows created (BookMyShow-style: all movies × all screens × 7 days)")

