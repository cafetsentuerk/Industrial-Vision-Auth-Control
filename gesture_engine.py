# gesture_engine.py - Gesture ML Model Manager

"""
Gesten ML Modell Management
- Nutzt KNN (K-Nearest Neighbors)
- Sammelt und trainiert Landmark-Daten
- Erstellt Vorhersagen
- Speichert/laedt Daten mit Pickle
- 42 DIMENSIONEN (21 Landmarks × 2 Koordinaten: x, y)
"""

import numpy as np
import pickle
import os
from sklearn.neighbors import KNeighborsClassifier


class GestureModel:
    def __init__(self):
        """ML Model Manager"""
        self.data_x = []  # Landmark-Daten
        self.data_y = []  # Gesten-Namen
        self.model = None
        self.is_trained = False
        self.data_file = "gesture_data.pkl"
        
        # Vorhandene Daten laden
        self.load_data()
    
    def add_sample(self, landmarks, gesture_name):
        """
        Ein neues Beispiel hinzufuegen
        
        Args:
            landmarks: Numpy array (42 features: 21 landmarks * 2 coordinates)
            gesture_name: Gesten-Name
        """
        if landmarks is None or len(landmarks) == 0:
            print("[WARNING] Ungueltige Landmark-Daten!")
            return
        
        self.data_x.append(landmarks)
        self.data_y.append(gesture_name)
    
    def train(self):
        """
        KNN-Modell trainieren + speichern
        
        Returns:
            (success: bool, message: str)
        """
        if len(self.data_x) < 10:
            return False, "Mindestens 10 Samples erforderlich!"
        
        try:
            X = np.array(self.data_x)
            y = np.array(self.data_y)
            
            # KNN-Training
            self.model = KNeighborsClassifier(n_neighbors=min(5, len(X)))
            self.model.fit(X, y)
            
            # Speichern
            self.save_data()
            
            unique_gestures = len(set(y))
            self.is_trained = True
            
            return True, f"Training erfolgreich!\n{len(X)} Samples, {unique_gestures} Gesten"
        
        except Exception as e:
            return False, f"Training-Fehler: {str(e)}"
    
    def predict(self, landmarks):
        """
        Gesten-Vorhersage machen
        
        Args:
            landmarks: Numpy array (42 features)
        
        Returns:
            (gesture_name: str, confidence: float)
        """
        if not self.is_trained or self.model is None:
            return "Modell nicht trainiert", 0.0
        
        if landmarks is None or len(landmarks) == 0:
            return "Ungueltige Daten", 0.0
        
        try:
            # In Numpy-Array umwandeln (Reshape)
            landmarks_array = np.array([landmarks])
            
            # Distanz zum nächsten Nachbarn abrufen
            distances, indices = self.model.kneighbors(landmarks_array)
            nearest_distance = distances[0][0]
            
            # Vorhersage erstellen
            prediction = self.model.predict(landmarks_array)[0]
            
            # Konfidenz-Score berechnen (distanzbasiert)
            # Distanz 0 → 100% Konfidenz
            # Distanz 0.5 → 50% Konfidenz
            # Distanz 1.0+ → 0% Konfidenz
            confidence = max(0.0, 1.0 - (nearest_distance / 0.7))
            
            return prediction, confidence
        
        except Exception as e:
            print(f"[ERROR] Vorhersage-Fehler: {e}")
            return "Fehler", 0.0
    
    def save_data(self):
        """Daten speichern"""
        try:
            data = {
                'x': self.data_x,
                'y': self.data_y,
                'model': self.model,
                'trained': self.is_trained
            }
            
            with open(self.data_file, 'wb') as f:
                pickle.dump(data, f)
            
            print(f"[OK] Daten gespeichert: {self.data_file}")
        
        except Exception as e:
            print(f"[ERROR] Speicher-Fehler: {e}")
    
    def load_data(self):
        """Daten laden"""
        if not os.path.exists(self.data_file):
            print(f"[INFO] {self.data_file} nicht gefunden (Erststart)")
            return
        
        try:
            with open(self.data_file, 'rb') as f:
                data = pickle.load(f)
            
            self.data_x = data.get('x', [])
            self.data_y = data.get('y', [])
            self.model = data.get('model', None)
            self.is_trained = data.get('trained', False)
            
            if self.is_trained and self.model:
                unique = len(set(self.data_y))
                print(f"[OK] Modell geladen: {len(self.data_x)} Beispiele, {unique} Gesten")
            else:
                print(f"[INFO] {len(self.data_x)} Beispiele geladen (Modell nicht trainiert)")
        
        except Exception as e:
            print(f"[ERROR] Lade-Fehler: {e}")
            self.data_x = []
            self.data_y = []
            self.model = None
            self.is_trained = False
    
    def delete_class(self, gesture_name):
        """
        Bestimmte Geste löschen
        
        Args:
            gesture_name: Name der zu löschenden Geste
        """
        if gesture_name not in self.data_y:
            print(f"[WARNING] '{gesture_name}' nicht gefunden!")
            return
        
        # Daten der Geste filtern
        new_data_x = []
        new_data_y = []
        
        removed_count = 0
        for i, name in enumerate(self.data_y):
            if name != gesture_name:
                new_data_x.append(self.data_x[i])
                new_data_y.append(name)
            else:
                removed_count += 1
        
        self.data_x = new_data_x
        self.data_y = new_data_y
        
        # Wenn das Modell trainiert ist, neu trainieren
        if len(self.data_x) >= 10:
            self.train()
        else:
            self.is_trained = False
            self.model = None
            self.save_data()
        
        print(f"[OK] '{gesture_name}' geloescht ({removed_count} Beispiele)")
    
    def get_class_stats(self):
        """
        Statistik für jede Geste
        
        Returns:
            dict: {gesture_name: sample_count}
        """
        stats = {}
        for name in self.data_y:
            stats[name] = stats.get(name, 0) + 1
        return stats
    
    def clear_all(self):
        """Alle Daten bereinigen"""
        self.data_x = []
        self.data_y = []
        self.model = None
        self.is_trained = False
        
        # Datei löschen
        if os.path.exists(self.data_file):
            os.remove(self.data_file)
            print(f"[OK] {self.data_file} gelöscht")
        
        print("[OK] Alle Daten bereinigt")
