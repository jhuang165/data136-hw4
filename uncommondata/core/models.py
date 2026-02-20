from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import os

class UserProfile(models.Model):
    """
    Extended user profile to add curator/harvester distinction.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_curator = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.username} - {'Curator' if self.is_curator else 'Harvester'}"

class Upload(models.Model):
    """
    Model to store file uploads from users
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploads')
    institution = models.CharField(max_length=200)
    year = models.CharField(max_length=20)  # e.g., "2024-2025"
    url = models.URLField(max_length=500, blank=True, null=True)
    file = models.FileField(upload_to='uploads/%Y/%m/')
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.original_filename} - {self.user.username} - {self.uploaded_at}"
    
    def save(self, *args, **kwargs):
        # Store the original filename
        if self.file and not self.original_filename:
            self.original_filename = os.path.basename(self.file.name)
        super().save(*args, **kwargs)

# Signals for UserProfile
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
