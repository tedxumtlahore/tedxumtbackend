App 1 — Core
WebsiteSettings (Singleton)
Field	Type
site_name	CharField
tagline	CharField
site_description	TextField
contact_email	EmailField
contact_phone	CharField
address	TextField
google_maps_url	URLField
footer_text	TextField
logo	ImageField
favicon	ImageField
created_at	DateTime
updated_at	DateTime
HeroSection
Field	Type
title	CharField
subtitle	TextField
background_image	ImageField
button_text	CharField
button_url	URLField
is_active	Boolean
NavigationItem
Field	Type
title	CharField
url	CharField
order	Integer
open_new_tab	Boolean
SocialLink
Field	Type
platform	ChoiceField
url	URLField
icon	CharField
order	Integer
FAQ
Field	Type
question	CharField
answer	TextField
order	Integer
App 2 — Website
AboutSection
Field	Type
title	CharField
content	TextField
image	ImageField
CoreValue
Field	Type
title	CharField
description	TextField
icon	CharField
order	Integer
Message

This is for the President / Organizer message.

Field	Type
name	CharField
designation	CharField
photo	ImageField
message	TextField
App 3 — Events
Venue
Field	Type
name	CharField
address	TextField
city	CharField
google_maps	URLField
Event
Field	Type
title	CharField
slug	SlugField
short_description	CharField
description	TextField
featured_image	ImageField
banner_image	ImageField
venue	FK
start_datetime	DateTime
end_datetime	DateTime
registration_url	URLField
max_attendees	Integer
event_type	Choice
status	Choice
is_featured	Boolean
EventScheduleItem
Field	Type
event	FK
title	CharField
speaker	FK (nullable)
start_time	TimeField
end_time	TimeField
description	TextField
App 4 — Speakers
Speaker
Field	Type
name	CharField
slug	SlugField
designation	CharField
organization	CharField
bio	TextField
profile_image	ImageField
linkedin	URLField
instagram	URLField
website	URLField
talk_title	CharField
event	FK
featured	Boolean
App 5 — Team
Department

Marketing

Design

Operations

Finance

Media

Logistics

Partnerships

etc.

Field	Type
name	CharField
order	Integer
TeamMember
Field	Type
name	CharField
slug	SlugField
role	CharField
photo	ImageField
bio	TextField
linkedin	URLField
email	EmailField
department	FK
order	Integer
App 6 — Gallery
GalleryAlbum
Field	Type
title	CharField
slug	SlugField
cover_image	ImageField
event	FK
description	TextField
GalleryImage
Field	Type
album	FK
image	ImageField
caption	CharField
App 7 — Blog
Category
Field	Type
name	CharField
slug	SlugField
Tag
Field	Type
name	CharField
slug	SlugField
BlogPost
Field	Type
title	CharField
slug	SlugField
excerpt	CharField
content	TextField
featured_image	ImageField
author	CharField
published_date	DateField
category	FK
tags	M2M
featured	Boolean
App 8 — Sponsors
SponsorTier

Platinum

Gold

Silver

Bronze

Community

Sponsor
Field	Type
name	CharField
logo	ImageField
website	URLField
tier	FK
order	Integer
App 9 — Applications
ContactMessage
name
email
phone
subject
message
is_read
NewsletterSubscriber
email
subscribed_at
SpeakerApplication
full_name
email
phone
organization
designation
talk_title
abstract
linkedin
resume
status
VolunteerApplication
full_name
email
phone
university
semester
department_preference
motivation
cv
status
PartnerApplication
organization
contact_person
email
phone
proposal
sponsorship_interest
status
App 10 — Media Library

Instead of every model managing uploads independently, create a central media library.

MediaAsset
Field	Type
title	CharField
file	ImageField/FileField
alt_text	CharField
uploaded_by	FK(User)
uploaded_at	DateTime
tags	CharField