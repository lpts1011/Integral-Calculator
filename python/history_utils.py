import tkinter as tk


def add_history_record(history, history_listbox, record):
    history.append(record)
    history_listbox.delete(0, tk.END)
    for rec in history:
        history_listbox.insert(tk.END, rec["display"])
