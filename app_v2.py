# app_v2.py - Konfigurationsbasierte GPIO-Steuerung (Unterstützung für benutzerdefinierte Gesten - FINAL)

# NEU: Unterstützung für Befehlszeilenargumente (--gpio, --profinet)
# NEU: Unterstützung für die Schließen-Schaltfläche (X)
# NEU: HandDetector-Integration (10-stufige Sicherheit)

"""
app_v2.py - Rollenbasierte Gestensteuerung mit GPIO-Auslösung

Sicherheiteigenschaften gegen Manipulation:
- Nur EINE Person erlaubt (Mehrere Personen = System blockiert)
- Hand-Körper-Zuordnung (Hand muss zur Person gehören)
- 10-stufige Sicherheitskontrolle (HandDetector)
- Gesicht-Hand-Distanz-Kontrolle
- Schulter-Sichtbarkeitsprüfung
- Rollenbasierte Berechtigung (Admin/Ingenieur/Operator)
- Config-basierte Gesture Verwaltung (gesture_config.json)
- Custom Gestures mit Rollenkontrolle + GPIO Support
"""

import cv2
import numpy as np
from gesture_detector_v2 import GestureDetector
from face_identity_v2 import FaceDatabase, Role, Action, is_allowed
from gpio_controller import GpioController
from plc_controller import PLCController
import json
import mediapipe as mp
import json
import os
import sys  
import time
from analytics_logger import AnalyticsLogger

def check_log_status():
    if os.path.exists("session_config.json"):
        try:
            with open("session_config.json", "r") as f:
                return json.load(f).get("logging_active", False)
        except: return False
    return False

enable_logging = check_log_status()
logger = AnalyticsLogger() if enable_logging else None
if logger: logger.start_session("SystemStart")

def load_gesture_config():
    """Lädt die gesture_config.json Datei"""
    if os.path.exists("gesture_config.json"):
        try:
            with open("gesture_config.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Konfiguration konnte nicht geladen werden: {e}")
            return {"gestures": {}, "available_channels": {}}
    else:
        print("WARNING: gesture_config.json nicht gefunden")
        return {"gestures": {}, "available_channels": {}}


def get_action_text(gesture_id: str, config: dict) -> str:
    """Gibt den Aktionstext für die Geste zurück (für die Bildschirmanzeige)"""
    gestures = config.get("gestures", {})
    gesture_info = gestures.get(gesture_id, {})
    return gesture_info.get("action_text", gesture_id)


def get_custom_gesture_info(gesture_name: str):
    """ Custom gesture info"""
    if os.path.exists("custom_gestures.json"):
        try:
            with open("custom_gestures.json", "r", encoding="utf-8") as f:
                custom_gestures = json.load(f)
                if gesture_name in custom_gestures:
                    return custom_gestures[gesture_name]
        except:
            pass
    return None


def check_custom_gesture_permission(user_role: Role, gesture_name: str, config: dict) -> bool:
    """
    Custom gesture Berechtigungkontrol
    """
    gestures = config.get("gestures", {})
    
    if gesture_name not in gestures:
        # Check from gesture_roles.json, if Config (custom gesture)
        if os.path.exists("gesture_roles.json"):
            try:
                with open("gesture_roles.json", "r") as f:
                    roles_data = json.load(f)
                    allowed_roles = roles_data.get(gesture_name, [])
            except:
                return True  
        else:
            
            custom_info = get_custom_gesture_info(gesture_name)
            if custom_info:
                allowed_roles = custom_info.get("roles", [])
            else:
                return True  
    else:
        gesture_info = gestures[gesture_name]
        allowed_roles = gesture_info.get("roles", [])
    
    user_role_str = user_role.value.lower()
    
    # Einfache Pruefung
    if user_role_str in allowed_roles:
        return True
    
    # ROLLENHIERARCHIE
    if user_role == Role.ADMIN:
        return True
    if user_role == Role.INGENIEUR and 'operator' in allowed_roles:
        return True
    
    return False


# NEU: Kommandozeilenargumente pruefen
use_gpio = "--gpio" in sys.argv
use_profinet = "--profinet" in sys.argv

# Wenn gar nicht ausgewählt verwendet beide
if not use_gpio and not use_profinet:
    use_gpio = True
    use_profinet = True

# ----------------------------------------
# INITIALIZATION
# ----------------------------------------
print("=" * 50)
print("ROLLENBASIERTE GESTENSTEUERUNG - CUSTOM SUPPORT")
print("=" * 50)

# Config laden
gesture_config = load_gesture_config()
print("\n[CONFIG] Gesture Configuration geladen")

# GPIO Controller 
if use_gpio:
    gpio_control = GpioController(duration=10, auto_load=True)
    print("[SYSTEM] GPIO-Modus aktiviert")
else:
    gpio_control = None
    print("[SYSTEM] GPIO-Modus deaktiviert")

#  PLC Controller and connection
if use_profinet:
    plc_control = PLCController()
    plc_connected = plc_control.connect()
    if plc_connected:
        print("[SYSTEM]  PLC PROFINET aktiv")
    else:
        print("[SYSTEM]  PLC PROFINET nicht aktiv")
else:
    plc_control = None
    plc_connected = False
    print("[SYSTEM] PLC PROFINET deaktiviert")

# Datenbank, Gestendetektor
faces = FaceDatabase()
gesture_detector = GestureDetector()

# MediaPipe Zeichenwerkzeuge
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_pose = mp.solutions.pose

# Kamera öffnen
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

print("w,h,fps,buf:",
      cap.get(cv2.CAP_PROP_FRAME_WIDTH),
      cap.get(cv2.CAP_PROP_FRAME_HEIGHT),
      cap.get(cv2.CAP_PROP_FPS),
      cap.get(cv2.CAP_PROP_BUFFERSIZE),
      flush=True)

system_text = ""
frame_skip = 3
frame_count = 0

face_skip = 7          # 1 Gesichtserkennung alle 7 Frames
recognized_faces = []  # cache: last faces

# Visualisierungseinstellungen
show_landmarks = False
show_pose = False

# Gesture ID -> Action mapping (Builtin gestures)
event_to_action = {
    "open": Action.START,
    "index_up": Action.SET,
    "peace": Action.RESET,
    "three_fingers_row": Action.STOP
}

print("\n[SYSTEM] Bereit. Druecken Sie 'q' zum Beenden.")
print("         'r' zum Reload der GPIO-Pins")
print("         'l' zum Umschalten der Hand-Landmarks")
print("         'p' zum Umschalten der Pose-Landmarks")
print("=" * 50)
t0 = time.perf_counter()
fps = 0.0
acc_face = acc_gesture = acc_draw = acc_total = 0.0
n_stat = 0
t_stat = time.perf_counter()

try:
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        t_loop0 = time.perf_counter()   
        t_gpio_latency = 0.0           
        t_plc_latency = 0.0
        t_gesture = 0.0
        t_draw = 0.0

        now = time.perf_counter()
        dt = now - t0
        t0 = now
        if dt > 0:
            fps = 0.9 * fps + 0.1 * (1.0 / dt)

        #cv2.putText(frame, f"FPS={fps:.1f}", (10, 25),
                    #cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)
        
        frame_count += 1
        
        # ============================================
        # SICHERHEITSKONTROLLE 1: Gesichtserkennung
        # ============================================
        # Gesichtserkennung nicht in jedem Frame
        if frame_count % face_skip == 0:
            t0f = time.perf_counter()
            recognized_faces = faces.recognize(frame)
            t_face = (time.perf_counter() - t0f) * 1000.0
        else:
            t_face = 0.0   # in dieser Runde keine Gesichtserkennung, Cache verwenden

        t0d = time.perf_counter()
        
        # --- Visualisierung der Landmarks ---
        if show_landmarks or show_pose:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            t_draw = (time.perf_counter() - t0d) * 1000.0
            
            #  Hand-Landmarks zeichnen 
            if show_landmarks:
                gesture_detector._hands.find_hands(frame, draw=True)
            
            # Pose-Landmarks zeichnen
            if show_pose:
                results_pose = gesture_detector._pose.process(rgb_frame)
                if results_pose.pose_landmarks:
                    mp_drawing.draw_landmarks(
                        frame,
                        results_pose.pose_landmarks,
                        mp_pose.POSE_CONNECTIONS,
                        landmark_drawing_spec=mp_drawing.DrawingSpec(
                            color=(0, 255, 0), thickness=2, circle_radius=3
                        ),
                        connection_drawing_spec=mp_drawing.DrawingSpec(
                            color=(0, 255, 255), thickness=2
                        )
                    )

        # ============================================
        # SICHERHEITSKONTROLLE 1:  Ist ein Person
        # ============================================
        if len(recognized_faces) != 1:
            if len(recognized_faces) > 1:
                system_text = "FEHLER: Mehrere Personen erkannt! System blockiert."
            else:
                system_text = ""
            
            for r in recognized_faces:
                t, rr, b, l = r.box
                cv2.rectangle(frame, (l, t), (rr, b), (0, 0, 255), 2)
                cv2.putText(frame, f"{r.name} ({r.role.value})", (l, max(20, t-10)),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
        
        else:
            # ============================================
            # EINE Person erkannt 
            # ============================================
            active_person = recognized_faces[0]
            t, rr, b, l = active_person.box
            
            # Gesichtsrahmen zeichnen (Grün)
            cv2.rectangle(frame, (l, t), (rr, b), (0, 255, 0), 2)
            cv2.putText(frame, f"{active_person.name} ({active_person.role.value})",
                       (l, max(20, t-10)),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
            
            # Gestenerkennung (Sicherheitkontrolle 3: Hand-Körper-Gesicht gehört gleiche Person?)
            if frame_count % frame_skip == 0:
                t0g = time.perf_counter()
                event, error_msg = gesture_detector.detect_gesture_with_face(frame, active_person.box)
                t_gesture = (time.perf_counter() - t0g) * 1000.0
                
                if error_msg:
                    # ============================================
                    # SICHERHEITSKONTROLLE 3: Unsuccess
                    # ============================================
                    system_text = error_msg
                
                else:
                    # ============================================
                    # Alle SICHERHEITSKONTROLLE erfolg
                    # Gesture Operation und Berechtigung
                    # ============================================
                    
                    # Pruefung auf feste Gesten (Builtin)
                    action = event_to_action.get(event) if event else None
                    
                    if action:
                        # ============================================
                        # BUILTIN GESTURE - ROLE KONTROLLE + GPIO
                        # ============================================
                        if is_allowed(active_person.role, action):
                            #  ACTION_TEXT (gesture_config.json)
                            system_text = get_action_text(event, gesture_config)
                            
                            # GPIO ausloesen (Channel verwenden)
                            if use_gpio and gpio_control:
                                channel = gpio_control.get_channel_for_gesture(event)
                                if channel:
                                    t0_io = time.perf_counter()
                                    gpio_control.activate_action(channel)
                                    t_gpio_latency = (time.perf_counter() - t0_io) * 1000.0 # ms cinsinden
                                    print(f"[GPIO] Builtin '{event}': {channel} aktiviert → {system_text}")
                                else:
                                    print(f"⚠ [GPIO] Builtin '{event}': Kanal nicht gefunden")
                            
                            #  PLC activate
                            if use_profinet and plc_connected:
                                t0_plc = time.perf_counter()
                                plc_control.activate_action(event)
                                t_plc_latency = (time.perf_counter() - t0_plc) * 1000.0
                            
                            # Auf Bildschirm ausgeben (Gruen - Erfolgreich)
                            cv2.putText(frame, system_text, (10, 50),
                                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
                        else:
                            system_text = f" KEINE BERECHTIGUNG fuer diese Aktion!"
                            cv2.putText(frame, "KEINE BERECHTIGUNG", (10, 50),
                                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
                    
                    # ============================================
                    # CUSTOM GESTURE - ROLE KONTROLLE + GPIO
                    # ============================================
                    elif event:
                        # Custom gesture gefunden
                        if check_custom_gesture_permission(active_person.role, event, gesture_config):
                            # BERECHTIGT- Custom gesture  + GPIO activate
                            custom_info = get_custom_gesture_info(event)
                            if custom_info:
                                action_text = custom_info.get("action_text", event)
                                system_text = f" {action_text}"
                                
                                #  GPIO tetikle
                                if use_gpio and gpio_control:
                                    channel = gpio_control.get_channel_for_gesture(event)
                                    if channel:
                                        t0_io = time.perf_counter()
                                        gpio_control.activate_action(channel)
                                        t_gpio_latency = (time.perf_counter() - t0_io) * 1000.0
                                        print(f"[GPIO] Custom '{event}': {channel} aktiviert → {action_text}")
                                    else:
                                        print(f"⚠ [GPIO] Custom '{event}':Kanal nicht gefunden")
                                
                                #  PLC activate
                                if use_profinet and plc_connected:
                                    t0_plc = time.perf_counter()
                                    plc_control.activate_action(event)
                                    t_plc_latency = (time.perf_counter() - t0_plc) * 1000.0
                            else:
                                system_text = f"✓ Erkannt: {event} (Custom)"
                            
                            # Schreib am Monitor
                            cv2.putText(frame, system_text, (10, 50),
                                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 165, 255), 3)
                        else:
                            # NICHT BERECHTIGT
                            system_text = f" KEINE BERECHTIGUNG fuer '{event}'!"
                            cv2.putText(frame, f"{event} - KEINE BERECHTIGUNG", (10, 50),
                                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
        
        # --- Systemmeldung auf dem Bildschirm anzeigen ---
        if system_text:
            # Schatten
            cv2.putText(frame, system_text, (10, 94),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 3)
            
            # Farbe
            if "WARNUNG" in system_text:
                color = (0, 165, 255)  # Orange
            elif "FEHLER" in system_text or "KEINE BERECHTIGUNG" in system_text:
                color = (0, 0, 255)  # Rot
            elif "Custom" in system_text or "[OK]" in system_text:
                color = (255, 165, 0)  # Orange
            elif "Start" in system_text or "eingestellt" in system_text or "zurueckgesetzt" in system_text or "Stop" in system_text:
                color = (0, 128, 0)  # Grün
            else:
                color = (0, 255, 255)  # Gelb
            
            cv2.putText(frame, system_text, (10, 94),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
        # Status 
        info_text = f"Personen: {len(recognized_faces)} | Hand: {'AN' if show_landmarks else 'AUS'} | Pose: {'AN' if show_pose else 'AUS'}"
        #cv2.putText(frame, info_text, (10, frame.shape[0]-10),
                   #cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 2)
        

        t_total = (time.perf_counter() - t_loop0) * 1000.0

        # ms aktuell auf dem Bildschirm
        #cv2.putText(frame, f"ms tot={t_total:.0f} face={t_face:.0f} gest={t_gesture:.0f} draw={t_draw:.0f}",
                    #(10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,255,255), 2)

        # 1 sec average (terminal)
        acc_face += t_face
        acc_gesture += t_gesture
        acc_draw += t_draw
        acc_total += t_total
        n_stat += 1

        if time.perf_counter() - t_stat >= 1.0:
            print(f"[ms avg] tot={acc_total/n_stat:.1f} face={acc_face/n_stat:.1f} "
                f"gest={acc_gesture/n_stat:.1f} draw={acc_draw/n_stat:.1f}",
                flush=True)
            acc_face = acc_gesture = acc_draw = acc_total = 0.0
            n_stat = 0
            t_stat = time.perf_counter()
        
        if enable_logging and logger:
            g_name = event if 'event' in locals() and event else "None"
            logger.log_frame(
                frame, 
                gesture_name=g_name, 
                display_fps=fps, 
                l_total=t_total,   
                l_face=t_face,     
                l_gest=t_gesture,
                l_gpio=t_gpio_latency, 
                l_plc=t_plc_latency
            )
        
        cv2.imshow("Rollenbasierte Gestensteuerung", frame)
        
        # Tastensteuerung
        k = cv2.waitKey(1) & 0xFF
        if k == ord('q'):
            print("\n[SYSTEM] Beende Programm...")
            break
        elif k == ord('l'):
            show_landmarks = not show_landmarks
            print(f"[DISPLAY] Hand-Landmarks: {'AN' if show_landmarks else 'AUS'}")
        elif k == ord('p'):
            show_pose = not show_pose
            print(f"[DISPLAY] Pose-Landmarks: {'AN' if show_pose else 'AUS'}")
        elif k == ord('r'):
            #  GPIO Pins laden
            print("\n[SYSTEM] GPIO-Pins werden neu geladen...")
            if gpio_control:
                gpio_control.reload_pins()
            gesture_config = load_gesture_config()
            
            #  PLC Config laden
            if plc_control:
                plc_control.load_plc_config()
                plc_connected = plc_control.connect()
            
            print("[SYSTEM] Config aktualisiert!")
        
        #  Fenster schliessen Button
        if cv2.getWindowProperty("Rollenbasierte Gestensteuerung", cv2.WND_PROP_VISIBLE) < 1:
            print("\n[SYSTEM] Fenster geschlossen - Beende Programm...")
            break

finally:
    if enable_logging and logger:
        logger.save_to_csv()
    print("\n[CLEANUP] Ressourcen werden freigegeben...")
    gesture_detector.close()
    cap.release()
    cv2.destroyAllWindows()
    
    if gpio_control:
        gpio_control.cleanup()
    
    if plc_control:
        plc_control.cleanup()
    
    print("[CLEANUP] Fertig. Programm beendet.")
