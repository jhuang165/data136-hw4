import hashlib
import os

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_curator = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {'Curator' if self.is_curator else 'Harvester'}"


class Upload(models.Model):
    upload_id = models.CharField(max_length=64, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploads')
    institution = models.CharField(max_length=200)
    year = models.CharField(max_length=20)
    url = models.URLField(max_length=500, blank=True, null=True)
    file = models.FileField(upload_to='uploads/%Y/%m/')
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.original_filename} - {self.user.username} - {self.uploaded_at}"

    @staticmethod
    def hash_uploaded_file(uploaded_file) -> str:
        digest = hashlib.sha256()
        for chunk in uploaded_file.chunks():
            digest.update(chunk)
        uploaded_file.seek(0)
        return digest.hexdigest()

    def save(self, *args, **kwargs):
        if self.file and not self.original_filename:
            self.original_filename = os.path.basename(self.file.name)

        if self.file and not self.upload_id:
            self.upload_id = self.hash_uploaded_file(self.file)

        super().save(*args, **kwargs)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
