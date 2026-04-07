# Ejecuciones EA — RuleExtractor Batch Runner

> Automatiza la ejecución desatendida del EA RuleExtractor en MetaTrader 5 para múltiples símbolos:
> extrae reglas de trading (modo 0) y genera series de datos sintéticos (modo 1).

---

## Índice
- [Descripción](#descripción)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Uso](#uso)
- [Módulos y funciones](#módulos-y-funciones)
- [Tests](#tests)
- [Versionado](#versionado)
- [Contribución](#contribución)

---

## Descripción

Este proyecto automatiza la ejecución del EA **RuleExtractor** en MetaTrader 5 de forma
completamente desatendida para una lista de símbolos definida en un fichero de texto.

### Flujo general

```
symbols.txt
    │
    ▼
run_batch.py ──── por cada símbolo ────► run_rule_extractor.py
                                               │
                          ┌────────────────────┴────────────────────┐
                          │                                         │
                     Modo 0 (extracción)                    Modo 1 (sintéticos)
                          │                                         │
                 Genera {symbol}_Trading.mq5         Genera 200 series sintéticas
                 en MQL5/Files/                      en bases/Custom/history/
```

### Mecanismo interno de run_rule_extractor

1. Parsea el fichero `.set` con los parámetros del EA.
2. Genera un perfil MT5 (`.chr`) con el EA adjunto y el símbolo/temporalidad configurados.
3. Activa el perfil modificando `common.ini` (`ProfileLast=...`).
4. Lanza `terminal64.exe` (carga el perfil automáticamente).
5. Detecta la finalización:
   - **Modo 0** → aparece `{symbol}_Trading.mq5` en `MQL5/Files/`.
   - **Modo 1** → se crean N directorios `{symbol}_SYNTH_NNN` con ficheros `.hcc` en `bases/Custom/history/`.
6. Modo 1: espera extra (`--flush-wait`) para el flush de caché antes de cerrar.
7. Cierra MT5 de forma **graceful** (sin `/F`) para que `symbols.custom.dat` se escriba
   correctamente y los símbolos sintéticos queden registrados en el terminal.
8. Valida que los N directorios sintéticos existen y tienen contenido.
9. Opcional (`--verify-synth`): abre MT5 con el último sintético generado para verificación visual.

---

## Requisitos

- Python 3.12+
- MetaTrader 5 instalado en `C:/Program Files/MetaTrader 5/`
- EA `RuleExtractor.ex5` en la carpeta `Experts` de MT5
- Paquetes Python: `pyyaml`, `pytest` (desarrollo)

---

## Instalación

```bash
git clone <repo>
cd "Ejecuciones EA"
pip install pyyaml
```

Para desarrollo (tests y linter):

```bash
pip install pyyaml pytest ruff mypy
```

---

## Configuración

### `src/config/factory.yaml`

Fichero YAML con todas las rutas y parámetros globales:

| Clave | Descripción |
|---|---|
| `mt5.terminal_path` | Ruta al ejecutable `terminal64.exe` |
| `mt5_data_dir` | Directorio de datos de MT5 (`AppData/Roaming/MetaQuotes/...`) |
| `run_context_defaults.period` | Temporalidad por defecto (`Daily`, `H1`, `W1`, …) |
| `run_context_defaults.from_date` | Fecha de inicio del rango (`YYYY.MM.DD`) |
| `run_context_defaults.to_date` | Fecha de fin del rango (`YYYY.MM.DD`) |

### `src/config/symbols.txt`

Lista de símbolos a procesar. Las líneas que empiezan por `#` se ignoran:

```
# Símbolos comentados (inactivos)
#AUDCAD.QDL
EURAUD.QDL
EURUSD.QDL
```

### `src/config/crear ea 201404 202504.set`

Fichero `.set` de MT5 con los parámetros del EA RuleExtractor. Soporta formato
UTF-16 LE (nativo de MT5) y UTF-8. El parámetro `NUM_SYNTHETICS` determina
cuántas series sintéticas genera el modo 1.

---

## Uso

### Ejecución completa (modo 0 + modo 1 para todos los símbolos)

```bash
python src/run_batch.py
```

### Solo extracción de reglas (modo 0)

```bash
python src/run_batch.py --modes 0
```

### Solo generación de sintéticos (modo 1)

```bash
python src/run_batch.py --modes 1
```

### Con verificación visual tras modo 1

Abre MT5 mostrando el último sintético generado y lo cierra automáticamente
tras N segundos:

```bash
python src/run_batch.py --modes 1 --verify-synth --verify-wait 5
```

### Un símbolo concreto, modo específico

```bash
python src/run_rule_extractor.py --symbol EURAUD.QDL --mode 0
python src/run_rule_extractor.py --symbol EURAUD.QDL --mode 1 --verify-synth
```

### Parámetros disponibles en `run_batch.py`

| Parámetro | Por defecto | Descripción |
|---|---|---|
| `--symbols` | `config/symbols.txt` | Fichero de símbolos |
| `--set` | `crear ea 201404 202504.set` | Fichero `.set` de parámetros |
| `--modes` | `0 1` | Modos a ejecutar (`0`, `1` o `0 1`) |
| `--timeout` | `60` | Segundos máximos de espera por símbolo y modo |
| `--flush-wait` | `15` | Segundos extra tras completar modo 1 |
| `--verify-synth` | off | Abre MT5 con el último sintético tras modo 1 |
| `--verify-wait` | `5` | Segundos que MT5 permanece abierto en la verificación |

### Parámetros disponibles en `run_rule_extractor.py`

| Parámetro | Por defecto | Descripción |
|---|---|---|
| `--symbol` | (requerido) | Símbolo MT5, p.ej. `EURAUD.QDL` |
| `--mode` | (requerido) | `0` = extracción, `1` = sintéticos |
| `--set` | `crear ea 201404 202504.set` | Fichero `.set` de parámetros |
| `--timeout` | `60` | Segundos máximos de espera |
| `--flush-wait` | `15` | Segundos extra tras modo 1 |
| `--verify-synth` | off | Verificación visual del último sintético |
| `--verify-wait` | `5` | Segundos que MT5 permanece abierto en la verificación |

---

## Módulos y funciones

### `src/run_rule_extractor.py`

Lanza el EA RuleExtractor en MT5 para un símbolo y modo dados, de forma desatendida.
Gestiona el ciclo completo: generar el perfil `.chr`, activarlo, lanzar MT5,
detectar la finalización, cerrar MT5 y validar el resultado.

| Función | Descripción | Parámetros | Retorna |
|---|---|---|---|
| `parse_set_file(set_path)` | Parsea un `.set` de MT5 (UTF-16 LE o UTF-8) | `set_path`: Path | `list[tuple[str, str\|None]]` — entradas ordenadas |
| `build_chr(symbol, mode, set_entries, ...)` | Genera el contenido de un `.chr` con EA adjunto | `symbol`, `mode`, `set_entries`, `period_type`, `period_size`, `date_start`, `date_end` | `str` — contenido del `.chr` |
| `build_simple_chr(symbol, ...)` | Genera un `.chr` sin EA para verificación visual | `symbol`, `period_type`, `period_size` | `str` — contenido del `.chr` |
| `get_current_profile(common_ini)` | Lee el perfil activo en `common.ini` | `common_ini`: Path | `str` — nombre del perfil |
| `set_profile_last(common_ini, profile_name)` | Escribe `ProfileLast=` en `common.ini` | `common_ini`: Path, `profile_name`: str | `None` |
| `active_profile(common_ini, profile_name)` | Context manager: activa un perfil y lo restaura al salir | `common_ini`: Path, `profile_name`: str | context manager |
| `wait_mode0(files_dir, symbol, timeout)` | Espera a que aparezca `{symbol}_Trading.mq5` | `files_dir`: Path, `symbol`: str, `timeout`: int | `bool` |
| `wait_mode1(mt5_data_dir, symbol, ...)` | Espera a que se creen N dirs sintéticos con contenido | `mt5_data_dir`, `symbol`, `set_entries`, `num_synthetics`, `timeout`, `flush_wait` | `bool` |
| `validate_synthetics(mt5_data_dir, symbol, num_synthetics)` | Valida que los N sintéticos existen y tienen contenido | `mt5_data_dir`: Path, `symbol`: str, `num_synthetics`: int | `tuple[bool, int, int]` — (ok, dirs, vacíos) |
| `launch_mt5(terminal_path)` | Lanza MT5 y espera 10 s a que arranque | `terminal_path`: Path | `None` |
| `close_mt5()` | Cierra MT5 de forma graceful; fallback a `/F` si no responde | — | `None` |
| `_load_paths()` | Carga rutas desde `factory.yaml` | — | `tuple[Path, Path, Path]` |
| `_load_run_context()` | Carga temporalidad y fechas desde `factory.yaml` | — | `tuple[int, int, int, int]` |

---

### `src/run_batch.py`

Orquesta la ejecución de `run_rule_extractor.py` para todos los símbolos activos
de `symbols.txt`, en los modos indicados, y escribe un log de resultados.

| Función | Descripción | Parámetros | Retorna |
|---|---|---|---|
| `load_symbols(symbols_file)` | Carga símbolos activos de un `.txt` (ignora `#` y vacíos) | `symbols_file`: Path | `list[str]` |
| `write_log(log_path, symbol, mode, ok, elapsed_s)` | Añade una línea al log de batch | `log_path`: Path, `symbol`: str, `mode`: int, `ok`: bool, `elapsed_s`: int | `None` |
| `run_symbol(symbol, mode, set_file, timeout, flush_wait, ...)` | Ejecuta `run_rule_extractor.py` como subprocess | `symbol`, `mode`, `set_file`, `timeout`, `flush_wait`, `verify_synth`, `verify_wait` | `bool` |

---

## Tests

```bash
# Todos los tests
pytest

# Solo unitarios
pytest tests/unit/ -v

# Módulo específico
pytest tests/unit/test_run_rule_extractor.py -v
pytest tests/unit/test_run_batch.py -v
```

Consultar [INTEGRATION_MAP.md](./INTEGRATION_MAP.md) para las relaciones entre módulos
y los tests de integración asociados.

---

## Versionado

Este proyecto sigue [Semantic Versioning](https://semver.org/lang/es/):

- **MAJOR** (X.0.0): cambios que rompen compatibilidad
- **MINOR** (0.X.0): nueva funcionalidad compatible
- **PATCH** (0.0.X): correcciones y ajustes menores

### Historial de cambios

| Versión | Fecha | Tipo | Descripción |
|---|---|---|---|
| 0.2.0 | 2026-04-01 | MINOR | Cierre graceful de MT5 para registro correcto de symbols.custom.dat |
| 0.2.0 | 2026-04-01 | MINOR | `--verify-synth` / `--verify-wait`: verificación visual post-modo 1 |
| 0.2.0 | 2026-04-01 | MINOR | `--modes` en run_batch para ejecutar solo modo 0 o solo modo 1 |
| 0.1.0 | 2026-03-31 | MINOR | Batch runner (`run_batch.py`) con log de ejecución y `symbols.txt` |
| 0.1.0 | 2026-03-31 | MINOR | Validación de sintéticos post-modo 1 |
| 0.1.0 | 2026-03-30 | MINOR | Versión inicial: `run_rule_extractor.py` con modos 0 y 1 |

---

## Contribución

1. Crear rama desde `main`:
   ```bash
   git checkout -b feature/<descripcion-corta>
   ```
2. Desarrollar siguiendo las reglas definidas en `CLAUDE.md`
3. Verificar tests y linter antes de hacer push:
   ```bash
   pytest
   ruff check .
   mypy src/
   ```
4. Abrir Pull Request hacia `main` con descripción del cambio
