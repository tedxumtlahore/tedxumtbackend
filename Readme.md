# TEDxUMT Lahore CMS

## Overview

TEDxUMT Lahore CMS is the official content management system and REST API backend for the TEDxUMT Lahore website.

This project provides a scalable, production-ready backend that powers the React frontend through Django REST Framework.

The CMS allows administrators to manage website content without modifying any source code.

---

# Objectives

- Build a modular Django backend
- Provide REST APIs for the React frontend
- Allow complete website management through Django Admin
- Maintain clean architecture and professional coding standards
- Be production-ready for deployment

---

# Tech Stack

## Backend

- Python 3.13+
- Django 5+
- Django REST Framework
- Pillow
- django-environ
- django-cors-headers

## Frontend

- React
- Axios

## Database

- SQLite (Development)
- PostgreSQL (Production)

## Deployment

- Render
- PostgreSQL
- Cloudinary / Supabase Storage (Future)

---

# Project Structure

tedxumt_backend/

```
apps/
    common/
    core/
    website/
    events/
    speakers/
    team/
    gallery/
    blog/
    sponsors/
    applications/

tedxumt/
    settings/
        base.py
        development.py
        production.py

media/
static/
requirements.txt
manage.py
```

---

# Features

- Website Settings
- Dynamic Hero Section
- Dynamic Navigation
- About Page CMS
- President Message
- Events Management
- Speakers Management
- Team Management
- Gallery Management
- Sponsors Management
- Blog System
- Contact Forms
- Newsletter
- Volunteer Applications
- Speaker Applications
- Partner Applications
- REST API
- Django Admin CMS

---

# Development Workflow

Every feature follows this workflow.

1. Design
2. Models
3. Admin
4. Serializers
5. ViewSets
6. URLs
7. Validation
8. Testing
9. Documentation
10. Git Commit

---

# Documentation

This repository contains:

- README.md
- BACKEND_GUIDE.md
- DATABASE_SCHEMA.md
- API_DOCUMENTATION.md
- DEPLOYMENT.md
- TODO.md

---

# Current Status

Project is currently under active development.

The backend is being developed incrementally, app by app, following the architecture defined in BACKEND_GUIDE.md.

---

# License

This project is developed for TEDxUMT Lahore.

All TED and TEDx branding remains the property of TED.