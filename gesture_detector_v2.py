"""
gesture_detector_v2.py - CUSTOM GESTURE + ERWEITERTE SICHERHEIT

FUNKTIONEN:
- Custom Gesture Unterstuetzung (gesture_data.pkl)
- Hand-Koerper-Zuordnung (Hand muss zur Person gehoeren)
- 12-stufige Sicherheitskontrolle ueber HandDetector
- 2-Haende-Kontrolle (Warnung bei 2 Haenden)
- Regelbasierte Erkennung (Builtin-Gesten)
- ML-Modell (Custom-Gesten)
- Schulter-Hoehenkontrolle

NEU:
- 2-Haende-Detektion mit deutscher Fehlermeldung
- Erweiterte Distanz-Toleranzen
"""

from typing import Optional, Tuple
import cv2
import mediapipe as mp
import numpy as np
import os
import pickle
from hand_tracking import HandDetector


class GestureDetector:
    def __init__(self, debounce_n: int = 3):
        """
        Gesture Detector mit Custom-Gesture-Unterstützung

        Args:
            debounce_n: Anzahl aufeinanderfolgender Frames für Builtin-Gesten
        """
        self.debounce_n = max(1, debounce_n)

        # Debounce für Builtin-Gesten
        self._streak = {"open": 0, "index_up": 0, "peace": 0, "three_fingers_row": 0}

        # CUSTOM GESTURE UNTERSTÜTZUNG
        self.custom_gestures = {}
        self.custom_model = None
        self.load_custom_gestures()

        #  HandDetector mit 12-stufiger Sicherheit
        self._hands = HandDetector(debug=False, max_hands=2)  # 2 Hände

        # MediaPipe Pose (für zusätzliche Kontrollen)
        self._mp_pose = mp.solutions.pose
        self._pose = self._mp_pose.Pose(
            static_image_mode=False,
            model_complexity=0,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def load_custom_gestures(self):
        """Lädt Custom-Gesten aus der Datei gesture_data.pkl"""
        if os.path.exists("gesture_data.pkl"):
            try:
                with open("gesture_data.pkl", "rb") as f:
                    data = pickle.load(f)

                if data.get('trained', False):
                    self.custom_gestures = {
                        'data_x': data['x'],
                        'data_y': data['y']
                    }
                    self.custom_model = data['model']
                    unique_gestures = set(data['y'])
                    print(f"[OK] {len(unique_gestures)} Custom-Gesten geladen: {unique_gestures}")
                else:
                    print("[WARNING] gesture_data.pkl gefunden, aber Modell nicht trainiert")
            except Exception as e:
                print(f"[ERROR] Custom-Geste konnte nicht geladen werden: {e}")
        else:
            print("[INFO] gesture_data.pkl nicht gefunden (Keine Custom-Gesten)")

    def close(self):
        """Ressourcen freigeben"""
        self._hands.close()
        self._pose.close()

    def detect_gesture_with_face(self, frame_bgr, face_box: Tuple[int, int, int, int]) -> Tuple[Optional[str], Optional[str]]:
        """
        Hand-Kopf-Zuordnung und Gestenerkennung + 12-stufige Sicherheitskontrolle

        Args:
            frame_bgr: Video-Frame
            face_box: Gesichts-Bounding-Box (top, right, bottom, left)

        Returns:
            gesture_id: Erkannte Geste oder None
            error_msg: Fehlermeldung oder None
        """
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w = frame_bgr.shape[:2]

        # Hand-Landmarks mit Sicherheitskontrolle erkennen
        self._hands.find_hands(frame_bgr, draw=False)

        #  NEU: 2-HÄNDE-KONTROLLE
        num_hands = self._hands.count_hands()
        if num_hands > 1:
            return None, " 2 HAENDE ERKANNT - BEFEHL BLOCKIERT"

        #  Hand-Position MIT 12-STUFIGER SICHERHEITSKONTROLLE
        lm_list, hand_type, is_valid_hand = self._hands.find_position(frame_bgr)

        #  SICHERHEITSKONTROLLE 1: Ist die Hand gültig?
        if lm_list and not is_valid_hand:
            return None, " WARNUNG: Fremde Hand erkannt!"

        # Keine Hand erkannt
        if not lm_list:
            # Reset debounce
            for k in self._streak:
                self._streak[k] = max(0, self._streak[k] - 1)
            return None, None

        #  SICHERHEITSKONTROLLE 2: Pose erkannt?
        results_pose = self._pose.process(rgb)
        if not results_pose or not results_pose.pose_landmarks:
            return None, " WARNUNG: Koerper nicht erkannt!"

        pose_lms = results_pose.pose_landmarks.landmark

        #  SICHERHEITSKONTROLLE 3: Schulter-Sichtbarkeit
        left_shoulder = pose_lms[self._mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = pose_lms[self._mp_pose.PoseLandmark.RIGHT_SHOULDER]

        if left_shoulder.visibility < 0.5 and right_shoulder.visibility < 0.5:
            return None, " WARNUNG: Schultern nicht sichtbar!"

        #  SICHERHEITSKONTROLLE 4: Hand-Gesicht-Abstand (ERWEITERT)
        face_top, face_right, face_bottom, face_left = face_box
        face_center_x = (face_left + face_right) / 2
        face_center_y = (face_top + face_bottom) / 2
        face_width = face_right - face_left

        # Hand-Position (Handgelenk - normalisiert)
        hand_x = lm_list[0][1]  # Normalisierte X
        hand_y = lm_list[0][2]  # Normalisierte Y

        # Gesichts-Position normalisieren
        face_center_x_norm = face_center_x / w
        face_center_y_norm = face_center_y / h

        # Schulterbreite für Schwellenwert
        shoulder_width = np.sqrt(
            (left_shoulder.x - right_shoulder.x)**2 +
            (left_shoulder.y - right_shoulder.y)**2
        )

        # Hand-Gesicht-Abstand
        hand_face_distance = np.sqrt(
            (hand_x - face_center_x_norm)**2 +
            (hand_y - face_center_y_norm)**2
        )

        # Schwellenwert: 3x Schulterbreite (ERWEITERT: 2.0 → 3.0)
        distance_threshold = shoulder_width * 3.0

        if hand_face_distance > distance_threshold:
            return None, " WARNUNG: Hand zu weit vom Gesicht entfernt!"

        #  ALLE SICHERHEITSKONTROLLEN BESTANDEN
        # Gesture-Erkennung durchführen
        detected = self._classify_gesture(lm_list, hand_type)

        # Debounce-Logik (nur für Builtin-Gesten)
        event = None
        if detected:
            # Wenn Builtin-Geste, debounce anwenden
            if detected in self._streak:
                for k in self._streak:
                    if k == detected:
                        self._streak[k] += 1
                    else:
                        self._streak[k] = max(0, self._streak[k] - 1)

                if self._streak.get(detected, 0) >= self.debounce_n:
                    event = detected
                    self._streak[detected] = 0
            else:
                # Custom Gesture direkt zurückgeben (kein Debounce)
                event = detected
        else:
            for k in self._streak:
                self._streak[k] = max(0, self._streak[k] - 1)

        return event, None

    def _classify_gesture(self, lm_list, hand_type) -> Optional[str]:
        """
        Gesten-Klassifizierung:
        1. Zuerst Builtin-Gesten (regelbasiert)
        2. Dann Custom-Gesten (ML-Modell)

        Args:
            lm_list: Landmark-Liste (21 Punkte, [id, x, y, z])
            hand_type: "Right" oder "Left"

        Returns:
            Gesten-ID oder None
        """
        if not lm_list or len(lm_list) < 21:
            return None

        # 1. BUILTIN-GESTEN (REGELBASIERT)
        builtin_gesture = self._classify_builtin(lm_list)
        if builtin_gesture:
            return builtin_gesture

        # 2.  CUSTOM-GESTEN (ML-MODELL) 
        if self.custom_model is not None:
            custom_result = self._classify_custom(lm_list, hand_type)
            if custom_result:
                return custom_result

        return None

    def _classify_builtin(self, lm_list) -> Optional[str]:
        """
        Regelbasierte Erkennung für Builtin-Gesten

        Args:
            lm_list: Landmark-Liste [[id, x, y, z], ...]

        Returns:
            Gesten-ID oder None
        """
        if len(lm_list) < 21:
            return None

        # Finger-Indizes
        IDX_TIP, IDX_PIP = 8, 6
        MID_TIP, MID_PIP = 12, 10
        RNG_TIP, RNG_PIP = 16, 14
        PNK_TIP, PNK_PIP = 20, 18
        THUMB_TIP, THUMB_IP = 4, 3

        def is_finger_extended(tip_idx, pip_idx):
            """Ist der Finger ausgestreckt? (Y-Koordinate)"""
            return lm_list[tip_idx][2] < lm_list[pip_idx][2]

        def is_thumb_extended(tip_idx, ip_idx):
            """Ist der Daumen ausgestreckt? (X-Koordinate)"""
            return abs(lm_list[tip_idx][1] - lm_list[ip_idx][1]) > 0.04

        # Finger-Status
        thumb_extended = is_thumb_extended(THUMB_TIP, THUMB_IP)
        index_extended = is_finger_extended(IDX_TIP, IDX_PIP)
        middle_extended = is_finger_extended(MID_TIP, MID_PIP)
        ring_extended = is_finger_extended(RNG_TIP, RNG_PIP)
        pinky_extended = is_finger_extended(PNK_TIP, PNK_PIP)

        # Priorität: spezifisch -> allgemein

        # Offene Hand (4 Finger)
        if index_extended and middle_extended and ring_extended and pinky_extended:
            return "open"

        # Drei Finger in einer Reihe
        if (not thumb_extended) and index_extended and middle_extended and ring_extended and (not pinky_extended):
            return "three_fingers_row"

        # Peace (Zeige- und Mittelfinger)
        if (not thumb_extended) and index_extended and middle_extended and (not ring_extended) and (not pinky_extended):
            return "peace"

        # Zeigefinger hoch
        if index_extended and (not middle_extended) and (not ring_extended) and (not pinky_extended):
            return "index_up"

        return None

    def _classify_custom(self, lm_list, hand_type) -> Optional[str]:
        """
         Custom-Gesten-Erkennung via ML-Modell 

        Args:
            lm_list: Landmark-Liste [[id, x, y, z], ...]
            hand_type: "Right" oder "Left"

        Returns:
            Gesten-Name oder None
        """
        try:
            # 1. Landmarks verarbeiten (nur x, y)
            coords = [[lm[1], lm[2]] for lm in lm_list]

            # 2. Normalisierung (handgelenkzentriert)
            base_x, base_y = coords[0][0], coords[0][1]
            temp_lms = []

            for landmark in coords:
                rel_x = landmark[0] - base_x
                rel_y = landmark[1] - base_y

                # Linke Hand spiegeln
                if hand_type == "Left":
                    rel_x = -rel_x

                temp_lms.append([rel_x, rel_y])

            temp_lms = np.array(temp_lms).flatten()

            # 3. Skalierung
            max_value = np.max(np.abs(temp_lms))
            if max_value > 0:
                temp_lms = temp_lms / max_value

            # 4. Vorhersage mit Modell
            landmarks_array = np.array([temp_lms])

            # Nächster Nachbar Distanz
            distances, indices = self.custom_model.kneighbors(landmarks_array)
            nearest_distance = distances[0][0]

            # Konfidenz-Score berechnen
            score = 1.0 - (nearest_distance / 0.7)
            score = max(0.0, min(1.0, score))

            # Schwellenwert: 50% Konfidenz
            if score >= 0.50:
                prediction = self.custom_model.predict(landmarks_array)[0]
                print(f" -> Custom: {prediction} (Konfidenz: {score*100:.1f}%)")
                return prediction

        except Exception as e:
            print(f"[ERROR] Custom-Gesten-Klassifizierung Fehler: {e}")

        return None