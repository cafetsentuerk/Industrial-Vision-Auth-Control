# face_identity_v2.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple
import os
import cv2
import numpy as np
import face_recognition

# # ---- Rollen und Berechtigungen ----
class Role(str, Enum):
    ADMIN = "admin"
    INGENIEUR = "ingenieur"
    OPERATOR = "operator"
    UNKNOWN = "unknown"

class Action(str, Enum):
    SET = "set"      # ☝️ Zeigefinger
    RESET = "reset"  # ✌️ Peace
    START = "start"  # ✋ Offene Hand
    STOP = "stop"    # ✊ Faust

# BERECHTIGUNGSTABELLE (KORRIGIERT!)
ROLE_PERMISSIONS = {
    Role.ADMIN:     {Action.SET, Action.RESET, Action.START, Action.STOP},  # Alle
    Role.INGENIEUR: {Action.SET, Action.RESET},                              # Nur SET, RESET
    Role.OPERATOR:  {Action.START, Action.STOP},                             # Nur START, STOP
    Role.UNKNOWN:   set(),                                                   # Keine
}

def is_allowed(role: Role, action: Action) -> bool:
    return action in ROLE_PERMISSIONS.get(role, set())

@dataclass
class RecognizedFace:
    name: str
    role: Role
    box: Tuple[int, int, int, int]

class FaceDatabase:
    def __init__(self, use_cnn: bool = False):
        self.known_encodings: List[np.ndarray] = []
        self.known_names: List[str] = []
        self.use_cnn = use_cnn
        self.face_detection_model = "cnn" if use_cnn else "hog"
        
        self.frame_count = 0
        self.last_result = []
        
        self._load_faces_from_databank()
        
    def _load_faces_from_databank(self):
        """Lädt alle Gesichter aus dem Ordner 'face_databank' automatisch."""
        databank_path = "face_databank"
        if not os.path.exists(databank_path):
            print(f"[WARNING] Datenbank-Ordner nicht gefunden: {databank_path}")
            return

        print("[INFO] Lade Gesichter aus der Datenbank...")
        for person_folder_name in os.listdir(databank_path):
            person_path = os.path.join(databank_path, person_folder_name)
            
            if os.path.isdir(person_path):
                image_files = [f for f in os.listdir(person_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                if image_files:
                    first_image_path = os.path.join(person_path, image_files[0])
                    person_name_with_role = person_folder_name
                    self._add_face(first_image_path, person_name_with_role)
        print(f"[INFO] {len(self.known_names)} Person(en) geladen.")

    def recognize(self, frame_bgr) -> List[RecognizedFace]:
        self.frame_count += 1
        if self.frame_count % 1 != 0 and self.last_result:
            return self.last_result
        
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        
        face_locations = face_recognition.face_locations(frame_rgb, model=self.face_detection_model)
        face_encodings = face_recognition.face_encodings(frame_rgb, face_locations)
        
        out: List[RecognizedFace] = []
        for enc, (top, right, bottom, left) in zip(face_encodings, face_locations):
            name = "Unknown"
            if self.known_encodings:
                matches = face_recognition.compare_faces(self.known_encodings, enc, tolerance=0.6)
                face_distances = face_recognition.face_distance(self.known_encodings, enc)
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = self.known_names[best_match_index]
            
            role = self._resolve_role(name)
            out.append(RecognizedFace(name=name, role=role, box=(top, right, bottom, left)))
        
        self.last_result = out
        return out
    
    def _add_face(self, img_path: str, name: str):
        try:
            img = face_recognition.load_image_file(img_path)
            encs = face_recognition.face_encodings(img)
            
            if not encs:
                print(f"[WARNING] Kein Gesicht in {img_path} gefunden.")
                return
            
            self.known_encodings.append(encs[0])
            self.known_names.append(name)
            print(f"[OK] Gesicht hinzugefügt: {name}")
        except Exception as e:
            print(f"[ERROR] Fehler beim Laden von {img_path}: {e}")
    
    def _resolve_role(self, label: str) -> Role:
        low = label.lower()
        if low.startswith("admin"): return Role.ADMIN
        if low.startswith("ingenieur"): return Role.INGENIEUR
        if low.startswith("operator"): return Role.OPERATOR
        return Role.UNKNOWN
