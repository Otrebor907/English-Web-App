# Le due tabelle che appartengono all'utente prendono il prefisso user_,
# in coerenza con dim_ delle tabelle dimensione:
#   learning_user      -> user_profile
#   learning_progresso -> user_progress
#
# Sparisce anche user_progress.minuti_effettivi: la colonna veniva
# incrementata solo da un parametro "minuti" che il frontend non ha mai
# inviato, quindi conteneva 0 per ogni riga. Con lei se ne va il parametro
# minutes di record_final_score().

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("learning", "0008_dim_tabelle_e_via_prerequisiti"),
    ]

    operations = [
        migrations.RemoveField(model_name="progresso", name="minuti_effettivi"),
        migrations.AlterModelTable(name="user", table="user_profile"),
        migrations.AlterModelTable(name="progresso", table="user_progress"),
    ]
