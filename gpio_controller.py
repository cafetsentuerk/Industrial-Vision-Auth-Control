# gpio_controller.py - GPIO Zero + Config Support (Pi 5 Uyumlu)

"""
GPIO Controller - GPIO Zero ile Channel-Based Control

ÖZELLİKLER:
✅ GPIO Zero kullanımı (Pi 5 uyumlu)
✅ gesture_config.json otomatik okuma
✅ custom_gestures.json desteği
✅ Runtime reload_pins() desteği
✅ Thread-safe pin kontrolü
"""

import time
import threading
import json
import os

try:
    from gpiozero import OutputDevice, Device
    IS_RPI = True
except ImportError:
    IS_RPI = False
    print("[GPIO] gpiozero kütüphanesi bulunamadı. Simülasyon modu aktif.")

class GpioController:
    def __init__(self, action_pins=None, duration=10, auto_load=True):
        """
        Args:
            action_pins: Manuel pin haritası (opsiyonel) - örn: {"CH5": 19, "CH6": 20}
            duration: Pin aktif kalma süresi (saniye)
            auto_load: True ise gesture_config.json'dan otomatik yükler
        """
        self.duration = duration
        self.pins = {}  # channel -> pin number
        self._output_devices = {}  # channel -> OutputDevice
        
        if action_pins:
            # Manuel harita varsa kullan
            self.pins = action_pins
        elif auto_load:
            # Otomatik config'den yükle
            self._load_pins_from_config()
        
        # GPIO başlatma
        if IS_RPI and self.pins:
            self._initialize_pins()
    
    def _load_pins_from_config(self):
        """Config dosyalarından channel->pin haritasını yükle"""
        print("[GPIO] Pin haritası config'den yükleniyor...")
        self.pins = self._build_channel_pin_map()
        print(f"[GPIO] {len(self.pins)} kanal yüklendi.")
    
    def _build_channel_pin_map(self):
        """
        gesture_config.json ve custom_gestures.json'dan channel->pin haritası oluştur
        
        Returns:
            {"CH5": 19, "CH6": 20, "CH7": 21, "CH8": 26, ...}
        """
        pin_map = {}
        
        # 1. Builtin gesture'lar (gesture_config.json)
        if os.path.exists("gesture_config.json"):
            try:
                with open("gesture_config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                    gestures = config.get("gestures", {})
                    
                    for gesture_id, info in gestures.items():
                        if info.get("enabled", 0) == 1:  # Sadece aktif olanlar
                            channel = info.get("channel")
                            gpio_pin = info.get("gpio_pin")
                            
                            if channel and gpio_pin is not None and gpio_pin > 0:
                                pin_map[channel] = gpio_pin
                                print(f" ✓ Builtin '{gesture_id}': {channel} = GPIO {gpio_pin}")
            except Exception as e:
                print(f"[GPIO] gesture_config.json okunamadı: {e}")
        
        # 2. Custom gesture'lar (custom_gestures.json)
        if os.path.exists("custom_gestures.json"):
            try:
                with open("custom_gestures.json", "r", encoding="utf-8") as f:
                    custom_gestures = json.load(f)
                    
                    for gesture_name, info in custom_gestures.items():
                        channel = info.get("channel")
                        gpio_pin = info.get("gpio_pin")
                        
                        if channel and gpio_pin is not None and gpio_pin > 0:
                            # Aynı channel zaten varsa üzerine yazma (builtin öncelikli)
                            if channel not in pin_map:
                                pin_map[channel] = gpio_pin
                                print(f" ✓ Custom '{gesture_name}': {channel} = GPIO {gpio_pin}")
            except Exception as e:
                print(f"[GPIO] custom_gestures.json okunamadı: {e}")
        
        return pin_map
    
    def _initialize_pins(self):
        """GPIO pinlerini OutputDevice olarak başlat"""
        for channel, pin in self.pins.items():
            try:
                self._output_devices[channel] = OutputDevice(
                    pin=pin, 
                    active_high=True, 
                    initial_value=False
                )
                self._output_devices[channel].off()
                print(f"[GPIO] {channel} -> Pin {pin} eingerichtet (AUS)")
            except Exception as e:
                print(f"[GPIO] WARNUNG: {channel} (Pin {pin}) başlatılamadı: {e}")
    
    def reload_pins(self):
        """
        ✅ Config dosyalarından channel->pin haritasını yeniden yükle
        """
        print("[GPIO] Pin haritası yenileniyor...")
        
        # Eski cihazları temizle
        self._cleanup_devices()
        
        # Yeni haritayı yükle
        self._load_pins_from_config()
        
        # Yeni pinleri başlat
        if IS_RPI and self.pins:
            self._initialize_pins()
        
        print(f"[GPIO] {len(self.pins)} kanal hazır.")
    
    def _cleanup_devices(self):
        """Mevcut GPIO cihazlarını kapat"""
        for channel, device in self._output_devices.items():
            try:
                if device:
                    device.off()
                    device.close()
            except:
                pass
        self._output_devices.clear()
    
    def _deactivate_output(self, channel: str):
        """Belirtilen süre sonra pini kapat"""
        time.sleep(self.duration)
        device = self._output_devices.get(channel)
        
        if device and device.is_active:
            device.off()
            pin_num = self.pins.get(channel, "?")
            print(f"[GPIO] {channel} (Pin {pin_num}) AUSGESCHALTET.")
    
    def activate_action(self, channel):
        """
        Channel'a göre GPIO'yu aktive et
        
        Args:
            channel: Kanal adı (örn: "CH5", "CH7")
        """
        # Channel string ise upper yap
        if isinstance(channel, str):
            channel = channel.upper()
        
        if not IS_RPI:
            print(f"[GPIO-SIM] {channel} tetiklendi (simülasyon)")
            return
        
        device = self._output_devices.get(channel)
        
        if not device:
            print(f"[GPIO] WARNUNG: Kanal '{channel}' tanımlı değil.")
            return
        
        # Zaten aktifse tekrar tetikleme
        if device.is_active:
            print(f"[GPIO] {channel} zaten aktif.")
            return
        
        # Önce hepsini kapat (Güvenlik)
        for ch, dev in self._output_devices.items():
            if dev.is_active:
                dev.off()
        
        # İlgili pini aç
        device.on()
        pin_num = self.pins.get(channel, "?")
        print(f"[GPIO] {channel} (Pin {pin_num}) EINGESCHALTET ({self.duration} Sekunden)")
        
        # Otomatik kapanma thread'i
        timer_thread = threading.Thread(target=self._deactivate_output, args=(channel,))
        timer_thread.daemon = True
        timer_thread.start()
    
    def get_channel_for_gesture(self, gesture_identifier):
        """
        ✅ Gesture ID veya name'den channel'ı bul
        
        Args:
            gesture_identifier: Builtin gesture_id (örn: "open") veya custom name (örn: "Daumen_hoch")
        
        Returns:
            channel (str) veya None
        """
        # 1. Builtin gesture kontrolü
        if os.path.exists("gesture_config.json"):
            try:
                with open("gesture_config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                    gestures = config.get("gestures", {})
                    
                    if gesture_identifier in gestures:
                        info = gestures[gesture_identifier]
                        if info.get("enabled", 0) == 1:
                            return info.get("channel")
            except:
                pass
        
        # 2. Custom gesture kontrolü
        if os.path.exists("custom_gestures.json"):
            try:
                with open("custom_gestures.json", "r", encoding="utf-8") as f:
                    custom_gestures = json.load(f)
                    
                    if gesture_identifier in custom_gestures:
                        return custom_gestures[gesture_identifier].get("channel")
            except:
                pass
        
        return None
    
    def cleanup(self):
        """GPIO temizliği"""
        if IS_RPI:
            print("[GPIO] Temizlik başlatılıyor...")
            self._cleanup_devices()
            print("[GPIO] Temizlik tamamlandı.")
    
    def __del__(self):
        self.cleanup()
