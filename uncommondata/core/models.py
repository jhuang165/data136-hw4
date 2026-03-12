import hashlib
import os

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    is_curator = models.BooleanField(default=False)

    def __str__(self):
        role = "Curator" if self.is_curator else "Harvester"
        return f"{self.user.username} - {role}"


class Upload(models.Model):
    id = models.CharField(max_length=64, primary_key=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="uploads")
    institution = models.CharField(max_length=200)
    year = models.CharField(max_length=20)
    url = models.URLField(max_length=500, blank=True, null=True)
    file = models.FileField(upload_to="uploads/%Y/%m/")
    original_filename = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.original_filename} - {self.user.username}"

    @staticmethod
    def hash_uploaded_file(uploaded_file) -> str:
        digest = hashlib.sha256()

        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)

        if hasattr(uploaded_file, "chunks"):
            for chunk in uploaded_file.chunks():
                digest.update(chunk)
        else:
            digest.update(uploaded_file.read())

        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)

        return digest.hexdigest()

    def save(self, *args, **kwargs):
        has_named_file = getattr(self, "file", None) is not None and bool(getattr(self.file, "name", ""))

        if has_named_file and not self.original_filename:
            self.original_filename = os.path.basename(self.file.name)

        if has_named_file and not self.id:
            self.id = self.hash_uploaded_file(self.file)

        super().save(*args, **kwargs)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
