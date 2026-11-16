# -*- coding: utf-8 -*-
"""
Лабораторная работа 2. Лабиринт – поиск кратчайшего пути.

- редактирование лабиринта мышью (стены, вход, выходы, размер);
- поиск ВСЕХ маршрутов от входа до выходов (поиск в глубину);
- кратчайший маршрут – волновой алгоритм Ли (поиск в ширину);
- вывод количества маршрутов и их длин, просмотр по очереди и переход к номеру.

Цвета как в методичке: стены – белые, проходы – чёрные,
вход – синий, выходы – красные, маршрут – зелёный.

Только стандартная библиотека. Запуск:  python lab2_maze.py
"""
import random
import sys
import tkinter as tk
from collections import deque
from tkinter import ttk, messagebox

sys.setrecursionlimit(10000)

FREE, WALL = 0, 1
MAX_ROUTES = 10000       # не перечислять больше этого числа маршрутов
MAX_STEPS = 500000       # ограничение числа шагов перебора

# Карты из методички: 0 – проход, 1 – стена, 7 – вход, 9 – выход
MAP1 = [[1, 1, 0, 0, 0, 0, 1, 1, 9, 1],
        [7, 0, 0, 1, 1, 0, 1, 0, 0, 1],
        [1, 1, 1, 1, 1, 0, 1, 0, 1, 0],
        [1, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        [0, 0, 1, 0, 1, 0, 1, 1, 0, 1],
        [0, 1, 1, 0, 0, 0, 0, 0, 0, 0],
        [0, 1, 1, 1, 1, 0, 1, 1, 1, 1],
        [0, 1, 1, 0, 0, 0, 1, 0, 0, 0],
        [0, 0, 1, 0, 1, 1, 1, 0, 1, 0],
        [1, 9, 1, 0, 0, 0, 0, 0, 1, 9]]

MAP2 = [[7, 0, 0, 0, 0, 0, 0, 0, 0, 9],
        [0, 1, 1, 1, 1, 1, 1, 1, 1, 0],
        [0, 1, 1, 1, 1, 0, 1, 0, 1, 0],
        [0, 1, 0, 0, 0, 0, 1, 0, 1, 0],
        [0, 1, 0, 0, 0, 0, 1, 1, 1, 0],
        [0, 1, 0, 0, 0, 0, 0, 0, 1, 0],
        [0, 1, 0, 0, 0, 0, 1, 1, 1, 0],
        [0, 1, 1, 0, 0, 0, 1, 0, 1, 0],
        [0, 1, 1, 1, 1, 1, 1, 1, 1, 0],
        [0, 0, 0, 0, 9, 0, 0, 0, 0, 0]]


# ----------------------------------------------------------------------
#  Алгоритмы
# ----------------------------------------------------------------------
def neighbors(grid, r, c):
    """Соседние проходимые клетки (вверх, вниз, влево, вправо)."""
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < len(grid) and 0 <= nc < len(grid[0]) and grid[nr][nc] == FREE:
            yield nr, nc


def shortest_path(grid, start, exits):
    """Волновой алгоритм Ли (поиск в ширину): кратчайший путь до ближайшего выхода."""
    prev = {start: None}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        if cell in exits:
            path = []
            while cell is not None:
                path.append(cell)
                cell = prev[cell]
            return path[::-1]
        for nb in neighbors(grid, *cell):
            if nb not in prev:
                prev[nb] = cell
                queue.append(nb)
    return None


def all_paths(grid, start, exits):
    """
    Все маршруты от входа до выходов без повторного прохода по клеткам
    (поиск в глубину с возвратом). Возвращает (маршруты по возрастанию длины, полнота).
    """
    routes, path, visited = [], [start], {start}
    state = {"steps": 0, "complete": True}

    def dfs(cell):
        state["steps"] += 1
        if state["steps"] > MAX_STEPS or len(routes) >= MAX_ROUTES:
            state["complete"] = False
            return
        if cell in exits:                      # дошли до выхода – маршрут найден
            routes.append(list(path))
            return
        for nb in neighbors(grid, *cell):
            if nb not in visited:
                visited.add(nb)
                path.append(nb)
                dfs(nb)
                path.pop()
                visited.discard(nb)
                if not state["complete"]:
                    return

    dfs(start)
    routes.sort(key=len)
    return routes, state["complete"]


def parse_map(m):
    grid = [[WALL if v == 1 else FREE for v in row] for row in m]
    start, exits = None, set()
    for r, row in enumerate(m):
        for c, v in enumerate(row):
            if v == 7:
                start = (r, c)
            elif v == 9:
                exits.add((r, c))
    return grid, start, exits


# ----------------------------------------------------------------------
#  Интерфейс
# ----------------------------------------------------------------------
CANVAS = 540
C_WALL, C_FREE, C_START, C_EXIT, C_PATH = "white", "black", "#1e40ff", "#e00000", "#00e000"


class MazeApp:
    def __init__(self, root):
        self.root = root
        root.title("Лабораторная работа 2 — Лабиринт: поиск кратчайшего пути")
        root.resizable(False, False)

        self.grid, self.start, self.exits = parse_map(MAP1)
        self.routes = []
        self.idx = 0
        self.shown = None          # отображаемый маршрут
        self.shortest = None
        self.paint_value = None

        self.canvas = tk.Canvas(root, width=CANVAS, height=CANVAS, bg="gray", highlightthickness=0)
        self.canvas.grid(row=0, column=0, padx=10, pady=10)
        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)

        p = ttk.Frame(root)
        p.grid(row=0, column=1, sticky="n", padx=(0, 10), pady=10)

        # --- редактирование -------------------------------------------
        edit = ttk.LabelFrame(p, text="Редактирование (клик по полю)")
        edit.pack(fill="x")
        self.mode = tk.StringVar(value="wall")
        for text, val in (("Стена / проход (можно вести мышью)", "wall"),
                          ("Поставить вход", "start"),
                          ("Добавить / убрать выход", "exit")):
            ttk.Radiobutton(edit, text=text, value=val, variable=self.mode).pack(anchor="w", padx=6)

        size = ttk.Frame(edit)
        size.pack(fill="x", padx=6, pady=4)
        ttk.Label(size, text="Строк:").pack(side="left")
        self.rows_var = tk.IntVar(value=10)
        ttk.Spinbox(size, from_=3, to=25, width=4, textvariable=self.rows_var).pack(side="left", padx=(2, 8))
        ttk.Label(size, text="Столбцов:").pack(side="left")
        self.cols_var = tk.IntVar(value=10)
        ttk.Spinbox(size, from_=3, to=25, width=4, textvariable=self.cols_var).pack(side="left", padx=2)

        btns = ttk.Frame(edit)
        btns.pack(fill="x", padx=6, pady=(0, 6))
        for text, cmd in (("Пустой", self.new_empty), ("Случайный", self.new_random),
                          ("Карта 1", lambda: self.load(MAP1)), ("Карта 2", lambda: self.load(MAP2))):
            ttk.Button(btns, text=text, command=cmd).pack(side="left", padx=1)

        ttk.Button(p, text="Найти маршруты", command=self.find).pack(fill="x", pady=8)

        # --- результаты -----------------------------------------------
        res = ttk.LabelFrame(p, text="Результат")
        res.pack(fill="x")
        self.lbl_total = ttk.Label(res, text="Всего маршрутов: —", font=("TkDefaultFont", 11, "bold"))
        self.lbl_total.pack(anchor="w", padx=6)
        self.lbl_short = ttk.Label(res, text="Кратчайший маршрут: —")
        self.lbl_short.pack(anchor="w", padx=6)
        ttk.Button(res, text="Показать кратчайший", command=self.show_shortest).pack(anchor="w", padx=6, pady=4)

        lb_frame = ttk.Frame(res)
        lb_frame.pack(fill="both", padx=6, pady=(0, 6))
        self.listbox = tk.Listbox(lb_frame, height=10, width=34, exportselection=False)
        sb = ttk.Scrollbar(lb_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.config(yscrollcommand=sb.set)
        self.listbox.pack(side="left", fill="both")
        sb.pack(side="left", fill="y")
        self.listbox.bind("<<ListboxSelect>>", self.on_list)

        # --- навигация ------------------------------------------------
        nav = ttk.LabelFrame(p, text="Просмотр маршрутов")
        nav.pack(fill="x", pady=8)
        row = ttk.Frame(nav)
        row.pack(pady=4)
        for text, cmd in (("|<", lambda: self.goto(0)), ("<", lambda: self.goto(self.idx - 1)),
                          (">", lambda: self.goto(self.idx + 1)),
                          (">|", lambda: self.goto(len(self.routes) - 1))):
            ttk.Button(row, text=text, width=4, command=cmd).pack(side="left", padx=2)
        jump = ttk.Frame(nav)
        jump.pack(pady=(0, 4))
        ttk.Label(jump, text="Перейти к №").pack(side="left")
        self.jump_var = tk.StringVar()
        e = ttk.Entry(jump, textvariable=self.jump_var, width=7)
        e.pack(side="left", padx=4)
        e.bind("<Return>", lambda _e: self.jump())
        ttk.Button(jump, text="Перейти", command=self.jump).pack(side="left")
        self.lbl_cur = ttk.Label(nav, text="Маршрут: —")
        self.lbl_cur.pack(pady=(0, 4))

        self.draw()

    # --- работа с лабиринтом -----------------------------------------
    def set_maze(self, grid, start, exits):
        self.grid, self.start, self.exits = grid, start, exits
        self.rows_var.set(len(grid))
        self.cols_var.set(len(grid[0]))
        self.reset_results()

    def load(self, m):
        self.set_maze(*parse_map(m))

    def read_size(self):
        try:
            r = max(3, min(25, int(self.rows_var.get())))
            c = max(3, min(25, int(self.cols_var.get())))
        except (ValueError, tk.TclError):
            r, c = 10, 10
        return r, c

    def new_empty(self):
        r, c = self.read_size()
        self.set_maze([[FREE] * c for _ in range(r)], (0, 0), {(r - 1, c - 1)})

    def new_random(self):
        r, c = self.read_size()
        grid = [[WALL if random.random() < 0.35 else FREE for _ in range(c)] for _ in range(r)]
        start = (random.randrange(r), 0)
        exits = {(random.randrange(r), c - 1), (0, random.randrange(c)), (r - 1, random.randrange(c))}
        exits.discard(start)
        for cell in exits | {start}:
            grid[cell[0]][cell[1]] = FREE
        self.set_maze(grid, start, exits)

    def reset_results(self):
        self.routes, self.idx, self.shown, self.shortest = [], 0, None, None
        self.listbox.delete(0, "end")
        self.lbl_total.config(text="Всего маршрутов: —")
        self.lbl_short.config(text="Кратчайший маршрут: —")
        self.lbl_cur.config(text="Маршрут: —")
        self.draw()

    def cell_at(self, x, y):
        size = self.cell_size()
        c, r = x // size, y // size
        if 0 <= r < len(self.grid) and 0 <= c < len(self.grid[0]):
            return r, c
        return None

    def on_press(self, ev):
        cell = self.cell_at(ev.x, ev.y)
        if not cell:
            return
        r, c = cell
        mode = self.mode.get()
        if mode == "wall":
            if cell == self.start or cell in self.exits:
                return
            self.paint_value = FREE if self.grid[r][c] == WALL else WALL
            self.grid[r][c] = self.paint_value
        elif mode == "start":
            self.start = cell
            self.exits.discard(cell)
            self.grid[r][c] = FREE
        else:
            if cell == self.start:
                return
            if cell in self.exits:
                self.exits.discard(cell)
            else:
                self.exits.add(cell)
                self.grid[r][c] = FREE
        self.reset_results()

    def on_drag(self, ev):
        if self.mode.get() != "wall" or self.paint_value is None:
            return
        cell = self.cell_at(ev.x, ev.y)
        if cell and cell != self.start and cell not in self.exits \
                and self.grid[cell[0]][cell[1]] != self.paint_value:
            self.grid[cell[0]][cell[1]] = self.paint_value
            self.reset_results()

    # --- поиск -------------------------------------------------------
    def find(self):
        if self.start is None or not self.exits:
            messagebox.showwarning("Лабиринт", "Задайте вход и хотя бы один выход.")
            return
        self.root.config(cursor="watch")
        self.root.update()
        self.shortest = shortest_path(self.grid, self.start, self.exits)
        self.routes, complete = all_paths(self.grid, self.start, self.exits)
        self.root.config(cursor="")

        self.listbox.delete(0, "end")
        if not self.routes:
            self.lbl_total.config(text="Всего маршрутов: 0")
            self.lbl_short.config(text="Выход недостижим")
            self.shown = None
            self.lbl_cur.config(text="Маршрут: —")
            self.draw()
            return

        total = f"Всего маршрутов: {len(self.routes)}"
        if not complete:
            total += " (перебор остановлен по лимиту)"
        self.lbl_total.config(text=total)
        self.lbl_short.config(text=f"Кратчайший маршрут: длина {len(self.shortest) - 1}")
        for i, route in enumerate(self.routes, 1):
            er, ec = route[-1]
            self.listbox.insert("end", f"№{i}: длина {len(route) - 1}  → выход ({er + 1}, {ec + 1})")
        self.goto(0)

    # --- навигация ---------------------------------------------------
    def goto(self, i):
        if not self.routes:
            return
        self.idx = max(0, min(len(self.routes) - 1, i))
        self.shown = self.routes[self.idx]
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(self.idx)
        self.listbox.see(self.idx)
        self.lbl_cur.config(text=f"Маршрут {self.idx + 1} из {len(self.routes)}, "
                                 f"длина {len(self.shown) - 1}")
        self.draw()

    def on_list(self, _ev):
        sel = self.listbox.curselection()
        if sel:
            self.goto(sel[0])

    def jump(self):
        try:
            self.goto(int(self.jump_var.get()) - 1)
        except ValueError:
            pass

    def show_shortest(self):
        if not self.shortest:
            return
        if self.shortest in self.routes:
            self.goto(self.routes.index(self.shortest))
        else:
            self.shown = self.shortest
            self.lbl_cur.config(text=f"Кратчайший маршрут, длина {len(self.shortest) - 1}")
            self.draw()

    # --- рисование ---------------------------------------------------
    def cell_size(self):
        return CANVAS // max(len(self.grid), len(self.grid[0]))

    def draw(self):
        cv = self.canvas
        cv.delete("all")
        s = self.cell_size()
        on_path = set(self.shown) if self.shown else set()
        for r, row in enumerate(self.grid):
            for c, v in enumerate(row):
                cell = (r, c)
                if cell == self.start:
                    color = C_START
                elif cell in self.exits:
                    color = C_EXIT
                elif cell in on_path:
                    color = C_PATH
                else:
                    color = C_WALL if v == WALL else C_FREE
                cv.create_rectangle(c * s, r * s, (c + 1) * s, (r + 1) * s, fill=color, outline="#555")
        if self.shown and len(self.shown) > 1:       # линия маршрута поверх клеток
            pts = [(c * s + s / 2, r * s + s / 2) for r, c in self.shown]
            cv.create_line(*[v for p in pts for v in p], fill="#006400", width=2)


if __name__ == "__main__":
    root = tk.Tk()
    MazeApp(root)
    root.mainloop()
