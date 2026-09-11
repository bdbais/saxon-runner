"""Test delle parti senza interfaccia: python -m unittest discover -s tests -v"""

import functools
import hashlib
import http.server
import os
import shutil
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import saxon_runner as sr  # noqa: E402
import updater  # noqa: E402


class SplitArgs(unittest.TestCase):
    def test_spazi(self):
        self.assertEqual(sr.split_args("-t   -dtd:on"), ["-t", "-dtd:on"])

    def test_valore_fra_virgolette(self):
        self.assertEqual(sr.split_args('p="due parole" -t'), ["p=due parole", "-t"])

    def test_percorso_windows(self):
        # Le barre rovesciate non sono escape: prima split() spezzava sullo spazio.
        self.assertEqual(sr.split_args(r'-o:"C:\My Dir\out.xml"'), [r"-o:C:\My Dir\out.xml"])

    def test_valore_vuoto(self):
        self.assertEqual(sr.split_args('p=""'), ["p="])

    def test_niente(self):
        self.assertEqual(sr.split_args("   "), [])


@unittest.skipUnless(os.name == "nt", "percorsi Windows")
class ResolveLocation(unittest.TestCase):
    def test_uri_con_una_barra_e_spazi_codificati(self):
        # Formato reale dei messaggi di Saxon.
        self.assertEqual(sr.resolve_location("file:/C:/Users/Me/My%20Dir/a.xsl"),
                         r"C:\Users\Me\My Dir\a.xsl")

    def test_uri_con_tre_barre_e_due_punti_finali(self):
        self.assertEqual(sr.resolve_location("file:///C:/x/a.xsl:"), r"C:\x\a.xsl")

    def test_nome_relativo_rispetto_allo_stylesheet(self):
        self.assertEqual(sr.resolve_location("a.xsl", r"C:\progetto"), r"C:\progetto\a.xsl")

    def test_percorso_di_rete(self):
        self.assertEqual(sr.resolve_location("file://server/share/a.xsl"), r"\\server\share\a.xsl")


@unittest.skipUnless(os.name == "nt", "percorsi Windows")
class ErrorLines(unittest.TestCase):
    STDERR = (
        "Error at char 4 in expression in xsl:value-of/@select on line 12 column 42 of main.xsl:\n"
        "  XPST0003  Unexpected token\n"
        "Error on line 7 column 3 of file:/C:/lavoro/My%20Dir/common.xsl:\n"
        "  XTSE0010  Element xsl:foo is not allowed\n"
        "Static error on line 30 of main.xsl: altro\n"
    )
    BASE = r"C:\lavoro\My Dir"

    def test_solo_le_righe_del_file_aperto(self):
        self.assertEqual(sr.error_lines_for(self.STDERR, os.path.join(self.BASE, "main.xsl"),
                                            self.BASE), [12, 30])

    def test_modulo_incluso(self):
        self.assertEqual(sr.error_lines_for(self.STDERR, os.path.join(self.BASE, "common.xsl"),
                                            self.BASE), [7])


class DecodeText(unittest.TestCase):
    def test_utf8(self):
        self.assertEqual(sr.decode_text("città\n".encode("utf-8")), ("città\n", "utf-8", "\n"))

    def test_bom_e_crlf(self):
        self.assertEqual(sr.decode_text(b"\xef\xbb\xbf<a/>\r\n<b/>\r\n"),
                         ("<a/>\n<b/>\n", "utf-8-sig", "\r\n"))

    def test_latin1_resta_identico(self):
        raw = "<?xml version='1.0' encoding='ISO-8859-1'?><a>perché</a>".encode("latin-1")
        text, enc, _ = sr.decode_text(raw)
        self.assertIn("perché", text)
        self.assertEqual(text.encode(enc), raw)


class TkIndex(unittest.TestCase):
    def test_uguale_al_calcolo_originale(self):
        text = "ab\ncd\n\nefg\n"
        starts = sr.line_starts(text)
        for off in range(len(text) + 1):
            before = text[:off]
            naive = f"{before.count(chr(10)) + 1}.{len(before) - before.rfind(chr(10)) - 1}"
            self.assertEqual(sr.tk_index(starts, off), naive, off)


class FindJava(unittest.TestCase):
    def test_impostazione_esplicita_vince(self):
        self.assertEqual(sr.find_java(r"  D:\jdk\bin\java.exe "), r"D:\jdk\bin\java.exe")


class Versions(unittest.TestCase):
    def test_parse(self):
        for text, expected in [("v3.1.0", (3, 1, 0)), ("3.2", (3, 2, 0)),
                               ("v10.0.1-beta", (10, 0, 1)), ("", (0, 0, 0))]:
            self.assertEqual(updater.parse_version(text), expected, text)

    def test_confronto_numerico(self):
        self.assertTrue(updater.is_newer("v3.10.0", "3.9.9"))
        self.assertFalse(updater.is_newer("3.1.0", "3.1.0"))
        self.assertFalse(updater.is_newer("3.0.9", "3.1.0"))

    def test_versione_del_programma(self):
        self.assertEqual(len(updater.parse_version(sr.__version__)), 3)
        self.assertGreater(updater.parse_version(sr.__version__), (3, 0, 0))


class Sums(unittest.TestCase):
    def test_formati_testo_e_binario(self):
        h = "a" * 64
        text = f"{h}  SaxonRunner-Setup.exe\r\n{'B' * 64} *SaxonRunner-portable.exe\n"
        self.assertEqual(updater.parse_sums(text), {"SaxonRunner-Setup.exe": h,
                                                    "SaxonRunner-portable.exe": "b" * 64})


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class DownloadInstaller(unittest.TestCase):
    """Download dell'installer da un server locale, con checksum giusto e sbagliato."""

    @classmethod
    def setUpClass(cls):
        # Con una variabile di proxy nell'ambiente urllib ignora il proxy di sistema.
        os.environ.setdefault("no_proxy", "localhost,127.0.0.1")
        cls.dir = tempfile.mkdtemp()
        cls.payload = os.urandom(300_000)
        with open(os.path.join(cls.dir, updater.SETUP_ASSET), "wb") as f:
            f.write(cls.payload)
        handler = functools.partial(_QuietHandler, directory=cls.dir)
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        shutil.rmtree(cls.dir, ignore_errors=True)

    def _release(self, sums_text):
        with open(os.path.join(self.dir, updater.SUMS_ASSET), "w") as f:
            f.write(sums_text)
        return updater.Release("9.9.9", "v9.9.9", "", "",
                               f"{self.base}/{updater.SETUP_ASSET}",
                               f"{self.base}/{updater.SUMS_ASSET}")

    def test_checksum_giusto(self):
        rel = self._release(f"{hashlib.sha256(self.payload).hexdigest()}  {updater.SETUP_ASSET}\n")
        seen = []
        path = updater.download_installer(rel, "0.0.0", lambda done, total: seen.append(done))
        try:
            with open(path, "rb") as f:
                self.assertEqual(f.read(), self.payload)
            self.assertEqual(seen[-1], len(self.payload))
        finally:
            os.remove(path)

    def test_checksum_sbagliato_non_lascia_file(self):
        rel = self._release(f"{'0' * 64}  {updater.SETUP_ASSET}\n")
        with self.assertRaises(updater.UpdateError):
            updater.download_installer(rel, "0.0.0")
        self.assertFalse(os.path.exists(
            os.path.join(tempfile.gettempdir(), "SaxonRunner-Setup-9.9.9.exe")))

    def test_senza_checksum_non_scarica(self):
        rel = self._release("")
        with self.assertRaises(updater.UpdateError):
            updater.download_installer(rel, "0.0.0")


if __name__ == "__main__":
    unittest.main()
