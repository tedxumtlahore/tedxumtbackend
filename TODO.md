# TEDxUMT Backend Development Roadmap

Status: **CMS complete; ticketing complete (Stages 1-4).** 234 backend tests
passing; frontend builds clean and every route is wired to the API.

Scale: the event sells roughly **100 tickets**. That retires several concerns
below — see the notes against each.

## Phase 0 — Foundation

- [x] Configure virtual environment
- [x] Install dependencies
- [x] Configure environment variables
- [x] Configure CORS
- [x] Configure Media
- [x] Configure Static files
- [x] Verify Django settings
- [x] Initial Git commit

---

# Phase 1 — Common App

- [x] Create common app
- [x] BaseModel
- [x] TimeStampedModel
- [x] ActiveModel
- [x] StatusChoices
- [x] Validators
- [x] Utilities
- [x] Tests

Added since: shared permissions, pagination, viewset mixins, and a unified API
exception handler.

---

# Phase 2 — Core App

- [x] WebsiteSettings
- [x] HeroSection
- [x] NavigationItem
- [x] SocialLink
- [x] FAQ

- [x] Admin
- [x] Serializers
- [x] ViewSets
- [x] URLs
- [x] Migrations
- [x] Tests

---

# Phase 3 — Website App

- [x] AboutSection
- [x] CoreValue
- [x] Message

- [x] Admin
- [x] Serializers
- [x] ViewSets
- [x] URLs
- [x] Tests

---

# Phase 4 — Events

- [x] Venue
- [x] Event
- [x] EventScheduleItem

- [x] Admin
- [x] Serializers
- [x] ViewSets
- [x] URLs
- [x] Tests

---

# Phase 5 — Speakers

- [x] Speaker

- [x] Admin
- [x] Serializers
- [x] ViewSets
- [x] URLs
- [x] Tests

---

# Phase 6 — Team

- [x] Department
- [x] TeamMember

- [x] Admin
- [x] Serializers
- [x] ViewSets
- [x] URLs
- [x] Tests

---

# Phase 7 — Gallery

- [x] GalleryAlbum
- [x] GalleryImage

- [x] Admin
- [x] Serializers
- [x] ViewSets
- [x] URLs
- [x] Tests

---

# Phase 8 — Blog

- [x] Category
- [x] Tag
- [x] BlogPost

- [x] Admin
- [x] Serializers
- [x] ViewSets
- [x] URLs
- [x] Tests

---

# Phase 9 — Sponsors

- [x] SponsorTier
- [x] Sponsor

- [x] Admin
- [x] Serializers
- [x] ViewSets
- [x] URLs
- [x] Tests

---

# Phase 10 — Applications

- [x] ContactMessage
- [x] NewsletterSubscriber
- [x] SpeakerApplication
- [x] VolunteerApplication
- [x] PartnerApplication

- [x] Validation
- [x] APIs
- [x] Tests

---

# Phase 11 — Frontend Integration

- [x] Axios configuration
- [x] API service layer
- [x] Events integration
- [x] Speakers integration
- [x] Team integration
- [x] Blog integration
- [x] Gallery integration
- [x] Sponsors integration
- [x] Contact API
- [x] Newsletter API

Also: About, Home, Sponsors, and the Apply page's three application tracks.
`src/data/siteData.js` is no longer imported anywhere.

---

# Phase 12 — Production

- [x] Authentication (session auth; admin is the CMS entry point)
- [x] Permissions (`IsStaffOrReadOnly`, `CreateOnlyOrStaff`)
- [x] Pagination (default 20, `?page_size=` up to 100)
- [x] Filtering (django-filter + per-endpoint query params)
- [x] Search (`?search=` on all collections)
- [x] Logging (rotating file + console; errors mailed to admins in production)
- [x] Error handling (single JSON error shape across the whole API)
- [x] Documentation (README, API_DOCUMENTATION.md, frontend README)
- [x] Deployment (production settings, WhiteNoise, proxy SSL header)
- [x] Final testing

---

# Final Checklist

- [x] All models complete
- [x] Admin fully functional
- [x] APIs documented
- [x] Frontend connected
- [x] Database migrated
- [x] Production deployment configured (not yet executed)
- [x] README updated
- [x] Documentation complete
- [x] Version 1.0 ready

---

# Phase 13 — Ticketing, Registration & Check-in (TicketPRD.md)

## Stage 1 — core backend ✅

- [x] Event ticketing fields (price, currency, registration window, hold, prefix)
- [x] Registration, Order, Ticket, TicketSequence, CheckInLog
- [x] Payment provider abstraction — free + manual bank transfer
- [x] Volunteers / Organizers groups, `IsVolunteer` / `IsOrganizer`
- [x] JWT for the scanner (alongside session auth, with token blacklist)
- [x] Registration, payment, ticket, check-in verify/perform, history endpoints
- [x] Admin with audited "Confirm payment and issue ticket" action
- [x] 61 tests covering the five correctness properties + PRD edge cases

Deliberate deviations from the PRD, and why:

1. **No public `GET /api/ticket/{ticket_number}`.** Ticket numbers are
   sequential, so that endpoint would let anyone enumerate the attendee list.
   The attendee reads their ticket at `/api/tickets/by-token/{access_token}/`.
2. **CNIC is hashed, not stored.** A salted hash enforces the duplicate rule and
   the last four digits allow an ID check at the door.
3. **No live payment gateway.** A provider abstraction with free and
   manual-transfer implementations; a real gateway is one class plus a signed
   webhook.

## Stage 2 — ticket delivery ✅

- [x] QR image generation (`qrcode`), served at `/qr.png`
- [x] Printable PDF ticket (`reportlab`), ticket-sized rather than A4
- [x] Email on issue via `transaction.on_commit`, failure-tolerant
- [x] "Resend ticket" admin action and organizer endpoint
- [x] 23 further tests

Notes:

- **Nothing is stored.** QR and PDF are rendered per request. A stored PDF on
  an ephemeral filesystem would vanish on deploy and 404 at the door.
- **QR quiet zone is 4 modules**, the spec minimum. Measured: a 2- or 3-module
  border fails to decode. `QR_QUIET_ZONE` guards this with a test.
- **Email is best effort.** A dead SMTP server logs and moves on; the ticket
  still exists and is viewable online. Resend is the retry path.
- **Delivery is synchronous** — there is no queue. Fine for one event's volume;
  move behind Celery before a large on-sale.

## Stage 3 — attendee & volunteer frontend ✅

- [x] Registration form at `/events/<slug>/register`, linked from the event page
- [x] Ticket page at `/ticket/<access_token>` with QR and PDF download
- [x] Volunteer scanner at `/checkin` (and `/checkin/<token>` from a scanned QR)
- [x] JWT sign-in with shared-refresh handling

PRD edge cases handled in the UI:

- **Camera permission denied** — a manual entry box is always present, and the
  denial is explained rather than leaving a dead black rectangle.
- **Volunteer loses internet** — scans queue in `localStorage` and replay on
  reconnect. A refused ticket is a resolved outcome and is dropped rather than
  retried forever.
- **Repeated decodes** — the camera fires continuously, so the same code is
  ignored for 3 seconds after a scan.
- **A refused scan still shows the attendee.** The 409 carries the name and
  ticket number, which is exactly what a volunteer needs to explain a refusal
  to the person in front of them.

## Stage 4 — organizer dashboard ✅

- [x] `/api/dashboard/` — capacity, registrations, door counts, money, arrivals
- [x] `/api/analytics/` — dense daily series
- [x] `/api/registrations/export/` — attendee CSV
- [x] `/organizer` page: live stats refreshing every 15s, event picker, CSV button
- [x] 19 further tests

Notes:

- **The export is an allow-list.** `EXPORT_COLUMNS` excludes the CNIC hash and
  both ticket tokens — a spreadsheet carrying a scan token is working door
  access sitting in a downloads folder. A test asserts the exclusions so a new
  model field cannot silently join the file.
- **A failed background poll keeps the last good numbers on screen** rather than
  blanking the dashboard someone is watching mid-event.
- **The chart is hand-rolled.** Fourteen bars did not justify a charting
  dependency larger than the rest of the dashboard.
- **Money is quantized.** `Sum()` drops the decimal scale on SQLite, which
  showed a total of "1500" beside a price of "1500.00".

---

# Known gaps before going live

1. **Media storage.** Uploads go to local disk. On a platform with an ephemeral
   filesystem (Render, Heroku), every deploy discards them — move to object
   storage via `django-storages` first.
2. **Large bundled images.** `TED.png` (1.9 MB) and `UMT Campus 2.jpeg` (5 MB)
   ship in the frontend bundle. Compress or move them into the CMS.
3. **`Speaker.event` is required.** A speaker cannot be created before their
   event exists. Intentional, but worth revisiting if speakers are ever announced
   before an event is scheduled.
4. **No caching layer.** Fine at current traffic; add per-view caching on the
   page-shaped endpoints if load becomes a concern.
5. **Throttling is per-process.** DRF counts against Django's default
   `LocMemCache`, so under gunicorn the registration limit multiplies by worker
   count. *At ~100 tickets a single worker is ample, so this is not a launch
   blocker* — it becomes one only if the site is scaled out.
6. **`select_for_update` is a no-op on SQLite.** The oversell guard leans on
   SQLite's database-wide write lock instead. *At this scale SQLite is genuinely
   adequate*, and the write lock does serialise the capacity check. Worth
   re-verifying on PostgreSQL only if the event grows or registration opens with
   a rush on the last few seats.
7. **No task queue.** Email is synchronous. *At ~100 tickets spread over days
   this is a non-issue*; Celery only matters for a large simultaneous on-sale.
8. **Seeded content is fictional.** The speakers and sponsors from
   `seed_content` are placeholders carried over from the prototype. Replace or
   clear them before the site is public — publishing invented sponsors implies
   relationships that do not exist.
