# CLAUDE.md

## Proyecto
Nombre: Ejecuciones desde script de EAs
Descripción breve: Dado un EA existente en la carpeta raiz de Experts de MT5, ejecuta dicho EA en un simbolo determinado para un timeFrame determinado. Cargando una configuración específica de dicho EA.
Python: 3.12+

## Arquitectura
src: como carpeta raiz del código de proyecto.
  config: como carpeta de configuración almacena las variables y valores de configuración
  modulos: código adicional que se pueda necesitar.

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

## Mission
Help implement Python code that is correct, maintainable, easy to test, and easy to understand.

Always prioritize:
1. Functional correctness
2. Clarity
3. Testability
4. Simplicity
5. Consistency with the repository
6. Performance only when it is a real requirement

## Working style
- Understand the goal before proposing or applying a final change.
- Prefer minimal, localized, reversible changes.
- Do not expand scope silently.
- Do not invent requirements.
- Respect existing architecture and conventions unless there is a clear reason to improve them.
- Prefer the simplest solution that solves the problem correctly.
- Do not introduce abstractions or layers unless they solve a concrete problem.

## Before changing code
- Summarize the task briefly.
- Identify relevant files, constraints, and risks.
- If the task is ambiguous, list the ambiguity and ask only the blocking questions.
- If the task is large or unclear, use plan mode first.
- If the task affects multiple files or shared contracts, make the impact explicit before editing.

## Python implementation rules
- Prefer explicit, readable Python over cleverness.
- Keep functions and classes small and cohesive.
- Use clear, domain-meaningful names.
- Use type hints in new or modified public interfaces when the project already uses them or when they improve clarity.
- Keep domain logic separate from I/O, framework code, and side effects.
- Avoid broad refactors unless they are required for correctness, clarity, or testability.
- Follow the existing project style before introducing new conventions.

## Testing rules
- Every meaningful behavior change should have automated validation or an explicit reason why it does not.
- Prefer fast, deterministic pytest tests.
- Cover happy path, edge cases, and expected failures when relevant.
- When fixing a bug, add or update a regression test.
- Use mocks or fakes only for external or non-deterministic dependencies.

## Error handling
- Do not hide errors silently.
- Distinguish expected exceptions from programming mistakes.
- Add useful context to errors and logs.
- Do not catch broad exceptions without a clear reason.

## Documentation
- Update docstrings, types, contracts, or README when behavior, usage, setup, or architecture changes.
- Document decisions that are not obvious from the code.
- Do not add redundant comments.

## Required checks before finishing
Before closing a task, verify:
- the goal is met;
- the scope stayed controlled;
- the code is readable;
- tests were added or updated when needed;
- remaining assumptions, risks, or follow-ups are explicit.

## Claude Code specific guidance
- Use plan mode for large, risky, or ambiguous changes.
- Use subagents only when they add real value, such as isolated review.
- Keep this file concise and actionable.
- If a rule needs deterministic enforcement, prefer hooks, permissions, or dedicated subagents instead of making this file longer.

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
