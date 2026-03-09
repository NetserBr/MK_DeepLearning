"""
Mortal Kombat Trilogy (N64) — Interactive keyboard play via stable_retro.

Uses the parallel_n64 emulator core with full button support.
No auto-reset between fights — the game flows naturally.
"""

import ctypes
import sys
import time

import pyglet
from pyglet import gl
from pyglet.window import key as keycodes

import stable_retro as retro


# N64 controller buttons (from parallel_n64.json):
#   ["A", "B", null, "START", "UP", "DOWN", "LEFT", "RIGHT",
#    "C-RIGHT", "C-UP", "L", "R", "Z", "C-MODE", "L3", "R3"]
#
# MK Trilogy N64 controls — classic MK PC keyboard layout:
#
#   Same layout as MK Arcade Kollection / MK Komplete Edition:
#
#        D   S         ← Punches  (High / Low)
#        C   X         ← Kicks    (High / Low)
#        A             ← Block
#        Z             ← Run
#     Arrows           ← Movement
#
#   D-pad   = Movement       → Arrow keys
#   START   = Pause          → Enter

# Map N64 button names to pyglet keycodes
_BUTTON_MAP = {
    "A":       keycodes.D,      # High Punch
    "B":       keycodes.S,      # Low Punch
    "START":   keycodes.RETURN,
    "UP":      keycodes.UP,
    "DOWN":    keycodes.DOWN,
    "LEFT":    keycodes.LEFT,
    "RIGHT":   keycodes.RIGHT,
    "C-UP":    keycodes.C,      # High Kick
    "C-RIGHT": keycodes.X,      # Low Kick
    "R":       keycodes.A,      # Block
    "L":       keycodes.Z,      # Run
    "Z":       keycodes.SPACE,  # Throw
}


class MKTrilogyInteractive:
    """Interactive MK Trilogy (N64) wrapper with full button support."""

    def __init__(self, game, state, record=None):
        self._env = retro.make(
            game=game,
            state=state,
            record=record,
            use_restricted_actions=retro.Actions.ALL,
            render_mode="rgb_array",
        )
        self._buttons = self._env.buttons
        obs, _ = self._env.reset()
        self._image = self._env.render()

        h, w = self._image.shape[:2]

        # Window sizing
        display = pyglet.canvas.get_display()
        screen = display.get_default_screen()
        max_w, max_h = screen.width * 0.9, screen.height * 0.9
        aspect = w / h
        win_w, win_h = w, h
        while win_w > max_w or win_h > max_h:
            win_w //= 2
            win_h //= 2
        while win_w < max_w / 2 and win_h < max_h / 2:
            win_w *= 2
            win_h *= 2

        self._win = pyglet.window.Window(width=win_w, height=win_h)
        self._keys = pyglet.window.key.KeyStateHandler()
        self._win.push_handlers(self._keys)
        self._win.on_close = self._on_close

        # OpenGL texture
        gl.glEnable(gl.GL_TEXTURE_2D)
        self._tex = gl.GLuint(0)
        gl.glGenTextures(1, ctypes.byref(self._tex))
        gl.glBindTexture(gl.GL_TEXTURE_2D, self._tex)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
        gl.glTexImage2D(
            gl.GL_TEXTURE_2D, 0, gl.GL_RGBA8,
            w, h, 0,
            gl.GL_RGB, gl.GL_UNSIGNED_BYTE, None,
        )

        self._tps = 60
        self._steps = 0

    def _keys_to_act(self):
        """Map held keyboard keys to N64 controller buttons."""
        return [
            bool(self._keys[_BUTTON_MAP.get(b, 0)]) if b else False
            for b in self._buttons
        ]

    def run(self):
        print("=" * 50)
        print("  MORTAL KOMBAT TRILOGY (N64)")
        print("=" * 50)
        print("  Arrows      Move / Jump / Crouch")
        print("  D           High Punch")
        print("  S           Low Punch")
        print("  C           High Kick")
        print("  X           Low Kick")
        print("  A           Block")
        print("  Z           Run")
        print("  Space       Throw")
        print("  Enter       Start / Pause")
        print("  F1          Reset to save-state")
        print("  Escape      Quit")
        print("=" * 50)

        prev = time.time()
        sim_time = 0.0
        cur_time = 0.0

        while True:
            self._win.switch_to()
            self._win.dispatch_events()

            now = time.time()
            dt = now - prev
            prev = now
            if dt > 4 / self._tps:
                dt = 4 / self._tps

            cur_time += dt
            while sim_time < cur_time:
                sim_time += 1 / self._tps

                if self._keys[keycodes.ESCAPE]:
                    self._on_close()

                if self._keys[keycodes.F1]:
                    self._env.reset()
                    print("[reset]")
                    continue

                act = self._keys_to_act()
                obs, rew, terminated, truncated, info = self._env.step(act)
                self._image = self._env.render()
                self._steps += 1

            self._draw()
            self._win.flip()

    def _draw(self):
        gl.glBindTexture(gl.GL_TEXTURE_2D, self._tex)
        buf = ctypes.cast(
            self._image.tobytes(), ctypes.POINTER(ctypes.c_short),
        )
        gl.glTexSubImage2D(
            gl.GL_TEXTURE_2D, 0, 0, 0,
            self._image.shape[1], self._image.shape[0],
            gl.GL_RGB, gl.GL_UNSIGNED_BYTE, buf,
        )
        w, h = self._win.width, self._win.height
        pyglet.graphics.draw(
            4, pyglet.gl.GL_QUADS,
            ("v2f", [0, 0, w, 0, w, h, 0, h]),
            ("t2f", [0, 1, 1, 1, 1, 0, 0, 0]),
        )

    def _on_close(self):
        self._env.close()
        sys.exit(0)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Play Mortal Kombat Trilogy (N64) with the keyboard.",
    )
    parser.add_argument(
        "--game", default="MortalKombatTrilogy-N64-v0",
    )
    parser.add_argument(
        "--state", default="Fight",
        help="Save-state to load (default: Fight)",
    )
    parser.add_argument(
        "--record", default=None, nargs="?", const=True,
    )
    args = parser.parse_args()

    game = MKTrilogyInteractive(
        game=args.game, state=args.state, record=args.record,
    )
    game.run()


if __name__ == "__main__":
    main()
