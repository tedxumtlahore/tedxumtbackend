# TEDxUMT Lahore — API Reference

Base URL (development): `http://127.0.0.1:8000/api/`

`GET /api/` returns a live, machine-readable index of every endpoint below.

---

## Conventions

**Authentication.** Two schemes, both accepted everywhere. Session auth drives
the CMS — organizers sign in at `/admin/` and that session authorises API
writes. JWT (`/api/auth/token/`) exists for the volunteer check-in scanner,
which runs on a phone with no session cookie. The public site authenticates for
neither: it reads content anonymously and posts to the form endpoints.

**Permissions.**

| Class | Behaviour | Used by |
|---|---|---|
| `IsStaffOrReadOnly` | Anyone reads, only staff writes | All content endpoints |
| `CreateOnlyOrStaff` | Anyone POSTs, only staff reads/edits | Submission endpoints |
| `IsVolunteer` | Volunteers group, or staff | Check-in endpoints |
| `IsOrganizer` | Organizers group, or staff | Ticketing collections |

**Pagination.** List endpoints return
`{"count": N, "next": url, "previous": url, "results": [...]}`.
Page size defaults to 20 (48 for gallery images); override with
`?page=2&page_size=50` up to the per-endpoint maximum.

The flat convenience endpoints (`/api/team/`, `/api/blog/`, `/api/sponsors/`,
`/api/gallery/`, `/api/about/`, `/api/site-config/`) are **not** paginated —
they return the full payload the matching page needs in one request.

**Filtering, search, ordering.** Most collections accept `?search=<text>` and
`?ordering=<field>` (prefix `-` to reverse), plus the per-endpoint filters
listed below.

**Errors.** Every non-2xx response uses one shape:

```json
{
  "success": false,
  "message": "Please write at least 20 characters so we can help properly.",
  "errors": { "message": ["Please write at least 20 characters..."] },
  "status_code": 400
}
```

`message` is safe to show the user directly; `errors` is keyed by field name for
inline form validation.

**Visibility.** Anonymous requests only ever see rows that are `is_active` and
(where the model has it) `is_visible`. Draft events and draft blog posts are
hidden from the public but visible to a signed-in staff user, so organizers can
preview unpublished content through the same endpoints.

**Throttling.** 1000 requests/hour anonymous, 5000/hour authenticated.
Form submissions are limited to 10/hour, newsletter signups to 20/hour, and
event registration to 15/hour per IP; staff are exempt. Check-in is capped at
2000/hour per volunteer — high enough for a full event day, low enough to bound
a compromised account.

---

## Service

| Method | Endpoint | Notes |
|---|---|---|
| GET | `/api/` | Index of all endpoints |
| GET | `/api/health/` | Liveness probe; 503 if the database is unreachable |
| GET | `/api/common/status-choices/` | Shared draft/published status choices |

---

## Site shell

| Method | Endpoint | Notes |
|---|---|---|
| GET | `/api/site-config/` | **Boot payload** — settings, hero, navigation, social links, FAQs |
| GET | `/api/settings/` | Global settings only |
| GET | `/api/navigation/` | Visible nav items, ordered |
| GET | `/api/social/` | Visible social links |
| GET | `/api/faq/` | Visible FAQs |
| GET / PUT / PATCH | `/api/website-settings/` | Editable singleton |
| GET / PUT / PATCH | `/api/hero/` | Editable singleton |
| GET / POST | `/api/navigation-items/` | Collection |
| GET / POST | `/api/social-links/` | Filter: `platform` |
| GET / POST | `/api/faqs/` | Collection |

`website-settings` and `hero` are one-row models, so they live at a single URL —
there is no `/1/` detail route.

---

## About page

| Method | Endpoint | Notes |
|---|---|---|
| GET | `/api/about/` | Sections + core values + messages combined |
| GET / POST | `/api/about-sections/` | Detail key: `section_key` |
| GET / POST | `/api/core-values/` | Filter: `icon_key` |
| GET / POST | `/api/messages/` | Detail key: `message_type` |

---

## Events

| Method | Endpoint | Notes |
|---|---|---|
| GET / POST | `/api/events/` | Filters: `event_type`, `status`, `is_featured`, `year` |
| GET / PUT / PATCH / DELETE | `/api/events/{slug}/` | Includes venue, schedule, and speakers |
| GET | `/api/events/upcoming/` | Future events, soonest first |
| GET | `/api/events/featured/` | Homepage picks |
| GET | `/api/events/options/` | Event type and status choice lists |
| GET / POST | `/api/venues/` | Filter: `city` |
| GET / POST | `/api/event-schedule-items/` | Filter: `event` (slug) |

Slugs are generated from the title and are never editable. `end_datetime` must be
after `start_datetime` — enforced in both the admin and the API.

---

## Speakers

| Method | Endpoint | Notes |
|---|---|---|
| GET / POST | `/api/speakers/` | Filters: `featured`, `event` (slug) |
| GET / PUT / PATCH / DELETE | `/api/speakers/{slug}/` | Adds bio and social links |
| GET | `/api/speakers/featured/` | Homepage picks |

---

## Team

| Method | Endpoint | Notes |
|---|---|---|
| GET | `/api/team/` | Departments with members nested — powers the Team page |
| GET / POST | `/api/departments/{slug}/` | Members nested on list and detail |
| GET / POST | `/api/team-members/{slug}/` | Filter: `department` (slug) |

---

## Gallery

| Method | Endpoint | Notes |
|---|---|---|
| GET | `/api/gallery/` | Flat feed; filters: `media_type`, `album`, `limit` |
| GET / POST | `/api/gallery-albums/{slug}/` | Detail nests visible images; filter: `event` |
| GET / POST | `/api/gallery-images/` | Filters: `album`, `media_type` |

`media_type` is one of `photo`, `video`, `bts`. Video items require a
`video_url`; the uploaded image acts as the thumbnail. When creating an image via
the API, send the file as `image_upload` (the read-only `image` field returns the
absolute URL).

---

## Blog

| Method | Endpoint | Notes |
|---|---|---|
| GET | `/api/blog/` | Featured post + remaining posts + categories |
| GET / POST | `/api/blog-posts/` | Filters: `category`, `tag`, `featured` |
| GET / PUT / PATCH / DELETE | `/api/blog-posts/{slug}/` | Adds `content` and `related_posts` |
| GET / POST | `/api/blog-categories/{slug}/` | Includes published post counts |
| GET / POST | `/api/blog-tags/{slug}/` | Collection |

Only `status="published"` posts are visible anonymously. Publishing stamps
`published_at` once and never overwrites it. `reading_minutes` is estimated from
the content length unless set explicitly.

---

## Sponsors

| Method | Endpoint | Notes |
|---|---|---|
| GET | `/api/sponsors/` | Tiers in rank order with sponsors nested |
| GET / POST | `/api/sponsor-tiers/{slug}/` | `benefit_list` splits `benefits` per line |
| GET / POST | `/api/sponsor-list/{slug}/` | Filters: `tier`, `event` |

---

## Submissions

All of these accept an anonymous `POST`. Reading, editing, and triaging require
staff. On success they return `201` with:

```json
{ "success": true, "message": "Message sent — we'll be in touch soon.", "id": 12 }
```

`status`, `internal_notes`, and `submitted_ip` are set server-side and can never
be supplied by the submitter.

| Method | Endpoint | Required fields |
|---|---|---|
| POST | `/api/contact/` | `name`, `email`, `subject`, `message` (min 20 chars) |
| POST | `/api/newsletter/` | `email` |
| POST | `/api/newsletter/unsubscribe/` | `email` |
| GET | `/api/apply/options/` | — (dropdown choices for the forms) |
| POST | `/api/apply/speaker/` | `full_name`, `email`, `talk_title`, `talk_summary` (min 50 chars) |
| POST | `/api/apply/volunteer/` | `full_name`, `email`, `motivation` (min 20 chars) |
| POST | `/api/apply/partner/` | `organization_name`, `contact_person`, `email`, `proposal` (min 20 chars) |

Subscribing an address twice is not an error — it re-subscribes a previously
removed address instead of returning a uniqueness failure.

Staff inboxes (all support `?status=` and `?search=`):

| Endpoint | Extra actions |
|---|---|
| `/api/contact-messages/` | `POST {id}/mark-read/` |
| `/api/newsletter-subscribers/` | `?subscribed=true|false` |
| `/api/speaker-applications/` | |
| `/api/volunteer-applications/` | |
| `/api/partner-applications/` | |

Submission `status` values: `new`, `in_review`, `accepted`, `rejected`, `archived`.

---

## Media URLs

Every image field returns an **absolute** URL built from the incoming request
(e.g. `http://127.0.0.1:8000/media/gallery/images/TEDx.jpg`), so the frontend can
use the value directly without joining paths. Fields with no upload return `null`
— the frontend substitutes a placeholder.

---

## Ticketing, registration & check-in

Added by the ticketing module. The existing `Event` gained ticketing fields
rather than a second event table being introduced — `max_attendees` is the
capacity, and `title`/`venue`/`start_datetime` were already there.

### Attendee (public)

| Method | Endpoint | Notes |
|---|---|---|
| GET | `/api/events/{slug}/ticketing/` | Price, capacity, seats remaining, whether registration is open and why not |
| POST | `/api/events/{slug}/register/` | `full_name`, `email`, `phone` required; `cnic`, `university`, `occupation` optional |
| GET | `/api/registrations/status/{public_ref}/` | The attendee's own status, by unguessable UUID |
| GET | `/api/tickets/by-token/{access_token}/` | The attendee's ticket, including the QR payload |
| GET | `/api/tickets/by-token/{access_token}/qr.png` | The QR image itself, rendered on demand |
| GET | `/api/tickets/by-token/{access_token}/pdf/` | The printable PDF ticket |

Registration returns `201` with the registration and a `payment` block:

```json
{
  "success": true,
  "registration": { "ticket_number": "TEDX2026-0001", "ticket_access_token": "…" },
  "payment": { "kind": "none|instructions|redirect", "message": "…", "details": {} }
}
```

Business-rule rejections return **409**, not 400 — the input was well formed,
the world said no. `code` distinguishes them: `duplicate_email`,
`duplicate_cnic`, `registration_closed`.

### Volunteer (requires the Volunteers group)

| Method | Endpoint | Notes |
|---|---|---|
| POST | `/api/auth/token/` | Obtain a JWT pair. Also `token/refresh/`, `token/verify/` |
| POST | `/api/checkin/verify/` | Read-only lookup — shows the attendee without consuming the ticket |
| POST | `/api/checkin/` | Verify **and** consume. 200 when allowed, 409 otherwise |
| GET | `/api/checkin/history/` | This volunteer's last 50 scans |

Both check-in endpoints accept either the bare `qr_token` or the full URL the QR
encodes. Results: `allowed`, `duplicate`, `invalid`, `unpaid`, `wrong_event`,
`cancelled`. Pass `event=<slug>` to scope a door to one event.

### Organizer (requires the Organizers group)

`POST /api/tickets/{ticket_number}/resend/` re-sends a ticket email.

Read-only: `/api/registrations/`, `/api/orders/`, `/api/tickets/`,
`/api/check-in-logs/`. All support `?search=`, `?ordering=`, and
`?event_slug=`. State changes happen through the admin's audited actions, never
through a PATCH.

### Design notes worth knowing

**No public lookup by ticket number.** Ticket numbers are sequential, so a
public endpoint keyed on them would let anyone enumerate the attendee list. The
PRD's `GET /api/ticket/{ticket_number}` is served instead at
`/api/tickets/by-token/{access_token}/`.

**Two tokens per ticket.** `qr_token` is what the door scanner accepts;
`access_token` is what the attendee's page uses. A shared screenshot of a ticket
page URL therefore does not hand over the value that opens the door.

**CNIC is never stored.** A salted hash enforces one-registration-per-person and
the last four digits let a volunteer eye-match an ID card. The number itself is
accepted, hashed, and discarded.

**Ticket numbers.** `TEDX{year}-0001`, per event. A second event in the same
year gets `TEDX{year}-2-0001`, since the year-derived prefix alone would
collide. Set `Event.ticket_prefix` for something specific.

**Payment.** A provider abstraction with two implementations: free events settle
instantly, priced events use bank transfer confirmed by an organizer in the
admin. A real gateway is one class plus a signed webhook, with no changes to
registration, tickets, or check-in. Nothing a client sends can mark an order
paid.

**Delivery.** The ticket email goes out on `transaction.on_commit`, so it is
only sent once the ticket is durably saved, and a mail failure is logged rather
than raised — a dead SMTP server must not roll back a paid registration. QR and
PDF are generated per request and never written to disk, so a deploy on an
ephemeral filesystem cannot destroy an issued ticket. `TICKET_BASE_URL`
configures the public address the QR and ticket links point at.
