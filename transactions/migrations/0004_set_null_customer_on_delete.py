from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("transactions", "0003_alter_purchase_quantity"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sale",
            name="customer",
            field=models.ForeignKey(
                blank=True,
                db_column="customer",
                null=True,
                on_delete=models.SET_NULL,
                to="accounts.customer",
            ),
        ),
    ]
