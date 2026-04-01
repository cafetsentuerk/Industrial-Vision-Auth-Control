"""
analytics_logger.py - System & Performance Metrics Logger
Raspberry Pi für CPU, RAM, Temperatur, FPS, Reaktionszeit, Latenz und Konfidenz
"""
import psutil
import cv2
import numpy as np
from datetime import datetime
import os
import csv
import time

class AnalyticsLogger:
    def __init__(self):
        self.start_time = None
        self.log_data = []
        self.base_folder = "Testergebnisse"
        self.current_module = "TestModus"
        
        # Variablen für FPS-Berechnung
        self.last_frame_time = None
        self.fps_history = []
        
        # Variablen für Reaktionszeit-Berechnung
        self.last_gesture_change_time = None
        self.last_gesture_name = None
        
    def start_session(self, module_name="TestModus"):
        """Startet eine neue Aufzeichnungssitzung"""
        self.current_module = module_name
        self.start_time = datetime.now()
        self.log_data = []
        
        # Reset FPS und Reaktion
        self.last_frame_time = time.time()
        self.fps_history = []
        self.last_gesture_change_time = None
        self.last_gesture_name = None
        
        # Ordner erstellen, falls nicht vorhanden
        module_folder = os.path.join(self.base_folder, module_name)
        if not os.path.exists(module_folder):
            os.makedirs(module_folder)
            print(f"Ordner erstellt: {module_folder}")
        
        print(f"Analytics gestartet: {module_name}")
    
    def get_cpu_temp(self):
        """Liest die CPU-Temperatur des Raspberry Pi (°C)"""
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = float(f.read()) / 1000.0
                return round(temp, 1)
        except:
            return 0.0
    
    def get_light_level(self, frame_bgr):
        """Berechnet die Helligkeit des Bildes (0-255)"""
        if frame_bgr is None:
            return 0
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        return round(np.mean(gray), 1)
    
    def calculate_fps(self):
        """Berechnet die aktuellen FPS (Frames pro Sekunde)"""
        current_time = time.time()
        
        if self.last_frame_time is not None:
            frame_duration = current_time - self.last_frame_time
            if frame_duration > 0:
                fps = 1.0 / frame_duration
                self.fps_history.append(fps)
                
                # Durchschnitt der letzten 10 Frames für Stabilität
                if len(self.fps_history) > 10:
                    self.fps_history.pop(0)
                
                avg_fps = sum(self.fps_history) / len(self.fps_history)
                self.last_frame_time = current_time
                return round(avg_fps, 1)
        
        self.last_frame_time = current_time
        return 0.0
    
    def calculate_reaction_time(self, gesture_name):
        """Berechnet die Reaktionszeit (Zeit seit der letzten Gestenänderung)"""
        current_time = time.time()
        reaction_time = 0.0
        
        # Hat sich die Geste geändert?
        if gesture_name != self.last_gesture_name:
            if self.last_gesture_change_time is not None and gesture_name is not None:
                reaction_time = current_time - self.last_gesture_change_time
            
            self.last_gesture_change_time = current_time
            self.last_gesture_name = gesture_name
        
        return round(reaction_time * 1000, 1)  # In Millisekunden zurückgeben
    
    def log_frame(self, frame_bgr, gesture_name=None, confidence=0.0, display_fps=0.0, 
                  l_total=0.0, l_face=0.0, l_gest=0.0, l_gpio=0.0, l_plc=0.0):
        if self.start_time is None: return
        
        elapsed_time = (datetime.now() - self.start_time).total_seconds()
        
        # Işık ölçümü
        light = self.get_light_level(frame_bgr)

        # Sistem bilgilerini al
        if not hasattr(self, 'frame_counter'): self.frame_counter = 0
        self.frame_counter += 1
        if self.frame_counter % 30 == 0 or not hasattr(self, '_last_cpu'):
            import psutil
            self._last_cpu = round(psutil.cpu_percent(), 1)
            self._last_ram = round(psutil.virtual_memory().used / (1024**2), 1)

        record = {
            "Zeitstempel": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "Verstrichene_Zeit_s": round(elapsed_time, 2),
            "FPS": round(display_fps, 1),
            "CPU_Auslastung_%": self._last_cpu,
            "CPU_Temperatur_C": self.get_cpu_temp(),
            "RAM_Nutzung_MB": self._last_ram,
            "Lichtstaerke": light,
            "Geste": gesture_name if gesture_name else "Keine",
            "Gesamt_Latenz_ms": round(l_total, 1),
            "Face_Latenz_ms": round(l_face, 1),
            "Gesten_Latenz_ms": round(l_gest, 1),
            "GPIO_Latenz_ms": round(l_gpio, 3), 
            "PLC_Latenz_ms": round(l_plc, 3)     
        }
        self.log_data.append(record)
    
    def save_to_csv(self):
        """Speichert die gesammelten Daten in eine CSV-Datei"""
        if not self.log_data:
            print("⚠️ Keine Daten zum Speichern vorhanden.")
            return None
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        module_folder = os.path.join(self.base_folder, self.current_module)
        
        # Dateinamen basierend auf Modul generieren
        if self.current_module == "TestModus":
            csv_name = f"test-{timestamp}.csv"
        elif self.current_module == "SystemStart":
            csv_name = f"system_start-{timestamp}.csv"
        else:
            csv_name = f"{self.current_module.lower()}-{timestamp}.csv"
        
        filename = os.path.join(module_folder, csv_name)
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                # Spaltennamen aus dem ersten Datensatz nehmen
                fieldnames = self.log_data[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
                
                writer.writeheader()
                writer.writerows(self.log_data)
            
            print(f"Daten erfolgreich gespeichert: {filename} ({len(self.log_data)} Einträge)")
            return filename
        except Exception as e:
            print(f"Fehler beim Speichern der CSV: {e}")
            return None