# TEDxUMT Backend Development Roadmap

Status: **CMS phases complete; ticketing Stage 1 complete.** 192 backend tests
passing; frontend builds clean and every route is wired to the API.

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

## Stage 2 — ticket delivery (next)

- [ ] QR image generation (`qrcode`)
- [ ] PDF ticket (`reportlab`)
- [ ] Email on issue, via `transaction.on_commit`, failure-tolerant
- [ ] "Resend ticket" admin action and staff endpoint

## Stage 3 — attendee & volunteer frontend

- [ ] Registration form on the event page
- [ ] Ticket page with QR and PDF download
- [ ] Volunteer scanner (camera QR, retries queued scans)

## Stage 4 — organizer dashboard

- [ ] Live stats, analytics, CSV export

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
   count and resets on restart. Ticketing makes this matter — point `CACHES` at
   Redis before opening registration.
6. **`select_for_update` is a no-op on SQLite.** The oversell guard currently
   leans on SQLite's database-wide write lock. Verify the capacity and check-in
   concurrency tests against PostgreSQL before a real event.
7. **Seeded content is fictional.** The speakers and sponsors from
   `seed_content` are placeholders carried over from the prototype. Replace or
   clear them before the site is public — publishing invented sponsors implies
   relationships that do not exist.
