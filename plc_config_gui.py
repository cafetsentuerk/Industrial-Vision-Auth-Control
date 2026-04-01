# plc_config_gui.py - Portrait Display Optimized v3 (Full Screen)

"""
PLC Konfiguration GUI - Portrait Version

ÖZELLİKLER:
✅ 5" Portrait ekran için optimize (700x1150)
✅ Tam ekran kullanımı (lacivert kenarlık yok)
✅ Dengeli layout
✅ Tüm özellikler korundu
"""

import tkinter as tk
from tkinter import messagebox, ttk
import threading

class PLCConfigGUI:
    def __init__(self, parent, config_manager, plc_controller):
        self.parent = parent
        self.config_manager = config_manager
        self.plc_controller = plc_controller
        
        self.window = tk.Toplevel(parent)
        self.window.title("PLC Konfiguration")
        
        # ✅ Portrait ekran için optimize
        self.window.geometry("700x1150")
        self.window.configure(bg="#ecf0f1")  # ✅ Artık tüm ekran açık gri
        self.window.transient(parent)
        self.window.grab_set()
        
        self.setup_ui()
    
    def setup_ui(self):
        # ✅ Ana Frame - Artık PADDING YOK, tam ekran
        main_frame = tk.Frame(self.window, bg="#ecf0f1")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Titel
        title = tk.Label(main_frame, text="🔌 PLC Konfiguration\n(PROFINET)", 
                        font=("Arial", 18, "bold"), bg="#ecf0f1", fg="#2c3e50")
        title.pack(pady=10)
        
        # === VERBINDUNGSEINSTELLUNGEN ===
        conn_frame = tk.LabelFrame(main_frame, text="VERBINDUNG",
                                   font=("Arial", 11, "bold"),
                                   bg="#ecf0f1", fg="#e74c3c",
                                   relief=tk.GROOVE, borderwidth=2)
        conn_frame.pack(fill=tk.X, pady=10, padx=10)
        
        # IP-Adresse
        ip_row = tk.Frame(conn_frame, bg="#ecf0f1")
        ip_row.pack(fill=tk.X, pady=8, padx=10)
        
        tk.Label(ip_row, text="IP-Adresse:", font=("Arial", 11, "bold"),
                bg="#ecf0f1", fg="#2c3e50", width=12, anchor="w").pack(side=tk.LEFT, padx=5)
        
        self.ip_entry = tk.Entry(ip_row, font=("Arial", 12), width=20)
        self.ip_entry.insert(0, self.plc_controller.ip)
        self.ip_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Rack/Slot
        rs_row = tk.Frame(conn_frame, bg="#ecf0f1")
        rs_row.pack(fill=tk.X, pady=8, padx=10)
        
        # Rack
        rack_frame = tk.Frame(rs_row, bg="#ecf0f1")
        rack_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        tk.Label(rack_frame, text="Rack:", font=("Arial", 11, "bold"),
                bg="#ecf0f1", fg="#2c3e50").pack(side=tk.LEFT, padx=5)
        
        self.rack_entry = tk.Entry(rack_frame, font=("Arial", 12), width=8)
        self.rack_entry.insert(0, str(self.plc_controller.rack))
        self.rack_entry.pack(side=tk.LEFT, padx=5)
        
        # Slot
        slot_frame = tk.Frame(rs_row, bg="#ecf0f1")
        slot_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        tk.Label(slot_frame, text="Slot:", font=("Arial", 11, "bold"),
                bg="#ecf0f1", fg="#2c3e50").pack(side=tk.LEFT, padx=5)
        
        self.slot_entry = tk.Entry(slot_frame, font=("Arial", 12), width=8)
        self.slot_entry.insert(0, str(self.plc_controller.slot))
        self.slot_entry.pack(side=tk.LEFT, padx=5)
        
        # Test-Button + Status
        btn_row = tk.Frame(conn_frame, bg="#ecf0f1")
        btn_row.pack(fill=tk.X, pady=10, padx=10)
        
        self.test_btn = tk.Button(btn_row, text="🔌 Verbindung testen",
                                  font=("Arial", 11, "bold"),
                                  bg="#3498db", fg="white",
                                  height=2,
                                  command=self.test_connection)
        self.test_btn.pack(fill=tk.X, pady=5)
        
        self.status_label = tk.Label(btn_row, text="● Nicht verbunden",
                                     font=("Arial", 11, "bold"), 
                                     bg="#ecf0f1", fg="#e74c3c")
        self.status_label.pack(pady=5)
        
        # === INFO ===
        info_frame = tk.Frame(main_frame, bg="#34495e", relief=tk.GROOVE, borderwidth=2)
        info_frame.pack(fill=tk.X, pady=10, padx=10)
        
        info_label = tk.Label(info_frame,
                             text="💡 Adress-Format: M0.0 | DB1.DBX0.0 | DB1.DBW0 | DB1.DBD0\n"
                                  "📌 Modi: PULSE(10s) | SET | RESET | TOGGLE | ANALOG",
                             font=("Arial", 9, "italic"), bg="#34495e", fg="white", 
                             justify=tk.LEFT, padx=10, pady=8)
        info_label.pack()
        
        # === GESTEN-ZUORDNUNG ===
        mapping_frame = tk.LabelFrame(main_frame, text="GESTEN → PLC-ADRESSEN",
                                     font=("Arial", 12, "bold"),
                                     bg="#ecf0f1", fg="#27ae60",
                                     relief=tk.GROOVE, borderwidth=2)
        mapping_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)
        
        # Scrollable Tabelle
        table_container = tk.Frame(mapping_frame, bg="#ecf0f1")
        table_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Canvas + Scrollbar
        canvas = tk.Canvas(table_container, bg="#ecf0f1", highlightthickness=0)
        scrollbar = tk.Scrollbar(table_container, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg="#ecf0f1")
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.populate_gesture_list()
        
        # === SPEICHERN/SCHLIESSEN ===
        bottom_frame = tk.Frame(main_frame, bg="#ecf0f1")
        bottom_frame.pack(fill=tk.X, pady=10, padx=10)
        
        tk.Button(bottom_frame, text="💾 Speichern & Schließen",
                 font=("Arial", 12, "bold"),
                 bg="#27ae60", fg="white",
                 height=2,
                 command=self.save_and_close).pack(fill=tk.X, pady=3)
        
        tk.Button(bottom_frame, text="❌ Abbrechen",
                 font=("Arial", 12, "bold"),
                 bg="#95a5a6", fg="white",
                 height=2,
                 command=self.window.destroy).pack(fill=tk.X, pady=3)
    
    def populate_gesture_list(self):
        """Alle Gesten mit PLC-Adress-Eingabefeldern auflisten"""
        # Clear existing
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.plc_entries = {}
        self.mode_combos = {}
        self.analog_entries = {}
        
        row = 0
        
        # Header
        headers = [
            ("GESTE", 0, 18),
            ("PLC-ADRESSE", 1, 15),
            ("MODE", 2, 10),
            ("WERT", 3, 8)
        ]
        
        for text, col, width in headers:
            tk.Label(self.scrollable_frame, text=text, font=("Arial", 9, "bold"),
                    bg="#34495e", fg="white", width=width, anchor="w",
                    relief=tk.RAISED, borderwidth=1).grid(
                        row=row, column=col, sticky="ew", padx=1, pady=2)
        
        row += 1
        
        # 1. Builtin Gesten
        builtin_gestures = self.config_manager.get_builtin_gestures()
        
        for gesture_id, info in builtin_gestures.items():
            if info.get("enabled", 0) == 1:
                row = self._add_gesture_row(row, gesture_id, info, is_builtin=True)
        
        # 2. Custom Gesten
        from gesture_engine import GestureModel
        model = GestureModel()
        stats = model.get_class_stats()
        builtin_ids = builtin_gestures.keys()
        
        for gesture_name, count in stats.items():
            if gesture_name in builtin_ids:
                continue
            
            custom_info = self.config_manager.get_custom_gesture_info(gesture_name)
            row = self._add_gesture_row(row, gesture_name, custom_info, is_builtin=False)
    
    def _add_gesture_row(self, row, gesture_id, info, is_builtin=True):
        """Einzelne Gesture-Zeile hinzufügen"""
        if is_builtin:
            display_name = info.get("display_name", gesture_id)
            icon = "🏭"
        else:
            display_name = info.get("display_name", gesture_id)
            icon = "📝"
        
        # Hintergrundfarbe (abwechselnd)
        bg_color = "#ffffff" if row % 2 == 0 else "#f8f9fa"
        
        # Gesture Name
        name_text = f"{icon} {display_name}"
        if len(name_text) > 20:
            name_text = name_text[:17] + "..."
        
        name_label = tk.Label(self.scrollable_frame,
                             text=name_text,
                             font=("Arial", 9), bg=bg_color, anchor="w",
                             padx=3)
        name_label.grid(row=row, column=0, sticky="ew", padx=1, pady=1)
        
        # PLC Address Entry
        plc_address, plc_mode, analog_value = self.plc_controller.get_mapping(gesture_id)
        
        plc_entry = tk.Entry(self.scrollable_frame, font=("Arial", 9), 
                            bg=bg_color, relief=tk.SOLID, borderwidth=1)
        plc_entry.insert(0, plc_address)
        plc_entry.grid(row=row, column=1, sticky="ew", padx=1, pady=1)
        
        # MODE Combobox
        mode_combo = ttk.Combobox(self.scrollable_frame,
                                  values=["PULSE", "SET", "RESET", "TOGGLE", "ANALOG"],
                                  state="readonly", font=("Arial", 9), width=10)
        mode_combo.set(plc_mode)
        mode_combo.grid(row=row, column=2, sticky="ew", padx=1, pady=1)
        
        # ANALOG Value Entry
        analog_entry = tk.Entry(self.scrollable_frame, font=("Arial", 9),
                               bg=bg_color, relief=tk.SOLID, borderwidth=1)
        if analog_value is not None:
            analog_entry.insert(0, str(analog_value))
        else:
            analog_entry.insert(0, "0")
        analog_entry.grid(row=row, column=3, sticky="ew", padx=1, pady=1)
        
        # Mode değiştiğinde analog field'i highlight
        def on_mode_change(event):
            if mode_combo.get() == "ANALOG":
                analog_entry.config(bg="#ffffcc", fg="black")
            else:
                analog_entry.config(bg=bg_color, fg="gray")
        
        mode_combo.bind("<<ComboboxSelected>>", on_mode_change)
        on_mode_change(None)
        
        self.plc_entries[gesture_id] = plc_entry
        self.mode_combos[gesture_id] = mode_combo
        self.analog_entries[gesture_id] = analog_entry
        
        return row + 1
    
    def test_connection(self):
        """PLC-Verbindung testen"""
        self.plc_controller.ip = self.ip_entry.get().strip()
        
        try:
            self.plc_controller.rack = int(self.rack_entry.get())
            self.plc_controller.slot = int(self.slot_entry.get())
        except:
            messagebox.showerror("Fehler", "Rack und Slot müssen Zahlen sein!")
            return
        
        self.test_btn.config(state="disabled", text="⏳ Teste...")
        self.status_label.config(text="● Verbindung wird getestet...", fg="#f39c12")
        
        def test_thread():
            success = self.plc_controller.test_connection()
            
            self.window.after(0, lambda: self.test_btn.config(
                state="normal", text="🔌 Verbindung testen"))
            
            if success:
                self.window.after(0, lambda: self.status_label.config(
                    text="● Verbunden", fg="#27ae60"))
                self.window.after(0, lambda: messagebox.showinfo(
                    "Erfolg", 
                    f"Verbindung zu {self.plc_controller.ip} erfolgreich!"))
            else:
                self.window.after(0, lambda: self.status_label.config(
                    text="● Verbindung fehlgeschlagen", fg="#e74c3c"))
                self.window.after(0, lambda: messagebox.showerror(
                    "Fehler", 
                    f"Keine Verbindung zu {self.plc_controller.ip} möglich!\n\n"
                    "Überprüfen Sie:\n"
                    "• IP-Adresse korrekt?\n"
                    "• PLC eingeschaltet?\n"
                    "• Netzwerkverbindung?"))
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def save_and_close(self):
        """PLC-Zuordnungen speichern"""
        # IP/Rack/Slot speichern
        self.plc_controller.ip = self.ip_entry.get().strip()
        
        try:
            self.plc_controller.rack = int(self.rack_entry.get())
            self.plc_controller.slot = int(self.slot_entry.get())
        except:
            messagebox.showerror("Fehler", "Rack und Slot müssen Zahlen sein!")
            return
        
        # Alle Zuordnungen speichern
        for gesture_id, entry in self.plc_entries.items():
            plc_address = entry.get().strip()
            plc_mode = self.mode_combos[gesture_id].get()
            
            analog_value = None
            if plc_mode == "ANALOG":
                try:
                    analog_value = int(self.analog_entries[gesture_id].get())
                except:
                    messagebox.showerror("Fehler",
                                       f"Ungültiger ANALOG-Wert für '{gesture_id}'!\n\n"
                                       f"Bitte eine Zahl eingeben.")
                    return
            
            self.plc_controller.update_mapping(gesture_id, plc_address, plc_mode, analog_value)
        
        # Config speichern
        self.plc_controller.save_plc_config()
        
        messagebox.showinfo("Gespeichert",
                          "✅ PLC-Konfiguration wurde gespeichert!\n\n"
                          "💡 Tipp: Drücken Sie 'r' im Hauptprogramm\n"
                          "    zum Neuladen der Konfiguration.")
        
        self.window.destroy()
