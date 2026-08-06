from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Sponsor, SponsorTier


class SponsorModelTests(TestCase):
    def setUp(self):
        self.tier = SponsorTier.objects.create(
            name='Title', order=0, benefits='Naming rights\n  Keynote intro  \n\nUnlimited passes\n'
        )

    def test_benefit_list_splits_and_strips_lines(self):
        self.assertEqual(
            self.tier.benefit_list,
            ['Naming rights', 'Keynote intro', 'Unlimited passes'],
        )

    def test_benefit_list_is_empty_when_unset(self):
        tier = SponsorTier.objects.create(name='Bronze', order=9)
        self.assertEqual(tier.benefit_list, [])

    def test_sponsor_str_includes_tier(self):
        sponsor = Sponsor.objects.create(name='Meridian Bank', tier=self.tier)
        self.assertEqual(str(sponsor), 'Meridian Bank (Title)')

    def test_sponsors_order_by_tier_rank_first(self):
        gold = SponsorTier.objects.create(name='Gold', order=1)
        Sponsor.objects.create(name='Northline Tech', tier=gold, order=0)
        Sponsor.objects.create(name='Meridian Bank', tier=self.tier, order=5)

        self.assertEqual(
            [s.name for s in Sponsor.objects.all()],
            ['Meridian Bank', 'Northline Tech'],
        )


class SponsorAPITests(APITestCase):
    def setUp(self):
        self.title = SponsorTier.objects.create(name='Title', order=0, benefits='Naming rights')
        self.gold = SponsorTier.objects.create(name='Gold', order=1)
        Sponsor.objects.create(name='Meridian Bank', tier=self.title)
        Sponsor.objects.create(name='Northline Tech', tier=self.gold)
        Sponsor.objects.create(name='Hidden Corp', tier=self.gold, is_visible=False)

    def test_sponsors_endpoint_groups_by_tier_in_rank_order(self):
        response = self.client.get(reverse('api-sponsors'))

        self.assertEqual(response.status_code, 200)
        tiers = response.data['tiers']
        self.assertEqual([t['name'] for t in tiers], ['Title', 'Gold'])
        self.assertEqual([s['name'] for s in tiers[0]['sponsors']], ['Meridian Bank'])

    def test_hidden_sponsors_are_excluded(self):
        response = self.client.get(reverse('api-sponsors'))

        gold = response.data['tiers'][1]
        self.assertEqual([s['name'] for s in gold['sponsors']], ['Northline Tech'])

    def test_tier_payload_exposes_parsed_benefits(self):
        response = self.client.get(reverse('api-sponsors'))

        self.assertEqual(response.data['tiers'][0]['benefit_list'], ['Naming rights'])

    def test_filter_sponsors_by_tier_slug(self):
        response = self.client.get('/api/sponsor-list/', {'tier': 'gold'})

        self.assertEqual([s['name'] for s in response.data['results']], ['Northline Tech'])

    def test_anonymous_users_cannot_create_sponsors(self):
        response = self.client.post('/api/sponsor-list/', {'name': 'Spam Inc', 'tier': self.gold.pk})

        self.assertEqual(response.status_code, 403)
