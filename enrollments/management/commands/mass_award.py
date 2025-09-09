import os
import sys
import uuid
import hashlib
from typing import List, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from enrollments.models import Badge, UserBadge, Profile


def field_exists(model, field_name: str) -> bool:
    return any(f.name == field_name for f in model._meta.get_fields())


class Command(BaseCommand):
    help = "Mass-award a badge to many usernames: paste interactively or provide a text file."

    def add_arguments(self, parser):
        parser.add_argument('--badge-id', type=int, help='ID of the badge to award')
        parser.add_argument('--file', type=str, help='Path to a text file with one username per line (optional)')
        parser.add_argument('--yes', action='store_true', help='Skip confirmation prompt')

    def handle(self, *args, **options):
        badge = self._select_badge(options.get('badge_id'))
        usernames_file = options.get('file')

        if usernames_file:
            if not os.path.isfile(usernames_file):
                raise CommandError(f"File not found: {usernames_file}")
            usernames = self._load_usernames(usernames_file)
        else:
            usernames = self._prompt_usernames_paste()

        if not usernames:
            raise CommandError("No usernames provided.")

        self.stdout.write(self.style.NOTICE(f"Badge: {badge.id} - {badge.name}"))
        self.stdout.write(self.style.NOTICE(f"Users to award: {len(usernames)} (unique)"))

        if not options.get('yes') and not self._confirm("Proceed with awarding?"):
            self.stdout.write(self.style.WARNING("Aborted."))
            return

        created, skipped, errors = self._award_many(badge, usernames)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Created: {len(created)} awards"))
        if skipped:
            self.stdout.write(self.style.WARNING(f"Skipped (already awarded): {len(skipped)}"))
        if errors:
            self.stdout.write(self.style.ERROR(f"Errors: {len(errors)}"))
            for u, err in errors:
                self.stdout.write(self.style.ERROR(f"  - {u}: {err}"))

    # --- helpers ---
    def _select_badge(self, badge_id: int | None) -> Badge:
        badges = list(Badge.objects.all().order_by('id'))
        if not badges:
            raise CommandError("No badges found. Create one first.")

        if badge_id is not None:
            try:
                return next(b for b in badges if b.id == badge_id)
            except StopIteration:
                raise CommandError(f"Badge with id {badge_id} not found.")

        # Interactive selection
        self.stdout.write("Available badges:")
        for b in badges:
            self.stdout.write(f"  [{b.id}] {b.name}")
        while True:
            raw = input("Enter badge id: ").strip()
            if not raw.isdigit():
                self.stdout.write("Please enter a numeric id.")
                continue
            bid = int(raw)
            match = next((b for b in badges if b.id == bid), None)
            if match:
                return match
            self.stdout.write("Badge not found, try again.")

    def _prompt_usernames_paste(self) -> List[str]:
        self.stdout.write("Paste usernames, one per line. Finish with an empty line. You can also paste a block.")
        seen = set()
        users: List[str] = []
        while True:
            try:
                line = input()
            except EOFError:
                break
            if line is None:
                break
            u = line.strip()
            if u == '':
                break
            if u.startswith('#'):
                continue
            if u in seen:
                continue
            seen.add(u)
            users.append(u)
        return users

    def _load_usernames(self, path: str) -> List[str]:
        seen = set()
        users: List[str] = []
        with open(path, 'r', encoding='utf-8') as fh:
            for line in fh:
                u = line.strip()
                if not u or u.startswith('#'):
                    continue
                if u in seen:
                    continue
                seen.add(u)
                users.append(u)
        return users

    def _award_many(self, badge: Badge, usernames: List[str]) -> Tuple[List[str], List[str], List[tuple]]:
        created: List[str] = []
        skipped: List[str] = []
        errors: List[tuple] = []

        has_ver_code = field_exists(UserBadge, 'verification_code')
        has_issued_at = field_exists(UserBadge, 'issued_at')

        for username in usernames:
            try:
                # Skip duplicates
                if UserBadge.objects.filter(user=username, badge=badge).exists():
                    skipped.append(username)
                    continue

                create_kwargs = {
                    'user': username,
                    'badge': badge,
                }
                if has_ver_code:
                    create_kwargs['verification_code'] = hashlib.sha256(
                        f"{badge.id}:{username}:{uuid.uuid4()}".encode()
                    ).hexdigest()[:64]

                ub = UserBadge.objects.create(**create_kwargs)
                if has_issued_at:
                    # Only set if model supports it and wasn't set automatically
                    if getattr(ub, 'issued_at', None) is None:
                        ub.issued_at = timezone.now()
                        ub.save(update_fields=['issued_at'])

                created.append(username)
            except Exception as e:
                errors.append((username, str(e)))

        return created, skipped, errors

    def _confirm(self, prompt: str) -> bool:
        ans = input(f"{prompt} [y/N]: ").strip().lower()
        return ans in ('y', 'yes')
