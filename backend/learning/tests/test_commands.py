from io import StringIO
from django.core.management import call_command
from django.test import TestCase
from learning.models import Lezione


class ContentCommandTests(TestCase):
    def test_dry_run_does_not_write(self):
        output = StringIO()
        call_command("importa_contenuti", "fixtures/contenuti_minimi.json", dry_run=True, stdout=output)
        self.assertEqual(Lezione.objects.count(), 0)
        self.assertIn("nessuna modifica salvata", output.getvalue())

    def test_validator_reports_real_source_as_valid_json(self):
        output = StringIO()
        call_command(
            "valida_contenuti", "../programma_lezioni_inglese_no_audio.xlsx",
            as_json=True, stdout=output,
        )
        self.assertIn('"valido": true', output.getvalue())
        self.assertIn('"lezioni_mvp": 29', output.getvalue())
