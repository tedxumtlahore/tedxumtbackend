# Deploying TEDxUMT

Vercel (site) → Render (API) → Supabase (Postgres + Storage).

The order below matters: the API needs the database before it can migrate, and
the QR codes need the site's final URL before any ticket is issued.

---

## 0. Before you start

Two things must be true or the deploy is wasted effort:

- **`DJANGO_SETTINGS_MODULE=tedxumt.settings.production` is set on Render.**
  `wsgi.py` falls back to the *development* module. Without this variable the
  API comes up with `DEBUG=True` and serves tracebacks containing settings and
  source code to anyone who can trigger a 500. `render.yaml` sets it; if you
  create the service by hand instead, set it by hand.

- **`TICKET_BASE_URL` is the Vercel origin, not the Render one.** It is what QR
  codes and "view your ticket" links encode. The API has no `/checkin` route,
  so pointing this at the API makes every ticket scan to a 404 — and you find
  out at the door.

---

## 1. Supabase

**Database.** Settings → Database → Connection string → **Session pooler**.
Not the direct connection (IPv6-only, and Render cannot reach it) and not
transaction mode (wrong shape for `loaddata`'s long transaction).

**Storage.** Create two buckets under Storage → New bucket:

| Bucket | Visibility | Holds |
|---|---|---|
| `tedx-media` | **Public** | gallery, portraits, sponsor logos, blog covers |
| `tedx-payment-proofs` | **Private** | transfer screenshots only |

The split is not cosmetic. A payment screenshot routinely shows the sender's
wallet balance and recent transactions; the private bucket means an unsigned
URL does not resolve even if the path leaks. `apps/common/storages.py` routes
`Order.payment_proof` to the private one and everything else to the public one.

No policies or folders need creating by hand. Public buckets are world-readable
already, the service key bypasses RLS for writes, and folders (`team/`,
`gallery/`, `speakers/`, …) are just key prefixes that appear as each model's
`upload_to` is first used.

Then Settings → Storage → S3 access keys → new key. **The secret is shown once.**
That key pair is separate from the anon/publishable and service keys, and it
grants full read/write to every bucket — server-side only, never in Vercel.

## 2. Render

Point Render at `render.yaml`, or create a web service manually with:

- Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
- Start: `gunicorn tedxumt.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --timeout 120`
- Health check: `/api/health/`

One worker is deliberate: DRF counts throttle hits in a per-process
`LocMemCache`, so N workers multiply the 15/hour registration cap by N.

**Do not use the free plan for the API.** Free instances sleep after ~15
minutes idle and take roughly a minute to wake — which is a failed page load
for every visitor after a quiet spell, and a stalled scanner when doors open.

### Environment variables

| Variable | Value |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `tedxumt.settings.production` |
| `SECRET_KEY` | freshly generated — never the development one |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `tedxumt-api.onrender.com` |
| `CORS_ALLOWED_ORIGINS` | the Vercel origin |
| `CSRF_TRUSTED_ORIGINS` | the Vercel origin **and** the Render origin |
| `TICKET_BASE_URL` | the Vercel origin |
| `DATABASE_URL` | Supabase session pooler string |
| `MEDIA_BUCKET` | `tedx-media` |
| `PRIVATE_MEDIA_BUCKET` | `tedx-payment-proofs` |
| `S3_ENDPOINT_URL` | `https://<project-ref>.storage.supabase.co/storage/v1/s3` |
| `S3_REGION` | the project's region |
| `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` | Storage → S3 access keys |
| `SUPABASE_URL` | `https://<project-ref>.supabase.co` — builds the public image URLs |
| `EMAIL_HOST` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | SMTP |
| `DEFAULT_FROM_EMAIL` | **must match the authenticated sending account**, or tickets land in spam |
| `ADMIN_EMAIL` | where 500s are mailed |

Leaving `MEDIA_BUCKET` unset falls back to local disk — correct only if you
have a real persistent volume, which Render's free tier does not offer at all.
Production logs a `RuntimeWarning` at startup when it is missing, because the
failure is otherwise invisible: uploads appear to succeed in the admin and then
serve a 404 to every visitor.

**Checking it worked.** After the first deploy, upload a photo to any Team
member and look at `/api/team/`. `photo` should read

```
https://<project-ref>.supabase.co/storage/v1/object/public/tedx-media/team/<name>-<8 hex>.jpg
```

If it still says `…onrender.com/media/…`, `MEDIA_BUCKET` did not reach the
process. If it contains `/storage/v1/s3/`, `SUPABASE_URL` is missing — that is
the signed-only S3 API path and a browser cannot read it.

### Media already in the database

Rows uploaded before storage was switched on still hold paths like
`team/new_02.jpg.jpeg`. `sync_media_to_storage` copies whatever is on local
disk into the bucket **under the same key**, so those rows start resolving with
no database change:

```bash
python manage.py sync_media_to_storage           # report only, writes nothing
python manage.py sync_media_to_storage --apply
```

It never deletes, never overwrites, and never edits a row, so it is safe to
re-run. It needs the files to actually be on the disk it runs against — on
Render they were discarded at the previous deploy, so run it locally with
`DATABASE_URL` pointed at Supabase, or simply re-upload through the admin.

## 3. Vercel

Root directory `frontend`. `vercel.json` already sets the build and the SPA
rewrite; without that rewrite every deep link 404s on refresh, **including every
ticket URL you email out**.

| Variable | Value |
|---|---|
| `VITE_API_URL` | `https://tedxumt-api.onrender.com/api` |
| `VITE_API_TIMEOUT` | omit for 30s; set `60000` if the API is on a plan that sleeps |

Vite inlines these at **build time**. Changing one requires a redeploy — editing
it in the dashboard does nothing to the build already serving traffic.

> Vercel's Hobby tier is non-commercial use only, and you are selling tickets.
> Worth reading their current terms before launch; the downside is suspension.

## 4. Seed the database

Everything currently in `db.sqlite3` is test data, fictional placeholder
content, or development credentials. Start clean:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_content
```

Then, through the admin:

- Re-upload the 6 real gallery images (they now land in Supabase Storage).
- Replace the **fictional** seeded speakers and sponsors. Publishing invented
  sponsors implies relationships that do not exist.
- Replace the **placeholder** payment account numbers (`0300 1234567`) with the
  real Easypaisa / JazzCash details. Someone's money goes wherever these point.

If you have hand-edited content worth keeping, dump it selectively instead:

```bash
python manage.py dumpdata core website events gallery blog team \
  --natural-foreign --natural-primary --indent 2 -o content.json
```

Use `-o`, never `>` — PowerShell redirection writes UTF-16 and `loaddata`
cannot read it. Never dump `contenttypes` or `auth.Permission`; `migrate`
creates them and loading them on top collides on the primary key.

## 5. Verify before trusting it

This is the first time the code runs on PostgreSQL, and `select_for_update`
stops being the no-op it is on SQLite — the oversell guard and the ticket-number
sequence take a genuinely different path than they ever have locally.

```bash
DATABASE_URL="postgresql://..." python manage.py test
```

Then, on the deployed site:

1. `GET /api/health/` returns 200.
2. Register for a paid event → payment instructions show the **real** account.
3. Confirm the order in the admin → ticket email arrives with the PDF attached.
4. Open the ticket URL → the QR renders.
5. **Scan that QR with an actual phone.** The camera path has never run on real
   hardware; decoding is proven and the scanner has a self-test mode, but the
   camera itself is unverified. It needs HTTPS, which both hosts provide.
6. Scan the same ticket twice → the second is refused as a duplicate.
