$readmeContent = @"
# Industrial Vision Auth & Control System (M.Sc. Thesis)

This repository contains the complete source code for my Master of Science thesis in **Ingenieurinformatik** at **Jade Hochschule**. The project introduces a high-security, vision-based Human-Machine Interface (HMI) designed for safety-critical industrial production environments.

##  Project Vision
The system replaces traditional physical control elements with an intelligent optical interface. By combining **Biometric Face Recognition** for authentication and **Hand Gesture Recognition** for machine control, it ensures a touchless, ergonomic, and secure interaction between humans and industrial machines (PLCs).

##  Key Technical Features

### 1. 14-Stage Industrial Safety Pipeline (`hand_tracking.py`)
To meet rigorous industrial safety standards, a **14-stage validation logic** is implemented to prevent accidental or malicious triggers:
- **Anthropometric Plausibility:** Verifies the 3D anatomical chain (Shoulder -> Elbow -> Wrist) to ensure the detected hand belongs to the authenticated operator.
- **Shoulder-Height Control:** Active monitoring of posture to ensure the operator is in a safe standing/working position.
- **Dynamic Spatial Awareness:** Real-time distance calculation between face and hand landmarks to verify intentionality.
- **Anti-Manipulation:** Immediate system lockout if multiple persons or unauthorized "ghost" hands are detected in the FOV.

### 2. Biometric Authentication & RBAC (`face_identity_v2.py`)
- **Role-Based Access Control (RBAC):** Integrated permission matrix for **Admin**, **Engineer**, and **Operator** roles.
- **Identity Verification:** High-precision face identification determines which gestures are unlocked (e.g., only an Admin can trigger a 'System Reset').

### 3. Hybrid Machine Learning Gesture Engine (`gesture_engine.py`)
- **Dual Recognition:** Uses MediaPipe for rule-based gestures and a **KNN (K-Nearest Neighbors)** classifier for custom, user-trained gestures.
- **42-Dimensional Analysis:** Processes 21 landmarks across X/Y coordinates for high-accuracy gesture classification.

### 4. Industrial Protocol & Hardware Integration
- **Siemens S7 Integration (`plc_controller.py`):** Native communication via **Snap7** supporting Pulse, Set/Reset, Toggle, and Analog (DB writing) modes.
- **GPIO Control (`gpio_controller.py`):** Direct hardware interaction optimized for Raspberry Pi 5.

##  Tech Stack
- **AI/CV:** MediaPipe, OpenCV, Scikit-learn (KNN)
- **Industrial:** Snap7 (S7 Communication), GPIO Zero
- **Frontend:** PyQt/Tkinter (Optimized for 5" Portrait Displays)
- **Performance:** Custom Analytics Logger (FPS, Latency, CPU/RAM Metrics)

##  Repository Structure
- `app_v2.py`: The "Central Brain" - integrates vision pipeline with safety logic and PLC commands.
- `main.py`: User registration, face databank management, and system entry.
- `gesture_training_gui.py`: Professional tool for training and updating the KNN gesture model.
- `analytics_viewer_gui.py`: Visualization tool for system health and performance auditing.

---
**Author:** Cafet Sentürk  
**Academic Institution:** Jade Hochschule (Jade University of Applied Sciences) in Wilhelmshaven  
**Supervisors:** Prof. Dr.-Ing. Jochen Radmer & Prof. Dr.-Ing. Nick Rüssmeier  
**Degree:** Master of Science - Ingenieurinformatik(Computer Science in Engineering) (2026)
"@
$readmeContent | Out-File -FilePath README.md -Encoding utf8