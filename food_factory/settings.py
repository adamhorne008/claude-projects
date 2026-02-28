# settings.py — single source of truth for all constants

# --- Display ---
SCREEN_W = 1280
SCREEN_H = 720
TITLE = "Food Factory Sim"
FPS = 60

# --- Tile Grid ---
TILE_SIZE = 48
MAP_COLS = 80
MAP_ROWS = 60

# --- Camera ---
CAMERA_SPEED = 300          # pixels per second when panning with keyboard
CAMERA_EDGE_MARGIN = 40    # px from screen edge that triggers auto-pan

# --- Simulation Speed ---
SPEED_STEPS = [0, 1, 2, 4]  # 0 = paused
BASE_MINUTE_MS = 500         # real ms per sim minute at 1x speed
MINUTES_PER_HOUR = 60
HOURS_PER_DAY = 24
DAYS_PER_WEEK = 7
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# --- Colors ---
COL_BG         = (25, 25, 35)
COL_GRID_LINE  = (45, 45, 55)
COL_FLOOR      = (55, 55, 65)
COL_WALL       = (15, 15, 20)
COL_CORRIDOR   = (50, 50, 60)
COL_WHITE      = (220, 220, 220)
COL_BLACK      = (0, 0, 0)

# Department zone colors
COL_RECEIVING  = (70, 130, 180)   # Steel blue
COL_PREP       = (200, 170, 40)   # Yellow
COL_COOKING    = (210, 90, 40)    # Orange/red
COL_QC         = (60, 160, 80)    # Green
COL_PACKAGING  = (140, 60, 180)   # Purple
COL_DISPATCH   = (40, 180, 200)   # Cyan

DEPT_COLORS = {
    "receiving": COL_RECEIVING,
    "prep":      COL_PREP,
    "cooking":   COL_COOKING,
    "qc":        COL_QC,
    "packaging": COL_PACKAGING,
    "dispatch":  COL_DISPATCH,
}

DEPT_NAMES = {
    "receiving": "Receiving",
    "prep":      "Prep",
    "cooking":   "Cooking",
    "qc":        "Quality Control",
    "packaging": "Packaging",
    "dispatch":  "Dispatch",
}

# --- Worker ---
WORKER_RADIUS = 10           # drawn as circle, pixels
WORKER_SPEED  = 120          # pixels per second at 1x speed
WORKER_WORK_DURATION = 4.0   # sim seconds to complete one task (base)
INITIAL_WORKERS_PER_DEPT = 2

# --- Production ---
STAGE_ORDER = ["receiving", "prep", "cooking", "qc", "packaging", "dispatch"]

# --- Items ---
MEAL_TYPES = ["Burger", "Salad", "Pasta", "Sandwich", "Soup", "Pizza", "Wrap"]

# --- Orders ---
ORDERS_PER_WEEK_MIN = 2
ORDERS_PER_WEEK_MAX = 4
ITEMS_PER_ORDER_MIN = 4
ITEMS_PER_ORDER_MAX = 10

CLIENT_NAMES = [
    "City Catering Co.", "Fresh Bites Ltd.", "QuickServe Foods",
    "Metro Meals", "Sunny Kitchen", "Peak Provisions", "Urban Eats",
    "Harbor House", "Valley Vittles", "Crestwood Catering",
]

# --- UI ---
HUD_HEIGHT        = 130
VIEWPORT_H        = SCREEN_H - HUD_HEIGHT   # 590px usable for world

COL_HUD_BG        = (18, 18, 28)
COL_PANEL_BG      = (28, 28, 42)
COL_PANEL_BORDER  = (60, 60, 90)

COL_BTN_NORMAL    = (55, 55, 80)
COL_BTN_HOVER     = (80, 80, 115)
COL_BTN_ACTIVE    = (40, 120, 200)
COL_BTN_DISABLED  = (35, 35, 50)
COL_BTN_TEXT      = (200, 200, 220)

FONT_SM = 13
FONT_MD = 17
FONT_LG = 22

# Order status colors
COL_STATUS = {
    "PENDING":     (160, 160, 160),
    "IN_PROGRESS": (80, 160, 220),
    "READY":       (80, 200, 80),
    "DELIVERED":   (120, 120, 120),
    "OVERDUE":     (220, 60, 60),
}
