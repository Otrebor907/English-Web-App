"""Refactoring coordinato dello schema.

1. Tassonomie -> tabelle `mapping_*`
2. Rimozione di `Lezione.priorita`
3. Rimozione del modello `Importanza` e della FK `Lezione.importanza_mvp`
4. `SezioneLezione` -> `StrutturaLezione` (tabella `struttura_lezione`)
5. `Quiz` -> `StrutturaQuiz` (tabella `struttura_quiz`)
6. `Quesito` -> `QuesitoGuidato` / `QuesitoFinale`
   (tabelle `struttura_quiz_guidato` / `struttura_quiz_finale`)

`Prerequisito` NON viene eliminata: la regola di derivazione dall'ID copre
solo 64 delle 96 lezioni con prerequisiti e non rappresenta ne' i 22 casi a
prerequisito multiplo ne' i 18 archi fra aree diverse. Al suo posto e' stata
aggiunta la property `Lezione.prerequisito_derivato`, che non tocca lo schema.
"""

from django.db import migrations, models
import django.db.models.deletion


def sposta_quesiti(apps, schema_editor):
    """Ripartisce i quesiti esistenti nelle due tabelle in base alla modalita' del quiz."""
    Quesito = apps.get_model("learning", "Quesito")
    Guidato = apps.get_model("learning", "QuesitoGuidato")
    Finale = apps.get_model("learning", "QuesitoFinale")
    campi = ("quiz_id", "ordine", "tipo", "testo", "opzioni", "risposta_corretta", "spiegazione")
    for quesito in Quesito.objects.select_related("quiz").all():
        destinazione = Guidato if quesito.quiz.modalita == "guidato" else Finale
        destinazione.objects.create(**{campo: getattr(quesito, campo) for campo in campi})


def ripristina_quesiti(apps, schema_editor):
    Quesito = apps.get_model("learning", "Quesito")
    campi = ("quiz_id", "ordine", "tipo", "testo", "opzioni", "risposta_corretta", "spiegazione")
    for nome in ("QuesitoGuidato", "QuesitoFinale"):
        for quesito in apps.get_model("learning", nome).objects.all():
            Quesito.objects.create(**{campo: getattr(quesito, campo) for campo in campi})


class Migration(migrations.Migration):

    dependencies = [("learning", "0005_alter_user_first_name_alter_user_last_name")]

    operations = [
        # --- 1. Tassonomie -> mapping_* -------------------------------------
        migrations.AlterModelTable(name="area", table="mapping_area_lezione"),
        migrations.AlterModelTable(name="tipologia", table="mapping_tipologia"),
        migrations.AlterModelTable(name="livello", table="mapping_livello"),
        migrations.AlterModelTable(name="difficolta", table="mapping_difficolta_lezione"),

        # --- 2/3. priorita e importanza --------------------------------------
        # La FK va rimossa prima del modello a cui punta.
        migrations.RemoveField(model_name="lezione", name="priorita"),
        migrations.RemoveField(model_name="lezione", name="importanza_mvp"),
        migrations.DeleteModel(name="Importanza"),

        # --- 4/5. Rinomina delle strutture -----------------------------------
        migrations.RenameModel(old_name="SezioneLezione", new_name="StrutturaLezione"),
        migrations.AlterModelTable(name="strutturalezione", table="struttura_lezione"),
        migrations.RenameModel(old_name="Quiz", new_name="StrutturaQuiz"),
        migrations.AlterModelTable(name="strutturaquiz", table="struttura_quiz"),

        # --- 6. Separazione dei quesiti --------------------------------------
        migrations.CreateModel(
            name="QuesitoGuidato",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ordine", models.PositiveSmallIntegerField()),
                ("tipo", models.CharField(choices=[("scelta_multipla", "Scelta multipla"), ("completamento", "Completamento")], max_length=20)),
                ("testo", models.TextField()),
                ("opzioni", models.JSONField(blank=True, default=list)),
                ("risposta_corretta", models.CharField(max_length=300)),
                ("spiegazione", models.TextField()),
                ("quiz", models.ForeignKey(
                    limit_choices_to={"modalita": "guidato"},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="quesiti_guidati", to="learning.strutturaquiz",
                )),
            ],
            options={"db_table": "struttura_quiz_guidato", "ordering": ["ordine"], "abstract": False},
        ),
        migrations.CreateModel(
            name="QuesitoFinale",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ordine", models.PositiveSmallIntegerField()),
                ("tipo", models.CharField(choices=[("scelta_multipla", "Scelta multipla"), ("completamento", "Completamento")], max_length=20)),
                ("testo", models.TextField()),
                ("opzioni", models.JSONField(blank=True, default=list)),
                ("risposta_corretta", models.CharField(max_length=300)),
                ("spiegazione", models.TextField()),
                ("quiz", models.ForeignKey(
                    limit_choices_to={"modalita": "finale"},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="quesiti_finali", to="learning.strutturaquiz",
                )),
            ],
            options={"db_table": "struttura_quiz_finale", "ordering": ["ordine"], "abstract": False},
        ),
        migrations.AddConstraint(
            model_name="quesitoguidato",
            constraint=models.UniqueConstraint(fields=("quiz", "ordine"), name="ordine_quesito_guidato_unico"),
        ),
        migrations.AddConstraint(
            model_name="quesitofinale",
            constraint=models.UniqueConstraint(fields=("quiz", "ordine"), name="ordine_quesito_finale_unico"),
        ),
        # I dati si spostano prima che la vecchia tabella sparisca.
        migrations.RunPython(sposta_quesiti, ripristina_quesiti),
        migrations.DeleteModel(name="Quesito"),
    ]
