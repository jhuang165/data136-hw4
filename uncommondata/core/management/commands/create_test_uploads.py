from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Upload, UserProfile
from django.core.files.base import ContentFile
import random
import os

class Command(BaseCommand):
    help = 'Create test uploads for development'

    def handle(self, *args, **options):
        self.stdout.write('Creating test uploads...')
        
        # Create test users if they don't exist
        users = []
        test_users = [
            {'username': 'testuser1', 'email': 'test1@example.com', 'is_curator': True},
            {'username': 'testuser2', 'email': 'test2@example.com', 'is_curator': False},
            {'username': 'testuser3', 'email': 'test3@example.com', 'is_curator': False},
        ]
        
        for user_data in test_users:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                }
            )
            if created:
                user.set_password('testpass123')
                user.save()
                # Set curator status
                user.profile.is_curator = user_data['is_curator']
                user.profile.save()
                self.stdout.write(f"  Created user: {user.username}")
            else:
                self.stdout.write(f"  User already exists: {user.username}")
            users.append(user)
        
        # Create test uploads
        institutions = [
            'University of Chicago',
            'Northwestern University',
            'Illinois State University',
            'Governors State University',
            'University of Illinois'
        ]
        
        years = ['2023-2024', '2024-2025', '2022-2023']
        filenames = ['cds_report.pdf', 'data_export.csv', 'statistics.xlsx', 'enrollment_data.pdf']
        
        # Clear existing uploads if any
        Upload.objects.all().delete()
        
        for i in range(5):
            user = random.choice(users)
            
            # Create upload without file first
            upload = Upload.objects.create(
                user=user,
                institution=random.choice(institutions),
                year=random.choice(years),
                url=f'https://example.com/upload/{i}' if random.choice([True, False]) else None,
                original_filename=random.choice(filenames)
            )
            
            # Create a dummy file content
            file_content = f'Test file content for upload {i} - This is a sample upload for testing purposes.'
            
            # Save the file
            upload.file.save(
                upload.original_filename,
                ContentFile(file_content.encode()),
                save=True
            )
            
            self.stdout.write(f"  Created upload: {upload.original_filename} for {user.username}")
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created {Upload.objects.count()} test uploads'))
