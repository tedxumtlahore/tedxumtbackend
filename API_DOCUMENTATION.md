# TEDxUMT Lahore — API Reference

Base URL (development): `http://127.0.0.1:8000/api/`

`GET /api/` returns a live, machine-readable index of every endpoint below.

---

## Conventions

**Authentication.** Session authentication only. The public site never
authenticates — it reads content anonymously and posts to the form endpoints.
Organizers sign in at `/admin/`; that same session authorises API writes.

**Permissions.**

| Class | Behaviour | Used by |
|---|---|---|
| `IsStaffOrReadOnly` | Anyone reads, only staff writes | All content endpoints |
| `CreateOnlyOrStaff` | Anyone POSTs, only staff reads/edits | All submission endpoints |

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
Form submissions are limited to 10/hour and newsletter signups to 20/hour per IP;
staff are exempt.

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
