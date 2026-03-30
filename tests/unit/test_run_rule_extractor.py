# =============================================================================
# Fichero   : test_run_rule_extractor.py
# Descripción: Tests unitarios para src/run_rule_extractor.py
# Autor     : Alberto Veiga
# Creado    : 2026-03-30
# Modificado: 2026-03-30 — Versión inicial
# =============================================================================

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import run_rule_extractor as rre


# ---------------------------------------------------------------------------
# parse_set_file
# ---------------------------------------------------------------------------

class TestParseSetFile:
    """Tests para parse_set_file: parseo de ficheros .set de MT5."""

    def test_parse_simple_utf8(self, tmp_path: Path) -> None:
        """Parsea parámetros simples en UTF-8."""
        content = "EA_MODE=0\nINP_SYMBOL=EURUSD\n"
        f = tmp_path / "test.set"
        f.write_text(content, encoding="utf-8")

        entries = rre.parse_set_file(f)

        assert ("param", ("EA_MODE", "0")) in entries
        assert ("param", ("INP_SYMBOL", "EURUSD")) in entries

    def test_parse_separators_semicolon(self, tmp_path: Path) -> None:
        """Las líneas con ';' se convierten en ('sep', None)."""
        content = "; === Section ===\nEA_MODE=0\n"
        f = tmp_path / "test.set"
        f.write_text(content, encoding="utf-8")

        entries = rre.parse_set_file(f)

        assert entries[0] == ("sep", None)

    def test_parse_separators_hash(self, tmp_path: Path) -> None:
        """Las líneas con '#' se convierten en ('sep', None)."""
        content = "# comment\nEA_MODE=0\n"
        f = tmp_path / "test.set"
        f.write_text(content, encoding="utf-8")

        entries = rre.parse_set_file(f)

        assert entries[0] == ("sep", None)

    def test_parse_full_format_takes_first_value(self, tmp_path: Path) -> None:
        """Formato completo Param=valor||min||step||max: toma solo el valor."""
        content = "LOT_SIZE=0.1||0.01||0.01||1.0||0\n"
        f = tmp_path / "test.set"
        f.write_text(content, encoding="utf-8")

        entries = rre.parse_set_file(f)

        assert ("param", ("LOT_SIZE", "0.1")) in entries

    def test_parse_skips_empty_lines(self, tmp_path: Path) -> None:
        """Las líneas vacías se ignoran."""
        content = "\nEA_MODE=0\n\n"
        f = tmp_path / "test.set"
        f.write_text(content, encoding="utf-8")

        entries = rre.parse_set_file(f)

        assert len(entries) == 1
        assert entries[0] == ("param", ("EA_MODE", "0"))

    def test_parse_utf16_le(self, tmp_path: Path) -> None:
        """Acepta ficheros codificados en UTF-16 LE (formato nativo de MT5)."""
        content = "EA_MODE=1\nINP_SYMBOL=GBPUSD\n"
        f = tmp_path / "test.set"
        f.write_bytes(content.encode("utf-16"))

        entries = rre.parse_set_file(f)

        assert ("param", ("EA_MODE", "1")) in entries
        assert ("param", ("INP_SYMBOL", "GBPUSD")) in entries

    def test_parse_order_preserved(self, tmp_path: Path) -> None:
        """El orden de las entradas se preserva tal como aparece en el fichero."""
        content = "; sep\nA=1\nB=2\nC=3\n"
        f = tmp_path / "test.set"
        f.write_text(content, encoding="utf-8")

        entries = rre.parse_set_file(f)

        assert entries[0] == ("sep", None)
        assert entries[1] == ("param", ("A", "1"))
        assert entries[2] == ("param", ("B", "2"))
        assert entries[3] == ("param", ("C", "3"))


# ---------------------------------------------------------------------------
# build_chr
# ---------------------------------------------------------------------------

class TestBuildChr:
    """Tests para build_chr: generación del fichero .chr de perfil MT5."""

    def _basic_entries(self) -> list:
        """Entradas mínimas que simulan un .set real."""
        return [
            ("sep", None),
            ("param", ("EA_MODE", "0")),
            ("param", ("INP_SYMBOL", "EURUSD")),
            ("param", ("NUM_SYNTHETICS", "200")),
        ]

    def test_symbol_in_header(self) -> None:
        """El símbolo aparece correctamente en la cabecera del .chr."""
        result = rre.build_chr("EURUSD.QDL", 0, self._basic_entries())

        assert "symbol=EURUSD.QDL" in result

    def test_mode_overrides_ea_mode_param(self) -> None:
        """EA_MODE en el .set se sobreescribe con el modo indicado."""
        result_mode0 = rre.build_chr("EURUSD", 0, self._basic_entries())
        result_mode1 = rre.build_chr("EURUSD", 1, self._basic_entries())

        assert "EA_MODE=0" in result_mode0
        assert "EA_MODE=1" in result_mode1

    def test_inp_symbol_cleared(self) -> None:
        """INP_SYMBOL queda vacío para que MT5 use el símbolo del gráfico."""
        result = rre.build_chr("EURUSD", 0, self._basic_entries())

        assert "INP_SYMBOL=" in result
        # El valor debe estar vacío (no "EURUSD" ni nada más)
        lines = result.splitlines()
        inp_symbol_line = next(l for l in lines if l.startswith("INP_SYMBOL="))
        assert inp_symbol_line == "INP_SYMBOL="

    def test_separator_becomes_unnamed(self) -> None:
        """Los separadores de sección del .set se convierten en <unnamed>=."""
        result = rre.build_chr("EURUSD", 0, self._basic_entries())

        assert "<unnamed>=" in result

    def test_expert_block_present(self) -> None:
        """El bloque <expert> está presente con nombre y ruta correctos."""
        result = rre.build_chr("EURUSD", 0, [])

        assert "<expert>" in result
        assert "name=RuleExtractor" in result
        assert "path=Experts\\RuleExtractor.ex5" in result
        assert "</expert>" in result

    def test_chart_wrapper(self) -> None:
        """El contenido comienza con <chart> y termina con </chart>."""
        result = rre.build_chr("EURUSD", 0, [])

        assert result.startswith("<chart>")
        assert result.endswith("</chart>")

    def test_inputs_block_present(self) -> None:
        """El bloque <inputs>...</inputs> está presente dentro de <expert>."""
        result = rre.build_chr("EURUSD", 0, self._basic_entries())

        assert "<inputs>" in result
        assert "</inputs>" in result

    def test_empty_entries_produces_valid_structure(self) -> None:
        """Con lista de entradas vacía el .chr sigue siendo estructuralmente válido."""
        result = rre.build_chr("TEST", 0, [])

        assert "<chart>" in result
        assert "<expert>" in result
        assert "<window>" in result


# ---------------------------------------------------------------------------
# get_current_profile / set_profile_last
# ---------------------------------------------------------------------------

class TestCommonIni:
    """Tests para lectura y escritura de ProfileLast en common.ini."""

    def _make_ini(self, tmp_path: Path, profile: str) -> Path:
        """Crea un common.ini codificado en UTF-16 con ProfileLast configurado."""
        content = f"[Terminal]\nProfileLast={profile}\nOtherKey=value\n"
        p = tmp_path / "common.ini"
        p.write_bytes(content.encode("utf-16"))
        return p

    def test_get_current_profile(self, tmp_path: Path) -> None:
        """Devuelve el nombre del perfil activo correctamente."""
        ini = self._make_ini(tmp_path, "my_profile")

        assert rre.get_current_profile(ini) == "my_profile"

    def test_get_current_profile_default_when_missing(self, tmp_path: Path) -> None:
        """Devuelve 'Default' cuando la clave ProfileLast no existe."""
        ini = tmp_path / "common.ini"
        ini.write_bytes("[Terminal]\nSomeKey=val\n".encode("utf-16"))

        assert rre.get_current_profile(ini) == "Default"

    def test_set_profile_last_updates_value(self, tmp_path: Path) -> None:
        """set_profile_last cambia ProfileLast al valor indicado."""
        ini = self._make_ini(tmp_path, "old_profile")

        rre.set_profile_last(ini, "new_profile")

        assert rre.get_current_profile(ini) == "new_profile"

    def test_set_profile_last_preserves_other_keys(self, tmp_path: Path) -> None:
        """Modificar ProfileLast no elimina otras claves del fichero."""
        ini = self._make_ini(tmp_path, "old_profile")

        rre.set_profile_last(ini, "new_profile")
        content = ini.read_bytes().decode("utf-16")

        assert "OtherKey=value" in content

    def test_set_profile_last_writes_utf16(self, tmp_path: Path) -> None:
        """El fichero resultante se escribe en UTF-16 (BOM presente)."""
        ini = self._make_ini(tmp_path, "original")

        rre.set_profile_last(ini, "updated")
        raw = ini.read_bytes()

        assert raw[:2] in (b"\xff\xfe", b"\xfe\xff"), "El fichero debe tener BOM UTF-16"


# ---------------------------------------------------------------------------
# _load_paths
# ---------------------------------------------------------------------------

class TestLoadPaths:
    """Tests para _load_paths: carga de rutas desde factory.yaml."""

    def _make_factory_yaml(self, tmp_path: Path) -> Path:
        """Crea un factory.yaml mínimo válido para las pruebas."""
        cfg = {
            "mt5_data_dir": str(tmp_path / "mt5data"),
            "mt5": {
                "terminal_path": str(tmp_path / "terminal64.exe"),
                "editor_path":   str(tmp_path / "metaeditor64.exe"),
            },
        }
        yaml_path = tmp_path / "factory.yaml"
        yaml_path.write_text(yaml.dump(cfg), encoding="utf-8")
        return yaml_path

    def test_returns_three_paths(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """_load_paths devuelve una tupla de exactamente tres Path."""
        yaml_path = self._make_factory_yaml(tmp_path)
        monkeypatch.setattr(rre, "_FACTORY_CFG", yaml_path)

        result = rre._load_paths()

        assert len(result) == 3
        assert all(isinstance(p, Path) for p in result)

    def test_terminal_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """terminal_path apunta al ejecutable configurado en el yaml."""
        yaml_path = self._make_factory_yaml(tmp_path)
        monkeypatch.setattr(rre, "_FACTORY_CFG", yaml_path)

        terminal_path, _, _ = rre._load_paths()

        assert terminal_path == Path(tmp_path / "terminal64.exe")

    def test_mt5_data_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """mt5_data_dir apunta al directorio configurado en el yaml."""
        yaml_path = self._make_factory_yaml(tmp_path)
        monkeypatch.setattr(rre, "_FACTORY_CFG", yaml_path)

        _, mt5_data_dir, _ = rre._load_paths()

        assert mt5_data_dir == Path(tmp_path / "mt5data")

    def test_editor_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """editor_path apunta al editor configurado en el yaml."""
        yaml_path = self._make_factory_yaml(tmp_path)
        monkeypatch.setattr(rre, "_FACTORY_CFG", yaml_path)

        _, _, editor_path = rre._load_paths()

        assert editor_path == Path(tmp_path / "metaeditor64.exe")

    def test_factory_cfg_points_to_src_config(self) -> None:
        """_FACTORY_CFG debe apuntar a src/config/factory.yaml (bug de ruta corregido)."""
        # Verifica que la ruta calculada a nivel de módulo es la correcta
        # tras la corrección del bug (_SCRIPT_DIR en vez de _PROJECT_DIR)
        assert rre._FACTORY_CFG.parts[-2:] == ("config", "factory.yaml")
        assert "src" in rre._FACTORY_CFG.parts
