# User non eredita piu' da AbstractUser ma da AbstractBaseUser: sparisce
# PermissionsMixin e con lui i permessi granulari di Django, che questo progetto
# non ha mai usato (l'unica distinzione e' is_staff / is_superuser).
#
# A livello di DB questa migrazione elimina:
#   - la tabella ponte learning_user_groups            (M2M User <-> auth_group)
#   - la tabella ponte learning_user_user_permissions  (M2M User <-> auth_permission)
#   - la colonna learning_user.date_joined, doppione di creato_il

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("learning", "0006_refactor_mapping_struttura_quiz"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="user",
            options={},
        ),
        migrations.RemoveField(
            model_name="user",
            name="groups",
        ),
        migrations.RemoveField(
            model_name="user",
            name="user_permissions",
        ),
        migrations.RemoveField(
            model_name="user",
            name="date_joined",
        ),
        # I tre booleani restano identici come colonna: cambia solo la loro
        # definizione (prima arrivava da AbstractUser/PermissionsMixin, ora e'
        # dichiarata in models.py). Nessun ALTER reale sul DB.
        migrations.AlterField(
            model_name="user",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name="user",
            name="is_staff",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="user",
            name="is_superuser",
            field=models.BooleanField(default=False),
        ),
    ]
