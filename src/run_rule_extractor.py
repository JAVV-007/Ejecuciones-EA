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

# Mapeo de nombre de período (factory.yaml) → (period_type, period_size) del .chr de MT5
_PERIOD_MAP: dict[str, tuple[int, int]] = {
    "M1":    (0, 1),    # period_type=0 → minutos
    "M5":    (0, 5),
    "M15":   (0, 15),
    "M30":   (0, 30),
    "H1":    (1, 1),    # period_type=1 → horas
    "H4":    (1, 4),
    "H12":   (1, 12),
    "Daily": (1, 24),   # D1 = 24 horas
    "D1":    (1, 24),
    "W1":    (2, 1),    # period_type=2 → semanas
    "MN":    (3, 1),    # period_type=3 → meses
}


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


def _load_run_context() -> tuple[int, int, int, int]:
    """Carga temporalidad y rango de fechas de run_context_defaults en factory.yaml.

    Returns:
        Tupla (period_type, period_size, date_start_ts, date_end_ts) donde
        date_start_ts y date_end_ts son timestamps Unix UTC.

    Raises:
        KeyError: Si falta alguna clave esperada en factory.yaml.
        ValueError: Si el período no está en _PERIOD_MAP o las fechas no son válidas.
    """
    cfg = yaml.safe_load(_FACTORY_CFG.read_text(encoding="utf-8"))
    ctx = cfg["run_context_defaults"]

    period = ctx["period"]
    if period not in _PERIOD_MAP:
        raise ValueError(f"Período '{period}' no reconocido. Valores válidos: {list(_PERIOD_MAP)}")
    period_type, period_size = _PERIOD_MAP[period]

    date_start = int(datetime.strptime(ctx["from_date"], "%Y.%m.%d").replace(tzinfo=timezone.utc).timestamp())
    date_end   = int(datetime.strptime(ctx["to_date"],   "%Y.%m.%d").replace(tzinfo=timezone.utc).timestamp())

    return period_type, period_size, date_start, date_end


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
period_type={period_type}
period_size={period_size}
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


def build_chr(
    symbol: str,
    mode: int,
    set_entries: list,
    period_type: int = 1,
    period_size: int = 24,
    date_start: int | None = None,
    date_end: int | None = None,
) -> str:
    """Genera el contenido de un fichero .chr para el perfil de RuleExtractor.

    Los separadores de sección del .set se convierten en <unnamed>= dentro
    del bloque <inputs>, respetando el formato real de MT5.
    Si se proporcionan date_start / date_end, sobreescriben INP_DATE_START /
    INP_DATE_END del .set para garantizar coherencia con factory.yaml.

    Args:
        symbol: Símbolo MT5 para el gráfico (p.ej. 'EURUSD.QDL').
        mode: Modo del EA (0=extracción, 1=sintéticos).
        set_entries: Entradas parseadas del fichero .set.
        period_type: Tipo de período MT5 según _PERIOD_MAP (por defecto 2=días).
        period_size: Tamaño del período (por defecto 1 → D1).
        date_start: Timestamp Unix UTC de inicio; sobreescribe INP_DATE_START si se indica.
        date_end: Timestamp Unix UTC de fin; sobreescribe INP_DATE_END si se indica.

    Returns:
        Contenido completo del fichero .chr como string.
    """
    inputs_lines: list[str] = []
    for kind, data in set_entries:
        if kind == "sep":
            inputs_lines.append("<unnamed>=")
        else:
            name, value = data
            if name == "EA_MODE":
                value = str(mode)
            elif name == "INP_SYMBOL":
                value = ""
            elif name == "INP_DATE_START" and date_start is not None:
                value = str(date_start)
            elif name == "INP_DATE_END" and date_end is not None:
                value = str(date_end)
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

    header = _CHR_HEADER_TEMPLATE.format(symbol=symbol, period_type=period_type, period_size=period_size)
    return header + expert_block + _CHR_FOOTER


def build_simple_chr(symbol: str, period_type: int = 1, period_size: int = 24) -> str:
    """Genera un .chr que abre el símbolo en chart sin ningún EA adjunto.

    Usado para verificación visual post-generación de sintéticos.

    Args:
        symbol: Símbolo a abrir (p.ej. 'EURAUD.QDL_SYNTH_200').
        period_type: Tipo de período (por defecto 1 = horas).
        period_size: Tamaño del período (por defecto 24 = D1).

    Returns:
        Contenido del fichero .chr como string.
    """
    header = _CHR_HEADER_TEMPLATE.format(symbol=symbol, period_type=period_type, period_size=period_size)
    return header + _CHR_FOOTER


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


def _synth_dir_has_content(d: Path) -> bool:
    """Devuelve True si el directorio de sintético contiene al menos un fichero > 0 bytes."""
    try:
        return any(f.is_file() and f.stat().st_size > 0 for f in d.iterdir())
    except OSError:
        return False


def validate_synthetics(mt5_data_dir: Path, symbol: str, num_synthetics: int) -> tuple[bool, int, int]:
    """Valida que los sintéticos se hayan generado correctamente.

    Comprueba:
      1. Existen exactamente num_synthetics directorios con patrón {symbol}_SYNTH_NNN.
      2. Ningún directorio tiene contenido a 0 bytes (todos tienen al menos un .hcc > 0).

    Args:
        mt5_data_dir: Directorio raíz de datos de MT5.
        symbol: Símbolo base (p.ej. 'EURAUD.QDL').
        num_synthetics: Número de sintéticos esperados.

    Returns:
        Tupla (ok, dir_count, empty_count) donde:
          - ok: True si dir_count == num_synthetics y empty_count == 0.
          - dir_count: directorios encontrados con el patrón.
          - empty_count: directorios sin contenido válido (vacíos o todos a 0 bytes).
    """
    synth_base = mt5_data_dir / "bases" / "Custom" / "history"
    prefix     = f"{symbol}_SYNTH_"

    if not synth_base.exists():
        return False, 0, 0

    dirs        = [d for d in synth_base.iterdir() if d.is_dir() and d.name.startswith(prefix)]
    dir_count   = len(dirs)
    empty_count = sum(1 for d in dirs if not _synth_dir_has_content(d))
    ok          = dir_count == num_synthetics and empty_count == 0

    return ok, dir_count, empty_count


def wait_mode1(mt5_data_dir: Path, symbol: str, set_entries: list,
               num_synthetics: int, timeout: int, flush_wait: int) -> bool:
    """Modo 1: monitoriza la creación de símbolos sintéticos en MT5.

    Cuenta únicamente directorios {symbol}_SYNTH_NNN que tengan contenido
    (al menos un fichero > 0 bytes), descartando directorios vacíos o en
    proceso de escritura. Espera hasta N dirs con contenido y luego
    flush_wait segundos de buffer para el flush de caché.

    Args:
        mt5_data_dir: Directorio raíz de datos de MT5.
        symbol: Símbolo base (p.ej. 'EURAUD.QDL').
        set_entries: Entradas del .set (no usadas en la detección, mantenidas
                     por compatibilidad de firma).
        num_synthetics: Número de sintéticos esperados.
        timeout: Segundos máximos de espera.
        flush_wait: Segundos extra tras completar para flush de caché MT5.

    Returns:
        True si se completaron los N sintéticos (con contenido) antes del timeout.
    """
    synth_base = mt5_data_dir / "bases" / "Custom" / "history"
    prefix     = f"{symbol}_SYNTH_"

    print(f"[INFO] Directorio sinteticos: {synth_base}")
    print(f"[INFO] Patron: {prefix}NNN")
    print(f"[INFO] Esperando {num_synthetics} sinteticos con contenido...")

    count = 0
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if synth_base.exists():
            count = sum(
                1 for d in synth_base.iterdir()
                if d.is_dir() and d.name.startswith(prefix) and _synth_dir_has_content(d)
            )
        elapsed = int(time.monotonic() - (deadline - timeout))
        print(f"\r[INFO] {count}/{num_synthetics} sinteticos ({elapsed}s)", end="", flush=True)
        if count >= num_synthetics:
            print()
            print(f"[OK]   {num_synthetics} sinteticos con contenido completados.")
            print(f"[INFO] Esperando {flush_wait}s para flush de cache MT5...")
            time.sleep(flush_wait)
            return True
        time.sleep(2)

    print()
    print(f"[WARN] Timeout -- solo {count}/{num_synthetics} sinteticos con contenido")
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
    """Cierra MT5 de forma graceful para que pueda escribir symbols.custom.dat.

    Envía WM_CLOSE a la ventana principal (cierre limpio). Si tras 15 s no ha
    terminado, fuerza la terminación con /F como fallback.
    """
    # Intento graceful: taskkill sin /F envía WM_CLOSE → MT5 puede flushear symbols.custom.dat
    subprocess.run(
        ["taskkill", "/IM", "terminal64.exe"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    # Esperar hasta 15 s a que el proceso desaparezca
    for _ in range(15):
        time.sleep(1)
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq terminal64.exe", "/NH"],
            capture_output=True, text=True,
        )
        if "terminal64.exe" not in result.stdout:
            break
    else:
        # Fallback: forzar si no salió en 15 s
        subprocess.run(
            ["taskkill", "/F", "/IM", "terminal64.exe"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
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
                        default=str(_SCRIPT_DIR / "config" / "crear ea 201404 202504.set"),
                        help="Fichero .set con parámetros\n"
                             "(por defecto: 'crear ea 201404 202504.set' junto al script)")
    parser.add_argument("--timeout", type=int, default=60,
                        help="Segundos máximos esperando finalización\n"
                             "(por defecto: 60 — modo 0 tarda ~10s, modo 1 ~30-40s)")
    parser.add_argument("--flush-wait", type=int, default=15,
                        help="Segundos extra tras completar modo 1 (por defecto: 15)")
    parser.add_argument("--verify-synth", action="store_true",
                        help="Tras modo 1: abre MT5 con el ultimo sintetico para verificacion visual")
    parser.add_argument("--verify-symbol", action="store_true",
                        help="Tras modo 0: abre MT5 con el simbolo sin EA para verificacion visual")
    parser.add_argument("--verify-wait", type=int, default=5,
                        help="Segundos que MT5 permanece abierto durante verificacion (por defecto: 5)")
    args = parser.parse_args()

    # --- Resolver rutas y contexto de ejecución ---
    terminal_path, mt5_data_dir, _ = _load_paths()
    period_type, period_size, date_start, date_end = _load_run_context()
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
    print(f"[INFO] Periodo : period_type={period_type}, period_size={period_size}  |  fechas: {date_start} -> {date_end}")

    # --- Crear perfil con el .chr ---
    profile_dir = profiles_dir / _PROFILE_NAME
    profile_dir.mkdir(parents=True, exist_ok=True)
    chr_content = build_chr(
        args.symbol, args.mode, set_entries,
        period_type=period_type, period_size=period_size,
        date_start=date_start, date_end=date_end,
    )
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
            print("[INFO] Esperando 10s antes de cerrar MT5...")
            time.sleep(10)
            close_mt5()

    # --- Validación post-ejecución modo 1 ---
    if success and args.mode == 1:
        ok, dir_count, empty_count = validate_synthetics(mt5_data_dir, args.symbol, num_synthetics)
        if ok:
            print(f"[OK]   Validacion: {dir_count}/{num_synthetics} dirs con contenido")
        else:
            print(f"[WARN] Validacion fallida: {dir_count}/{num_synthetics} dirs  |  {empty_count} vacias o a 0 bytes")
            success = False

    # --- Resultado ---
    if success:
        print(f"\n[OK] RuleExtractor completado — {args.symbol} modo {args.mode}")
    else:
        print(f"\n[WARN] Completado con timeout — {args.symbol} modo {args.mode}")
        sys.exit(1)

    # --- Verificación visual del último sintético (modo 1 + --verify-synth) ---
    if args.mode == 1 and args.verify_synth:
        last_synth = f"{args.symbol}_SYNTH_{num_synthetics:03d}"
        print(f"\n[VERIFY] Abriendo MT5 con el ultimo sintetico: {last_synth}")
        verify_dir = profiles_dir / "synth_verify"
        verify_dir.mkdir(parents=True, exist_ok=True)
        chr_content = build_simple_chr(last_synth, period_type=period_type, period_size=period_size)
        (verify_dir / "chart01.chr").write_bytes(chr_content.encode("utf-16"))
        set_profile_last(common_ini, "synth_verify")
        launch_mt5(terminal_path)
        print(f"[VERIFY] MT5 abierto con {last_synth}. Cerrando en {args.verify_wait}s...")
        time.sleep(args.verify_wait)
        close_mt5()

    # --- Verificación visual del símbolo real (modo 0 + --verify-symbol) ---
    if args.mode == 0 and args.verify_symbol:
        print(f"\n[VERIFY] Abriendo MT5 con el simbolo: {args.symbol} (sin EA)")
        verify_dir = profiles_dir / "symbol_verify"
        verify_dir.mkdir(parents=True, exist_ok=True)
        chr_content = build_simple_chr(args.symbol, period_type=period_type, period_size=period_size)
        (verify_dir / "chart01.chr").write_bytes(chr_content.encode("utf-16"))
        set_profile_last(common_ini, "symbol_verify")
        launch_mt5(terminal_path)
        print(f"[VERIFY] MT5 abierto con {args.symbol}. Cerrando en {args.verify_wait}s...")
        time.sleep(args.verify_wait)
        close_mt5()


if __name__ == "__main__":
    main()
