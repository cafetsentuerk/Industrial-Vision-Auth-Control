# camera_registration_gui.py - Portrait Display Optimized v2 (Dengeli)

"""
Rollenbasiertes Steuerungssystem - Portrait Version

ÖZELLİKLER:
✅ 5" Portrait ekran için optimize (700x1200)
✅ Dengeli buton yerleşimi
✅ Boşluklar optimize edildi
✅ Tüm özellikler korundu
"""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import cv2
from PIL import Image, ImageTk
import os
import subprocess
import sys
from datetime import datetime
import shutil

class KameraGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Rollenbasiertes Steuerungssystem")
        
        # ✅ Portrait ekran için optimize
        self.root.geometry("700x1200")
        
        # Sicherstellen, dass der face_databank Ordner existiert
        if not os.path.exists("face_databank"):
            os.makedirs("face_databank")
        
        self.camera = None
        self.is_camera_open = False
        
        # ✅ Ana Frame (Scrollbar YOK - hepsi sığacak)
        main_frame = tk.Frame(root, bg="#2c3e50")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # === TITLE ===
        title = tk.Label(main_frame, text="Gesichtserfassung\n& Verwaltung", 
                        font=("Arial", 20, "bold"), bg="#2c3e50", fg="white")
        title.pack(pady=10)
        
        # === HAUPTFUNKTIONEN ===
        button_frame_main = tk.Frame(main_frame, bg="#2c3e50")
        button_frame_main.pack(pady=15, padx=20, fill=tk.X)
        
        self.sistem_btn = tk.Button(button_frame_main, 
                                    text="🚀 System starten", 
                                    font=("Arial", 14, "bold"), 
                                    bg="#95a5a6", fg="white", 
                                    height=2,
                                    command=self.sistem_starten)
        self.sistem_btn.pack(fill=tk.X, pady=5)
        
        self.kayit_btn = tk.Button(button_frame_main, 
                                   text="👤 Neue Person", 
                                   font=("Arial", 14, "bold"), 
                                   bg="#27ae60", fg="white", 
                                   height=2,
                                   command=self.neue_aufnahme)
        self.kayit_btn.pack(fill=tk.X, pady=5)
        
        self.manage_btn = tk.Button(button_frame_main, 
                                    text="📋 Benutzer verwalten", 
                                    font=("Arial", 14, "bold"), 
                                    bg="#3498db", fg="white", 
                                    height=2,
                                    command=self.manage_users)
        self.manage_btn.pack(fill=tk.X, pady=5)
        
        # === VERBINDUNGSTYP ===
        connection_frame = tk.LabelFrame(main_frame, 
                                        text="Verbindungstyp auswählen",
                                        font=("Arial", 12, "bold"),
                                        bg="#34495e", fg="white",
                                        padx=15, pady=10)
        connection_frame.pack(pady=15, padx=20, fill=tk.X)
        
        self.use_gpio = tk.BooleanVar(value=True)
        self.use_profinet = tk.BooleanVar(value=True)
        
        gpio_check = tk.Checkbutton(connection_frame, 
                                   text="⚡ GPIO verwenden",
                                   variable=self.use_gpio,
                                   font=("Arial", 11, "bold"),
                                   bg="#34495e", fg="#27ae60",
                                   selectcolor="#2c3e50",
                                   activebackground="#34495e",
                                   activeforeground="#27ae60")
        gpio_check.pack(anchor=tk.W, pady=5)
        
        profinet_check = tk.Checkbutton(connection_frame, 
                                       text="🔌 PROFINET PLC verwenden",
                                       variable=self.use_profinet,
                                       font=("Arial", 11, "bold"),
                                       bg="#34495e", fg="#3498db",
                                       selectcolor="#2c3e50",
                                       activebackground="#34495e",
                                       activeforeground="#3498db")
        profinet_check.pack(anchor=tk.W, pady=5)
        
        info_label = tk.Label(connection_frame, 
                             text="💡 Beide gleichzeitig möglich",
                             font=("Arial", 9, "italic"),
                             bg="#34495e", fg="#ecf0f1")
        info_label.pack(pady=5)
        
        # === GESTURE TRAINING ===
        gesture_frame = tk.LabelFrame(main_frame,
                                     text="Erweiterte Einstellungen",
                                     font=("Arial", 12, "bold"),
                                     bg="#34495e", fg="white",
                                     padx=15, pady=10)
        gesture_frame.pack(pady=15, padx=20, fill=tk.X)
        
        self.gesture_training_btn = tk.Button(gesture_frame, 
                                             text="✋ Gesture Training", 
                                             font=("Arial", 14, "bold"), 
                                             bg="#e67e22", fg="white", 
                                             height=2,
                                             command=self.gesture_training_starten)
        self.gesture_training_btn.pack(fill=tk.X)
        
        info_label = tk.Label(gesture_frame, 
                             text="Eigene Handgesten trainieren\n🔒 Passwortgeschützt",
                             font=("Arial", 9, "italic"),
                             bg="#34495e", fg="#ecf0f1")
        info_label.pack(pady=5)
        
        # === STATUS ===
        status_frame = tk.Frame(main_frame, bg="#2c3e50")
        status_frame.pack(pady=20, fill=tk.X)
        
        self.durum_label = tk.Label(status_frame, 
                                    text="✅ Bereit zur Verwaltung von Benutzern\noder zum Systemstart.",
                                    font=("Arial", 11),
                                    bg="#2c3e50", fg="#ecf0f1",
                                    justify=tk.CENTER)
        self.durum_label.pack()
        
        # === KAMERA VORSCHAU (optional, wenn gebraucht) ===
        self.camera_label = tk.Label(main_frame, bg="#34495e", height=2)
        self.camera_label.pack(pady=10)
    
    def check_password(self):
        """Spezielle Methode: Überprüft das Passwort."""
        password = simpledialog.askstring("Passwort benötigt", 
                                         "Bitte geben Sie das Administratorpasswort ein:", 
                                         show='*')
        if password == "jade-hs":
            return True
        else:
            if password is not None:
                messagebox.showerror("Zugriff verweigert", "Falsches Passwort!")
            return False
    
    def sistem_starten(self):
        """System starten - app_v2.py'yi başlatır"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(script_dir, "app_v2.py")
        
        if not os.path.exists(app_path):
            messagebox.showerror("Fehler", f"Die Datei 'app_v2.py' wurde nicht gefunden!")
            return
        
        use_gpio_arg = "--gpio" if self.use_gpio.get() else ""
        use_profinet_arg = "--profinet" if self.use_profinet.get() else ""
        
        try:
            start_command = ["sudo", sys.executable, app_path]
            
            if use_gpio_arg:
                start_command.append(use_gpio_arg)
            if use_profinet_arg:
                start_command.append(use_profinet_arg)
            
            if sys.platform == "win32":
                start_command = [sys.executable, app_path]
                if use_gpio_arg:
                    start_command.append(use_gpio_arg)
                if use_profinet_arg:
                    start_command.append(use_profinet_arg)
                subprocess.Popen(start_command, creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                subprocess.Popen(start_command)
            
            messagebox.showinfo("System", "app_v2.py wurde erfolgreich gestartet!")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Starten von app_v2.py:\n{str(e)}")
    
    def gesture_training_starten(self):
        """Gesture Training GUI'sini şifre ile başlatır"""
        if not self.check_password():
            return
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        training_path = os.path.join(script_dir, "gesture_training_gui.py")
        
        if not os.path.exists(training_path):
            messagebox.showerror("Fehler", 
                               f"Die Datei 'gesture_training_gui.py' wurde nicht gefunden!\n"
                               f"Bitte stellen Sie sicher, dass die Datei im gleichen Ordner ist.")
            return
        
        try:
            if sys.platform == "win32":
                subprocess.Popen([sys.executable, training_path], 
                               creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                subprocess.Popen([sys.executable, training_path])
            
            messagebox.showinfo("Gesture Training", 
                              "Gesten-Training wurde erfolgreich gestartet!\n\n"
                              "💡 Tipp: Trainieren Sie Ihre eigenen Handgesten.")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Starten des Gesture-Trainings:\n{str(e)}")
    
    def neue_aufnahme(self):
        """Yeni kişi kaydetme diyalogu"""
        if not self.check_password():
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Neue Person registrieren")
        dialog.geometry("600x300")
        dialog.configure(bg="#ecf0f1")
        
        # Frame für zentrierten Inhalt
        content_frame = tk.Frame(dialog, bg="#ecf0f1")
        content_frame.pack(expand=True, padx=30, pady=20)
        
        tk.Label(content_frame, text="Name der Person:", 
                font=("Arial", 12, "bold"), bg="#ecf0f1").pack(pady=10)
        
        name_entry = tk.Entry(content_frame, width=30, font=("Arial", 12))
        name_entry.pack(pady=5)
        
        tk.Label(content_frame, text="Rolle auswählen:", 
                font=("Arial", 12, "bold"), bg="#ecf0f1").pack(pady=10)
        
        role_var = tk.StringVar()
        role_combo = ttk.Combobox(content_frame, textvariable=role_var, 
                                  state="readonly", font=("Arial", 12), width=28)
        role_combo['values'] = ("admin", "ingenieur", "operator")
        role_combo.current(1)
        role_combo.pack(pady=5)
        
        def on_submit():
            person_name = name_entry.get().strip()
            role = role_var.get()
            
            if not person_name or not role:
                messagebox.showwarning("Warnung", 
                                     "Bitte geben Sie einen Namen und eine Rolle ein!", 
                                     parent=dialog)
                return
            
            folder_name = f"{role}-{person_name}"
            save_folder = os.path.join("face_databank", folder_name)
            
            if os.path.exists(save_folder):
                messagebox.showerror("Fehler", 
                                   f"Diese Person ({folder_name}) ist bereits registriert!", 
                                   parent=dialog)
                return
            
            os.makedirs(save_folder)
            dialog.destroy()
            self.start_camera_session(save_folder, folder_name)
        
        submit_btn = tk.Button(content_frame, text="📷 Weiter zur Fotoaufnahme", 
                              command=on_submit,
                              font=("Arial", 12, "bold"),
                              bg="#27ae60", fg="white",
                              height=2)
        submit_btn.pack(pady=20, fill=tk.X)
        
        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)
    
    def start_camera_session(self, save_folder, person_name):
        """Kamera açma ve fotoğraf çekme"""
        self.camera = cv2.VideoCapture(0, cv2.CAP_V4L2)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        
        if not self.camera.isOpened():
            messagebox.showerror("Fehler", "Kamera konnte nicht geöffnet werden!")
            return
        
        self.is_camera_open = True
        self.captured_count = 0
        self.save_folder = save_folder
        
        self.camera_window = tk.Toplevel(self.root)
        self.camera_window.title(f"{person_name} - Fotoaufnahme")
        self.camera_window.geometry("680x700")
        self.camera_window.configure(bg="#2c3e50")
        
        # Titel
        title = tk.Label(self.camera_window, text=f"📷 {person_name}",
                        font=("Arial", 14, "bold"), bg="#2c3e50", fg="white")
        title.pack(pady=10)
        
        self.cam_display = tk.Label(self.camera_window, bg="#34495e")
        self.cam_display.pack(pady=10)
        
        self.info_label = tk.Label(self.camera_window, 
                                   text=f"Drücken Sie die Leertaste\noder den Button zum Fotografieren",
                                   font=("Arial", 11),
                                   bg="#2c3e50", fg="white")
        self.info_label.pack(pady=10)
        
        btn_frame = tk.Frame(self.camera_window, bg="#2c3e50")
        btn_frame.pack(pady=10, padx=20, fill=tk.X)
        
        foto_btn = tk.Button(btn_frame, 
                            text="📷 Foto aufnehmen", 
                            command=self.foto_aufnehmen,
                            font=("Arial", 12, "bold"),
                            bg="#3498db", fg="white",
                            height=2)
        foto_btn.pack(fill=tk.X, pady=5)
        
        kapat_btn = tk.Button(btn_frame, 
                             text="✅ Fertig & Schließen", 
                             command=self.kamera_schliessen,
                             font=("Arial", 12, "bold"),
                             bg="#27ae60", fg="white",
                             height=2)
        kapat_btn.pack(fill=tk.X, pady=5)
        
        self.camera_window.bind('<space>', lambda e: self.foto_aufnehmen())
        self.camera_window.protocol("WM_DELETE_WINDOW", self.kamera_schliessen)
        
        self.video_stream()
    
    def video_stream(self):
        """Video stream gösterimi"""
        if self.is_camera_open:
            ret, frame = self.camera.read()
            if ret:
                self.last_frame = frame.copy()
                
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb).resize((640, 480))
                imgtk = ImageTk.PhotoImage(image=img)
                
                self.cam_display.imgtk = imgtk
                self.cam_display.configure(image=imgtk)
            
            self.camera_window.after(50, self.video_stream)
    
    def foto_aufnehmen(self):
        """Fotoğraf çekme"""
        if hasattr(self, 'last_frame'):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"foto_{timestamp}.jpg"
            filepath = os.path.join(self.save_folder, filename)
            
            cv2.imwrite(filepath, self.last_frame)
            self.captured_count += 1
            self.info_label.config(text=f"✅ {self.captured_count} Fotos aufgenommen")
    
    def kamera_schliessen(self):
        """Kamerayı kapatma"""
        self.is_camera_open = False
        if self.camera:
            self.camera.release()
        if hasattr(self, 'camera_window'):
            self.camera_window.destroy()
        
        if self.captured_count > 0:
            messagebox.showinfo("Erfolg", 
                              f"{self.captured_count} Fotos wurden gespeichert!\n\n"
                              "Die Person ist jetzt registriert.")
    
    def manage_users(self):
        """Kullanıcı yönetim penceresi"""
        if not self.check_password():
            return
        
        self.manage_window = tk.Toplevel(self.root)
        self.manage_window.title("Benutzerverwaltung")
        self.manage_window.geometry("680x700")
        self.manage_window.configure(bg="#2c3e50")
        
        # Titel
        title = tk.Label(self.manage_window, 
                        text="📋 Benutzerverwaltung",
                        font=("Arial", 16, "bold"),
                        bg="#2c3e50", fg="white")
        title.pack(pady=15)
        
        # Liste Frame
        list_frame = tk.Frame(self.manage_window, bg="#2c3e50")
        list_frame.pack(padx=15, pady=10, fill=tk.BOTH, expand=True)
        
        self.user_listbox = tk.Listbox(list_frame, width=50, height=15, 
                                       font=("Arial", 11))
        self.user_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame, orient="vertical")
        scrollbar.config(command=self.user_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        
        self.user_listbox.config(yscrollcommand=scrollbar.set)
        
        # Butonlar
        btn_frame = tk.Frame(self.manage_window, bg="#2c3e50")
        btn_frame.pack(pady=10, fill=tk.X, padx=15)
        
        delete_btn = tk.Button(btn_frame, 
                               text="🗑 Person löschen", 
                               command=self.delete_user,
                               font=("Arial", 12, "bold"),
                               bg="#e74c3c", fg="white",
                               height=2)
        delete_btn.pack(fill=tk.X, pady=5)
        
        change_role_btn = tk.Button(btn_frame, 
                                    text="🔄 Rolle ändern", 
                                    command=self.change_user_role,
                                    font=("Arial", 12, "bold"),
                                    bg="#3498db", fg="white",
                                    height=2)
        change_role_btn.pack(fill=tk.X, pady=5)
        
        close_btn = tk.Button(btn_frame, 
                             text="✅ Schließen", 
                             command=self.manage_window.destroy,
                             font=("Arial", 12, "bold"),
                             bg="#95a5a6", fg="white",
                             height=2)
        close_btn.pack(fill=tk.X, pady=5)
        
        self.refresh_user_list()
        
        self.manage_window.transient(self.root)
        self.manage_window.grab_set()
    
    def refresh_user_list(self):
        """Kullanıcı listesini yenileme"""
        self.user_listbox.delete(0, tk.END)
        
        databank_path = "face_databank"
        if os.path.exists(databank_path):
            for user in sorted(os.listdir(databank_path)):
                if os.path.isdir(os.path.join(databank_path, user)):
                    self.user_listbox.insert(tk.END, user)
    
    def delete_user(self):
        """Kullanıcı silme"""
        selected_indices = self.user_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Warnung", 
                                 "Bitte wählen Sie eine Person aus der Liste aus.", 
                                 parent=self.manage_window)
            return
        
        selected = self.user_listbox.get(selected_indices[0])
        
        if messagebox.askyesno("Bestätigung", 
                              f"Sind Sie sicher, dass Sie '{selected}' löschen möchten?", 
                              parent=self.manage_window):
            try:
                shutil.rmtree(os.path.join("face_databank", selected))
                messagebox.showinfo("Erfolg", 
                                  f"'{selected}' wurde erfolgreich gelöscht.", 
                                  parent=self.manage_window)
                self.refresh_user_list()
            except Exception as e:
                messagebox.showerror("Fehler", 
                                   f"Fehler beim Löschen: {e}", 
                                   parent=self.manage_window)
    
    def change_user_role(self):
        """Kullanıcı rolünü değiştirme"""
        selected_indices = self.user_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Warnung", 
                                 "Bitte wählen Sie eine Person aus der Liste aus.", 
                                 parent=self.manage_window)
            return
        
        selected = self.user_listbox.get(selected_indices[0])
        
        try:
            current_role, name = selected.split("-", 1)
        except ValueError:
            messagebox.showerror("Fehler", 
                               "Ungültiger Ordnername. Format muss 'rolle-name' sein.", 
                               parent=self.manage_window)
            return
        
        new_role = simpledialog.askstring("Rolle ändern", 
                                         f"Geben Sie die neue Rolle für '{name}' ein:\n(admin, ingenieur, operator)", 
                                         parent=self.manage_window)
        
        if new_role and new_role.lower() in ["admin", "ingenieur", "operator"]:
            new_folder_name = f"{new_role.lower()}-{name}"
            old_path = os.path.join("face_databank", selected)
            new_path = os.path.join("face_databank", new_folder_name)
            
            if os.path.exists(new_path):
                messagebox.showerror("Fehler", 
                                   f"Ein Benutzer mit dem Namen '{new_folder_name}' existiert bereits.", 
                                   parent=self.manage_window)
                return
            
            try:
                os.rename(old_path, new_path)
                messagebox.showinfo("Erfolg", 
                                  f"Die Rolle wurde erfolgreich in '{new_role.lower()}' geändert.", 
                                  parent=self.manage_window)
                self.refresh_user_list()
            except Exception as e:
                messagebox.showerror("Fehler", 
                                   f"Fehler beim Umbenennen: {e}", 
                                   parent=self.manage_window)
        elif new_role:
            messagebox.showerror("Ungültige Rolle", 
                               "Die Rolle muss 'admin', 'ingenieur' oder 'operator' sein.", 
                               parent=self.manage_window)


if __name__ == "__main__":
    root = tk.Tk()
    app = KameraGUI(root)
    root.mainloop()
