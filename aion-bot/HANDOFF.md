# Traspaso del proyecto (para una sesión de Claude que corra en el PC del usuario)

Lee este archivo entero antes de hacer nada. El usuario habla español.

## Qué es
Bot de leveling para **Aion 4.6 (servidor privado EUROaion)**, en Python + Tkinter, tema asmodiano.
Personaje: **Ranger asmodiano, nivel 13**, zona actual **Guardavieja** (niveles 10-19). Equipo muy fuerte (gear_power = 2).
El bot **lee la pantalla y pulsa teclas/clics** en la ventana activa. No lee memoria ni red, ni se va a hacer (anti-trampas/bans).
No implementar nada de speedhack, noclip, teletransporte, radar por memoria, inyección ni similares: el usuario ya lo pidió y se rechazó.

## Datos del PC del usuario (ya comprobados)
- Cliente: `C:\Program Files (x86)\EuroAion`, proceso `aion.bin`, ventana «Aion client 64».
- El Control inteligente de aplicaciones de Windows bloqueó algo en su día: NO le propongas desactivarlo sin explicar que es irreversible.
- Carpeta del bot: donde esté este archivo (junto a `app.py`, `config.json`, `INICIAR.bat`). Versión: ver `VERSION`.

## Estado (v1.8.1) y lo que hay
`engine.py` (cerebro), `app.py` (ventana), `skillbook.py` (auto-habilidades por icono), `monsters.py` (analizador y puntos de farmeo),
`guide.py`/`guide.json` (guía de leveling), `explorer.py`/`minimap.py` (exploración), `autoconfig.py` (detecta barras y barra de habilidades),
`vision.py` (vista de lo que ve el bot), `diagnostics.py`/`inputs.py` (prueba de movimiento, teclas por scancode),
`gamescan.py` (lee archivos del juego), `updater.py`/`launcher.py` (actualizaciones). Tests: `python -m unittest discover` (59 pasan).
Repo: rama `claude/nice-brahmagupta-5dfcf1` (carpeta `aion-bot/`).

## Lo que falta y el usuario quiere (se hace en SU PC)
1. **Actualizar el bot a la última versión conservando sus datos**: `config.json`, `knowledge.json`, `guide.json`, `skills_learned.json`,
   `monsters.json`, `routes.json`, `game_data.json`, `update.json`. No sobrescribir esos con los del zip. Hay `GUARDAR-EN-ESCRITORIO.bat` y `RESTAURAR-DESDE-ESCRITORIO.bat`.
2. **El personaje no se mueve**: ejecutar `diagnostics` (pestaña 🔧) o un script equivalente; probable causa: Aion como administrador vs bot normal, o teclas que
   solo aceptan scancode (`behavior.input_mode = "scancode"`). Comprobar también `behavior.game_window = "Aion client 64"`.
3. **Calibrar**: pestaña 👁 Vista → Capturar → ✨ Configurar automáticamente; o `python autoconfig.py captura.png --apply`. Revisar `autoconfig_preview.png`
   (puedes leer la imagen) y corregir `bars.*` y `hotbar` en `config.json`. Falta marcar a mano la barra de XP, el nombre del objetivo y el minimapa.
4. **Datos del juego**: `Npcs.pak`, `skills.pak`, `items.pak` son ZIP legibles (client_npcs.xml, client_skills.xml…); los textos están sueltos en
   `L10N\2_<idioma>\data\Strings\`. Ejecutar `gamescan` (extract_paks + copy_strings + import_dir) y comprobar si los XML salen legibles o codificados.
   Si están codificados haría falta AION-Encdec (herramienta de terceros con ejecutables cerrados; solo sobre copias en `game_work\PAK`, nunca Repack,
   nunca sobre la carpeta del juego, y avisar al usuario de pasar antivirus). Ajustar `gamescan.import_dir` al formato real.
5. Después: probar el bot unos minutos en un sitio seguro con el usuario delante.

## Cómo trabajar con él
Frases cortas, sin jerga. Pide aprobación antes de tocar nada fuera de la carpeta del bot. No ejecutes nada que mande teclas al juego sin avisar antes
(el personaje puede moverse). Los bots pueden estar prohibidos en EUROaion: el riesgo de ban es del usuario; no lo ocultes.
