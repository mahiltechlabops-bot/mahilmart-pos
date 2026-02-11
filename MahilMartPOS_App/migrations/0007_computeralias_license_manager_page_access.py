from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("MahilMartPOS_App", "0006_cashierpermission_allow_license_manager_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="computeralias",
            name="license_manager_page_access",
            field=models.BooleanField(blank=True, default=None, null=True),
        ),
    ]
