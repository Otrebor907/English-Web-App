from django.core.management.base import BaseCommand, CommandError
from learning.importer import import_content, load_source, source_report, validate_source


class Command(BaseCommand):
    help = "Importa in modo idempotente il catalogo da un workbook .xlsx o da un JSON, validandolo prima di scrivere"

    def add_arguments(self, parser):
        parser.add_argument("file")
        parser.add_argument("--dry-run", action="store_true", help="Valida senza scrivere nel database")

    def handle(self, *args, **options):
        try:
            if options["dry_run"]:
                data = load_source(options["file"])
                validate_source(data)
                report = source_report(data)
                self.stdout.write(self.style.SUCCESS(
                    f"Dry-run valido: {report['conteggi']['lezioni']} lezioni; "
                    f"nessuna modifica salvata"
                ))
                return
            result = import_content(options["file"])
        except Exception as exc:
            raise CommandError(f"IMPORT FALLITO — nessuna modifica salvata: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(
            f"Import completato: {result['lezioni']} lezioni"
        ))
