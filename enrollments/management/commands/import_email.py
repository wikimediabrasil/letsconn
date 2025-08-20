import csv
from django.core.management.base import BaseCommand
from enrollments.models import Profile

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file containing user email data')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']

        with open(csv_file_path, 'r', encoding='utf-8') as file:
            profiles_data = csv.DictReader(file)

            # Import data into the database
            for profile_data in profiles_data:
                username = profile_data.get('username')
                email = profile_data.get('email')
                full_name = profile_data.get('name')

                if username:
                    profile = Profile.objects.filter(username=username).first()
                    if profile:
                        profile.email = email
                        profile.full_name = full_name
                        profile.save()
                        self.stdout.write(self.style.SUCCESS(f"Updated profile for {username}"))
                    else:
                        self.stdout.write(self.style.WARNING(f"Profile for {username} not found"))
