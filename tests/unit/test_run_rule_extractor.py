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
            ("param", ("INP_DATE_START", "1396310400")),
            ("param", ("INP_DATE_END",   "1743465600")),
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

    def test_default_period_is_daily(self) -> None:
        """El período por defecto es D1 (period_type=1, period_size=24 = 24 horas)."""
        result = rre.build_chr("EURUSD", 0, [])

        assert "period_type=1" in result
        assert "period_size=24" in result

    def test_custom_period_h1(self) -> None:
        """Se puede especificar H1 (period_type=1, period_size=1)."""
        result = rre.build_chr("EURUSD", 0, [], period_type=1, period_size=1)

        assert "period_type=1" in result
        assert "period_size=1" in result

    def test_date_start_overridden(self) -> None:
        """INP_DATE_START del .set se sobreescribe con el valor de date_start."""
        result = rre.build_chr("EURUSD", 0, self._basic_entries(), date_start=9999999)

        assert "INP_DATE_START=9999999" in result
        assert "INP_DATE_START=1396310400" not in result

    def test_date_end_overridden(self) -> None:
        """INP_DATE_END del .set se sobreescribe con el valor de date_end."""
        result = rre.build_chr("EURUSD", 0, self._basic_entries(), date_end=8888888)

        assert "INP_DATE_END=8888888" in result
        assert "INP_DATE_END=1743465600" not in result

    def test_dates_not_overridden_when_none(self) -> None:
        """Si no se pasan date_start/date_end se conservan los valores del .set."""
        result = rre.build_chr("EURUSD", 0, self._basic_entries())

        assert "INP_DATE_START=1396310400" in result
        assert "INP_DATE_END=1743465600"   in result


# ---------------------------------------------------------------------------
# wait_mode1
# ---------------------------------------------------------------------------

class TestWaitMode1:
    """Tests para wait_mode1: detección de sintéticos con contenido en bases/Custom/history/."""

    def _make_synth_dir(self, tmp_path: Path, symbol: str, count: int,
                         with_content: bool = True) -> Path:
        """Crea N directorios {symbol}_SYNTH_NNN con o sin fichero de contenido."""
        synth_base = tmp_path / "bases" / "Custom" / "history"
        synth_base.mkdir(parents=True)
        for i in range(1, count + 1):
            d = synth_base / f"{symbol}_SYNTH_{i:03d}"
            d.mkdir()
            if with_content:
                (d / "2014.hcc").write_bytes(b"\x00" * 1024)  # fichero > 0 bytes
        return tmp_path

    def test_returns_true_when_synthetics_with_content_present(self, tmp_path: Path) -> None:
        """Devuelve True si los N sintéticos existen con contenido."""
        mt5_data_dir = self._make_synth_dir(tmp_path, "EURAUD.QDL", 200, with_content=True)

        result = rre.wait_mode1(mt5_data_dir, "EURAUD.QDL", [], 200, timeout=5, flush_wait=0)

        assert result is True

    def test_returns_false_when_dirs_exist_but_empty(self, tmp_path: Path) -> None:
        """Directorios vacíos (0 bytes) no cuentan como sintéticos completados."""
        mt5_data_dir = self._make_synth_dir(tmp_path, "EURAUD.QDL", 200, with_content=False)

        result = rre.wait_mode1(mt5_data_dir, "EURAUD.QDL", [], 200, timeout=3, flush_wait=0)

        assert result is False

    def test_returns_false_on_timeout_with_zero_synthetics(self, tmp_path: Path) -> None:
        """Devuelve False si no aparece ningún sintético antes del timeout."""
        (tmp_path / "bases" / "Custom" / "history").mkdir(parents=True)

        result = rre.wait_mode1(tmp_path, "EURAUD.QDL", [], 5, timeout=3, flush_wait=0)

        assert result is False

    def test_counts_only_matching_symbol(self, tmp_path: Path) -> None:
        """Solo cuenta directorios del símbolo indicado, no de otros símbolos."""
        synth_base = tmp_path / "bases" / "Custom" / "history"
        synth_base.mkdir(parents=True)
        for i in range(1, 201):
            d = synth_base / f"AUDCAD.QDL_SYNTH_{i:03d}"
            d.mkdir()
            (d / "2014.hcc").write_bytes(b"\x00" * 1024)

        result = rre.wait_mode1(tmp_path, "EURAUD.QDL", [], 200, timeout=3, flush_wait=0)

        assert result is False

    def test_partial_count_triggers_timeout(self, tmp_path: Path) -> None:
        """Con menos sintéticos de los esperados devuelve False por timeout."""
        mt5_data_dir = self._make_synth_dir(tmp_path, "EURAUD.QDL", 50, with_content=True)

        result = rre.wait_mode1(mt5_data_dir, "EURAUD.QDL", [], 200, timeout=3, flush_wait=0)

        assert result is False

    def test_synth_base_missing_does_not_crash(self, tmp_path: Path) -> None:
        """Si bases/Custom/history no existe aún, espera sin crashear."""
        result = rre.wait_mode1(tmp_path, "EURAUD.QDL", [], 5, timeout=3, flush_wait=0)

        assert result is False


# ---------------------------------------------------------------------------
# validate_synthetics
# ---------------------------------------------------------------------------

class TestValidateSynthetics:
    """Tests para validate_synthetics: validación post-generación de sintéticos."""

    def _make_synth_dirs(self, tmp_path: Path, symbol: str, count: int,
                          empty_indices: list[int] | None = None) -> Path:
        """Crea N dirs con contenido; empty_indices indica cuáles quedan vacíos."""
        synth_base = tmp_path / "bases" / "Custom" / "history"
        synth_base.mkdir(parents=True)
        empty_set = set(empty_indices or [])
        for i in range(1, count + 1):
            d = synth_base / f"{symbol}_SYNTH_{i:03d}"
            d.mkdir()
            if i not in empty_set:
                (d / "2014.hcc").write_bytes(b"\x00" * 1024)
        return tmp_path

    def test_ok_when_all_dirs_with_content(self, tmp_path: Path) -> None:
        """Retorna (True, 200, 0) cuando todos los sintéticos tienen contenido."""
        mt5 = self._make_synth_dirs(tmp_path, "EURAUD.QDL", 200)

        ok, dir_count, empty_count = rre.validate_synthetics(mt5, "EURAUD.QDL", 200)

        assert ok is True
        assert dir_count   == 200
        assert empty_count == 0

    def test_fail_when_count_mismatch(self, tmp_path: Path) -> None:
        """Retorna False si hay menos dirs de los esperados."""
        mt5 = self._make_synth_dirs(tmp_path, "EURAUD.QDL", 150)

        ok, dir_count, empty_count = rre.validate_synthetics(mt5, "EURAUD.QDL", 200)

        assert ok is False
        assert dir_count == 150

    def test_fail_when_some_dirs_empty(self, tmp_path: Path) -> None:
        """Retorna False si algún directorio está vacío o a 0 bytes."""
        mt5 = self._make_synth_dirs(tmp_path, "EURAUD.QDL", 200, empty_indices=[1, 50, 100])

        ok, dir_count, empty_count = rre.validate_synthetics(mt5, "EURAUD.QDL", 200)

        assert ok is False
        assert dir_count   == 200
        assert empty_count == 3

    def test_fail_when_synth_base_missing(self, tmp_path: Path) -> None:
        """Retorna (False, 0, 0) si el directorio base no existe."""
        ok, dir_count, empty_count = rre.validate_synthetics(tmp_path, "EURAUD.QDL", 200)

        assert ok is False
        assert dir_count   == 0
        assert empty_count == 0

    def test_counts_only_matching_symbol(self, tmp_path: Path) -> None:
        """Solo cuenta dirs del símbolo indicado."""
        synth_base = tmp_path / "bases" / "Custom" / "history"
        synth_base.mkdir(parents=True)
        # 200 dirs de AUDCAD, 0 de EURAUD
        for i in range(1, 201):
            d = synth_base / f"AUDCAD.QDL_SYNTH_{i:03d}"
            d.mkdir()
            (d / "2014.hcc").write_bytes(b"\x00" * 1024)

        ok, dir_count, _ = rre.validate_synthetics(tmp_path, "EURAUD.QDL", 200)

        assert ok is False
        assert dir_count == 0


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


# ---------------------------------------------------------------------------
# _load_run_context
# ---------------------------------------------------------------------------

class TestLoadRunContext:
    """Tests para _load_run_context: carga de período y fechas desde factory.yaml."""

    def _make_factory_yaml(self, tmp_path: Path, period: str = "Daily",
                            from_date: str = "2014.04.01",
                            to_date:   str = "2025.04.01") -> Path:
        """Crea un factory.yaml con run_context_defaults configurado."""
        cfg = {
            "mt5_data_dir": str(tmp_path),
            "mt5": {
                "terminal_path": str(tmp_path / "terminal64.exe"),
                "editor_path":   str(tmp_path / "metaeditor64.exe"),
            },
            "run_context_defaults": {
                "period":    period,
                "from_date": from_date,
                "to_date":   to_date,
            },
        }
        yaml_path = tmp_path / "factory.yaml"
        yaml_path.write_text(yaml.dump(cfg), encoding="utf-8")
        return yaml_path

    def test_daily_maps_to_period_type_1_size_24(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """El período 'Daily' se mapea a period_type=1, period_size=24 (24 horas = D1)."""
        yaml_path = self._make_factory_yaml(tmp_path, period="Daily")
        monkeypatch.setattr(rre, "_FACTORY_CFG", yaml_path)

        period_type, period_size, _, _ = rre._load_run_context()

        assert period_type == 1
        assert period_size == 24

    def test_h1_maps_correctly(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """El período 'H1' se mapea a period_type=1, period_size=1."""
        yaml_path = self._make_factory_yaml(tmp_path, period="H1")
        monkeypatch.setattr(rre, "_FACTORY_CFG", yaml_path)

        period_type, period_size, _, _ = rre._load_run_context()

        assert period_type == 1
        assert period_size == 1

    def test_from_date_converted_to_timestamp(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """from_date '2014.04.01' se convierte al timestamp Unix UTC correcto."""
        yaml_path = self._make_factory_yaml(tmp_path, from_date="2014.04.01")
        monkeypatch.setattr(rre, "_FACTORY_CFG", yaml_path)

        _, _, date_start, _ = rre._load_run_context()

        assert date_start == 1396310400  # 2014-04-01 00:00:00 UTC

    def test_to_date_converted_to_timestamp(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """to_date '2025.04.01' se convierte al timestamp Unix UTC correcto."""
        yaml_path = self._make_factory_yaml(tmp_path, to_date="2025.04.01")
        monkeypatch.setattr(rre, "_FACTORY_CFG", yaml_path)

        _, _, _, date_end = rre._load_run_context()

        assert date_end == 1743465600  # 2025-04-01 00:00:00 UTC

    def test_unknown_period_raises_value_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Un período no reconocido lanza ValueError con mensaje descriptivo."""
        yaml_path = self._make_factory_yaml(tmp_path, period="XYZ")
        monkeypatch.setattr(rre, "_FACTORY_CFG", yaml_path)

        with pytest.raises(ValueError, match="XYZ"):
            rre._load_run_context()


# ---------------------------------------------------------------------------
# Validación contra factory.yaml real
# ---------------------------------------------------------------------------

class TestRunContextWithRealConfig:
    """Valida que _load_run_context() y build_chr() son coherentes con
    el factory.yaml del proyecto (src/config/factory.yaml).
    Estos tests fallarán si el fichero no existe o tiene valores inesperados.
    """

    def test_real_factory_yaml_loads_without_error(self) -> None:
        """_load_run_context() no lanza excepción con el factory.yaml real."""
        # Si este test falla, el fichero no existe o tiene claves mal formadas
        period_type, period_size, date_start, date_end = rre._load_run_context()

        assert isinstance(period_type, int)
        assert isinstance(period_size, int)
        assert date_start > 0
        assert date_end > date_start

    def test_real_config_period_is_daily(self) -> None:
        """factory.yaml tiene period='Daily' → period_type=1, period_size=24 (D1 = 24h)."""
        period_type, period_size, _, _ = rre._load_run_context()

        assert period_type == 1,  f"Se esperaba period_type=1 (horas), obtenido {period_type}"
        assert period_size == 24, f"Se esperaba period_size=24 (D1=24h), obtenido {period_size}"

    def test_real_config_dates_match_yaml(self) -> None:
        """Las fechas cargadas coinciden con los valores declarados en factory.yaml."""
        _, _, date_start, date_end = rre._load_run_context()

        # Valores esperados según factory.yaml: from_date=2014.04.01, to_date=2025.04.01
        assert date_start == 1396310400, f"from_date esperado 1396310400 (2014-04-01), obtenido {date_start}"
        assert date_end   == 1743465600, f"to_date esperado 1743465600 (2025-04-01), obtenido {date_end}"

    def test_chr_generated_with_real_config_has_correct_period(self) -> None:
        """El .chr generado con los valores de factory.yaml contiene period_type=1, period_size=24 (D1)."""
        period_type, period_size, date_start, date_end = rre._load_run_context()
        chr_content = rre.build_chr(
            "EURAUD.QDL", 0, [],
            period_type=period_type, period_size=period_size,
            date_start=date_start, date_end=date_end,
        )

        assert f"period_type={period_type}" in chr_content
        assert f"period_size={period_size}" in chr_content

    def test_chr_generated_with_real_config_has_correct_dates(self) -> None:
        """El .chr generado con los valores de factory.yaml incluye las fechas correctas."""
        period_type, period_size, date_start, date_end = rre._load_run_context()
        entries = [
            ("param", ("INP_DATE_START", "0")),
            ("param", ("INP_DATE_END",   "0")),
        ]
        chr_content = rre.build_chr(
            "EURAUD.QDL", 0, entries,
            period_type=period_type, period_size=period_size,
            date_start=date_start, date_end=date_end,
        )

        assert f"INP_DATE_START={date_start}" in chr_content
        assert f"INP_DATE_END={date_end}"   in chr_content
