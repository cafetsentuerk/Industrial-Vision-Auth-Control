# gesture_editor_dialogs.py - Vollstaendige Bearbeitung fuer Custom-Gesten

"""
Bearbeitungsfenster für die Gesture Training GUI

NEUE FUNKTIONEN:
- channel/GPIO/action_text auch fuer Custom-Gesten hinzugefuegt
- Gleiches Bearbeitungssystem wie bei Builtin-Gesten
- NEU: Beim Factory Reset werden Beispieldaten fuer Builtin-Gesten hinzugefuegt
"""

import tkinter as tk
from tkinter import messagebox, ttk
import numpy as np

class BuiltinGestureEditor:
    """Bearbeitungsfenster für Builtin-Gesten"""
    
    def __init__(self, parent, gesture_id, gesture_info, config_manager, callback=None):
        self.parent = parent
        self.gesture_id = gesture_id
        self.gesture_info = gesture_info
        self.config_manager = config_manager
        self.callback = callback
    
    def open(self):
        """Bearbeitungsfenster oeffnen"""
        self.edit_win = tk.Toplevel(self.parent)
        self.edit_win.title(f"Geste bearbeiten: {self.gesture_info.get('display_name', self.gesture_id)}")
        self.edit_win.geometry("500x550")
        self.edit_win.transient(self.parent)
        self.edit_win.grab_set()
        
        tk.Label(self.edit_win, text=f"Geste: {self.gesture_info.get('display_name', self.gesture_id)}", 
                font=("Arial", 14, "bold")).pack(pady=15)
        
        # Display Name
        name_frame = tk.Frame(self.edit_win)
        name_frame.pack(pady=10, padx=20, fill=tk.X)
        tk.Label(name_frame, text="Anzeigename:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.name_entry = tk.Entry(name_frame, font=("Arial", 11), width=30)
        self.name_entry.insert(0, self.gesture_info.get("display_name", ""))
        self.name_entry.pack(fill=tk.X, pady=5)
        
        # Action Text
        action_frame = tk.Frame(self.edit_win)
        action_frame.pack(pady=10, padx=20, fill=tk.X)
        tk.Label(action_frame, text="Aktionstext (Bildschirmanzeige):", 
                font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.action_entry = tk.Entry(action_frame, font=("Arial", 11), width=30)
        self.action_entry.insert(0, self.gesture_info.get("action_text", ""))
        self.action_entry.pack(fill=tk.X, pady=5)
        
        # Channel
        channel_frame = tk.Frame(self.edit_win)
        channel_frame.pack(pady=10, padx=20, fill=tk.X)
        tk.Label(channel_frame, text="Kanal:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        available_channels = self.config_manager.get_available_channels()
        self.channel_var = tk.StringVar(value=self.gesture_info.get("channel", "CH5"))
        channel_combo = ttk.Combobox(channel_frame, textvariable=self.channel_var, 
                                     values=available_channels, state="readonly", font=("Arial", 11))
        channel_combo.pack(fill=tk.X, pady=5)
        
        # GPIO Pin (automatische Aktualisierung)
        pin_frame = tk.Frame(self.edit_win)
        pin_frame.pack(pady=10, padx=20, fill=tk.X)
        pin_label = tk.Label(pin_frame, text="GPIO Pin: ", font=("Arial", 10, "bold"))
        pin_label.pack(anchor=tk.W)
        self.pin_value_label = tk.Label(pin_frame, text=str(self.gesture_info.get("gpio_pin", "?")), 
                                   font=("Arial", 11), fg="#e74c3c")
        self.pin_value_label.pack(anchor=tk.W)
        
        def update_pin_display(*args):
            selected_channel = self.channel_var.get()
            channel_info = self.config_manager.get_channel_info(selected_channel)
            bcm_pin = channel_info.get("bcm_pin", "?")
            self.pin_value_label.config(text=str(bcm_pin))
        
        self.channel_var.trace('w', update_pin_display)
        
        # Rollen
        role_frame = tk.LabelFrame(self.edit_win, text="Berechtigte Rollen", 
                                   font=("Arial", 10, "bold"))
        role_frame.pack(pady=10, padx=20, fill=tk.X)
        
        current_roles = self.gesture_info.get("roles", [])
        self.role_vars = {
            'admin': tk.BooleanVar(value='admin' in current_roles),
            'ingenieur': tk.BooleanVar(value='ingenieur' in current_roles),
            'operator': tk.BooleanVar(value='operator' in current_roles)
        }
        
        tk.Checkbutton(role_frame, text=" Admin", variable=self.role_vars['admin'],
                      font=("Arial", 10, "bold"), fg="#e74c3c").pack(anchor=tk.W, padx=10, pady=3)
        tk.Checkbutton(role_frame, text=" Ingenieur", variable=self.role_vars['ingenieur'],
                      font=("Arial", 10, "bold"), fg="#3498db").pack(anchor=tk.W, padx=10, pady=3)
        tk.Checkbutton(role_frame, text=" Operator", variable=self.role_vars['operator'],
                      font=("Arial", 10, "bold"), fg="#95a5a6").pack(anchor=tk.W, padx=10, pady=3)
        
        # Speichern-Button
        tk.Button(self.edit_win, text=" Speichern", command=self.save_changes,
                 bg="#27ae60", fg="white", font=("Arial", 11, "bold"), 
                 width=20).pack(pady=15)
    
    def save_changes(self):
        """Aenderungen speichern"""
        selected_roles = [role for role, var in self.role_vars.items() if var.get()]
        if not selected_roles:
            messagebox.showwarning("Fehler", 
                                  "Mindestens eine Rolle muss ausgewählt sein!", 
                                  parent=self.edit_win)
            return
        
        # Neuen GPIO-Pin abrufen
        selected_channel = self.channel_var.get()
        channel_info = self.config_manager.get_channel_info(selected_channel)
        new_gpio_pin = channel_info.get("bcm_pin", self.gesture_info.get("gpio_pin"))
        
        # Config aktualisieren
        updates = {
            "display_name": self.name_entry.get().strip(),
            "action_text": self.action_entry.get().strip(),
            "channel": selected_channel,
            "gpio_pin": new_gpio_pin,
            "roles": selected_roles
        }
        
        success = self.config_manager.update_gesture(self.gesture_id, updates)
        
        if success:
            messagebox.showinfo("Erfolg", "Änderungen gespeichert!", parent=self.edit_win)
            if self.callback:
                self.callback()
            self.edit_win.destroy()
        else:
            messagebox.showerror("Fehler", "Änderungen konnten nicht gespeichert werden!", 
                               parent=self.edit_win)


class CustomGestureEditor:
    """VOLLSTÄNDIGE Bearbeitung fuer Custom-Gesten (wie Builtin)"""
    
    def __init__(self, parent, gesture_name, config_manager, callback=None):
        self.parent = parent
        self.gesture_name = gesture_name
        self.config_manager = config_manager
        self.callback = callback
    
    def open(self):
        """Bearbeitungsfenster öffnen"""
        self.edit_win = tk.Toplevel(self.parent)
        self.edit_win.title(f"Custom Geste bearbeiten: {self.gesture_name}")
        self.edit_win.geometry("500x550")
        self.edit_win.transient(self.parent)
        self.edit_win.grab_set()
        
        tk.Label(self.edit_win, text=f"Custom Geste: {self.gesture_name}", 
                font=("Arial", 14, "bold")).pack(pady=15)
        
        # Aktuelle Informationen abrufen
        current_info = self.config_manager.get_custom_gesture_info(self.gesture_name)
        
        # Display Name
        name_frame = tk.Frame(self.edit_win)
        name_frame.pack(pady=10, padx=20, fill=tk.X)
        tk.Label(name_frame, text="Anzeigename:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.name_entry = tk.Entry(name_frame, font=("Arial", 11), width=30)
        self.name_entry.insert(0, current_info.get("display_name", self.gesture_name))
        self.name_entry.pack(fill=tk.X, pady=5)
        
        # Action Text
        action_frame = tk.Frame(self.edit_win)
        action_frame.pack(pady=10, padx=20, fill=tk.X)
        tk.Label(action_frame, text="Aktionstext (Bildschirmanzeige):", 
                font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.action_entry = tk.Entry(action_frame, font=("Arial", 11), width=30)
        self.action_entry.insert(0, current_info.get("action_text", f"Geste: {self.gesture_name}"))
        self.action_entry.pack(fill=tk.X, pady=5)
        
        # Channel
        channel_frame = tk.Frame(self.edit_win)
        channel_frame.pack(pady=10, padx=20, fill=tk.X)
        tk.Label(channel_frame, text="Kanal:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        available_channels = self.config_manager.get_available_channels()
        self.channel_var = tk.StringVar(value=current_info.get("channel", "CH1"))
        channel_combo = ttk.Combobox(channel_frame, textvariable=self.channel_var, 
                                     values=available_channels, state="readonly", font=("Arial", 11))
        channel_combo.pack(fill=tk.X, pady=5)
        
        # GPIO Pin
        pin_frame = tk.Frame(self.edit_win)
        pin_frame.pack(pady=10, padx=20, fill=tk.X)
        pin_label = tk.Label(pin_frame, text="GPIO Pin: ", font=("Arial", 10, "bold"))
        pin_label.pack(anchor=tk.W)
        
        channel_info = self.config_manager.get_channel_info(self.channel_var.get())
        self.pin_value_label = tk.Label(pin_frame, text=str(channel_info.get("bcm_pin", "?")), 
                                   font=("Arial", 11), fg="#e74c3c")
        self.pin_value_label.pack(anchor=tk.W)
        
        def update_pin_display(*args):
            selected_channel = self.channel_var.get()
            channel_info = self.config_manager.get_channel_info(selected_channel)
            bcm_pin = channel_info.get("bcm_pin", "?")
            self.pin_value_label.config(text=str(bcm_pin))
        
        self.channel_var.trace('w', update_pin_display)
        
        # Rollen
        role_frame = tk.LabelFrame(self.edit_win, text="Berechtigte Rollen", 
                                   font=("Arial", 10, "bold"))
        role_frame.pack(pady=10, padx=20, fill=tk.X)
        
        current_roles = current_info.get("roles", ['admin', 'ingenieur', 'operator'])
        self.role_vars = {
            'admin': tk.BooleanVar(value='admin' in current_roles),
            'ingenieur': tk.BooleanVar(value='ingenieur' in current_roles),
            'operator': tk.BooleanVar(value='operator' in current_roles)
        }
        
        tk.Checkbutton(role_frame, text=" Admin", variable=self.role_vars['admin'],
                      font=("Arial", 10, "bold"), fg="#e74c3c").pack(anchor=tk.W, padx=10, pady=3)
        tk.Checkbutton(role_frame, text=" Ingenieur", variable=self.role_vars['ingenieur'],
                      font=("Arial", 10, "bold"), fg="#3498db").pack(anchor=tk.W, padx=10, pady=3)
        tk.Checkbutton(role_frame, text=" Operator", variable=self.role_vars['operator'],
                      font=("Arial", 10, "bold"), fg="#95a5a6").pack(anchor=tk.W, padx=10, pady=3)
        
        # Speichern-Button
        tk.Button(self.edit_win, text=" Speichern", command=self.save_changes,
                 bg="#27ae60", fg="white", font=("Arial", 11, "bold"), 
                 width=20).pack(pady=15)
    
    def save_changes(self):
        """Custom gesture bilgilerini kaydet"""
        selected_roles = [role for role, var in self.role_vars.items() if var.get()]
        if not selected_roles:
            messagebox.showwarning("Fehler", 
                                  "Mindestens eine Rolle muss ausgewählt sein!", 
                                  parent=self.edit_win)
            return
        
        # Yeni GPIO pin'i al
        selected_channel = self.channel_var.get()
        channel_info = self.config_manager.get_channel_info(selected_channel)
        new_gpio_pin = channel_info.get("bcm_pin", 5)
        
        # Custom gesture info'yu kaydet
        custom_info = {
            "display_name": self.name_entry.get().strip(),
            "action_text": self.action_entry.get().strip(),
            "channel": selected_channel,
            "gpio_pin": new_gpio_pin,
            "roles": selected_roles
        }
        
        success = self.config_manager.save_custom_gesture_info(self.gesture_name, custom_info)
        
        if success:
            messagebox.showinfo("Erfolg", "Änderungen gespeichert!", parent=self.edit_win)
            if self.callback:
                self.callback()
            self.edit_win.destroy()
        else:
            messagebox.showerror("Fehler", "Änderungen konnten nicht gespeichert werden!", 
                               parent=self.edit_win)


class CustomGestureRoleEditor:
    """ESKİ: Sadece rol düzenleme (artık kullanılmıyor)"""
    pass  # CustomGestureEditor ile değiştirildi


class FactoryResetDialog:
    """Fabrika ayarları diyalogu"""
    
    def __init__(self, parent, config_manager, model_manager, callback=None):
        self.parent = parent
        self.config_manager = config_manager
        self.model_manager = model_manager
        self.callback = callback
    
    def open(self):
        """Diyalogu aç"""
        self.reset_win = tk.Toplevel(self.parent)
        self.reset_win.title("Werkseinstellungen")
        self.reset_win.geometry("450x250")
        self.reset_win.transient(self.parent)
        self.reset_win.grab_set()
        
        tk.Label(self.reset_win, text="Werkseinstellungen wiederherstellen", 
                font=("Arial", 14, "bold")).pack(pady=20)
        
        tk.Label(self.reset_win, 
                text="ACHTUNG!\n\n"
                     "• ALLE Custom-Gesten werden gelöscht\n"
                     "• 4 Fabrik-Gesten werden wiederhergestellt\n"
                     "• Alle Einstellungen werden zurückgesetzt",
                font=("Arial", 10), justify=tk.LEFT).pack(pady=10, padx=20)
        
        btn_frame = tk.Frame(self.reset_win)
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="Ausfuehren", command=self.execute_reset,
                 bg="#c0392b", fg="white", font=("Arial", 11, "bold"), 
                 width=15).pack(side=tk.LEFT, padx=10)
        
        tk.Button(btn_frame, text="Abbrechen", command=self.reset_win.destroy,
                 bg="#95a5a6", fg="white", font=("Arial", 11, "bold"), 
                 width=15).pack(side=tk.LEFT, padx=10)
    
    def execute_reset(self):
        """Reset işlemini gerçekleştir"""
        # 1. Tüm verileri temizle
        self.model_manager.data_x = []
        self.model_manager.data_y = []
        
        # 2. ✅ YENİ: Builtin gesture'lar için örnek data ekle
        self.add_builtin_training_data()
        
        # 3. Config manager ile reset
        success, message = self.config_manager.factory_reset("all")
        
        # 4. Modeli kaydet
        self.model_manager.is_trained = False
        self.model_manager.save_model()
        
        if success:
            messagebox.showinfo("Erfolg", 
                              "Werkseinstellungen wiederhergestellt!\n\n"
                              "• Custom-Gesten gelöscht\n"
                              "• 4 Fabrik-Gesten mit Trainingsdaten hinzugefügt\n"
                              "• Bitte trainieren Sie das Modell neu!", 
                              parent=self.reset_win)
            if self.callback:
                self.callback()
            self.reset_win.destroy()
        else:
            messagebox.showerror("Fehler", message, parent=self.reset_win)
    
    def add_builtin_training_data(self):
        """NEU: Einfache Beispieldaten fuer Builtin-Gesten hinzufuegen"""
        print("[INFO] Beispieldaten fuer Builtin-Gesten werden hinzugefuegt...")
        
        # 30 Beispiele fuer jede Builtin-Geste hinzufuegen
        num_samples = 30
        
        # open - Alle Finger offen (normalized 42 Werte)
        for i in range(num_samples):
            sample = []
            for _ in range(21):  # 21 landmark
                sample.extend([
                    np.random.uniform(-0.1, 0.1),  # x
                    np.random.uniform(-0.5, -0.3)  # y (Finger nach oben)
                ])
            self.model_manager.add_sample(sample, "open")
        
        # index_up - Nur Zeigefinger offen
        for i in range(num_samples):
            sample = []
            for idx in range(21):
                if idx in [5, 6, 7, 8]:  # Zeigefinger-Landmarks
                    sample.extend([
                        np.random.uniform(-0.1, 0.1),
                        np.random.uniform(-0.5, -0.3)  # Offen
                    ])
                else:
                    sample.extend([
                        np.random.uniform(-0.1, 0.1),
                        np.random.uniform(0.3, 0.5)  # Geschlossen
                    ])
            self.model_manager.add_sample(sample, "index_up")
        
        # peace - Zeige- + Mittelfinger offen
        for i in range(num_samples):
            sample = []
            for idx in range(21):
                if idx in [5,6,7,8, 9,10,11,12]:  # Zeige- + Mittelfinger
                    sample.extend([
                        np.random.uniform(-0.1, 0.1),
                        np.random.uniform(-0.5, -0.3)  # Offen
                    ])
                else:
                    sample.extend([
                        np.random.uniform(-0.1, 0.1),
                        np.random.uniform(0.3, 0.5)  # Geschlossen
                    ])
            self.model_manager.add_sample(sample, "peace")
        
        # three_fingers_row - Zeige- + Mittel- + Ringfinger offen
        for i in range(num_samples):
            sample = []
            for idx in range(21):
                if idx in [5,6,7,8, 9,10,11,12, 13,14,15,16]:  # Zeige- + Mittel- + Ringfinger
                    sample.extend([
                        np.random.uniform(-0.1, 0.1),
                        np.random.uniform(-0.5, -0.3)  # Offen
                    ])
                else:
                    sample.extend([
                        np.random.uniform(-0.1, 0.1),
                        np.random.uniform(0.3, 0.5)  # Geschlossen
                    ])
            self.model_manager.add_sample(sample, "three_fingers_row")
        
        print("[OK] Builtin-Gesten-Daten hinzugefuegt: open, index_up, peace, three_fingers_row")
