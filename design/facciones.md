# Abyssbound — Sistema de Facciones

Decisión de diseño por defecto (ajustable): las facciones **sí afectan al
combate automático**, no son solo etiqueta narrativa — si luego prefieres que
empiecen siendo puramente narrativas y active el efecto mecánico más adelante,
es un cambio de una línea (desactivar el cálculo de sinergia).

## Principio base

- La **Facción** es un atributo independiente de la **Raza**. Cada personaje
  invocado tiene ambos: `raza` (Varkyn, Undead, Orco...) y `faccion` (una de las
  de abajo). Cualquier combinación raza×facción es válida.
- La facción se asigna de forma procedural al invocar, igual que la raza y el
  grado de potencial (E→SSS) — con pesos configurables por facción si luego
  quieres que unas sean más raras que otras.

## Las 4 facciones (propuesta de partida)

1. **El Dominio** (orden establecido) — disciplina, jerarquía, magia sagrada
   permitida. Bonus sugerido: +defensa cuando hay 2+ del Dominio en el grupo.
2. **Los Proscritos** (fuera de la ley / rebeldes) — libertad sobre estructura,
   tácticas sucias. Bonus sugerido: +crítico/sigilo en grupo.
3. **El Culto del Abismo** (ligado al Ritual/invocación, coherente con el
   nombre del juego) — poder a cambio de riesgo. Bonus sugerido: +daño mágico,
   -defensa en grupo (todo o nada).
4. **Los Errantes** (clanes/mercaderes sin bandera fija) — independencia,
   supervivencia. Bonus sugerido: +loot/recursos en grupo, sin bonus de combate
   directo.

Puedes renombrarlas o ajustar el lore sin tocar el sistema — mecánicamente solo
son 4 IDs con un modificador de grupo asociado.

## Cómo interactúa con combate automático

Como el jugador no controla directamente a los personajes, el valor de la
facción se expresa como **sinergia pasiva de grupo**, evaluada al formar el
equipo (no turno a turno):

- Se cuentan cuántos miembros del grupo (de hasta N) comparten facción.
- A partir de un umbral (sugerido: 2 de 4, o 3 de 6, según tamaño de grupo) se
  activa el bonus de esa facción.
- Un grupo totalmente mixto (sin mayoría) no tiene bonus de facción, solo los
  bonus de raza.

Esto le da sentido a elegir el grupo de invocados pensando en "¿formo un grupo
de una sola facción para el bonus, o mezclo por cobertura de roles?" — que es
justo el tipo de decisión estratégica que tiene sentido en un juego sin control
directo.

## Interacción con el Ritual de invocación

- El retrato/IA generado al invocar puede usar la facción como parte del
  prompt (paleta de color, simbología) además de la habilidad del personaje —
  así un Demonio del Culto del Abismo y un Demonio del Dominio se ven distintos
  aunque sean la misma raza.
- Grado de potencial (E→SSS) sigue siendo ortogonal: determina magnitud de
  stats; raza determina forma de stats; facción determina sinergia de grupo.

## Pendiente de confirmar contigo

- Nombres definitivos de las 4 facciones (las de arriba son placeholder).
- Si el bonus de facción debe mostrarse en la UI del grupo antes de entrar a
  la mazmorra (recomendado, para que la decisión estratégica sea visible).
