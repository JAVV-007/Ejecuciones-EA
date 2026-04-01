# =============================================================================
# Fichero   : test_run_batch.py
# Descripción: Tests unitarios para src/run_batch.py
# Autor     : Alberto Veiga
# Creado    : 2026-03-31
# Modificado: 2026-03-31 — Añadidos tests de write_log
# =============================================================================

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import run_batch


# ---------------------------------------------------------------------------
# load_symbols
# ---------------------------------------------------------------------------

class TestLoadSymbols:
    """Tests para load_symbols: parseo de symbols.txt."""

    def test_returns_active_symbols(self, tmp_path: Path) -> None:
        """Devuelve los símbolos no comentados."""
        content = "#AUDCAD.QDL\nEURAUD.QDL\nEURUSD.QDL\n"
        f = tmp_path / "symbols.txt"
        f.write_text(content, encoding="utf-8")

        result = run_batch.load_symbols(f)

        assert result == ["EURAUD.QDL", "EURUSD.QDL"]

    def test_skips_empty_lines(self, tmp_path: Path) -> None:
        """Las líneas vacías se ignoran."""
        content = "\nEURAUD.QDL\n\nEURUSD.QDL\n\n"
        f = tmp_path / "symbols.txt"
        f.write_text(content, encoding="utf-8")

        result = run_batch.load_symbols(f)

        assert result == ["EURAUD.QDL", "EURUSD.QDL"]

    def test_skips_comment_lines(self, tmp_path: Path) -> None:
        """Las líneas que empiezan por '#' se ignoran."""
        content = "# cabecera\n#AUDCAD.QDL\nEURAUD.QDL\n"
        f = tmp_path / "symbols.txt"
        f.write_text(content, encoding="utf-8")

        result = run_batch.load_symbols(f)

        assert result == ["EURAUD.QDL"]

    def test_preserves_order(self, tmp_path: Path) -> None:
        """El orden de los símbolos se preserva tal como aparece en el fichero."""
        content = "EURUSD.QDL\nEURAUD.QDL\nEURJPY.QDL\n"
        f = tmp_path / "symbols.txt"
        f.write_text(content, encoding="utf-8")

        result = run_batch.load_symbols(f)

        assert result == ["EURUSD.QDL", "EURAUD.QDL", "EURJPY.QDL"]

    def test_all_commented_returns_empty(self, tmp_path: Path) -> None:
        """Si todos los símbolos están comentados devuelve lista vacía."""
        content = "#EURAUD.QDL\n#EURUSD.QDL\n"
        f = tmp_path / "symbols.txt"
        f.write_text(content, encoding="utf-8")

        result = run_batch.load_symbols(f)

        assert result == []

    def test_strips_whitespace(self, tmp_path: Path) -> None:
        """Los espacios al inicio y al final de cada línea se eliminan."""
        content = "  EURAUD.QDL  \n  EURUSD.QDL  \n"
        f = tmp_path / "symbols.txt"
        f.write_text(content, encoding="utf-8")

        result = run_batch.load_symbols(f)

        assert result == ["EURAUD.QDL", "EURUSD.QDL"]

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        """Lanza FileNotFoundError si el fichero no existe."""
        with pytest.raises(FileNotFoundError):
            run_batch.load_symbols(tmp_path / "nonexistent.txt")

    def test_real_symbols_file_loads(self) -> None:
        """El fichero symbols.txt real carga sin errores y contiene símbolos activos."""
        symbols = run_batch.load_symbols(run_batch._SYMBOLS_FILE)

        assert isinstance(symbols, list)
        assert len(symbols) > 0
        assert all(isinstance(s, str) and s for s in symbols)
        assert all(not s.startswith("#") for s in symbols)


# ---------------------------------------------------------------------------
# write_log
# ---------------------------------------------------------------------------

class TestWriteLog:
    """Tests para write_log: escritura del log de ejecución."""

    def test_creates_file_if_not_exists(self, tmp_path: Path) -> None:
        """Crea el fichero de log si no existe."""
        log_path = tmp_path / "batch.log"

        run_batch.write_log(log_path, "EURAUD.QDL", 0, True, 12)

        assert log_path.exists()

    def test_appends_to_existing_file(self, tmp_path: Path) -> None:
        """Añade líneas sin borrar el contenido previo."""
        log_path = tmp_path / "batch.log"
        run_batch.write_log(log_path, "EURAUD.QDL", 0, True,  10)
        run_batch.write_log(log_path, "EURAUD.QDL", 1, True,  35)
        run_batch.write_log(log_path, "EURUSD.QDL", 0, False, 65)

        lines = log_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 3

    def test_ok_status_in_line(self, tmp_path: Path) -> None:
        """Una ejecución exitosa escribe 'OK' en la línea."""
        log_path = tmp_path / "batch.log"

        run_batch.write_log(log_path, "EURAUD.QDL", 0, True, 10)
        content = log_path.read_text(encoding="utf-8")

        assert "OK" in content

    def test_fail_status_in_line(self, tmp_path: Path) -> None:
        """Una ejecución fallida escribe 'FAIL' en la línea."""
        log_path = tmp_path / "batch.log"

        run_batch.write_log(log_path, "EURAUD.QDL", 0, False, 65)
        content = log_path.read_text(encoding="utf-8")

        assert "FAIL" in content

    def test_line_contains_symbol_mode_and_elapsed(self, tmp_path: Path) -> None:
        """La línea contiene el símbolo, el modo y el tiempo transcurrido."""
        log_path = tmp_path / "batch.log"

        run_batch.write_log(log_path, "EURUSD.QDL", 1, True, 38)
        content = log_path.read_text(encoding="utf-8")

        assert "EURUSD.QDL" in content
        assert "modo 1"     in content
        assert "38s"        in content

    def test_line_contains_timestamp(self, tmp_path: Path) -> None:
        """Cada línea comienza con un timestamp entre corchetes."""
        log_path = tmp_path / "batch.log"

        run_batch.write_log(log_path, "EURAUD.QDL", 0, True, 10)
        line = log_path.read_text(encoding="utf-8").strip()

        assert line.startswith("[20")   # [20YY-...


# ---------------------------------------------------------------------------
# run_symbol
# ---------------------------------------------------------------------------

class TestRunSymbol:
    """Tests para run_symbol: invocación del extractor por símbolo."""

    def test_returns_true_on_exit_code_0(self) -> None:
        """Devuelve True cuando el subprocess termina con exit code 0."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("run_batch.subprocess.run", return_value=mock_result):
            result = run_batch.run_symbol("EURAUD.QDL", 0, "", 60, 15)

        assert result is True

    def test_returns_false_on_nonzero_exit(self) -> None:
        """Devuelve False cuando el subprocess termina con exit code distinto de 0."""
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch("run_batch.subprocess.run", return_value=mock_result):
            result = run_batch.run_symbol("EURAUD.QDL", 0, "", 60, 15)

        assert result is False

    def test_command_includes_symbol_and_mode(self) -> None:
        """El comando incluye --symbol y --mode con los valores correctos."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("run_batch.subprocess.run", return_value=mock_result) as mock_run:
            run_batch.run_symbol("EURUSD.QDL", 1, "", 90, 20)
            cmd = mock_run.call_args[0][0]

        assert "--symbol" in cmd
        assert "EURUSD.QDL" in cmd
        assert "--mode" in cmd
        assert "1" in cmd

    def test_command_includes_set_file_when_provided(self) -> None:
        """Si se indica set_file, el comando incluye --set con esa ruta."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("run_batch.subprocess.run", return_value=mock_result) as mock_run:
            run_batch.run_symbol("EURAUD.QDL", 0, "mi_config.set", 60, 15)
            cmd = mock_run.call_args[0][0]

        assert "--set" in cmd
        assert "mi_config.set" in cmd

    def test_command_omits_set_when_empty(self) -> None:
        """Si set_file es cadena vacía, no se incluye --set en el comando."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("run_batch.subprocess.run", return_value=mock_result) as mock_run:
            run_batch.run_symbol("EURAUD.QDL", 0, "", 60, 15)
            cmd = mock_run.call_args[0][0]

        assert "--set" not in cmd
