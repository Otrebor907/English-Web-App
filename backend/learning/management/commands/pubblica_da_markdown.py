import json

from django.core.management.base import BaseCommand, CommandError

from learning.markdown_source import parse_markdown_lesson, publish_markdown_lesson


class Command(BaseCommand):
    help = "Pubblica una singola lezione a partire dal suo brief markdown (fonte editoriale)."

    def add_arguments(self, parser):
        parser.add_argument("file", help="Percorso del brief markdown della lezione")
        parser.add_argument("--dry-run", action="store_true", help="Mostra il parse senza scrivere nel database")

    def handle(self, *args, **options):
        try:
            if options["dry_run"]:
                data = parse_markdown_lesson(options["file"])
                self.stdout.write(json.dumps(data, ensure_ascii=False, indent=2))
                self.stdout.write(self.style.WARNING(
                    f"\nDry-run: {len(data['sezioni'])} sezioni, "
                    f"{len(data['guidato'])} quesiti guidati, {len(data['finale'])} quesiti finali; "
                    "nessuna modifica salvata."
                ))
                return
            result = publish_markdown_lesson(options["file"])
        except Exception as exc:
            raise CommandError(f"PUBBLICAZIONE FALLITA — nessuna modifica salvata: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(
            f"Pubblicata {result['id']}: {result['sezioni']} sezioni, "
            f"{result['guidato']} quesiti guidati, {result['finale']} quesiti finali."
        ))
