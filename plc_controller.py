# plc_controller.py - PLC/PROFINET Controller (GPIO'ya alternatif/ek)

"""
PLC Controller - PROFINET über Snap7
FEATURES:
- Merker (M) ve Data Block (DB) Unterstützung
- Verbindungsstatus-Prüfung
- Thread-safe Operationen
- Kein Crash bei Verbindungsproblemen
- PULSE/SET/RESET/TOGGLE/ANALOG Modi
"""

import snap7
from snap7.util import *
from snap7.type import Areas
import threading
import time
import json
import os

IS_SNAP7_AVAILABLE = True
try:
    import snap7
except ImportError:
    IS_SNAP7_AVAILABLE = False
    print("[PLC] snap7 nicht installiert. PLC-Modus deaktiviert.")

class PLCController:
    def __init__(self, ip="192.168.1.1", rack=0, slot=1, duration=10):
        """
        Args:
            ip: PLC IP-Adresse
            rack: Rack-Nummer (Standard: 0)
            slot: Slot-Nummer (Standard: 1)
            duration: Aktivierungsdauer in Sekunden (für PULSE-Modus)
        """
        self.ip = ip
        self.rack = rack
        self.slot = slot
        self.duration = duration
        self.client = None
        self.connected = False
        self.plc_mappings = {}  # gesture_id/name -> {"address": "M0.0", "mode": "PULSE", "analog_value": 100}
        
        if IS_SNAP7_AVAILABLE:
            self.client = snap7.client.Client()
        
        # Config laden
        self.load_plc_config()
    
    def load_plc_config(self):
        """PLC-Zuordnungen aus plc_config.json laden"""
        if os.path.exists("plc_config.json"):
            try:
                with open("plc_config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.ip = config.get("ip", self.ip)
                    self.rack = config.get("rack", self.rack)
                    self.slot = config.get("slot", self.slot)
                    self.plc_mappings = config.get("mappings", {})
                    
                    # Eski format kontrolü (backward compatibility)
                    for gesture_id, mapping in self.plc_mappings.items():
                        if isinstance(mapping, str):
                            # Eski format: "M0.0"
                            self.plc_mappings[gesture_id] = {
                                "address": mapping,
                                "mode": "PULSE"
                            }
                    
                    print(f"[PLC] Config geladen: {len(self.plc_mappings)} Zuordnungen")
            except Exception as e:
                print(f"[PLC] Config-Fehler: {e}")
    
    def save_plc_config(self):
        """PLC-Config speichern"""
        try:
            config = {
                "ip": self.ip,
                "rack": self.rack,
                "slot": self.slot,
                "mappings": self.plc_mappings
            }
            with open("plc_config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[PLC] Speicherfehler: {e}")
            return False
    
    def connect(self):
        """PLC-Verbindung herstellen"""
        if not IS_SNAP7_AVAILABLE:
            print("[PLC] snap7 nicht verfügbar")
            return False
        
        try:
            self.client.connect(self.ip, self.rack, self.slot)
            self.connected = True
            print(f"[PLC] ✓ Verbunden: {self.ip}")
            return True
        except Exception as e:
            self.connected = False
            print(f"[PLC] ✗ Verbindungsfehler: {e}")
            return False
    
    def disconnect(self):
        """PLC-Verbindung trennen"""
        if self.client and self.connected:
            try:
                self.client.disconnect()
                self.connected = False
                print("[PLC] Verbindung getrennt")
            except:
                pass
    
    def test_connection(self):
        """Verbindung testen"""
        if self.connect():
            self.disconnect()
            return True
        return False
    
    def parse_address(self, address_str):
        """
        PLC-Adresse parsen
        Unterstützte Formate:
        - M0.0, M1.5, M10.7 (Merker)
        - DB1.DBX0.0, DB5.DBX10.3 (Data Block Bit)
        - DB1.DBD0, DB5.DBW10 (Data Block Word/DWord)
        
        Returns:
            (area, db_number, byte_offset, bit_offset, data_type)
        """
        address_str = address_str.strip().upper()
        
        # Merker: M0.0
        if address_str.startswith("M"):
            parts = address_str[1:].split(".")
            if len(parts) == 2:
                byte_offset = int(parts[0])
                bit_offset = int(parts[1])
                return ("M", None, byte_offset, bit_offset, "BOOL")
        
        # Data Block: DB1.DBX0.0 oder DB1.DBD0
        elif address_str.startswith("DB"):
            # DB-Nummer extrahieren
            db_part = address_str.split(".")[0]
            db_number = int(db_part[2:])
            
            # Rest analysieren
            rest = address_str[len(db_part)+1:]
            
            if rest.startswith("DBX"):
                # Bit: DB1.DBX0.0
                rest = rest[3:]
                parts = rest.split(".")
                if len(parts) == 2:
                    byte_offset = int(parts[0])
                    bit_offset = int(parts[1])
                    return ("DB", db_number, byte_offset, bit_offset, "BOOL")
            
            elif rest.startswith("DBD"):
                # DWord: DB1.DBD0
                byte_offset = int(rest[3:])
                return ("DB", db_number, byte_offset, 0, "DWORD")
            
            elif rest.startswith("DBW"):
                # Word: DB1.DBW0
                byte_offset = int(rest[3:])
                return ("DB", db_number, byte_offset, 0, "WORD")
        
        return None
    
    def write_plc(self, address_str, value=True):
        """
        PLC-Adresse schreiben
        Args:
            address_str: z.B. "M0.0", "DB1.DBX0.0"
            value: True/False für Bool, Zahl für Word/DWord
        """
        if not self.connected:
            print("[PLC] ⚠ Nicht verbunden - Übersprungen")
            return False
        
        parsed = self.parse_address(address_str)
        if not parsed:
            print(f"[PLC] ✗ Ungültige Adresse: {address_str}")
            return False
        
        area_type, db_number, byte_offset, bit_offset, data_type = parsed
        
        try:
            if area_type == "M":
                # Merker schreiben
                data = self.client.read_area(Areas.MK, 0, byte_offset, 1)
                set_bool(data, 0, bit_offset, value)
                self.client.write_area(Areas.MK, 0, byte_offset, data)
                print(f"[PLC] ✓ M{byte_offset}.{bit_offset} = {value}")
                
            elif area_type == "DB":
                if data_type == "BOOL":
                    # DB Bit schreiben
                    data = self.client.db_read(db_number, byte_offset, 1)
                    set_bool(data, 0, bit_offset, value)
                    self.client.db_write(db_number, byte_offset, data)
                    print(f"[PLC] ✓ DB{db_number}.DBX{byte_offset}.{bit_offset} = {value}")
                
                elif data_type == "WORD":
                    # Word schreiben
                    data = bytearray(2)
                    set_int(data, 0, int(value))
                    self.client.db_write(db_number, byte_offset, data)
                    print(f"[PLC] ✓ DB{db_number}.DBW{byte_offset} = {value}")
                
                elif data_type == "DWORD":
                    # DWord schreiben
                    data = bytearray(4)
                    set_dword(data, 0, int(value))
                    self.client.db_write(db_number, byte_offset, data)
                    print(f"[PLC] ✓ DB{db_number}.DBD{byte_offset} = {value}")
            
            return True
            
        except Exception as e:
            print(f"[PLC] ✗ Schreibfehler bei {address_str}: {e}")
            return False
    
    def read_plc_bool(self, address_str):
        """PLC Boolean-Wert lesen"""
        if not self.connected:
            return False
        
        parsed = self.parse_address(address_str)
        if not parsed:
            return False
        
        area_type, db_number, byte_offset, bit_offset, data_type = parsed
        
        try:
            if area_type == "M":
                data = self.client.read_area(Areas.MK, 0, byte_offset, 1)
                return get_bool(data, 0, bit_offset)
            elif area_type == "DB" and data_type == "BOOL":
                data = self.client.db_read(db_number, byte_offset, 1)
                return get_bool(data, 0, bit_offset)
        except:
            return False
        
        return False
    
    def write_plc_with_mode(self, address_str, mode="PULSE", analog_value=None):
        """
        PLC-Adresse mit Modus schreiben
        Args:
            address_str: z.B. "M0.0", "DB1.DBX0.0", "DB1.DBW0"
            mode: "PULSE", "SET", "RESET", "TOGGLE", "ANALOG"
            analog_value: Wert für ANALOG-Modus (z.B. 100, 1500)
        """
        if not self.connected:
            print("[PLC] ⚠ Nicht verbunden - Übersprungen")
            return False
        
        parsed = self.parse_address(address_str)
        if not parsed:
            print(f"[PLC] ✗ Ungültige Adresse: {address_str}")
            return False
        
        area_type, db_number, byte_offset, bit_offset, data_type = parsed
        
        try:
            if mode == "ANALOG":
                # ✅ ANALOG Modus - Word/DWord schreiben
                if data_type not in ["WORD", "DWORD"]:
                    print(f"[PLC] ✗ ANALOG nur für DBW/DBD möglich, nicht für Bit-Adressen!")
                    return False
                
                if analog_value is None:
                    print(f"[PLC] ✗ ANALOG-Modus benötigt einen Wert!")
                    return False
                
                print(f"[PLC] ANALOG {address_str} = {analog_value}")
                return self.write_plc(address_str, analog_value)
            
            # Für BOOL-Operationen
            if data_type != "BOOL":
                print(f"[PLC] ✗ {mode}-Modus nur für Bit-Adressen (M0.0, DBX) möglich!")
                return False
            
            if mode == "TOGGLE":
                current_value = self.read_plc_bool(address_str)
                new_value = not current_value
                print(f"[PLC] TOGGLE {address_str}: {current_value} → {new_value}")
                return self.write_plc(address_str, new_value)
            
            elif mode == "SET":
                print(f"[PLC] SET {address_str} = TRUE (dauerhaft)")
                return self.write_plc(address_str, True)
            
            elif mode == "RESET":
                print(f"[PLC] RESET {address_str} = FALSE (dauerhaft)")
                return self.write_plc(address_str, False)
            
            elif mode == "PULSE":
                success = self.write_plc(address_str, True)
                if success:
                    print(f"[PLC] PULSE {address_str} = TRUE ({self.duration}s)")
                    timer_thread = threading.Thread(target=self._deactivate_output, args=(address_str,))
                    timer_thread.daemon = True
                    timer_thread.start()
                return success
            
            return False
            
        except Exception as e:
            print(f"[PLC] ✗ Schreibfehler bei {address_str}: {e}")
            return False
    
    def _deactivate_output(self, address_str):
        """Timer: Adresse nach duration zurücksetzen"""
        time.sleep(self.duration)
        if self.connected:
            self.write_plc(address_str, False)
            print(f"[PLC] {address_str} AUSGESCHALTET (nach {self.duration}s)")
    
    def activate_action(self, gesture_identifier):
        """
        Geste-basierte PLC-Aktivierung
        Args:
            gesture_identifier: Builtin gesture_id oder custom name
        """
        if not self.connected:
            print(f"[PLC] ⚠ PROFINET NICHT AKTIV - '{gesture_identifier}' übersprungen")
            return
        
        mapping = self.plc_mappings.get(gesture_identifier)
        if not mapping:
            print(f"[PLC] ⚠ Keine PLC-Zuordnung für '{gesture_identifier}'")
            return
        
        plc_address = mapping.get("address", "")
        plc_mode = mapping.get("mode", "PULSE")
        analog_value = mapping.get("analog_value", None)
        
        if not plc_address:
            print(f"[PLC] ⚠ Leere Adresse für '{gesture_identifier}'")
            return
        
        print(f"[PLC] '{gesture_identifier}' → {plc_address} ({plc_mode})")
        
        # ANALOG değer varsa gönder
        if plc_mode == "ANALOG" and analog_value is not None:
            self.write_plc_with_mode(plc_address, plc_mode, analog_value)
        else:
            self.write_plc_with_mode(plc_address, plc_mode)
    
    def update_mapping(self, gesture_identifier, plc_address, plc_mode="PULSE", analog_value=None):
        """Gesture -> PLC Zuordnung aktualisieren"""
        if plc_address and plc_address.strip():
            mapping_data = {
                "address": plc_address.strip().upper(),
                "mode": plc_mode
            }
            
            # ANALOG değer varsa ekle
            if plc_mode == "ANALOG" and analog_value is not None:
                mapping_data["analog_value"] = analog_value
            
            self.plc_mappings[gesture_identifier] = mapping_data
        elif gesture_identifier in self.plc_mappings:
            del self.plc_mappings[gesture_identifier]
        
        self.save_plc_config()
    
    def get_mapping(self, gesture_identifier):
        """Gesture -> PLC Zuordnung abrufen"""
        mapping = self.plc_mappings.get(gesture_identifier, {})
        if isinstance(mapping, str):
            # Eski format
            return mapping, "PULSE", None
        
        address = mapping.get("address", "")
        mode = mapping.get("mode", "PULSE")
        analog_value = mapping.get("analog_value", None)
        
        return address, mode, analog_value
    
    def cleanup(self):
        """Ressourcen freigeben"""
        self.disconnect()

# Globale Instanz (Optional)
_plc_instance = None

def get_plc_controller():
    """Singleton: PLC Controller abrufen"""
    global _plc_instance
    if _plc_instance is None:
        _plc_instance = PLCController()
    return _plc_instance
