# Bot de leveling para Aion (Asmodiano · Ranger) — tema asmodiano

Ventana con tema violeta/plata. El bot **mira tu pantalla** (barras de vida, maná y objetivo) y **simula teclas**;
no lee memoria del juego ni inyecta nada.

## Instalación (Windows)
1. Instala Python 3.11+ (con la opción *tcl/tk*, viene por defecto en python.org).
2. `pip install pyautogui pynput pillow`  (opcional, para leer el nivel: `pip install pytesseract` + instalar Tesseract OCR).
3. `python app.py`

## Primer uso
1. **Personaje**: nivel, zona actual y poder del equipo ("Muy fuerte" en tu caso).
2. **Habilidades**: pon en cada fila la tecla de TU barra de acceso rápido y ajusta cooldowns. Pociones al final.
3. **Calibración**: marca las barras de vida, maná y objetivo (esquinas sup. izq. e inf. der.). Pulsa *Probar lectura* y comprueba que los % coinciden.
4. **Batalla** → *Iniciar*. Tienes 5 s para poner Aion en primer plano (ventana o ventana sin bordes).

F10 pausa · F12 detiene · ratón a una esquina = parada de emergencia.

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
- Los rangos de zona de `knowledge.json` están escritos de memoria: verifícalos para EUROaion y edítalos.
- No sabe navegar el mapa ni esquivar; las rutas son pulsaciones grabadas (dependen de dónde empieces).
- El nivel solo se lee solo si instalas OCR; si no, súbelo tú a mano en *Personaje*.
- La interfaz no se ha probado visualmente en el entorno de desarrollo (sin pantalla); la lógica sí tiene tests: `python -m unittest test_engine`.
- Revisa las reglas de EUROaion sobre bots: el riesgo de ban es tuyo. Vigila los primeros 20-30 min antes de dejarlo de noche.
