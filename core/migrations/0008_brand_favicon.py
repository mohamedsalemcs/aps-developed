# Generated for the favicon upload feature (CMS Brand & theme screen).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_brand_cms_theme'),
    ]

    operations = [
        migrations.AddField(
            model_name='brand',
            name='favicon',
            field=models.CharField(blank=True, default='', max_length=300),
        ),
    ]
