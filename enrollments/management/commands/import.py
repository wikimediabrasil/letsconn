import json
from django.core.management.base import BaseCommand
from enrollments.models import Profile

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to the JSON file containing profiles data')

    def handle(self, *args, **options):
        json_file_path = options['json_file']

        with open(json_file_path, 'r', encoding='utf-8') as file:
            profiles_data = json.load(file)

        # Import data into the database
        for profile_data in profiles_data:
            Profile.objects.create(
                username=profile_data.get('username', ''),
                username_org=profile_data.get('username_org', ''),
                reconciled_affiliation=profile_data.get('reconciled_affiliation', ''),
                reconciled_territory=profile_data.get('reconciled_territory', ''),
                reconciled_languages=profile_data.get('reconciled_languages', None),
                reconciled_projects=profile_data.get('reconciled_projects', None),
                reconciled_want_to_learn=profile_data.get('reconciled_want_to_learn', None),
                reconciled_want_to_share=profile_data.get('reconciled_want_to_share', None)
            )

        print("Profiles imported successfully!")