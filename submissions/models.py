from django.db import models


class ContactSubmission(models.Model):
    """Stores contact-form submissions from contact.html (EN + AR).

    Fields mirror his form: name, email, phone, company (optional), message.
    """
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=60)
    company = models.CharField(max_length=200, blank=True, default="")
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} <{self.email}> ({self.created_at:%Y-%m-%d})"
