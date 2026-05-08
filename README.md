# is-real-arcade-bomber

## 🧩 Intro
A 3D arcade bomber game where you pilot a B-2 Spirit stealth bomber over a Tel-Aviv, Israel. Drop bombs on targets, collect power-ups, and survive enemy air defences.

---

## 📖 Description
is-real-arcade-bomber is a Python-based 3D game built with OpenGL, inspired by War Thunder for academic purposes. You fly a stealth bomber over a city rendered in real-time, choosing your targets carefully — destroy buildings for points, but avoid hospitals or face a score penalty. As your score climbs, enemy air defences spawn and shoot back. Collect repair and upgrade tokens to stay alive and extend your bomb loadout.

### 🔹 What you can do:
- Pilot a B-2 Spirit bomber in full 3D flight
- Drop bombs on buildings, military bases, and city blocks
- Toggle **bomber scope** for a top-down precision targeting view
- Mouse-wheel zoom in third-person chase camera view
- Survive **enemy ground-to-air defence turrets** that get more aggressive over time
- Collect **green repair tokens** to restore health mid-flight
- Collect **blue upgrade tokens** to expand your bomb capacity
- Watch out for hospitals — hitting one triggers a **score penalty and a red warning**

---

## 🛠️ Tech Stack
- Python
- PyOpenGL (OpenGL, GLU, GLUT)
- PyOpenGL-accelerate

---

## ⚙️ Installation & Usage

### 🔹 Step 1: Clone the repository
```bash
git clone https://github.com/Sakif16/is-real-arcade-bomber.git
```

### 🔹 Step 2: Enter directory
```bash
cd is-real-arcade-bomber
```

### 🔹 Step 3: Install system-level OpenGL/GLUT (Linux only)
- **Windows**: Nothing extra needed — PyOpenGL bundles freeglut.
- **macOS**: Nothing extra needed — GLUT is built in.
- **Linux**:
```bash
sudo apt install freeglut3-dev
```

### 🔹 Step 4: Install the dependencies
```bash
pip install -r requirements.txt
```

### 🔹 Step 5: Run the game
```bash
python bomber.py
```

---

## 🎮 Controls

| Key | Action |
|-----|--------|
| A / D | Steer left / right |
| W | Decrease altitude |
| S | Increase altitude |
| Left Shift | Increase speed (hold) |
| Left Ctrl | Decrease speed (hold) |
| Space | Drop bomb |
| B | Toggle bomber scope (top-down view) |
| Mouse Wheel | Zoom in/out (third-person view) |
| Enter | Advance through title / monologue screen |
| R | Restart after game over |
| Q | Quit |

---

## 🏆 Scoring

| Target | Points |
|--------|--------|
| Tall building | +20 |
| Medium building | +10 |
| Military base | +50 |
| Hospital | -30 ⚠️ |

---

## 💊 Power-ups

| Token | Effect | Spawn Rate |
|-------|--------|------------|
| 🟢 Green (Repair) | +10 health (max 100) | Every 60 seconds |
| 🔵 Blue (Upgrade) | +5 bomb capacity | Every 60 seconds |

---

## ⚠️ Known Issues
- Mouse-wheel zoom may not work on all GLUT builds (handled gracefully with a fallback)
- Modifier keys (Shift / Ctrl) rely on Windows API for best accuracy — behaviour may differ on Linux/macOS
- No audio or sound effects
- GLUT window cannot be resized after launch
- Limited testing on Linux and macOS environments

---

## 🚀 Future Development
- Cross-platform modifier key support (Linux & macOS parity)
- Sound effects and background music
- Multiple city maps / biomes
- Moving enemy aircraft that intercept the bomber
- Difficulty levels (easy / normal / hard)
- High-score leaderboard saved to disk
- Resizable window and fullscreen toggle
- Improved explosion and particle effects
- Minimap HUD overlay
- Packaging as a standalone executable (no Python install needed)

---

## 🤝 Contributions
Contributions are welcome!

### You can contribute by:
- Reporting bugs or issues
- Suggesting new features or improvements
- Refactoring code for better performance or readability
- Improving game mechanics, controls, or difficulty balance
- Enhancing documentation

### How to contribute:

### 1) Fork the repository

### 2) Clone your fork
```bash
git clone https://github.com/YOUR_USERNAME/is-real-arcade-bomber.git
```

### 3) Create a new branch
```bash
git checkout -b feature-name
```

### 4) Make your changes and commit
```bash
git commit -m "Add: your feature description"
```

### 5) Push to your fork
```bash
git push origin feature-name
```

### 6) Open a Pull Request on GitHub
