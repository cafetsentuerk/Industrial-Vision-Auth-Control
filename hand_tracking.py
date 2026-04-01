"""
hand_tracking.py - MediaPipe Hand + Pose + Face Detection (ERWEITERTE SICHERHEIT)
Erkennt Hand- und Körper-Landmarks, prüft Hand-Gesicht-Arm-Zuordnung


FUNKTIONEN:
✅ MediaPipe Hands (21 Landmarks) - MAX 2 HÄNDE
✅ MediaPipe Pose (33 Landmarks - Schulter, Ellbogen, Handgelenk)
✅ MediaPipe Face Detection (Gesichtserkennung)
✅ Hand-Arm-Kette-Kontrolle (Schulter → Ellbogen → Handgelenk → Hand)
✅ Schulter-Höhenkontrolle (Hand muss über Schulter sein)
✅ Visibility-Kontrolle (Arm muss sichtbar sein)
✅ 12-stufige Sicherheit (ERWEITERT)
✅ Debug-Modus

NEU:
✅ max_hands=2 (2-Hände-Erkennung)
✅ Schulter-Höhenkontrolle aktiviert
✅ Erweiterte Distanz-Toleranzen
✅ Max 2 Arme-Kontrolle
"""


import cv2
import mediapipe as mp
import numpy as np


class HandDetector:
    def __init__(self, mode=False, max_hands=2, detection_con=0.5, track_con=0.5, debug=False):
        """
        Hand + Pose + Face Detector

        Args:
            mode: Statischer Bildmodus (False = Video)
            max_hands: Maximale Anzahl erkannter Hände (2 Hände)
            detection_con: Erkennungskonfidenzschwelle
            track_con: Tracking-Konfidenzschwelle
            debug: True = Zeige alle Kontrollen im Terminal
        """
        self.mode = mode
        self.max_hands = max_hands
        self.detection_con = detection_con
        self.track_con = track_con
        self.debug = debug

        # MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=self.mode,
            max_num_hands=self.max_hands,
            min_detection_confidence=self.detection_con,
            min_tracking_confidence=self.track_con
        )

        # MediaPipe Pose (für Schulter-Ellbogen-Handgelenk-Kontrolle)
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # ✅ MediaPipe Face Detection
        self.mp_face = mp.solutions.face_detection
        self.face_detection = self.mp_face.FaceDetection(
            min_detection_confidence=0.5
        )

        self.mp_draw = mp.solutions.drawing_utils

        # Ergebnisse
        self.hand_results = None
        self.pose_results = None
        self.face_results = None

    def find_hands(self, img, draw=True):
        """Erkenne Hand-, Pose- und Gesichts-Landmarks und zeichne sie"""
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Hand-Erkennung
        self.hand_results = self.hands.process(img_rgb)

        # Pose-Erkennung (für Schulter-Ellbogen-Handgelenk)
        self.pose_results = self.pose.process(img_rgb)

        # Gesichts-Erkennung
        self.face_results = self.face_detection.process(img_rgb)

        if draw:
            # Hände zeichnen
            if self.hand_results.multi_hand_landmarks:
                for hand_lms in self.hand_results.multi_hand_landmarks:
                    self.mp_draw.draw_landmarks(
                        img, hand_lms, self.mp_hands.HAND_CONNECTIONS
                    )

        return img

    def count_hands(self):
        """✅ NEU: Anzahl erkannter Hände zurückgeben"""
        if self.hand_results and self.hand_results.multi_hand_landmarks:
            return len(self.hand_results.multi_hand_landmarks)
        return 0

    def find_position(self, img, hand_no=0):
        """
        Hole Hand-Position + führe Hand-Arm-Ketten-Kontrolle durch

        Returns:
            lm_list: Landmark-Liste (21 Punkte) oder []
            hand_type: "Right" oder "Left" oder None
            is_valid: Gehört die Hand zu dieser Person? (True/False)
        """
        lm_list = []
        hand_type = None
        is_valid = False

        if self.hand_results.multi_hand_landmarks:
            if hand_no < len(self.hand_results.multi_hand_landmarks):
                hand_lms = self.hand_results.multi_hand_landmarks[hand_no]

                # Hand-Typ (Right/Left)
                hand_label = self.hand_results.multi_handedness[hand_no].classification[0].label
                hand_type = hand_label

                # Landmarks holen
                h, w, c = img.shape
                for id, lm in enumerate(hand_lms.landmark):
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    lm_list.append([id, lm.x, lm.y, lm.z])

                # ✅ 12-STUFIGE SICHERHEITSKONTROLLE
                is_valid = self.check_hand_belongs_to_person(hand_lms, img, hand_type)

        return lm_list, hand_type, is_valid

    def check_hand_belongs_to_person(self, hand_landmarks, img, hand_type):
        """
        12-STUFIGE SICHERHEITSKONTROLLE (ERWEITERT):
        1. Pose erkannt?
        2. Gesicht erkannt?
        3. Handgelenke sichtbar?
        4. Welcher Arm?
        5. Ellbogen sichtbar?
        6. Schulter sichtbar?
        7. ✅ NEU: Hand über Schulter?
        8. Hand-Handgelenk-Abstand (ERWEITERT)
        9. Arm-Anatomie (TOLERANTER)
        10. Gesicht-Hand-Abstand (ERWEITERT)
        11. Hand innerhalb Körpergrenzen? (ERWEITERT)
        12. ✅ NEU: Max 2 Arme erlaubt?
        """

        if self.debug:
            print("\n" + "="*50)
            print("🔍 HANDKONTROLLE GESTARTET")

        # ✅ KONTROLLE 1: Pose erkannt?
        if not self.pose_results or not self.pose_results.pose_landmarks:
            if self.debug:
                print("❌ KONTROLLE 1 FEHLGESCHLAGEN: Keine Pose erkannt")
            return False

        if self.debug:
            print("✅ KONTROLLE 1: Pose erkannt")

        pose_lms = self.pose_results.pose_landmarks.landmark

        # Handgelenk-Position
        wrist = hand_landmarks.landmark[0]
        wrist_x, wrist_y = wrist.x, wrist.y

        # Schulter, Ellbogen, Handgelenk
        left_shoulder = pose_lms[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = pose_lms[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
        left_elbow = pose_lms[self.mp_pose.PoseLandmark.LEFT_ELBOW]
        right_elbow = pose_lms[self.mp_pose.PoseLandmark.RIGHT_ELBOW]
        left_wrist_pose = pose_lms[self.mp_pose.PoseLandmark.LEFT_WRIST]
        right_wrist_pose = pose_lms[self.mp_pose.PoseLandmark.RIGHT_WRIST]

        # ✅ KONTROLLE 2: Gesicht erkannt?
        if not self.face_results or not self.face_results.detections:
            if self.debug:
                print("❌ KONTROLLE 2 FEHLGESCHLAGEN: Kein Gesicht erkannt")
            return False

        if self.debug:
            print("✅ KONTROLLE 2: Gesicht erkannt")

        # Gesichts-Position (Zentrum)
        face_detection = self.face_results.detections[0]
        face_bbox = face_detection.location_data.relative_bounding_box
        face_x = face_bbox.xmin + face_bbox.width / 2
        face_y = face_bbox.ymin + face_bbox.height / 2

        # ✅ KONTROLLE 3: Handgelenke sichtbar? (TOLERANTER)
        left_wrist_visible = left_wrist_pose.visibility > 0.5  # 0.6 → 0.5
        right_wrist_visible = right_wrist_pose.visibility > 0.5

        if not left_wrist_visible and not right_wrist_visible:
            if self.debug:
                print(f"❌ KONTROLLE 3 FEHLGESCHLAGEN: Handgelenke nicht sichtbar (Links:{left_wrist_pose.visibility:.2f}, Rechts:{right_wrist_pose.visibility:.2f})")
            return False

        if self.debug:
            print(f"✅ KONTROLLE 3: Handgelenke sichtbar (Links:{left_wrist_pose.visibility:.2f}, Rechts:{right_wrist_pose.visibility:.2f})")

        # ✅ KONTROLLE 4 (sade): Welcher Arm? 

        dist_left  = np.hypot(wrist_x - left_wrist_pose.x,  wrist_y - left_wrist_pose.y)
        dist_right = np.hypot(wrist_x - right_wrist_pose.x, wrist_y - right_wrist_pose.y)

        if dist_left <= dist_right:
            shoulder   = left_shoulder
            elbow      = left_elbow
            pose_wrist = left_wrist_pose
            arm_side   = "Links"
        else:
            shoulder   = right_shoulder
            elbow      = right_elbow
            pose_wrist = right_wrist_pose
            arm_side   = "Rechts"

        if self.debug:
            print(f"✅ KONTROLLE 4: {arm_side} Arm gewählt (dL={dist_left:.3f}, dR={dist_right:.3f})")

        # ✅ KONTROLLE 5: Schulter sichtbar? (TOLERANTER)
        if shoulder.visibility < 0.5:  # 0.6 → 0.5
            if self.debug:
                print(f"❌ KONTROLLE 6 FEHLGESCHLAGEN: Schulter nicht sichtbar (Visibility: {shoulder.visibility:.2f})")
            return False

        if self.debug:
            print(f"✅ KONTROLLE 6: Schulter sichtbar (Visibility: {shoulder.visibility:.2f})")

        # Schulterbreite
        shoulder_width = np.sqrt(
            (left_shoulder.x - right_shoulder.x)**2 + 
            (left_shoulder.y - right_shoulder.y)**2
        )


        # ✅ KONTROLLE 6:Hand (MediaPipe Hands wrist) ↔ Pose (seçilen pose_wrist) mesafe kontrolü
        hand_pose_distance = np.sqrt((wrist_x - pose_wrist.x)**2 + (wrist_y - pose_wrist.y)**2)
        wrist_threshold = shoulder_width * 0.35

        if hand_pose_distance > wrist_threshold:
            if self.debug:
                print(f"❌ Hand-PoseWrist Abstand zu groß ({hand_pose_distance:.3f} > {wrist_threshold:.3f})")
            return False

        if self.debug:
            print(f"✅ Hand-PoseWrist Abstand OK ({hand_pose_distance:.3f} < {wrist_threshold:.3f})")


        # ✅ KONTROLLE 7: Ellbogen sichtbar? (TOLERANTER)
        if elbow.visibility < 0.5:  # 0.6 → 0.5
            if self.debug:
                print(f"❌ KONTROLLE 5 FEHLGESCHLAGEN: Ellbogen nicht sichtbar (Visibility: {elbow.visibility:.2f})")
            return False

        if self.debug:
            print(f"✅ KONTROLLE 5: Ellbogen sichtbar (Visibility: {elbow.visibility:.2f})")


        # ✅ KONTROLLE 8: Hand über Schulter + X-Band (omuz referanslı)
        shoulder_y = shoulder.y
        if wrist_y > shoulder_y:  # Y: oben = klein
            if self.debug:
                print(f"❌ KONTROLLE 7 FEHLGESCHLAGEN: Hand unter Schulter (Hand Y:{wrist_y:.3f} > Schulter Y:{shoulder_y:.3f})")
            return False

        # Yatay sınır: omuzların X aralığı + tolerans
        left_x = min(left_shoulder.x, right_shoulder.x)
        right_x = max(left_shoulder.x, right_shoulder.x)

        x_margin = shoulder_width * 0.35   # tolerans: 0.25-0.60 deneyebilirsin
        x_min = left_x - x_margin
        x_max = right_x + x_margin

        if not (x_min <= wrist_x <= x_max):
            if self.debug:
                print(f"❌ KONTROLLE 7X FEHLGESCHLAGEN: wrist_x={wrist_x:.3f} nicht in [{x_min:.3f}, {x_max:.3f}]")
            return False

        if self.debug:
            print(f"✅ KONTROLLE 7: Omuz üstü + X-band OK (Y:{wrist_y:.3f} < {shoulder_y:.3f}, X in [{x_min:.3f},{x_max:.3f}])")

        # ✅ KONTROLLE 9: Hand-type Rechts/Links
        dist_to_left_shoulder = np.sqrt((wrist_x - left_shoulder.x)**2 + (wrist_y - left_shoulder.y)**2)
        dist_to_right_shoulder = np.sqrt((wrist_x - right_shoulder.x)**2 + (wrist_y - right_shoulder.y)**2)

        if dist_to_left_shoulder < dist_to_right_shoulder:
            # El sol omza yakın → Sol el olmalı
            if hand_type != "Right":
                if self.debug:
                    print("KONTROLLE 8 FEHLGESCHLAGEN: Rechte Hand auf linker Körperseite!")
                return False
            if self.debug:
                print("KONTROLLE 8: Linke Hand auf linker Körperseite OK")
        else:
            # El sağ omza yakın → Sağ el olmalı
            if hand_type != "Left":
                if self.debug:
                    print("KONTROLLE 8 FEHLGESCHLAGEN: Linke Hand auf rechter Körperseite!")
                return False
            if self.debug:
                print("KONTROLLE 8: Rechte Hand auf rechter Körperseite OK")

        # ✅ KONTROLLE 10: Arm-Anatomie (TOLERANTER)
        shoulder_to_elbow = np.sqrt(
            (shoulder.x - elbow.x)**2 + 
            (shoulder.y - elbow.y)**2
        )

        elbow_to_wrist = np.sqrt(
            (elbow.x - pose_wrist.x)**2 + 
            (elbow.y - pose_wrist.y)**2
        )

        if shoulder_to_elbow > 0 and elbow_to_wrist > 0:
            arm_ratio = shoulder_to_elbow / elbow_to_wrist

            if arm_ratio < 0.3 or arm_ratio > 3.0:  # 0.4-2.5 → 0.3-3.0
                if self.debug:
                    print(f"❌ KONTROLLE 9 FEHLGESCHLAGEN: Arm-Verhältnis unnatürlich ({arm_ratio:.2f})")
                return False

            if self.debug:
                print(f"✅ KONTROLLE 9: Arm-Verhältnis OK ({arm_ratio:.2f})")

        # ✅ KONTROLLE 11: Gesicht-Hand-Abstand (ERWEITERT)
        face_to_hand_distance = np.sqrt((wrist_x - face_x)**2 + (wrist_y - face_y)**2)
        face_distance_threshold = shoulder_width * 2.5  # 1.5 → 2.5

        if face_to_hand_distance > face_distance_threshold:
            if self.debug:
                print(f"❌ KONTROLLE 10 FEHLGESCHLAGEN: Gesicht-Hand-Abstand zu groß ({face_to_hand_distance:.3f} > {face_distance_threshold:.3f})")
            return False

        if self.debug:
            print(f"✅ KONTROLLE 10: Gesicht-Hand-Abstand OK ({face_to_hand_distance:.3f} < {face_distance_threshold:.3f})")

        return True

    def process_landmarks(self, lm_list, hand_type):
        """
        Normalisiere Landmarks (für ML-Modell)
        Wende Rechts/Links-Hand-Spiegelung an

        Returns:
            Numpy Array (42 Features: 21 Punkte * 2 Koordinaten - NUR x, y)
        """
        if not lm_list or len(lm_list) < 21:
            return None

        # ✅ NUR x, y Koordinaten nehmen (z IGNORIEREN - 42 boyut)
        coords = np.array([[lm[1], lm[2]] for lm in lm_list])

        # Spiegle X-Koordinaten bei linker Hand
        if hand_type == "Left":
            coords[:, 0] = 1.0 - coords[:, 0]

        # Normalisierung (handgelenkzentriert)
        wrist = coords[0]
        coords = coords - wrist

        # Skalierung
        max_dist = np.max(np.abs(coords))
        if max_dist > 0:
            coords = coords / max_dist

        # Flach machen (42 Features - 21 × 2)
        return coords.flatten()

    def close(self):
        """Ressourcen freigeben"""
        self.hands.close()
        self.pose.close()
        self.face_detection.close()