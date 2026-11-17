"""Exploración: cómo se mueve el personaje cuando no hay monstruos a la vista.

Cada llamada a step() hace UNA acción corta:
  - girar un paso (la bot pulsa Tab entre giros: así barre los 360° buscando objetivos), o
  - tras una vuelta completa sin objetivo, caminar hacia delante y comprobar que no se ha quedado atascado
    (si la imagen no cambia, gira entre 90° y 180° para salir).
Si el minimapa está calibrado y no hay puntos rojos, se salta el barrido y camina directamente.
"""
import random
import time

from diagnostics import frame_diff


class Explorer:
    def __init__(self, cfg, act, grab=None, dots=None, sleep=time.sleep, log=print, rnd=random.random):
        self.cfg, self.act, self.grab, self.dots = cfg, act, grab, dots
        self.sleep, self.log, self.rnd = sleep, log, rnd
        self.sweeps = 0
        self.empty_walks = 0
        self.stuck_count = 0

    def _hold(self, key, secs):
        self.act.down(key)
        self.sleep(secs)
        self.act.up(key)

    def step(self):
        ec = self.cfg["explore"]
        n = self.dots() if self.dots else None            # nº de monstruos en el minimapa (None = sin minimapa)
        if self.sweeps < ec.get("sweeps_per_circle", 8) and n != 0:
            self._hold(ec["turn_keys"][0], ec["turn_seconds"])
            self.sweeps += 1
            return "turn"
        self.sweeps = 0
        lo, hi = ec.get("walk_seconds", [2.0, 4.0])
        secs = lo + (hi - lo) * self.rnd()
        before = self.grab() if self.grab else None
        self._hold(ec["forward_key"], secs)
        result = "walk"
        if before is not None:
            self.sleep(0.15)
            if frame_diff(before, self.grab()) < ec.get("stuck_threshold", 3.0):
                self._hold(ec["turn_keys"][-1], ec["turn_seconds"] * (2 + int(self.rnd() * 3)))   # 90-180°
                self.stuck_count += 1
                result = "stuck"
        self.empty_walks = self.empty_walks + 1 if n == 0 else 0
        return result
