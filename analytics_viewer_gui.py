"""
analytics_viewer_gui.py - Standalone CSV Analytics Visualizer
Visualisiert Testergebnisse (FPS, CPU, Latenz, Konfidenz) aus CSV-Dateien.

FUNKTIONEN:
- Ordner- und Dateiauswahl
- Matplotlib Integration für Liniendiagramme
- Unterstützung für neue Metriken: GPIO/PLC Latenz & Konfidenz
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import csv
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib

# Matplotlib Backend für Tkinter setzen
matplotlib.use('TkAgg')

class AnalyticsViewer:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Analytics Viewer")
        self.window.geometry("1100x800")
        self.window.configure(bg="#2c3e50")
        
        self.base_folder = "Testergebnisse"
        self.folders = []
        self.csv_files = []
        self.current_data = []
        self.current_folder = None
        
        # UI Aufbauen
        self.setup_ui()
        
        # Ordner laden
        self.load_folders()
    
    def setup_ui(self):
        # --- HEADER ---
        title_frame = tk.Frame(self.window, bg="#2c3e50")
        title_frame.pack(fill=tk.X, pady=10)
        
        title = tk.Label(title_frame, text="System & Performance Analyse", 
                        font=("Arial", 16, "bold"), bg="#2c3e50", fg="white")
        title.pack()

        # --- MAIN CONTAINER ---
        main_container = tk.Frame(self.window, bg="#2c3e50")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # --- LINKES PANEL (Auswahl) ---
        left_panel = tk.Frame(main_container, bg="#34495e", width=250)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Ordner Liste
        tk.Label(left_panel, text="Module / Tests", bg="#34495e", fg="white", font=("Arial", 10, "bold")).pack(pady=5)
        self.folder_listbox = tk.Listbox(left_panel, bg="#ecf0f1", height=8)
        self.folder_listbox.pack(fill=tk.X, padx=5)
        self.folder_listbox.bind('<<ListboxSelect>>', self.on_folder_select)
        
        # Datei Liste
        tk.Label(left_panel, text="CSV Dateien", bg="#34495e", fg="white", font=("Arial", 10, "bold")).pack(pady=5)
        self.file_listbox = tk.Listbox(left_panel, bg="#ecf0f1", height=12)
        self.file_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.file_listbox.bind('<<ListboxSelect>>', self.on_file_select)
        
        # Aktualisieren Button
        tk.Button(left_panel, text="Aktualisieren", command=self.load_folders, 
                 bg="#e67e22", fg="white").pack(fill=tk.X, padx=5, pady=10)

        # --- RECHTES PANEL (Grafik & Steuerung) ---
        right_panel = tk.Frame(main_container, bg="#ecf0f1")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        # Steuerungs-Buttons (Oben)
        control_frame = tk.Frame(right_panel, bg="#bdc3c7", height=50)
        control_frame.pack(fill=tk.X, pady=2)
        
        # Button Styles
        btn_style = {"font": ("Arial", 9, "bold"), "width": 9, "pady": 5}
        
        # --- Reihe 1: System und Hardware (5 Buton) ---
        row1 = tk.Frame(control_frame, bg="#bdc3c7")
        row1.pack(fill=tk.X, pady=2)
        
        tk.Button(row1, text="FPS", bg="#1abc9c", fg="white", **btn_style,
                 command=lambda: self.plot_metric_smart("FPS")).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        
        tk.Button(row1, text="CPU Temp", bg="#e74c3c", fg="white", **btn_style,
                 command=lambda: self.plot_metric("CPU_Temperatur_C")).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        
        tk.Button(row1, text="CPU %", bg="#d35400", fg="white", **btn_style,
                 command=lambda: self.plot_metric("CPU_Auslastung_%")).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)

        tk.Button(row1, text="RAM", bg="#9b59b6", fg="white", **btn_style,
                 command=lambda: self.plot_metric("RAM_Nutzung_MB")).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
                 
        tk.Button(row1, text="Licht", bg="#f1c40f", fg="white", **btn_style,
                 command=lambda: self.plot_metric_smart("Lichtstaerke")).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)

        # --- Reihe 2: Performance und Latency (5 Buton) ---
        row2 = tk.Frame(control_frame, bg="#bdc3c7")
        row2.pack(fill=tk.X, pady=2)

        tk.Button(row2, text="Gesamt ms", bg="#8e44ad", fg="white", **btn_style,
                 command=lambda: self.plot_metric("Gesamt_Latenz_ms")).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)

        tk.Button(row2, text="Face ms", bg="#2980b9", fg="white", **btn_style,
                 command=lambda: self.plot_metric("Face_Latenz_ms")).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)

        tk.Button(row2, text="Gesten ms", bg="#e67e22", fg="white", **btn_style,
                 command=lambda: self.plot_metric("Gesten_Latenz_ms")).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)

        tk.Button(row2, text="GPIO ms", bg="#c0392b", fg="white", **btn_style,
                 command=lambda: self.plot_metric("GPIO_Latenz_ms")).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)

        tk.Button(row2, text="PLC ms", bg="#34495e", fg="white", **btn_style,
                 command=lambda: self.plot_metric("PLC_Latenz_ms")).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        # Grafik Bereich
        self.plot_frame = tk.Frame(right_panel, bg="white")
        self.plot_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Info Label
        self.info_label = tk.Label(self.plot_frame, text="Bitte eine Datei auswählen...", 
                                  bg="white", fg="#7f8c8d", font=("Arial", 14))
        self.info_label.place(relx=0.5, rely=0.5, anchor="center")

    def load_folders(self):
        self.folder_listbox.delete(0, tk.END)
        self.file_listbox.delete(0, tk.END)
        self.folders = []
        
        if not os.path.exists(self.base_folder):
            os.makedirs(self.base_folder)
            
        for item in os.listdir(self.base_folder):
            path = os.path.join(self.base_folder, item)
            if os.path.isdir(path):
                self.folders.append(item)
                self.folder_listbox.insert(tk.END, item)

    def on_folder_select(self, event):
        selection = self.folder_listbox.curselection()
        if selection:
            index = selection[0]
            self.current_folder = self.folders[index]
            self.load_files(self.current_folder)

    def load_files(self, folder_name):
        self.file_listbox.delete(0, tk.END)
        self.csv_files = []
        folder_path = os.path.join(self.base_folder, folder_name)
        
        files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
        files.sort(reverse=True) # Neueste zuerst
        
        for f in files:
            self.csv_files.append(f)
            self.file_listbox.insert(tk.END, f)

    def on_file_select(self, event):
        selection = self.file_listbox.curselection()
        if selection and self.current_folder:
            file_name = self.csv_files[selection[0]]
            self.load_csv_data(self.current_folder, file_name)

    def load_csv_data(self, folder, filename):
        path = os.path.join(self.base_folder, folder, filename)
        self.current_data = []
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    self.current_data.append(row)
            
            self.info_label.config(text=f"Datei geladen: {filename}\n{len(self.current_data)} Datensaetze")
            # Automatisch FPS plotten
            self.plot_metric("FPS")
            
        except Exception as e:
            messagebox.showerror("Fehler", f"Konnte Datei nicht lesen:\n{e}")

    def plot_metric_smart(self, metric_name):
        """
        - FPS: FPS_Real oder FPS
        - Lichtstaerke: Lichtstaerke_ROI oder Lichtstaerke
        """
        if not self.current_data:
            return
        
        # Zuerst FPS_Real für FPS versuchen
        if metric_name == "FPS":
            if "FPS_Real" in self.current_data[0]:
                self.plot_metric("FPS_Real")
                return
            elif "FPS" in self.current_data[0]:
                self.plot_metric("FPS")
                return
            else:
                messagebox.showwarning("Daten fehlen", "Weder 'FPS' noch 'FPS_Real' gefunden!")
                return
        
        # Zuerst Lichtstaerke_ROI für Licht 
        if metric_name == "Lichtstaerke":
            if "Lichtstaerke_ROI" in self.current_data[0]:
                self.plot_metric("Lichtstaerke_ROI")
                return
            elif "Lichtstaerke" in self.current_data[0]:
                self.plot_metric("Lichtstaerke")
                return
            else:
                messagebox.showwarning("Daten fehlen", "Weder 'Lichtstaerke' noch 'Lichtstaerke_ROI' gefunden!")
                return
        
    
        self.plot_metric(metric_name)
    
    def plot_metric(self, metric_name):
        if not self.current_data:
            return

        # Prüfen ob Metrik existiert
        if metric_name not in self.current_data[0]:
            messagebox.showwarning("Daten fehlen", f"Die Metrik '{metric_name}' ist in dieser Datei nicht verfügbar.")
            return

        # Daten extrahieren
        x_values = [] # Zeit
        y_values = [] # Wert
        
        try:
            for row in self.current_data:
                time_val = float(row["Verstrichene_Zeit_s"])
                
                # Leere Werte als 0 behandeln
                val_str = row[metric_name]
                if val_str == "" or val_str is None:
                    val = 0.0
                else:
                    val = float(val_str)
                
                x_values.append(time_val)
                y_values.append(val)
        except ValueError:
            messagebox.showerror("Fehler", "Datenformat-Fehler beim Parsen der CSV.")
            return

        # Alte Grafik löschen
        for widget in self.plot_frame.winfo_children():
            widget.destroy()

        # Matplotlib Figure
        fig = Figure(figsize=(8, 5), dpi=100)
        fig.patch.set_facecolor('#ecf0f1') # Hintergrund hellgrau
        
        ax = fig.add_subplot(111)
        ax.set_facecolor('#2c3e50') # Plot Hintergrund dunkelblau
        
        # Farben definieren
        colors = {
            # --- Standart Metrikler ---
            'FPS': '#1abc9c',               # Türkis
            'CPU_Temperatur_C': '#e74c3c',  # Rot
            'RAM_Nutzung_MB': '#9b59b6',    # Lila
            'Lichtstaerke': '#f1c40f',      # Gelb
            'GPIO_Latenz_ms': '#e74c3c',
            'PLC_Latenz_ms': '#00d2ff',
            'CPU_Auslastung_%': '#d35400',
            'Gesamt_Latenz_ms': '#8e44ad',  
            'Face_Latenz_ms': '#3498db',    
            'Gesten_Latenz_ms': '#e67e22', 
            
            'FPS_Real': '#1abc9c',          
            'Lichtstaerke_ROI': '#f1c40f'
        }
        
        line_color = colors.get(metric_name, '#3498db') # Default Blau
        
        # Plotten
        ax.plot(x_values, y_values, color=line_color, linewidth=2, label=metric_name)
        
        # Styling
        ax.set_title(f"Verlauf: {metric_name.replace('_', ' ')}", color='#2c3e50', fontsize=12, fontweight='bold')
        ax.set_xlabel("Zeit (Sekunden)", color='#7f8c8d')
        ax.set_ylabel("Wert", color='#7f8c8d')
        ax.grid(True, linestyle='--', alpha=0.3, color='white')
        ax.tick_params(colors='#2c3e50')
        
        # Durchschnittslinie
        if len(y_values) > 0:
            avg = sum(y_values) / len(y_values)
            ax.axhline(y=avg, color='white', linestyle='--', alpha=0.7, label=f"Ø {avg:.2f}")
            ax.legend()

        # Canvas in Tkinter einbetten
        canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = AnalyticsViewer()
    app.run()
