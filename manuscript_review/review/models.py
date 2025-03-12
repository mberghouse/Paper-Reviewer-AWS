from django.db import models
from django.conf import settings
import os
import sys

def manuscript_file_path(instance, filename):
    """Generate a unique path for each manuscript file"""
    print(f"GENERATING PATH FOR: {filename}", file=sys.stderr)
    ext = filename.split('.')[-1]
    filename = f"{instance.id or 'new'}_{filename}"
    path = os.path.join('manuscripts', filename)
    print(f"PATH GENERATED: {path}", file=sys.stderr)
    return path

class Manuscript(models.Model):
    file = models.CharField(max_length=500)  # Store the S3 path directly
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Manuscript {self.id} uploaded at {self.uploaded_at}"

    @property
    def file_url(self):
        if self.file:
            return f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{self.file}"
        return None

    def save(self, *args, **kwargs):
        print(f"SAVING MANUSCRIPT: {self.id or 'new'}", file=sys.stderr)
        if not self.id:
            super().save(*args, **kwargs)
            print(f"SAVED NEW MANUSCRIPT: {self.id}", file=sys.stderr)
            # If this is a new instance, save again to get the correct file path with the ID
            if self.file:
                old_name = self.file.name
                print(f"UPDATING FILE PATH from {old_name}", file=sys.stderr)
                self.file.name = manuscript_file_path(self, old_name.split('/')[-1])
                print(f"NEW FILE PATH: {self.file.name}", file=sys.stderr)
                super().save(*args, **kwargs)
        else:
            print(f"UPDATING EXISTING MANUSCRIPT: {self.id}", file=sys.stderr)
            super().save(*args, **kwargs)
