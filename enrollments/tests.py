from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Badge, UserBadge


class BadgeVerificationViewTests(TestCase):
	def setUp(self):
		self.badge = Badge.objects.create(
			name="Great Sharer",
			description="Awarded for sharing resources",
			image="https://example.com/badge.png",
		)
		self.userbadge = UserBadge.objects.create(
			user="Alice",
			badge=self.badge,
			issued_at=timezone.now(),
			verification_code="abc123",
		)

	def test_verification_page_ok(self):
		url = reverse('badge_verification', kwargs={'verification_code': self.userbadge.verification_code})
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)
		self.assertContains(resp, "Alice")
		self.assertContains(resp, "Great Sharer")

	def test_verification_page_404(self):
		url = reverse('badge_verification', kwargs={'verification_code': 'does-not-exist'})
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 404)
