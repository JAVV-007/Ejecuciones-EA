# <Nombre del proyecto>

> <Descripción breve del proyecto en una o dos frases>

---

## Índice
- [Descripción](#descripción)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Uso](#uso)
- [Módulos y funciones](#módulos-y-funciones)
- [Tests](#tests)
- [Versionado](#versionado)
- [Contribución](#contribución)

---

## Descripción

<Descripción detallada del proyecto: qué problema resuelve, contexto, decisiones
de diseño relevantes.>

---

## Requisitos

- Python 3.12+
- <otras dependencias relevantes>

---

## Instalación

```bash
git clone https://github.com/<usuario>/<proyecto>.git
cd <proyecto>
pip install -e .
```

Para entorno de desarrollo:

```bash
pip install -e ".[dev]"
```

---

## Uso

```bash
# Ejemplo de uso básico
python -m <módulo> <argumentos>
```

<Añadir ejemplos adicionales según el proyecto>

---

## Módulos y funciones

<!--
INSTRUCCIONES PARA CLAUDE CODE:
- Al crear un módulo nuevo, añadir una sección H3 con su nombre y descripción
  general, seguida de la tabla de funciones.
- Al añadir o modificar una función pública, actualizar la fila correspondiente
  en la tabla del módulo. Si la función no existe aún en la tabla, añadirla.
- Al eliminar una función, eliminar su fila de la tabla.
- No eliminar secciones de módulo sin confirmación explícita del desarrollador.
- Mantener las tablas ordenadas alfabéticamente por nombre de función.
- Formato de la tabla: ver ejemplo en la plantilla de módulo más abajo.
-->

---

### Plantilla de módulo — copiar por cada módulo nuevo

<!--
### `src/<nombre_módulo>.py`

<Descripción general del módulo: qué responsabilidad tiene dentro del proyecto.>

| Función | Descripción | Parámetros | Retorna |
|---|---|---|---|
| `nombre_funcion(param1, param2)` | Qué hace esta función | `param1`: tipo — descripción<br>`param2`: tipo — descripción | tipo — descripción |
-->

---

<!-- Las secciones reales de módulos se añaden aquí conforme se desarrolla -->

---

## Tests

```bash
# Ejecutar todos los tests
pytest

# Solo unitarios
pytest tests/unit/ -v

# Solo integración
pytest tests/integration/ -v

# Un módulo específico
pytest tests/unit/test_<módulo>.py -v

# Con cobertura
pytest --cov=src --cov-report=term-missing
```

Consultar [INTEGRATION_MAP.md](./INTEGRATION_MAP.md) para ver las relaciones
entre módulos y qué tests de integración corresponden a cada conjunto.

---

## Versionado

Este proyecto sigue [Semantic Versioning](https://semver.org/lang/es/):

- **MAJOR** (X.0.0): cambios que rompen compatibilidad
- **MINOR** (0.X.0): nueva funcionalidad compatible
- **PATCH** (0.0.X): correcciones y ajustes menores

### Historial de cambios

| Versión | Fecha | Tipo | Descripción |
|---|---|---|---|
| 0.1.0 | <YYYY-MM-DD> | MINOR | Versión inicial |

<!-- Claude Code añadirá filas a esta tabla al proponer bumps de versión -->

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