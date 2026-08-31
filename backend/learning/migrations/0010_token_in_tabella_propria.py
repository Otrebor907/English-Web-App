# Il token di sessione dell'API passa da authtoken_token (tabella di
# rest_framework.authtoken) a user_authtoken_token, modello learning.Token.
#
# La migrazione crea la tabella nuova e poi, SE trova la vecchia, ci travasa
# dentro le righe e la elimina. Il "se" serve perche' i due casi divergono:
#   - database gia' esistente (Neon): authtoken_token c'e', i token vengono
#     spostati e restano validi, nessuno viene disconnesso;
#   - database creato da zero (i test, una nuova installazione): l'app
#     rest_framework.authtoken non e' piu' installata, quindi authtoken_token
#     non e' mai stata creata e non c'e' niente da travasare.

from django.db import migrations, models
import django.db.models.deletion


def travasa_token(apps, schema_editor):
    connection = schema_editor.connection
    if "authtoken_token" not in connection.introspection.table_names():
        return
    with connection.cursor() as cursor:
        cursor.execute(
            'INSERT INTO "user_authtoken_token" ("key", "created", "user_id") '
            'SELECT "key", "created", "user_id" FROM "authtoken_token"'
        )
        cursor.execute('DROP TABLE "authtoken_token"')
        # L'app non e' piu' in INSTALLED_APPS: le sue righe qui sono relitti.
        cursor.execute("DELETE FROM django_migrations WHERE app = 'authtoken'")


class Migration(migrations.Migration):

    dependencies = [
        ("learning", "0009_tabelle_utente_e_via_minuti"),
    ]

    operations = [
        migrations.CreateModel(
            name="Token",
            fields=[
                (
                    "key",
                    models.CharField(
                        max_length=40,
                        primary_key=True,
                        serialize=False,
                        verbose_name="Key",
                    ),
                ),
                (
                    "created",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created"),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="auth_token",
                        to="learning.user",
                        verbose_name="User",
                    ),
                ),
            ],
            options={
                "db_table": "user_authtoken_token",
            },
        ),
        migrations.RunPython(travasa_token, migrations.RunPython.noop),
    ]
