from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
import random

from core.models import Upload


class Command(BaseCommand):
    help = 'Create test uploads for development'

    def handle(self, *args, **options):
        self.stdout.write('Creating test uploads...')

        users = []
        test_users = [
            {'username': 'testuser1', 'email': 'test1@example.com', 'is_curator': True},
            {'username': 'testuser2', 'email': 'test2@example.com', 'is_curator': False},
            {'username': 'testuser3', 'email': 'test3@example.com', 'is_curator': False},
        ]

        for user_data in test_users:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={'email': user_data['email']},
            )
            if created:
                user.set_password('testpass123')
                user.save()
            user.profile.is_curator = user_data['is_curator']
            user.profile.save()
            users.append(user)

        institutions = [
            'University of Chicago',
            'Northwestern University',
            'Illinois State University',
            'Governors State University',
            'University of Illinois',
        ]
        years = ['2023-2024', '2024-2025', '2022-2023']
        filenames = ['cds_report.txt', 'data_export.csv', 'statistics.txt', 'enrollment_data.txt']

        Upload.objects.all().delete()

        for i in range(5):
            user = random.choice(users)
            filename = random.choice(filenames)
            file_content = ContentFile(
                f'Test file content for upload {i}.\nTuition (Undergraduates) {70000+i}'.encode(),
                name=filename,
            )
            upload = Upload.objects.create(
                user=user,
                institution=random.choice(institutions),
                year=random.choice(years),
                url=f'https://example.com/upload/{i}' if random.choice([True, False]) else None,
                file=file_content,
                original_filename=filename,
            )
            self.stdout.write(f'  Created upload: {upload.original_filename} for {user.username}')

        self.stdout.write(self.style.SUCCESS(f'Successfully created {Upload.objects.count()} test uploads'))
