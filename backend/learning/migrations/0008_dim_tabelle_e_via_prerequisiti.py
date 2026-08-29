# Tre cose insieme, tutte di semplificazione dello schema:
#
# 1. Le cinque tabelle codice-etichetta prendono il prefisso dim_ (dimensione).
#    Minuscolo perche' Postgres abbassa gli identificatori non virgolettati:
#    "SELECT * FROM dim_livello" funziona, "DIM_livello" avrebbe richiesto
#    le virgolette per sempre.
# 2. learning_lezione.fase_roadmap sparisce: aveva solo due valori
#    ("Fase 1 - MVP" / "TODO_FONTE") ed erano gia' deducibili da stato_id
#    e da ordine_mvp. Informazione tripla, tenuta in un punto solo.
# 3. Via il grafo dei prerequisiti: la tabella learning_prerequisito e la M2M
#    Lezione<->Lezione che le stava sopra. Le lezioni non sono mai state
#    bloccate dai prerequisiti (erano un consiglio); l'ordine di percorrenza
#    resta in ordine_mvp / ordine_percorso.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("learning", "0007_rimuove_permessi_granulari_user"),
    ]

    operations = [
        # 1 — tabelle dimensione
        migrations.AlterModelTable(name="area", table="dim_area_lezione"),
        migrations.AlterModelTable(name="tipologia", table="dim_tipologia"),
        migrations.AlterModelTable(name="livello", table="dim_livello"),
        migrations.AlterModelTable(name="difficolta", table="dim_difficolta_lezione"),
        migrations.AlterModelTable(name="statolezione", table="dim_stato_lezione"),
        # 2 — colonna ridondante
        migrations.RemoveField(model_name="lezione", name="fase_roadmap"),
        # 3 — prerequisiti: prima la M2M, poi la tabella ponte che la reggeva
        migrations.RemoveField(model_name="lezione", name="prerequisiti"),
        migrations.DeleteModel(name="Prerequisito"),
    ]
