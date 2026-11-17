# Bot de leveling para Aion (Asmodiano · Ranger) — tema asmodiano

Ventana con tema violeta/plata. El bot **mira tu pantalla** (barras de vida, maná y objetivo) y **simula teclas**;
no lee memoria del juego ni inyecta nada.

## Instalación (Windows)
1. Instala Python 3.11+ (con la opción *tcl/tk*, viene por defecto en python.org).
2. `pip install pyautogui pynput pillow`  (opcional, para leer el nivel: `pip install pytesseract` + instalar Tesseract OCR).
3. `python launcher.py` (o doble click en `INICIAR.bat`). El launcher busca actualizaciones y abre el bot.

## Primer uso
1. **Personaje**: nivel, zona actual y poder del equipo ("Muy fuerte" en tu caso).
2. **Habilidades**: pon en cada fila la tecla de TU barra de acceso rápido y ajusta cooldowns. Pociones al final.
3. **Calibración**: marca las barras de vida, maná y objetivo (esquinas sup. izq. e inf. der.). Pulsa *Probar lectura* y comprueba que los % coinciden.
4. **Batalla** → *Iniciar*. Tienes 5 s para poner Aion en primer plano (ventana o ventana sin bordes).

F10 pausa · F12 detiene · ratón a una esquina = parada de emergencia.

## Auto-habilidades (pestaña ✦)
El bot puede **escanear tu barra de acceso rápido**, aprender qué hace cada habilidad y usarlas solo, incluidas las nuevas.
1. Pestaña *Auto-habilidades* → *Marcar mi barra* (esquinas de TODA la barra: todas las filas), indica columnas y filas, y en
   *Filas a ignorar* la de pergaminos/consumibles (1 = arriba).
   Por defecto el bot lanza cada habilidad con un **clic del ratón sobre su hueco**, así que NO necesitas conocer las teclas.
   (Si prefieres teclas, elige ese modo e indica teclas y modificadores por fila.) El ratón no debe usarse mientras corre el bot;
   si los clics caen desplazados, pon la escala de pantalla de Windows al 100 %.
2. *Escanear ahora*: detecta los iconos. Elige el modo: manual / mixto / totalmente automático.
3. Al combatir, cada habilidad desconocida se **prueba** (solo con tu vida ≥ 60 % y el objetivo con vida) y mide su efecto:
   baja la vida del enemigo más que el ataque básico → **daño**; te sube la vida → **curación**; nada → **utilidad** (no se usa sola).
4. Elige la de más daño medio cuando está lista (se ve por el icono: oscuro = enfriando), cura si tu vida < 50 %.
5. Si pones una habilidad nueva en la barra, se detecta y se prueba sola. Lo aprendido se guarda en `skills_learned.json`.
6. Corrígelo con *Forzar rol* (daño, curación, buff, ignorar) si se equivoca; los buffs y DoT suelen salir como "utilidad".
Antes de lanzar el bot pulsa *Escanear ahora* (no pulsa nada): verás los huecos detectados y podrás marcar como *Ignorar* los de
pociones u objetos que estén en las filas que sí usas.
Nunca toca las teclas de pociones ni las del sistema (Tab, botín, sentarse…). Necesita la barra de vida del objetivo calibrada.

## Analizador de monstruos y puntos de farmeo (pestañas 🐺 y 🗺)
- Calibra además la **barra de experiencia** y la **región del nombre del objetivo** (el nombre se lee por OCR: instala Tesseract y `pip install pytesseract`).
- Tras cada muerte mide XP ganada, tiempo y vida perdida → XP/min por monstruo. Descarta los que rinden poco o son peligrosos (ajustable).
- **Puntos de farmeo**: crea uno por cada sitio, graba su *patrulla* (recorrido que repite si no hay enemigos) y las rutas entre ellos
  (`A->B`). El bot los prueba 5 min cada uno y se queda en el de más XP/min.
- **Plan de farmeo**: nivel desde el que ir a cada zona; con rutas grabadas (`Zona->Zona`) cambia de mapa solo.
- No conoce el mapa: se mueve repitiendo lo que grabaste. Si no hay patrulla, da pasos cortos y avisa si pasa mucho sin matar.

## Launcher y actualizaciones
`python launcher.py` comprueba `update.json` (repo, rama, token si el repositorio es privado). Si hay versión nueva te la enseña
y pregunta antes de instalar. Solo reemplaza código; **no toca** tu config, lo aprendido, monstruos ni rutas, y deja copia en `_backup/`
(`python launcher.py --rollback` o el botón *Revertir*). Solo apunta `update.json` a un repositorio de tu confianza: se ejecuta su código.

## Guía de leveling (pestaña 📖)
`guide.json` contiene una ruta por tramos de nivel (zonas, misiones, instancias) reunida de guías de la comunidad de EuroAion 4.6.
Donde se puede farmear (1-8 Ishalgen, 10-20 Altgard, 21-26 Morheim) el bot va solo a esa zona; donde la guía manda misiones o
instancias (ascensión al 9, campañas, Alquimia, Adma, Balaur Temple…) el bot no puede, así que te avisa y se pausa (o sigue farmeando, a tu elección).
Las guías son antiguas y no pude abrir los temas completos del foro: contrasta los tramos y edita `guide.json`.

## Vista: lo que ve el bot (pestaña 👁)
El bot no se conecta al juego: mira la pantalla y pulsa teclas/clics en la ventana activa. Por eso Aion debe verse completo (ventana o
ventana sin bordes), sin nada encima, y estar en primer plano. En *Vista* pulsa *Capturar*, pon Aion delante y verás tu pantalla con lo detectado
dibujado encima y un informe (✔ bien, ⚠ aviso, ✖ error). Después usa *Usar esta ventana como la del juego*: así el bot deja de pulsar si Aion no está activo.

## Diagnóstico: el personaje no se mueve (pestaña 🔧)
Con Aion en primer plano y en un sitio seguro, *Probar movimiento* mantiene `W` con dos métodos (normal y por scancode), mira si la imagen cambia
y activa el que funciona. Si ninguno mueve al personaje: ejecuta el bot como administrador (clic derecho en INICIAR.bat) si Aion va como
administrador, usa modo ventana/sin bordes y revisa que `W` sea tu tecla de avanzar.

## Configuración automática (✨ en la pestaña Vista)
Con Aion delante, vida y maná llenos, un enemigo seleccionado con vida llena y la barra de habilidades visible: *Capturar* → *Configurar automáticamente*.
Detecta solo las barras de vida, maná y objetivo (por su color) y la barra de habilidades (columnas y filas). Revisa el resultado en la misma vista.
La barra de experiencia y el nombre del objetivo se marcan a mano en Calibración. También funciona desde una captura guardada: `python autoconfig.py captura.png --apply`.

## Qué decide el bot
- **Habilidades**: por prioridad (orden de la lista), respetando cooldowns, maná mínimo, apertura (una vez por combate),
  remate (objetivo ≤ X %) y defensiva (mi vida ≤ X %). Si nada está listo, ataque básico.
- **Pociones**: vida y maná por umbral + cooldown. Con equipo fuerte el umbral de vida baja 10 % por nivel de poder.
- **Descanso**: se sienta fuera de combate si la vida baja y se levanta al recuperarse.
- **Botín**: tras morir el objetivo.
- **Atascos**: si el objetivo no pierde vida en 20 s, lo descarta.
- **Muerte**: si la vida marca 0 un rato, pausa y avisa.
- **Sin enemigos**: reintenta Tab, se mueve un poco y avisa si lleva 3 min sin matar nada.
- **Cambio de zona**: compara tu nivel (+ bonus de equipo) con `knowledge.json` y avisa/pausa cuando toca otra zona.
  Si grabaste una ruta (pestaña *Rutas*) y activaste "ejecutar ruta", la hace sola.

## Límites honestos
- Los rangos de zona de `knowledge.json` están escritos de memoria y NO verificados para la 4.6 de EUROaion: comprueba el nivel recomendado de cada zona en el juego y edítalos.
- No sabe navegar el mapa ni esquivar; las rutas son pulsaciones grabadas (dependen de dónde empieces).
- El nivel solo se lee solo si instalas OCR; si no, súbelo tú a mano en *Personaje*.
- El reconocimiento de iconos se ha probado con imágenes sintéticas, no con la barra real de Aion: usa *Escanear ahora* y comprueba que cuenta bien tus habilidades antes de lanzar el bot.
- La interfaz no se ha probado visualmente en el entorno de desarrollo (sin pantalla); la lógica sí tiene tests: `python -m unittest discover`.
- Revisa las reglas de EUROaion sobre bots: el riesgo de ban es tuyo. Vigila los primeros 20-30 min antes de dejarlo de noche.
