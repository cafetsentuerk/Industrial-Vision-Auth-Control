# gesture_training_gui.py - Portrait Display Optimized (5" 720x1280)

"""
Gesture Training GUI - Portrait Display Version

FUNKTIONEN:
- Optimiert fuer 5" Portrait-Display (700x1200)
- Kamera oben, Steuerungen unten
- Scrollbar fuer alle Steuerungen erreichbar
- Kompakte Buttons und Schriftgroessen
- Builtin: REGELBASIERT (benoetigt keine Samples)
- Custom: ML (benoetigt Samples)
- Analytics: FPS, CPU, RAM, Temperatur, Reaktionszeit
- Hand-Erkennung, Namensgebung, Berechtigungen, Kanalzuordnung
- Test-Modus: Prozentuale Aehnlichkeitskontrolle
- KEINE SICHERHEITSKONTROLLE IM TRAININGSMODUS (is_valid_hand WIRD NICHT VERWENDET)
"""

import tkinter as tk
from tkinter import messagebox
import cv2
from PIL import Image, ImageTk
import json
import sys
import os

# Module laden
from hand_tracking import HandDetector
from gesture_engine import GestureModel
from config_manager import GestureConfigManager
from gesture_editor_dialogs import BuiltinGestureEditor, CustomGestureEditor, FactoryResetDialog
from plc_controller import PLCController
from analytics_logger import AnalyticsLogger

class GestureTrainingApp:
    def __init__(self, window, window_title):
        self.window = window
        self.window.title(window_title)
        
        #  Optimiert für Portrait-Display (720x1280)
        self.window.geometry("700x1200")
        self.window.attributes('-topmost', False)
        self.window.lift()
        self.window.focus_force()
        self.window.protocol("WM_DELETE_WINDOW", self.close_window)
        
        # Config Manager
        self.config_manager = GestureConfigManager()
        self.config_manager.reload_config()
        
        # PLC Controller
        self.plc_controller = PLCController()
        
        # Analytics Logger
        self.analytics_logger = AnalyticsLogger()
        self.analytics_enabled = False
        
        #  Module initialisieren (OHNE Debug - Trainung mode)
        self.detector = HandDetector(debug=False)
        self.model_manager = GestureModel()
        
        # Raspberry Pi Kamera-Einstellungen
        self.cap = self.init_camera()
        self.recording = False
        
        # UI aufbauen
        self.setup_ui()
        
        # Liste initial füllen
        self.update_gesture_list()
        
        # Schleife starten
        self.loop()
    
    def update_session_json(self):
        with open("session_config.json", "w") as f:
            json.dump({"logging_active": self.analytics_var.get()}, f)


    def init_camera(self):
        """Raspberry Pi kompatible Kamera starten"""
        try:
            cap = cv2.VideoCapture(0)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 30)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            if not cap.isOpened():
                messagebox.showerror("Fehler", "Kamera konnte nicht geoeffnet werden!")
                sys.exit(1)
            
            return cap
        except Exception as e:
            messagebox.showerror("Fehler", f"Kamera-Fehler: {str(e)}")
            sys.exit(1)
    
    def setup_ui(self):
        #  Hauptcontainer mit Scrollbar
        main_container = tk.Frame(self.window, bg="#2c3e50")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Canvas + Scrollbar
        canvas = tk.Canvas(main_container, bg="#2c3e50")
        scrollbar = tk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        self.main_frame = tk.Frame(canvas, bg="#2c3e50")
        
        self.main_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.main_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Titel
        title = tk.Label(self.main_frame, text="Gesture Training",
                        font=("Arial", 16, "bold"), bg="#2c3e50", fg="white")
        title.pack(pady=5)
        
        # KAMERA OBEN
        camera_frame = tk.Frame(self.main_frame, bg="#34495e", relief=tk.SUNKEN, borderwidth=2)
        camera_frame.pack(padx=5, pady=5, fill=tk.X)
        
        self.video_label = tk.Label(camera_frame, bg="#34495e")
        self.video_label.pack(padx=5, pady=5)
        
        #  KONTROLLPANEL UNTEN (kompakt)
        self.control_frame = tk.Frame(self.main_frame, bg="#ecf0f1")
        self.control_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # -- Status --
        self.mode_label = tk.Label(self.control_frame, text="Status: Bereit",
                                   font=("Arial", 11, "bold"), bg="#ecf0f1", fg="#2c3e50")
        self.mode_label.pack(pady=5)
        
        # PLC Config (kompakt)
        self.plc_config_btn = tk.Button(self.control_frame,
                                        text=" PLC Config",
                                        font=("Arial", 10, "bold"),
                                        bg="#9b59b6", fg="white",
                                        height=1,
                                        command=self.open_plc_config)
        self.plc_config_btn.pack(fill=tk.X, pady=3, padx=5)
        
        # -- Neue Geste aufnehmen (kompakt) --
        record_frame = tk.LabelFrame(self.control_frame, text="NEUE GESTE",
                                    font=("Arial", 9, "bold"), bg="#ecf0f1", fg="#16a085")
        record_frame.pack(pady=5, padx=5, fill=tk.X)
        
        tk.Label(record_frame, text="Name:", bg="#ecf0f1",
                font=("Arial", 9)).pack(pady=2)
        
        self.entry_name = tk.Entry(record_frame, font=("Arial", 10), width=20)
        self.entry_name.insert(0, "z.B. Daumen_hoch")
        self.entry_name.pack(pady=2)
        
        # Rollenauswahl (kompakt - eine Zeile)
        role_label = tk.Label(record_frame, text="Rollen:", bg="#ecf0f1", font=("Arial", 8))
        role_label.pack(pady=1)
        
        role_frame = tk.Frame(record_frame, bg="#ecf0f1")
        role_frame.pack(pady=2)
        
        self.role_vars = {
            'admin': tk.BooleanVar(value=True),
            'ingenieur': tk.BooleanVar(value=True),
            'operator': tk.BooleanVar(value=True)
        }
        
        tk.Checkbutton(role_frame, text="admin", variable=self.role_vars['admin'],
                      bg="#ecf0f1", font=("Arial", 10)).pack(side=tk.LEFT, padx=3)
        tk.Checkbutton(role_frame, text="ingenieur", variable=self.role_vars['ingenieur'],
                      bg="#ecf0f1", font=("Arial", 10)).pack(side=tk.LEFT, padx=3)
        tk.Checkbutton(role_frame, text="operator", variable=self.role_vars['operator'],
                      bg="#ecf0f1", font=("Arial", 10)).pack(side=tk.LEFT, padx=3)
        
        # Start / Stopp Button
        self.btn_record = tk.Button(record_frame, text=" AUFNAHME",
                                    bg="#27ae60", fg="white", height=1,
                                    font=("Arial", 10, "bold"),
                                    command=self.toggle_recording)
        self.btn_record.pack(pady=3, fill=tk.X, padx=3)
        
        self.record_count_label = tk.Label(record_frame, text="Samples: 0",
                                          bg="#ecf0f1", font=("Arial", 8))
        self.record_count_label.pack(pady=1)
        
        self.sample_count = 0
        
        # -- Listenverwaltung (kompakt) --
        list_frame = tk.LabelFrame(self.control_frame, text="ALLE GESTEN",
                                  font=("Arial", 9, "bold"), bg="#ecf0f1", fg="#e74c3c")
        list_frame.pack(pady=5, padx=5, fill=tk.BOTH, expand=True)
        
        # Listbox und Scrollbar
        listbox_frame = tk.Frame(list_frame, bg="#ecf0f1")
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        self.gesture_listbox = tk.Listbox(listbox_frame, height=6, font=("Arial", 8))
        self.gesture_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar_list = tk.Scrollbar(listbox_frame)
        scrollbar_list.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.gesture_listbox.config(yscrollcommand=scrollbar_list.set)
        scrollbar_list.config(command=self.gesture_listbox.yview)
        
        #  Verwaltungsbuttons (ALMANCA İSİMLER)
        btn_frame1 = tk.Frame(list_frame, bg="#ecf0f1")
        btn_frame1.pack(fill=tk.X, pady=2, padx=2)
        
        self.btn_edit = tk.Button(btn_frame1, text="\nBearbeiten", bg="#3498db", fg="white",
                                 font=("Arial", 7, "bold"), width=10, height=2,
                                 command=self.edit_selected)
        self.btn_edit.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        
        self.btn_toggle = tk.Button(btn_frame1, text="\nDeaktivieren/Aktivieren", bg="#f39c12", fg="white",
                                    font=("Arial", 7, "bold"), width=10, height=2,
                                    command=self.toggle_selected)
        self.btn_toggle.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        
        self.btn_delete = tk.Button(btn_frame1, text="\nLöschen", bg="#e74c3c", fg="white",
                                    font=("Arial", 7, "bold"), width=10, height=2,
                                    command=self.delete_selected)
        self.btn_delete.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        
        # WERKSEINSTELLUNGEN
        tk.Button(list_frame, text=" WERKSEINSTELLUNGEN",
                 bg="#c0392b", fg="white", font=("Arial", 8, "bold"),
                 command=self.factory_reset_simple).pack(fill=tk.X, pady=2, padx=2)
        
        # -- Training und Test (kompakt) --
        train_frame = tk.LabelFrame(self.control_frame, text="TRAINING & TEST",
                                   font=("Arial", 9, "bold"), bg="#ecf0f1", fg="#3498db")
        train_frame.pack(pady=5, padx=5, fill=tk.X)
        
        self.btn_train = tk.Button(train_frame, text=" TRAINIEREN",
                                   bg="#3498db", fg="white",
                                   font=("Arial", 10, "bold"), height=1,
                                   command=self.train_model)
        self.btn_train.pack(pady=3, fill=tk.X, padx=3)
        
        # Test und Analytics Checkboxen (nebeneinander)
        checkbox_frame = tk.Frame(train_frame, bg="#ecf0f1")
        checkbox_frame.pack(pady=2)
        
        self.test_var = tk.BooleanVar()
        self.chk_test = tk.Checkbutton(checkbox_frame, text=" Test",
                                       variable=self.test_var, bg="#ecf0f1",
                                       font=("Arial", 8, "bold"),
                                       command=self.toggle_test)
        self.chk_test.pack(side=tk.LEFT, padx=2)
        
        # Analytics Checkbox - UNABHÄNGIG!
        init_log = False
        if os.path.exists("session_config.json"):
            try:
                with open("session_config.json", "r") as f:
                    init_log = json.load(f).get("logging_active", False)
            except: 
                pass
        
        #  2. ADIM: Değişkeni tanımla
        self.analytics_var = tk.BooleanVar(value=init_log)
        self.chk_analytics = tk.Checkbutton(checkbox_frame, text=" Log", 
                                            variable=self.analytics_var, 
                                            command=self.update_session_json, # ✅ Bu eklendi
                                            bg="#ecf0f1")
        self.chk_analytics.pack(side=tk.LEFT, padx=2)
        
        result_container = tk.Frame(train_frame, bg="#34495e", relief=tk.SUNKEN, borderwidth=2)
        result_container.pack(pady=3, padx=3)
        
        self.result_display = tk.Label(result_container, text="Warte...",
                                       font=("Arial", 10, "bold"),
                                       bg="#34495e", fg="white",
                                       width=20, height=2)
        self.result_display.pack(padx=3, pady=3)
        
        # Beenden
        tk.Button(self.control_frame, text=" BEENDEN", bg="#95a5a6", fg="white",
                 font=("Arial", 9, "bold"), command=self.close_window).pack(pady=5, fill=tk.X, padx=5)
    
    def update_gesture_list(self):
        """ EINE LISTE: Builtin  + Custom """
        self.gesture_listbox.delete(0, tk.END)
        
        # 1. Builtin-Gesten
        builtin_gestures = self.config_manager.get_builtin_gestures()
        for gesture_id, info in builtin_gestures.items():
            enabled_icon = "[OK]" if info.get("enabled", 0) == 1 else "[X]"
            display_name = info.get("display_name", gesture_id)
            channel = info.get("channel", "?")
            roles = info.get("roles", [])
            
            role_icons = {
                'admin': 'A',
                'ingenieur': 'I',
                'operator': 'O'
            }
            role_display = ''.join([role_icons.get(r, '.') for r in roles])
            
            # Kompaktes Format (W: Werkseinstellung/Builtin)
            text = f"[W] {enabled_icon} {display_name} ({channel}) {role_display}"
            self.gesture_listbox.insert(tk.END, text)
        
        # 2.  Trainierte Gesten 
        stats = self.model_manager.get_class_stats()
        builtin_ids = builtin_gestures.keys()
        
        for name, count in stats.items():
            # Builtin-Gesten ueberspringen
            if name in builtin_ids:
                continue
            
            # Custom-Gesten-Info holen
            custom_info = self.config_manager.get_custom_gesture_info(name)
            display_name = custom_info.get("display_name", name)
            channel = custom_info.get("channel", "?")
            roles = custom_info.get("roles", ['admin', 'ingenieur', 'operator'])
            
            role_icons = {
                'admin': 'A',
                'ingenieur': 'I',
                'operator': 'O'
            }
            role_display = ''.join([role_icons.get(r, '.') for r in roles])
            
            # Kompaktes Format ([C]: Custom-Geste)
            text = f"[C] {display_name} ({channel}, {count}x) {role_display}"
            self.gesture_listbox.insert(tk.END, text)
    
    def edit_selected(self):
        """Ausgewählte Geste bearbeiten"""
        selection = self.gesture_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warnung", "Bitte wählen Sie eine Geste aus.")
            return
        
        text = self.gesture_listbox.get(selection[0])
        
        if text.startswith("🏭"):
            # Builtin-Gesten bearbeiten
            parts = text.split(" (")
            # "🏭 ✓ Offene Hand" -> "Offene Hand"
            display_name = parts[0].split(" ", 2)[2].strip()
            
            # Gesten-ID finden
            gesture_id = None
            for gid, info in self.config_manager.get_builtin_gestures().items():
                if info.get("display_name") == display_name:
                    gesture_id = gid
                    break
            
            if gesture_id:
                gesture_info = self.config_manager.get_gesture_info(gesture_id)
                editor = BuiltinGestureEditor(self.window, gesture_id, gesture_info,
                                             self.config_manager, self.update_gesture_list)
                editor.open()
        
        elif text.startswith("📝"):
            # Custom-Geste - VOLLSTÄNDIGE Bearbeitung
            parts = text.split(" (")
            gesture_name = parts[0].replace("📝 ", "").strip()
            
            editor = CustomGestureEditor(self.window, gesture_name,
                                        self.config_manager, self.update_gesture_list)
            editor.open()
    
    def toggle_selected(self):
        """Aktiv/Deaktiv (Nur Builtin)"""
        selection = self.gesture_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warnung", "Bitte wählen Sie eine Geste aus.")
            return
        
        text = self.gesture_listbox.get(selection[0])
        
        if not text.startswith("🏭"):
            messagebox.showinfo("Info", "Custom-Gesten können nicht deaktiviert werden.\nLöschen Sie sie stattdessen.")
            return
        
        parts = text.split(" (")
        display_name = parts[0].split(" ", 2)[2].strip()
        
        # Gesten-ID finden
        gesture_id = None
        for gid, info in self.config_manager.get_builtin_gestures().items():
            if info.get("display_name") == display_name:
                gesture_id = gid
                break
        
        if gesture_id:
            success = self.config_manager.toggle_gesture_enabled(gesture_id)
            if success:
                self.update_gesture_list()
                is_enabled = self.config_manager.is_gesture_enabled(gesture_id)
                status = "aktiviert" if is_enabled else "deaktiviert"
                messagebox.showinfo("Erfolg", f"'{display_name}' wurde {status}.")
    
    def delete_selected(self):
        """Custom-Geste löschen (Builtin nicht löschbar)"""
        selection = self.gesture_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warnung", "Bitte wählen Sie eine Geste aus.")
            return
        
        text = self.gesture_listbox.get(selection[0])
        
        if text.startswith("🏭"):
            messagebox.showwarning("Warnung", "Fabrik-Gesten können nicht gelöscht werden!\nSie können sie nur deaktivieren.")
            return
        
        # Custom-Geste
        parts = text.split(" (")
        name = parts[0].replace("📝 ", "").strip()
        
        if messagebox.askyesno("Löschen bestätigen", f"Möchten Sie '{name}' wirklich löschen?"):
            self.model_manager.delete_class(name)
            self.config_manager.delete_custom_gesture_info(name)
            self.update_gesture_list()
            self.test_var.set(False)
            messagebox.showinfo("Erfolg", f"'{name}' wurde gelöscht.")
    
    def factory_reset_simple(self):
        """✅ WERKSEINSTELLUNGEN"""
        dialog = FactoryResetDialog(self.window, self.config_manager,
                                    self.model_manager, self.update_gesture_list)
        dialog.open()
    
    def toggle_recording(self):
        """Aufnahme starten/stoppen"""
        if not self.recording:
            name = self.entry_name.get().strip()
            if not name or "z.B." in name:
                messagebox.showwarning("Fehler", "Bitte geben Sie einen gültigen Namen ein!")
                return
            
            # Builtin-Kontrolle
            builtin_ids = self.config_manager.get_builtin_gestures().keys()
            if name in builtin_ids:
                messagebox.showerror("Fehler", f"'{name}' ist eine Fabrik-Geste!")
                return
            
            selected_roles = [role for role, var in self.role_vars.items() if var.get()]
            if not selected_roles:
                messagebox.showwarning("Fehler", "Bitte wählen Sie mindestens eine Rolle aus!")
                return
            
            # Bei erster Aufnahme Standardinformationen speichern
            self.config_manager.save_custom_gesture_info(name, {
                "display_name": name,
                "action_text": f"Geste: {name}",
                "channel": "CH1",
                "gpio_pin": 5,
                "roles": selected_roles
            })
            
            self.recording = True
            self.sample_count = 0
            self.btn_record.config(text="⏹ STOPP", bg="#e74c3c")
            role_text = ", ".join(selected_roles)
            self.mode_label.config(text=f"⏺ REC: {name}", fg="#e74c3c")
            
            if self.test_var.get():
                self.test_var.set(False)
                self.toggle_test()
        
        else:
            self.recording = False
            self.btn_record.config(text="⏺ AUFNAHME", bg="#27ae60")
            self.mode_label.config(text="Status: Bereit", fg="#2c3e50")
            self.update_gesture_list()
            messagebox.showinfo("Erfolg",
                              f"{self.sample_count} Samples aufgenommen!\n"
                              f"Vergessen Sie nicht, das Modell zu trainieren.")
    
    def train_model(self):
        success, msg = self.model_manager.train()
        if success:
            messagebox.showinfo("Training erfolgreich", msg)
            self.mode_label.config(text="✅ Modell trainiert", fg="#27ae60")
        else:
            messagebox.showerror("Fehler", msg)
    
    def toggle_test(self):
        if self.test_var.get():
            self.mode_label.config(text="🧪 TEST-MODUS", fg="#3498db")
        else:
            self.mode_label.config(text="Status: Bereit", fg="#2c3e50")
            self.result_display.config(text="Warte...", bg="#34495e", fg="white")
    
    def toggle_analytics(self):
        """Analytics-Aufzeichnung ein/aus - UNABHÄNGIG VON TEST!"""
        self.config_manager.set_logging_status(self.analytics_var.get())
        if self.analytics_var.get():
            self.analytics_enabled = True
            self.analytics_logger.start_session("TestModus")
            self.mode_label.config(text="📊 LOG AKTIV", fg="#16a085")
            print("📊 Analytics aktiviert")
        else:
            if self.analytics_enabled:
                csv_file = self.analytics_logger.save_to_csv()
                if csv_file:
                    messagebox.showinfo("Analytics", f"Daten gespeichert:\n{os.path.basename(csv_file)}")
            
            self.analytics_enabled = False
            
            # Wenn Test nicht aktiv, Status zurücksetzen
            if not self.test_var.get():
                self.mode_label.config(text="Status: Bereit", fg="#2c3e50")
            
            print("📊 Analytics deaktiviert")
    
    def open_plc_config(self):
        """PLC-Konfigurationsfenster öffnen"""
        from plc_config_gui import PLCConfigGUI
        PLCConfigGUI(self.window, self.config_manager, self.plc_controller)
    
    def _detect_builtin_rule_based(self, lm_list):
        """✅ REGELBASIERT: Builtin-Gesten erkennen (kein ML erforderlich)"""
        if not lm_list or len(lm_list) < 21:
            return None
        
        IDX_TIP, IDX_PIP = 8, 6
        MID_TIP, MID_PIP = 12, 10
        RNG_TIP, RNG_PIP = 16, 14
        PNK_TIP, PNK_PIP = 20, 18
        THUMB_TIP, THUMB_IP = 4, 3
        
        def is_finger_extended(tip_idx, pip_idx):
            """Ist der Finger ausgestreckt? (Y-Koordinaten-Kontrolle)"""
            return lm_list[tip_idx][2] < lm_list[pip_idx][2]
        
        def is_thumb_extended(tip_idx, ip_idx):
            """Ist der Daumen ausgestreckt? (X-Koordinaten-Kontrolle)"""
            return abs(lm_list[tip_idx][1] - lm_list[ip_idx][1]) > 0.04
        
        thumb_extended = is_thumb_extended(THUMB_TIP, THUMB_IP)
        index_extended = is_finger_extended(IDX_TIP, IDX_PIP)
        middle_extended = is_finger_extended(MID_TIP, MID_PIP)
        ring_extended = is_finger_extended(RNG_TIP, RNG_PIP)
        pinky_extended = is_finger_extended(PNK_TIP, PNK_PIP)
        
        # Priorität von spezifisch zu allgemein
        if index_extended and middle_extended and ring_extended and pinky_extended:
            return "open"
        
        if (not thumb_extended) and index_extended and middle_extended and ring_extended and (not pinky_extended):
            return "three_fingers_row"
        
        if (not thumb_extended) and index_extended and middle_extended and (not ring_extended) and (not pinky_extended):
            return "peace"
        
        if index_extended and (not middle_extended) and (not ring_extended) and (not pinky_extended):
            return "index_up"
        
        return None
    
    def loop(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            frame = self.detector.find_hands(frame)
            
            # ✅ 3 PARAMETRE AL (ama is_valid_hand KULLANMA - EĞİTİM MODUNDA!)
            lm_list, hand_type, is_valid_hand = self.detector.find_position(frame)
            
            # ✅ EĞİTİM MODUNDA HER ELİ KABUL ET (is_valid_hand kontrolü YOK!)
            if lm_list:
                processed_lms = self.detector.process_landmarks(lm_list, hand_type)
                
                if self.recording:
                    name = self.entry_name.get().strip()
                    self.model_manager.add_sample(processed_lms, name)
                    self.sample_count += 1
                    self.record_count_label.config(text=f"Samples: {self.sample_count}")
                    
                    cv2.circle(frame, (30, 30), 15, (0, 0, 255), -1)
                    cv2.putText(frame, "REC", (55, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    cv2.putText(frame, f"Hand: {hand_type}", (10, 450),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                
                elif self.test_var.get():
                    # ✅ TEST-MODUS - GESTE ERKENNEN + % BENZERLİK
                    detected_gesture = None
                    confidence = 0.0
                    gesture_type = None
                    
                    # 1. REGELBASIERTE KONTROLLE (Builtin)
                    builtin_result = self._detect_builtin_rule_based(lm_list)
                    
                    if builtin_result:
                        # Builtin gefunden - ist aktiv?
                        gesture_info = self.config_manager.get_gesture_info(builtin_result)
                        if gesture_info and gesture_info.get("enabled", 0) == 1:
                            detected_gesture = builtin_result
                            confidence = 1.0  # 100% Konfidenz
                            gesture_type = "🏭"
                    
                    if not detected_gesture:
                        # 2. ML-MODELL (Custom-Gesten)
                        if self.model_manager.is_trained:
                            pred, conf = self.model_manager.predict(processed_lms)
                            
                            if pred != "Modell nicht trainiert" and conf > 0.5:
                                detected_gesture = pred
                                confidence = conf
                                gesture_type = "📝"
                    
                    # Ergebnis anzeigen MIT % BENZERLİK
                    if detected_gesture:
                        percent = int(confidence * 100)
                        
                        # Gesten-Info holen
                        if gesture_type == "🏭":
                            gesture_info = self.config_manager.get_gesture_info(detected_gesture)
                            roles = gesture_info.get("roles", ['?'])
                            display_name = gesture_info.get("display_name", detected_gesture)
                        else:
                            custom_info = self.config_manager.get_custom_gesture_info(detected_gesture)
                            roles = custom_info.get("roles", ['?'])
                            display_name = custom_info.get("display_name", detected_gesture)
                        
                        role_text = ', '.join(roles)
                        
                        self.result_display.config(
                            text=f"{gesture_type} {display_name}\n{percent}%\n[{role_text}]",
                            bg="#27ae60" if percent > 70 else "#f39c12",
                            fg="white"
                        )
                        
                        color = (0, 255, 0) if confidence > 0.7 else (0, 165, 255)
                        cv2.putText(frame, f"{display_name} {percent}%", (10, 50),
                                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
                        
                        # Analytics aufzeichnen
                        if self.analytics_enabled:
                            self.analytics_logger.log_frame(frame, detected_gesture, confidence)
                    
                    else:
                        self.result_display.config(text="Keine Geste", bg="#999", fg="white")
                        
                        # Analytics aufzeichnen (keine Geste)
                        if self.analytics_enabled:
                            self.analytics_logger.log_frame(frame, None, 0.0)
                
                # Analytics NUR wenn Log aktiv (auch ohne Test!)
                elif self.analytics_enabled:
                    # Nicht im Test-Modus, aber Log aktiv
                    # Trotzdem Gestenerkennung für Analytics
                    detected_gesture = None
                    confidence = 0.0
                    
                    builtin_result = self._detect_builtin_rule_based(lm_list)
                    if builtin_result:
                        gesture_info = self.config_manager.get_gesture_info(builtin_result)
                        if gesture_info and gesture_info.get("enabled", 0) == 1:
                            detected_gesture = builtin_result
                            confidence = 1.0
                    
                    if not detected_gesture and self.model_manager.is_trained:
                        pred, conf = self.model_manager.predict(processed_lms)
                        if pred != "Modell nicht trainiert" and conf > 0.5:
                            detected_gesture = pred
                            confidence = conf
                    
                    self.analytics_logger.log_frame(frame, detected_gesture, confidence)
            
            else:
                # Keine Hand erkannt
                if self.test_var.get():
                    self.result_display.config(text="Keine Hand", bg="#7f8c8d", fg="white")
                
                # Analytics aufzeichnen (keine Hand)
                if self.analytics_enabled:
                    self.analytics_logger.log_frame(frame, None, 0.0)
            
            # OpenCV -> Tkinter
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
            img = Image.fromarray(cv2image)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
        
        self.window.after(10, self.loop)
    
    def close_window(self):
        if self.cap.isOpened():
            self.cap.release()
        self.window.destroy()
    
    def __del__(self):
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()


if __name__ == "__main__":
    root = tk.Tk()
    app = GestureTrainingApp(root, "Gesture Training System")
    root.protocol("WM_DELETE_WINDOW", app.close_window)
    root.mainloop()
