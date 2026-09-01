"""Import del workbook con rete di sicurezza, seguito dalla ripubblicazione dei brief.

Esiste per un motivo preciso: `importa_contenuti` cancella TUTTE le sezioni e
TUTTI i quiz del database e riporta ogni lezione allo stato scritto nel
workbook. Da solo, quindi, spubblica il lavoro editoriale gia' fatto. La
riparazione e' ripubblicare i brief markdown, e finora andava ricordata a mano.

In piu', il piano Free di Neon conserva la cronologia solo 6 ore: un import
sbagliato scoperto il giorno dopo non e' piu' recuperabile con l'instant
restore. Un branch, invece, resta finche' non lo si cancella.

Questo comando mette le tre cose in fila:
    1. crea un branch di backup su Neon (rete di sicurezza duratura)
    2. importa il workbook
    3. ripubblica tutti i brief marcati come testo definitivo verificato
"""
import re
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from learning import neon
from learning.markdown_source import publish_markdown_lesson

# Nome dei branch generati da questo comando. Lo schema e' rigido di proposito:
# la potatura cancella SOLO cio' che combacia, cosi' un branch creato a mano
# (per esempio "pre-refactor-0006-backup") non puo' finirci dentro per sbaglio.
SCHEMA_NOME_BACKUP = re.compile(r"^backup-\d{8}-\d{4}$")
FORMATO_NOME_BACKUP = "backup-%Y%m%d-%H%M"

# Il brief e' pronto quando l'autore lo dichiara nel frontmatter. Gli altri
# contengono solo lo scheletro e non vanno pubblicati.
MARCATORE_BRIEF_PRONTO = 'content_status: "testo-definitivo-verificato"'

RADICE = Path(settings.BASE_DIR).parent
WORKBOOK_PREDEFINITO = RADICE / "programma_lezioni_inglese_no_audio.xlsx"
BRIEF_PREDEFINITI = RADICE / "lezioni_markdown"


def brief_pronti(cartella):
    """I brief con contenuto definitivo, in ordine di pubblicazione (per nome file)."""
    return sorted(
        percorso for percorso in Path(cartella).glob("*/*/*.md")
        if MARCATORE_BRIEF_PRONTO in percorso.read_text(encoding="utf-8")
    )


class Command(BaseCommand):
    help = (
        "Crea un branch di backup su Neon, importa il workbook e ripubblica i brief "
        "con testo definitivo. Ripristina in un colpo solo cio' che l'import cancella."
    )

    def add_arguments(self, parser):
        parser.add_argument("file", nargs="?", default=str(WORKBOOK_PREDEFINITO), help="Workbook da importare")
        parser.add_argument("--brief", default=str(BRIEF_PREDEFINITI), help="Cartella dei brief markdown")
        parser.add_argument("--tieni", type=int, default=5, help="Quanti branch di backup conservare (default 5)")
        parser.add_argument("--senza-backup", action="store_true", help="Salta il branch di backup (sconsigliato)")
        parser.add_argument("--dry-run", action="store_true", help="Mostra il piano senza toccare nulla")

    # ---------- fase 1: il branch di backup ----------

    def _crea_backup(self, tieni):
        elenco = neon.elenca_branch()
        genitore = neon.branch_predefinito(elenco)
        backup = sorted(
            (riga for riga in elenco if SCHEMA_NOME_BACKUP.match(riga.get("name", ""))),
            key=lambda riga: riga["name"],  # il nome contiene la data: ordine alfabetico = cronologico
        )

        # Pota PRIMA di creare, cosi' alla fine i backup sono esattamente `tieni`
        # e si fa spazio sotto il tetto del piano.
        da_cancellare = backup[: max(0, len(backup) - max(tieni - 1, 0))]
        for riga in da_cancellare:
            neon.cancella_branch(riga["id"])
            self.stdout.write(f"  potato    {riga['name']}")

        rimasti = len(elenco) - len(da_cancellare)
        if rimasti >= neon.LIMITE_BRANCH_PIANO_FREE:
            raise CommandError(
                f"Il progetto ha gia' {rimasti} branch e il piano Free ne consente "
                f"{neon.LIMITE_BRANCH_PIANO_FREE}. Cancellane qualcuno dalla console Neon, "
                f"oppure abbassa --tieni."
            )

        nome = datetime.now(timezone.utc).strftime(FORMATO_NOME_BACKUP)
        creato = neon.crea_branch(nome, genitore["id"])
        self.stdout.write(self.style.SUCCESS(
            f"  creato    {nome}  (da «{genitore['name']}», id {creato.get('id', '?')})"
        ))
        return nome

    # ---------- fase 3: la ripubblicazione ----------

    def _ripubblica(self, percorsi):
        pubblicate, falliti = [], []
        for percorso in percorsi:
            try:
                esito = publish_markdown_lesson(str(percorso))
            except Exception as errore:  # una lezione rotta non deve fermare le altre
                falliti.append((percorso.name, f"{type(errore).__name__}: {errore}"))
                self.stdout.write(self.style.ERROR(f"  FALLITA   {percorso.name}: {errore}"))
                continue
            pubblicate.append(esito)
            self.stdout.write(
                f"  {esito['id']:12} {esito['sezioni']} sezioni, "
                f"{esito['guidato']} guidati, {esito['finale']} finali"
            )
        return pubblicate, falliti

    # ---------- orchestrazione ----------

    def handle(self, *args, **opzioni):
        workbook = Path(opzioni["file"])
        cartella_brief = Path(opzioni["brief"])
        if not workbook.exists():
            raise CommandError(f"Workbook non trovato: {workbook}")
        if not cartella_brief.is_dir():
            raise CommandError(f"Cartella dei brief non trovata: {cartella_brief}")
        percorsi = brief_pronti(cartella_brief)

        if opzioni["dry_run"]:
            self.stdout.write(f"Workbook          : {workbook}")
            self.stdout.write(f"Brief pronti      : {len(percorsi)}")
            self.stdout.write(f"Branch di backup  : {'SALTATO' if opzioni['senza_backup'] else 'sì'}"
                              f"  (conservati: {opzioni['tieni']})")
            for percorso in percorsi:
                self.stdout.write(f"  pubblicherei  {percorso.name}")
            self.stdout.write(self.style.WARNING("\nDry-run: nessuna modifica, ne' su Neon ne' nel database."))
            return

        nome_backup = None
        if opzioni["senza_backup"]:
            self.stdout.write(self.style.WARNING(
                "1/3  Backup SALTATO — se questo import va storto, hai solo le 6 ore "
                "di cronologia del piano Free per tornare indietro."
            ))
        else:
            self.stdout.write("1/3  Branch di backup su Neon")
            try:
                nome_backup = self._crea_backup(opzioni["tieni"])
            except neon.NeonError as errore:
                # Fermarsi qui e' il punto: senza rete di sicurezza non si importa.
                raise CommandError(
                    f"BACKUP FALLITO — non ho importato nulla.\n{errore}\n\n"
                    f"Per procedere comunque senza rete di sicurezza: --senza-backup"
                ) from errore

        self.stdout.write("\n2/3  Import del workbook")
        try:
            call_command("importa_contenuti", str(workbook))
        except Exception as errore:
            raise CommandError(
                f"IMPORT FALLITO — nessuna modifica salvata (la transazione e' stata annullata): {errore}"
                + (f"\nIl branch di backup «{nome_backup}» resta disponibile su Neon." if nome_backup else "")
            ) from errore

        self.stdout.write(f"\n3/3  Ripubblicazione di {len(percorsi)} brief")
        pubblicate, falliti = self._ripubblica(percorsi)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Fatto: {len(pubblicate)} lezioni pubblicate, "
            f"{sum(e['finale'] for e in pubblicate)} quesiti finali, "
            f"{sum(e['guidato'] for e in pubblicate)} guidati."
        ))
        if nome_backup:
            self.stdout.write(
                f"Ripristino: il branch «{nome_backup}» contiene il database com'era prima di questo import.\n"
                f"Dalla console Neon puoi ispezionarlo o ripristinarlo su production."
            )
        if falliti:
            self.stdout.write(self.style.ERROR(f"\n{len(falliti)} brief non pubblicati:"))
            for nome, motivo in falliti:
                self.stdout.write(self.style.ERROR(f"  {nome}: {motivo}"))
            raise CommandError(f"{len(falliti)} brief su {len(percorsi)} non sono stati pubblicati (vedi sopra).")
