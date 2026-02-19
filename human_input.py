import ctypes
import time
import random
import math

user32 = ctypes.windll.user32


class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long), ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class Input_I(ctypes.Union):
    _fields_ = [("mi", MouseInput)]


class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", Input_I)]


# Konstanten
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


class HumanMouse:
    def __init__(self):
        self.screen_w = user32.GetSystemMetrics(0)
        self.screen_h = user32.GetSystemMetrics(1)

    def _get_current_pos(self):
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    def _send_mouse_event(self, x, y, flags):
        norm_x = int(x * 65535 / self.screen_w)
        norm_y = int(y * 65535 / self.screen_h)
        extra = ctypes.c_ulong(0)
        ii_ = Input_I()
        ii_.mi = MouseInput(norm_x, norm_y, 0, flags, 0, ctypes.pointer(extra))
        inp = Input(ctypes.c_ulong(0), ii_)
        user32.SendInput(1, ctypes.pointer(inp), ctypes.sizeof(inp))

    def _ease_out_quad(self, t):
        """Mathematische Abbremsung kurz vor dem Ziel"""
        return t * (2 - t)

    def _generate_bezier_curve(self, start, end, control1, control2, steps):
        """Berechnet die Kurvenpunkte vorab."""
        points = []
        for i in range(steps):
            t = i / float(steps - 1)
            t_eased = self._ease_out_quad(t)

            u = 1 - t_eased
            tt = t_eased * t_eased
            uu = u * u
            uuu = uu * u
            ttt = tt * t_eased

            p_x = uuu * start[0] + 3 * uu * t_eased * control1[0] + 3 * u * tt * control2[0] + ttt * end[0]
            p_y = uuu * start[1] + 3 * uu * t_eased * control1[1] + 3 * u * tt * control2[1] + ttt * end[1]
            points.append((int(p_x), int(p_y)))
        return points

    def move_to_humanized(self, target_x, target_y):
        """Bewegt die Maus auf natürliche Weise zum Ziel, inklusive leichtem Overshooting."""
        start_x, start_y = self._get_current_pos()

        distance = math.hypot(target_x - start_x, target_y - start_y)
        if distance < 5:
            return

        deviation = min(distance * 0.3, 150)
        cp1_x = start_x + (target_x - start_x) * 0.3 + random.uniform(-deviation, deviation)
        cp1_y = start_y + (target_y - start_y) * 0.3 + random.uniform(-deviation, deviation)
        cp2_x = start_x + (target_x - start_x) * 0.7 + random.uniform(-deviation, deviation)
        cp2_y = start_y + (target_y - start_y) * 0.7 + random.uniform(-deviation, deviation)

        steps = int(max(15, min(80, distance * 0.05)))

        final_x, final_y = target_x, target_y
        if random.random() < 0.10:
            target_x += random.randint(-8, 8)
            target_y += random.randint(-8, 8)

        curve_points = self._generate_bezier_curve(
            (start_x, start_y), (target_x, target_y),
            (cp1_x, cp1_y), (cp2_x, cp2_y), steps
        )

        for point in curve_points:
            self._send_mouse_event(point[0], point[1], MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE)
            time.sleep(random.uniform(0.001, 0.003))

        if (target_x, target_y) != (final_x, final_y):
            time.sleep(random.uniform(0.02, 0.06))
            self._send_mouse_event(final_x, final_y, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE)

    def human_click(self):
        """Klickt mit Gauss-verteilter Haltedauer."""
        hold_time = random.gauss(0.055, 0.010)
        hold_time = max(0.025, min(0.110, hold_time))

        self._send_mouse_event(0, 0, MOUSEEVENTF_LEFTDOWN)
        time.sleep(hold_time)
        self._send_mouse_event(0, 0, MOUSEEVENTF_LEFTUP)