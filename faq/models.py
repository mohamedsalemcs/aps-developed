from django.db import models


class FAQItem(models.Model):
    """Mirrors store.js faq.items[] — {q:{en,ar}, a:{en,ar}}."""
    question_en = models.CharField(max_length=300)
    question_ar = models.CharField(max_length=300)
    answer_en = models.TextField()
    answer_ar = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.question_en
