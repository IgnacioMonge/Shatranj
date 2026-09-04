# Auditoría Z80 completa

Fecha: 2026-08-31  
Commit auditado: `e71d7fb` (`main`, limpio al iniciar)  
Modo: `audit-z80 full` + `workflow heavy`  
Ámbito: todo NetChessZX; Classic, Next TAP, `.nex`, SpectraNext, C común, ASM, overlays, ABI, mapas, firmware, herramientas, tests y artefactos generados.  
Contrato: auditoría de solo lectura. Las únicas mutaciones fueron dos vectores de prueba en un worktree desechable; no se modificó código de producto.

## Hallazgos

### [RETRACTED] A-01 — El stride de sprites Next ya era correcto

- Type: `FALSE POSITIVE`
- File: `asm/next/graphics_bank_next.asm:160`
- Confidence: `PROVEN RETRACTION`
- What: la aritmética se leyó mal durante la auditoría. La secuencia calcula `index * 3072` correctamente.
- Evidence: parte de `index * 256`, hace dos dobles hasta `index * 1024`, copia ese valor a `DE`, dobla `HL` una vez más hasta `index * 2048` y suma `DE`: total `index * 3072`. Coincide con `next_sprite_set_size EQU 3072`.
- Impact: ninguno; no existía corrupción de sprites por este camino.
- Fix: ningún cambio de producto. Se añadió una prueba estructural que enlaza aritmética, tamaño de juego, offsets 0/3072/6144 y límites del bundle.
- Cost: sólo test; 0 bytes y 0 ciclos.
- Hardware/toolchain note: afecta al camino de sprites hardware de ZX Spectrum Next; Classic y SpectraNext no ejecutan esta rutina.

Offsets correctos demostrados:

| Índice | Esperado | Actual | Región |
|---:|---:|---:|---|
| 0 | 0 | 0 | juego 0 |
| 1 | 3072 | 3072 | juego 1 |
| 2 | 6144 | 6144 | juego 2 |

### [HIGH] A-02 — DIRECT puede ensamblar una línea con fragmentos de dos conexiones distintas

- Type: `BUG`
- File: `src/spectrum/overlay/direct_ovl.c:395`
- Confidence: `LIKELY`
- What: en modo servidor `CIPMUX=1`, `direct_rx_payload_len` conserva una línea TCP parcial entre bloques `+IPD`, pero la identidad del enlace no se conserva con esa línea. El siguiente encabezado sobrescribe `direct_ipd_link`.
- Evidence: `direct_parse_ipd_header_ovl` asigna el enlace actual en `direct_ipd_link` (`:443`); `direct_feed_payload_byte_ovl` mantiene el parcial cuando termina el bloque sin `\n` (`:473-478`); `direct_queue_payload_ovl` atribuye la línea terminada al último `direct_ipd_link` (`:382-389`). Un vector desechable reprodujo: `+IPD,0,13:HELLO DIRECT ` seguido de `+IPD,1,6:GUEST\n` deja una única línea `HELLO DIRECT GUEST` atribuida al enlace 1. El ejecutable de prueba falla exactamente en esa invariante; el test normal de fragmentación en el mismo enlace sigue verde.
- Impact: antes de fijar `active_link`, dos clientes simultáneos pueden mezclar sus fragmentos. El segundo puede completar el `HELLO` del primero, ganar una sesión equivocada o provocar fallo de conexión/reconexión. No se observó corrupción de memoria.
- Fix: asociar el parcial a un `direct_partial_link` válido. Si llega un nuevo bloque aceptado de otro enlace con parcial no vacío, descartar el parcial; conservar la reagrupación para el mismo enlace. Limpiar metadatos al encolar, descartar o reiniciar.
- Cost: 1–2 bytes residentes si el estado permanece residente, más bytes en `DIRECT`; medir antes de aceptar porque el overlay Classic tiene 151 bytes libres y el camino Next TAP sólo 151, pero SpectraNext usa otra implementación. Alternativa sin RAM: reservar un byte ya ocioso del estado, si se demuestra su exclusividad.
- Hardware/toolchain note: Espressif documenta `+IPD,<link_id>,<length>:<data>` para `CIPMUX=1`; el `link_id` es la identidad de conexión. No documenta una garantía que impida bloques consecutivos de enlaces distintos. Fuente: https://docs.espressif.com/projects/esp-at/en/latest/esp32/AT_Command_Set/TCP-IP_AT_Commands.html

### [MEDIUM] A-03 — El gate canónico `make full-check` está roto en un checkout limpio

- Type: `BUG`
- File: `tools/check_overlay_entry_abi.py:336`; `docs/overlay_capabilities.json`
- Confidence: `PROVEN`
- What: dos validadores no se actualizaron junto con cambios válidos del código.
- Evidence: `make full-check` falla antes de completar:
  - `check_overlay_entry_abi.py` exige aún `ld hl,_netchesszx_mqtt_code`, pero la edición correcta empieza en `+2` para los cuatro dígitos configurables; también omite `ld hl,_setup_port_text` en el control PORT independiente. La implementación actual está en `asm/overlay/setup/entry_setup.asm:790-810`.
  - la política de capabilities no permite las importaciones XFS/ESXDOS condicionales de `ABOUT` (`_esx_fopen`, `_esx_fclose`, `_esx_handle`, `_spxn_xfs_fseek`) ni el uso ya existente de `spectrum_append_text` por `CONFIG`.
- Impact: el gate de release produce falsos negativos y no puede certificar el commit actual. Esto oculta regresiones reales entre ruido de infraestructura.
- Fix: actualizar las secuencias esperadas del ABI checker y modelar las capabilities reales/condicionales de `ABOUT` y `CONFIG`; después ejecutar `make full-check` completo.
- Cost: sólo herramientas/documentación; 0 bytes de binario y 0 ciclos.
- Hardware/toolchain note: no es un fallo del ABI enlazado: `make abi-check`, layering y el resto de guards pasan; es divergencia entre política y producto.

### [MEDIUM] A-04 — `session-spectrum-pair-test` conserva un estado imposible y falla fuera del gate normal

- Type: `BUG`
- File: `tests/spectrum/test_session_spectrum_pair.c:42`
- Confidence: `PROVEN`
- What: el fixture configura un guest DIRECT pero no reinicia `netchesszx_host_color_ready`. El estado global previo queda en 1 y la protección de coherencia rechaza el `HELLO` válido del host.
- Evidence: el target falla con `FAIL: direct Spectrum guest accepts host hello`. Producción borra el flag al iniciar JOIN en `src/spectrum/app/app.c:751-753`; el test unitario directo ya hace lo mismo en `tests/spectrum/test_session_direct.c:60-64`. La nueva validación correcta está en `src/spectrum/session/direct.c:49-52`.
- Impact: falso negativo en un target explícito y pérdida de cobertura efectiva del emparejamiento Spectrum/Spectrum. No demuestra un fallo runtime.
- Fix: hacer que el fixture ejecute la transición productiva o, como mínimo, poner `netchesszx_host_color_ready = 0` al configurar JOIN. Integrar este target en el gate canónico para evitar nueva deriva.
- Cost: sólo test; 0 bytes y 0 ciclos.
- Hardware/toolchain note: reproducido en host; no requiere emulador.

### [LOW] A-05 — El `.nex` tiene sólo 218 bytes sobre el suelo duro de stack

- Type: `OBSERVATION`
- File: `build/size_report.json`
- Confidence: `PROVEN`
- What: el artefacto `.nex` deja `SP_GAP=730`; tras reservar 512 bytes, `STACK_GAP=218` según el criterio del generador. Está por debajo del aviso de 768, aunque aún supera el mínimo duro de 512.
- Evidence: build fresco y `make next-size-report`; no se usó el resumen genérico del mapa para este valor porque el BSS fijo bajo induce una interpretación incorrecta.
- Impact: no hay overflow demostrado, pero cambios residentes/BSS o mayor profundidad de llamada tienen margen pequeño.
- Fix: mantener `make size-check` obligatorio para cualquier cambio residente/ABI y medir high-water de stack en emulador/hardware antes de una release Next.
- Cost: instrumentación temporal; sin coste en release.
- Hardware/toolchain note: el peor caso dinámico de interrupción/cadena de llamadas sigue sin medición física.

### [MEDIUM] A-06 — Classic no sondea RTC cuando la configuración activa contiene UTC

- Type: `BUG`
- File: `src/spectrum/app/app.c:495`; `src/spectrum/config/session.c:68`; `src/spectrum/overlay/config_ovl.c:49`
- Confidence: `PROVEN`
- What: el probe Classic sólo se ejecuta si `netchesszx_timezone` ya vale RTC, pero el estado y los defaults arrancaban en UTC. Por ello `netchesszx_rtc_available` seguía a cero y el menú ocultaba RTC incluso en hardware compatible.
- Evidence: MirrorShift usa el mismo probe y menú, pero inicia RTC y lo vuelve a seleccionar tras cargar la configuración. El backend prueba la capacidad; si falla, restaura `netchesszx_timezone_last`. El menú sólo consulta `netchesszx_rtc_available`, sin identificar plataformas.
- Impact: RTC funcional pero no visible ni seleccionable desde TIME en Classic. UTC continuaba funcionando.
- Fix: replicar el contrato de MirrorShift: RTC como selección de arranque/default, probe durante preflight y fallback numérico ya existente. Mantener la UI estrictamente gobernada por la capacidad detectada.
- Cost: cambio de inicializadores/constantes sin RAM nueva ni ABI nuevo; el probe de arranque ya existía.
- Hardware/toolchain note: la disponibilidad real sigue determinada por los probes de driver API, `M_GETDATE` y PCF8563; SpectraNext informa ausencia desde su backend.

## Veredicto

Tras corregir el falso positivo A-01 y añadir el defecto RTC observado después de la auditoría, quedan 2 defectos de producto, 2 defectos de validación y 1 riesgo medido. No se hallaron violaciones demostrables de ABI C/ASM, balance de stack, IY, DI/EI, memoria fija, slot de overlays ni descompresión ZX0 en los artefactos actuales.

Prioridad de reparación:

1. A-02: impedir mezcla de fragmentos DIRECT entre enlaces y conservar fragmentación del mismo enlace.
2. A-06: aplicar el probe/default/fallback RTC de MirrorShift sin lógica de plataforma en la UI.
3. A-03: restaurar `make full-check` como señal fiable.
4. A-04: corregir el fixture e incorporar el target al gate.
5. A-05: medir high-water de stack Next antes de release.

## Matriz original de validación

| Comando | Resultado | Evidencia |
|---|---|---|
| `make test` | PASS | tests host, protocolo, sesión, ASM vectors, GUI; paridad MQTT Spectrum 64/64 |
| `make rules-oracle` | PASS | 205 comprobaciones de movimientos; 416 de perft |
| `make abi-check size-check` | PASS | Classic y Next frescos; ABI y límites actuales |
| `make next-size-report` | PASS | mapa `.nex` y márgenes actuales |
| `make spectranext-port-build SPXN_DIR=C:/dev/SpectraNext/driver` | PASS | puerto SpectraNext enlazado |
| `make spectranext-conformance-test` | PASS | 10 pruebas; paridad DIRECT |
| `make layering-check` | PASS | capas/importaciones estructurales |
| guards restantes individuales | PASS | transporte, IDs MQTT, políticas DIRECT, límites de sesión |
| `make overlay-entry-abi-check` | FAIL conocido | A-03: expectativas obsoletas |
| `make full-check` | FAIL conocido | A-03: capabilities/ABI checker obsoletos |
| `make session-spectrum-pair-test` | FAIL conocido | A-04: fixture obsoleto |
| vector desechable inter-link DIRECT | FAIL esperado | A-02 reproducido; no se conservó el parche |

## Estado tras corrección

- A-01: retractado; producción no cambió. `test_next_graphics_bank.py` demuestra stride 3072 y límites de los tres juegos.
- A-02: corregido sin estado/RAM adicional. Un bloque aceptado de otro enlace descarta el parcial anterior; un intruso rechazado no destruye el parcial del enlace activo.
- A-03: corregidas las expectativas de edición ROOM/PORT y las capabilities reales de ABOUT/CONFIG. `make module-guards` pasa completo.
- A-04: fixture JOIN reiniciado correctamente y `session-spectrum-pair-test` incorporado a `make test`.
- A-06: aplicado el patrón RTC de MirrorShift: selección inicial RTC, probe por backend, `rtc_available` como única capacidad visible y fallback a `timezone_last`.
- Validación posterior: suite host completa, `module-guards`, `spectranext-clock-test` y `spectranext-config-test`, todos PASS. No se reejecutaron builds de tamaño/release; no hubo cambios de ABI ni RAM declarada.

Toolchain observado: z88dk `zcc v24860-762578732c-20260630`; host Windows 11/pwsh 7. Los builds se ejecutaron en worktree desechable detached mediante el runner canónico de skills.

## Tamaño y presión medidos

| Target | Resident | BSS | SP gap | Stack tras reserva | OVL | DAT |
|---|---:|---:|---:|---:|---:|---:|
| Classic | 34966 | 424 | 1306 | 962 | 26066 | 7148 |
| Next TAP | 35065 | 424 | 1206 | 862 | 26599 | 7148 |
| `.nex` | 35442 | 523 | 730 | 218 | 26270 | 1964 |
| SpectraNext | 35899 | 272 | 773 | 261 | 25896 | 7148 |

Overlays más presionados, todos con límite 2048:

| Target/overlay | Bytes | Libres |
|---|---:|---:|
| SpectraNext `CONFIG` | 2033 | 15 |
| `SETUP` (todos) | 2021 | 27 |
| Next TAP `MQTT_TX` | 1999 | 49 |
| SpectraNext `TIME` | 2000 | 48 |
| `TIME_CONFIG` | 1913 | 135 |
| Classic/Next `DIRECT` | 1897 | 151 |

## Cobertura

- ABI: entradas de overlay, convenciones SDCC/z88dk, packed/fastcall/callee, preservación IX/IY, RST 8, retorno y stack.
- Memoria: mapas frescos de cuatro targets, BSS, low RAM fija, stack, slot `$6800`, scratch `$672B`, contexto `$5FE0`, bancos/MMU y expansión ZX0.
- Concurrencia/hardware: DI/EI, IM1, HALT, UART Classic/Next, I2C/RTC, esxDOS/XFS, sprites Next y atributos/pantalla.
- Semántica: reglas, protocolo, MQTT, DIRECT, sesiones, save/load/CRC, configuración, input, colas y timeouts.
- Toolchain: fuentes C/ASM, generated ASM/maps/manifests y guards del proyecto.
- Investigación externa limitada a contratos oficiales de ESP-AT y z88dk. z88dk confirma que `sdcc_iy` reserva IY; los sitios RST 8 del proyecto guardan/restauran IY y `check_sdcc_iy_contract` pasa. Fuentes: https://github.com/z88dk/z88dk/blob/master/lib/config/zx.cfg y https://www.z88dk.org/wiki/doku.php?id=libnew:examples:sp1_ex1

## Candidatos rechazados

- `DI; RET` del dispatcher: `RET` transfiere al overlay; la salida común `ovl_return` ejecuta `EI; RET`. No es retorno con interrupciones perdidas.
- RST 8/IY: todos los sitios Classic inspeccionados preservan IY; el contrato automático pasa.
- Inline ASM de MQTT/RTC: los registros necesarios se preservan y los probes ABI actuales pasan.
- `LDIR/LDDR` con `BC=0`: no apareció una ruta alcanzable en los sitios de producto.
- Alias SpectraNext `_line_buf/$5B00`–`_spxn_regs`: alias de enlace con consumidores mutuamente excluyentes; no hay solapamiento runtime probado.
- Carry indeterminado del copiador Next con longitud cero: las llamadas actuales usan longitudes no nulas.
- Overflow decimal de `+IPD`: exigiría un encabezado malformado producido por firmware/ruido; sin ruta de producto demostrada.
- Resumen genérico de stack SpectraNext: falso positivo por BSS fijo bajo; se usaron los valores del generador específico.

## Límites residuales

- No se ejecutó hardware físico ni FuseX automatizado con captura visual; A-01 debe confirmarse en Next real/emulador tras corregirlo.
- No hay high-water dinámico de stack; A-05 se basa en límites estáticos enlazados.
- La documentación oficial ESP-AT define identidad/longitud de cada `+IPD`, pero no promete no alternar conexiones; A-02 queda `LIKELY` pese al reproducer determinista del parser.
- El `full-check` completo no puede terminar hasta reparar A-03; se ejecutaron por separado todos los gates independientes disponibles.
