# final.py  (updated)
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import random
import math

# -------------------------------
# Minimal, safe addition: OS key polling on Windows for modifiers
# -------------------------------
HAS_WIN_KBD = False
VK_LSHIFT = 0xA0
VK_LCONTROL = 0xA2
def _is_vk_down(_vk): return False  # default no-op
try:
    import ctypes
    _user32 = ctypes.WinDLL('user32', use_last_error=True)
    def _is_vk_down(vk):
        return (_user32.GetAsyncKeyState(vk) & 0x8000) != 0
    HAS_WIN_KBD = True
except Exception:
    HAS_WIN_KBD = False  # non-Windows keeps existing behavior

# -------------------------------
# City configuration
# -------------------------------
CITY_SIZE = 800  # Larger city area
BLOCK_SIZE = 40  # Size of each city block
STREET_WIDTH = 8  # Width of streets between blocks
BULLET_SPEED = 20.0
BULLET_GRAVITY = -0.05  # Re-introducing gravity for the bombs

# ---- NEW: special-building frequency + palette (city map only) ----
SPECIAL_RATE = 12  # ~1/12 hospital and ~1/12 military base (low count vs others)

OLIVE = (0.36, 0.42, 0.25)
OLIVE_DARK = (0.28, 0.33, 0.20)
HOSPITAL_BLUE = (0.60, 0.80, 0.95)
HOSPITAL_RED = (0.80, 0.00, 0.00)

# Aircraft configuration
aircraft_x = 0.0
aircraft_y = 220.0  # Much higher altitude by default
aircraft_z = 0.0
aircraft_speed = 1.0
aircraft_heading = 0.0
aircraft_turn_rate = 0.0
min_speed = 0.8
max_speed = 8.0
aircraft_velocity_x = 0.0
aircraft_velocity_z = 0.0

# --- NEW: Z-axis (altitude) movement ---
aircraft_altitude_speed = 1.5
min_altitude = 20.0  # Minimum safe altitude to avoid instant crash
max_altitude = 500.0

# Movement smoothing parameters
turn_acceleration = 4.0
turn_deceleration = 8.0
max_turn_rate = 2.5
speed_acceleration = 2.0
movement_smoothing = 0.12

# --- NEW: Game State & Health ---
game_over = False
bomber_health = 100
BOMBER_RADIUS = 17.0  # collision radius used for bullet/aircraft collisions
death_reason = 'none'  # 'none', 'building', 'defence'

# Input states
keys_pressed = {
    'a': False,
    'd': False,
    'w': False,  # W decreases altitude (user requested)
    's': False,  # S increases altitude (user requested)
    'shift': False,
    'ctrl': False,
    'space': False
}

# Timing
last_frame_time = 0.0
frame_dt = 0.0  # delta time for the last frame (seconds)

# -------------------------------
# Bomber scope parameters (added)
# -------------------------------
bomber_scope_enabled = False

default_fov = 60.0
topdown_fov = 12.0
current_fov = default_fov
zoom_rate = 6.0  # how fast we ease to target FOV (per second)

topdown_ahead_distance = 240.0  # how far ahead to center top-down view
topdown_eye_height = 600.0  # how high above that point to place camera

# -------------------------------
# NEW (feature): Third-person mouse-wheel zoom controls
# -------------------------------
# These affect ONLY the chase camera (bomber_scope disabled).
chase_cam_distance = 40.0
CHASE_CAM_MIN = 28.0
CHASE_CAM_MAX = 60.0
ZOOM_STEP = 2.0  # per wheel notch

# -------------------------------
# Bullet and Explosion configuration
# -------------------------------
BULLET_SIZE = 1.6  # smaller bomb visual size
# Increased defence projectile size (slightly larger for visibility)
DEFENCE_BULLET_SIZE = 1.0
EXPLOSION_LIFETIME = 50
EXPLOSION_SIZE_MAX = 18.0  # default max explosion sphere size
bullets_fired_count = 0

# Score
score = 0  # global score counter

# -------------------------------
# Bomb loadout & reload
# -------------------------------
DEFAULT_MAX_BOMBS = 5
MAX_BOMBS = DEFAULT_MAX_BOMBS
bombs_available = MAX_BOMBS
is_reloading = False
RELOAD_TIME_TOTAL = 15.0  # seconds
reload_time_remaining = 0.0

# Ground air-defence configuration
defences = []  # list of defence dicts
# spawn three defences per 30 points (handled in timer)
DEFENCE_SPAWN_SCORE_STEP = 30
# Make them shoot more frequently: shorter intervals
DEFENCE_SHOOT_INTERVAL_MIN = 0.25  # faster
DEFENCE_SHOOT_INTERVAL_MAX = 0.60
DEFENCE_BULLET_SPEED = 6.0
DEFENCE_CLEARANCE = 6.0  # minimal distance from building center when placing

# Global lists to manage active bullets and explosions
bullets = []
explosions = []

# Global list to store building data
buildings = []
buildings_generated = False

# -------------------------------
# NEW FEATURE: Repair Tokens
# -------------------------------
repair_tokens = []  # each: {'x','y','z','radius'}
REPAIR_SPAWN_INTERVAL = 60.0  # seconds
repair_spawn_accum = 0.0
REPAIR_TOKEN_RADIUS = 20.0       # pickup radius (generous)
REPAIR_TOKEN_VISUAL_SCALE = 16.0 # how big it looks
REPAIR_TOKEN_SPIN_DEG = 0.0

def spawn_repair_token():
    max_h = get_max_building_height()
    y = random.uniform(max_h + 30.0, max_altitude - 20.0)  # always above tallest building
    x = random.uniform(-CITY_SIZE / 2 + 30, CITY_SIZE / 2 - 30)
    z = random.uniform(-CITY_SIZE / 2 + 30, CITY_SIZE / 2 - 30)
    repair_tokens.append({
        'x': x, 'y': y, 'z': z,
        'radius': REPAIR_TOKEN_RADIUS
    })

def drawRepairToken(tok):
    """Bright, spinning green cross with a soft core sphere. Easy to see."""
    glPushMatrix()
    glTranslatef(tok['x'], tok['y'], tok['z'])
    glRotatef(REPAIR_TOKEN_SPIN_DEG, 0, 1, 0)

    # Glow-ish core
    glColor4f(0.2, 1.0, 0.2, 0.85)
    glutSolidSphere(REPAIR_TOKEN_VISUAL_SCALE * 0.35, 18, 18)

    # Plus sign: two perpendicular bars (thin cubes)
    glColor3f(0.1, 0.95, 0.1)
    # Vertical bar
    glPushMatrix()
    glScalef(REPAIR_TOKEN_VISUAL_SCALE * 0.30,
             REPAIR_TOKEN_VISUAL_SCALE * 1.20,
             REPAIR_TOKEN_VISUAL_SCALE * 0.30)
    glutSolidCube(1.0)
    glPopMatrix()
    # Horizontal bar
    glPushMatrix()
    glScalef(REPAIR_TOKEN_VISUAL_SCALE * 1.20,
             REPAIR_TOKEN_VISUAL_SCALE * 0.30,
             REPAIR_TOKEN_VISUAL_SCALE * 0.30)
    glutSolidCube(1.0)
    glPopMatrix()

    # Slim ring accent using scaled sphere hint (to avoid torus dependency)
    glColor4f(0.3, 1.0, 0.3, 0.6)
    glPushMatrix()
    glScalef(REPAIR_TOKEN_VISUAL_SCALE * 0.95,
             REPAIR_TOKEN_VISUAL_SCALE * 0.10,
             REPAIR_TOKEN_VISUAL_SCALE * 0.95)
    glutSolidSphere(0.8, 20, 16)
    glPopMatrix()

    glPopMatrix()

# -------------------------------
# NEW FEATURE: Upgrade Tokens (blue) - increases MAX_BOMBS by +5 when picked up
# -------------------------------
upgrade_tokens = []
UPGRADE_SPAWN_INTERVAL = REPAIR_SPAWN_INTERVAL
upgrade_spawn_accum = 0.0
UPGRADE_TOKEN_RADIUS = REPAIR_TOKEN_RADIUS
UPGRADE_TOKEN_VISUAL_SCALE = REPAIR_TOKEN_VISUAL_SCALE
UPGRADE_TOKEN_SPIN_DEG = 0.0

def spawn_upgrade_token():
    max_h = get_max_building_height()
    y = random.uniform(max_h + 30.0, max_altitude - 20.0)  # always above tallest building
    x = random.uniform(-CITY_SIZE / 2 + 30, CITY_SIZE / 2 - 30)
    z = random.uniform(-CITY_SIZE / 2 + 30, CITY_SIZE / 2 - 30)
    upgrade_tokens.append({
        'x': x, 'y': y, 'z': z,
        'radius': UPGRADE_TOKEN_RADIUS
    })
def drawUpgradeToken(tok):
    """Spinning blue upgrade token; visually similar to repair token but blue."""
    glPushMatrix()
    glTranslatef(tok['x'], tok['y'], tok['z'])
    glRotatef(UPGRADE_TOKEN_SPIN_DEG, 0, 1, 0)

    # Glow-ish core
    glColor4f(0.2, 0.45, 1.0, 0.95)
    glutSolidSphere(UPGRADE_TOKEN_VISUAL_SCALE * 0.38, 18, 18)

    # Up-arrow / bar design: vertical bar and arrow tip
    glColor3f(0.06, 0.36, 0.95)
    # Vertical bar
    glPushMatrix()
    glScalef(UPGRADE_TOKEN_VISUAL_SCALE * 0.25,
             UPGRADE_TOKEN_VISUAL_SCALE * 1.25,
             UPGRADE_TOKEN_VISUAL_SCALE * 0.25)
    glutSolidCube(1.0)
    glPopMatrix()
    # Arrow tip (cone)
    glPushMatrix()
    glTranslatef(0, UPGRADE_TOKEN_VISUAL_SCALE * 0.75, 0)
    glRotatef(-90, 1, 0, 0)
    glutSolidCone(UPGRADE_TOKEN_VISUAL_SCALE * 0.42, UPGRADE_TOKEN_VISUAL_SCALE * 0.6, 12, 8)
    glPopMatrix()

    # Slim ring accent
    glColor4f(0.25, 0.55, 1.0, 0.6)
    glPushMatrix()
    glScalef(UPGRADE_TOKEN_VISUAL_SCALE * 0.95,
             UPGRADE_TOKEN_VISUAL_SCALE * 0.10,
             UPGRADE_TOKEN_VISUAL_SCALE * 0.95)
    glutSolidSphere(0.8, 20, 16)
    glPopMatrix()

    glPopMatrix()

# -------------------------------
# NEW FEATURE: Repair/Hospital warning
# -------------------------------
HOSPITAL_WARNING_MESSAGE = "DON'T HIT HOSPITALS! WE'RE NOT ISRAELIS, YOU DUMMY!!"
HOSPITAL_WARNING_DURATION = 5.0
hospital_warning_time_remaining = 0.0

# -------------------------------
# NEW (feature): very small start menu (overlay)
# -------------------------------
game_state = "title"   # "title" → "monologue" → "playing"
game_started = False   # keep this (used internally)
WINDOW_W, WINDOW_H = 1200, 900
# Button rect in NDC (for easy drawing & hit-test conversion in mouse handler)
BTN_X0, BTN_X1 = -0.15, 0.15
BTN_Y0, BTN_Y1 = -0.06, 0.06

def start_game():

    global game_started, last_frame_time, repair_spawn_accum, upgrade_spawn_accum, hospital_warning_time_remaining
    game_started = True
    # Reset timing so dt does not spike at the first frame after menu
    last_frame_time = 0.0
    repair_spawn_accum = 0.0  # start counting for first token
    upgrade_spawn_accum = 0.0
    hospital_warning_time_remaining = 0.0


def drawTitleScreen():
    glPushAttrib(GL_ENABLE_BIT | GL_COLOR_BUFFER_BIT)
    glDisable(GL_DEPTH_TEST)

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    # -----------------------
    # Background (black)
    # -----------------------
    glColor3f(0.0, 0.0, 0.0)
    glBegin(GL_QUADS)
    glVertex2f(-1, -1)
    glVertex2f(1, -1)
    glVertex2f(1, 1)
    glVertex2f(-1, 1)
    glEnd()

    # -----------------------
    # Title Setup
    # -----------------------
    title = "Israel Arcade Bomber"
    font = GLUT_BITMAP_TIMES_ROMAN_24

    # Calculate pixel width of title
    total_width = 0
    for ch in title:
        total_width += glutBitmapWidth(font, ord(ch))

    # Convert to NDC (-1 to 1)
    start_x = - (total_width / WINDOW_W)

    y_pos = 0.1

    # -----------------------
    # Draw OUTLINE (yellow)
    # -----------------------
    glColor3f(1.0, 1.0, 0.0)

    offsets = [
        (-0.003, 0), (0.003, 0),
        (0, -0.003), (0, 0.003),
        (-0.003, -0.003), (0.003, 0.003),
        (-0.003, 0.003), (0.003, -0.003)
    ]

    for dx, dy in offsets:
        glRasterPos2f(start_x + dx, y_pos + dy)
        for ch in title:
            glutBitmapCharacter(font, ord(ch))

    # -----------------------
    # Draw MAIN TEXT (red)
    # -----------------------
    glColor3f(1.0, 0.0, 0.0)
    glRasterPos2f(start_x, y_pos)
    for ch in title:
        glutBitmapCharacter(font, ord(ch))

    # -----------------------
    # Subtitle (centered)
    # -----------------------
    subtitle = "Press ENTER to continue"
    font2 = GLUT_BITMAP_HELVETICA_18

    sub_width = 0
    for ch in subtitle:
        sub_width += glutBitmapWidth(font2, ord(ch))

    sub_x = - (sub_width / WINDOW_W)

    glColor3f(1, 1, 1)
    glRasterPos2f(sub_x, -0.15)
    for ch in subtitle:
        glutBitmapCharacter(font2, ord(ch))

    # -----------------------
    # Cleanup
    # -----------------------
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopAttrib()





def drawMonologueScreen():
    # Pure overlay, no side-effects on the 3D world
    glPushAttrib(GL_ENABLE_BIT | GL_COLOR_BUFFER_BIT | GL_LINE_BIT)
    glDisable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    # Dim background
    glColor4f(0.0, 0.0, 0.0, 0.25)
    glBegin(GL_QUADS)
    glVertex2f(-1.0, -1.0); glVertex2f( 1.0, -1.0)
    glVertex2f( 1.0,  1.0); glVertex2f(-1.0,  1.0)
    glEnd()

    # Title / description
    glColor3f(1.0, 1.0, 1.0)
    glRasterPos2f(-0.70, 0.40)
    for ch in "Mission: Bomb Israel": glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
    glRasterPos2f(-0.70, 0.34)
    for ch in "Buckle up you Syrian war dog! Our friends from the United States of Israel sent us a wittle pwetty gift!":
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
    glRasterPos2f(-0.70, 0.29)
    for ch in "Behold! The fabulous B-2 Spirit Bomber! This bird came with a manual too!! Umm.....It says~~":
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
    glRasterPos2f(-0.70, 0.24)
    for ch in "WASD to maneuver the bomber, Spacebar to drop bombs and B for scope, LShift to speed up and LCtrl to speed down.":
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
    glRasterPos2f(-0.70, 0.19)
    for ch in "Wow! That was hella simple!":
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
    glRasterPos2f(-0.70, 0.14)
    for ch in "We will be supplying you with repairs and upgrades every 60 seconds. Now go bomb those bastards STRAIGHT TO HELL!":
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))

    # Start button
    glColor4f(0.15, 0.15, 0.18, 0.95)
    glBegin(GL_QUADS)
    glVertex2f(BTN_X0, BTN_Y0); glVertex2f(BTN_X1, BTN_Y0)
    glVertex2f(BTN_X1, BTN_Y1); glVertex2f(BTN_X0, BTN_Y1)
    glEnd()
    glLineWidth(2.0)
    glColor3f(0.9, 0.9, 0.9)
    glBegin(GL_LINE_LOOP)
    glVertex2f(BTN_X0, BTN_Y0); glVertex2f(BTN_X1, BTN_Y0)
    glVertex2f(BTN_X1, BTN_Y1); glVertex2f(BTN_X0, BTN_Y1)
    glEnd()

    # Button label
    label = "START"
    # Center-ish label
    glRasterPos2f(-0.035 * len(label) / 6.0, -0.01)
    for ch in label: glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))

    # Cleanup matrices/state
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopAttrib()

# -------------------------------
# Bullet and Explosion Classes
# -------------------------------
class Bullet:
    def __init__(self, x, y, z, vx, vy, vz, owner='player'):
        self.x = x
        self.y = y
        self.z = z
        self.vx = vx
        self.vy = vy
        self.vz = vz
        self.owner = owner  # 'player' or 'defence'
        self.is_active = True

class Explosion:
    """
    Backwards-compatible Explosion class:
    - default size_max and lifetime use globals
    - optional size_max and lifetime may be provided for bigger/smaller explosions
    """
    def __init__(self, x, y, z, size_max=EXPLOSION_SIZE_MAX, lifetime=EXPLOSION_LIFETIME):
        self.x = x
        self.y = y
        self.z = z
        self.size_max = size_max
        self.lifetime = lifetime
        self.initial_lifetime = lifetime
        self.is_active = True

# -------------------------------
# Draw aircraft with banking (tilting during turns)
# -------------------------------
def drawAircraft(x, y, z, heading):
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(math.degrees(heading), 0, 1, 0)

    # banking (roll) still present
    bank_angle = aircraft_turn_rate * -15  # Bank opposite to turn direction
    glRotatef(bank_angle, 0, 0, 1)

    top_y = 1.0
    bottom_y = -0.4

    verts_top = [
        (0.0, top_y, 12.0),
        (-22.0, top_y, 4.0),
        (-42.0, top_y, -10.0),
        (-18.0, top_y, -20.0),
        (0.0, top_y, -8.0),
        (18.0, top_y, -20.0),
        (42.0, top_y, -10.0),
        (22.0, top_y, 4.0),
    ]

    glColor3f(0.08, 0.08, 0.10)
    glBegin(GL_POLYGON)
    for vx, vy, vz in verts_top:
        glVertex3f(vx, vy, vz)
    glEnd()

    glColor3f(0.03, 0.03, 0.04)
    glBegin(GL_POLYGON)
    for vx, vy, vz in reversed(verts_top):
        glVertex3f(vx, bottom_y, vz)
    glEnd()

    glColor3f(0.06, 0.06, 0.08)
    glBegin(GL_QUADS)
    n = len(verts_top)
    for i in range(n):
        x1, y1, z1 = verts_top[i]
        x2, y2, z2 = verts_top[(i + 1) % n]
        glVertex3f(x1, bottom_y, z1)
        glVertex3f(x2, bottom_y, z2)
        glVertex3f(x2, top_y, z2)
        glVertex3f(x1, top_y, z1)
    glEnd()

    glPushMatrix()
    glTranslatef(0.0, top_y + 0.8, 5.0)
    glScalef(4.0, 1.2, 6.0)
    glColor3f(0.10, 0.10, 0.12)
    glutSolidSphere(1.0, 20, 20)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(0.0, top_y + 0.45, -6.0)
    glScalef(6.0, 0.6, 4.0)
    glColor3f(0.09, 0.09, 0.10)
    glutSolidSphere(1.0, 16, 16)
    glPopMatrix()

    glColor3f(0.11, 0.11, 0.13)
    glBegin(GL_TRIANGLES)
    glVertex3f(0.0, top_y + 0.05, 12.0)
    glVertex3f(-6.0, top_y + 0.02, 8.0)
    glVertex3f(-12.0, top_y + 0.02, 6.0)
    glVertex3f(0.0, top_y + 0.05, 12.0)
    glVertex3f(12.0, top_y + 0.02, 6.0)
    glVertex3f(6.0, top_y + 0.02, 8.0)
    glEnd()

    glPopMatrix()

# -------------------------------
# Draw a generic rectangular building
# -------------------------------
def drawBuilding(x, y, z, width, height, depth, color, destruction_phase):
    glPushMatrix()
    glTranslatef(x, y + height / 2 * destruction_phase, z)
    glScalef(width, height * destruction_phase, depth)
    glColor3f(*color)
    glutSolidCube(1.0)
    glPopMatrix()

# -------------------------------
# NEW: Draw a hospital (blue body + red cross on roof)
# -------------------------------
def drawHospital(x, y, z, width, height, depth, destruction_phase):
    drawBuilding(x, y, z, width, height, depth, HOSPITAL_BLUE, destruction_phase)
    top_y = y + height * destruction_phase
    cross_thickness = min(width, depth) * 0.30
    cross_length = min(width, depth) * 0.80
    cross_height = 1.0

    glPushMatrix()
    glTranslatef(x, top_y + cross_height / 2.0 + 0.2, z)
    glColor3f(*HOSPITAL_RED)

    glPushMatrix()
    glScalef(cross_thickness, cross_height, cross_length)
    glutSolidCube(1.0)
    glPopMatrix()

    glPushMatrix()
    glScalef(cross_length, cross_height, cross_thickness)
    glutSolidCube(1.0)
    glPopMatrix()

    glPopMatrix()

# -------------------------------
# Draw military base
# -------------------------------
def drawMilitaryBase(x, y, z, width, height, depth, destruction_phase):
    drawBuilding(x, y, z, width, height, depth, OLIVE, destruction_phase)

    hangar_h = max(10.0, height * 0.9 + 4.0)
    glPushMatrix()
    glTranslatef(x, y + height * destruction_phase + hangar_h / 2.0, z)
    glScalef(width * 0.60, hangar_h, depth * 0.60)
    glColor3f(*OLIVE_DARK)
    glutSolidCube(1.0)
    glPopMatrix()

    tower_h = max(8.0, height * 1.4)
    tower_w = min(width, depth) * 0.12
    offsets = [
        (+width * 0.45, +depth * 0.45),
        (+width * 0.45, -depth * 0.45),
        (-width * 0.45, +depth * 0.45),
        (-width * 0.45, -depth * 0.45),
    ]
    for ox, oz in offsets:
        glPushMatrix()
        glTranslatef(x + ox, y + tower_h / 2.0, z + oz)
        glScalef(tower_w, tower_h, tower_w)
        glColor3f(0.22, 0.26, 0.16)
        glutSolidCube(1.0)
        glPopMatrix()

# -------------------------------
# Draw streets & ground
# -------------------------------
def drawStreets():
    glColor3f(0.2, 0.2, 0.2)
    for z in range(-CITY_SIZE // 2, CITY_SIZE // 2 + BLOCK_SIZE + STREET_WIDTH, BLOCK_SIZE + STREET_WIDTH):
        glBegin(GL_QUADS)
        glVertex3f(-CITY_SIZE // 2, 0.1, z - STREET_WIDTH // 2)
        glVertex3f(-CITY_SIZE // 2, 0.1, z + STREET_WIDTH // 2)
        glVertex3f(CITY_SIZE // 2, 0.1, z + STREET_WIDTH // 2)
        glVertex3f(CITY_SIZE // 2, 0.1, z - STREET_WIDTH // 2)
        glEnd()
    for x in range(-CITY_SIZE // 2, CITY_SIZE // 2 + BLOCK_SIZE + STREET_WIDTH, BLOCK_SIZE + STREET_WIDTH):
        glBegin(GL_QUADS)
        glVertex3f(x - STREET_WIDTH // 2, 0.1, -CITY_SIZE // 2)
        glVertex3f(x + STREET_WIDTH // 2, 0.1, -CITY_SIZE // 2)
        glVertex3f(x + STREET_WIDTH // 2, 0.1, CITY_SIZE // 2)
        glVertex3f(x - STREET_WIDTH // 2, 0.1, CITY_SIZE // 2)
        glEnd()

def drawGround():
    glPushMatrix()
    glColor3f(0.3, 0.5, 0.3)
    glScalef(CITY_SIZE, 0.1, CITY_SIZE)
    glutSolidCube(1)
    glPopMatrix()

# -------------------------------
# Draw air-defence turret
# -------------------------------
def drawAirDefence(def_obj):
    x = def_obj['x']
    z = def_obj['z']
    y = def_obj['y']

    glPushMatrix()
    glTranslatef(x, y + 1.0, z)
    glScalef(3.0, 2.0, 3.0)
    glColor3f(0.1, 0.1, 0.12)
    glutSolidCube(1.0)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(x, y + 3.2, z)
    glScalef(0.6, 2.4, 0.6)
    glColor3f(0.18, 0.18, 0.18)
    glutSolidCube(1.0)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(x, y + 4.8, z)
    glScalef(0.8, 0.8, 0.8)
    glColor3f(0.3, 0.2, 0.2)
    glutSolidSphere(0.5, 10, 10)
    glPopMatrix()

# -------------------------------
# Draw an Israeli flag banner on a building side
# (simple 2D banner attached slightly off the face)
# -------------------------------
def drawIsraelFlagBanner(building):
    """
    Draw a rectangular banner with two blue stripes and a stylized Star of David (two triangles).
    The banner will be drawn on the +Z (front) face and +X (right) face so it's visible from multiple angles.
    """
    x = building['x']
    z = building['z']
    base_y = building['y']
    height = building['height'] * building.get('destruction_phase', 1.0)
    width = building['width']
    depth = building['depth']

    # banner size relative to building (caps to avoid oversized)
    banner_w = min(width * 0.85, depth * 2.0)   # extend across front face but not past edges
    banner_h = max(6.0, height * 0.35)          # a visible mid-height banner (min height)
    y_center = base_y + height * 0.55           # slightly above mid-height

    # small offset to avoid z-fighting
    eps = 0.015

    # Helper to draw a flat flag in the XY plane, centered at origin, width=1 height=1
    def draw_flag_unit():
        # white background
        glColor3f(1.0, 1.0, 1.0)
        glBegin(GL_QUADS)
        glVertex3f(-0.5, -0.5, 0.0)
        glVertex3f( 0.5, -0.5, 0.0)
        glVertex3f( 0.5,  0.5, 0.0)
        glVertex3f(-0.5,  0.5, 0.0)
        glEnd()

        # blue stripes (thin)
        stripe_h = 0.12
        glColor3f(0.06, 0.36, 0.95)
        # bottom stripe
        glBegin(GL_QUADS)
        glVertex3f(-0.5, -0.5, 0.001)
        glVertex3f( 0.5, -0.5, 0.001)
        glVertex3f( 0.5, -0.5 + stripe_h*2.0, 0.001)
        glVertex3f(-0.5, -0.5 + stripe_h*2.0, 0.001)
        glEnd()
        # top stripe
        glBegin(GL_QUADS)
        glVertex3f(-0.5, 0.5 - stripe_h*2.0, 0.001)
        glVertex3f( 0.5, 0.5 - stripe_h*2.0, 0.001)
        glVertex3f( 0.5, 0.5, 0.001)
        glVertex3f(-0.5, 0.5, 0.001)
        glEnd()

        # Star of David approximation: two filled triangles (one upright, one inverted)
        glColor3f(0.06, 0.36, 0.95)
        tri_scale = 0.28
        # upright triangle
        glBegin(GL_TRIANGLES)
        glVertex3f( 0.0,  tri_scale, 0.002)
        glVertex3f(-tri_scale*0.866, -tri_scale*0.5, 0.002)
        glVertex3f( tri_scale*0.866, -tri_scale*0.5, 0.002)
        glEnd()
        # inverted triangle
        glBegin(GL_TRIANGLES)
        glVertex3f( 0.0, -tri_scale, 0.002)
        glVertex3f(-tri_scale*0.866, tri_scale*0.5, 0.002)
        glVertex3f( tri_scale*0.866, tri_scale*0.5, 0.002)
        glEnd()

    # Draw on front (+Z)
    glPushMatrix()
    glTranslatef(x, y_center, z + depth / 2.0 + eps)
    # align plane facing +Z
    # scale unit flag to banner_w x banner_h
    glScalef(banner_w, banner_h, 1.0)
    draw_flag_unit()
    glPopMatrix()

    # Draw on right (+X)
    glPushMatrix()
    glTranslatef(x + width / 2.0 + eps, y_center, z)
    # rotate so the unit flag faces +X (rotate around Y by -90)
    glRotatef(-90.0, 0, 1, 0)
    glScalef(banner_w, banner_h, 1.0)
    draw_flag_unit()
    glPopMatrix()


def get_max_building_height():
    if not buildings:
        return 0
    return max(b['height'] for b in buildings)




# -------------------------------
# World with ground + cityscape
# -------------------------------
def drawWorld():
    global buildings, buildings_generated

    if not buildings_generated:
        random.seed(42)
        buildings.clear()
        for block_x in range(-CITY_SIZE // 2, CITY_SIZE // 2, BLOCK_SIZE + STREET_WIDTH):
            for block_z in range(-CITY_SIZE // 2, CITY_SIZE // 2, BLOCK_SIZE + STREET_WIDTH):
                if random.random() > 0.05:
                    buildings_per_side = random.randint(2, 4)
                    building_spacing = BLOCK_SIZE / buildings_per_side
                    for i in range(buildings_per_side):
                        for j in range(buildings_per_side):
                            x_offset = (i - (buildings_per_side - 1) / 2) * building_spacing * 0.8
                            z_offset = (j - (buildings_per_side - 1) / 2) * building_spacing * 0.8
                            x = block_x + x_offset
                            z = block_z + z_offset
                            roll = random.randint(1, SPECIAL_RATE)
                            if roll == 1:
                                btype = 'hospital'
                            elif roll == 2:
                                btype = 'military'
                            else:
                                btype = 'tall' if random.random() < 0.45 else 'medium'
                            if btype == 'tall':
                                width = random.uniform(10, 15)
                                depth = random.uniform(10, 15)
                                height = random.uniform(120, 180)
                                color_options = [
                                    (0.6, 0.6, 0.6), (0.7, 0.7, 0.8), (0.5, 0.5, 0.5),
                                    (0.8, 0.7, 0.6), (0.4, 0.4, 0.5), (0.6, 0.5, 0.4),
                                    (0.9, 0.9, 0.9), (0.3, 0.3, 0.4)
                                ]
                                color = random.choice(color_options)
                            elif btype == 'medium':
                                width = random.uniform(12, 20)
                                depth = random.uniform(12, 20)
                                height = random.uniform(40, 100)
                                color_options = [
                                    (0.65, 0.65, 0.7), (0.55, 0.55, 0.6), (0.7, 0.6, 0.5),
                                    (0.75, 0.75, 0.75), (0.5, 0.5, 0.55)
                                ]
                                color = random.choice(color_options)
                            elif btype == 'hospital':
                                width = random.uniform(14, 22)
                                depth = random.uniform(14, 22)
                                height = random.uniform(35, 60)
                                color = HOSPITAL_BLUE
                            else:
                                width = random.uniform(22, 35)
                                depth = random.uniform(22, 35)
                                height = random.uniform(8, 16)
                                color = OLIVE
                            buildings.append({
                                'x': x,
                                'y': 0,
                                'z': z,
                                'width': width,
                                'height': height,
                                'depth': depth,
                                'color': color,
                                'type': btype,
                                'is_destroyed': False,
                                'destruction_phase': 1.0
                            })

        # ---- NEW: Add the central special building (very visible, flagged) ----
        # It sits at the exact city center (0,0), 2x wider than typical buildings and slightly taller
        center_width = 60.0   # significantly wider than normal (normal widths previously up to ~35)
        center_depth = 40.0
        center_height = 200.0  # slightly taller than the tall buildings (talls were up to ~200)
        center_color = (0.08, 0.08, 0.08)  # darkest grey
        buildings.append({
            'x': 0.0,
            'y': 0,
            'z': 0.0,
            'width': center_width,
            'height': center_height,
            'depth': center_depth,
            'color': center_color,
            'type': 'tall',                  # treat as 'tall' for scoring & consistency
            'is_destroyed': False,
            'destruction_phase': 1.0,
            'is_center_flag': True          # custom marker to draw the Israeli banner
        })

        buildings_generated = True

    drawGround()
    drawStreets()

    for building in buildings:
        if not building['is_destroyed']:
            if building['type'] == 'hospital':
                drawHospital(
                    building['x'], building['y'], building['z'],
                    building['width'], building['height'], building['depth'],
                    building['destruction_phase']
                )
            elif building['type'] == 'military':
                drawMilitaryBase(
                    building['x'], building['y'], building['z'],
                    building['width'], building['height'], building['depth'],
                    building['destruction_phase']
                )
            else:
                drawBuilding(
                    building['x'], building['y'], building['z'],
                    building['width'], building['height'], building['depth'],
                    building['color'], building['destruction_phase']
                )
                # If this is the special center building, draw the flag banner
                if building.get('is_center_flag', False):
                    drawIsraelFlagBanner(building)

    for d in defences:
        drawAirDefence(d)

# -------------------------------
# Utility functions
# -------------------------------
def clamp(value, min_val, max_val):
    return max(min_val, min(value, max_val))

def place_defence_nonoverlapping():
    attempts = 0
    while attempts < 100:
        attempts += 1
        x = random.uniform(-CITY_SIZE / 2 + 10, CITY_SIZE / 2 - 10)
        z = random.uniform(-CITY_SIZE / 2 + 10, CITY_SIZE / 2 - 10)
        ok = True
        for b in buildings:
            half_w = b['width'] / 2.0 + DEFENCE_CLEARANCE
            half_d = b['depth'] / 2.0 + DEFENCE_CLEARANCE
            if (x >= b['x'] - half_w and x <= b['x'] + half_w and
                z >= b['z'] - half_d and z <= b['z'] + half_d):
                ok = False
                break
        if ok:
            return x, z
    return random.uniform(-CITY_SIZE / 2 + 10, CITY_SIZE / 2 - 10), random.uniform(-CITY_SIZE / 2 + 10, CITY_SIZE / 2 - 10)

def spawn_defence():
    x, z = place_defence_nonoverlapping()
    def_obj = {
        'x': x,
        'y': 0.0,
        'z': z,
        'time_since_last_shot': 0.0,
        'shot_interval': random.uniform(DEFENCE_SHOOT_INTERVAL_MIN, DEFENCE_SHOOT_INTERVAL_MAX)
    }
    defences.append(def_obj)

# -------------------------------
# Update aircraft position with fluid movement
# -------------------------------
def updateAircraft():
    global aircraft_x, aircraft_z, aircraft_y, aircraft_heading, aircraft_speed, aircraft_velocity_x, aircraft_velocity_z, aircraft_turn_rate, last_frame_time, current_fov, frame_dt, game_over, death_reason

    if game_over:
        return

    current_time = glutGet(GLUT_ELAPSED_TIME) / 1000.0
    if last_frame_time == 0:
        last_frame_time = current_time
    dt = current_time - last_frame_time
    if dt > 0.05:
        dt = 0.05
    last_frame_time = current_time

    frame_dt = dt
    if dt <= 0:
        return

    if HAS_WIN_KBD:
        keys_pressed['shift'] = _is_vk_down(VK_LSHIFT)
        keys_pressed['ctrl']  = _is_vk_down(VK_LCONTROL)

    if keys_pressed.get('s', False):
        aircraft_y += aircraft_altitude_speed
    if keys_pressed.get('w', False):
        aircraft_y -= aircraft_altitude_speed
    aircraft_y = clamp(aircraft_y, min_altitude, max_altitude)

    target_turn_rate = 0.0
    if keys_pressed['a']:
        target_turn_rate = max_turn_rate
    elif keys_pressed['d']:
        target_turn_rate = -max_turn_rate

    if abs(target_turn_rate - aircraft_turn_rate) > 0.001:
        if target_turn_rate == 0.0:
            if aircraft_turn_rate > 0:
                aircraft_turn_rate = max(0, aircraft_turn_rate - turn_deceleration * dt)
            else:
                aircraft_turn_rate = min(0, aircraft_turn_rate + turn_deceleration * dt)
        else:
            if target_turn_rate > aircraft_turn_rate:
                aircraft_turn_rate = min(target_turn_rate, aircraft_turn_rate + turn_acceleration * dt)
            else:
                aircraft_turn_rate = max(target_turn_rate, aircraft_turn_rate - turn_acceleration * dt)

    aircraft_heading += aircraft_turn_rate * dt

    target_speed = aircraft_speed
    if keys_pressed['shift'] and aircraft_speed < max_speed:
        target_speed = min(max_speed, aircraft_speed + speed_acceleration * dt)
    if keys_pressed['ctrl'] and aircraft_speed > min_speed:
        target_speed = max(min_speed, aircraft_speed - speed_acceleration * dt)
    aircraft_speed = target_speed

    target_vel_x = aircraft_speed * math.sin(aircraft_heading)
    target_vel_z = aircraft_speed * math.cos(aircraft_heading)

    aircraft_velocity_x += (target_vel_x - aircraft_velocity_x) * movement_smoothing
    aircraft_velocity_z += (target_vel_z - aircraft_velocity_z) * movement_smoothing

    aircraft_x += aircraft_velocity_x
    aircraft_z += aircraft_velocity_z

    if aircraft_x > CITY_SIZE // 2:
        aircraft_x = -CITY_SIZE // 2
    if aircraft_x < -CITY_SIZE // 2:
        aircraft_x = CITY_SIZE // 2
    if aircraft_z > CITY_SIZE // 2:
        aircraft_z = -CITY_SIZE // 2
    if aircraft_z < -CITY_SIZE // 2:
        aircraft_z = CITY_SIZE // 2

    bomber_radius = BOMBER_RADIUS
    for b in buildings:
        if not b['is_destroyed']:
            bx, by, bz = b['x'], b['y'], b['z']
            bw, bh, bd = b['width'], b['height'], b['depth']
            if (abs(aircraft_x - bx) < bw / 2 + bomber_radius and
                abs(aircraft_z - bz) < bd / 2 + bomber_radius and
                aircraft_y <= by + bh):
                game_over = True
                death_reason = 'building'
                explosions.append(Explosion(aircraft_x, aircraft_y, aircraft_z, size_max=80.0, lifetime=120))
                return

    target_fov = topdown_fov if bomber_scope_enabled else default_fov
    dt = max(1e-6, dt)
    alpha = 1.0 - math.exp(-zoom_rate * dt)
    current_fov += (target_fov - current_fov) * alpha

# -------------------------------
# Bomber scope overlay (pure 2D overlay; no side effects)
# -------------------------------
def drawBomberScopeOverlay():
    glPushAttrib(GL_ENABLE_BIT | GL_COLOR_BUFFER_BIT | GL_LINE_BIT)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glDisable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    r_inner = 0.65
    r_outer = 1.20
    segments = 128

    glColor4f(0.0, 0.0, 0.0, 0.75)
    glBegin(GL_TRIANGLE_STRIP)
    for i in range(segments + 1):
        a = 2.0 * math.pi * i / segments
        x_in = r_inner * math.cos(a)
        y_in = r_inner * math.sin(a)
        x_out = r_outer * math.cos(a)
        y_out = r_outer * math.sin(a)
        glVertex3f(x_out, y_out, 0.0)
        glVertex3f(x_in, y_in, 0.0)
    glEnd()

    glLineWidth(2.0)
    glColor3f(0.95, 0.95, 0.95)
    glBegin(GL_LINE_LOOP)
    for i in range(segments):
        a = 2.0 * math.pi * i / segments
        glVertex3f(r_inner * math.cos(a), r_inner * math.sin(a), 0.0)
    glEnd()

    glLineWidth(1.5)
    glBegin(GL_LINES)
    glVertex3f(-r_inner * 0.95, 0.0, 0.0); glVertex3f(-0.08, 0.0, 0.0)
    glVertex3f(0.08, 0.0, 0.0); glVertex3f(r_inner * 0.95, 0.0, 0.0)
    glVertex3f(0.0, -r_inner * 0.95, 0.0); glVertex3f(0.0, -0.08, 0.0)
    glVertex3f(0.0, 0.08, 0.0); glVertex3f(0.0, r_inner * 0.95, 0.0)
    glEnd()

    glColor3f(1.0, 0.9, 0.2)
    glRasterPos2f(-0.12, -r_inner - 0.06)
    for ch in "TOP-DOWN ZOOM":
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopAttrib()

# -------------------------------
# Display function
# -------------------------------
def display():
    global hospital_warning_time_remaining
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    if game_state == "title":
        drawTitleScreen()
        glutSwapBuffers()
        return

    elif game_state == "monologue":
        drawMonologueScreen()
        glutSwapBuffers()
        return

    aspect = float(WINDOW_W) / float(WINDOW_H)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(current_fov, aspect, 1, 2000)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    if bomber_scope_enabled:
        look_x = aircraft_x + topdown_ahead_distance * math.sin(aircraft_heading)
        look_z = aircraft_z + topdown_ahead_distance * math.cos(aircraft_heading)
        eye_x = look_x
        eye_z = look_z
        eye_y = aircraft_y + topdown_eye_height
        gluLookAt(eye_x, eye_y, eye_z,
                  look_x, 0.0, look_z,
                  0.0, 0.0, -1.0)
    else:
        camera_distance = chase_cam_distance
        camera_height = 25
        camera_x = aircraft_x - camera_distance * math.sin(aircraft_heading)
        camera_y = aircraft_y + camera_height
        camera_z = aircraft_z - camera_distance * math.cos(aircraft_heading)
        look_x = aircraft_x + 20 * math.sin(aircraft_heading)
        look_y = aircraft_y
        look_z = aircraft_z + 20 * math.cos(aircraft_heading)
        gluLookAt(camera_x, camera_y, camera_z,
                  look_x, look_y, look_z,
                  0, 1, 0)

    drawWorld()

    for tok in repair_tokens:
        drawRepairToken(tok)

    for tok in upgrade_tokens:
        drawUpgradeToken(tok)

    if not game_over:
        drawAircraft(aircraft_x, aircraft_y, aircraft_z, aircraft_heading)

    for bullet in bullets:
        glPushMatrix()
        glTranslatef(bullet.x, bullet.y, bullet.z)
        if bullet.owner == 'player':
            glColor3f(0.05, 0.05, 0.05)
            glutSolidSphere(BULLET_SIZE, 16, 16)
            glPushMatrix()
            glTranslatef(0, -BULLET_SIZE * 0.6, 0)
            glRotatef(180, 1, 0, 0)
            glColor3f(0.18, 0.18, 0.18)
            glutSolidCone(BULLET_SIZE * 0.6, BULLET_SIZE * 1.2, 10, 10)
            glPopMatrix()
        else:
            glColor3f(1.0, 1.0, 0.0)
            glutSolidSphere(DEFENCE_BULLET_SIZE, 12, 12)
        glPopMatrix()

    for exp in explosions:
        glPushMatrix()
        glTranslatef(exp.x, exp.y, exp.z)
        if exp.initial_lifetime > 0:
            progress = (exp.initial_lifetime - exp.lifetime) / exp.initial_lifetime
        else:
            progress = 1.0
        current_size = progress * exp.size_max
        red = 1.0
        green = 0.5 + 0.5 * (1 - progress)
        blue = 0.0
        glColor4f(red, green, blue, clamp(1.0 - progress, 0.0, 1.0))
        glutSolidSphere(current_size, 20, 20)
        glPopMatrix()

    # HUD overlay
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glDisable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # Health bar (top-center)
    bar_half_width = 0.35
    bar_height = 0.035
    bar_top = 0.95
    bar_bottom = bar_top - bar_height

    glColor4f(0.06, 0.06, 0.06, 0.9)
    glBegin(GL_QUADS)
    glVertex2f(-bar_half_width - 0.01, bar_bottom - 0.01)
    glVertex2f(bar_half_width + 0.01, bar_bottom - 0.01)
    glVertex2f(bar_half_width + 0.01, bar_top + 0.01)
    glVertex2f(-bar_half_width - 0.01, bar_top + 0.01)
    glEnd()

    glColor4f(0.22, 0.22, 0.22, 0.95)
    glBegin(GL_QUADS)
    glVertex2f(-bar_half_width, bar_bottom)
    glVertex2f(bar_half_width, bar_bottom)
    glVertex2f(bar_half_width, bar_top)
    glVertex2f(-bar_half_width, bar_top)
    glEnd()

    fill_frac = clamp(float(bomber_health) / 100.0, 0.0, 1.0)
    fill_right = -bar_half_width + (2.0 * bar_half_width) * fill_frac
    glColor4f(0.05, 0.9, 0.05, 0.95)
    glBegin(GL_QUADS)
    glVertex2f(-bar_half_width, bar_bottom)
    glVertex2f(fill_right, bar_bottom)
    glVertex2f(fill_right, bar_top)
    glVertex2f(-bar_half_width, bar_top)
    glEnd()

    glColor3f(1.0, 1.0, 1.0)
    glRasterPos2f(-0.06, bar_top + 0.02)
    for ch in "HEALTH":
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(ch))

    # Score & HUD left
    glColor3f(1, 1, 1)
    glRasterPos2f(-0.9, 0.95)
    score_text = f"Score: {score}"
    for char in score_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))

    glRasterPos2f(-0.9, 0.89)
    if is_reloading:
        reload_text = f"Bombs: {bombs_available}/{MAX_BOMBS} (Reloading: {reload_time_remaining:.1f}s)"
        for ch in reload_text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
    else:
        bombs_text = f"Bombs: {bombs_available}/{MAX_BOMBS}"
        for ch in bombs_text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))

    glRasterPos2f(-0.9, 0.86)
    speed_text = f"Speed: {aircraft_speed:.1f}"
    for char in speed_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))

    glRasterPos2f(-0.9, 0.83)
    turn_text = f"Turn Rate: {aircraft_turn_rate:.1f}"
    for char in turn_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(char))

    glRasterPos2f(-0.9, 0.80)
    pos_text = f"Position: ({aircraft_x:.0f}, {aircraft_z:.0f})"
    for char in pos_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(char))

    glRasterPos2f(-0.9, 0.77)
    bullets_text = f"Bullets Fired: {bullets_fired_count}"
    for char in bullets_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(char))

    # Hospital-hit big red warning (centered, visible for full duration)
    if hospital_warning_time_remaining > 0.0:
        msg = HOSPITAL_WARNING_MESSAGE
        total_px = 0
        for ch in msg:
            total_px += glutBitmapWidth(GLUT_BITMAP_TIMES_ROMAN_24, ord(ch))
        x_px = int(WINDOW_W / 2 - total_px / 2)
        y_px = int(WINDOW_H * 0.62)
        # shadow
        glColor3f(0.0, 0.0, 0.0)
        glWindowPos2i(x_px - 1, y_px - 1)
        for ch in msg:
            glutBitmapCharacter(GLUT_BITMAP_TIMES_ROMAN_24, ord(ch))
        # main
        glColor3f(1.0, 0.18, 0.18)
        glWindowPos2i(x_px, y_px)
        for ch in msg:
            glutBitmapCharacter(GLUT_BITMAP_TIMES_ROMAN_24, ord(ch))

    # -------------------------------
    # GAME OVER overlay (now uses same centered pixel style + shadow as hospital warning)
    # -------------------------------
    if game_over:
        # lines to draw (all centered, same style)
        title = "STRIKE OVER"
        line2 = f"FINAL SCORE: {score}"
        line3 = "PRESS 'R' TO SRIKE AGAIN"

        # Use TIMES_ROMAN_24 for all 3 lines to match hospital warning style
        font = GLUT_BITMAP_TIMES_ROMAN_24
        # compute widths
        def text_pixel_width(s, fnt):
            w = 0
            for ch in s:
                w += glutBitmapWidth(fnt, ord(ch))
            return w

        px_title = text_pixel_width(title, font)
        px_line2 = text_pixel_width(line2, font)
        px_line3 = text_pixel_width(line3, font)

        # positions (stacked vertically, centered)
        # start Y a bit above center
        title_y_px = int(WINDOW_H * 0.56)
        spacing = 40  # pixel spacing between lines (approx; suitable for 24px font)
        line2_y_px = title_y_px - spacing
        line3_y_px = line2_y_px - spacing

        # Draw title shadow and main
        title_x_px = int(WINDOW_W / 2 - px_title / 2)
        glColor3f(0.0, 0.0, 0.0)
        glWindowPos2i(title_x_px - 1, title_y_px - 1)
        for ch in title:
            glutBitmapCharacter(font, ord(ch))
        glColor3f(1.0, 0.2, 0.2)
        glWindowPos2i(title_x_px, title_y_px)
        for ch in title:
            glutBitmapCharacter(font, ord(ch))

        # Draw line2 shadow and main
        line2_x_px = int(WINDOW_W / 2 - px_line2 / 2)
        glColor3f(0.0, 0.0, 0.0)
        glWindowPos2i(line2_x_px - 1, line2_y_px - 1)
        for ch in line2:
            glutBitmapCharacter(font, ord(ch))
        glColor3f(1.0, 0.85, 0.15)  # different color to distinguish final score
        glWindowPos2i(line2_x_px, line2_y_px)
        for ch in line2:
            glutBitmapCharacter(font, ord(ch))

        # Draw line3 shadow and main
        line3_x_px = int(WINDOW_W / 2 - px_line3 / 2)
        glColor3f(0.0, 0.0, 0.0)
        glWindowPos2i(line3_x_px - 1, line3_y_px - 1)
        for ch in line3:
            glutBitmapCharacter(font, ord(ch))
        glColor3f(0.9, 0.9, 0.95)
        glWindowPos2i(line3_x_px, line3_y_px)
        for ch in line3:
            glutBitmapCharacter(font, ord(ch))

        # optional neutral note when building death (keeps previous neutral wording)
        if death_reason == 'building':
            note = "YOU THOUGHT THAT WOULD DESTROY THE BUILDING?! THIS AIN'T YOUR AMERICAN-FUNDED ISRAELI PROPAGANDA, SOLDIER! DROP BOMBS NEXT TIME!"
            px_note = text_pixel_width(note, GLUT_BITMAP_HELVETICA_12)
            note_x = int(WINDOW_W / 2 - px_note / 2)
            note_y = line3_y_px - 36
            # shadow + main
            glColor3f(0.0, 0.0, 0.0)
            glWindowPos2i(note_x - 1, note_y - 1)
            for ch in note:
                glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(ch))
            glColor3f(1.0, 1.0, 1.0)
            glWindowPos2i(note_x, note_y)
            for ch in note:
                glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(ch))

    # restore matrices & state
    glEnable(GL_DEPTH_TEST)
    glDisable(GL_BLEND)

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

    if bomber_scope_enabled:
        drawBomberScopeOverlay()

    glutSwapBuffers()

# -------------------------------
# Timer function
# -------------------------------
def timer(value):
    global buildings, bullets, explosions, score, defences, frame_dt
    global is_reloading, reload_time_remaining, bombs_available
    global bomber_health, game_over, bullets_fired_count, death_reason
    global repair_spawn_accum, REPAIR_TOKEN_SPIN_DEG, repair_tokens
    global upgrade_spawn_accum, UPGRADE_TOKEN_SPIN_DEG, upgrade_tokens
    global hospital_warning_time_remaining, MAX_BOMBS

    if game_state != "playing":
        glutPostRedisplay()
        glutTimerFunc(16, timer, 0)
        return

    updateAircraft()

    if game_over:
        for exp in list(explosions):
            exp.lifetime -= 1
            if exp.lifetime <= 0:
                try:
                    explosions.remove(exp)
                except ValueError:
                    pass
        # spin tokens even during game over
        REPAIR_TOKEN_SPIN_DEG = (REPAIR_TOKEN_SPIN_DEG + 60.0 * frame_dt) % 360.0
        UPGRADE_TOKEN_SPIN_DEG = (UPGRADE_TOKEN_SPIN_DEG + 90.0 * frame_dt) % 360.0
        hospital_warning_time_remaining = max(0.0, hospital_warning_time_remaining - frame_dt)
        glutPostRedisplay()
        glutTimerFunc(16, timer, 0)
        return

    if is_reloading:
        reload_time_remaining -= frame_dt
        if reload_time_remaining <= 0.0:
            bombs_available = MAX_BOMBS
            is_reloading = False
            reload_time_remaining = 0.0

    desired_defence_count = max(0, (score // DEFENCE_SPAWN_SCORE_STEP) * 3)
    while len(defences) < desired_defence_count:
        spawn_defence()

    for d in defences:
        d['time_since_last_shot'] += frame_dt
        if d['time_since_last_shot'] >= d['shot_interval']:
            spawn_x = d['x']
            spawn_z = d['z']
            spawn_y = d['y'] + 5.0
            vb_x = 0.0
            vb_z = 0.0
            vb_y = DEFENCE_BULLET_SPEED
            new_db = Bullet(spawn_x, spawn_y, spawn_z, vb_x, vb_y, vb_z, owner='defence')
            bullets.append(new_db)
            d['time_since_last_shot'] = 0.0
            d['shot_interval'] = random.uniform(DEFENCE_SHOOT_INTERVAL_MIN, DEFENCE_SHOOT_INTERVAL_MAX)

    for bullet in list(bullets):
        if not bullet.is_active:
            try:
                bullets.remove(bullet)
            except ValueError:
                pass
            continue

        if bullet.owner == 'player':
            bullet.vy += BULLET_GRAVITY
        bullet.x += bullet.vx
        bullet.y += bullet.vy
        bullet.z += bullet.vz

        if bullet.owner == 'player':
            for building in list(buildings):
                if not building['is_destroyed']:
                    if (bullet.x >= building['x'] - building['width'] / 2 and
                        bullet.x <= building['x'] + building['width'] / 2 and
                        bullet.z >= building['z'] - building['depth'] / 2 and
                        bullet.z <= building['z'] + building['depth'] / 2 and
                        bullet.y <= building['y'] + building['height']):
                        btype = building.get('type', 'medium')
                        if btype == 'tall':
                            score += 20
                        elif btype == 'medium':
                            score += 10
                        elif btype == 'military':
                            score += 50
                        elif btype == 'hospital':
                            score -= 30
                            # set warning timer (full duration)
                            hospital_warning_time_remaining = HOSPITAL_WARNING_DURATION

                        bullet.is_active = False
                        building['is_destroyed'] = True
                        explosions.append(Explosion(bullet.x, bullet.y, bullet.z))
                        break

            if bullet.y <= 0 and bullet.is_active:
                bullet.is_active = False
        else:
            dx = bullet.x - aircraft_x
            dy = bullet.y - aircraft_y
            dz = bullet.z - aircraft_z
            dist_sq = dx*dx + dy*dy + dz*dz
            hit_radius = (DEFENCE_BULLET_SIZE + BOMBER_RADIUS)
            if dist_sq < hit_radius * hit_radius:
                bomber_health -= 10
                explosions.append(Explosion(bullet.x, bullet.y, bullet.z, size_max=15.0))
                bullet.is_active = False
                if bomber_health <= 0:
                    bomber_health = 0
                    game_over = True
                    death_reason = 'defence'
                    explosions.append(Explosion(aircraft_x, aircraft_y, aircraft_z, size_max=80.0, lifetime=120))
                    break
            if bullet.y > max(aircraft_y + 200.0, 800.0):
                bullet.is_active = False

    for exp in list(explosions):
        exp.lifetime -= 1
        if exp.lifetime <= 0:
            try:
                explosions.remove(exp)
            except ValueError:
                pass

    buildings[:] = [b for b in buildings if not b['is_destroyed']]

    # Repair tokens spawn logic
    repair_spawn_accum += frame_dt
    if repair_spawn_accum >= REPAIR_SPAWN_INTERVAL:
        while repair_spawn_accum >= REPAIR_SPAWN_INTERVAL:
            repair_spawn_accum -= REPAIR_SPAWN_INTERVAL
            spawn_repair_token()

    # Upgrade tokens spawn logic (same interval as repair tokens)
    upgrade_spawn_accum += frame_dt
    if upgrade_spawn_accum >= UPGRADE_SPAWN_INTERVAL:
        while upgrade_spawn_accum >= UPGRADE_SPAWN_INTERVAL:
            upgrade_spawn_accum -= UPGRADE_SPAWN_INTERVAL
            spawn_upgrade_token()

    REPAIR_TOKEN_SPIN_DEG = (REPAIR_TOKEN_SPIN_DEG + 90.0 * frame_dt) % 360.0
    UPGRADE_TOKEN_SPIN_DEG = (UPGRADE_TOKEN_SPIN_DEG + 90.0 * frame_dt) % 360.0

    for tok in list(repair_tokens):
        dx = tok['x'] - aircraft_x
        dy = tok['y'] - aircraft_y
        dz = tok['z'] - aircraft_z
        dist_sq = dx*dx + dy*dy + dz*dz
        pickup_r = (tok['radius'] + BOMBER_RADIUS)
        if dist_sq <= pickup_r * pickup_r:
            bomber_health = clamp(bomber_health + 10, 0, 100)
            try:
                repair_tokens.remove(tok)
            except ValueError:
                pass
            explosions.append(Explosion(aircraft_x, aircraft_y, aircraft_z, size_max=10.0, lifetime=30))

    for tok in list(upgrade_tokens):
        dx = tok['x'] - aircraft_x
        dy = tok['y'] - aircraft_y
        dz = tok['z'] - aircraft_z
        dist_sq = dx*dx + dy*dy + dz*dz
        pickup_r = (tok['radius'] + BOMBER_RADIUS)
        if dist_sq <= pickup_r * pickup_r:
            # Apply the upgrade: capacity +5; give immediate +5 bombs
            MAX_BOMBS += 5
            bombs_available += 5
            # ensure bombs_available not exceed MAX_BOMBS (it shouldn't, but clamp defensively)
            bombs_available = min(bombs_available, MAX_BOMBS)
            try:
                upgrade_tokens.remove(tok)
            except ValueError:
                pass
            # small visual feedback explosion
            explosions.append(Explosion(aircraft_x, aircraft_y, aircraft_z, size_max=12.0, lifetime=30))
            print(f"Upgrade picked: MAX_BOMBS increased to {MAX_BOMBS}")

    # decrement hospital warning timer after processing events so it remains visible for full duration
    hospital_warning_time_remaining = max(0.0, hospital_warning_time_remaining - frame_dt)

    glutPostRedisplay()
    glutTimerFunc(16, timer, 0)

# -------------------------------
# Reset / Restart Game
# -------------------------------
def reset_game():
    global game_over, bomber_health, score, aircraft_x, aircraft_y, aircraft_z, aircraft_heading, aircraft_speed
    global bullets, explosions, defences, buildings_generated, bombs_available, is_reloading, last_frame_time, bullets_fired_count, death_reason
    global repair_tokens, repair_spawn_accum, REPAIR_TOKEN_SPIN_DEG, hospital_warning_time_remaining
    global upgrade_tokens, upgrade_spawn_accum, UPGRADE_TOKEN_SPIN_DEG, MAX_BOMBS

    game_over = False
    bomber_health = 100
    score = 0
    aircraft_x, aircraft_y, aircraft_z = 0.0, 220.0, 0.0
    aircraft_heading, aircraft_speed = 0.0, 1.0
    bullets.clear()
    explosions.clear()
    defences.clear()
    buildings_generated = False
    bombs_available = DEFAULT_MAX_BOMBS
    MAX_BOMBS = DEFAULT_MAX_BOMBS  # reset the upgraded capacity on full game reset
    is_reloading = False
    bullets_fired_count = 0
    death_reason = 'none'
    last_frame_time = 0.0

    repair_tokens.clear()
    repair_spawn_accum = 0.0
    REPAIR_TOKEN_SPIN_DEG = 0.0

    upgrade_tokens.clear()
    upgrade_spawn_accum = 0.0
    UPGRADE_TOKEN_SPIN_DEG = 0.0

    hospital_warning_time_remaining = 0.0

    global game_started
    game_started = True
    print("Game Reset! (bomb capacity reset to DEFAULT)")

# -------------------------------
# Keyboard input
# -------------------------------
def keyboard(key, x, y):
    global keys_pressed, bullets, bullets_fired_count, bomber_scope_enabled, aircraft_velocity_x, aircraft_velocity_z
    global bombs_available, is_reloading, reload_time_remaining, game_over

    global game_state

    if game_state == "title":
        if key == b'\r':  # ENTER
            game_state = "monologue"
        return

    elif game_state == "monologue":
        if key == b'\r':  # ENTER again
            game_state = "playing"
            start_game()
        return

    modifiers = glutGetModifiers()
    keys_pressed['shift'] = bool(modifiers & GLUT_ACTIVE_SHIFT) if not HAS_WIN_KBD else keys_pressed['shift']
    keys_pressed['ctrl']  = bool(modifiers & GLUT_ACTIVE_CTRL)  if not HAS_WIN_KBD else keys_pressed['ctrl']

    if key == b'a':
        keys_pressed['a'] = True
    elif key == b'd':
        keys_pressed['d'] = True
    elif key == b'w':
        keys_pressed['w'] = True
    elif key == b's':
        keys_pressed['s'] = True
    elif key == b'q':
        exit()
    elif key == b' ':
        if not game_over and not is_reloading and bombs_available > 0:
            bombs_available -= 1
            bullets_fired_count += 1
            spawn_x = aircraft_x
            spawn_y = aircraft_y - 5.0
            spawn_z = aircraft_z
            bullet_vx = 0.0
            bullet_vz = 0.0
            bullet_vy = -3.0
            if bomber_scope_enabled:
                look_x = aircraft_x + topdown_ahead_distance * math.sin(aircraft_heading)
                look_z = aircraft_z + topdown_ahead_distance * math.cos(aircraft_heading)
                spawn_x = look_x
                spawn_z = look_z
                bullet_vx = aircraft_velocity_x
                bullet_vz = aircraft_velocity_z
                bullet_vy = -3.0
            new_bullet = Bullet(spawn_x, spawn_y, spawn_z, bullet_vx, bullet_vy, bullet_vz, owner='player')
            bullets.append(new_bullet)
            if bombs_available <= 0:
                is_reloading = True
                reload_time_remaining = RELOAD_TIME_TOTAL
    elif key == b'b':
        bomber_scope_enabled = not bomber_scope_enabled
    elif key in (b'r', b'R'):
        if game_over:
            reset_game()

def keyboardUpFunc(key, x, y):
    if key == b'a':
        keys_pressed['a'] = False
    elif key == b'd':
        keys_pressed['d'] = False
    elif key == b'w':
        keys_pressed['w'] = False
    elif key == b's':
        keys_pressed['s'] = False

    if not HAS_WIN_KBD:
        modifiers = glutGetModifiers()
        keys_pressed['shift'] = bool(modifiers & GLUT_ACTIVE_SHIFT)
        keys_pressed['ctrl']  = bool(modifiers & GLUT_ACTIVE_CTRL)

# -------------------------------
# Mouse input for wheel zoom + Start button click
# -------------------------------
def mouse(button, state, x, y):
    global chase_cam_distance
    if not game_started and state == GLUT_DOWN and button == GLUT_LEFT_BUTTON:
        ndc_x = (x / float(WINDOW_W)) * 2.0 - 1.0
        ndc_y = 1.0 - (y / float(WINDOW_H)) * 2.0
        if (BTN_X0 <= ndc_x <= BTN_X1) and (BTN_Y0 <= ndc_y <= BTN_Y1):
            start_game()
        return

    if bomber_scope_enabled or state != GLUT_DOWN:
        return
    if button == 3:
        chase_cam_distance = max(CHASE_CAM_MIN, chase_cam_distance - ZOOM_STEP)
        glutPostRedisplay()
    elif button == 4:
        chase_cam_distance = min(CHASE_CAM_MAX, chase_cam_distance + ZOOM_STEP)
        glutPostRedisplay()

def mouseWheel(wheel, direction, x, y):
    global chase_cam_distance
    if not game_started:
        return
    if bomber_scope_enabled:
        return
    if direction > 0:
        chase_cam_distance = max(CHASE_CAM_MIN, chase_cam_distance - ZOOM_STEP)
    else:
        chase_cam_distance = min(CHASE_CAM_MAX, chase_cam_distance + ZOOM_STEP)
    glutPostRedisplay()

# -------------------------------
# Main
# -------------------------------
def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_W, WINDOW_H)
    glutInitWindowPosition(100, 100)
    glutCreateWindow(b"Israel Bombing Simulator")

    glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glClearColor(0.6, 0.8, 1.0, 1.0)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(current_fov, WINDOW_W / WINDOW_H, 1, 2000)

    glutDisplayFunc(display)
    glutKeyboardFunc(keyboard)
    glutKeyboardUpFunc(keyboardUpFunc)

    glutMouseFunc(mouse)
    try:
        glutMouseWheelFunc(mouseWheel)
    except Exception:
        pass

    glutTimerFunc(16, timer, 0)

    print("Flight Controls:")
    print("A/D - Steer left/right")
    print("W/S - Decrease/Increase Altitude (S increases altitude, W decreases altitude)")
    print("Left Shift - Increase speed (hold for gradual accel)")
    print("Left Ctrl  - Decrease speed (hold for gradual decel)")
    print("Spacebar - Fire bomb (limited loadout)")
    print("B - Toggle bomber scope (top-down zoom + overlay)")
    print("Mouse Wheel - Zoom in/out (third-person view only)")
    print("Enter/Space - Start game from menu")
    print("R - Restart (after game over)")
    print("Q - Quit")
    print("NEW: Every 60s a GREEN repair token spawns in the sky. Fly through it for +10 health (max 100).")
    print("NEW: Every 60s a BLUE upgrade token spawns in the sky. Fly through it to increase bomb capacity by +5.")
    print("NEW: Hitting a hospital shows a big red warning for 5 seconds.")
    print("GAME OVER texts now use the same centered bold style as the hospital warning.")

    glutMainLoop()

if __name__ == "__main__":
    main()
