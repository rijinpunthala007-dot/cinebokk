"""
Data migration — relocate locally-stored media references to /static/img/.

Pre-seeded poster/cast/backdrop assets moved from /media/... to /static/img/...
so WhiteNoise + collectstatic serve them on Render's ephemeral filesystem.
This rewrites the string paths already stored in the database.

Reversible: flips /static/img/ back to /media/ for local rollback.
"""

from django.db import migrations


PREFIX_OLD = "/media/"
PREFIX_NEW = "/static/img/"

# (model_name, field_name) pairs holding stored path strings
STRING_FIELDS = [
    ("Movie", "poster_url"),
    ("Movie", "backdrop_url"),
    ("CastMember", "photo_url"),
]


def _rewrite(apps, from_prefix, to_prefix):
    for model_name, field_name in STRING_FIELDS:
        Model = apps.get_model("movies", model_name)
        for obj in Model.objects.all():
            val = getattr(obj, field_name) or ""
            if val.startswith(from_prefix):
                setattr(obj, field_name, to_prefix + val[len(from_prefix):])
                obj.save(update_fields=[field_name])

    # ImageField `poster` stores a relative path ("posters/x.jpg") without a
    # leading prefix; its URL is derived from STATIC/MEDIA at render time, so
    # there is no stored string to rewrite here.


def forwards(apps, schema_editor):
    _rewrite(apps, PREFIX_OLD, PREFIX_NEW)


def backwards(apps, schema_editor):
    _rewrite(apps, PREFIX_NEW, PREFIX_OLD)


class Migration(migrations.Migration):

    dependencies = [
        ("movies", "0002_movie_backdrop_url_movie_poster_url_movie_tmdb_id_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
