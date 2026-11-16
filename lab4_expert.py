# -*- coding: utf-8 -*-
"""
Лабораторная работа 4. Экспертная система, реализующая продукционную модель
представления знаний.

Предметная область – выбор языка программирования.
База знаний хранится в отдельном файле lab4_kb.xml (вопросы и правила
«ЕСЛИ условие, ТО действие»). Программа от предметной области не зависит:
можно загрузить любую другую базу того же формата.

Состав ЭС:
- база знаний          – XML-файл;
- рабочая память       – ответы пользователя + выведенные факты;
- решатель             – прямой вывод по правилам (функция infer);
- подсистема объяснений – цепочка сработавших правил;
- интерфейс            – диалог с кнопками «Назад» / «Далее».

Только стандартная библиотека. Запуск:  python lab4_expert.py
"""
import os
import tkinter as tk
import xml.etree.ElementTree as ET
from tkinter import ttk, filedialog, messagebox

KB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lab4_kb.xml")


# ----------------------------------------------------------------------
#  База знаний
# ----------------------------------------------------------------------
class KnowledgeBase:
    def __init__(self, path):
        root = ET.parse(path).getroot()
        self.title = root.get("title", "Экспертная система")

        # вопросы: id -> (текст, {id ответа: текст ответа})
        self.questions = {}
        for q in root.find("questions"):
            self.questions[q.get("id")] = (q.get("text"), {a.get("id"): a.text.strip() for a in q})

        # правила: (i); Q; ЕСЛИ P ТО B
        self.rules = []
        for r in root.find("rules"):
            then = r.find("then")
            self.rules.append({
                "id": r.get("id"),
                "scope": r.get("scope", ""),
                "if": [(c.get("fact"), c.get("value")) for c in r.findall("if")],
                "advice": then.get("advice"),                       # совет или None
                "fact": (then.get("fact"), then.get("value")),      # новый факт
                "text": (then.text or "").strip(),
            })
        # описания выводимых фактов – для объяснений
        self.fact_text = {r["fact"]: r["text"] for r in self.rules if not r["advice"]}
        self.advices = sorted({r["advice"] for r in self.rules if r["advice"]})

    def describe(self, fact, value):
        """Текст факта на русском языке."""
        if fact in self.questions:
            text, answers = self.questions[fact]
            return f"«{text}» = «{answers.get(value, value)}»"
        return self.fact_text.get((fact, value), f"{fact} = {value}")

    def rule_text(self, rule):
        cond = " И ".join(self.describe(f, v) for f, v in rule["if"])
        result = f"СОВЕТ: {rule['advice']}" if rule["advice"] else rule["text"]
        return f"[{rule['id']}; {rule['scope']}]\nЕСЛИ {cond}\nТО {result}"


# ----------------------------------------------------------------------
#  Решатель (механизм вывода)
# ----------------------------------------------------------------------
def infer(kb, answers):
    """
    Прямой вывод. answers – список (вопрос, ответ) в порядке диалога.
    Возвращает (рабочая память, сработавшие правила, правило-совет | None,
                следующий вопрос | None).
    """
    memory = dict(answers)
    fired = []
    changed = True
    while changed:                               # применяем правила, пока появляются новые факты
        changed = False
        for rule in kb.rules:
            if rule in fired or not all(memory.get(f) == v for f, v in rule["if"]):
                continue
            fired.append(rule)
            if rule["advice"]:
                return memory, fired, rule, None
            memory[rule["fact"][0]] = rule["fact"][1]
            changed = True

    # Совета ещё нет: ищем правило, которому не хватает ответа на вопрос
    for rule in kb.rules:
        if rule in fired:
            continue
        if any(f in memory and memory[f] != v for f, v in rule["if"]):
            continue                             # правило противоречит известным фактам
        unknown = [f for f, _ in rule["if"] if f not in memory]
        if unknown and unknown[0] in kb.questions:
            return memory, fired, None, unknown[0]
    return memory, fired, None, None


# ----------------------------------------------------------------------
#  Интерфейс
# ----------------------------------------------------------------------
class ExpertApp:
    def __init__(self, root):
        self.root = root
        root.geometry("980x560")
        root.minsize(860, 500)

        top = ttk.Frame(root)
        top.pack(fill="x", padx=10, pady=(8, 0))
        self.lbl_kb = ttk.Label(top, text="", foreground="#555")
        self.lbl_kb.pack(side="left")
        ttk.Button(top, text="Загрузить базу знаний…", command=self.open_kb).pack(side="right")
        ttk.Button(top, text="Правила базы знаний", command=self.show_rules).pack(side="right", padx=6)

        body = ttk.Frame(root)
        body.pack(fill="both", expand=True, padx=10, pady=8)

        # диалог
        self.dialog = ttk.LabelFrame(body, text="Консультация")
        self.dialog.pack(side="left", fill="both", expand=True)
        self.content = ttk.Frame(self.dialog)
        self.content.pack(fill="both", expand=True, padx=12, pady=10)
        nav = ttk.Frame(self.dialog)
        nav.pack(fill="x", padx=12, pady=(0, 10))
        self.btn_back = ttk.Button(nav, text="← Назад", command=self.back)
        self.btn_back.pack(side="left")
        self.btn_next = ttk.Button(nav, text="Далее →", command=self.next)
        self.btn_next.pack(side="left", padx=6)
        ttk.Button(nav, text="Начать заново", command=self.restart).pack(side="right")

        # рабочая память
        side = ttk.LabelFrame(body, text="Рабочая память (известные факты)")
        side.pack(side="left", fill="y", padx=(10, 0))
        self.memory_box = tk.Text(side, width=42, wrap="word", state="disabled",
                                  relief="flat", background="#f7f7f7", font="TkDefaultFont")
        self.memory_box.pack(fill="both", expand=True, padx=6, pady=6)
        self.memory_box.tag_config("derived", foreground="#1565c0")

        self.choice = tk.StringVar()
        self.load(KB_FILE)

    # --- база знаний -------------------------------------------------
    def load(self, path):
        try:
            self.kb = KnowledgeBase(path)
        except Exception as e:                    # нет файла или ошибка в XML
            messagebox.showerror("База знаний", f"Не удалось загрузить {path}:\n{e}")
            if not hasattr(self, "kb"):
                self.root.destroy()
            return
        self.root.title(f"Лабораторная работа 4 — Экспертная система «{self.kb.title}»")
        self.lbl_kb.config(text=f"База знаний: {os.path.basename(path)} — вопросов: {len(self.kb.questions)}, "
                                f"правил: {len(self.kb.rules)}, советов: {len(self.kb.advices)}")
        self.restart()

    def open_kb(self):
        path = filedialog.askopenfilename(filetypes=[("База знаний XML", "*.xml")])
        if path:
            self.load(path)

    def show_rules(self):
        win = tk.Toplevel(self.root)
        win.title("Правила базы знаний")
        win.geometry("760x520")
        text = tk.Text(win, wrap="word", font="TkDefaultFont")
        sb = ttk.Scrollbar(win, command=text.yview)
        text.config(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        text.pack(fill="both", expand=True)
        text.insert("end", "\n\n".join(self.kb.rule_text(r) for r in self.kb.rules))
        text.config(state="disabled")

    # --- диалог ------------------------------------------------------
    def restart(self):
        self.answers = []          # данные ответы: [(вопрос, ответ)]
        self.future = []           # ответы, от которых вернулись кнопкой «Назад»
        self.show()

    def back(self):
        if self.answers:
            self.future.append(self.answers.pop())
            self.show()

    def next(self):
        if self.question is None or not self.choice.get():
            return
        answer = (self.question, self.choice.get())
        if self.future and self.future[-1] == answer:
            self.future.pop()      # идём вперёд по уже пройденному пути
        else:
            self.future = []       # ответ изменился – старое продолжение неактуально
        self.answers.append(answer)
        self.show()

    def show(self):
        memory, fired, advice, self.question = infer(self.kb, self.answers)
        for w in self.content.winfo_children():
            w.destroy()

        if advice:
            self.show_advice(advice, fired)
        elif self.question:
            text, options = self.kb.questions[self.question]
            ttk.Label(self.content, text=f"Вопрос {len(self.answers) + 1}", foreground="#777").pack(anchor="w")
            ttk.Label(self.content, text=text, font=("TkDefaultFont", 13, "bold"),
                      wraplength=480, justify="left").pack(anchor="w", pady=(2, 12))
            # при возврате назад подставляем ранее выбранный ответ
            prev = self.future[-1][1] if self.future and self.future[-1][0] == self.question else ""
            self.choice.set(prev)
            for aid, atext in options.items():
                ttk.Radiobutton(self.content, text=atext, value=aid, variable=self.choice).pack(anchor="w", pady=3)
        else:
            ttk.Label(self.content, text="В базе знаний нет подходящего совета.",
                      font=("TkDefaultFont", 13, "bold")).pack(anchor="w")

        self.btn_back.config(state="normal" if self.answers else "disabled")
        self.btn_next.config(state="normal" if self.question else "disabled")
        self.show_memory(memory)

    def show_advice(self, rule, fired):
        ttk.Label(self.content, text="Рекомендация экспертной системы:", foreground="#777").pack(anchor="w")
        ttk.Label(self.content, text=rule["advice"], font=("TkDefaultFont", 20, "bold"),
                  foreground="#2e7d32").pack(anchor="w", pady=(2, 6))
        ttk.Label(self.content, text=rule["text"], wraplength=500, justify="left").pack(anchor="w")
        ttk.Label(self.content, text="Объяснение (сработавшие правила):",
                  foreground="#777").pack(anchor="w", pady=(14, 2))
        box = tk.Text(self.content, height=10, wrap="word", relief="flat", background="#f7f7f7",
                      font="TkDefaultFont")
        box.pack(fill="both", expand=True)
        box.insert("end", "\n\n".join(self.kb.rule_text(r) for r in fired))
        box.config(state="disabled")

    def show_memory(self, memory):
        box = self.memory_box
        box.config(state="normal")
        box.delete("1.0", "end")
        for fact, value in memory.items():
            if fact in self.kb.questions:
                text, answers = self.kb.questions[fact]
                box.insert("end", f"{text}\n   → {answers[value]}\n\n")
            else:
                box.insert("end", f"Вывод: {self.kb.describe(fact, value)}\n\n", "derived")
        box.config(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    ExpertApp(root)
    root.mainloop()
