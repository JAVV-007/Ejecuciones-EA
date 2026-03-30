# CLAUDE.md

## Proyecto
Nombre: <nombre del proyecto>
Descripción breve: <qué hace este proyecto>
Python: 3.12+

## Arquitectura
<descripción breve de la estructura de carpetas y responsabilidad de cada capa>

```
src/
  <módulo>/     # <responsabilidad>
tests/
  unit/         # Un fichero por módulo: test_<nombre>.py
  integration/  # Un fichero por conjunto relacionado: test_<a>_<b>.py
```

---

## Convenciones de código

### Nomenclatura
- Clases: PascalCase
- Funciones y métodos: snake_case
- Variables locales: snake_case
- Constantes: UPPER_SNAKE_CASE
- Ficheros y módulos: snake_case

### Cabecera obligatoria en cada fichero
Todo fichero debe comenzar con el siguiente bloque:

```python
# =============================================================================
# Fichero   : <nombre_fichero.py>
# Descripción: <qué hace este módulo>
# Autor     : <autor>
# Creado    : <fecha YYYY-MM-DD>
# Modificado: <fecha YYYY-MM-DD> — <motivo del cambio>
# =============================================================================
```

### Documentación
- Docstrings en todas las funciones y clases (formato Google style)
- Comentarios en línea para lógica no evidente
- Type hints obligatorios en todas las funciones públicas
- Longitud máxima de línea: 100 caracteres

Ejemplo de función correctamente documentada:

```python
def calculate_total(prices: list[float], tax_rate: float = 0.0) -> float:
    """Calcula el total de una lista de precios aplicando impuestos.

    Args:
        prices: Lista de precios unitarios.
        tax_rate: Porcentaje de impuesto a aplicar (0.0 a 1.0).

    Returns:
        Total con impuestos aplicados.

    Raises:
        ValueError: Si tax_rate está fuera del rango [0.0, 1.0].
    """
    if not 0.0 <= tax_rate <= 1.0:
        raise ValueError(f"tax_rate debe estar entre 0.0 y 1.0, recibido: {tax_rate}")
    return sum(prices) * (1 + tax_rate)
```

---

## Herramientas
- Linter/formatter: ruff (configurado en pyproject.toml)
- Tipado estático: mypy
- Tests: pytest
- Gestión de dependencias: <uv / pip / poetry — elige uno>

---

## Tests — Reglas obligatorias

### Pruebas unitarias
- Cada función o clase tiene su test unitario en `tests/unit/test_<módulo>.py`
- El test se entrega en la misma tarea que el código. No son opcionales.
- Al finalizar el desarrollo de cada tarea, ejecutar:
  ```bash
  pytest tests/unit/test_<módulo>.py -v
  ```

### Pruebas de integración
- Antes de iniciar cualquier tarea, leer `INTEGRATION_MAP.md` y comprobar si el
  módulo afectado aparece en alguna relación registrada.
- Si se descubre una nueva dependencia entre módulos durante el desarrollo,
  actualizar `INTEGRATION_MAP.md` en la misma tarea antes de cerrarla.
- Si dos o más módulos están relacionados (uno llama al otro, comparten datos
  o dependen funcionalmente), crear `tests/integration/test_<a>_<b>.py`.
- Si se modifica cualquiera de los módulos implicados en una relación, ejecutar:
  ```bash
  pytest tests/unit/test_<módulo>.py -v
  pytest tests/integration/test_<a>_<b>.py -v
  ```

### Checklist de cierre de tarea
Antes de dar una tarea por terminada, reportar explícitamente:

```
[ ] INTEGRATION_MAP.md leído al inicio (relaciones afectadas identificadas)
[ ] Nuevas dependencias detectadas añadidas a INTEGRATION_MAP.md
    (si no se detectaron nuevas, indicar explícitamente "sin nuevas dependencias")
[ ] Test unitario creado / actualizado
[ ] Tests de integración afectados identificados y ejecutados
    (si no aplica, indicar explícitamente "sin tests de integración afectados")
[ ] README.md actualizado con nuevas funciones o módulos
[ ] Comandos de ejecución de tests indicados
[ ] Propuesta de bump de versión indicada
```

---

## Documentación de proyecto

- Al crear o modificar una función pública, actualizar `README.md` en la sección
  correspondiente al módulo.
- Al añadir un módulo nuevo, crear su sección en `README.md` con descripción
  general y tabla de funciones.
- El `README.md` es fuente de verdad para cualquier persona nueva en el proyecto.

---

## Control de versiones — GitHub

### Checkpoint de inicio de sesión
Antes de iniciar cualquier cambio en una sesión nueva:

1. Verificar que la rama de trabajo está al día con main:
   ```bash
   git fetch origin
   git status
   git log main..HEAD --oneline
   ```
2. Si hay discrepancias (commits no mergeados, conflictos potenciales),
   reportarlo y esperar confirmación antes de continuar.
3. Nunca trabajar directamente sobre `main`.

### Ramas
- Una rama por tarea o feature: `feature/<descripcion-corta>`
- Correcciones urgentes: `hotfix/<descripcion-corta>`

### Versionado semántico — propuesta obligatoria al cerrar cada tarea

| Tipo   | Cuándo usarlo |
|--------|---------------|
| MAJOR (X.0.0) | Cambios que rompen compatibilidad, refactors estructurales, cambios de API pública |
| MINOR (0.X.0) | Nueva funcionalidad que no rompe lo existente |
| PATCH (0.0.X) | Corrección de bugs, ajustes menores, documentación |

El bump de versión se aplica en `pyproject.toml` **solo con confirmación explícita** del desarrollador.

### Formato de commit obligatorio

```
<tipo>(<scope>): <descripción corta en presente>

Tipos válidos: feat | fix | docs | refactor | test | chore
Ejemplos:
  feat(auth): añadir endpoint de login con JWT
  fix(db): corregir cierre de conexión en timeout
  test(api): añadir tests de integración para auth + db
  docs(readme): actualizar tabla de funciones del módulo api
```

---

## Comportamiento esperado

### Inicio obligatorio de cada sesión
Antes de cualquier otra acción, ejecutar siempre estos dos pasos en orden:

1. **Leer `INTEGRATION_MAP.md`** completo e identificar qué módulos de la tarea
   actual aparecen en relaciones registradas. Reportar el resultado:
   - Si hay relaciones afectadas: listarlas explícitamente antes de empezar.
   - Si no hay relaciones afectadas: indicarlo con "INTEGRATION_MAP revisado — sin dependencias afectadas".

2. **Checkpoint Git** (ver sección Control de versiones).

No iniciar ningún desarrollo hasta completar ambos pasos.

### Durante el desarrollo
- Hacer **UNA sola cosa por tarea**. Si se detecta que hay que tocar algo fuera
  del scope indicado, preguntar antes de hacerlo.
- No reorganizar imports ni reformatear código que no sea parte de la tarea.
- No añadir dependencias nuevas sin indicarlo explícitamente en la respuesta
  y esperar confirmación.
- Si algo es ambiguo o hay dudas técnicas, **preguntar siempre antes de
  implementar**. No asumir ni inferir intenciones.
- Nunca modificar ficheros fuera de los indicados en la tarea.
- Si durante el desarrollo se detecta una dependencia entre módulos no registrada,
  **actualizar `INTEGRATION_MAP.md` de forma inmediata** antes de continuar.

---

## Ficheros y carpetas fuera de límites — NO MODIFICAR salvo instrucción explícita

- `.env` y cualquier fichero `*.env.*`
- `pyproject.toml`
- `.github/`
- `CLAUDE.md` (este fichero)

---

## Comandos habituales

```bash
make dev        # Levantar entorno de desarrollo
make test       # Ejecutar suite completa de tests
make lint       # Ruff check + format
make typecheck  # mypy sobre src/
```