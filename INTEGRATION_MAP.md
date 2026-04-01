# INTEGRATION_MAP.md
# Mapa de dependencias entre módulos del proyecto
#
# INSTRUCCIONES PARA CLAUDE CODE:
# - Leer este fichero al inicio de cada sesión antes de tocar ningún módulo.
# - Si durante el desarrollo se detecta una nueva dependencia entre módulos,
#   añadir la entrada correspondiente antes de cerrar la tarea.
# - Si se modifica un módulo que aparece en alguna relación registrada aquí,
#   ejecutar también los tests de integración indicados en esa entrada.
# - No eliminar entradas existentes sin confirmación explícita del desarrollador.
# - Mantener las entradas ordenadas alfabéticamente por nombre del primer módulo.
# =============================================================================

---

## Cómo leer este fichero

Cada bloque describe una relación entre dos o más módulos:

- **Tipo de relación**: cómo se relacionan técnicamente
  - `llamada directa` — un módulo importa y llama funciones del otro
  - `datos compartidos` — ambos leen/escriben sobre la misma estructura o recurso
  - `herencia` — una clase extiende a otra de otro módulo
  - `evento` — uno emite eventos que el otro consume
- **Dirección**: quién depende de quién (`A → B` significa A depende de B)
- **Test de integración**: fichero que valida el comportamiento conjunto
- **Tests a ejecutar si se modifica**: lista completa de tests afectados

---

## Relaciones registradas

### run_batch ↔ run_rule_extractor
- Tipo de relación  : llamada directa (subprocess)
- Dirección         : run_batch → run_rule_extractor
- Descripción       : run_batch lanza run_rule_extractor.py como subprocess por cada símbolo activo
- Ficheros          :
    src/run_batch.py
    src/run_rule_extractor.py
- Test de integración: tests/integration/test_run_batch_run_rule_extractor.py
- Tests al modificar run_batch.py:
    pytest tests/unit/test_run_batch.py -v
    pytest tests/integration/test_run_batch_run_rule_extractor.py -v
- Tests al modificar run_rule_extractor.py:
    pytest tests/unit/test_run_rule_extractor.py -v
    pytest tests/integration/test_run_batch_run_rule_extractor.py -v
- Detectado en tarea: implementacion del batch runner
- Fecha             : 2026-03-31

<!-- Las entradas se añaden aquí conforme se detectan dependencias.          -->
<!-- Usar la plantilla de bloque definida al final de este fichero.          -->
<!-- Ejemplo de entrada real:                                                 -->
<!--                                                                          -->
<!-- ### auth ↔ db                                                            -->
<!-- - Tipo de relación  : llamada directa                                    -->
<!-- - Dirección         : auth → db                                          -->
<!-- - Descripción       : auth.login() consulta usuarios a través de db      -->
<!-- - Ficheros          :                                                     -->
<!--     src/auth.py                                                           -->
<!--     src/db.py                                                             -->
<!-- - Test de integración: tests/integration/test_auth_db.py                 -->
<!-- - Tests al modificar auth.py:                                            -->
<!--     pytest tests/unit/test_auth.py -v                                    -->
<!--     pytest tests/integration/test_auth_db.py -v                          -->
<!-- - Tests al modificar db.py:                                              -->
<!--     pytest tests/unit/test_db.py -v                                      -->
<!--     pytest tests/integration/test_auth_db.py -v                          -->
<!-- - Detectado en tarea: implementación de login con JWT                    -->
<!-- - Fecha             : 2025-01-15                                          -->

---

## Plantilla de bloque

```
### <módulo_a> ↔ <módulo_b>
- Tipo de relación  : <llamada directa | datos compartidos | herencia | evento>
- Dirección         : <módulo_a> → <módulo_b>
- Descripción       : <qué hace uno respecto al otro, en una línea>
- Ficheros          :
    src/<ruta/módulo_a.py>
    src/<ruta/módulo_b.py>
- Test de integración: tests/integration/test_<módulo_a>_<módulo_b>.py
- Tests al modificar <módulo_a>.py:
    pytest tests/unit/test_<módulo_a>.py -v
    pytest tests/integration/test_<módulo_a>_<módulo_b>.py -v
- Tests al modificar <módulo_b>.py:
    pytest tests/unit/test_<módulo_b>.py -v
    pytest tests/integration/test_<módulo_a>_<módulo_b>.py -v
- Detectado en tarea: <descripción breve de la tarea donde se descubrió>
- Fecha             : <YYYY-MM-DD>
```