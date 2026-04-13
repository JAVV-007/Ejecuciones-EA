# =============================================================================
# Fichero   : run_batch.py
# Descripción: Ejecuta run_rule_extractor en modo batch para todos los símbolos
#              activos definidos en src/config/symbols.txt.
#              Por cada símbolo ejecuta modo 0 (extracción) y luego modo 1
#              (sintéticos) antes de pasar al siguiente símbolo.
# Autor     : Alberto Veiga
# Creado    : 2026-03-31
# Modificado: 2026-04-13 — Verificación visual del símbolo en modo 0 (último símbolo)
# =============================================================================

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

_SCRIPT_DIR   = Path(__file__).resolve().parent
_PROJECT_DIR  = _SCRIPT_DIR.parent
_SYMBOLS_FILE = _SCRIPT_DIR / "config" / "symbols.txt"
_EXTRACTOR    = _SCRIPT_DIR / "run_rule_extractor.py"
_LOGS_DIR     = _PROJECT_DIR / "logs"


def load_symbols(symbols_file: Path) -> list[str]:
    """Carga la lista de símbolos activos desde un fichero de texto.

    Ignora líneas vacías y líneas que comienzan por '#' (comentarios).

    Args:
        symbols_file: Ruta al fichero de símbolos.

    Returns:
        Lista de símbolos en el orden en que aparecen en el fichero.

    Raises:
        FileNotFoundError: Si el fichero no existe.
    """
    lines = symbols_file.read_text(encoding="utf-8").splitlines()
    return [
        line.strip()
        for line in lines
        if line.strip() and not line.strip().startswith("#")
    ]


def write_log(log_path: Path, symbol: str, mode: int, ok: bool, elapsed_s: int) -> None:
    """Añade una línea al fichero de log del batch.

    Formato: [YYYY-MM-DD HH:MM:SS] SYMBOL | modo N | OK/FAIL | Xs

    Args:
        log_path: Ruta al fichero de log (se crea o se añade si ya existe).
        symbol: Símbolo procesado.
        mode: Modo ejecutado (0 o 1).
        ok: True si la ejecución fue exitosa.
        elapsed_s: Segundos que tardó la ejecución.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status    = "OK  " if ok else "FAIL"
    line      = f"[{timestamp}] {symbol:<20} | modo {mode} | {status} | {elapsed_s}s\n"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line)


def run_symbol(
    symbol: str,
    mode: int,
    set_file: str,
    timeout: int,
    flush_wait: int,
    verify_synth: bool = False,
    verify_symbol: bool = False,
) -> bool:
    """Ejecuta run_rule_extractor.py para un símbolo y modo dados como subprocess.

    Args:
        symbol: Símbolo MT5 a procesar (p.ej. 'EURAUD.QDL').
        mode: Modo del EA (0=extracción de reglas, 1=generación de sintéticos).
        set_file: Ruta al fichero .set; cadena vacía usa el valor por defecto.
        timeout: Segundos máximos de espera.
        flush_wait: Segundos extra tras completar modo 1.
        verify_synth: Si True, abre MT5 con el último sintético tras modo 1 (10s).
        verify_symbol: Si True, abre MT5 con el símbolo sin EA tras modo 0 (10s).

    Returns:
        True si el proceso terminó con exit code 0.
    """
    cmd = [
        sys.executable, str(_EXTRACTOR),
        "--symbol",     symbol,
        "--mode",       str(mode),
        "--timeout",    str(timeout),
        "--flush-wait", str(flush_wait),
    ]
    if set_file:
        cmd += ["--set", set_file]
    if verify_synth and mode == 1:
        cmd += ["--verify-synth", "--verify-wait", "10"]
    if verify_symbol and mode == 0:
        cmd += ["--verify-symbol", "--verify-wait", "10"]

    result = subprocess.run(cmd)
    return result.returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch runner: ejecuta RuleExtractor (modo 0 + modo 1) por simbolo",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--symbols", default=str(_SYMBOLS_FILE),
                        help="Fichero de simbolos (por defecto: config/symbols.txt)")
    parser.add_argument("--set", dest="set_file", default="",
                        help="Fichero .set de parametros\n"
                             "(opcional, usa el por defecto si no se indica)")
    parser.add_argument("--timeout", type=int, default=60,
                        help="Segundos maximos de espera por simbolo y modo (por defecto: 60)")
    parser.add_argument("--flush-wait", type=int, default=15,
                        help="Segundos extra tras completar modo 1 (por defecto: 15)")
    parser.add_argument("--modes", nargs="+", type=int, choices=[0, 1], default=[0, 1],
                        help="Modos a ejecutar por simbolo (por defecto: 0 1)\n"
                             "Ejemplo: --modes 1  (solo sinteticos)")
    args = parser.parse_args()

    symbols_file = Path(args.symbols)
    if not symbols_file.exists():
        print(f"[ERROR] Fichero de simbolos no encontrado: {symbols_file}")
        sys.exit(1)

    symbols = load_symbols(symbols_file)
    if not symbols:
        print("[WARN] No hay simbolos activos en el fichero.")
        sys.exit(0)

    # Crear directorio de logs y fichero para esta ejecución
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    run_ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = _LOGS_DIR / f"batch_{run_ts}.log"

    total = len(symbols)
    print(f"[BATCH] Fichero  : {symbols_file.name}")
    print(f"[BATCH] Total    : {total} simbolos activos")
    print(f"[BATCH] Lista    : {', '.join(symbols)}")
    print(f"[BATCH] Log      : {log_path.name}")
    print("-" * 60)

    # Escribir cabecera en el log
    with log_path.open("w", encoding="utf-8") as f:
        f.write(f"# Batch run {run_ts}\n")
        f.write(f"# Simbolos : {', '.join(symbols)}\n")
        f.write(f"# Formato  : [timestamp] symbol | modo N | OK/FAIL | Xs\n")
        f.write("#" + "-" * 58 + "\n")

    results: dict[str, dict[int, bool]] = {}
    t_batch = time.monotonic()

    for i, symbol in enumerate(symbols, 1):
        print(f"\n[BATCH] [{i}/{total}] {symbol}")
        results[symbol] = {}

        for mode in args.modes:
            mode_label = "extraccion" if mode == 0 else "sinteticos"
            print(f"[BATCH]   modo {mode} ({mode_label}) ...")
            t0 = time.monotonic()
            is_last_synth  = (i == total and mode == 1)
            is_last_mode0  = (i == total and mode == 0 and args.modes == [0])
            ok = run_symbol(symbol, mode, args.set_file, args.timeout, args.flush_wait,
                            verify_synth=is_last_synth,
                            verify_symbol=is_last_mode0)
            elapsed_s = int(time.monotonic() - t0)

            results[symbol][mode] = ok
            write_log(log_path, symbol, mode, ok, elapsed_s)
            print(f"[BATCH]   modo {mode} -> {'OK' if ok else 'FAIL'} ({elapsed_s}s)")

    elapsed_total = int(time.monotonic() - t_batch)
    ok_count   = sum(1 for modes in results.values() for ok in modes.values() if ok)
    fail_count = sum(1 for modes in results.values() for ok in modes.values() if not ok)
    total_ops  = total * len(args.modes)

    print("\n" + "=" * 60)
    print(f"[BATCH] Resumen : {ok_count}/{total_ops} OK  |  {fail_count} fallidos  |  {elapsed_total}s total")
    for symbol, modes in results.items():
        parts = "  ".join(
            f"modo{m}={'OK  ' if modes[m] else 'FAIL'}"
            for m in args.modes
        )
        print(f"        {symbol:<20}  {parts}")
    print(f"[BATCH] Log guardado en: {log_path}")
    print("=" * 60)

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
