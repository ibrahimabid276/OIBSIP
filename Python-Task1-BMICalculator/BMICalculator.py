import sqlite3
from datetime import datetime

DB_FILE = "bmi_records.db"


def get_category(bmi):
    if bmi < 18.5:
        return "Underweight", "#3b82f6"
    elif bmi < 25:
        return "Normal", "#22c55e"
    elif bmi < 30:
        return "Overweight", "#f59e0b"
    else:
        return "Obese", "#ef4444"


def get_number(prompt):
    while True:
        val = input(prompt)
        try:
            val = float(val)
        except ValueError:
            print("that's not a number, try again")
            continue

        if val <= 0:
            print("has to be more than 0")
            continue

        return val


def run_cli():
    weight = get_number("weight in kg: ")
    height = get_number("height in m: ")

    bmi = weight / (height * height)
    category, _ = get_category(bmi)

    print(f"\nyour bmi is {bmi:.2f}")
    print(f"category: {category}")


def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            weight REAL,
            height REAL,
            bmi REAL,
            category TEXT,
            recorded_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_record(username, weight, height, bmi, category):
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "INSERT INTO records (username, weight, height, bmi, category, recorded_at) VALUES (?, ?, ?, ?, ?, ?)",
        (username, weight, height, bmi, category, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()


def load_history(username):
    conn = sqlite3.connect(DB_FILE)
    rows = conn.execute(
        "SELECT recorded_at, bmi FROM records WHERE username=? ORDER BY recorded_at ASC",
        (username,)
    ).fetchall()
    conn.close()
    return rows


def run_gui():
    import tkinter as tk
    from tkinter import ttk, messagebox
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    class BMIApp(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("BMI Calculator")
            self.geometry("460x540")
            self.configure(bg="#1e1e2e")

            try:
                init_db()
            except sqlite3.Error as e:
                messagebox.showerror("DB error", f"couldn't set up the database:\n{e}")
                self.destroy()
                return

            tk.Label(self, text="BMI Calculator", font=("Segoe UI", 16, "bold"),
                     bg="#1e1e2e", fg="white").pack(pady=15)

            form = tk.Frame(self, bg="#1e1e2e")
            form.pack(pady=5)

            tk.Label(form, text="Name", bg="#1e1e2e", fg="white").grid(row=0, column=0, sticky="w", pady=5, padx=5)
            self.name_entry = ttk.Entry(form)
            self.name_entry.grid(row=0, column=1, pady=5)

            tk.Label(form, text="Weight (kg)", bg="#1e1e2e", fg="white").grid(row=1, column=0, sticky="w", pady=5, padx=5)
            self.weight_entry = ttk.Entry(form)
            self.weight_entry.grid(row=1, column=1, pady=5)

            tk.Label(form, text="Height (m)", bg="#1e1e2e", fg="white").grid(row=2, column=0, sticky="w", pady=5, padx=5)
            self.height_entry = ttk.Entry(form)
            self.height_entry.grid(row=2, column=1, pady=5)

            ttk.Button(self, text="Calculate", command=self.calculate).pack(pady=10)

            self.result_lbl = tk.Label(self, text="", font=("Segoe UI", 20, "bold"), bg="#1e1e2e", fg="white")
            self.result_lbl.pack()

            self.category_lbl = tk.Label(self, text="", font=("Segoe UI", 13), bg="#1e1e2e", fg="white")
            self.category_lbl.pack(pady=(0, 10))

            ttk.Button(self, text="Show Trend Chart", command=self.show_chart).pack(pady=5)

            self.chart_area = tk.Frame(self, bg="#1e1e2e")
            self.chart_area.pack(fill="both", expand=True, padx=10, pady=10)

        def calculate(self):
            name = self.name_entry.get().strip()
            if not name:
                messagebox.showerror("Missing name", "type a name first")
                return

            try:
                weight = float(self.weight_entry.get())
                height = float(self.height_entry.get())
            except ValueError:
                messagebox.showerror("Bad input", "weight and height need to be numbers")
                return

            if weight <= 0 or height <= 0:
                messagebox.showerror("Bad input", "weight and height need to be positive")
                return

            bmi = weight / (height ** 2)
            category, color = get_category(bmi)

            self.result_lbl.config(text=f"BMI: {bmi:.2f}", fg=color)
            self.category_lbl.config(text=category, fg=color)

            try:
                save_record(name, weight, height, bmi, category)
            except sqlite3.Error as e:
                messagebox.showerror("DB error", f"couldn't save that record:\n{e}")

        def show_chart(self):
            name = self.name_entry.get().strip()
            if not name:
                messagebox.showerror("Missing name", "type a name to look up first")
                return

            try:
                history = load_history(name)
            except sqlite3.Error as e:
                messagebox.showerror("DB error", f"couldn't load history:\n{e}")
                return

            if not history:
                messagebox.showinfo("No data", f"nothing saved for '{name}' yet")
                return

            for widget in self.chart_area.winfo_children():
                widget.destroy()

            dates = [row[0][5:10] for row in history]
            bmis = [row[1] for row in history]

            fig = Figure(figsize=(4.2, 3), dpi=100)
            ax = fig.add_subplot(111)
            ax.plot(bmis, marker="o")
            ax.set_title(f"{name}'s BMI over time")
            ax.set_ylabel("BMI")
            ax.set_xticks(range(len(dates)))
            ax.set_xticklabels(dates, rotation=45, fontsize=7)
            fig.tight_layout()

            canvas = FigureCanvasTkAgg(fig, master=self.chart_area)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)

    app = BMIApp()
    app.mainloop()


if __name__ == "__main__":
    print("BMI Calculator")
    print("1. CLI (command line)")
    print("2. GUI (window)")

    choice = input("pick 1 or 2: ").strip()

    while choice not in ("1", "2"):
        choice = input("just type 1 or 2: ").strip()

    if choice == "1":
        run_cli()
    else:
        run_gui()
