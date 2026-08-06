# TEDxUMT Lahore CMS

The content management system and REST API behind the TEDxUMT Lahore website.

Organizers edit everything — copy, events, speakers, team, gallery, blog,
sponsors — through the Django admin. The React frontend reads it all over a
versionless JSON API and posts form submissions back to it.

---

## Quick start

```bash
python -m venv .venv
```

```bash
.venv/Scripts/activate
```

```bash
pip install -r requirements.txt
```

Create a `.env` from the template (`cp .env.example .env`) and set at minimum:

```
SECRET_KEY=<any long random string>
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,testserver
```

Then set up the database and start the server:

```bash
python manage.py migrate
```

```bash
python manage.py createsuperuser
```

```bash
python manage.py seed_content
```

```bash
python manage.py runserver
```

- Admin CMS — <http://127.0.0.1:8000/admin/>
- API index — <http://127.0.0.1:8000/api/>
- Health probe — <http://127.0.0.1:8000/api/health/>

`seed_content` is idempotent, so it is safe to re-run. It populates the launch
content set and imports the prototype's photos into the gallery. Use
`--flush` to wipe seeded content first, or `--media-dir <path>` to import gallery
photos from somewhere other than `../frontend/src/images`.

---

## Tests

```bash
python manage.py test
```

120 tests covering models, serializers, permissions, validation, throttling,
and the full HTTP surface of every endpoint.

---

## Architecture

```
apps/
  common/        BaseModel, validators, permissions, pagination,
                 shared viewset mixins, unified API error handler
  core/          WebsiteSettings, HeroSection, Navigation, SocialLink, FAQ
  website/       AboutSection, CoreValue, Message
  events/        Venue, Event, EventScheduleItem
  speakers/      Speaker
  team/          Department, TeamMember
  gallery/       GalleryAlbum, GalleryImage
  blog/          Category, Tag, BlogPost
  sponsors/      SponsorTier, Sponsor
  applications/  ContactMessage, NewsletterSubscriber,
                 Speaker/Volunteer/Partner applications

tedxumt/
  settings/      base.py, development.py, production.py
  api_router.py  mounts every app's urls.py under /api/
  views.py       API index + health probe
```

Each app follows the same layout: `models.py`, `admin.py`, `serializers.py`,
`viewsets.py` (routed collections), `views.py` (flat page-shaped endpoints),
`urls.py`, `tests.py`.

### Conventions worth knowing

- **`BaseModel`** gives every content model `created_at`, `updated_at`, and
  `is_active`. Most also carry `is_visible` — `is_active` is a soft delete,
  `is_visible` is an editor's on/off switch.
- **Slugs** are generated from the title/name, are unique, and are not editable.
  They are the public lookup key for events, speakers, posts, and albums.
- **Page-shaped endpoints** (`/api/site-config/`, `/api/about/`, `/api/team/`,
  `/api/gallery/`, `/api/blog/`, `/api/sponsors/`) return everything one page
  needs in a single unpaginated request. The routed collections underneath them
  are for the CMS and for filtered queries.
- **Writes require a staff session.** Reads are public. Submission endpoints
  invert this: anyone can POST, only staff can read.

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for the full endpoint reference.

---

## Deployment

1. Set `DJANGO_SETTINGS_MODULE=tedxumt.settings.production`.
2. Fill in `.env` from `.env.example` — a real `SECRET_KEY`, `DEBUG=False`,
   `ALLOWED_HOSTS`, `DATABASE_URL`, and `CORS_ALLOWED_ORIGINS` pointing at the
   deployed frontend.
3. Uncomment the production extras in `requirements.txt` (gunicorn,
   psycopg2-binary, whitenoise) and install.
4. `python manage.py migrate && python manage.py collectstatic --noinput`
5. Serve with `gunicorn tedxumt.wsgi:application`.

Production settings enable HSTS, secure cookies, SSL redirect, and
`SECURE_PROXY_SSL_HEADER` for a TLS-terminating proxy; they disable the
browsable API and mail unhandled errors to `ADMIN_EMAIL`. WhiteNoise is wired up
automatically if it is installed.

`MEDIA_ROOT` is local disk by default. For a platform with an ephemeral
filesystem, move uploads to object storage (`django-storages`) before launch —
otherwise every deploy discards uploaded images.

---

## Tech stack

Django 5.2 · Django REST Framework · django-filter · django-cors-headers ·
django-environ · Pillow · SQLite (dev) / PostgreSQL (prod)

---

## License

Developed for TEDxUMT Lahore. All TED and TEDx branding remains the property of TED.
