# TEDxUMT Backend Development Guide

Version: 1.0

---

# Project Goal

Develop a professional, scalable Django REST API backend for the official TEDxUMT Lahore website.

The backend should serve the React frontend as a complete CMS, allowing all website content to be managed through Django Admin.

The backend must be production-ready, modular, reusable, and easy to extend.

---

# Technology Stack

Backend
- Python 3.13+
- Django 5+
- Django REST Framework
- Pillow
- django-environ
- django-cors-headers

Database
- SQLite (Development)
- PostgreSQL (Production)

Frontend
- React
- Axios

Deployment
- Render
- Supabase Storage (optional later)

---

# Project Structure

apps/

    core/
    website/
    events/
    speakers/
    team/
    gallery/
    sponsors/
    blog/
    applications/

tedxumt/

    settings/
        base.py
        development.py
        production.py

media/
static/
requirements.txt

---

# Every App Must Contain

models.py

admin.py

serializers.py

views.py

urls.py

tests.py

apps.py

migrations/

No exceptions.

---

# Model Standards

Every model must include

created_at

updated_at

is_active

ordering

Meta class

__str__()

Example

created_at = models.DateTimeField(auto_now_add=True)

updated_at = models.DateTimeField(auto_now=True)

is_active = models.BooleanField(default=True)

---

# Slugs

Every public model must have

slug

Rules

- unique
- generated automatically
- editable=False

Use slugify()

Never manually type slugs.

---

# Images

Every image field

upload_to=

Example

events/

speakers/

gallery/

etc.

Always use

ImageField

Never FileField.

---

# Admin Standards

Every model must have

list_display

search_fields

list_filter

prepopulated_fields (if applicable)

ordering

readonly_fields

image preview where possible

Admin should be usable by non-developers.

---

# API Rules

Every app exposes

GET list

GET detail

POST

PUT

PATCH

DELETE

using ModelViewSet unless read-only is required.

---

# URL Pattern

/api/events/

/api/events/<slug>/

/api/speakers/

/api/blog/

/api/team/

etc.

No nested routes unless necessary.

---

# Serializer Rules

Always separate

ListSerializer

DetailSerializer

when data differs significantly.

Avoid deeply nested serializers unless required.

---

# Validation

Validation belongs inside serializers.

Never trust frontend input.

Validate

emails

links

dates

required fields

duplicate subscriptions

etc.

---

# Permissions

Public content

AllowAny

Forms

AllowAny POST

Admin

IsAuthenticated

Future authentication

JWT

---

# Pagination

Default page size

10

Maximum

100

DRF PageNumberPagination

---

# Ordering

Newest first

unless business logic says otherwise.

---

# Naming Convention

Models

PascalCase

Example

SpeakerApplication

Fields

snake_case

API

plural

/api/events/

/api/sponsors/

---

# Status Choices

Use TextChoices

Example

Draft

Published

Archived

Never use magic strings.

---

# Rich Text

Long content

TextField

Short content

CharField

---

# Foreign Keys

Always use

related_name

Never leave default names.

---

# Delete Rules

Use

PROTECT

when deleting would break data.

Use

CASCADE

only where appropriate.

---

# API Response

Consistent JSON.

Avoid unnecessary nesting.

Example

{
    "id":1,
    "title":"TEDxUMT 2026",
    "slug":"tedxumt-2026"
}

---

# Code Style

PEP8

Maximum readability.

Meaningful variable names.

Small methods.

No duplicated code.

---

# Testing

Every app must include

tests.py

Minimum

Model tests

API tests

Serializer validation tests

---

# Git Commits

Small commits.

Example

Finished Events models

Finished Events APIs

Finished Speaker admin

Connected React Events page

Never commit unfinished features.

---

# Development Order

1 Core

2 Website

3 Events

4 Speakers

5 Team

6 Gallery

7 Blog

8 Sponsors

9 Applications

10 Frontend Integration

11 Production

---

# Definition of Done

A feature is complete only when

✓ Models exist

✓ Migrations created

✓ Admin works

✓ API works

✓ Serializer validated

✓ Images upload correctly

✓ Tested

✓ Committed