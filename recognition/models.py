from django.db import models
from django.contrib.auth.models import User

class PredictionHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='predictions', null=True, blank=True)
    image_name = models.CharField(max_length=255)
    class_name = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=150, blank=True)
    confidence = models.CharField(max_length=20)
    tag = models.CharField(max_length=50, default='Object')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        user_str = self.user.username if self.user else "Anonymous"
        return f"{self.class_name} ({self.confidence}) - {user_str}"

class UserPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preference')
    theme = models.CharField(max_length=20, default='light')
    auto_save_history = models.BooleanField(default=True)
    show_wikipedia_summary = models.BooleanField(default=True)

    def __str__(self):
        return f"Preferences for {self.user.username}"

