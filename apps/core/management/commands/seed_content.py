"""
Seed the CMS with the content the prototype frontend used to hardcode.

Idempotent: every object is matched on its natural key, so running this twice
updates rather than duplicates. Safe to run against an existing database.

    python manage.py seed_content
    python manage.py seed_content --flush   # wipe seeded content first
"""

from datetime import datetime, time
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.blog.models import BlogPost, Category, Tag
from apps.common.models import StatusChoices
from apps.core.models import FAQ, HeroSection, NavigationItem, SocialLink, WebsiteSettings
from apps.events.models import Event, EventScheduleItem, Venue
from apps.gallery.models import GalleryAlbum, GalleryImage
from apps.speakers.models import Speaker
from apps.sponsors.models import Sponsor, SponsorTier
from apps.team.models import Department, TeamMember
from apps.website.models import AboutSection, CoreValue, Message

NAVIGATION = [
    ('Home', '/'), ('About', '/about'), ('Events', '/events'), ('Speakers', '/speakers'),
    ('Team', '/team'), ('Gallery', '/gallery'), ('Blog', '/blog'), ('Sponsors', '/sponsors'),
    ('Contact', '/contact'),
]

SOCIAL_LINKS = [
    ('instagram', 'https://www.instagram.com/tedxumtlahore', 'IG', 'Instagram'),
    ('linkedin', 'https://www.linkedin.com/company/tedxumtlahore/', 'in', 'LinkedIn'),
    ('facebook', 'https://www.facebook.com/tedxumtlahore', 'FB', 'Facebook'),
    ('youtube', 'https://www.youtube.com/@tedxumtlahore', 'YT', 'YouTube'),
]

FAQS = [
    ('Where is TEDxUMT Lahore held?',
     'Our flagship event is held at the UMT Auditorium on the University of Management and '
     'Technology campus in Lahore.'),
    ('How can I apply to speak?',
     'Visit the Apply page and submit the Speaker application. Our programming team reviews '
     'submissions on a rolling basis.'),
    ('Is the event open to the public?',
     'Yes — tickets are released ahead of each event and are open to students, faculty, and '
     'the general public.'),
    ('How do I become a sponsor?',
     'Head to the Sponsors page to review our packages, or reach out directly through the '
     'Contact form.'),
]

ABOUT_SECTIONS = [
    ('what_is_ted', 'What is TED?', 'Ideas worth spreading, since 1984.',
     'TED is a nonprofit devoted to spreading ideas, usually in the form of short, powerful '
     'talks of eighteen minutes or less. TED began as a conference on Technology, Entertainment '
     'and Design, and today covers almost every topic — from science to business to the big '
     'global issues facing our world.', 'right'),
    ('what_is_tedx', 'What is TEDx?', 'Independently organized. Globally connected.',
     'In the spirit of ideas worth spreading, TEDx is a program of local, self-organized events '
     'that bring people together to share a TED-like experience. At a TEDx event, TED Talks '
     'video and live speakers combine to spark deep discussion in local communities — the "x" '
     'signifies an independently organized event.', 'left'),
    ('our_story', 'Our Story', 'About TEDxUMT Lahore',
     'TEDxUMT Lahore is the University of Management and Technology\'s first officially licensed '
     'TEDx organization, founded in December 2025. Built on the spirit of Ideas Worth Spreading, '
     'we bring together innovators, creators, researchers, entrepreneurs, and changemakers to '
     'spark meaningful conversations and inspire positive impact.', 'right'),
    ('mission', 'Our Mission', 'Our Mission',
     'To create a platform where ideas are judged on their merit alone — giving a stage to '
     'voices that might otherwise go unheard, and an audience the room to think differently.',
     'right'),
    ('vision', 'Our Vision', 'Our Vision',
     'A Lahore where the exchange of bold ideas is a civic habit, not an annual event — and '
     'where a university stage can shape a city\'s conversation.', 'left'),
]

CORE_VALUES = [
    ('innovation', 'Innovation', 'We seek out the idea nobody else is saying yet.'),
    ('curiosity', 'Curiosity', 'Every talk starts with a question worth chasing.'),
    ('leadership', 'Leadership', 'We give first-time speakers the same stage as veterans.'),
    ('collaboration', 'Collaboration', 'Great ideas are built by rooms full of different people.'),
    ('creativity', 'Creativity', 'Format is a tool, not a constraint — we experiment freely.'),
    ('impact', 'Community Impact', 'An idea only matters once it leaves the room.'),
]

MESSAGES = [
    ('president', 'Ayesha Bint e Hamid', 'President & Official Organizer · TEDxUMT Lahore',
     'TEDxUMT Lahore is more than an event—it\'s a community driven by curiosity, innovation, '
     'and the belief that ideas can transform lives. We are proud to create a space where every '
     'voice has the opportunity to inspire, connect, and make a meaningful impact.'),
    ('vice_president', 'Muhammad Ahmed', 'Vice President · TEDxUMT Lahore',
     'Every year we set out to build a day that people leave differently than they arrived. '
     'That takes a team willing to sweat the details nobody in the audience will ever see.'),
]

EVENTS = [
    ('Resonance', 2026, 'upcoming', datetime(2026, 11, 14, 10, 0), datetime(2026, 11, 14, 17, 0),
     'A single day exploring the ideas that echo far beyond the room they were spoken in — '
     'from neuroscience to street art.', True),
    ('Convergence', 2025, 'past', datetime(2025, 11, 8, 10, 0), datetime(2025, 11, 8, 17, 0),
     'Where disciplines met — engineers, poets, and policymakers shared one stage to talk about '
     'collision as progress.', False),
    ('Genesis', 2024, 'past', datetime(2024, 11, 2, 10, 0), datetime(2024, 11, 2, 17, 0),
     'The first chapter — TEDxUMT Lahore\'s inaugural exploration of beginnings, origins, and '
     'first principles.', False),
]

SCHEDULE = [
    (time(9, 0), time(10, 0), 'Doors Open & Registration',
     'Check-in, badge collection, and morning coffee in the main foyer.'),
    (time(10, 0), time(10, 30), 'Opening Remarks',
     'Welcome address from the TEDxUMT Lahore organizing committee.'),
    (time(10, 30), time(13, 0), 'Session I — Signals',
     'Talks on communication, neuroscience, and the science of being heard.'),
    (time(13, 0), time(14, 30), 'Lunch & Networking',
     'A curated lunch break with structured networking activities.'),
    (time(14, 30), time(17, 0), 'Session II — Structures',
     'Talks on systems, architecture, and the invisible frameworks around us.'),
    (time(17, 0), time(18, 30), 'Closing & Reception',
     'Closing remarks followed by an evening reception in the courtyard.'),
]

SPEAKERS = [
    ('Dr. Amina Raza', 'Cognitive Neuroscientist', 'LUMS School of Science & Engineering',
     'The Architecture of Memory', 'Resonance 2026', True,
     'Dr. Amina Raza studies how the brain encodes long-term memory and what that means for how '
     'we design education and technology.'),
    ('Hamza Tariq', 'Robotics Engineer', 'NUST Robotics Lab', 'Machines That Listen',
     'Resonance 2026', True,
     'Hamza builds assistive robotics for low-resource clinics across Pakistan, focused on '
     'machines that adapt to people, not the other way around.'),
    ('Sana Idris', 'Urban Designer', 'Studio Meridian', 'Cities That Remember',
     'Resonance 2026', True,
     'Sana designs public spaces that preserve collective memory in fast-growing South Asian cities.'),
    ('Bilal Siddiqui', 'Climate Economist', 'Institute for Policy Research', 'The Cost of Silence',
     'Resonance 2026', True,
     'Bilal researches how climate risk gets systematically underpriced — and what that costs '
     'emerging economies.'),
    ('Zainab Farooq', 'Composer & Sound Artist', 'Independent Artist', 'Frequencies of Belonging',
     'Convergence 2025', False,
     'Zainab composes soundscapes from field recordings across Punjab, exploring what sound '
     'reveals about identity.'),
    ('Ibrahim Khalid', 'AI Ethicist', 'Centre for Digital Futures', 'Who Trains the Trainer?',
     'Convergence 2025', False,
     'Ibrahim works at the intersection of machine learning governance and public policy in South Asia.'),
    ('Noor Fatima', 'Physician & Author', 'Shaukat Khanum Hospital', 'The Body Keeps Time',
     'Genesis 2024', False,
     'Noor writes on the intersection of medicine and memory, drawing on a decade of clinical practice.'),
    ('Usman Ali', 'Social Entrepreneur', 'Rasta Ventures', 'Building Without Permission',
     'Genesis 2024', False,
     'Usman founded three ventures aimed at closing Pakistan\'s rural-urban opportunity gap.'),
]

DEPARTMENTS = [
    ('Executive Board', 0, [
        ('Ayesha Bint e Hamid', 'President',
         'https://www.linkedin.com/in/ayesha-bint-e-hamid-597b56381'),
        ('Muhammad Ahmed', 'Vice President',
         'https://www.linkedin.com/in/muhammad-ahmed-3aa9a83a1'),
    ]),
    ('Operations', 1, [
        ('Talha Mir', 'Operations Lead', ''),
        ('Areeba Sohail', 'Logistics Manager', ''),
    ]),
    ('Marketing', 2, [
        ('Danish Aslam', 'Marketing Lead', ''),
        ('Hania Yousaf', 'Content Strategist', ''),
    ]),
    ('Design', 3, [
        ('Zara Malik', 'Creative Director', ''),
        ('Omar Farooq', 'Brand Designer', ''),
    ]),
    ('Media', 4, [
        ('Rida Aftab', 'Media Lead', ''),
        ('Junaid Sarwar', 'Videographer', ''),
    ]),
    ('Partnerships', 5, [
        ('Laiba Zahid', 'Partnerships Lead', ''),
    ]),
]

BLOG_POSTS = [
    ('Why Good Ideas Still Need a Room to Live In', 'Reflections',
     'In an age of infinite feeds, the case for eighteen minutes, one stage, and an audience '
     'that showed up on purpose.', True, datetime(2026, 7, 12, 9, 0)),
    ('Inside the Curation of Resonance', 'Behind the Scenes',
     'How our programming team narrowed 140 speaker applications down to twelve talks.',
     False, datetime(2026, 6, 28, 9, 0)),
    ('A First-Time Speaker\'s Guide to the TEDx Stage', 'Guides',
     'What we tell every speaker in their first coaching session, distilled into five principles.',
     False, datetime(2026, 6, 14, 9, 0)),
    ('From Campus Society to Global Stage', 'Community',
     'A short history of how a student club became one of Lahore\'s most anticipated annual '
     'gatherings.', False, datetime(2026, 5, 30, 9, 0)),
]

POST_BODY = (
    'Every year, our programming committee begins with a wide net — open calls, faculty '
    'nominations, and a fair share of cold outreach to people doing work we admire from a '
    'distance. What follows is months of coaching, cutting, and rewriting, all in service of '
    'the same goal: eighteen minutes that earn their place on the stage.\n\n'
    'That process rarely feels glamorous from the inside. It is Google Docs with more comments '
    'than text, rehearsal rooms booked past midnight, and speakers rewriting their opening line '
    'for the ninth time. But it is also the only way we know to protect what makes a TEDx talk '
    'different from a keynote — the sense that an idea is still being discovered, live, in '
    'front of you.'
)

SPONSOR_TIERS = [
    ('Title', 0, 'Our headline partner for the year.',
     'Naming rights\nKeynote introduction\nUnlimited event passes\nYear-round partnership',
     ['Meridian Bank']),
    ('Gold', 1, 'Major partners with on-stage presence.',
     'Stage mention\nBooth space\n10 event passes\nNewsletter feature',
     ['Northline Tech', 'Aurora Foods']),
    ('Silver', 2, 'Supporting partners.',
     'Logo placement\n4 event passes\nSocial media mention',
     ['Bramble Coffee', 'Vantage Media', 'Codeworks']),
]

# Photos shipped with the prototype frontend, reused to populate the gallery.
MEDIA_SOURCE_CAPTIONS = {
    'OathTEDX.jpeg': ('The TEDxUMT Lahore organizing oath', 'photo'),
    'TEDx.jpg': ('On the TEDx stage', 'photo'),
    'UMT Campus.jpg': ('UMT campus, Johar Town', 'bts'),
    'UMT Campus 2.jpeg': ('Arriving at the venue', 'bts'),
    'PresidentTEDX.png': ('Opening remarks from the President', 'photo'),
    'VicePresidentTEDX.png': ('Behind the scenes with the Vice President', 'bts'),
}

SEEDED_MODELS = [
    EventScheduleItem, Speaker, GalleryImage, GalleryAlbum, Event, Venue,
    TeamMember, Department, BlogPost, Tag, Category,
    Sponsor, SponsorTier, Message, CoreValue, AboutSection,
    FAQ, SocialLink, NavigationItem, HeroSection, WebsiteSettings,
]


def aware(value):
    return timezone.make_aware(value) if timezone.is_naive(value) else value


class Command(BaseCommand):
    help = 'Populate the CMS with the launch content set (idempotent).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Delete existing content before seeding. Does not touch users or submissions.',
        )
        parser.add_argument(
            '--media-dir',
            default=None,
            help=(
                'Directory of photos to import into the gallery. '
                'Defaults to the prototype frontend images folder if it exists.'
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['flush']:
            for model in SEEDED_MODELS:
                model.objects.all().delete()
            self.stdout.write(self.style.WARNING('Existing content flushed.'))

        self.seed_core()
        self.seed_website()
        events = self.seed_events()
        self.seed_speakers(events)
        self.seed_team()
        self.seed_gallery(events, options.get('media_dir'))
        self.seed_blog()
        self.seed_sponsors()

        self.stdout.write(self.style.SUCCESS('\nContent seeded successfully.'))
        self.stdout.write(f'  Events:       {Event.objects.count()}')
        self.stdout.write(f'  Speakers:     {Speaker.objects.count()}')
        self.stdout.write(f'  Team members: {TeamMember.objects.count()}')
        self.stdout.write(f'  Blog posts:   {BlogPost.objects.count()}')
        self.stdout.write(f'  Sponsors:     {Sponsor.objects.count()}')
        self.stdout.write(f'  Gallery:      {GalleryImage.objects.count()} images')
        self.stdout.write(f'  FAQs:         {FAQ.objects.count()}')

    def seed_core(self):
        WebsiteSettings.load()
        HeroSection.load()

        for index, (label, url) in enumerate(NAVIGATION):
            NavigationItem.objects.update_or_create(
                label=label, defaults={'url': url, 'order': index, 'is_visible': True}
            )

        for index, (platform, url, label, aria) in enumerate(SOCIAL_LINKS):
            SocialLink.objects.update_or_create(
                platform=platform,
                defaults={'url': url, 'display_label': label, 'aria_label': aria, 'order': index},
            )

        for index, (question, answer) in enumerate(FAQS):
            FAQ.objects.update_or_create(
                question=question, defaults={'answer': answer, 'order': index}
            )
        self.stdout.write('  core ............ ok')

    def seed_website(self):
        for index, (key, eyebrow, heading, body, position) in enumerate(ABOUT_SECTIONS):
            AboutSection.objects.update_or_create(
                section_key=key,
                defaults={
                    'eyebrow': eyebrow, 'heading': heading, 'body': body,
                    'image_position': position, 'order': index,
                },
            )

        for index, (icon, title, description) in enumerate(CORE_VALUES):
            CoreValue.objects.update_or_create(
                title=title, defaults={'icon_key': icon, 'description': description, 'order': index}
            )

        for index, (kind, name, role, body) in enumerate(MESSAGES):
            Message.objects.update_or_create(
                message_type=kind,
                defaults={
                    'person_name': name, 'role_title': role,
                    'message_body': body, 'order': index,
                },
            )
        self.stdout.write('  website ......... ok')

    def seed_events(self):
        venue, _ = Venue.objects.update_or_create(
            name='UMT Auditorium',
            defaults={
                'address': 'University of Management and Technology, C-II, Johar Town',
                'city': 'Lahore',
                'google_maps': 'https://maps.google.com/?q=University+of+Management+and+Technology+Lahore',
            },
        )

        events = {}
        for theme, year, status, start, end, description, featured in EVENTS:
            title = f'{theme} {year}'
            event, _ = Event.objects.update_or_create(
                slug=f'{theme.lower()}-{year}',
                defaults={
                    'title': title,
                    'short_description': description[:300],
                    'description': description,
                    'venue': venue,
                    'start_datetime': aware(start),
                    'end_datetime': aware(end),
                    'event_type': Event.EventTypeChoices.FLAGSHIP,
                    'status': status,
                    'is_featured': featured,
                    'registration_url': 'https://www.ted.com/tedx/events/69864',
                    'max_attendees': 500,
                },
            )
            events[title] = event

        flagship = events['Resonance 2026']
        for start, end, title, description in SCHEDULE:
            EventScheduleItem.objects.update_or_create(
                event=flagship, title=title,
                defaults={'start_time': start, 'end_time': end, 'description': description},
            )
        self.stdout.write('  events .......... ok')
        return events

    def seed_speakers(self, events):
        for name, designation, org, talk, event_title, featured, bio in SPEAKERS:
            Speaker.objects.update_or_create(
                name=name,
                defaults={
                    'designation': designation, 'organization': org, 'bio': bio,
                    'talk_title': talk, 'featured': featured, 'event': events[event_title],
                },
            )
        self.stdout.write('  speakers ........ ok')

    def seed_team(self):
        for name, order, members in DEPARTMENTS:
            department, _ = Department.objects.update_or_create(name=name, defaults={'order': order})
            for index, (member_name, role, linkedin) in enumerate(members):
                TeamMember.objects.update_or_create(
                    name=member_name,
                    defaults={
                        'role': role, 'department': department,
                        'linkedin': linkedin, 'order': index,
                    },
                )
        self.stdout.write('  team ............ ok')

    def seed_gallery(self, events, media_dir=None):
        albums = {}
        for title, event in events.items():
            album, _ = GalleryAlbum.objects.update_or_create(
                title=title,
                defaults={
                    'event': event,
                    'description': f'Photos and video from {title}.',
                    'order': 0,
                },
            )
            albums[title] = album

        imported = self.import_gallery_media(albums.get('Resonance 2026'), media_dir)
        suffix = f'{imported} image(s) imported' if imported else 'albums only — upload images in the admin'
        self.stdout.write(f'  gallery ......... ok ({suffix})')

    def import_gallery_media(self, album, media_dir):
        """Copy source photos into MEDIA_ROOT as gallery items, skipping duplicates."""
        if album is None:
            return 0

        source = Path(media_dir) if media_dir else settings.BASE_DIR.parent / 'frontend' / 'src' / 'images'
        if not source.is_dir():
            return 0

        imported = 0
        for order, (filename, (caption, media_type)) in enumerate(MEDIA_SOURCE_CAPTIONS.items()):
            path = source / filename
            if not path.is_file():
                continue
            if GalleryImage.objects.filter(album=album, caption=caption).exists():
                continue

            image = GalleryImage(
                album=album, caption=caption, alt_text=caption,
                media_type=media_type, order=order,
            )
            with path.open('rb') as handle:
                image.image.save(filename.replace(' ', '-'), File(handle), save=True)
            imported += 1

        return imported

    def seed_blog(self):
        tag, _ = Tag.objects.get_or_create(name='TEDxUMT')

        for index, (title, category_name, excerpt, featured, published) in enumerate(BLOG_POSTS):
            category, _ = Category.objects.get_or_create(
                name=category_name, defaults={'order': index}
            )
            post, _ = BlogPost.objects.update_or_create(
                title=title,
                defaults={
                    'excerpt': excerpt,
                    'content': POST_BODY,
                    'category': category,
                    'status': StatusChoices.PUBLISHED,
                    'published_at': aware(published),
                    'is_featured': featured,
                },
            )
            post.tags.add(tag)
        self.stdout.write('  blog ............ ok')

    def seed_sponsors(self):
        for name, order, description, benefits, sponsors in SPONSOR_TIERS:
            tier, _ = SponsorTier.objects.update_or_create(
                name=name,
                defaults={'order': order, 'description': description, 'benefits': benefits},
            )
            for index, sponsor_name in enumerate(sponsors):
                Sponsor.objects.update_or_create(
                    name=sponsor_name, defaults={'tier': tier, 'order': index}
                )
        self.stdout.write('  sponsors ........ ok')
