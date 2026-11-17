# Novedades

## 1.6.1
- El buscador reconoce clientes de servidores privados (carpetas tipo EUROaion sin aion.bin) y mira también Escritorio y Descargas.

## 1.6.0
- Pestaña 📂 Archivos del juego: busca tu carpeta de Aion, la escanea (solo lectura), extrae los .pak legibles e importa nombres y niveles de monstruos y habilidades.
- El bot descarta monstruos muy por debajo o por encima de tu nivel usando esos datos.
- Indicador de conexión con el juego en la pestaña Batalla y comprobación previa al iniciar (no arranca si no ve la barra de vida o Aion no está delante).

## 1.5.0
- Autoconfiguración: detecta las barras de vida, maná y objetivo y la barra de habilidades en una captura (botón ✨ en la pestaña Vista, o `python autoconfig.py captura.png`).

## 1.4.0
- Pestaña 🔧 Diagnóstico: prueba si el personaje se mueve con dos métodos de teclado y activa solo el que funciona.
- Nuevo modo de teclas por scancode (juegos que ignoran las teclas normales).

## 1.3.0
- Pestaña 👁 Vista: captura tu pantalla y dibuja lo que detecta el bot (barras, % leídos, nombre del objetivo, barra de habilidades con su rol).
- Vigilancia de ventana: si Aion no está en primer plano el bot no pulsa nada (así no escribe en otra aplicación).

## 1.2.1
- Añadida la zona Guardavieja (niveles 10-19). Cuenta como válida en el tramo de Altgard y el bot no te manda a otra zona si ya estás en una válida para tu nivel.

## 1.2.0
- Guía de leveling (pestaña 📖): ruta por tramos de nivel basada en guías de EuroAion 4.6. El bot farmea los tramos que puede y te avisa en los de misiones/instancias.

## 1.1.5
- Corregido un error de sintaxis en app.py de la 1.1.4 que impedía abrir la app. Si tienes la 1.1.4, actualiza.

## 1.1.4
- 'Zona actual' admite escribir el nombre de cualquier zona y las zonas nuevas aparecen al instante en todos los desplegables.

## 1.1.3
- La tabla de zonas se puede editar desde la pestaña Conocimiento (nombre, niveles, notas).

## 1.1.2
- Zonas ajustadas: Beluslan 30-44, Brusthonin 45-50, Gelkmaros 51-55 y nueva zona Enshar 56-65.

## 1.1.1
- Corregidas las zonas asmodianas: Altgard (10-19) va antes que Morheim (20-29). Zona inicial del config: Altgard.
- Marcado que los rangos no están verificados para EUROaion 4.6.

## 1.1.0
- Launcher con actualizaciones (copia de seguridad y vuelta atrás; tus datos no se tocan).
- Analizador de monstruos: mide XP, tiempo y vida perdida por monstruo y evita los poco rentables.
- Puntos de farmeo con patrulla, elección del mejor por XP/min y rutas entre puntos y zonas.
- Plan de farmeo por nivel y acercamiento al objetivo si no le hace daño.

## 1.0.0
- Interfaz asmodiana, pociones, descanso, auto-habilidades por clic y aviso de cambio de zona.
