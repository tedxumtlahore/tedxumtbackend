# TEDxUMT Backend Development Roadmap

Status: **all phases complete.** 120 backend tests passing; frontend builds clean
and every route is wired to the API.

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
