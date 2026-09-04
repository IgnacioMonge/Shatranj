# Diario de partida — dossier de producto

Stage: spec
Mode ceiling: auto
Demand: Standard
Status: AT PRODUCT CHECKPOINT
Canonical dossier: `docs/game-journal-design.md`
Spec accepted: pending
Goal accepted: user, conversación 2026-08-14
Auto-advance milestones: no

## Objetivo

Cada partida genera incrementalmente en el almacenamiento local un historial
completo de movimientos comprometidos sin conservarlo en RAM. Al guardar, se
crea un `.STJ` que contiene ese historial y una instantánea final suficiente
para cargar inmediatamente la posición. La partida puede continuar y los
guardados posteriores incorporan los nuevos movimientos.

El valor para el jugador es conservar la partida completa sin aumentar la RAM
con la duración de la partida ni alterar el juego de red.

### Corte mínimo convincente

En Classic y Next, jugar una partida con movimientos locales, remotos y un
TAKEBACK; guardarla; verificar externamente que el `.STJ` contiene exactamente
esa secuencia; cargarlo y continuar jugando desde el tablero y los relojes
restaurados, con `RESTORED` como frontera visible en ambos jugadores.

### Fuera de alcance

- Recuperar automáticamente el temporal después de corte eléctrico, reset o
  cierre del programa.
- Cabeceras A/B, generaciones y checkpoints periódicos.
- Reproducir o navegar el historial completo en Spectrum.
- Restaurar las filas anteriores en la lista de movimientos de Spectrum.
- Generar PGN en Spectrum.
- Transferir el diario al rival durante RESTORE o cambiar el protocolo de red.
- Registrar timestamps por movimiento, chat, tráfico, retransmisiones,
  movimientos rechazados, DRAW, RESIGN o RESET.
- Cargar el formato provisional de 60 bytes. El nuevo `.STJ` v1 es el único
  formato de fichero soportado.

## Perfil de plataforma

### Targets y entrega

- Classic 48K: `SHATRANJ.tap`, `SHATRANJ.OVL` y `SHATRANJ.DAT`, con esxDOS.
- Spectrum Next: `SHATRANJ.nex`, usando el mismo contrato de fichero.
- Cliente Qt: mismo `.STJ` v1; implementación de almacenamiento propia.
- C99 y Z80 ASM para Spectrum; C++17/Qt para escritorio; sin dependencias
  nuevas.

### Restricciones

- Cada overlay continúa limitado a 2048 bytes y no se anidan overlays.
- El estado persistente residente del diario no debe crecer con la partida.
- Objetivo de BSS residente nuevo: como máximo 8 bytes para estado, contador,
  CRC y registro pendiente; debe demostrarse mediante artefactos enlazados.
- Un fallo de almacenamiento nunca cambia tablero, turno, resultado, ACK/NACK
  ni política de sesión.
- El I/O del diario no puede provocar retransmisiones, pérdida UART, caída de
  CTS, expiración de watchdog ni desconexión.
- DIRECT, MQTT y RESTORE siguen transmitiendo únicamente el estado de partida
  actual. El diario es persistencia local.

## Definiciones de producto

### Movimiento comprometido

Un MOVE entra en el diario exactamente una vez cuando ya forma parte del
tablero local:

- movimiento local: al aplicar el pendiente tras su ACK, o mediante la ruta
  equivalente que confirma implícitamente el movimiento;
- movimiento remoto: después de validarlo y aplicarlo, aunque falle el envío de
  su ACK posterior;
- duplicado o retransmisión: no añade registro;
- movimiento rechazado o todavía pendiente: no añade registro.

Un TAKEBACK aceptado añade `UNDO_ONE` exactamente una vez después de restaurar
el tablero. Una retransmisión del TAKEBACK no añade otro registro.

### Historial completo y parcial

`HISTORY_COMPLETE` significa que el cuerpo parte del comienzo real de la
partida y contiene todos sus MOVE y UNDO comprometidos.

El historial pasa a parcial si falla una escritura o si el estado procede de un
RESTORE remoto que no trae diario. Desde ese momento no se vuelve a declarar
completo durante esa partida. El tablero continúa siendo guardable y cargable.

### Ciclo de vida

1. Un GAME START confirmado declara una partida nueva con historial vacío, pero
   no toca todavía el fichero temporal.
2. El primer registro comprometido crea o trunca el temporal y lo escribe.
3. Los registros siguientes se añaden al mismo temporal.
4. Mate, ahogado, abandono, desconexión o vuelta a configuración conservan el
   diario de la partida terminada.
5. Un GAME START posterior cambia lógicamente a un historial nuevo; el temporal
   anterior solo se trunca cuando se compromete el primer registro nuevo.
6. Guardar una partida sin registros crea un `.STJ` válido con cuerpo vacío.
7. Cargar un `.STJ` copia su cuerpo válido al temporal antes de permitir la
   continuación. Si esa copia falla, se carga la posición y la continuación se
   marca como historial parcial.
8. Un peer que recibe únicamente el RESTORE de red carga la posición, pero su
   diario local comienza como parcial porque no recibió el historial anterior.

## Formato `.STJ` v1

No existe ruta de compatibilidad. Los enteros multibyte son little-endian.

```text
offset 0   cabecera fija, 76 bytes
offset 76  diario, 2 bytes por registro
EOF        exactamente 76 + record_count * 2
```

### Cabecera

| Rango | Tamaño | Contenido |
|---|---:|---|
| 0..3 | 4 | magic ASCII `STJ1` |
| 4 | 1 | versión, `1` |
| 5 | 1 | flags; bit 0 = `HISTORY_COMPLETE`, resto cero |
| 6..7 | 2 | tamaño de cabecera, `76` |
| 8..9 | 2 | número de registros |
| 10..11 | 2 | CRC-16 del diario |
| 12..13 | 2 | reservado, cero |
| 14..15 | 2 | CRC-16 de cabecera |
| 16..75 | 60 | estado restaurable Base64URL actual |

Ambos CRC usan CRC-16/CCITT-FALSE: polinomio `0x1021`, valor inicial `0xffff`,
sin reflexión y `xorout 0`. Para calcular el CRC de los bytes 0..75 de la
cabecera, los bytes 14..15 se consideran cero. El CRC de un diario vacío es
`0xffff`.

El estado Base64URL se conserva porque ya es el payload de RESTORE y ya tiene
codec compacto en Spectrum; no se conserva por compatibilidad con ficheros
anteriores.

La cabecera restaura tablero, turno, enroques, en-passant, color del host,
estado de partida, orientación y relojes. La lista de movimientos se reinicia y
muestra `RESTORED`, igual que el producto actual. Es una frontera deliberada:
la posición cargada no se presenta como si procediera de las filas visibles.
El jugador que carga y su oponente muestran lo mismo.

### Registro de 16 bits

MOVE, con bit 15 a cero:

```text
bits 0..5    casilla origen 0..63
bits 6..11   casilla destino 0..63
bits 12..14  promoción: 0 ninguna, 1 dama, 2 torre, 3 alfil, 4 caballo
bit 15       0
```

CONTROL, con bit 15 a uno:

```text
bits 0..3    opcode
bits 4..14   argumento
bit 15       1
```

En v1 solo existe `UNDO_ONE`, opcode 0 y argumento 0. Un valor de promoción,
opcode, argumento o bit reservado desconocido invalida el historial desde ese
registro, pero no invalida una instantánea de cabecera correcta.

## Temporal y guardado

El temporal contiene solo los registros del diario, sin cabecera. En Spectrum
usa un nombre 8.3 fuera del filtro `.STJ`, por ejemplo
`/SYS/CONFIG/SHATJRNL.TMP`.

Guardar es completamente secuencial:

1. Capturar el estado restaurable y los relojes mientras la aplicación no
   procesa otro movimiento.
2. Crear el destino `.STJ` y escribir sus 76 bytes de cabecera.
3. Copiar exactamente `record_count * 2` bytes del temporal al destino.
4. Cerrar y validar magic, campos, tamaño exacto y ambos CRC.
5. Mostrar éxito solo tras la validación; después continuar el mismo diario.

No se hace prepend, no se reescribe el temporal y no se necesita `F_SEEK` para
construir el `.STJ`. La estrategia de append del temporal queda condicionada a
la sonda: manejador persistente o `open/seek/write/close` por registro.

Si una escritura del diario falla o devuelve menos de dos bytes, se conserva el
último `record_count` y CRC válidos, se marca el historial parcial, se desactiva
el append durante esa partida y se notifica una sola vez. Los guardados
posteriores copian únicamente el prefijo válido y siguen restaurando el estado.

## Carga

1. Validar magic, versión, campos reservados, rangos, CRC de cabecera y payload
   restaurable.
2. Aplicar inmediatamente la instantánea, reiniciar la lista y mostrar
   `RESTORED`.
3. Validar longitud y CRC del diario para habilitar su continuación completa.
4. Copiar el cuerpo válido al temporal.

Una cabecera o estado inválidos rechazan la carga. Un diario inválido no impide
cargar una cabecera válida: se avisa y la continuación queda parcial. El host
puede enviar el payload de 60 bytes al peer mediante el RESTORE existente; el
diario no viaja por red y ambos conservan la presentación `RESTORED`.

## Criterios de aceptación

| ID | Tipo | Criterio | Verificación |
|---|---|---|---|
| AC-P-01 | Producto | El `.STJ` contiene en orden exactamente un registro por MOVE comprometido y por TAKEBACK aceptado. | Partida controlada y decodificador de referencia. |
| AC-P-02 | Producto | Guardar y cargar restaura tablero, turno, derechos, en-passant, color, estado, orientación y relojes; ambos jugadores ven únicamente `RESTORED` en la lista. | Comparación antes/después en Classic y Next, local y con peer. |
| AC-P-03 | Producto | Guardar a media partida no termina ni reinicia el diario; el siguiente guardado contiene también los movimientos posteriores. | Dos guardados de una misma partida. |
| AC-P-04 | Producto | Rechazos, pendientes y retransmisiones no duplican el historial; TAKEBACK lo revierte una sola vez. | Casos DIRECT y MQTT existentes ampliados con observación del journal. |
| AC-P-05 | Producto | Cualquier fallo de almacenamiento deja intactos juego y sesión, avisa una vez y permite guardar/cargar el snapshot como historial parcial. | Inyección de fallos open/write/short-write/close. |
| AC-P-06 | Producto | Cargar y continuar conserva el historial si el `.STJ` local es válido; un RESTORE remoto produce explícitamente historial parcial local. | Flujos local y de dos peers. |
| AC-T-01 | Técnico | Codec v1 rechaza tamaños, flags, registros, CRC y campos reservados inválidos sin leer fuera de límites. | Vectores host positivos, negativos y truncados. |
| AC-T-02 | Técnico | La captura se engancha después del commit real en todas las rutas local/remota/TAKEBACK. | Trazado de rutas y pruebas de sesión enfocadas. |
| AC-T-03 | Técnico | `SAVELOAD` permanece ≤2048 bytes; BSS nuevo ≤8 bytes; límites de residente, stack y overlays pasan. | Mapas enlazados, `make size-check` y reportes Next/NEX. |
| AC-T-04 | Técnico | El append no introduce retry, NACK, desconexión, overflow UART ni fallo CTS en 100 plies con red activa. | Sonda hardware Classic y Next, DIRECT y MQTT. |
| AC-T-05 | Técnico | El guardado valida tamaño y CRC del destino antes de informar éxito. | Fallos de copia y corrupción inyectada. |
| AC-T-06 | Técnico | Wire/session grammar, payload RESTORE de 60 bytes y semántica de ACK/NACK no cambian. | Transcripts y `make full-check`. |
| AC-T-07 | Técnico | Qt lee y escribe el mismo formato y corpus de registros. | `make client-test` con vectores compartidos. |

Todos los criterios están `NOT RUN` hasta implementación y evidencia fresca.

## Ledger de opciones

| Opción | Evidencia/coste esperado | Riesgo | Decisión |
|---|---|---|---|
| Temporal solo con registros; construir destino como cabecera + cuerpo | Elimina prepend, checkpoints, 1024 bytes reservados y seek de cabecera | Requiere copiar al guardar | **Hacer** |
| Cabecera reservada dentro del temporal | Solo aporta valor a recuperación tras corte, fuera de alcance | Más I/O, formato y estados | **Rechazar** |
| Cabeceras A/B y checkpoints | No ayudan al objetivo aceptado | Complejidad, CRC/generación y replay | **Rechazar en v1** |
| Registro de 2 bytes + CRC-16 final | 400 bytes para 200 plies; estado residente constante | No localiza corrupción intermedia | **Hacer** |
| CRC-8 dentro de cada registro | Añade 50 % al cuerpo y código por una recuperación no requerida | Coste recurrente | **Rechazar en v1** |
| `TIME_MARK` | Útil para análisis temporal futuro, no para historial de jugadas | Amplía semántica y pruebas | **Diferir** |
| Manejador persistente del temporal | Menos llamadas y menor latencia prevista | Durabilidad y coexistencia de handles no demostradas | **Medir en M0** |
| Abrir/seek/escribir/cerrar por registro | Mayor durabilidad prevista | Puede bloquear red y ACK | **Medir en M0** |
| Instantánea completa por jugada | Rama anterior llegó a 1989/2048 en SAVELOAD y +193 B BSS sin terminar | No conserva historial y presiona RAM/overlay | **Rechazar** |

Mismo comportamiento visible; menor coste total mediante temporal sin cabecera,
registros de 2 bytes, CRC único y reutilización del payload RESTORE existente.

## Evidencia

| ID | Afirmación | Clase | Riesgo | Ancla/frescura |
|---|---|---|---|---|
| E-01 | SAVELOAD ocupa 1240/2048; BSS 408; stack guard gap 1507 | VERIFIED | HIGH | `docs/size_report.baseline.json`, árbol 2026-08-14 |
| E-02 | El cargador Spectrum actual lee y escribe 60 bytes | VERIFIED | MEDIUM | `src/spectrum/overlay/saveload_ovl.c`, árbol 2026-08-14 |
| E-03 | Qt exige actualmente un fichero de 60 bytes | VERIFIED | LOW | `src/pc/client/save_game_store.cpp`, árbol 2026-08-14; se reemplazará, sin compatibilidad |
| E-04 | El commit local ocurre en `apply_pending_local_move`; el remoto antes de enviar ACK | VERIFIED | HIGH | `src/spectrum/app/app.c`, árbol 2026-08-14 |
| E-05 | La carga actual reinicia los logs y añade `RESTORED` en ambos peers | VERIFIED | MEDIUM | `src/spectrum/app/app.c`, árbol 2026-08-14 |
| E-06 | Latencia y durabilidad reales del append esxDOS con red viva | UNVERIFIED | BLOCKER | Requiere M0 en hardware |
| E-07 | Coexistencia segura de un handle persistente con carga de overlays | UNVERIFIED | HIGH | Requiere M0 y revisión ABI esxDOS |

## Milestones

| ID | Resultado inspeccionable | Puerta de finalización | Rollback | Estado |
|---|---|---|---|---|
| M0 | Sonda esxDOS compara las dos estrategias de append con red activa | E-06/E-07 resueltas y estrategia elegida sin violar AC-T-04 | Descartar sonda/worktree | PENDING |
| M1 | Classic y Next generan un temporal cuyo decoder reproduce MOVE/UNDO exactos | AC-P-01, AC-P-04, AC-T-01..04 | Revertir entradas y estado journal | PENDING |
| M2 | Spectrum guarda, valida, carga y continúa `.STJ` v1 | AC-P-02, AC-P-03, AC-P-05, AC-P-06, AC-T-05/06 | Revertir codec/entradas SAVELOAD | PENDING |
| M3 | Qt comparte formato, diario y corpus de pruebas | AC-T-07 y criterios de producto aplicables | Revertir persistencia Qt | PENDING |

## Tareas del hito M0

| ID | Tipo | Resultado | Dependencias | Superficie máxima | AC | Check | Estado |
|---|---|---|---|---|---|---|---|
| T-00 | SPIKE | Sonda descartable que escribe registros de 2 bytes mediante handle persistente y mediante open/seek/write/close | Especificación aceptada | Worktree descartable; wrapper esxDOS y telemetría mínima | AC-T-04 | Build Classic/Next y archivo decodificable | TODO |
| T-01 | VERIFY | Medir ambas estrategias con 100 plies en DIRECT y MQTT, Classic y Next | T-00 | Hardware y capturas externas | AC-T-04 | Cero fallos de sesión/UART; tabla de latencia | TODO |
| T-02 | SPIKE | Elegir estrategia y demostrar su coste enlazado antes de promover código | T-01 | Dossier y artefactos de la sonda | AC-T-03/04 | Mapas, tamaño, decisión y rollback | TODO |

## Decisiones y revisiones

- D-01: el objetivo aceptado es historial completo sin RAM más snapshot de
  carga; recuperación tras corte no forma parte de v1.
- D-02: no hay compatibilidad con el fichero provisional de 60 bytes.
- D-03: el temporal no lleva cabecera; el destino se construye secuencialmente.
- D-04: v1 registra jugadas y TAKEBACK, no tiempo ni otros eventos.
- D-05 / SPEC REVISION R-01: por decisión del usuario, cargar conserva la
  presentación actual `RESTORED` en ambos jugadores. Se eliminan de la cabecera
  las siete filas y `move_line_count`; no se amplía RESTORE para transmitirlos.

## Verificación y siguiente acción

- Revisión documental: pendiente tras esta especificación.
- Builds, tests, emulador y hardware: NOT RUN; no se ha autorizado código.
- Riesgo bloqueante de implementación: E-06, estrategia de append aún no medida.
- Siguiente acción: aceptar o revisar esta especificación. Después, preparar
  T-00 en worktree descartable; no modificar producto antes de la aceptación.
