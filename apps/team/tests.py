from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Department, TeamMember


class TeamModelTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name='Executive Board', order=1)

    def test_department_slug_is_generated(self):
        self.assertEqual(self.department.slug, 'executive-board')

    def test_duplicate_member_names_get_unique_slugs(self):
        first = TeamMember.objects.create(name='Ayesha Hamid', role='President', department=self.department)
        second = TeamMember.objects.create(name='Ayesha Hamid', role='Advisor', department=self.department)

        self.assertEqual(first.slug, 'ayesha-hamid')
        self.assertEqual(second.slug, 'ayesha-hamid-1')

    def test_members_order_by_department_then_order(self):
        marketing = Department.objects.create(name='Marketing', order=2)
        TeamMember.objects.create(name='Zara Malik', role='Lead', department=marketing, order=1)
        TeamMember.objects.create(name='Talha Mir', role='VP', department=self.department, order=2)
        TeamMember.objects.create(name='Ali Raza', role='President', department=self.department, order=1)

        self.assertEqual(
            [m.name for m in TeamMember.objects.all()],
            ['Ali Raza', 'Talha Mir', 'Zara Malik'],
        )

    def test_str_representations(self):
        member = TeamMember.objects.create(name='Ali Raza', role='President', department=self.department)
        self.assertEqual(str(self.department), 'Executive Board')
        self.assertEqual(str(member), 'Ali Raza — President')


class TeamAPITests(APITestCase):
    def setUp(self):
        self.department = Department.objects.create(name='Executive Board', order=1)
        self.member = TeamMember.objects.create(
            name='Ayesha Hamid', role='President', department=self.department, order=1
        )
        TeamMember.objects.create(
            name='Hidden Member', role='Ghost', department=self.department, is_visible=False
        )

    def test_team_endpoint_groups_members_by_department(self):
        response = self.client.get(reverse('api-team'))

        self.assertEqual(response.status_code, 200)
        departments = response.data['departments']
        self.assertEqual(len(departments), 1)
        self.assertEqual(departments[0]['name'], 'Executive Board')
        self.assertEqual([m['name'] for m in departments[0]['members']], ['Ayesha Hamid'])

    def test_team_member_list_hides_invisible_members(self):
        response = self.client.get('/api/team-members/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual([m['name'] for m in response.data['results']], ['Ayesha Hamid'])

    def test_team_member_detail_uses_slug(self):
        response = self.client.get(f'/api/team-members/{self.member.slug}/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['department_name'], 'Executive Board')

    def test_filter_members_by_department_slug(self):
        marketing = Department.objects.create(name='Marketing', order=2)
        TeamMember.objects.create(name='Zara Malik', role='Lead', department=marketing)

        response = self.client.get('/api/team-members/?department=marketing')

        self.assertEqual(response.status_code, 200)
        self.assertEqual([m['name'] for m in response.data['results']], ['Zara Malik'])

    def test_anonymous_users_cannot_create_members(self):
        response = self.client.post('/api/team-members/', {
            'name': 'Intruder', 'role': 'Hacker', 'department': self.department.pk,
        })

        self.assertEqual(response.status_code, 403)
