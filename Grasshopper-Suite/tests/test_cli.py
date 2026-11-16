import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

fake_net = types.ModuleType("network_tools")
for name in ("dns_lookup", "http_headers", "tls_certificate", "tcp_ports"):
    setattr(fake_net, name, mock.Mock(name=name, return_value={"ok": True}))

fake_files = types.ModuleType("file_tools")
for name in (
    "sha256_file",
    "file_metadata",
    "directory_manifest",
    "compare_manifests",
    "inspect_zip",
):
    setattr(fake_files, name, mock.Mock(name=name, return_value={"ok": True}))

spec = importlib.util.spec_from_file_location(
    "grasshopper_cli_under_test",
    ROOT / "Grasshopper.py",
)
cli = importlib.util.module_from_spec(spec)

with mock.patch.dict(
    sys.modules,
    {"network_tools": fake_net, "file_tools": fake_files},
):
    spec.loader.exec_module(cli)


class FakeProcess:
    def __init__(self, returncode=0, pid=1234):
        self.returncode = returncode
        self.pid = pid
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.killed = True
        self.returncode = -9


class CliTests(unittest.TestCase):
    def setUp(self):
        cli.EXTERNAL_HISTORY.clear()
        for module in (fake_net, fake_files):
            for value in vars(module).values():
                if isinstance(value, mock.Mock):
                    value.reset_mock(return_value=True, side_effect=True)
                    value.return_value = {"ok": True}

    def run_cli(self, answers):
        output = io.StringIO()
        with mock.patch("builtins.input", side_effect=answers), contextlib.redirect_stdout(output):
            result = cli.main()
        return result, output.getvalue()

    def test_exit_invalid_option_and_help(self):
        result, output = self.run_cli(["?", "6", "0"])
        self.assertEqual(result, 0)
        self.assertIn("Opção inválida", output)
        self.assertIn("GRASSHOPPER", output)
        self.assertIn("autorização", output)
        self.assertIn("tools/", output)
        self.assertIn("Até mais.", output)

    def test_all_network_delegations(self):
        result, output = self.run_cli([
            "1", "1", "example.test", "",
            "2", "https://example.test", "",
            "3", "example.test", "", "",
            "4", "example.test", "22, 443", "s", "",
            "0", "0",
        ])
        self.assertEqual(result, 0)
        fake_net.dns_lookup.assert_called_once_with("example.test")
        fake_net.http_headers.assert_called_once_with("https://example.test")
        fake_net.tls_certificate.assert_called_once_with("example.test", 443)
        fake_net.tcp_ports.assert_called_once_with(
            "example.test", [22, 443], authorized=True
        )
        self.assertIn('"ok": true', output)

    def test_invalid_ports_and_custom_tls(self):
        _, output = self.run_cli([
            "1", "4", "example.test", "0,80",
            "3", "example.test", "8443", "",
            "0", "0",
        ])
        self.assertIn("entre 1 e 65535", output)
        fake_net.tcp_ports.assert_not_called()
        fake_net.tls_certificate.assert_called_once_with("example.test", 8443)

    def test_file_functions_and_json_save(self):
        with tempfile.TemporaryDirectory() as temporary:
            saved = Path(temporary) / "result.json"
            _, output = self.run_cli([
                "2", "1", "/tmp/example", str(saved),
                "2", "/tmp/example", "",
                "3", "/tmp", "",
                "5", "/tmp/a.zip", "",
                "0", "0",
            ])
            self.assertEqual(
                json.loads(saved.read_text(encoding="utf-8")),
                {"ok": True},
            )
            self.assertIn("JSON salvo", output)

        fake_files.sha256_file.assert_called_once_with(Path("/tmp/example"))
        fake_files.file_metadata.assert_called_once_with(Path("/tmp/example"))
        fake_files.directory_manifest.assert_called_once_with(Path("/tmp"))
        fake_files.inspect_zip.assert_called_once_with(Path("/tmp/a.zip"))

    def test_compare_receives_dicts(self):
        with tempfile.TemporaryDirectory() as temporary:
            old = Path(temporary) / "old.json"
            new = Path(temporary) / "new.json"
            old.write_text('{"files": {"a": 1}}', encoding="utf-8")
            new.write_text('{"files": {"b": 2}}', encoding="utf-8")
            self.run_cli(["2", "4", str(old), str(new), "", "0", "0"])

        fake_files.compare_manifests.assert_called_once_with(
            {"files": {"a": 1}},
            {"files": {"b": 2}},
        )

    def test_manifest_validation_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "existing.json"
            path.write_text("[]", encoding="utf-8")
            _, output = self.run_cli([
                "2", "4", str(path),
                "1", "/tmp/example", str(path),
                "0", "0",
            ])
            self.assertIn("deve ser um objeto JSON", output)
            self.assertEqual(path.read_text(encoding="utf-8"), "[]")

        fake_files.compare_manifests.assert_not_called()

    def test_backend_error_does_not_exit(self):
        fake_files.inspect_zip.side_effect = Exception("arquivo inválido")
        _, output = self.run_cli(["2", "5", "/tmp/no.zip", "0", "0"])
        self.assertIn("arquivo inválido", output)
        self.assertIn("Até mais.", output)

    def test_command_mode_cd_and_shell(self):
        original = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                with mock.patch.object(cli.subprocess, "run") as run:
                    run.return_value.returncode = 0
                    _, output = self.run_cli([
                        "3",
                        f'cd "{temporary}"',
                        "echo hi | sort",
                        "voltar",
                        "0",
                    ])
                    self.assertEqual(os.getcwd(), temporary)
                    run.assert_called_once_with(
                        "echo hi | sort",
                        shell=True,
                        check=False,
                    )
                    self.assertIn("Comandos reais", output)
        finally:
            os.chdir(original)

    def test_tools_folder_can_be_empty(self):
        with tempfile.TemporaryDirectory() as temporary:
            original = cli.TOOLS_DIR
            cli.TOOLS_DIR = Path(temporary)
            try:
                _, output = self.run_cli(["6", "0"])
                self.assertIn("aguardando arquivo em tools/", output)
            finally:
                cli.TOOLS_DIR = original

    def test_recursive_discovery_and_outem_alias(self):
        with tempfile.TemporaryDirectory() as temporary:
            original = cli.TOOLS_DIR
            cli.TOOLS_DIR = Path(temporary)
            try:
                nested = cli.TOOLS_DIR / "Outerm"
                nested.mkdir()
                program = nested / "OUTERM.PY"
                program.write_text("print('ok')\n", encoding="utf-8")
                found = cli.find_program_file(cli.PROGRAMS["10"]["stems"])
                self.assertEqual(found, program.resolve())
                self.assertEqual(
                    cli.build_execution_command(found),
                    [sys.executable, "-u", str(found)],
                )
            finally:
                cli.TOOLS_DIR = original

    def test_duplicate_program_files_are_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            original = cli.TOOLS_DIR
            cli.TOOLS_DIR = Path(temporary)
            try:
                (cli.TOOLS_DIR / "Rasco.py").write_text("pass\n")
                (cli.TOOLS_DIR / "Rasco.js").write_text(" ")
                with self.assertRaisesRegex(RuntimeError, "Mais de um arquivo"):
                    cli.find_program_file(cli.PROGRAMS["11"]["stems"])
            finally:
                cli.TOOLS_DIR = original

    def test_launcher_inherits_terminal_and_returns_to_menu(self):
        with tempfile.TemporaryDirectory() as temporary:
            original = cli.TOOLS_DIR
            cli.TOOLS_DIR = Path(temporary)
            try:
                script = cli.TOOLS_DIR / "AliensEye.py"
                script.write_text("print('original')\n", encoding="utf-8")
                process = FakeProcess()
                with mock.patch.object(cli.subprocess, "Popen", return_value=process) as popen:
                    with mock.patch.object(cli, "install_project_dependencies", return_value=True):
                        with mock.patch("builtins.input", side_effect=["s"]):
                            output = io.StringIO()
                            with contextlib.redirect_stdout(output):
                                cli.launch_program("4")

                args, kwargs = popen.call_args
                self.assertEqual(args[0], [sys.executable, "-u", str(script.resolve())])
                self.assertIsNone(kwargs["stdin"])
                self.assertIsNone(kwargs["stdout"])
                self.assertIsNone(kwargs["stderr"])
                self.assertFalse(kwargs["shell"])
                self.assertEqual(kwargs["cwd"], str(script.parent))
                self.assertIn("Controle devolvido", output.getvalue())
                self.assertEqual(len(cli.EXTERNAL_HISTORY), 1)
            finally:
                cli.TOOLS_DIR = original

    def test_launcher_cancel_does_not_start_process(self):
        with tempfile.TemporaryDirectory() as temporary:
            original = cli.TOOLS_DIR
            cli.TOOLS_DIR = Path(temporary)
            try:
                (cli.TOOLS_DIR / "PyLoggy.py").write_text("pass\n")
                with mock.patch.object(cli.subprocess, "Popen") as popen:
                    with mock.patch("builtins.input", return_value="n"):
                        output = io.StringIO()
                        with contextlib.redirect_stdout(output):
                            cli.launch_program("5")
                popen.assert_not_called()
                self.assertIn("Execução cancelada", output.getvalue())
            finally:
                cli.TOOLS_DIR = original

    def test_python_syntax_error_is_caught_before_launch(self):
        with tempfile.TemporaryDirectory() as temporary:
            original = cli.TOOLS_DIR
            cli.TOOLS_DIR = Path(temporary)
            try:
                (cli.TOOLS_DIR / "DhAll.py").write_text("not valid python !!!\n")
                with mock.patch.object(cli.subprocess, "Popen") as popen:
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        cli.launch_program("9")
                popen.assert_not_called()
                self.assertIn("Erro de sintaxe", output.getvalue())
            finally:
                cli.TOOLS_DIR = original

    def test_runtime_resolution(self):
        with tempfile.TemporaryDirectory() as temporary:
            js = Path(temporary) / "test.js"
            js.write_text("console.log('ok')")
            with mock.patch.object(cli.shutil, "which", return_value="/usr/bin/node"):
                self.assertEqual(
                    cli.build_execution_command(js),
                    ["/usr/bin/node", str(js.resolve())],
                )

            with mock.patch.object(cli.shutil, "which", return_value=None):
                with self.assertRaisesRegex(RuntimeError, "Interpretador não encontrado"):
                    cli.build_execution_command(js)

    def test_terminate_external_process(self):
        process = FakeProcess(returncode=None)
        cli.terminate_external_process(process)
        self.assertTrue(process.terminated)

    def test_interrupt_and_eof(self):
        result, output = self.run_cli([
            KeyboardInterrupt,
            "1",
            KeyboardInterrupt,
            "0",
            EOFError,
        ])
        self.assertEqual(result, 0)
        self.assertIn("Interrompido", output)
        self.assertIn("Operação interrompida", output)
        self.assertIn("Até mais.", output)


if __name__ == "__main__":
    unittest.main()
