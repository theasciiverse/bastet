#!/usr/bin/env python3
"""Records asciiverse/bastet.cast, the catalog preview, at 100x30
(hub/RECORDING.md): a normal game played by a driver that reads the
screen. Each time a block shows in the well, the driver works out where
it can go (every rotation and column the game would allow from where the
block is), scores the resulting well (height, holes, bumpiness, lines
cleared) and sends the keys for the best one, then Enter to drop it.
After about 45 seconds it drops the rest straight down until the game
ends, enters "player" in the high score table and quits from the menu.

bastet runs from out/ (asciiverse/build.sh) by name, so the cast's header
holds no local path, with a throwaway HOME and data folder, so nothing
touches your own keys or scores.

Needs asciinema 3.x and pyte. Usage, from the repo root:
  uv run --with pyte python3 asciiverse/record-preview.py
Any extra argument is used as the cast's path instead (for test runs)."""
import fcntl, os, pty, select, shutil, struct, sys, tempfile, termios, time
import pyte

# ncurses draws a run of one character with REP (CSI n b, "repeat the last
# character n times"), which pyte does not know. Teach it here.
_draw = pyte.Screen.draw


def _draw_remembering(self, data):
    if data:
        self.last_char = data[-1]
    _draw(self, data)


def _repeat_last(self, n=1, *rest, **kw):
    if getattr(self, "last_char", None):
        _draw(self, self.last_char * max(1, n))


pyte.Screen.draw = _draw_remembering
pyte.Screen.repeat_last = _repeat_last
pyte.Stream.csi = dict(pyte.Stream.csi, b="repeat_last")

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cast = sys.argv[1] if len(sys.argv) > 1 else f"{root}/asciiverse/bastet.cast"
COLS, ROWS, PLAY = 100, 30, 45.0
W, H = 10, 20

# the blocks as Block.cpp has them: four orientations of four (x, y) dots
# each, relative to the block's position; a new block starts at (3, -2)
# in orientation 0, two rows above the visible well
BLOCKS = {
    "O": [[(1, 1), (2, 1), (1, 0), (2, 0)]] * 4,
    "I": [[(0, 1), (1, 1), (2, 1), (3, 1)], [(2, 3), (2, 1), (2, 2), (2, 0)],
          [(0, 2), (1, 2), (2, 2), (3, 2)], [(1, 3), (1, 1), (1, 2), (1, 0)]],
    "Z": [[(1, 1), (2, 1), (0, 0), (1, 0)], [(1, 2), (1, 1), (2, 1), (2, 0)],
          [(1, 2), (2, 2), (0, 1), (1, 1)], [(0, 2), (0, 1), (1, 1), (1, 0)]],
    "T": [[(0, 1), (1, 1), (2, 1), (1, 0)], [(1, 2), (1, 1), (2, 1), (1, 0)],
          [(1, 2), (0, 1), (1, 1), (2, 1)], [(1, 2), (0, 1), (1, 1), (1, 0)]],
    "J": [[(0, 1), (1, 1), (2, 1), (0, 0)], [(1, 2), (1, 1), (1, 0), (2, 0)],
          [(2, 2), (0, 1), (1, 1), (2, 1)], [(0, 2), (1, 2), (1, 1), (1, 0)]],
    "S": [[(0, 1), (1, 1), (1, 0), (2, 0)], [(2, 2), (1, 1), (2, 1), (1, 0)],
          [(0, 2), (1, 2), (1, 1), (2, 1)], [(1, 2), (0, 1), (1, 1), (0, 0)]],
    "L": [[(0, 1), (1, 1), (2, 1), (2, 0)], [(1, 2), (2, 2), (1, 1), (1, 0)],
          [(0, 2), (0, 1), (1, 1), (2, 1)], [(1, 2), (1, 1), (0, 0), (1, 0)]],
}
# background colours (pyte's names) of the blocks, from Block.cpp's pairs
COLOURS = {"white": "O", "cyan": "I", "red": "Z", "magenta": "T",
           "blue": "J", "green": "S", "brown": "L"}

work = tempfile.mkdtemp(prefix="bastet-preview-")
os.makedirs(f"{work}/data")
env = dict(os.environ, TERM="xterm-256color", COLORTERM="truecolor", LANG="C.UTF-8",
           HOME=work, XDG_DATA_HOME=f"{work}/data", USER="player", LOGNAME="player",
           PATH=f"{root}/out:{os.environ['PATH']}")
for v in ("VTE_VERSION", "TERM_PROGRAM", "TERM_PROGRAM_VERSION", "TMUX"):
    env.pop(v, None)

pid, fd = pty.fork()
if pid == 0:
    os.chdir(work)
    os.execvpe("asciinema", ["asciinema", "rec", "--overwrite", "-q", "--idle-time-limit", "2",
        "--window-size", f"{COLS}x{ROWS}", "--capture-env", "TERM,COLORTERM,LANG",
        "--title", "bastet", "--command", "bastet", cast], env)
fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", ROWS, COLS, 0, 0))
screen = pyte.Screen(COLS, ROWS)
stream = pyte.ByteStream(screen)
start = time.time()


def pump(seconds):
    end = time.time() + seconds
    while True:
        left = end - time.time()
        r, _, _ = select.select([fd], [], [], max(0.0, min(0.02, left)))
        if r:
            try:
                stream.feed(os.read(fd, 65536))
            except OSError:
                return False
        if left <= 0:
            return True


def key(k, wait=0.06):
    os.write(fd, k)
    pump(wait)


def text():
    return "\n".join(screen.display)


def well_origin():
    """Screen position of the well's top left cell: inside the first box
    corner on the screen, which is the well's. With TERM=xterm-256color
    ncurses draws the boxes in the VT100 line set, which pyte keeps as
    letters ('l' and 'q' for the corner and the line)."""
    for y in range(ROWS):
        for corner in ("┌─", "lq"):
            x = screen.display[y].find(corner)
            if x >= 0:
                return x + 1, y + 1
    return None


def read_well():
    """The set of filled (x, y) cells in the well, read from the colours."""
    o = well_origin()
    if not o:
        return None, None
    cells, colours = set(), {}
    for y in range(H):
        for x in range(W):
            c = screen.buffer[o[1] + y][o[0] + 2 * x]
            if c.bg in COLOURS:
                cells.add((x, y))
                colours[(x, y)] = c.bg
    return cells, colours


def dots(b, o, px, py):
    return [(px + dx, py + dy) for dx, dy in BLOCKS[b][o]]


def fits(cells, b, o, px, py):
    return all(0 <= x < W and -2 <= y < H and (x, y) not in cells for x, y in dots(b, o, px, py))


def evaluate(cells):
    """Clears full lines; scores the well like the classic hand-tuned
    players do (fewer lines high, holes and steps are better)."""
    full = [y for y in range(H) if all((x, y) in cells for x in range(W))]
    if full:
        kept = {}
        for x, y in cells:
            if y not in full:
                kept[(x, y + sum(1 for f in full if f > y))] = 1
        cells = set(kept)
    heights = []
    holes = 0
    for x in range(W):
        col = [y for (cx, y) in cells if cx == x]
        top = min(col) if col else H
        heights.append(H - top)
        holes += sum(1 for y in range(top, H) if (x, y) not in cells)
    bump = sum(abs(heights[i] - heights[i + 1]) for i in range(W - 1))
    return -0.51 * sum(heights) + 0.76 * len(full) - 0.36 * holes - 0.18 * bump - 0.3 * max(heights)


def best_move(locked, b, px, py):
    """Keys (rotations, then sideways moves) for the best place to drop
    block b, standing at (px, py) in orientation 0."""
    best, best_keys = None, None
    for rot in range(4):
        if b == "O" and rot:
            break
        if not fits(locked, b, rot, px, py):
            continue
        for step in (-1, 1):
            x = px
            while True:
                y = py
                while fits(locked, b, rot, x, y + 1):
                    y += 1
                final = set(locked) | set(dots(b, rot, x, y))
                if any(dy < 0 for _, dy in dots(b, rot, x, y)):
                    score = -1e9
                else:
                    score = evaluate(final)
                if best is None or score > best:
                    move = (b"\x1bOD" if x < px else b"\x1bOC") * abs(x - px)
                    best, best_keys = score, b" " * rot + move
                if not fits(locked, b, rot, x + step, py):
                    break
                x += step
    return best_keys


def find_block(cells, colours, locked):
    """The falling block: its type and position, from the cells that are
    not part of the locked well."""
    falling = cells - locked
    if len(falling) != 4:
        return None
    kinds = {COLOURS[colours[c]] for c in falling}
    if len(kinds) != 1:
        return None
    b = kinds.pop()
    minx = min(x for x, _ in falling)
    miny = min(y for _, y in falling)
    t = BLOCKS[b][0]
    tx, ty = min(x for x, _ in t), min(y for _, y in t)
    px, py = minx - tx, miny - ty
    if set(dots(b, 0, px, py)) != falling:
        return None
    return b, px, py


def settled():
    """The well once the dropped block is locked and a line clear, which
    flashes the full rows with ':' for two seconds, is over: no ':' and
    no change for half a second. None when the game is over."""
    last, since = None, time.time()
    while True:
        pump(0.05)
        if "Congratulations" in text() or "did not get" in text():
            return None
        cells, _ = read_well()
        o = well_origin()
        flashing = o is not None and any(":" in screen.display[o[1] + y][o[0]:o[0] + 2 * W]
                                         for y in range(H))
        if flashing or cells != last:
            last, since = cells, time.time()
        elif time.time() - since > 0.5:
            return cells or set()


pump(1.5)                  # the menu
key(b"\r", 0.3)            # Play! (normal version)
locked = set()
while time.time() - start < PLAY:
    pump(0.03)
    if "Congratulations" in text() or "did not get" in text():
        break
    cells, colours = read_well()
    if cells is None:
        continue
    seen = find_block(cells, colours, locked)
    if not seen:
        continue
    b, px, py = seen
    keys = best_move(locked, b, px, py) or b""
    os.write(fd, keys)
    pump(0.25)             # let the block be seen in place
    key(b"\r", 0.1)        # drop
    locked = settled()
    if locked is None:
        break

# the end of the game: blocks dropped where they come
for _ in range(400):
    if "Congratulations" in text() or "did not get" in text():
        break
    key(b"\r", 0.15)
if "Congratulations" in text():
    pump(0.8)
    for ch in b"player":
        key(bytes([ch]), 0.12)
    key(b"\r", 1.5)        # the high score table
else:
    pump(1.5)
for _ in range(10):        # through the dialogs to the menu
    if "Play! (normal" in text():
        break
    key(b"\r", 1.0)
key(b"\x1bOB" * 4, 0.6)    # Quit
key(b"\r", 0.5)
end = time.time() + 5
while time.time() < end:
    if not pump(0.1):
        break
    done, _ = os.waitpid(pid, os.WNOHANG)
    if done:
        break
else:
    os.kill(pid, 9)
try:
    os.waitpid(pid, 0)
except ChildProcessError:
    pass
shutil.rmtree(work, ignore_errors=True)
print(f"{cast}: {time.time() - start:.0f} s", file=sys.stderr)
