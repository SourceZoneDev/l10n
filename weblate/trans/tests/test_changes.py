# Copyright © Michal Čihař <michal@weblate.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for changes browsing."""

from datetime import timedelta
from html import escape

from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode

from weblate.trans.models import Unit
from weblate.trans.tests.test_views import ViewTestCase


class ChangesTest(ViewTestCase):
    def test_basic(self) -> None:
        response = self.client.get(reverse("changes"))
        self.assertContains(response, "Resource update")

    def test_basic_csv_denied(self) -> None:
        response = self.client.get(reverse("changes-csv"))
        self.assertEqual(response.status_code, 403)

    def test_basic_csv(self) -> None:
        self.user.is_superuser = True
        self.user.save()
        response = self.client.get(reverse("changes-csv"))
        self.assertContains(response, "timestamp,")

    def test_filter(self) -> None:
        response = self.client.get(reverse("changes", kwargs={"path": ["test"]}))
        self.assertContains(response, "Resource update")
        response = self.client.get(
            reverse("changes", kwargs={"path": ["test", "test"]})
        )
        self.assertContains(response, "Resource update")
        response = self.client.get(
            reverse("changes", kwargs={"path": ["test", "test", "cs"]})
        )
        self.assertContains(response, "Resource update")
        response = self.client.get(
            reverse("changes", kwargs={"path": ["-", "-", "cs"]})
        )
        self.assertContains(response, "Resource update")
        response = self.client.get(
            reverse("changes", kwargs={"path": ["testx", "test", "cs"]})
        )
        self.assertEqual(response.status_code, 404)

    def test_string(self) -> None:
        response = self.client.get(
            reverse("changes", kwargs={"path": Unit.objects.all()[0].get_url_path()})
        )
        self.assertContains(response, "Source string added")
        self.assertContains(response, "Changes of string in")

    def test_user(self) -> None:
        self.edit_unit("Hello, world!\n", "Nazdar svete!\n")
        response = self.client.get(reverse("changes"), {"user": self.user.username})
        self.assertContains(response, f'title="{self.user.full_name}"')
        # Filtering by another user should not show the change made by
        # the current test user.
        response = self.client.get(
            reverse("changes"), {"user": self.anotheruser.username}
        )
        self.assertNotContains(response, f'title="{self.user.full_name}"')

    def test_exclude_user(self) -> None:
        self.edit_unit("Hello, world!\n", "Nazdar svete!\n")
        response = self.client.get(reverse("changes"))
        self.assertContains(response, f'title="{self.user.full_name}"')
        # Filtering by current user should not show the change made by
        # the current test user.
        response = self.client.get(
            reverse("changes"), {"exclude_user": self.user.username}
        )
        self.assertNotContains(response, f'title="{self.user.full_name}"')
        # Filtering by another user should show the change made by
        # the current test user.
        response = self.client.get(
            reverse("changes"), {"exclude_user": self.anotheruser.username}
        )
        self.assertContains(response, f'title="{self.user.full_name}"')

    def test_daterange(self) -> None:
        end = timezone.now()
        start = end - timedelta(days=1)
        period = "{} - {}".format(start.strftime("%m/%d/%Y"), end.strftime("%m/%d/%Y"))
        response = self.client.get(reverse("changes"), {"period": period})
        self.assertContains(response, "Resource update")

    def test_pagination(self) -> None:
        end = timezone.now()
        start = end - timedelta(days=1)
        period = "{} - {}".format(start.strftime("%m/%d/%Y"), end.strftime("%m/%d/%Y"))
        response = self.client.get(reverse("changes"), {"period": period})
        query_string = urlencode({"page": 2, "limit": 20, "period": period})
        self.assertContains(response, escape(query_string))
        response = self.client.get(
            reverse("changes"), {"page": 2, "limit": 20, "period": period}
        )
        self.assertContains(response, "String added in the upload")

    def test_last_changes_display(self):
        unit_to_delete = self.get_unit("Orangutan has %d banana")
        self.translation.delete_unit(None, unit_to_delete)
        response = self.client.get(reverse("changes"))
        self.assertContains(
            response, "String removed", count=2
        )  # one is from search options, second from history-data
