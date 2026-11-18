# -*- coding: utf-8 -*-
"""
Лабораторная работа 1. Шахматы – патовые и матовые ситуации.

Белый король + любые две белые фигуры против одинокого чёрного короля.
Пользователь кликом ставит чёрного короля – программа находит ВСЕ
матовые и патовые позиции (ход чёрных), без учёта перестановок
одинаковых фигур (2 слона, 2 ладьи, 2 коня, 2 ферзя, 2 пешки).

Только стандартная библиотека (tkinter). Запуск:  python lab1_chess.py
"""
import sys
import threading
import tkinter as tk
from tkinter import ttk

# ----------------------------------------------------------------------
#  Модель
# ----------------------------------------------------------------------
FILES = "abcdefgh"
NAMES = {"K": "Король", "Q": "Ферзь", "R": "Ладья", "B": "Слон",
         "N": "Конь", "P": "Пешка"}
GLYPH = {"K": "\u265A", "Q": "\u265B", "R": "\u265C",
         "B": "\u265D", "N": "\u265E", "P": "\u265F"}


def sq_name(s):
    return FILES[s % 8] + str(s // 8 + 1)


def _build_tables():
    king = [0] * 64
    knight = [0] * 64
    pawn = [0] * 64            # белая пешка бьёт «вверх»
    rook_rays = [[] for _ in range(64)]
    bishop_rays = [[] for _ in range(64)]
    for s in range(64):
        r, f = divmod(s, 8)
        for dr in (-1, 0, 1):
            for df in (-1, 0, 1):
                if (dr or df) and 0 <= r + dr < 8 and 0 <= f + df < 8:
                    king[s] |= 1 << ((r + dr) * 8 + f + df)
        for dr, df in ((1, 2), (2, 1), (-1, 2), (-2, 1),
                       (1, -2), (2, -1), (-1, -2), (-2, -1)):
            if 0 <= r + dr < 8 and 0 <= f + df < 8:
                knight[s] |= 1 << ((r + dr) * 8 + f + df)
        for df in (-1, 1):
            if r < 7 and 0 <= f + df < 8:
                pawn[s] |= 1 << ((r + 1) * 8 + f + df)
        for rays, dirs in ((rook_rays, ((1, 0), (-1, 0), (0, 1), (0, -1))),
                           (bishop_rays, ((1, 1), (1, -1), (-1, 1), (-1, -1)))):
            for dr, df in dirs:
                ray, rr, ff = [], r + dr, f + df
                while 0 <= rr < 8 and 0 <= ff < 8:
                    ray.append(rr * 8 + ff)
                    rr += dr
                    ff += df
                if ray:
                    rays[s].append(ray)
    queen_rays = [rook_rays[s] + bishop_rays[s] for s in range(64)]
    return king, knight, pawn, rook_rays, bishop_rays, queen_rays


KING, KNIGHT, PAWN, ROOK_RAYS, BISHOP_RAYS, QUEEN_RAYS = _build_tables()


def attacks(t, s, occ):
    """Маска полей, которые бьёт фигура t с поля s (занятое поле включается)."""
    if t == "N":
        return KNIGHT[s]
    if t == "P":
        return PAWN[s]
    if t == "K":
        return KING[s]
    rays = ROOK_RAYS[s] if t == "R" else BISHOP_RAYS[s] if t == "B" else QUEEN_RAYS[s]
    m = 0
    for ray in rays:
        for q in ray:
            b = 1 << q
            m |= b
            if occ & b:
                break
    return m


def search(bk, use_pawns=False):
    """
    Все позиции с чёрным королём на bk, где чёрным (их ход) мат или пат.
    Результат: список (вид, поле_бк, тип1, поле1, тип2, поле2), вид 'M'/'S'.
    Пара фигур неупорядоченная -> перестановки одинаковых фигур не дублируются.
    """
    types = "QRBN" + ("P" if use_pawns else "")
    entries = []
    for t in types:
        for s in range(64):
            if t == "P" and not (8 <= s <= 55):     # пешка не на 1-й/8-й горизонтали
                continue
            entries.append((t, s, attacks(t, s, 0)))   # «псевдо»-атака без блокировок

    need = KING[bk]                  # все соседние поля чёрного короля
    result = []
    for wk in range(64):
        if wk == bk or (KING[bk] >> wk) & 1:        # короли не рядом
            continue
        kmask = KING[wk]
        rem = need & ~kmask
        ents = [e for e in entries if e[1] != wk and e[1] != bk]
        n = len(ents)
        for i in range(n):
            ti, si, pi = ents[i]
            r1 = rem & ~pi
            for j in range(i + 1, n):
                if r1 & ~ents[j][2]:                # быстрый отсев (необходимое условие)
                    continue
                tj, sj, _ = ents[j]
                occ = (1 << wk) | (1 << si) | (1 << sj)   # чёрный король не блокирует лучи
                att = kmask | attacks(ti, si, occ) | attacks(tj, sj, occ)
                if need & ~att:                     # у чёрного есть свободное поле
                    continue
                kind = "M" if (att >> bk) & 1 else "S"
                result.append((kind, wk, ti, si, tj, sj))
    return result


# ----------------------------------------------------------------------
#  Интерфейс
# ----------------------------------------------------------------------
CELL = 64
MARGIN = 26
LIGHT, DARK = "#f0d9b5", "#b58863"
FONT_FAMILY = "Segoe UI Symbol" if sys.platform.startswith("win") else "DejaVu Sans"


class App:
    def __init__(self, root):
        self.root = root
        root.title("Лабораторная работа 1 — Шахматы: маты и паты")
        root.resizable(False, False)
        self.bk = None
        self.all = []
        self.view = []
        self.idx = 0
        self.busy = False
        self._lock = False

        side = 8 * CELL + 2 * MARGIN
        self.canvas = tk.Canvas(root, width=side, height=side, highlightthickness=0)
        self.canvas.grid(row=0, column=0, padx=10, pady=10)
        self.canvas.bind("<Button-1>", self.on_click)

        panel = ttk.Frame(root)
        panel.grid(row=0, column=1, sticky="n", padx=(0, 12), pady=10)

        ttk.Label(panel, text="Кликните по доске, чтобы поставить\nчёрного короля.",
                  justify="left").pack(anchor="w")

        box = ttk.LabelFrame(panel, text="Что показывать")
        box.pack(fill="x", pady=8)
        self.mode = tk.StringVar(value="all")
        for text, val in (("Мат и пат", "all"), ("Только мат", "M"), ("Только пат", "S")):
            ttk.Radiobutton(box, text=text, value=val, variable=self.mode,
                            command=self.apply_filter).pack(anchor="w", padx=6)

        self.pawns = tk.BooleanVar(value=False)
        ttk.Checkbutton(panel, text="Учитывать пешки как фигуры", variable=self.pawns,
                        command=self.restart).pack(anchor="w")

        self.stats = ttk.Label(panel, text="Всего вариантов: —", font=("TkDefaultFont", 11, "bold"))
        self.stats.pack(anchor="w", pady=(10, 0))
        self.stats2 = ttk.Label(panel, text="")
        self.stats2.pack(anchor="w")

        nav = ttk.LabelFrame(panel, text="Просмотр комбинаций")
        nav.pack(fill="x", pady=10)
        row = ttk.Frame(nav)
        row.pack(pady=4)
        for text, cmd in (("|<", lambda: self.goto(0)),
                          ("<", lambda: self.goto(self.idx - 1)),
                          (">", lambda: self.goto(self.idx + 1)),
                          (">|", lambda: self.goto(len(self.view) - 1))):
            ttk.Button(row, text=text, width=4, command=cmd).pack(side="left", padx=2)

        self.scale = tk.Scale(nav, from_=1, to=1, orient="horizontal", length=260,
                              showvalue=False, command=self.on_scale)
        self.scale.pack(padx=6)
        self.pos_label = ttk.Label(nav, text="Комбинация: —")
        self.pos_label.pack()

        jump = ttk.Frame(nav)
        jump.pack(pady=6)
        ttk.Label(jump, text="Перейти к №").pack(side="left")
        self.jump_var = tk.StringVar()
        e = ttk.Entry(jump, textvariable=self.jump_var, width=8)
        e.pack(side="left", padx=4)
        e.bind("<Return>", lambda _e: self.jump())
        ttk.Button(jump, text="Перейти", command=self.jump).pack(side="left")

        self.desc = tk.Label(panel, text="", justify="left", anchor="w", font=("TkDefaultFont", 10))
        self.desc.pack(fill="x", pady=(4, 0))
        self.verdict = tk.Label(panel, text="", font=("TkDefaultFont", 14, "bold"))
        self.verdict.pack(anchor="w")

        root.bind("<Left>", lambda _e: self.goto(self.idx - 1))
        root.bind("<Right>", lambda _e: self.goto(self.idx + 1))
        root.bind("<Home>", lambda _e: self.goto(0))
        root.bind("<End>", lambda _e: self.goto(len(self.view) - 1))
        self.draw()

    # --- поиск -------------------------------------------------------
    def on_click(self, ev):
        f = (ev.x - MARGIN) // CELL
        r = 7 - (ev.y - MARGIN) // CELL
        if 0 <= f < 8 and 0 <= r < 8:
            self.bk = r * 8 + f
            self.restart()

    def restart(self):
        if self.bk is None or self.busy:
            return
        self.busy = True
        self.stats.config(text="Идёт поиск…")
        self.stats2.config(text="")
        bk, pawns = self.bk, self.pawns.get()
        self._res = None

        def work():
            self._res = search(bk, pawns)

        threading.Thread(target=work, daemon=True).start()
        self.root.after(80, self.poll)

    def poll(self):
        if self._res is None:
            self.root.after(80, self.poll)
            return
        self.all = self._res
        self.busy = False
        self.apply_filter()

    def apply_filter(self):
        mode = self.mode.get()
        self.view = [x for x in self.all if mode == "all" or x[0] == mode]
        self.idx = 0
        n = len(self.view)
        self.scale.config(from_=1, to=max(1, n), state="normal" if n else "disabled")
        m = sum(1 for x in self.all if x[0] == "M")
        self.stats.config(text=f"Всего вариантов: {n}")
        self.stats2.config(text=f"(найдено: матов — {m}, патов — {len(self.all) - m})")
        self.refresh()

    # --- навигация ---------------------------------------------------
    def goto(self, i):
        if not self.view:
            return
        self.idx = max(0, min(len(self.view) - 1, i))
        self.refresh()

    def on_scale(self, v):
        if not self._lock:
            self.goto(int(float(v)) - 1)

    def jump(self):
        try:
            self.goto(int(self.jump_var.get()) - 1)
        except ValueError:
            pass

    def refresh(self):
        n = len(self.view)
        if n:
            self._lock = True
            self.scale.set(self.idx + 1)
            self._lock = False
            self.pos_label.config(text=f"Комбинация: {self.idx + 1} из {n}")
            kind, wk, t1, s1, t2, s2 = self.view[self.idx]
            self.desc.config(text=(f"Белый король: {sq_name(wk)}\n"
                                   f"{NAMES[t1]}: {sq_name(s1)}\n"
                                   f"{NAMES[t2]}: {sq_name(s2)}\n"
                                   f"Чёрный король: {sq_name(self.bk)}"))
            self.verdict.config(text="МАТ" if kind == "M" else "ПАТ",
                                fg="#c62828" if kind == "M" else "#ef6c00")
        else:
            self.pos_label.config(text="Комбинация: —")
            self.desc.config(text="")
            self.verdict.config(text="")
        self.draw()

    # --- рисование ---------------------------------------------------
    def piece(self, s, t, white):
        r, f = divmod(s, 8)
        x = MARGIN + f * CELL + CELL // 2
        y = MARGIN + (7 - r) * CELL + CELL // 2
        font = (FONT_FAMILY, 38)
        if white:
            for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1), (0, 2), (0, -2), (2, 0), (-2, 0)):
                self.canvas.create_text(x + dx, y + dy, text=GLYPH[t], font=font, fill="black")
            self.canvas.create_text(x, y, text=GLYPH[t], font=font, fill="white")
        else:
            self.canvas.create_text(x, y, text=GLYPH[t], font=font, fill="black")

    def draw(self):
        c = self.canvas
        c.delete("all")
        cur = self.view[self.idx] if self.view else None
        for r in range(8):
            for f in range(8):
                color = DARK if (r + f) % 2 == 0 else LIGHT
                if cur and r * 8 + f == self.bk:
                    color = "#e57373" if cur[0] == "M" else "#ffd54f"
                x0 = MARGIN + f * CELL
                y0 = MARGIN + (7 - r) * CELL
                c.create_rectangle(x0, y0, x0 + CELL, y0 + CELL, fill=color, outline="")
        for i in range(8):
            c.create_text(MARGIN + i * CELL + CELL // 2, MARGIN // 2, text=FILES[i])
            c.create_text(MARGIN + i * CELL + CELL // 2, MARGIN + 8 * CELL + MARGIN // 2, text=FILES[i])
            c.create_text(MARGIN // 2, MARGIN + (7 - i) * CELL + CELL // 2, text=str(i + 1))
            c.create_text(MARGIN + 8 * CELL + MARGIN // 2, MARGIN + (7 - i) * CELL + CELL // 2, text=str(i + 1))
        if self.bk is not None:
            self.piece(self.bk, "K", white=False)
        if cur:
            _, wk, t1, s1, t2, s2 = cur
            self.piece(wk, "K", True)
            self.piece(s1, t1, True)
            self.piece(s2, t2, True)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
