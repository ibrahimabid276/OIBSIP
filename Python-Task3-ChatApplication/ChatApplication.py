import socket
import threading
import sqlite3
import json
import hashlib
import os
import re
from datetime import datetime

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except ImportError:
    tk = None

HOST = "127.0.0.1"
PORT = 6000
DB_FILE = "chat.db"

EMOJI_MAP = {
    ":smile:": "\U0001F604",
    ":laughing:": "\U0001F606",
    ":heart:": "\u2764\ufe0f",
    ":thumbsup:": "\U0001F44D",
    ":thumbsdown:": "\U0001F44E",
    ":fire:": "\U0001F525",
    ":cry:": "\U0001F622",
    ":thinking:": "\U0001F914",
    ":wave:": "\U0001F44B",
    ":tada:": "\U0001F389",
    ":eyes:": "\U0001F440",
    ":100:": "\U0001F4AF",
}


def render_emoji(text):
    def replace(m):
        return EMOJI_MAP.get(m.group(0), m.group(0))
    return re.sub(r":\w+:", replace, text)


# ===========================================================================
# SERVER
# ===========================================================================

lock = threading.Lock()
rooms = {}  # room_name -> list of connected sockets in that room


def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        salt TEXT NOT NULL,
        pw_hash TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room TEXT NOT NULL,
        username TEXT NOT NULL,
        text TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )""")
    conn.commit()
    conn.close()


def hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16).hex()
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return salt, h


def send_json(conn, obj):
    try:
        conn.sendall((json.dumps(obj) + "\n").encode())
    except OSError:
        pass


def broadcast(room, obj, exclude=None):
    with lock:
        for c in rooms.get(room, []):
            if c is not exclude:
                send_json(c, obj)


def handle_register(conn, data):
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        send_json(conn, {"type": "register_result", "ok": False, "error": "missing fields"})
        return

    conn_db = db()
    existing = conn_db.execute("SELECT username FROM users WHERE username=?", (username,)).fetchone()
    if existing:
        conn_db.close()
        send_json(conn, {"type": "register_result", "ok": False, "error": "username taken"})
        return

    salt, pw_hash = hash_password(password)
    conn_db.execute("INSERT INTO users (username, salt, pw_hash) VALUES (?, ?, ?)", (username, salt, pw_hash))
    conn_db.commit()
    conn_db.close()

    send_json(conn, {"type": "register_result", "ok": True})


def handle_login(conn, data):
    username = data.get("username", "").strip()
    password = data.get("password", "")

    conn_db = db()
    row = conn_db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn_db.close()

    if not row:
        send_json(conn, {"type": "login_result", "ok": False, "error": "no such user"})
        return

    _, pw_hash = hash_password(password, row["salt"])
    if pw_hash != row["pw_hash"]:
        send_json(conn, {"type": "login_result", "ok": False, "error": "wrong password"})
        return

    send_json(conn, {"type": "login_result", "ok": True, "username": username})


def handle_join(conn, data, client_info):
    room = data.get("room", "").strip()
    username = data.get("username", "anon")

    with lock:
        old_room = client_info.get("room")
        if old_room and conn in rooms.get(old_room, []):
            rooms[old_room].remove(conn)

        rooms.setdefault(room, [])
        if conn not in rooms[room]:
            rooms[room].append(conn)

    client_info["room"] = room
    client_info["username"] = username

    conn_db = db()
    history_rows = conn_db.execute(
        "SELECT username, text, timestamp FROM messages WHERE room=? ORDER BY id ASC LIMIT 50",
        (room,)
    ).fetchall()
    conn_db.close()

    history = [{"username": r["username"], "text": r["text"], "timestamp": r["timestamp"]} for r in history_rows]
    send_json(conn, {"type": "history", "room": room, "messages": history})

    broadcast(room, {"type": "status", "msg": f"{username} joined #{room}"}, exclude=conn)


def handle_message(conn, data, client_info):
    room = client_info.get("room")
    username = client_info.get("username", "anon")
    text = data.get("text", "")

    if not room or not text:
        return

    ts = datetime.now().strftime("%H:%M")

    conn_db = db()
    conn_db.execute(
        "INSERT INTO messages (room, username, text, timestamp) VALUES (?, ?, ?, ?)",
        (room, username, text, ts)
    )
    conn_db.commit()
    conn_db.close()

    broadcast(room, {"type": "message", "username": username, "text": text, "timestamp": ts})


def handle_client(conn, addr):
    client_info = {"room": None, "username": None}
    buffer = ""

    print(f"connected: {addr}")

    while True:
        try:
            chunk = conn.recv(4096)
        except OSError:
            chunk = None

        if not chunk:
            break

        buffer += chunk.decode()
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type")
            if msg_type == "register":
                handle_register(conn, data)
            elif msg_type == "login":
                handle_login(conn, data)
            elif msg_type == "join":
                handle_join(conn, data, client_info)
            elif msg_type == "message":
                handle_message(conn, data, client_info)

    room = client_info.get("room")
    username = client_info.get("username")
    with lock:
        if room and conn in rooms.get(room, []):
            rooms[room].remove(conn)

    if room and username:
        broadcast(room, {"type": "status", "msg": f"{username} disconnected"})

    print(f"disconnected: {addr}")
    conn.close()


def run_server():
    init_db()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(20)
    print(f"chat server listening on {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        t.start()


# ===========================================================================
# CLIENT (tkinter GUI)
# ===========================================================================

class ChatClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat")
        self.sock = None
        self.buffer = ""
        self.username = None
        self.room = None
        self.window_focused = True

        self.root.bind("<FocusIn>", self.on_focus_in)
        self.root.bind("<FocusOut>", self.on_focus_out)

        self.connect_to_server()
        self.build_auth_screen()

    def connect_to_server(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((HOST, PORT))
        except OSError as e:
            messagebox.showerror("Connection failed", f"couldn't reach server: {e}")
            self.root.destroy()
            return

        t = threading.Thread(target=self.listen_loop, daemon=True)
        t.start()

    def send_json(self, obj):
        try:
            self.sock.sendall((json.dumps(obj) + "\n").encode())
        except OSError:
            messagebox.showerror("Error", "lost connection to server")

    def listen_loop(self):
        while True:
            try:
                chunk = self.sock.recv(4096)
            except OSError:
                break
            if not chunk:
                break

            self.buffer += chunk.decode()
            while "\n" in self.buffer:
                line, self.buffer = self.buffer.split("\n", 1)
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self.root.after(0, self.handle_incoming, data)

    def handle_incoming(self, data):
        msg_type = data.get("type")

        if msg_type == "register_result":
            if data["ok"]:
                messagebox.showinfo("Registered", "account created, now log in")
            else:
                messagebox.showerror("Register failed", data.get("error", "unknown error"))

        elif msg_type == "login_result":
            if data["ok"]:
                self.username = data["username"]
                self.build_room_screen()
            else:
                messagebox.showerror("Login failed", data.get("error", "unknown error"))

        elif msg_type == "history":
            self.chat_box.config(state="normal")
            self.chat_box.delete("1.0", tk.END)
            for m in data["messages"]:
                self.append_line(f"[{m['timestamp']}] {m['username']}: {m['text']}")
            self.chat_box.config(state="disabled")

        elif msg_type == "message":
            self.append_line(f"[{data['timestamp']}] {data['username']}: {data['text']}")
            if data["username"] != self.username and not self.window_focused:
                self.flash_title()

        elif msg_type == "status":
            self.append_line(f"* {data['msg']}")

    def on_focus_in(self, event):
        self.window_focused = True
        self.root.title(f"Chat - #{self.room}" if self.room else "Chat")

    def on_focus_out(self, event):
        self.window_focused = False

    def flash_title(self):
        self.root.bell()
        self.root.title("New message! - Chat")

    def build_auth_screen(self):
        for w in self.root.winfo_children():
            w.destroy()

        frame = ttk.Frame(self.root, padding=20)
        frame.grid()

        ttk.Label(frame, text="Username").grid(row=0, column=0, sticky="w")
        self.user_entry = ttk.Entry(frame)
        self.user_entry.grid(row=0, column=1, pady=4)

        ttk.Label(frame, text="Password").grid(row=1, column=0, sticky="w")
        self.pass_entry = ttk.Entry(frame, show="*")
        self.pass_entry.grid(row=1, column=1, pady=4)

        ttk.Button(frame, text="Login", command=self.do_login).grid(row=2, column=0, pady=10)
        ttk.Button(frame, text="Register", command=self.do_register).grid(row=2, column=1, pady=10)

    def do_login(self):
        username = self.user_entry.get().strip()
        password = self.pass_entry.get()
        if not username or not password:
            messagebox.showwarning("Missing info", "enter a username and password")
            return
        self.send_json({"type": "login", "username": username, "password": password})

    def do_register(self):
        username = self.user_entry.get().strip()
        password = self.pass_entry.get()
        if not username or not password:
            messagebox.showwarning("Missing info", "enter a username and password")
            return
        self.send_json({"type": "register", "username": username, "password": password})

    def build_room_screen(self):
        for w in self.root.winfo_children():
            w.destroy()

        frame = ttk.Frame(self.root, padding=15)
        frame.grid()

        ttk.Label(frame, text=f"logged in as {self.username}").grid(row=0, column=0, sticky="w")
        ttk.Label(frame, text="Room name:").grid(row=1, column=0, sticky="w")
        self.room_entry = ttk.Entry(frame)
        self.room_entry.grid(row=1, column=1)
        ttk.Button(frame, text="Join / Create", command=self.do_join).grid(row=1, column=2, padx=5)

    def do_join(self):
        room = self.room_entry.get().strip()
        if not room:
            messagebox.showwarning("Missing room", "enter a room name")
            return
        self.room = room
        self.send_json({"type": "join", "room": room, "username": self.username})
        self.build_chat_screen()

    def build_chat_screen(self):
        for w in self.root.winfo_children():
            w.destroy()

        self.root.title(f"Chat - #{self.room}")

        frame = ttk.Frame(self.root, padding=10)
        frame.grid()

        ttk.Label(frame, text=f"#{self.room}  (logged in as {self.username})").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )

        self.chat_box = tk.Text(frame, width=60, height=20, state="disabled", wrap="word")
        self.chat_box.grid(row=1, column=0, columnspan=2, pady=8)

        self.msg_entry = ttk.Entry(frame, width=45)
        self.msg_entry.grid(row=2, column=0, pady=4)
        self.msg_entry.bind("<Return>", lambda e: self.do_send())

        ttk.Button(frame, text="Send", command=self.do_send).grid(row=2, column=1, padx=5)

    def do_send(self):
        text = self.msg_entry.get().strip()
        if not text:
            return
        text = render_emoji(text)
        self.send_json({"type": "message", "text": text})
        self.msg_entry.delete(0, tk.END)

    def append_line(self, line):
        self.chat_box.config(state="normal")
        self.chat_box.insert(tk.END, line + "\n")
        self.chat_box.see(tk.END)
        self.chat_box.config(state="disabled")


def run_client():
    if tk is None:
        print("tkinter isn't available on this system.")
        print("on Debian/Ubuntu, install it with: sudo apt install python3-tk")
        return
    root = tk.Tk()
    ChatClient(root)
    root.mainloop()


# ===========================================================================
# ENTRY POINT
# ===========================================================================

def main():
    print("chat app")
    print("1) start server")
    print("2) start client")

    while True:
        choice = input("pick one (1/2): ").strip()
        if choice == "1":
            run_server()
            break
        elif choice == "2":
            run_client()
            break
        else:
            print("just type 1 or 2")


if __name__ == "__main__":
    main()
