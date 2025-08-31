from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import random, time
from math import sin, cos, radians

scr_w, scr_h = 1000, 800
fov = 70.0

cam_az = 40.0
cam_dist = 900.0
cam_y = 320.0
cam_y_min, cam_y_max = 120.0, 700.0

cells = 20
grid_half = 10
cell_size = 60
board_half_w = grid_half * cell_size
ground_y = 0.0

snake = []
dir_dx, dir_dz = 1, 0
pending_dx, pending_dz = 1, 0
length_init = 3
score = 0
paused = False
game_over = False
cheat_on = False

step_base = 0.28
step_min  = 0.07
last_step_t = 0.0

food_cell = None

clr_white   = (1.00, 1.00, 1.00)
clr_lilac   = (0.78, 0.66, 0.95)
clr_head    = (0.10, 0.85, 0.25)
clr_body    = (0.10, 0.45, 0.85)
clr_food    = (1.00, 0.70, 0.10)
clr_text    = (1.00, 1.00, 1.00)
bg_clr      = (0.05, 0.06, 0.09, 1.0)

def cell_to_world(cx, cz):
    wx = (cx - grid_half + 0.5) * cell_size
    wz = (cz - grid_half + 0.5) * cell_size
    return wx, wz

def dir_is_reverse(nx, nz, ox, oz):
    return (nx == -ox) and (nz == -oz)

def valid_cell(cx, cz):
    return 0 <= cx < cells and 0 <= cz < cells

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18, color=(1,1,1)):
    glColor3f(*color)
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    gluOrtho2D(0, scr_w, 0, scr_h)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def spawn_food():
    global food_cell
    occupied = set(snake)
    while True:
        cx = random.randint(0, cells-1)
        cz = random.randint(0, cells-1)
        if (cx, cz) not in occupied:
            food_cell = (cx, cz)
            return

def reset_game():
    global snake, dir_dx, dir_dz, pending_dx, pending_dz
    global score, paused, game_over, last_step_t, food_cell, cheat_on
    center = grid_half
    snake = [(center, center), (center-1, center), (center-2, center)]
    dir_dx, dir_dz = 1, 0
    pending_dx, pending_dz = 1, 0
    score = 0
    paused = False
    game_over = False
    cheat_on = False
    last_step_t = time.time()
    spawn_food()

def draw_ground():
    glDisable(GL_CULL_FACE)
    for i in range(cells):
        for j in range(cells):
            wx0 = (i - grid_half) * cell_size
            wz0 = (j - grid_half) * cell_size
            wx1, wz1 = wx0 + cell_size, wz0 + cell_size
            if ((i + j) & 1) == 0: glColor3f(*clr_white)
            else:                   glColor3f(*clr_lilac)
            glBegin(GL_QUADS)
            glVertex3f(wx0, ground_y, wz0)
            glVertex3f(wx1, ground_y, wz0)
            glVertex3f(wx1, ground_y, wz1)
            glVertex3f(wx0, ground_y, wz1)
            glEnd()
    glEnable(GL_CULL_FACE)

def draw_snake():
    for idx, (cx, cz) in enumerate(snake):
        wx, wz = cell_to_world(cx, cz)
        y = 15.0
        sx = sz = cell_size * 0.8
        sy = 28.0
        glPushMatrix()
        glTranslatef(wx, y, wz)
        glScalef(sx, sy, sz)
        if idx == 0:
            glColor3f(*clr_head)
        else:
            t = max(0.25, 1.0 - (idx / max(1.0, len(snake)-1)))
            glColor3f(clr_body[0]*t, clr_body[1], clr_body[2])
        glutSolidCube(1.0)
        glPopMatrix()
        if idx == 0:
            glPushMatrix()
            glTranslatef(wx, y + 16.0, wz)
            if   (dir_dx, dir_dz) == (1, 0):   yaw_deg = 0.0
            elif (dir_dx, dir_dz) == (-1, 0):  yaw_deg = 180.0
            elif (dir_dx, dir_dz) == (0, 1):   yaw_deg = 90.0
            else:                               yaw_deg = -90.0
            glRotatef(yaw_deg, 0, 1, 0)
            glColor3f(0.15, 0.95, 0.25)
            glRotatef(-90, 1, 0, 0)
            q = gluNewQuadric()
            gluCylinder(q, 4.0, 4.0, 22.0, 16, 1)
            gluDeleteQuadric(q)
            glPopMatrix()

def draw_food():
    if not food_cell: return
    wx, wz = cell_to_world(*food_cell)
    glPushMatrix()
    glTranslatef(wx, 18.0, wz)
    glColor3f(*clr_food)
    glutSolidSphere(16.0, 18, 18)
    glPopMatrix()

def setup_camera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fov, scr_w/float(scr_h), 1.0, 5000.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    th = radians(cam_az)
    ex = sin(th) * cam_dist
    ez = cos(th) * cam_dist
    ey = cam_y
    gluLookAt(ex, ey, ez, 0.0, 40.0, 0.0, 0.0, 1.0, 0.0)

def step_interval():
    l = max(len(snake), length_init)
    return max(step_min, step_base - (l - length_init) * 0.008)

def game_step():
    global snake, dir_dx, dir_dz, score, game_over
    global pending_dx, pending_dz
    if not dir_is_reverse(pending_dx, pending_dz, dir_dx, dir_dz):
        dir_dx, dir_dz = pending_dx, pending_dz
    hx, hz = snake[0]
    nx, nz = hx + dir_dx, hz + dir_dz
    if not valid_cell(nx, nz):
        game_over = True
        return
    if (nx, nz) in snake:
        game_over = True
        return
    snake.insert(0, (nx, nz))
    if food_cell and (nx, nz) == food_cell:
        score += 1
        spawn_food()
    else:
        snake.pop()

def autopilot_pick_dir():
    global pending_dx, pending_dz
    if not food_cell or not snake: return
    hx, hz = snake[0]
    fx, fz = food_cell
    occ = set(snake[:-1])
    cand = []
    dx = 1 if fx > hx else (-1 if fx < hx else 0)
    dz = 1 if fz > hz else (-1 if fz < hz else 0)
    if dx != 0: cand.append((dx, 0))
    if dz != 0: cand.append((0, dz))
    if len(cand) < 2:
        for alt in [(1,0),(-1,0),(0,1),(0,-1)]:
            if alt not in cand: cand.append(alt)
    safe = None
    for (tx, tz) in cand:
        if dir_is_reverse(tx, tz, dir_dx, dir_dz): continue
        nx, nz = hx + tx, hz + tz
        if valid_cell(nx, nz) and (nx, nz) not in occ:
            safe = (tx, tz); break
    if safe is None:
        for (tx, tz) in [(1,0),(-1,0),(0,1),(0,-1)]:
            if dir_is_reverse(tx, tz, dir_dx, dir_dz): continue
            nx, nz = hx + tx, hz + tz
            if valid_cell(nx, nz):
                safe = (tx, tz); break
    if safe is not None:
        pending_dx, pending_dz = safe

def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glEnable(GL_DEPTH_TEST)
    setup_camera()
    draw_ground()
    draw_food()
    draw_snake()
    if game_over:
        draw_text(scr_w//2 - 80, scr_h//2 + 40, " GAME OVER ", color=(0,0,0))
        draw_text(scr_w//2 - 70, scr_h//2 + 10, f"Final Score: {score}", color=(0,0,0))
        draw_text(scr_w//2 - 110, scr_h//2 - 20, "Press 'R' to Restart", color=(0,0,0))
    else:
        hud_x = scr_w - 500
        hud_y = scr_h - 40
        draw_text(hud_x, hud_y,       f"Score: {score}")
        draw_text(hud_x, hud_y - 25, "W/A/S/D = Move   Arrows = Camera   P = Pause   R = Restart   C = Cheat")
        if cheat_on:
            draw_text(hud_x, hud_y - 50, "[Cheat Mode: ON]")
        if paused:
            draw_text(scr_w//2 - 60, scr_h//2, "=== PAUSED ===")
    glutSwapBuffers()

def keyboard(k, x, y):
    global pending_dx, pending_dz, paused, cheat_on
    key = k.decode('utf-8').lower()
    if key == 'p':
        if not game_over:
            paused = not paused
        return
    if key == 'r':
        reset_game()
        return
    if key == 'c':
        if not game_over:
            cheat_on = not cheat_on
        return
    if   key == 'w': pending_dx, pending_dz = 0,  1
    elif key == 's': pending_dx, pending_dz = 0, -1
    elif key == 'a': pending_dx, pending_dz = -1, 0
    elif key == 'd': pending_dx, pending_dz = 1,  0

def special_keys(key, x, y):
    global cam_az, cam_y
    if key == GLUT_KEY_LEFT:  cam_az -= 4.0
    if key == GLUT_KEY_RIGHT: cam_az += 4.0
    if key == GLUT_KEY_UP:    cam_y = min(cam_y_max, cam_y + 20.0)
    if key == GLUT_KEY_DOWN:  cam_y = max(cam_y_min, cam_y - 20.0)

def idle():
    global last_step_t
    now = time.time()
    if not paused and not game_over:
        if cheat_on:
            autopilot_pick_dir()
        if now - last_step_t >= step_interval():
            game_step()
            last_step_t = now
    glutPostRedisplay()

def init_gl():
    glClearColor(*bg_clr)
    glShadeModel(GL_SMOOTH)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_CULL_FACE)
    glCullFace(GL_BACK)

def main():
    random.seed(42)
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(scr_w, scr_h)
    glutInitWindowPosition(60, 40)
    glutCreateWindow(b"3D snake game")
    init_gl()
    reset_game()
    glutDisplayFunc(display)
    glutKeyboardFunc(keyboard)
    glutSpecialFunc(special_keys)
    glutIdleFunc(idle)
    glutMainLoop()

if __name__ == "__main__":
    main()
