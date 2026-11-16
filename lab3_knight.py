# -*- coding: utf-8 -*-
"""
Лабораторная работа 3. Задача о ходе коня.

- доска произвольного размера N x M (вводится на форме);
- начальная позиция коня – поля ввода или клик по доске;
- поиск обхода по правилу Варнсдорфа + перебор с возвратом,
  если правило заводит в тупик (с отсечением заведомых тупиков);
- если обхода нет – выводится сообщение (с причиной);
- результат: номера ходов на доске (статика) и анимация движения коня.

Только стандартная библиотека. Запуск:  python lab3_knight.py
"""
import random
import time
import tkinter as tk
from tkinter import ttk, messagebox

MOVES = ((1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2))
TIME_LIMIT = 10.0          # секунд на перебор


# ----------------------------------------------------------------------
#  Алгоритм
# ----------------------------------------------------------------------
def free_moves(x, y, n, m, board):
    """Поля, куда конь может пойти из (x, y) и где он ещё не был."""
    res = []
    for dx, dy in MOVES:
        nx, ny = x + dx, y + dy
        if 0 <= nx < n and 0 <= ny < m and board[ny][nx] == 0:
            res.append((nx, ny))
    return res


def knight_tour(n, m, sx, sy):
    """
    Поиск обхода доски n (ширина) x m (высота) конём из поля (sx, sy), отсчёт с 0.
    1) Известные теоремы о неразрешимости (проверка мгновенная).
    2) Перебор с возвратом, ходы в порядке правила Варнсдорфа, с отсечением тупиков.
       На маленьких досках он успевает перебрать всё и доказать, что решения нет.
    3) Если перебор затянулся – перезапуски со случайным выбором среди
       равноценных по Варнсдорфу ходов.
    Возвращает (список полей | None, причина).
    """
    total = n * m
    # Если число полей нечётное, обход возможен только с полей «большего» цвета
    if total % 2 == 1 and (sx + sy) % 2 == 1:
        return None, "parity"
    # Доска 4 x K: с полей двух внутренних линий обхода не существует
    if n == 4 and m > 4 and sx in (1, 2) or m == 4 and n > 4 and sy in (1, 2):
        return None, "four"

    deadline = time.time() + TIME_LIMIT
    path, reason = search(n, m, sx, sy, time.time() + min(1.5, TIME_LIMIT), prune=True)
    if reason != "timeout":
        return path, reason
    rnd = random.Random(0)
    while time.time() < deadline:
        path, reason = search(n, m, sx, sy, deadline, max_nodes=3000, rnd=rnd)
        if path:
            return path, "ok"
    return None, "timeout"


def search(n, m, sx, sy, deadline, prune=False, max_nodes=None, rnd=None):
    """
    Перебор с возвратом. Возвращает (путь, "ok") | (None, "none") – решений нет |
    (None, "timeout") – кончилось время или лимит узлов.
    """
    total = n * m
    board = [[0] * n for _ in range(m)]
    board[sy][sx] = 1
    path = [(sx, sy)]

    def ordered(x, y):
        cand = free_moves(x, y, n, m, board)
        # правило Варнсдорфа; равноценные ходы – случайно (при перезапусках)
        cand.sort(key=lambda p: (len(free_moves(p[0], p[1], n, m, board)),
                                 rnd.random() if rnd else 0))
        return cand

    def hopeless(x, y):
        """
        Отсечение тупиков: каждое непосещённое поле должно оставаться достижимым.
        Поле, в которое можно попасть только одним ходом, станет концом маршрута –
        а конец у маршрута один. Конь стоит на (x, y).
        """
        ends = 0
        for cy in range(m):
            for cx in range(n):
                if board[cy][cx]:
                    continue
                deg = len(free_moves(cx, cy, n, m, board))
                if deg == 0 and len(path) < total - 1:
                    near = any((cx + dx, cy + dy) == (x, y) for dx, dy in MOVES)
                    if not near:
                        return True
                    ends += 1
                elif deg == 1 and not any((cx + dx, cy + dy) == (x, y) for dx, dy in MOVES):
                    ends += 1
                if ends > 1:
                    return True
        # все непосещённые поля должны быть связаны с текущим положением коня
        left = total - len(path)
        seen, queue = {(x, y)}, [(x, y)]
        while queue:
            cx, cy = queue.pop()
            for p in free_moves(cx, cy, n, m, board):
                if p not in seen:
                    seen.add(p)
                    queue.append(p)
        return len(seen) - 1 < left

    use_prune = prune and total <= 150  # на больших досках правило Варнсдорфа справляется само
    stack = [ordered(sx, sy)]           # для каждого шага – ещё не опробованные ходы
    nodes = 0
    while stack:
        if len(path) == total:
            return path, "ok"
        nodes += 1
        if (max_nodes and nodes > max_nodes) or (nodes % 256 == 0 and time.time() > deadline):
            return None, "timeout"
        options = stack[-1]
        if options:
            x, y = options.pop(0)
            board[y][x] = len(path) + 1
            path.append((x, y))
            if use_prune and len(path) < total and hopeless(x, y):
                stack.append([])       # тупик – этот ход сразу откатится
            else:
                stack.append(ordered(x, y))
        else:                          # тупик – откат на шаг назад
            stack.pop()
            x, y = path.pop()
            board[y][x] = 0
    return None, "none"


# ----------------------------------------------------------------------
#  Интерфейс
# ----------------------------------------------------------------------
AREA = 560
LIGHT, DARK = "#eeeeee", "#c85000"


class KnightApp:
    def __init__(self, root):
        self.root = root
        root.title("Лабораторная работа 3 — Задача о ходе коня")
        root.resizable(False, False)
        self.n, self.m = 8, 8
        self.path = []
        self.step = 0              # сколько ходов показано
        self.playing = False
        self.after_id = None

        self.canvas = tk.Canvas(root, width=AREA, height=AREA, bg="#d9b38c", highlightthickness=0)
        self.canvas.grid(row=0, column=0, padx=10, pady=10)
        self.canvas.bind("<Button-1>", self.on_click)

        p = ttk.Frame(root)
        p.grid(row=0, column=1, sticky="n", padx=(0, 10), pady=10)

        form = ttk.LabelFrame(p, text="Параметры")
        form.pack(fill="x")
        self.vars = {}
        for i, (key, text, val) in enumerate((("n", "Ширина доски N:", 8), ("m", "Высота доски M:", 8),
                                              ("x", "Начальная X (1..N):", 1), ("y", "Начальная Y (1..M):", 1))):
            ttk.Label(form, text=text).grid(row=i, column=0, sticky="w", padx=6, pady=2)
            v = tk.StringVar(value=str(val))
            ttk.Entry(form, textvariable=v, width=7).grid(row=i, column=1, padx=6, pady=2)
            self.vars[key] = v
        ttk.Label(form, text="X – столбец (a=1), Y – строка снизу.\nНачало можно выбрать кликом по доске.",
                  foreground="#555").grid(row=4, column=0, columnspan=2, sticky="w", padx=6, pady=(2, 6))
        for v in (self.vars["n"], self.vars["m"]):
            v.trace_add("write", lambda *_: self.on_size_change())

        ttk.Button(p, text="Найти", command=self.solve).pack(fill="x", pady=(8, 2))
        ttk.Button(p, text="Начать заново", command=self.reset).pack(fill="x", pady=2)

        show = ttk.LabelFrame(p, text="Отображение")
        show.pack(fill="x", pady=8)
        row = ttk.Frame(show)
        row.pack(pady=4)
        self.play_btn = ttk.Button(row, text="▶ Пуск", width=9, command=self.toggle_play)
        self.play_btn.pack(side="left", padx=2)
        ttk.Button(row, text="Сразу весь", width=10, command=self.show_all).pack(side="left", padx=2)
        row2 = ttk.Frame(show)
        row2.pack(pady=2)
        ttk.Button(row2, text="< Шаг", width=8, command=lambda: self.set_step(self.step - 1)).pack(side="left", padx=2)
        ttk.Button(row2, text="Шаг >", width=8, command=lambda: self.set_step(self.step + 1)).pack(side="left", padx=2)

        ttk.Label(show, text="Скорость обхода (мс на ход):").pack(anchor="w", padx=6, pady=(6, 0))
        self.speed = tk.IntVar(value=150)
        tk.Scale(show, from_=10, to=1000, orient="horizontal", variable=self.speed,
                 length=220).pack(padx=6, pady=(0, 4))

        self.lbl_move = ttk.Label(p, text="Ход: —", font=("TkDefaultFont", 12, "bold"))
        self.lbl_move.pack(anchor="w", pady=(4, 0))
        self.lbl_info = ttk.Label(p, text="", wraplength=250, justify="left")
        self.lbl_info.pack(anchor="w", pady=4)

        self.draw()

    # --- ввод ------------------------------------------------------------
    def read_int(self, key, lo, hi):
        try:
            v = int(self.vars[key].get())
        except ValueError:
            raise ValueError(f"Поле «{key.upper()}» должно быть целым числом")
        if not lo <= v <= hi:
            raise ValueError(f"Значение {key.upper()} должно быть от {lo} до {hi}")
        return v

    def on_size_change(self):
        try:
            n, m = int(self.vars["n"].get()), int(self.vars["m"].get())
        except ValueError:
            return
        if 1 <= n <= 30 and 1 <= m <= 30 and (n, m) != (self.n, self.m):
            self.n, self.m = n, m
            self.reset()

    def on_click(self, ev):
        s, ox, oy = self.geometry()
        col, row = int((ev.x - ox) // s), int((ev.y - oy) // s)
        if 0 <= col < self.n and 0 <= row < self.m:
            self.vars["x"].set(str(col + 1))
            self.vars["y"].set(str(self.m - row))
            self.reset()

    # --- решение ---------------------------------------------------------
    def solve(self):
        try:
            n = self.read_int("n", 1, 30)
            m = self.read_int("m", 1, 30)
            x = self.read_int("x", 1, n)
            y = self.read_int("y", 1, m)
        except ValueError as e:
            messagebox.showerror("Ошибка ввода", str(e))
            return
        self.n, self.m = n, m
        self.stop()
        self.root.config(cursor="watch")
        self.root.update()
        t = time.time()
        path, reason = knight_tour(n, m, x - 1, y - 1)
        dt = time.time() - t
        self.root.config(cursor="")

        if path is None:
            self.path, self.step = [], 0
            self.draw()
            msg = {"parity": "Для данного положения коня решения нет: при нечётном числе полей "
                             "обход возможен только с полей того же цвета, что и угловые.",
                   "four": "Для данного положения коня решения нет: на доске шириной 4 обход "
                           "невозможен, если конь стоит на одной из двух внутренних линий.",
                   "none": "Для данного размера доски и положения коня задача решения не имеет.",
                   "timeout": f"Обход не найден за {TIME_LIMIT:.0f} с перебора."}[reason]
            self.lbl_move.config(text="Ход: —")
            self.lbl_info.config(text=msg)
            messagebox.showinfo("Результат", msg)
            return

        self.path = path
        closed = any((path[-1][0] + dx, path[-1][1] + dy) == path[0] for dx, dy in MOVES)
        self.lbl_info.config(text=f"Обход найден за {dt:.2f} с.\n"
                                  f"Маршрут {'замкнутый' if closed else 'незамкнутый'}, "
                                  f"{len(path)} полей.")
        self.set_step(1)
        self.toggle_play()

    # --- анимация --------------------------------------------------------
    def toggle_play(self):
        if not self.path:
            return
        if self.playing:
            self.stop()
        else:
            if self.step >= len(self.path):
                self.step = 1
            self.playing = True
            self.play_btn.config(text="❚❚ Пауза")
            self.tick()

    def tick(self):
        if not self.playing:
            return
        if self.step >= len(self.path):
            self.stop()
            return
        self.set_step(self.step + 1)
        self.after_id = self.root.after(self.speed.get(), self.tick)

    def stop(self):
        self.playing = False
        self.play_btn.config(text="▶ Пуск")
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def show_all(self):
        self.stop()
        self.set_step(len(self.path))

    def set_step(self, k):
        if not self.path:
            return
        self.step = max(1, min(len(self.path), k))
        self.lbl_move.config(text=f"Ход: {self.step} из {len(self.path)}")
        self.draw()

    def reset(self):
        self.stop()
        self.path, self.step = [], 0
        self.lbl_move.config(text="Ход: —")
        self.lbl_info.config(text="")
        self.draw()

    # --- рисование -------------------------------------------------------
    def geometry(self):
        s = (AREA - 40) / max(self.n, self.m)
        ox = (AREA - s * self.n) / 2
        oy = (AREA - s * self.m) / 2
        return s, ox, oy

    def center(self, x, y):
        s, ox, oy = self.geometry()
        return ox + x * s + s / 2, oy + (self.m - 1 - y) * s + s / 2

    def draw(self):
        cv = self.canvas
        cv.delete("all")
        s, ox, oy = self.geometry()
        for y in range(self.m):
            for x in range(self.n):
                x0, y0 = ox + x * s, oy + (self.m - 1 - y) * s
                cv.create_rectangle(x0, y0, x0 + s, y0 + s, outline="#333",
                                    fill=DARK if (x + y) % 2 == 0 else LIGHT)
        # подписи
        letters = "abcdefghijklmnopqrstuvwxyzABCD"
        for x in range(self.n):
            cv.create_text(ox + x * s + s / 2, oy - 10, text=letters[x], font=("TkDefaultFont", 8))
        for y in range(self.m):
            cv.create_text(ox - 10, oy + (self.m - 1 - y) * s + s / 2, text=str(y + 1), font=("TkDefaultFont", 8))

        num_font = ("TkDefaultFont", max(6, int(s / 3)), "bold")
        shown = self.path[:self.step]
        if len(shown) > 1:
            pts = [v for p in shown for v in self.center(*p)]
            cv.create_line(*pts, fill="#1565c0", width=max(1, int(s / 20)))
        for i, (x, y) in enumerate(shown[:-1], 1):
            cx, cy = self.center(x, y)
            cv.create_text(cx, cy, text=str(i), font=num_font, fill="black")

        # конь: текущее положение, а до решения – выбранное начальное поле
        if shown:
            kx, ky = shown[-1]
        else:
            try:
                kx, ky = int(self.vars["x"].get()) - 1, int(self.vars["y"].get()) - 1
            except ValueError:
                return
            if not (0 <= kx < self.n and 0 <= ky < self.m):
                return
        cx, cy = self.center(kx, ky)
        cv.create_oval(cx - s * 0.42, cy - s * 0.42, cx + s * 0.42, cy + s * 0.42,
                       fill="#ffeb3b", outline="black")
        cv.create_text(cx, cy, text="♞", font=("DejaVu Sans", max(8, int(s * 0.55))), fill="black")
        if shown:
            cv.create_text(cx + s * 0.32, cy + s * 0.32, text=str(len(shown)),
                           font=("TkDefaultFont", max(6, int(s / 5)), "bold"))


if __name__ == "__main__":
    root = tk.Tk()
    KnightApp(root)
    root.mainloop()
