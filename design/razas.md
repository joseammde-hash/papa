# Abyssbound — Razas nuevas

Documento de diseño para las razas añadidas al roster original de 10. Pensado para
encajar con el sistema de invocación procedural (grado E → SSS) y el combate
automático por grupo.

Estado: borrador de trabajo. La raza marcada como `TBD` queda pendiente de que
me digas cuál era — avísame y la rellenamos.

---

## Varkyn (corrección de "Lycan")

- **Concepto**: semihumanos con rasgos bestiales, no monstruos puros. Mantienen
  forma humanoide base; la "forma animal" es un rasgo cosmético/mecánico que varía
  por individuo, no una raza distinta por animal.
- **Pool de formas bestiales** (elegible al generarse el personaje, procedural):
  lobo, zorro, oso, jabalí, águila, serpiente, lince, cuervo. Cada forma da un
  ligero sesgo de stats y una animación/retrato distintos, pero comparten el
  mismo esqueleto 2.5D base — así no se multiplica el trabajo de arte.
- **Rol de combate sugerido**: híbridos ágiles, buenos en daño físico sostenido;
  la forma bestial decide si el sesgo es velocidad (lobo/zorro/águila), resistencia
  (oso/jabalí) o crítico/sigilo (lince/serpiente/cuervo).
- **Gancho narrativo**: tribus Varkyn ligadas a un territorio/clan, no a una sola
  facción — un mismo clan puede tener miembros en facciones distintas.

## Undead

- **Concepto**: personajes que murieron y fueron reanimados (no monstruos
  genéricos — cada Undead invocado tiene una "vida anterior" generada
  proceduralmente, igual que las demás razas).
- **Rasgo distintivo**: inmunes a efectos de veneno/sangrado; vulnerables a
  magia de luz/sagrada. Cura mediante magia oscura o maná en vez de HP estándar
  en algunas builds (opcional, a decidir si se implementa como regla especial).
- **Rol de combate sugerido**: tanque/control — alta resistencia física, baja
  resistencia a lo sagrado. Buenos como "ancla" del grupo en el crawler.
- **Gancho narrativo**: encajan bien como la raza con más presencia en una
  facción "prohibida" o "al margen de la ley" (ver Facciones).

## Demonios

- **Concepto**: entidades del Abismo (coherente con el nombre del juego),
  invocadas igual que el resto pero con un origen de poder distinto: pactos,
  no linaje.
- **Rasgo distintivo**: fuerte en magia ofensiva y daño elemental (fuego/caos);
  penalización de defensa física para compensar.
- **Rol de combate sugerido**: DPS mágico de alto riesgo/alta recompensa.
- **Gancho narrativo**: ligados temáticamente al "Ritual" de invocación que ya
  existe en el juego — un Demonio invocado puede tener lore sobre *qué* se pagó
  para traerlo.

## Orcos

- **Concepto**: raza guerrera, físicamente dominante, cultura de clanes y honor
  en combate.
- **Rasgo distintivo**: bonus de daño cuando pelean en grupo (sinergia con el
  combate automático por grupo: un grupo con 2+ Orcos gana un modificador).
- **Rol de combate sugerido**: tanque/bruiser de línea frontal.
- **Gancho narrativo**: clanes orcos pueden estar repartidos entre varias
  facciones — el honor de clan pesa más que la bandera política.

## Goblins

- **Concepto**: pequeños, numerosos, ingeniosos; contraparte ágil/utilitaria de
  los Orcos.
- **Rasgo distintivo**: mayor tasa de drops/loot o de crítico en combate
  automático (encajan bien como raza "económica" del roster); baja HP.
- **Rol de combate sugerido**: DPS a distancia (trampas, alquimia, arcos) o
  soporte (debuffs, robo de objetos).
- **Gancho narrativo**: buenos como raza dominante de una facción mercantil o
  de saqueadores independiente del bien/mal.

## Minotauros

- **Concepto**: raza grande, de fuerza bruta y vínculo con laberintos/dungeons
  (temáticamente perfectos para un dungeon-crawler).
- **Rasgo distintivo**: daño de área en el primer golpe de cada combate (carga);
  movimiento algo más lento en exploración.
- **Rol de combate sugerido**: rompedor de formaciones / daño en área.
- **Gancho narrativo**: ligados a las propias mazmorras del juego — podrían ser
  la raza con lore de "guardianes" que ahora pelean para el jugador.

## `TBD` — raza pendiente

Falta el nombre/concepto de la séptima raza que mencionaste. En cuanto me la
digas la documento igual que las anteriores.

---

## Resumen de roles (para balance rápido)

| Raza       | Rol principal       | Rasgo clave                          |
|------------|----------------------|---------------------------------------|
| Varkyn     | Híbrido ágil         | Forma bestial variable (stats/retrato)|
| Undead     | Tanque/control        | Inmune veneno/sangrado, débil a luz   |
| Demonios   | DPS mágico            | Alto daño elemental, baja defensa     |
| Orcos      | Tanque/bruiser        | Bonus en grupo (2+ Orcos)             |
| Goblins    | DPS/soporte ligero    | Más loot/crítico, baja HP             |
| Minotauros | Rompedor de formación | Daño de área al iniciar combate       |

Todas las razas son compatibles con el grado de potencial E→SSS existente: el
grado sigue siendo independiente de la raza (determina la magnitud de las
stats), la raza determina la *forma* de esas stats (a qué tira cada una).
