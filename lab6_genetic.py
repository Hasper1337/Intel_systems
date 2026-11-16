# -*- coding: utf-8 -*-
"""
Лабораторная работа 6. Генетический алгоритм. Вариант 1.

Закупка продуктов для предприятия общественного питания: подобрать количество
единиц каждого продукта (в пределах «мин.–макс.») так, чтобы суммарная стоимость
не превышала бюджет и использовала его как можно полнее.

- таблица продуктов (55 шт.) редактируется прямо на главной форме
  (двойной клик по ячейке, кнопки «Добавить» / «Удалить», загрузка и сохранение CSV);
- бюджет и параметры алгоритма вводятся с клавиатуры;
- ход эволюции показывается на графике.

Генетический алгоритм:
  особь        – список количеств (по одному гену на продукт);
  приспособл.  – сумма закупки; за превышение бюджета – штраф;
  отбор        – турнирный; скрещивание – одноточечное; мутация – изменение гена;
  элитизм      – две лучшие особи переходят в новое поколение без изменений.

Только стандартная библиотека. Запуск:  python lab6_genetic.py
"""
import csv
import random
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Наименование, мин. количество, макс. количество, стоимость единицы (руб.)
DEFAULT_DATA = [
    ("Мука пшеничная, кг", 20, 80, 52), ("Сахар, кг", 10, 50, 68), ("Соль, кг", 2, 10, 25),
    ("Масло подсолнечное, л", 10, 40, 135), ("Масло сливочное, кг", 5, 25, 820),
    ("Молоко, л", 20, 100, 89), ("Сливки 20%, л", 5, 30, 310), ("Сметана, кг", 5, 25, 280),
    ("Творог, кг", 5, 20, 390), ("Сыр твёрдый, кг", 5, 25, 760), ("Яйцо куриное, десяток", 10, 60, 115),
    ("Говядина, кг", 10, 50, 690), ("Свинина, кг", 10, 50, 420), ("Филе куриное, кг", 15, 70, 360),
    ("Фарш мясной, кг", 5, 30, 450), ("Бекон, кг", 2, 12, 880), ("Колбаса варёная, кг", 3, 15, 520),
    ("Сосиски, кг", 3, 20, 430), ("Рыба (минтай), кг", 5, 30, 260), ("Сёмга, кг", 2, 12, 1650),
    ("Креветки, кг", 1, 10, 990), ("Картофель, кг", 30, 150, 38), ("Морковь, кг", 10, 40, 42),
    ("Лук репчатый, кг", 10, 40, 36), ("Капуста белокочанная, кг", 10, 40, 34),
    ("Свёкла, кг", 5, 25, 39), ("Помидоры, кг", 5, 30, 240), ("Огурцы, кг", 5, 30, 210),
    ("Перец болгарский, кг", 3, 15, 290), ("Чеснок, кг", 1, 5, 320), ("Зелень, кг", 1, 6, 650),
    ("Грибы шампиньоны, кг", 3, 20, 340), ("Яблоки, кг", 5, 30, 125), ("Лимоны, кг", 2, 10, 190),
    ("Бананы, кг", 3, 20, 140), ("Рис, кг", 10, 40, 110), ("Гречка, кг", 10, 40, 95),
    ("Макароны, кг", 10, 40, 85), ("Овсяные хлопья, кг", 3, 15, 78), ("Горох, кг", 2, 10, 64),
    ("Фасоль консервированная, банка", 5, 30, 92), ("Кукуруза консервированная, банка", 5, 30, 88),
    ("Горошек зелёный, банка", 5, 30, 84), ("Томатная паста, кг", 2, 12, 230),
    ("Майонез, кг", 3, 15, 245), ("Кетчуп, кг", 2, 12, 195), ("Горчица, кг", 1, 5, 260),
    ("Уксус, л", 1, 5, 70), ("Перец чёрный молотый, кг", 1, 3, 1200), ("Лавровый лист, кг", 1, 2, 900),
    ("Чай чёрный, кг", 1, 8, 980), ("Кофе молотый, кг", 1, 8, 1750), ("Какао-порошок, кг", 1, 5, 720),
    ("Хлеб, буханка", 20, 100, 48), ("Вода питьевая 19 л, бутыль", 5, 25, 260),
]


# ----------------------------------------------------------------------
#  Генетический алгоритм
# ----------------------------------------------------------------------
def cost(ind, prices):
    """Суммарная стоимость закупки."""
    return sum(q * p for q, p in zip(ind, prices))


def fitness(ind, prices, budget):
    """
    Допустимая особь: приспособленность = сумма закупки (чем ближе к бюджету, тем лучше).
    Превышение бюджета: отрицательное значение – такая особь хуже любой допустимой,
    но чем меньше превышение, тем она «лучше» (рельеф функции остаётся гладким).
    """
    total = cost(ind, prices)
    if total <= budget:
        return total
    return budget - total


def genetic(lows, highs, prices, budget, pop_size=100, generations=500, p_mut=0.03, p_cross=0.9):
    """
    Генератор: после каждого поколения выдаёт (номер поколения, лучшая особь, её стоимость).
    Лучшая особь всегда допустима (не превышает бюджет).
    """
    n = len(prices)

    def random_individual():
        # доля заполнения у каждой особи своя – в популяции есть и «дешёвые», и «дорогие»
        share = random.random()
        return [lo + round((hi - lo) * share * random.random()) for lo, hi in zip(lows, highs)]

    def tournament(scored):
        return max(random.sample(scored, 3))[1]

    def mutate(ind):
        for i in range(n):
            if random.random() < p_mut:
                if random.random() < 0.5:                       # небольшой сдвиг
                    ind[i] += random.choice((-2, -1, 1, 2))
                    ind[i] = max(lows[i], min(highs[i], ind[i]))
                else:                                           # новое случайное значение
                    ind[i] = random.randint(lows[i], highs[i])

    population = [list(lows)] + [random_individual() for _ in range(pop_size - 1)]
    for gen in range(1, generations + 1):
        scored = sorted(((fitness(ind, prices, budget), ind) for ind in population), reverse=True)
        best = scored[0][1]
        yield gen, best, cost(best, prices)
        if scored[0][0] == budget:                              # бюджет израсходован полностью
            return

        new_population = [scored[0][1][:], scored[1][1][:]]     # элитизм
        while len(new_population) < pop_size:
            a, b = tournament(scored), tournament(scored)
            if random.random() < p_cross and n > 1:             # одноточечное скрещивание
                point = random.randint(1, n - 1)
                a, b = a[:point] + b[point:], b[:point] + a[point:]
            else:
                a, b = a[:], b[:]
            mutate(a)
            mutate(b)
            new_population += [a, b]
        population = new_population[:pop_size]


# ----------------------------------------------------------------------
#  Интерфейс
# ----------------------------------------------------------------------
COLUMNS = (("num", "№", 40), ("name", "Наименование продукта", 250), ("min", "Мин. кол-во", 105),
           ("max", "Макс. кол-во", 110), ("price", "Стоимость ед., руб.", 150),
           ("qty", "Закупить", 85), ("sum", "Сумма, руб.", 105))


def money(x):
    return f"{x:,.2f}".replace(",", " ").replace(".00", "")


class GeneticApp:
    def __init__(self, root):
        self.root = root
        root.title("Лабораторная работа 6 — Генетический алгоритм: закупка продуктов")
        root.geometry("1280x680")
        self.running = None        # работающий генератор алгоритма
        self.history = []          # лучшая стоимость по поколениям
        self.editor = None

        # --- таблица --------------------------------------------------
        left = ttk.Frame(root)
        left.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=10)
        ttk.Label(left, text="Входные данные (двойной клик по ячейке – изменить значение)").pack(anchor="w")
        frame = ttk.Frame(left)
        frame.pack(fill="both", expand=True, pady=4)
        self.tree = ttk.Treeview(frame, columns=[c[0] for c in COLUMNS], show="headings")
        for key, title, width in COLUMNS:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor="w" if key == "name" else "center")
        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.config(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.tree.bind("<Double-1>", self.edit_cell)

        btns = ttk.Frame(left)
        btns.pack(fill="x")
        for text, cmd in (("Добавить", self.add_row), ("Удалить", self.delete_rows),
                          ("Загрузить CSV…", self.load_csv), ("Сохранить CSV…", self.save_csv),
                          ("Исходные данные", lambda: self.set_data(DEFAULT_DATA))):
            ttk.Button(btns, text=text, command=cmd).pack(side="left", padx=(0, 4))
        self.lbl_range = ttk.Label(left, text="", foreground="#555")
        self.lbl_range.pack(anchor="w", pady=(6, 0))

        # --- управление -----------------------------------------------
        right = ttk.Frame(root)
        right.pack(side="left", fill="y", padx=(5, 10), pady=10)

        form = ttk.LabelFrame(right, text="Параметры")
        form.pack(fill="x")
        self.vars = {}
        for i, (key, text, val) in enumerate((("budget", "Бюджет, руб.:", "250000"),
                                              ("pop", "Размер популяции:", "100"),
                                              ("gens", "Число поколений:", "500"),
                                              ("mut", "Вероятность мутации гена:", "0.03"))):
            ttk.Label(form, text=text).grid(row=i, column=0, sticky="w", padx=6, pady=3)
            v = tk.StringVar(value=val)
            ttk.Entry(form, textvariable=v, width=12).grid(row=i, column=1, padx=6, pady=3)
            self.vars[key] = v

        self.btn_run = ttk.Button(right, text="Запустить алгоритм", command=self.start)
        self.btn_run.pack(fill="x", pady=(8, 2))
        self.btn_stop = ttk.Button(right, text="Остановить", command=self.stop, state="disabled")
        self.btn_stop.pack(fill="x")

        res = ttk.LabelFrame(right, text="Результат")
        res.pack(fill="x", pady=8)
        self.lbl_gen = ttk.Label(res, text="Поколение: —")
        self.lbl_gen.pack(anchor="w", padx=6)
        self.lbl_total = ttk.Label(res, text="Стоимость закупки: —", font=("TkDefaultFont", 11, "bold"))
        self.lbl_total.pack(anchor="w", padx=6)
        self.lbl_rest = ttk.Label(res, text="Остаток бюджета: —")
        self.lbl_rest.pack(anchor="w", padx=6, pady=(0, 4))

        ttk.Label(right, text="Лучшая стоимость по поколениям:").pack(anchor="w")
        self.chart = tk.Canvas(right, width=360, height=260, bg="white", highlightthickness=1,
                               highlightbackground="#999")
        self.chart.pack()

        self.set_data(DEFAULT_DATA)

    # --- данные таблицы ----------------------------------------------
    def set_data(self, rows):
        self.stop()
        self.tree.delete(*self.tree.get_children())
        for name, lo, hi, price in rows:
            self.tree.insert("", "end", values=(0, name, lo, hi, f"{price:g}", "", ""))
        self.data_changed()

    def get_data(self):
        """Таблица -> список (название, мин, макс, цена)."""
        rows = []
        for item in self.tree.get_children():
            v = self.tree.item(item, "values")
            rows.append((v[1], int(v[2]), int(v[3]), float(v[4])))
        return rows

    def data_changed(self):
        """Перенумеровать строки, сбросить старый результат, обновить подсказку."""
        for i, item in enumerate(self.tree.get_children(), 1):
            self.tree.set(item, "num", i)
            self.tree.set(item, "qty", "")
            self.tree.set(item, "sum", "")
        rows = self.get_data()
        lo = sum(r[1] * r[3] for r in rows)
        hi = sum(r[2] * r[3] for r in rows)
        self.lbl_range.config(text=f"Продуктов: {len(rows)}.  Минимально возможная сумма: {money(lo)} руб., "
                                   f"максимальная: {money(hi)} руб.")

    def add_row(self):
        item = self.tree.insert("", "end", values=(0, "Новый продукт", 0, 10, 100, "", ""))
        self.data_changed()
        self.tree.see(item)
        self.tree.selection_set(item)

    def delete_rows(self):
        for item in self.tree.selection():
            self.tree.delete(item)
        self.data_changed()

    def edit_cell(self, ev):
        """Редактирование ячейки: поверх неё появляется поле ввода."""
        if self.running:
            return
        item = self.tree.identify_row(ev.y)
        col = self.tree.identify_column(ev.x)          # '#1', '#2', ...
        if not item or not col:
            return
        key = COLUMNS[int(col[1:]) - 1][0]
        if key not in ("name", "min", "max", "price"):
            return
        if self.editor:
            self.editor.destroy()
        x, y, w, h = self.tree.bbox(item, col)
        entry = ttk.Entry(self.tree)
        entry.insert(0, self.tree.set(item, key))
        entry.select_range(0, "end")
        entry.place(x=x, y=y, width=w, height=h)
        entry.focus()
        self.editor = entry

        def commit(_ev=None):
            if not entry.winfo_exists():
                return
            text = entry.get().strip().replace(",", ".")
            entry.destroy()
            error = self.check_value(item, key, text)
            if error:
                messagebox.showerror("Ошибка ввода", error)
                return
            self.tree.set(item, key, text)
            self.data_changed()

        entry.bind("<Return>", commit)
        entry.bind("<FocusOut>", commit)
        entry.bind("<Escape>", lambda _e: entry.destroy())

    def check_value(self, item, key, text):
        """Проверка введённого значения. Возвращает текст ошибки или None."""
        if key == "name":
            return None if text else "Название не может быть пустым."
        try:
            value = float(text) if key == "price" else int(text)
        except ValueError:
            return "Нужно ввести число (количество – целое)."
        if key == "price" and value <= 0:
            return "Стоимость должна быть больше нуля."
        if value < 0:
            return "Количество не может быть отрицательным."
        if key == "min" and value > int(self.tree.set(item, "max")):
            return "Минимальное количество больше максимального."
        if key == "max" and value < int(self.tree.set(item, "min")):
            return "Максимальное количество меньше минимального."
        return None

    def load_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            with open(path, encoding="utf-8-sig", newline="") as f:
                rows = []
                for r in csv.reader(f, delimiter=";"):
                    if len(r) < 4 or not r[1].strip().isdigit():
                        continue                      # заголовок или пустая строка
                    lo, hi, price = int(r[1]), int(r[2]), float(r[3].replace(",", "."))
                    if lo > hi or price <= 0:
                        raise ValueError(f"некорректная строка: {r}")
                    rows.append((r[0], lo, hi, price))
        except (OSError, ValueError) as e:
            messagebox.showerror("Загрузка", f"Не удалось прочитать файл:\n{e}")
            return
        self.set_data(rows)

    def save_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["Наименование", "Мин. количество", "Макс. количество", "Стоимость ед."])
            w.writerows(self.get_data())

    # --- запуск алгоритма --------------------------------------------
    def start(self):
        if self.editor and self.editor.winfo_exists():
            self.editor.destroy()
        rows = self.get_data()
        try:
            budget = float(self.vars["budget"].get().replace(",", ".").replace(" ", ""))
            pop = int(self.vars["pop"].get())
            gens = int(self.vars["gens"].get())
            mut = float(self.vars["mut"].get().replace(",", "."))
            if budget <= 0 or pop < 4 or gens < 1 or not 0 <= mut <= 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка ввода", "Проверьте параметры: бюджет > 0, популяция ≥ 4, "
                                                 "поколений ≥ 1, вероятность мутации от 0 до 1.")
            return
        if not rows:
            messagebox.showerror("Данные", "Таблица продуктов пуста.")
            return

        lows = [r[1] for r in rows]
        highs = [r[2] for r in rows]
        prices = [r[3] for r in rows]
        self.budget = budget
        self.prices = prices
        self.history = []
        min_total, max_total = cost(lows, prices), cost(highs, prices)
        if min_total > budget:
            self.data_changed()
            self.draw_chart()
            messagebox.showwarning("Решения нет", f"Даже минимальные количества стоят {money(min_total)} руб. – "
                                                  f"это больше бюджета {money(budget)} руб.")
            return
        if max_total <= budget:                        # ограничение не действует – искать нечего
            self.show_result(0, highs, max_total)
            self.draw_chart()
            messagebox.showinfo("Результат", "Бюджета хватает на максимальные количества всех продуктов – "
                                             "оптимизация не требуется.")
            return

        self.running = genetic(lows, highs, prices, budget, pop, gens, mut)
        self.btn_run.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.tick()

    def tick(self):
        """Несколько поколений за один «тик», чтобы окно не зависало."""
        if not self.running:
            return
        result = None
        try:
            for _ in range(5):
                result = next(self.running)
                self.history.append(result[2])
        except StopIteration:
            self.stop()
        if result:
            self.show_result(*result)
            self.draw_chart()
        if self.running:
            self.root.after(1, self.tick)

    def stop(self):
        self.running = None
        self.btn_run.config(state="normal")
        self.btn_stop.config(state="disabled")

    # --- вывод -------------------------------------------------------
    def show_result(self, gen, best, total):
        for item, q, p in zip(self.tree.get_children(), best, self.prices):
            self.tree.set(item, "qty", q)
            self.tree.set(item, "sum", money(q * p))
        self.lbl_gen.config(text=f"Поколение: {gen if gen else '—'}")
        self.lbl_total.config(text=f"Стоимость закупки: {money(total)} руб.")
        self.lbl_rest.config(text=f"Остаток бюджета: {money(self.budget - total)} руб. "
                                  f"(использовано {100 * total / self.budget:.2f} %)")

    def draw_chart(self):
        cv = self.chart
        cv.delete("all")
        if len(self.history) < 2:
            return
        w, h, pad = int(cv["width"]), int(cv["height"]), 30
        lo, hi = min(self.history), self.budget
        span = (hi - lo) or 1
        x = lambda i: pad + i * (w - 2 * pad) / (len(self.history) - 1)
        y = lambda v: h - pad - (v - lo) * (h - 2 * pad) / span
        cv.create_line(pad, y(hi), w - pad, y(hi), fill="#e53935", dash=(4, 3))
        cv.create_text(w - pad, y(hi) - 9, text=f"бюджет {money(hi)}", anchor="e", fill="#e53935")
        cv.create_line(pad, h - pad, w - pad, h - pad, fill="#888")
        cv.create_line(pad, pad - 10, pad, h - pad, fill="#888")
        cv.create_text(pad, h - pad + 12, text="1", anchor="w")
        cv.create_text(w - pad, h - pad + 12, text=str(len(self.history)), anchor="e")
        cv.create_text(w // 2, h - pad + 12, text="поколение")
        cv.create_text(pad + 4, h - pad - 8, text=money(lo), anchor="w", fill="#555")
        pts = [c for i, v in enumerate(self.history) for c in (x(i), y(v))]
        cv.create_line(*pts, fill="#1565c0", width=2)


if __name__ == "__main__":
    root = tk.Tk()
    GeneticApp(root)
    root.mainloop()
