from django.db import migrations, models

import restaurant.models


def backfill_confirmation_codes(apps, schema_editor):
    """Give each existing reservation its own code.

    A plain AddField would call the default once and give every existing row
    the same code, which the unique constraint (added below) would reject.
    """
    Reservation = apps.get_model("restaurant", "Reservation")
    used = set()
    for reservation in Reservation.objects.all():
        code = restaurant.models.generate_confirmation_code()
        while code in used:
            code = restaurant.models.generate_confirmation_code()
        used.add(code)
        reservation.confirmation_code = code
        reservation.save(update_fields=["confirmation_code"])


class Migration(migrations.Migration):

    dependencies = [
        ("restaurant", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="reservation",
            name="contact_email",
            field=models.EmailField(blank=True, default="", max_length=254),
        ),
        migrations.AddField(
            model_name="reservation",
            name="confirmation_code",
            field=models.CharField(editable=False, max_length=6, null=True),
        ),
        migrations.RunPython(backfill_confirmation_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="reservation",
            name="confirmation_code",
            field=models.CharField(
                default=restaurant.models.generate_confirmation_code,
                editable=False,
                max_length=6,
                unique=True,
            ),
        ),
    ]
