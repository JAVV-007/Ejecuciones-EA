#!/usr/bin/env python3
# =============================================================================
# prueba_generacion_reglas_sinth/run_rule_extractor.py
#
# Lanza RuleExtractor en MT5 sobre un símbolo dado de forma desatendida.
#
# Mecanismo:
#   1. Parsea el .set para obtener los parámetros del EA
#   2. Genera un .chr (perfil de gráfico MT5) con RuleExtractor adjunto
#   3. Activa el perfil modificando common.ini  (ProfileLast=...)
#   4. Lanza terminal64.exe (sin args extra — carga el último perfil)
#   5. Detecta finalización:
#        Modo 0 → aparece {symbol}_Trading.mq5 en MQL5/Files/
#        Modo 1 → se crean N directorios en history/Custom/synth/...
#   6. Modo 1: espera extra para flush de caché antes de cerrar MT5
#   7. Cierra MT5 y restaura ProfileLast original
#
# Uso:
#   python run_rule_extractor.py --symbol EURUSD.QDL --mode 0
#   python run_rule_extractor.py --symbol EURUSD.QDL --mode 1
#   python run_rule_extractor.py --symbol EURUSD.QDL --mode 0 --set "mi_params.set"
# =============================================================================

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Rutas — se cargan del factory.yaml del proyecto padre
# ---------------------------------------------------------------------------

_SCRIPT_DIR  = Path(__file__).resolve().parent
_PROJECT_DIR = _SCRIPT_DIR.parent
_FACTORY_CFG = _SCRIPT_DIR / "config" / "factory.yaml"

_PROFILE_NAME = "rule_extractor_run"


def _load_paths() -> tuple[Path, Path, Path]:
    """
    Carga terminal_path y mt5_data_dir de factory.yaml.
    Devuelve (terminal_path, mt5_data_dir, editor_path).
    """
    cfg = yaml.safe_load(_FACTORY_CFG.read_text(encoding="utf-8"))
    mt5_data_dir  = Path(cfg["mt5_data_dir"])
    terminal_path = Path(cfg["mt5"]["terminal_path"])
    editor_path   = Path(cfg["mt5"]["editor_path"])
    return terminal_path, mt5_data_dir, editor_path


# ---------------------------------------------------------------------------
# Parser del .set (UTF-16 LE o UTF-8, preserva separadores de sección)
# ---------------------------------------------------------------------------

def parse_set_file(set_path: Path) -> list[tuple[str, str | None]]:
    """
    Parsea un fichero .set de MT5.

    Devuelve lista de entradas:
      ("sep",   None)          → línea comentario/separador  → <unnamed>= en .chr
      ("param", (name, value)) → parámetro normal

    Soporta:
      - UTF-16 LE con BOM
      - UTF-8
      - Formato simple  Param=valor
      - Formato completo Param=valor||min||step||max||optimize  (toma solo valor)
    """
    raw = set_path.read_bytes()
    txt = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8", errors="replace")

    entries: list[tuple[str, str | None]] = []
    for line in txt.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(";") or line.startswith("#"):
            entries.append(("sep", None))
        elif "=" in line:
            name, _, rest = line.partition("=")
            name  = name.strip()
            value = rest.split("||")[0].strip()
            if name:
                entries.append(("param", (name, value)))

    return entries


# ---------------------------------------------------------------------------
# Generador del fichero .chr
# ---------------------------------------------------------------------------

_CHR_HEADER_TEMPLATE = """\
<chart>
id=999999999999999001
symbol={symbol}
description=
period_type=1
period_size=1
digits=5
tick_size=0.000000
position_time=1744675200
scale_fix=0
scale_fixed_min=1.000000
scale_fixed_max=2.000000
scale_fix11=0
scale_bar=0
scale_bar_val=1.000000
scale=16
mode=1
fore=0
grid=1
volume=2
scroll=1
shift=0
shift_size=20.000000
fixed_pos=0.000000
ticker=1
ohlc=0
one_click=0
one_click_btn=1
bidline=1
askline=0
lastline=0
days=0
descriptions=0
tradelines=0
tradehistory=0
window_left=64
window_top=64
window_right=1920
window_bottom=1080
window_type=3
floating=0
floating_left=0
floating_top=0
floating_right=0
floating_bottom=0
floating_type=1
floating_toolbar=1
floating_tbstate=
background_color=0
foreground_color=16777215
barup_color=65280
bardown_color=65280
bullcandle_color=0
bearcandle_color=16777215
chartline_color=65280
volumes_color=3329330
grid_color=10061943
bidline_color=10061943
askline_color=255
lastline_color=49152
stops_color=255
windows_total=1
"""

_CHR_FOOTER = """\

<window>
height=100.000000
objects=0

<indicator>
name=Main
path=
apply=1
show_data=1
scale_inherit=0
scale_line=0
scale_line_percent=50
scale_line_value=0.000000
scale_fix_min=0
scale_fix_min_val=0.000000
scale_fix_max=0
scale_fix_max_val=0.000000
expertmode=0
fixed_height=-1
</indicator>
</window>
</chart>"""


def build_chr(symbol: str, mode: int, set_entries: list) -> str:
    """
    Genera el contenido de un fichero .chr para el perfil de RuleExtractor.

    Los separadores de sección del .set se convierten en <unnamed>= dentro
    del bloque <inputs>, respetando el formato real de MT5.
    """
    inputs_lines: list[str] = []
    for kind, data in set_entries:
        if kind == "sep":
            inputs_lines.append("<unnamed>=")
        else:
            name, value = data
            if name == "EA_MODE":
                value = str(mode)       # sobreescribir con el modo solicitado
            elif name == "INP_SYMBOL":
                value = ""              # vacío: EA usa el símbolo del gráfico
            inputs_lines.append(f"{name}={value}")

    inputs_block = "\n".join(inputs_lines)

    expert_block = (
        "<expert>\n"
        "name=RuleExtractor\n"
        "path=Experts\\RuleExtractor.ex5\n"
        "expertmode=5\n"
        "<inputs>\n"
        f"{inputs_block}\n"
        "</inputs>\n"
        "</expert>"
    )

    header = _CHR_HEADER_TEMPLATE.format(symbol=symbol)
    return header + expert_block + _CHR_FOOTER


# ---------------------------------------------------------------------------
# Activación del perfil en common.ini
# ---------------------------------------------------------------------------

def _read_common_ini(path: Path) -> str:
    raw = path.read_bytes()
    return raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8", errors="replace")


def _write_common_ini(path: Path, content: str) -> None:
    path.write_bytes(content.encode("utf-16"))


def get_current_profile(common_ini: Path) -> str:
    txt = _read_common_ini(common_ini)
    m = re.search(r"ProfileLast=(.+)", txt)
    return m.group(1).strip() if m else "Default"


def set_profile_last(common_ini: Path, profile_name: str) -> None:
    txt = _read_common_ini(common_ini)
    new_txt = re.sub(r"ProfileLast=.+", f"ProfileLast={profile_name}", txt)
    _write_common_ini(common_ini, new_txt)


@contextmanager
def active_profile(common_ini: Path, profile_name: str):
    """Context manager que activa un perfil y lo restaura al salir."""
    original = get_current_profile(common_ini)
    print(f"[INFO] Activando perfil '{profile_name}' (anterior: '{original}')")
    set_profile_last(common_ini, profile_name)
    try:
        yield
    finally:
        set_profile_last(common_ini, original)
        print(f"[INFO] Perfil restaurado: '{original}'")


# ---------------------------------------------------------------------------
# Detección de finalización
# ---------------------------------------------------------------------------

def wait_mode0(files_dir: Path, symbol: str, timeout: int) -> bool:
    """Modo 0: espera a que aparezca {symbol}_Trading.mq5 en MQL5/Files/."""
    target = files_dir / f"{symbol}_Trading.mq5"
    print(f"[INFO] Esperando: {target.name}")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if target.exists():
            print(f"[OK]   Fichero detectado: {target.name}")
            return True
        time.sleep(1)
    print(f"[WARN] Timeout — no apareció {target.name}")
    return False


def wait_mode1(mt5_data_dir: Path, symbol: str, set_entries: list,
               num_synthetics: int, timeout: int, flush_wait: int) -> bool:
    """
    Modo 1: monitoriza el directorio de símbolos sintéticos.
    Formato del directorio: history/Custom/synth/{symbol}_D1_{from}_{to}/
    Cada subdirectorio = un símbolo sintético generado.
    Espera hasta N subdirectorios y luego flush_wait segundos de buffer.
    """
    # Calcular fechas desde los parámetros del .set
    params = {n: v for kind, data in set_entries if kind == "param" for n, v in [data]}
    date_start = int(params.get("INP_DATE_START", 1396310400))
    date_end   = int(params.get("INP_DATE_END",   1743465600))
    d_start = datetime.fromtimestamp(date_start, tz=timezone.utc).strftime("%Y%m%d")
    d_end   = datetime.fromtimestamp(date_end,   tz=timezone.utc).strftime("%Y%m%d")

    synth_root = mt5_data_dir / "history" / "Custom" / "synth"
    synth_dir  = synth_root / f"{symbol}_D1_{d_start}_{d_end}"

    print(f"[INFO] Directorio sintéticos: {synth_dir}")
    print(f"[INFO] Esperando {num_synthetics} sintéticos...")

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        count = 0
        if synth_dir.exists():
            count = sum(1 for d in synth_dir.iterdir() if d.is_dir())
        elapsed = int(time.monotonic() - (deadline - timeout))
        print(f"\r[INFO] {count}/{num_synthetics} sintéticos ({elapsed}s)", end="", flush=True)
        if count >= num_synthetics:
            print()
            print(f"[OK]   {num_synthetics} sintéticos completados.")
            print(f"[INFO] Esperando {flush_wait}s para flush de caché MT5...")
            time.sleep(flush_wait)
            return True
        time.sleep(2)

    print()
    print(f"[WARN] Timeout — sólo {count}/{num_synthetics} sintéticos generados")
    return False


# ---------------------------------------------------------------------------
# MT5: lanzar y cerrar
# ---------------------------------------------------------------------------

def launch_mt5(terminal_path: Path) -> None:
    subprocess.Popen([str(terminal_path)])
    print(f"[INFO] MT5 lanzado: {terminal_path.name}")
    print("[INFO] Esperando arranque (10s)...")
    time.sleep(10)


def close_mt5() -> None:
    os.system("taskkill /F /IM terminal64.exe >nul 2>&1")
    time.sleep(2)
    print("[INFO] MT5 cerrado.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Lanza RuleExtractor en MT5 de forma desatendida",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--symbol", required=True,
                        help="Símbolo MT5, p.ej. EURUSD.QDL")
    parser.add_argument("--mode", type=int, required=True, choices=[0, 1],
                        help="0 = Extraccion de reglas  (genera {symbol}_Trading.mq5)\n"
                             "1 = Generacion de sinteticos  (crea simbolos Custom)")
    parser.add_argument("--set", dest="set_file",
                        default=str(_SCRIPT_DIR / "crear ea 201404 202504.set"),
                        help="Fichero .set con parámetros\n"
                             "(por defecto: 'crear ea 201404 202504.set' junto al script)")
    parser.add_argument("--timeout", type=int, default=120,
                        help="Segundos máximos esperando finalización (por defecto: 120)")
    parser.add_argument("--flush-wait", type=int, default=15,
                        help="Segundos extra tras completar modo 1 (por defecto: 15)")
    args = parser.parse_args()

    # --- Resolver rutas ---
    terminal_path, mt5_data_dir, _ = _load_paths()
    common_ini   = mt5_data_dir / "config" / "common.ini"
    profiles_dir = mt5_data_dir / "MQL5" / "Profiles" / "Charts"
    files_dir    = mt5_data_dir / "MQL5" / "Files"

    set_path = Path(args.set_file)
    if not set_path.exists():
        print(f"[ERROR] Fichero .set no encontrado: {set_path}")
        sys.exit(1)

    # --- Parsear .set ---
    set_entries = parse_set_file(set_path)
    params      = {n: v for kind, data in set_entries if kind == "param" for n, v in [data]}
    num_synthetics = int(params.get("NUM_SYNTHETICS", 200))
    mode_label  = "EXTRACCIÓN (modo 0)" if args.mode == 0 else f"SINTÉTICOS (modo 1, N={num_synthetics})"

    print(f"[INFO] Símbolo : {args.symbol}")
    print(f"[INFO] Modo    : {mode_label}")
    print(f"[INFO] .set    : {set_path.name}  ({len(params)} parámetros)")

    # --- Crear perfil con el .chr ---
    profile_dir = profiles_dir / _PROFILE_NAME
    profile_dir.mkdir(parents=True, exist_ok=True)
    chr_content = build_chr(args.symbol, args.mode, set_entries)
    chr_path    = profile_dir / "chart01.chr"
    chr_path.write_bytes(chr_content.encode("utf-16"))
    print(f"[INFO] Perfil  : {chr_path}")

    # --- Lanzar MT5, ejecutar, cerrar ---
    success = False
    with active_profile(common_ini, _PROFILE_NAME):
        try:
            launch_mt5(terminal_path)

            if args.mode == 0:
                success = wait_mode0(files_dir, args.symbol, timeout=args.timeout)
            else:
                success = wait_mode1(
                    mt5_data_dir, args.symbol, set_entries, num_synthetics,
                    timeout=args.timeout, flush_wait=args.flush_wait,
                )
        finally:
            close_mt5()

    # --- Resultado ---
    if success:
        print(f"\n[OK] RuleExtractor completado — {args.symbol} modo {args.mode}")
    else:
        print(f"\n[WARN] Completado con timeout — {args.symbol} modo {args.mode}")
        sys.exit(1)


if __name__ == "__main__":
    main()
