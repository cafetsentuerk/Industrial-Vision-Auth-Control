# config_manager.py - JSON-Fokussiertes Config Management

"""
Gesture Config Management System

FEATURES:
- Direktes Lesen aus JSON (create_default_config() entfernt)
- Erstellung von Standard-JSON bei der Erstinstallation
- Verwaltung von Builtin- und Custom-Gesten
"""

import os
import json
import shutil

class GestureConfigManager:
    def __init__(self):
        self.gesture_config = {}
        self.factory_config = {}
        self.ensure_config_files()
        self.load_configs()
    
    def ensure_config_files(self):
        """Überprüft die Existenz von Config-Dateien und erstellt diese bei Bedarf """
        # Wenn gesture_config.json nicht existiert, Standard erstellen
        if not os.path.exists("gesture_config.json"):
            self.create_default_json_files()
            print("[OK] gesture_config.json erstellt")
        
        # Wenn factory_config.json nicht existiert, aus gesture_config.json kopieren
        if not os.path.exists("factory_config.json"):
            shutil.copy("gesture_config.json", "factory_config.json")
            print("[OK] factory_config.json erstellt")
    
    def create_default_json_files(self):
        """Erstellt direkte JSON-Dateien (Standardwerte)"""
        default_config = {
            "gestures": {
                "open": {
                    "enabled": 1,
                    "display_name": "Offene Hand",
                    "description": "Alle Finger offen",
                    "action_text": "System Start",
                    "roles": ["admin", "ingenieur", "operator"],
                    "gpio_pin": 19,
                    "channel": "CH5",
                    "gesture_type": "builtin"
                },
                "index_up": {
                    "enabled": 1,
                    "display_name": "Zeigefinger",
                    "description": "Zeigefinger hoch",
                    "action_text": "System ist eingestellt",
                    "roles": ["admin", "ingenieur"],
                    "gpio_pin": 21,
                    "channel": "CH7",
                    "gesture_type": "builtin"
                },
                "peace": {
                    "enabled": 1,
                    "display_name": "Victory/Peace",
                    "description": "Zwei Finger",
                    "action_text": "System ist zurückgesetzt",
                    "roles": ["admin", "ingenieur"],
                    "gpio_pin": 26,
                    "channel": "CH8",
                    "gesture_type": "builtin"
                },
                "three_fingers_row": {
                    "enabled": 1,
                    "display_name": "Drei Finger",
                    "description": "Drei Finger hoch",
                    "action_text": "System Stop",
                    "roles": ["admin"],
                    "gpio_pin": 20,
                    "channel": "CH6",
                    "gesture_type": "builtin"
                }
            },
            "available_channels": {
                "CH1": {"bcm_pin": 5, "physical_pin": 29, "description": "Kanal 1"},
                "CH2": {"bcm_pin": 6, "physical_pin": 31, "description": "Kanal 2"},
                "CH3": {"bcm_pin": 13, "physical_pin": 33, "description": "Kanal 3"},
                "CH4": {"bcm_pin": 16, "physical_pin": 36, "description": "Kanal 4"},
                "CH5": {"bcm_pin": 19, "physical_pin": 35, "description": "Kanal 5"},
                "CH6": {"bcm_pin": 20, "physical_pin": 38, "description": "Kanal 6"},
                "CH7": {"bcm_pin": 21, "physical_pin": 40, "description": "Kanal 7"},
                "CH8": {"bcm_pin": 26, "physical_pin": 37, "description": "Kanal 8"}
            },
            "settings": {
                "allow_multiple_gestures_same_channel": False,
                "gpio_mode": "BCM"
            }
        }
        
        # In JSON schreiben
        with open("gesture_config.json", "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
    
    def load_configs(self):
        """Lädt alle Config-Dateien"""
        self.gesture_config = self.load_config("gesture_config.json")
        self.factory_config = self.load_config("factory_config.json")
    
    def load_config(self, filename):
        """Lädt eine einzelne Config-Datei"""
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[ERROR] {filename} konnte nicht geladen werden: {e}")
                return {"gestures": {}, "available_channels": {}, "settings": {}}
        else:
            return {"gestures": {}, "available_channels": {}, "settings": {}}
    
    def save_config(self, filename, config):
        """Speichert die Config-Datei"""
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"[OK] {filename} gespeichert")
            return True
        except Exception as e:
            print(f"[ERROR] {filename} konnte nicht gespeichert werden: {e}")
            return False
    
    def save_current_config(self):
        """Speichert die aktuelle Config"""
        return self.save_config("gesture_config.json", self.gesture_config)
    
    def reload_config(self):
        """Config neu laden (um den aktuellen Status nach Neustart zu sehen)"""
        self.load_configs()
    
    def get_gesture_info(self, gesture_id):
        """Gesteninformationen abrufen (Builtin)"""
        return self.gesture_config.get("gestures", {}).get(gesture_id, None)
    
    def get_all_gestures(self):
        """Alle Gesten abrufen"""
        return self.gesture_config.get("gestures", {})
    
    def get_builtin_gestures(self):
        """Nur Builtin-Gesten abrufen"""
        gestures = self.gesture_config.get("gestures", {})
        return {gid: info for gid, info in gestures.items() 
                if info.get("gesture_type") == "builtin"}
    
    def get_available_channels(self):
        """Verfügbare Kanaele abrufen"""
        return list(self.gesture_config.get("available_channels", {}).keys())
    
    def get_channel_info(self, channel):
        """Kanalinformationen abrufen"""
        return self.gesture_config.get("available_channels", {}).get(channel, {})
    
    def update_gesture(self, gesture_id, updates):
        """Gesteninformationen aktualisieren (Builtin)"""
        if gesture_id in self.gesture_config.get("gestures", {}):
            self.gesture_config["gestures"][gesture_id].update(updates)
            return self.save_current_config()
        return False
    
    def toggle_gesture_enabled(self, gesture_id):
        """Geste aktivieren/deaktivieren (Builtin)"""
        gesture = self.get_gesture_info(gesture_id)
        if gesture:
            current_enabled = gesture.get("enabled", 0)
            new_enabled = 0 if current_enabled == 1 else 1
            return self.update_gesture(gesture_id, {"enabled": new_enabled})
        return False
    
    def is_gesture_enabled(self, gesture_id):
        """Prüfen, ob die Geste aktiv ist"""
        gesture = self.get_gesture_info(gesture_id)
        return gesture.get("enabled", 0) == 1 if gesture else False
    
    def factory_reset(self, option="all"):
        """Auf Werkseinstellungen zuruecksetzen"""
        if option == "all":
            # KOMPLETTER RESET
            self.gesture_config = self.factory_config.copy()
            success = self.save_current_config()
            
            # gesture_roles.json entfernen
            if os.path.exists("gesture_roles.json"):
                os.remove("gesture_roles.json")
            
            # custom_gestures.json entfernen
            if os.path.exists("custom_gestures.json"):
                os.remove("custom_gestures.json")
            
            if success:
                return True, "Werkseinstellungen komplett wiederhergestellt!"
            return False, "Fehler beim Speichern"
        
        elif option == "enable":
            # NUR ENABLE
            gestures = self.gesture_config.get("gestures", {})
            for gesture_id, info in gestures.items():
                if info.get("gesture_type") == "builtin":
                    self.gesture_config["gestures"][gesture_id]["enabled"] = 1
            
            success = self.save_current_config()
            if success:
                return True, "Alle Fabrik-Gesten aktiviert!"
            return False, "Fehler beim Speichern"
        
        elif option == "roles":
            # NUR ROLLEN RESET
            factory_gestures = self.factory_config.get("gestures", {})
            for gesture_id, info in self.gesture_config.get("gestures", {}).items():
                if gesture_id in factory_gestures:
                    self.gesture_config["gestures"][gesture_id]["roles"] = \
                        factory_gestures[gesture_id].get("roles", [])
            
            success = self.save_current_config()
            if success:
                return True, "Rollen zurückgesetzt!"
            return False, "Fehler beim Speichern"
        
        return False, "Ungültige Option"
    
    # ===== CUSTOM GESTURE YÖNETİMİ =====
    
    def get_custom_gesture_roles(self, gesture_name):
        """Rollen für Custom-Gesten abrufen"""
        if os.path.exists("gesture_roles.json"):
            try:
                with open("gesture_roles.json", "r") as f:
                    roles_data = json.load(f)
                    return roles_data.get(gesture_name, ['admin', 'ingenieur', 'operator'])
            except:
                return ['admin', 'ingenieur', 'operator']
        return ['admin', 'ingenieur', 'operator']
    
    def save_custom_gesture_roles(self, gesture_name, roles):
        """Rollen für Custom-Gesten abrufen"""
        roles_data = {}
        if os.path.exists("gesture_roles.json"):
            try:
                with open("gesture_roles.json", "r") as f:
                    roles_data = json.load(f)
            except:
                pass
        
        roles_data[gesture_name] = roles
        
        try:
            with open("gesture_roles.json", "w") as f:
                json.dump(roles_data, f, indent=2)
            return True
        except:
            return False
    
    def delete_custom_gesture_roles(self, gesture_name):
        """Rollen für Custom-Gesten löschen"""
        if os.path.exists("gesture_roles.json"):
            try:
                with open("gesture_roles.json", "r") as f:
                    roles_data = json.load(f)
                
                if gesture_name in roles_data:
                    del roles_data[gesture_name]
                
                with open("gesture_roles.json", "w") as f:
                    json.dump(roles_data, f, indent=2)
                return True
            except:
                return False
        return True
    
    def get_custom_gesture_info(self, gesture_name):
        """Informationen über Custom-Geste abrufen"""
        if os.path.exists("custom_gestures.json"):
            try:
                with open("custom_gestures.json", "r", encoding="utf-8") as f:
                    custom_data = json.load(f)
                    if gesture_name in custom_data:
                        return custom_data[gesture_name]
            except:
                pass
        
        # Standardwerte zurückgeben
        return {
            "display_name": gesture_name,
            "action_text": f"Geste: {gesture_name}",
            "channel": "CH1",
            "gpio_pin": 5,
            "roles": self.get_custom_gesture_roles(gesture_name)
        }
    
    def save_custom_gesture_info(self, gesture_name, info):
        """Informationen ueber Custom-Geste speichern"""
        custom_data = {}
        if os.path.exists("custom_gestures.json"):
            try:
                with open("custom_gestures.json", "r", encoding="utf-8") as f:
                    custom_data = json.load(f)
            except:
                pass
        
        custom_data[gesture_name] = info
        
        try:
            with open("custom_gestures.json", "w", encoding="utf-8") as f:
                json.dump(custom_data, f, indent=2, ensure_ascii=False)
            
            # Rollen ebenfalls speichern
            self.save_custom_gesture_roles(gesture_name, info.get("roles", []))
            return True
        except Exception as e:
            print(f"[ERROR] custom_gestures.json konnte nicht gespeichert werden: {e}")
            return False
    
    def delete_custom_gesture_info(self, gesture_name):
        """Informationen über Custom-Geste löschen"""
        if os.path.exists("custom_gestures.json"):
            try:
                with open("custom_gestures.json", "r", encoding="utf-8") as f:
                    custom_data = json.load(f)
                
                if gesture_name in custom_data:
                    del custom_data[gesture_name]
                
                with open("custom_gestures.json", "w", encoding="utf-8") as f:
                    json.dump(custom_data, f, indent=2, ensure_ascii=False)
            except:
                pass
        
        # Rollen ebenfalls loeschen
        self.delete_custom_gesture_roles(gesture_name)
