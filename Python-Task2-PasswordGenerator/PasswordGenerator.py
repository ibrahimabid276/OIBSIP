import random
import string

ambiguous = "0Ol1I"
symbols = "!@#$%^&*()-_=+[]{};:,.<>?/"


def ask_length():
    while True:
        val = input("Password length (min 8): ").strip()
        if not val.isdigit():
            print("enter a number")
            continue
        val = int(val)
        if val < 8:
            print("min is 8")
            continue
        return val


def ask_types():
    print("\npick at least 2:")
    print("1) uppercase")
    print("2) lowercase")
    print("3) numbers")
    print("4) symbols")

    while True:
        choice = input("choices (comma separated): ").strip()
        picks = [c.strip() for c in choice.split(",") if c.strip()]

        if any(p not in ["1", "2", "3", "4"] for p in picks):
            print("only 1-4")
            continue
        if len(set(picks)) < 2:
            print("need at least 2")
            continue

        pools = []
        if "1" in picks:
            pools.append(string.ascii_uppercase)
        if "2" in picks:
            pools.append(string.ascii_lowercase)
        if "3" in picks:
            pools.append(string.digits)
        if "4" in picks:
            pools.append(symbols)

        return pools


def make_password(length, pools):
    pw = []
    for p in pools:
        pw.append(random.choice(p))

    all_chars = ""
    for p in pools:
        all_chars += p

    while len(pw) < length:
        pw.append(random.choice(all_chars))

    random.shuffle(pw)
    return "".join(pw)


def run_cli():
    print("password generator")
    while True:
        length = ask_length()
        pools = ask_types()
        pw = make_password(length, pools)
        print("\n" + pw + "\n")

        if input("another one? (y/n) ").lower() != "y":
            break


def run_gui():
    import secrets
    import tkinter as tk
    from tkinter import ttk, messagebox

    try:
        import pyperclip
        have_clipboard = True
    except ImportError:
        have_clipboard = False

    last_passwords = []

    root = tk.Tk()
    root.title("Password Generator")

    upper_var = tk.BooleanVar(value=True)
    lower_var = tk.BooleanVar(value=True)
    digit_var = tk.BooleanVar(value=True)
    symbol_var = tk.BooleanVar(value=True)
    exclude_var = tk.BooleanVar(value=False)
    length_var = tk.IntVar(value=16)
    result_var = tk.StringVar()

    tk.Label(root, text="Length").grid(row=0, column=0, sticky="w")
    tk.Spinbox(root, from_=8, to=128, textvariable=length_var, width=5).grid(row=0, column=1)

    tk.Checkbutton(root, text="Uppercase", variable=upper_var).grid(row=1, column=0, columnspan=2, sticky="w")
    tk.Checkbutton(root, text="Lowercase", variable=lower_var).grid(row=2, column=0, columnspan=2, sticky="w")
    tk.Checkbutton(root, text="Numbers", variable=digit_var).grid(row=3, column=0, columnspan=2, sticky="w")
    tk.Checkbutton(root, text="Symbols", variable=symbol_var).grid(row=4, column=0, columnspan=2, sticky="w")
    tk.Checkbutton(root, text="No ambiguous chars (0/O, 1/l/I)", variable=exclude_var).grid(row=5, column=0, columnspan=2, sticky="w")

    entry = tk.Entry(root, textvariable=result_var, width=30, justify="center")
    entry.grid(row=7, column=0, columnspan=2, pady=5)

    strength_lbl = tk.Label(root, text="")
    strength_lbl.grid(row=9, column=0, columnspan=2)

    bar = ttk.Progressbar(root, length=200, maximum=100)
    bar.grid(row=10, column=0, columnspan=2, pady=5)

    history_box = tk.Listbox(root, height=5, width=35)
    history_box.grid(row=12, column=0, columnspan=2, pady=5)

    def get_pools():
        pools = []
        if upper_var.get():
            pools.append(string.ascii_uppercase)
        if lower_var.get():
            pools.append(string.ascii_lowercase)
        if digit_var.get():
            pools.append(string.digits)
        if symbol_var.get():
            pools.append(symbols)

        if exclude_var.get():
            new_pools = []
            for p in pools:
                cleaned = ""
                for ch in p:
                    if ch not in ambiguous:
                        cleaned += ch
                if cleaned != "":
                    new_pools.append(cleaned)
            pools = new_pools

        return pools

    def gen_secure(length, pools):
        pw = [secrets.choice(p) for p in pools]
        all_chars = "".join(pools)
        while len(pw) < length:
            pw.append(secrets.choice(all_chars))

    
        i = len(pw) - 1
        while i > 0:
            j = secrets.randbelow(i + 1)
            pw[i], pw[j] = pw[j], pw[i]
            i -= 1

        return "".join(pw)

    def check_strength(pw, pools):
        score = min(100, int(len(pw) / 20 * 60) + len(pools) * 10)
        if score < 40:
            return score, "Weak", "red"
        elif score < 75:
            return score, "Medium", "orange"
        else:
            return score, "Strong", "green"

    def on_generate():
        length = length_var.get()
        if length < 8:
            messagebox.showerror("Error", "length needs to be 8 or more")
            return

        pools = get_pools()
        if len(pools) < 2:
            messagebox.showerror("Error", "select at least 2 char types")
            return

        pw = gen_secure(length, pools)
        result_var.set(pw)

        score, label, color = check_strength(pw, pools)
        strength_lbl.config(text=f"Strength: {label}", fg=color)
        bar["value"] = score

        last_passwords.insert(0, pw)
        if len(last_passwords) > 5:
            last_passwords.pop()

        history_box.delete(0, tk.END)
        for p in last_passwords:
            history_box.insert(tk.END, p)

        if have_clipboard:
            pyperclip.copy(pw)

    def on_copy():
        pw = result_var.get()
        if pw == "":
            messagebox.showinfo("Info", "nothing generated yet")
            return
        if have_clipboard:
            pyperclip.copy(pw)
            messagebox.showinfo("Copied", "password copied")
        else:
            messagebox.showwarning("Missing", "install pyperclip first")

    gen_btn = tk.Button(root, text="Generate", command=on_generate)
    gen_btn.grid(row=6, column=0, columnspan=2, pady=5)

    copy_btn = tk.Button(root, text="Copy to Clipboard", command=on_copy)
    copy_btn.grid(row=8, column=0, columnspan=2, pady=5)
    if not have_clipboard:
        copy_btn.config(state="disabled")

    root.mainloop()


def main():
    print("password generator")
    print("1) cli")
    print("2) gui")

    while True:
        choice = input("pick one (1/2): ").strip()
        if choice == "1":
            run_cli()
            break
        elif choice == "2":
            run_gui()
            break
        else:
            print("just type 1 or 2")


if __name__ == "__main__":
    main()
