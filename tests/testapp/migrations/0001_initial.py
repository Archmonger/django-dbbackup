from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="CharModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("field", models.CharField(max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name="FileModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("field", models.FileField(upload_to=".")),
            ],
        ),
        migrations.CreateModel(
            name="ForeignKeyModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "field",
                    models.ForeignKey(to="testapp.CharModel", on_delete=models.CASCADE),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ManyToManyModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("field", models.ManyToManyField(to="testapp.CharModel")),
            ],
        ),
    ]
