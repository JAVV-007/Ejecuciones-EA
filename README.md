# Python minimal Claude Code starter

## Objetivo
Base mínima para Claude Code en proyectos Python con poco consumo de contexto:
- `CLAUDE.md` corto y orientado a Python
- `autoMemoryEnabled: false`
- 2 hooks baratos
- subagente de review read-only con `haiku`
- permisos preparados para `pytest`, `ruff` y `mypy`

## Instalación
Copia estos archivos a la raíz del repositorio y ejecuta:

```bash
chmod +x .claude/hooks/*.sh
```

## Uso recomendado
- Implementa normalmente.
- Antes de cerrar una tarea, invoca el review:

```text
@agent-code-reviewer review my last changes
```

## Ajustes rápidos
- Si tu proyecto usa `uv`, `tox` o `poetry`, añade esos comandos a `permissions.allow`.
- Si no usas `mypy`, elimina esa regla.
- Si prefieres que el formatter no toque Markdown o YAML, quita esos patrones del hook.
