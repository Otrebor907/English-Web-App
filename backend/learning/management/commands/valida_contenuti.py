import json
from django.core.management.base import BaseCommand, CommandError
from learning.importer import load_source, source_report


class Command(BaseCommand):
    help = "Analizza la fonte e restituisce tutte le anomalie note in testo o JSON"

    def add_arguments(self, parser):
        parser.add_argument("file")
        parser.add_argument("--json", action="store_true", dest="as_json", help="Stampa JSON per CI e automazioni")

    def handle(self, *args, **options):
        try:
            report = source_report(load_source(options["file"]))
        except Exception as exc:
            raise CommandError(f"VALIDAZIONE IMPOSSIBILE: {exc}") from exc
        if options["as_json"]:
            self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            counts = report["conteggi"]
            self.stdout.write(
                f"Fonte: {counts['lezioni']} lezioni, {counts['lezioni_mvp']} MVP, "
                f"{counts['prerequisiti']} prerequisiti, {counts['sezioni']} sezioni"
            )
            for warning in report["avvisi"]:
                self.stdout.write(self.style.WARNING(f"AVVISO — {warning}"))
            for error in report["errori"]:
                self.stdout.write(self.style.ERROR(f"ERRORE — {error}"))
        if not report["valido"]:
            raise CommandError(f"Fonte non valida: {len(report['errori'])} errore/i")
