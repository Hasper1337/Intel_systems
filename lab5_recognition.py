# -*- coding: utf-8 -*-
"""
Лабораторная работа 5. Распознавание образов.

ИС распознавания рукописных символов (цифры и русские буквы)
на основе нейронной сети.

- нейронная сеть – многослойный персептрон 784 → 256 → 43, написан на NumPy
  (обратное распространение ошибки, мини-пакетный градиентный спуск);
- обучающая выборка – файл lab5_dataset.npz (25 332 образца 28x28): рукописные
  цифры из набора MNIST, рукописные русские буквы из набора CoMNIST
  (github.com/GregVial/CoMNIST, лицензия CC BY-SA 4.0) и цифры, нарисованные
  разными шрифтами; при обучении каждый образец дополнительно случайно
  искажается (поворот, наклон, толщина линий);
- пользователь рисует символ мышью, программа выдаёт вероятности символов;
- нарисованный символ можно добавить в обучающую выборку и переобучить сеть.

Нужны библиотеки:  pip install numpy pillow
Запуск:            python lab5_recognition.py
Обученная сеть хранится в lab5_weights.npz. Если этого файла нет, сеть
обучается при запуске (1–2 минуты).
"""
import os
import random
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

DIGITS = "0123456789"
LETTERS = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
CLASSES = DIGITS + LETTERS

SIZE = 28                 # сторона входного изображения сети
HIDDEN = 256              # нейронов в скрытом слое
COPIES = 2                # искажённых копий каждого образца выборки
USER_COPIES = 40          # ... и каждого образца, добавленного пользователем
EPOCHS = 25

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET_FILE = os.path.join(HERE, "lab5_dataset.npz")
WEIGHTS_FILE = os.path.join(HERE, "lab5_weights.npz")
SAMPLES_FILE = os.path.join(HERE, "lab5_user_samples.npz")


# ----------------------------------------------------------------------
#  Подготовка изображений
# ----------------------------------------------------------------------
def normalize(img):
    """
    Приводит рисунок (белый символ на чёрном фоне, режим 'L') к стандартному виду:
    символ вырезается по границам, вписывается в квадрат 20x20 и ставится в центр 28x28.
    Возвращает вектор из 784 чисел 0..1 или None, если рисунок пуст.
    """
    box = img.getbbox()
    if box is None:
        return None
    img = img.crop(box)
    w, h = img.size
    k = 20 / max(w, h)
    img = img.resize((max(1, round(w * k)), max(1, round(h * k))), Image.LANCZOS)
    out = Image.new("L", (SIZE, SIZE), 0)
    out.paste(img, ((SIZE - img.width) // 2, (SIZE - img.height) // 2))
    return np.asarray(out, dtype=np.float32).ravel() / 255


def distort(img, rnd):
    """Случайное искажение: имитация разного почерка."""
    choice = rnd.random()                         # толщина линий
    if choice < 0.3:
        img = img.filter(ImageFilter.MaxFilter(3))
    elif choice < 0.45:
        img = img.filter(ImageFilter.MaxFilter(5))
    elif choice < 0.6:
        img = img.filter(ImageFilter.MinFilter(3))
    shear = rnd.uniform(-0.3, 0.3)                # наклон
    sx, sy = rnd.uniform(0.8, 1.25), rnd.uniform(0.8, 1.25)   # растяжение
    c = img.width / 2
    img = img.transform(img.size, Image.AFFINE,
                        (sx, shear, c - sx * c - shear * c, 0, sy, c - sy * c), Image.BILINEAR)
    return img.rotate(rnd.uniform(-12, 12), Image.BILINEAR)


def build_dataset(progress=lambda text: None):
    """Обучающая выборка: готовые рукописные образцы + примеры пользователя + искажённые копии."""
    if not os.path.exists(DATASET_FILE):
        raise RuntimeError("не найден файл выборки lab5_dataset.npz (должен лежать рядом с программой)")
    data = np.load(DATASET_FILE)
    samples = [(x, int(y), COPIES) for x, y in zip(data["x"], data["y"])]
    ux, uy = load_user_samples()
    samples += [((x * 255).astype(np.uint8), int(y), USER_COPIES) for x, y in zip(ux, uy)]

    rnd = random.Random(0)
    xs, ys = [], []
    for n, (pixels, label, copies) in enumerate(samples):
        if n % 500 == 0:
            progress(f"Подготовка выборки: {n} из {len(samples)}")
        xs.append(pixels.astype(np.float32) / 255)
        ys.append(label)
        big = Image.fromarray(pixels.reshape(SIZE, SIZE)).resize((96, 96))
        for _ in range(copies):
            x = normalize(distort(big, rnd))
            if x is not None:
                xs.append(x)
                ys.append(label)
    return np.array(xs, dtype=np.float32), np.array(ys), len(data["x"]), len(ux)


def load_user_samples():
    if os.path.exists(SAMPLES_FILE):
        data = np.load(SAMPLES_FILE)
        return list(data["x"]), list(data["y"])
    return [], []


# ----------------------------------------------------------------------
#  Нейронная сеть: 784 -> 256 (ReLU) -> 43 (softmax)
# ----------------------------------------------------------------------
class Network:
    def __init__(self):
        rng = np.random.default_rng(0)
        self.w1 = rng.normal(0, np.sqrt(2 / (SIZE * SIZE)), (SIZE * SIZE, HIDDEN)).astype(np.float32)
        self.b1 = np.zeros(HIDDEN, dtype=np.float32)
        self.w2 = rng.normal(0, np.sqrt(2 / HIDDEN), (HIDDEN, len(CLASSES))).astype(np.float32)
        self.b2 = np.zeros(len(CLASSES), dtype=np.float32)

    def forward(self, x):
        """Прямой проход. Возвращает выходы скрытого слоя и вероятности классов."""
        hidden = np.maximum(0, x @ self.w1 + self.b1)
        z = hidden @ self.w2 + self.b2
        z -= z.max(axis=1, keepdims=True)
        p = np.exp(z)
        return hidden, p / p.sum(axis=1, keepdims=True)

    def train(self, x, y, epochs=EPOCHS, lr=0.1, batch=64, progress=lambda text: None):
        """Обучение методом обратного распространения ошибки."""
        rng = np.random.default_rng(0)
        targets = np.eye(len(CLASSES), dtype=np.float32)[y]
        for epoch in range(1, epochs + 1):
            order = rng.permutation(len(x))
            for i in range(0, len(x), batch):
                idx = order[i:i + batch]
                xb = x[idx] + rng.normal(0, 0.1, (len(idx), x.shape[1])).astype(np.float32)   # шум
                hidden, p = self.forward(xb)
                d2 = (p - targets[idx]) / len(idx)            # ошибка выходного слоя
                d1 = (d2 @ self.w2.T) * (hidden > 0)          # ошибка скрытого слоя
                self.w2 -= lr * hidden.T @ d2
                self.b2 -= lr * d2.sum(axis=0)
                self.w1 -= lr * xb.T @ d1
                self.b1 -= lr * d1.sum(axis=0)
            lr *= 0.93
            acc = (self.forward(x)[1].argmax(axis=1) == y).mean()
            progress(f"Обучение: эпоха {epoch} из {epochs}, точность {acc:.1%}")

    def predict(self, x):
        return self.forward(x.reshape(1, -1))[1][0]

    def save(self, path):
        np.savez_compressed(path, w1=self.w1, b1=self.b1, w2=self.w2, b2=self.b2)

    def load(self, path):
        data = np.load(path)
        if data["w1"].shape != self.w1.shape or data["w2"].shape != self.w2.shape:
            raise ValueError("файл весов не подходит к сети")
        self.w1, self.b1, self.w2, self.b2 = data["w1"], data["b1"], data["w2"], data["b2"]


# ----------------------------------------------------------------------
#  Интерфейс
# ----------------------------------------------------------------------
PAD = 300                 # размер поля для рисования
BRUSH = 16


class RecognitionApp:
    def __init__(self, root):
        self.root = root
        root.title("Лабораторная работа 5 — Распознавание рукописных символов")
        root.resizable(False, False)
        self.net = Network()
        self.ready = False            # сеть готова к распознаванию
        self.training = False         # идёт обучение
        self.status_text = "Запуск…"
        self.last = None

        left = ttk.Frame(root)
        left.grid(row=0, column=0, padx=10, pady=10, sticky="n")
        ttk.Label(left, text="Нарисуйте цифру или русскую букву (заглавную):").pack(anchor="w")
        self.canvas = tk.Canvas(left, width=PAD, height=PAD, bg="white", cursor="pencil",
                                highlightthickness=1, highlightbackground="#555")
        self.canvas.pack(pady=4)
        self.canvas.bind("<Button-1>", self.pen_down)
        self.canvas.bind("<B1-Motion>", self.pen_move)
        self.canvas.bind("<ButtonRelease-1>", lambda _e: self.recognize())
        # тот же рисунок параллельно ведётся в памяти – его и получает сеть
        self.image = Image.new("L", (PAD, PAD), 0)
        self.draw = ImageDraw.Draw(self.image)

        row = ttk.Frame(left)
        row.pack(fill="x")
        ttk.Button(row, text="Распознать", command=self.recognize).pack(side="left")
        ttk.Button(row, text="Очистить", command=self.clear).pack(side="left", padx=4)
        ttk.Label(row, text="(правая кнопка мыши – очистить)", foreground="#777").pack(side="left")
        self.canvas.bind("<Button-3>", lambda _e: self.clear())

        right = ttk.Frame(root)
        right.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="n")

        box = ttk.LabelFrame(right, text="Среди чего искать")
        box.pack(fill="x")
        self.mode = tk.StringVar(value="all")
        for text, val in (("Цифры и буквы", "all"), ("Только цифры", "digits"), ("Только буквы", "letters")):
            ttk.Radiobutton(box, text=text, value=val, variable=self.mode,
                            command=self.recognize).pack(side="left", padx=4, pady=2)

        res = ttk.LabelFrame(right, text="Результат")
        res.pack(fill="x", pady=8)
        top = ttk.Frame(res)
        top.pack(fill="x", padx=6)
        self.lbl_symbol = tk.Label(top, text="?", font=("TkDefaultFont", 54, "bold"), width=2, fg="#1565c0")
        self.lbl_symbol.pack(side="left")
        info = ttk.Frame(top)
        info.pack(side="left", padx=8)
        self.lbl_best = ttk.Label(info, text="", font=("TkDefaultFont", 11, "bold"))
        self.lbl_best.pack(anchor="w")
        ttk.Label(info, text="Так рисунок видит сеть (28×28):", foreground="#777").pack(anchor="w")
        self.preview = tk.Canvas(info, width=84, height=84, bg="black", highlightthickness=0)
        self.preview.pack(anchor="w")
        ttk.Label(res, text="Вероятности (пять самых похожих символов):", foreground="#777").pack(anchor="w", padx=6)
        self.bars = tk.Canvas(res, width=330, height=150, highlightthickness=0)
        self.bars.pack(padx=6, pady=(0, 6))

        teach = ttk.LabelFrame(right, text="Дообучение на своём почерке")
        teach.pack(fill="x")
        row = ttk.Frame(teach)
        row.pack(fill="x", padx=6, pady=4)
        ttk.Label(row, text="Это символ:").pack(side="left")
        self.true_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.true_var, width=4).pack(side="left", padx=4)
        ttk.Button(row, text="Добавить в выборку", command=self.add_sample).pack(side="left")
        self.btn_train = ttk.Button(teach, text="Переобучить сеть", command=self.start_training)
        self.btn_train.pack(fill="x", padx=6, pady=(0, 6))

        self.status = ttk.Label(root, text="", relief="sunken", anchor="w")
        self.status.grid(row=1, column=0, columnspan=2, sticky="ew")

        self.draw_bars([])
        try:
            self.net.load(WEIGHTS_FILE)
            self.ready = True
            self.status_text = "Сеть загружена из файла lab5_weights.npz. Можно рисовать."
        except (OSError, ValueError, KeyError):
            self.start_training()
        self.update_status()

    # --- рисование мышью ---------------------------------------------
    def pen_down(self, ev):
        self.last = (ev.x, ev.y)
        self.pen_move(ev)

    def pen_move(self, ev):
        x0, y0 = self.last
        r = BRUSH // 2
        self.canvas.create_line(x0, y0, ev.x, ev.y, width=BRUSH, capstyle="round", fill="black")
        self.draw.line((x0, y0, ev.x, ev.y), fill=255, width=BRUSH)
        self.draw.ellipse((ev.x - r, ev.y - r, ev.x + r, ev.y + r), fill=255)
        self.last = (ev.x, ev.y)

    def clear(self):
        self.canvas.delete("all")
        self.draw.rectangle((0, 0, PAD, PAD), fill=0)
        self.lbl_symbol.config(text="?")
        self.lbl_best.config(text="")
        self.preview.delete("all")
        self.draw_bars([])

    # --- распознавание -----------------------------------------------
    def recognize(self):
        if not self.ready:
            return
        x = normalize(self.image)
        if x is None:
            return
        p = self.net.predict(x)
        if self.mode.get() == "digits":           # оставляем только нужные классы
            p[len(DIGITS):] = 0
        elif self.mode.get() == "letters":
            p[:len(DIGITS)] = 0
        p = p / p.sum()
        top = [(CLASSES[i], float(p[i])) for i in np.argsort(p)[::-1][:5]]
        self.lbl_symbol.config(text=top[0][0])
        self.lbl_best.config(text=f"Это «{top[0][0]}» с вероятностью {top[0][1]:.1%}")
        self.draw_bars(top)
        self.preview.delete("all")
        for i, v in enumerate(x):
            if v > 0.05:
                g = int(v * 255)
                cx, cy = (i % SIZE) * 3, (i // SIZE) * 3
                self.preview.create_rectangle(cx, cy, cx + 3, cy + 3, outline="", fill=f"#{g:02x}{g:02x}{g:02x}")

    def draw_bars(self, top):
        cv = self.bars
        cv.delete("all")
        for row, (ch, prob) in enumerate(top):
            y = 6 + row * 29
            cv.create_text(14, y + 11, text=ch, font=("TkDefaultFont", 14, "bold"))
            cv.create_rectangle(34, y, 34 + 220, y + 22, fill="#e0e0e0", outline="")
            cv.create_rectangle(34, y, 34 + 220 * prob, y + 22, outline="",
                                fill="#2e7d32" if row == 0 else "#90a4ae")
            cv.create_text(262, y + 11, text=f"{prob:.1%}", anchor="w")

    # --- обучение ----------------------------------------------------
    def add_sample(self):
        ch = self.true_var.get().strip().upper()
        x = normalize(self.image)
        if len(ch) != 1 or ch not in CLASSES:
            messagebox.showwarning("Дообучение", "Введите один символ: цифру или русскую букву.")
            return
        if x is None:
            messagebox.showwarning("Дообучение", "Сначала нарисуйте символ.")
            return
        xs, ys = load_user_samples()
        xs.append(x)
        ys.append(CLASSES.index(ch))
        np.savez_compressed(SAMPLES_FILE, x=np.array(xs, dtype=np.float32), y=np.array(ys))
        self.status_text = (f"Пример «{ch}» сохранён (всего своих примеров: {len(xs)}). "
                            f"Нажмите «Переобучить сеть», чтобы учесть их.")
        self.clear()

    def start_training(self):
        if self.training:
            return
        self.training = True
        self.ready = False
        self.btn_train.config(state="disabled")
        threading.Thread(target=self.training_thread, daemon=True).start()

    def training_thread(self):
        """Обучение идёт в отдельном потоке, чтобы окно не зависало."""
        def progress(text):
            self.status_text = text
        try:
            x, y, n_data, n_user = build_dataset(progress)
            net = Network()
            net.train(x, y, progress=progress)
            net.save(WEIGHTS_FILE)
            self.net = net
            self.status_text = (f"Сеть обучена: образцов в выборке – {n_data}, своих примеров – {n_user}, "
                                f"всего с искажёнными копиями – {len(x)}. Можно рисовать.")
        except Exception as e:
            self.status_text = f"Ошибка обучения: {e}"
        self.ready = True

    def update_status(self):
        """Раз в 0,2 с переносим сообщение из потока обучения на форму."""
        self.status.config(text=" " + self.status_text)
        if self.ready and self.training:          # обучение только что закончилось
            self.training = False
            self.btn_train.config(state="normal")
            self.recognize()
        self.root.after(200, self.update_status)


if __name__ == "__main__":
    root = tk.Tk()
    RecognitionApp(root)
    root.mainloop()
