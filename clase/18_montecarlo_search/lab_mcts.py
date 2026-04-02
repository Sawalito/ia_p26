#!/usr/bin/env python3
"""
Laboratorio: Monte Carlo Tree Search (imágenes para las notas)

Uso:
    cd clase/18_montecarlo_search
    python3 lab_mcts.py

Genera ~18 imágenes en:
    clase/18_montecarlo_search/images/

Dependencias: numpy, matplotlib
"""

from pathlib import Path
import math
import copy
import random
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import RegularPolygon
import matplotlib.colors as mcolors
import numpy as np

# ---------------------------------------------------------------------------
# Shared styling
# ---------------------------------------------------------------------------
plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams["figure.figsize"] = (12, 6)
plt.rcParams["font.size"] = 11

COLORS = {
    "blue":   "#2E86AB",
    "red":    "#E94F37",
    "green":  "#27AE60",
    "gray":   "#7F8C8D",
    "orange": "#F39C12",
    "purple": "#8E44AD",
    "light":  "#ECF0F1",
    "dark":   "#2C3E50",
    "teal":   "#1ABC9C",
    "pink":   "#E91E8C",
}

# Player colors
BLACK_COLOR = COLORS["dark"]
WHITE_COLOR = "#FFFFFF"
EMPTY_COLOR = "#F5F0E1"
HIGHLIGHT_COLOR = COLORS["orange"]
WIN_PATH_COLOR = COLORS["green"]
NEIGHBOR_COLOR = COLORS["teal"]

ROOT = Path(__file__).resolve().parent
IMAGES_DIR = ROOT / "images"
IMAGES_DIR.mkdir(exist_ok=True)

np.random.seed(42)
random.seed(42)


def _save(fig, name: str) -> None:
    out = IMAGES_DIR / name
    fig.savefig(out, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"✓  {out.name}")


# ---------------------------------------------------------------------------
# Hex game engine
# ---------------------------------------------------------------------------

class Hex:
    """Hex game with offset coordinates. Player 1=Black, 2=White."""

    NEIGHBORS = [(-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0)]

    def __init__(self, size=7, board=None, current_player=1):
        self.size = size
        if board is not None:
            self.board = [row[:] for row in board]
        else:
            self.board = [[0] * size for _ in range(size)]
        self.current_player = current_player

    def actions(self):
        return [(r, c) for r in range(self.size)
                for c in range(self.size) if self.board[r][c] == 0]

    def result(self, action):
        new = Hex(self.size, self.board, 3 - self.current_player)
        r, c = action
        new.board[r][c] = self.current_player
        return new

    def is_terminal(self):
        return self._has_path(1) or self._has_path(2) or not self.actions()

    def utility(self, player):
        if self._has_path(player):
            return 1
        if self._has_path(3 - player):
            return -1
        return 0

    def _has_path(self, player):
        n = self.size
        if player == 1:
            start = [(0, c) for c in range(n) if self.board[0][c] == 1]
            goal_fn = lambda r, c: r == n - 1
        else:
            start = [(r, 0) for r in range(n) if self.board[r][0] == 2]
            goal_fn = lambda r, c: c == n - 1
        visited = set()
        queue = list(start)
        for pos in queue:
            if pos in visited:
                continue
            visited.add(pos)
            r, c = pos
            if goal_fn(r, c):
                return True
            for dr, dc in self.NEIGHBORS:
                nr, nc = r + dr, c + dc
                if 0 <= nr < n and 0 <= nc < n and self.board[nr][nc] == player:
                    queue.append((nr, nc))
        return False

    def get_winning_path(self, player):
        """Return the winning path as a list of (r, c) or empty list."""
        n = self.size
        if player == 1:
            start = [(0, c) for c in range(n) if self.board[0][c] == 1]
            goal_fn = lambda r, c: r == n - 1
        else:
            start = [(r, 0) for r in range(n) if self.board[r][0] == 2]
            goal_fn = lambda r, c: c == n - 1
        visited = {}
        queue = list(start)
        for s in start:
            visited[s] = None
        i = 0
        while i < len(queue):
            pos = queue[i]
            i += 1
            r, c = pos
            if goal_fn(r, c):
                path = []
                cur = pos
                while cur is not None:
                    path.append(cur)
                    cur = visited[cur]
                return path
            for dr, dc in self.NEIGHBORS:
                nr, nc = r + dr, c + dc
                if (0 <= nr < n and 0 <= nc < n
                        and self.board[nr][nc] == player
                        and (nr, nc) not in visited):
                    visited[(nr, nc)] = pos
                    queue.append((nr, nc))
        return []


# ---------------------------------------------------------------------------
# MCTS engine
# ---------------------------------------------------------------------------

class MCTSNode:
    def __init__(self, state, parent=None):
        self.state = state
        self.parent = parent
        self.children = {}
        self.N = 0
        self.Q = 0.0
        self.unexpanded = list(state.actions())
        random.shuffle(self.unexpanded)


def _uct_value(child, parent_n, c):
    if child.N == 0:
        return float('inf')
    return child.Q / child.N + c * math.sqrt(math.log(parent_n) / child.N)


def _run_mcts(state, iterations, player, c=1.41):
    """Run MCTS with UCT, return (best_action, root_node)."""
    root = MCTSNode(state)
    for _ in range(iterations):
        node = root
        # Selection
        while not node.unexpanded and node.children:
            node = max(node.children.values(),
                       key=lambda ch: _uct_value(ch, node.N, c))
        # Expansion
        if node.unexpanded:
            action = node.unexpanded.pop()
            child_state = node.state.result(action)
            child = MCTSNode(child_state, parent=node)
            node.children[action] = child
            node = child
        # Simulation
        sim = Hex(node.state.size, node.state.board, node.state.current_player)
        while not sim.is_terminal():
            acts = sim.actions()
            a = acts[random.randint(0, len(acts) - 1)]
            sim = sim.result(a)
        reward = sim.utility(player)
        # Backpropagation
        while node is not None:
            node.N += 1
            node.Q += reward
            node = node.parent

    if not root.children:
        return root.state.actions()[0], root
    best = max(root.children, key=lambda a: root.children[a].N)
    return best, root


def _run_mcts_naive(state, iterations, player):
    """MCTS with greedy selection (no exploration bonus)."""
    root = MCTSNode(state)
    for _ in range(iterations):
        node = root
        while not node.unexpanded and node.children:
            node = max(node.children.values(),
                       key=lambda ch: (ch.Q / ch.N if ch.N > 0 else float('inf')))
        if node.unexpanded:
            action = node.unexpanded.pop()
            child_state = node.state.result(action)
            child = MCTSNode(child_state, parent=node)
            node.children[action] = child
            node = child
        sim = Hex(node.state.size, node.state.board, node.state.current_player)
        while not sim.is_terminal():
            acts = sim.actions()
            sim = sim.result(acts[random.randint(0, len(acts) - 1)])
        reward = sim.utility(player)
        while node is not None:
            node.N += 1
            node.Q += reward
            node = node.parent
    if not root.children:
        return root.state.actions()[0], root
    best = max(root.children, key=lambda a: root.children[a].N)
    return best, root


def _play_game(size, agent1_fn, agent2_fn):
    """Play a game, return 1 if player 1 wins, 2 if player 2 wins."""
    state = Hex(size)
    while not state.is_terminal():
        if state.current_player == 1:
            action = agent1_fn(state, 1)
        else:
            action = agent2_fn(state, 2)
        state = state.result(action)
    if state.utility(1) == 1:
        return 1
    return 2


def _random_agent(state, player):
    acts = state.actions()
    return acts[random.randint(0, len(acts) - 1)]


def _mcts_agent(iterations, c=1.41):
    def agent(state, player):
        a, _ = _run_mcts(state, iterations, player, c)
        return a
    return agent


def _minimax(state, player, depth=99):
    """Simple minimax for small boards."""
    if state.is_terminal() or depth == 0:
        return state.utility(player), None
    best_val = -2
    best_act = None
    for a in state.actions():
        child = state.result(a)
        val, _ = _minimax(child, player, depth - 1)
        val = -val  # opponent's perspective
        if val > best_val:
            best_val = val
            best_act = a
    return best_val, best_act


def _alphabeta_agent(depth=3):
    """Alpha-beta agent with simple distance-based eval."""
    def _eval(state, player):
        # Heuristic: how close is player to connecting?
        n = state.size
        if state._has_path(player):
            return 100
        if state._has_path(3 - player):
            return -100
        # Count min distance from each side for each player
        score = 0
        for p, sign in [(player, 1), (3 - player, -1)]:
            # BFS from starting edge
            if p == 1:
                starts = [(0, c) for c in range(n) if state.board[0][c] != (3 - p)]
                goal_fn = lambda r, c: r == n - 1
            else:
                starts = [(r, 0) for r in range(n) if state.board[r][0] != (3 - p)]
                goal_fn = lambda r, c: c == n - 1
            # Simple: count player stones on shortest potential path
            own_count = sum(1 for r in range(n) for c in range(n)
                           if state.board[r][c] == p)
            score += sign * own_count
        return score

    def _ab(state, player, depth_left, alpha, beta, maximizing):
        if state.is_terminal() or depth_left == 0:
            return _eval(state, player), None
        best_act = None
        if maximizing:
            val = -200
            for a in state.actions():
                child = state.result(a)
                v, _ = _ab(child, player, depth_left - 1, alpha, beta, False)
                if v > val:
                    val = v
                    best_act = a
                alpha = max(alpha, val)
                if alpha >= beta:
                    break
            return val, best_act
        else:
            val = 200
            for a in state.actions():
                child = state.result(a)
                v, _ = _ab(child, player, depth_left - 1, alpha, beta, True)
                if v < val:
                    val = v
                    best_act = a
                beta = min(beta, val)
                if alpha >= beta:
                    break
            return val, best_act

    def agent(state, player):
        _, act = _ab(state, player, depth, -200, 200, True)
        if act is None:
            acts = state.actions()
            act = acts[0] if acts else None
        return act
    return agent


# ---------------------------------------------------------------------------
# Hex board drawing helper
# ---------------------------------------------------------------------------

def _hex_to_pixel(r, c, hex_size=1.0):
    """Convert offset hex coordinates to pixel coordinates."""
    x = hex_size * 1.5 * c + hex_size * 0.75 * r
    y = -hex_size * math.sqrt(3) * (r + 0.5 * (c % 2 == 1) * 0) - hex_size * math.sqrt(3) / 2 * r
    # Simpler: offset coordinates
    x = c * 1.5 + r * 0.75
    y = -(r * math.sqrt(3) * 0.5 + c * 0.0)
    # Actually use axial-like offset:
    x = c + r * 0.5
    y = -r * math.sqrt(3) / 2
    return x, y


def _draw_hex_board(ax, board, size, hex_size=0.55,
                    highlights=None, win_path=None, neighbor_cell=None,
                    show_coords=False, edge_labels=True):
    """Draw a hex board on the given axes.

    board: 2D list (size x size), values 0=empty, 1=black, 2=white
    highlights: set of (r,c) to highlight (e.g. legal moves)
    win_path: list of (r,c) for winning path highlight
    neighbor_cell: (r,c) to highlight neighbors of
    """
    if highlights is None:
        highlights = set()
    if win_path is None:
        win_path = []
    win_set = set(win_path)

    for r in range(size):
        for c in range(size):
            x, y = _hex_to_pixel(r, c)

            # Determine fill color
            val = board[r][c]
            if (r, c) in win_set:
                fc = WIN_PATH_COLOR
            elif (r, c) in highlights:
                fc = HIGHLIGHT_COLOR
            elif val == 1:
                fc = BLACK_COLOR
            elif val == 2:
                fc = WHITE_COLOR
            else:
                fc = EMPTY_COLOR

            # Edge color for neighbor highlight
            ec = COLORS["dark"]
            lw = 1.0
            if neighbor_cell is not None:
                nr, nc = neighbor_cell
                if (r, c) == (nr, nc):
                    ec = COLORS["red"]
                    lw = 3.0
                elif _is_neighbor(r, c, nr, nc):
                    ec = NEIGHBOR_COLOR
                    lw = 2.5

            hex_patch = RegularPolygon((x, y), numVertices=6, radius=hex_size,
                                       orientation=0, facecolor=fc,
                                       edgecolor=ec, linewidth=lw)
            ax.add_patch(hex_patch)

            if show_coords:
                ax.text(x, y, f"({r},{c})", ha='center', va='center',
                        fontsize=7, color=COLORS["gray"])

    # Edge labels
    if edge_labels:
        # Top edge (Black)
        mid_c = (size - 1) / 2
        x_top, y_top = _hex_to_pixel(-0.8, mid_c)
        ax.text(x_top, y_top, "Negro ↕", ha='center', va='center',
                fontsize=10, fontweight='bold', color=BLACK_COLOR)
        # Bottom edge (Black)
        x_bot, y_bot = _hex_to_pixel(size - 0.2, mid_c)
        ax.text(x_bot, y_bot, "Negro ↕", ha='center', va='center',
                fontsize=10, fontweight='bold', color=BLACK_COLOR)
        # Left edge (White)
        mid_r = (size - 1) / 2
        x_left, y_left = _hex_to_pixel(mid_r, -0.9)
        ax.text(x_left, y_left, "Blanco\n↔", ha='center', va='center',
                fontsize=10, fontweight='bold', color=COLORS["gray"])
        # Right edge (White)
        x_right, y_right = _hex_to_pixel(mid_r, size - 0.1)
        ax.text(x_right, y_right, "Blanco\n↔", ha='center', va='center',
                fontsize=10, fontweight='bold', color=COLORS["gray"])

    ax.set_aspect('equal')
    ax.axis('off')
    # Set limits
    all_x = [_hex_to_pixel(r, c)[0] for r in range(size) for c in range(size)]
    all_y = [_hex_to_pixel(r, c)[1] for r in range(size) for c in range(size)]
    margin = 1.5
    ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
    ax.set_ylim(min(all_y) - margin, max(all_y) + margin)


def _is_neighbor(r1, c1, r2, c2):
    for dr, dc in Hex.NEIGHBORS:
        if r1 + dr == r2 and c1 + dc == c2:
            return True
    return False


# ---------------------------------------------------------------------------
# Plot functions: Hex board figures (01-06)
# ---------------------------------------------------------------------------

def plot_01_hex_empty_board():
    """Empty 7x7 hex board with edge labels."""
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    board = [[0] * 7 for _ in range(7)]
    _draw_hex_board(ax, board, 7, show_coords=True)
    ax.set_title("Tablero de Hex 7×7 vacío", fontsize=14, fontweight='bold')
    _save(fig, "01_hex_empty_board.png")


def plot_02_hex_neighbors():
    """Show neighbors of a central cell."""
    fig, ax = plt.subplots(1, 1, figsize=(8, 7))
    size = 5
    board = [[0] * size for _ in range(size)]
    _draw_hex_board(ax, board, size, neighbor_cell=(2, 2),
                    show_coords=True, edge_labels=False)
    ax.set_title("Los 6 vecinos de la celda (2,2)", fontsize=14, fontweight='bold')
    _save(fig, "02_hex_neighbors.png")


def plot_03_hex_legal_moves():
    """Mid-game board with legal moves highlighted."""
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    size = 7
    board = [[0] * size for _ in range(size)]
    # Place some stones for a mid-game position
    black_moves = [(0, 3), (1, 2), (1, 3), (2, 2), (3, 1), (3, 3), (4, 2)]
    white_moves = [(0, 5), (1, 5), (2, 4), (2, 5), (3, 4), (4, 4), (4, 5)]
    for r, c in black_moves:
        board[r][c] = 1
    for r, c in white_moves:
        board[r][c] = 2
    # Legal moves = empty cells
    legal = set()
    for r in range(size):
        for c in range(size):
            if board[r][c] == 0:
                legal.add((r, c))
    _draw_hex_board(ax, board, size, highlights=legal)
    ax.set_title("Posición a mitad de partida — celdas legales resaltadas",
                 fontsize=13, fontweight='bold')
    _save(fig, "03_hex_legal_moves.png")


def plot_04_hex_winning_path():
    """Completed game with winning path highlighted."""
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    size = 7
    # Play a scripted game where Black wins
    board = [[0] * size for _ in range(size)]
    black_path = [(0, 3), (1, 2), (2, 2), (3, 2), (4, 1), (5, 1), (6, 0)]
    other_black = [(0, 0), (1, 5), (3, 5), (5, 4)]
    white_stones = [(0, 4), (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3),
                    (0, 6), (2, 5), (4, 5)]
    for r, c in black_path + other_black:
        board[r][c] = 1
    for r, c in white_stones:
        board[r][c] = 2
    _draw_hex_board(ax, board, size, win_path=black_path)
    ax.set_title("Negro gana — cadena conectada de arriba a abajo",
                 fontsize=13, fontweight='bold')
    _save(fig, "04_hex_winning_path.png")


def plot_05_hex_3x3_games():
    """Two completed 3x3 games side by side."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Game 1: Black wins
    b1 = [[1, 2, 0],
           [2, 1, 0],
           [0, 2, 1]]
    win1 = [(0, 0), (1, 1), (2, 2)]
    _draw_hex_board(ax1, b1, 3, hex_size=0.8, win_path=win1, edge_labels=False)
    ax1.set_title("Negro gana (diagonal)", fontsize=12, fontweight='bold')

    # Game 2: White wins
    b2 = [[1, 2, 1],
           [0, 2, 1],
           [0, 2, 0]]
    win2 = [(0, 1), (1, 1), (2, 1)]
    _draw_hex_board(ax2, b2, 3, hex_size=0.8, win_path=win2, edge_labels=False)
    ax2.set_title("Blanco gana (columna central)", fontsize=12, fontweight='bold')

    fig.suptitle("Hex 3×3: dos partidas completas", fontsize=14, fontweight='bold')
    _save(fig, "05_hex_3x3_games.png")


def plot_06_hex_strategy():
    """Strategy patterns: bridge, ladder."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # Bridge pattern
    b_bridge = [[0]*5 for _ in range(5)]
    b_bridge[2][1] = 1
    b_bridge[2][3] = 1
    bridge_highlight = {(1, 2), (2, 2)}  # the two connecting cells
    _draw_hex_board(axes[0], b_bridge, 5, hex_size=0.5,
                    highlights=bridge_highlight, edge_labels=False)
    axes[0].set_title("Puente (bridge)", fontsize=11, fontweight='bold')

    # Ladder pattern
    b_ladder = [[0]*5 for _ in range(5)]
    b_ladder[0][2] = 1
    b_ladder[1][2] = 1
    b_ladder[2][1] = 1
    b_ladder[3][1] = 1
    b_ladder[4][0] = 1
    _draw_hex_board(axes[1], b_ladder, 5, hex_size=0.5, edge_labels=False)
    axes[1].set_title("Escalera (ladder)", fontsize=11, fontweight='bold')

    # Corner control
    b_corner = [[0]*5 for _ in range(5)]
    b_corner[0][0] = 1
    b_corner[0][4] = 1
    b_corner[4][0] = 1
    b_corner[4][4] = 1
    corner_hl = {(0, 0), (0, 4), (4, 0), (4, 4)}
    _draw_hex_board(axes[2], b_corner, 5, hex_size=0.5,
                    highlights=corner_hl, edge_labels=False)
    axes[2].set_title("Control de esquinas", fontsize=11, fontweight='bold')

    fig.suptitle("Patrones estratégicos en Hex", fontsize=14, fontweight='bold')
    _save(fig, "06_hex_strategy.png")


# ---------------------------------------------------------------------------
# Plot functions: MCTS algorithm figures (07-09)
# ---------------------------------------------------------------------------

def plot_07_mcts_four_phases():
    """Diagram showing the four MCTS phases."""
    fig, axes = plt.subplots(1, 4, figsize=(16, 5))
    phase_names = ["1. Selección", "2. Expansión", "3. Simulación", "4. Retropropagación"]
    phase_colors = [COLORS["blue"], COLORS["green"], COLORS["orange"], COLORS["purple"]]
    phase_desc = [
        "Bajar por el árbol\nusando UCT",
        "Añadir un\nnodo nuevo",
        "Rollout aleatorio\nhasta terminal",
        "Actualizar N y Q\nhacia la raíz"
    ]

    for i, ax in enumerate(axes):
        # Draw a simple tree
        nodes = [(0.5, 0.9), (0.3, 0.6), (0.7, 0.6),
                 (0.15, 0.3), (0.45, 0.3), (0.55, 0.3), (0.85, 0.3)]
        edges = [(0, 1), (0, 2), (1, 3), (1, 4), (2, 5), (2, 6)]

        for p, ch in edges:
            ax.plot([nodes[p][0], nodes[ch][0]], [nodes[p][1], nodes[ch][1]],
                    'k-', linewidth=1, alpha=0.3)

        for j, (x, y) in enumerate(nodes):
            color = COLORS["light"]
            if i == 0 and j in [0, 1, 3]:  # selection path
                color = phase_colors[i]
            elif i == 1 and j == 4:  # new node
                color = phase_colors[i]
            elif i == 3 and j in [0, 1, 4]:  # backprop path
                color = phase_colors[i]
            ax.plot(x, y, 'o', markersize=18, color=color,
                    markeredgecolor=COLORS["dark"], markeredgewidth=1.5)

        if i == 0:  # Selection arrow
            ax.annotate('', xy=(0.15, 0.32), xytext=(0.5, 0.88),
                        arrowprops=dict(arrowstyle='->', color=phase_colors[i],
                                       lw=2.5))
        elif i == 1:  # New node
            ax.plot(0.45, 0.3, 'o', markersize=18, color=phase_colors[i],
                    markeredgecolor=COLORS["dark"], markeredgewidth=2)
            ax.text(0.45, 0.15, "nuevo", ha='center', fontsize=8, color=phase_colors[i])
        elif i == 2:  # Rollout squiggly line
            xs = np.linspace(0.45, 0.45, 10)
            ys = np.linspace(0.28, 0.05, 10)
            xs = xs + np.random.uniform(-0.05, 0.05, 10)
            ax.plot(xs, ys, '--', color=phase_colors[i], linewidth=2)
            ax.text(0.45, 0.0, "terminal", ha='center', fontsize=8,
                    color=phase_colors[i])
        elif i == 3:  # Backprop arrow
            ax.annotate('', xy=(0.5, 0.88), xytext=(0.45, 0.32),
                        arrowprops=dict(arrowstyle='->', color=phase_colors[i],
                                       lw=2.5))

        ax.set_xlim(-0.05, 1.05)
        ax.set_ylim(-0.1, 1.05)
        ax.set_title(phase_names[i], fontsize=11, fontweight='bold',
                     color=phase_colors[i])
        ax.text(0.5, -0.07, phase_desc[i], ha='center', va='top',
                fontsize=9, color=COLORS["gray"])
        ax.axis('off')

    fig.suptitle("Las cuatro fases de MCTS", fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    _save(fig, "07_mcts_four_phases.png")


def plot_08_mcts_tree_growth():
    """Tree size after 10, 50, 200 iterations on Hex 3x3."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    iters_list = [10, 50, 200]

    for idx, iters in enumerate(iters_list):
        random.seed(42)
        state = Hex(3)
        _, root = _run_mcts(state, iters, 1, c=1.41)

        # Count tree stats
        def _count(node, depth=0):
            total = 1
            max_d = depth
            for ch in node.children.values():
                t, d = _count(ch, depth + 1)
                total += t
                max_d = max(max_d, d)
            return total, max_d

        total_nodes, max_depth = _count(root)

        # Draw simple bar chart of root children visits
        actions = sorted(root.children.keys())
        visits = [root.children[a].N for a in actions]
        values = [root.children[a].Q / root.children[a].N if root.children[a].N > 0 else 0
                  for a in actions]
        labels = [f"({r},{c})" for r, c in actions]

        colors = [COLORS["blue"] if v > 0 else COLORS["red"] for v in values]
        axes[idx].bar(range(len(actions)), visits, color=colors, alpha=0.8,
                      edgecolor=COLORS["dark"])
        axes[idx].set_xticks(range(len(actions)))
        axes[idx].set_xticklabels(labels, rotation=45, fontsize=8)
        axes[idx].set_ylabel("Visitas N(v)")
        axes[idx].set_title(f"M = {iters} iteraciones\n({total_nodes} nodos, "
                           f"prof. máx. {max_depth})",
                           fontsize=11, fontweight='bold')

    fig.suptitle("Crecimiento del árbol MCTS en Hex 3×3",
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    _save(fig, "08_mcts_tree_growth.png")


def plot_09_mcts_trace():
    """Visual trace of MCTS iterations."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 6))
    random.seed(42)
    state = Hex(3)

    # Run 30 iterations and track root children stats
    iterations = 30
    root = MCTSNode(state)
    history = {a: [] for a in state.actions()}

    for it in range(1, iterations + 1):
        node = root
        while not node.unexpanded and node.children:
            node = max(node.children.values(),
                       key=lambda ch: _uct_value(ch, node.N, 1.41))
        if node.unexpanded:
            action = node.unexpanded.pop()
            child_state = node.state.result(action)
            child = MCTSNode(child_state, parent=node)
            node.children[action] = child
            node = child
        sim = Hex(node.state.size, node.state.board, node.state.current_player)
        while not sim.is_terminal():
            acts = sim.actions()
            sim = sim.result(acts[random.randint(0, len(acts) - 1)])
        reward = sim.utility(1)
        while node is not None:
            node.N += 1
            node.Q += reward
            node = node.parent

        for a in state.actions():
            if a in root.children:
                history[a].append(root.children[a].N)
            else:
                history[a].append(0)

    # Plot visit counts over iterations
    color_cycle = [COLORS["blue"], COLORS["red"], COLORS["green"],
                   COLORS["orange"], COLORS["purple"], COLORS["teal"],
                   COLORS["pink"], COLORS["gray"], COLORS["dark"]]
    for i, a in enumerate(sorted(history.keys())):
        ax.plot(range(1, iterations + 1), history[a],
                label=f"({a[0]},{a[1]})", color=color_cycle[i % len(color_cycle)],
                linewidth=2, alpha=0.8)

    ax.set_xlabel("Iteración", fontsize=12)
    ax.set_ylabel("Visitas acumuladas N(v)", fontsize=12)
    ax.set_title("Traza MCTS: visitas a cada acción de la raíz (Hex 3×3)",
                 fontsize=13, fontweight='bold')
    ax.legend(ncol=3, fontsize=9, title="Acción", title_fontsize=10)
    _save(fig, "09_mcts_trace.png")


# ---------------------------------------------------------------------------
# Plot functions: UCT figures (10-11)
# ---------------------------------------------------------------------------

def plot_10_uct_vs_uniform():
    """Compare UCT vs naive selection on Hex 3x3."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    for ax, title, runner in [
        (ax1, "Naive (mayor Q/N)", lambda s, it, p: _run_mcts_naive(s, it, p)),
        (ax2, "UCT (c = √2)", lambda s, it, p: _run_mcts(s, it, p, c=1.41))
    ]:
        random.seed(42)
        state = Hex(3)
        _, root = runner(state, 500, 1)
        actions = sorted(root.children.keys())
        visits = [root.children[a].N for a in actions]
        qn = [root.children[a].Q / root.children[a].N if root.children[a].N > 0 else 0
              for a in actions]
        labels = [f"({r},{c})" for r, c in actions]
        colors = [COLORS["blue"] if v > 0 else COLORS["red"] for v in qn]
        ax.bar(range(len(actions)), visits, color=colors, alpha=0.8,
               edgecolor=COLORS["dark"])
        ax.set_xticks(range(len(actions)))
        ax.set_xticklabels(labels, rotation=45, fontsize=9)
        ax.set_ylabel("Visitas N(v)")
        ax.set_title(title, fontsize=12, fontweight='bold')
        # Annotate Q/N on top
        for j, (v, q) in enumerate(zip(visits, qn)):
            ax.text(j, v + 2, f"{q:.2f}", ha='center', fontsize=8, color=COLORS["gray"])

    fig.suptitle("Selección UCT vs Naive — 500 iteraciones en Hex 3×3",
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    _save(fig, "10_uct_vs_uniform.png")


def plot_11_uct_c_effect():
    """Win rate vs exploration constant c on Hex 5x5."""
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))

    c_values = [0.1, 0.25, 0.5, 0.75, 1.0, 1.41, 2.0, 3.0, 5.0]
    n_games = 40
    iters_per_move = 200
    win_rates = []

    for c in c_values:
        wins = 0
        for g in range(n_games):
            random.seed(g * 100)
            result = _play_game(5, _mcts_agent(iters_per_move, c), _random_agent)
            if result == 1:
                wins += 1
        win_rates.append(wins / n_games)
        print(f"  c={c:.2f}: {wins}/{n_games} wins")

    ax.plot(c_values, win_rates, 'o-', color=COLORS["blue"], linewidth=2.5,
            markersize=8, markerfacecolor=COLORS["blue"])
    ax.axvline(x=1.41, color=COLORS["red"], linestyle='--', alpha=0.7,
               label=f"c = √2 ≈ 1.41")
    ax.set_xlabel("Constante de exploración c", fontsize=12)
    ax.set_ylabel("Tasa de victorias vs aleatorio", fontsize=12)
    ax.set_title("Efecto de c en MCTS con UCT (Hex 5×5, 200 iter/movimiento)",
                 fontsize=13, fontweight='bold')
    ax.legend(fontsize=11)
    ax.set_ylim(0, 1.05)
    _save(fig, "11_uct_c_effect.png")


# ---------------------------------------------------------------------------
# Plot functions: Experiment figures (12-15)
# ---------------------------------------------------------------------------

def plot_12_mcts_vs_minimax_3x3():
    """MCTS convergence to minimax value on Hex 3x3."""
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))

    state = Hex(3)
    # Get exact minimax value
    mm_val, mm_act = _minimax(state, 1)

    # Run MCTS with increasing iterations
    iter_values = [10, 20, 50, 100, 200, 500, 1000]
    n_trials = 30
    estimates = {it: [] for it in iter_values}

    for it in iter_values:
        for trial in range(n_trials):
            random.seed(trial * 7)
            _, root = _run_mcts(state, it, 1, c=1.41)
            # Best action's Q/N
            if root.children:
                best_a = max(root.children, key=lambda a: root.children[a].N)
                best_qn = root.children[best_a].Q / root.children[best_a].N
                estimates[it].append(best_qn)

    means = [np.mean(estimates[it]) for it in iter_values]
    stds = [np.std(estimates[it]) for it in iter_values]

    ax.errorbar(iter_values, means, yerr=stds, fmt='o-', color=COLORS["blue"],
                linewidth=2, markersize=8, capsize=5, label="MCTS estimado")
    ax.axhline(y=mm_val, color=COLORS["red"], linestyle='--', linewidth=2,
               label=f"Minimax exacto = {mm_val}")
    ax.set_xscale('log')
    ax.set_xlabel("Iteraciones M", fontsize=12)
    ax.set_ylabel("Valor estimado (Q/N de la mejor acción)", fontsize=12)
    ax.set_title("Convergencia de MCTS al valor minimax (Hex 3×3)",
                 fontsize=13, fontweight='bold')
    ax.legend(fontsize=11)
    _save(fig, "12_mcts_vs_minimax_3x3.png")


def plot_13_tournament_results():
    """Tournament results: MCTS vs alpha-beta vs random on Hex 5x5."""
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))

    agents = {
        "MCTS (UCT)": _mcts_agent(300, 1.41),
        "Alpha-beta (d=3)": _alphabeta_agent(3),
        "Aleatorio": _random_agent,
    }
    agent_names = list(agents.keys())
    n_games = 20  # per matchup per side
    results = {name: 0 for name in agent_names}

    print("  Torneo en Hex 5×5...")
    for i, name1 in enumerate(agent_names):
        for j, name2 in enumerate(agent_names):
            if i >= j:
                continue
            wins1, wins2 = 0, 0
            for g in range(n_games):
                random.seed(g * 31 + i * 7 + j * 13)
                r = _play_game(5, agents[name1], agents[name2])
                if r == 1:
                    wins1 += 1
                else:
                    wins2 += 1
            for g in range(n_games):
                random.seed(g * 31 + i * 7 + j * 13 + 1000)
                r = _play_game(5, agents[name2], agents[name1])
                if r == 1:
                    wins2 += 1
                else:
                    wins1 += 1
            results[name1] += wins1
            results[name2] += wins2
            print(f"    {name1} vs {name2}: {wins1}-{wins2}")

    # Bar chart
    colors_bar = [COLORS["blue"], COLORS["orange"], COLORS["gray"]]
    bars = ax.bar(agent_names, [results[n] for n in agent_names],
                  color=colors_bar, edgecolor=COLORS["dark"], alpha=0.85)
    for bar, name in zip(bars, agent_names):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                str(results[name]), ha='center', fontsize=12, fontweight='bold')
    ax.set_ylabel("Victorias totales", fontsize=12)
    ax.set_title("Torneo round-robin en Hex 5×5", fontsize=14, fontweight='bold')
    _save(fig, "13_tournament_results.png")


def plot_14_iteration_budget():
    """Win rate vs iteration budget on Hex 5x5."""
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))

    budgets = [50, 100, 200, 500, 1000]
    n_games = 30
    wr_vs_random = []
    wr_vs_ab = []

    ab_agent = _alphabeta_agent(3)

    for budget in budgets:
        wins_r, wins_ab = 0, 0
        for g in range(n_games):
            random.seed(g * 17)
            if _play_game(5, _mcts_agent(budget), _random_agent) == 1:
                wins_r += 1
            random.seed(g * 17 + 5000)
            if _play_game(5, _mcts_agent(budget), ab_agent) == 1:
                wins_ab += 1
        wr_vs_random.append(wins_r / n_games)
        wr_vs_ab.append(wins_ab / n_games)
        print(f"  budget={budget}: vs_random={wins_r}/{n_games}, vs_ab={wins_ab}/{n_games}")

    ax.plot(budgets, wr_vs_random, 'o-', color=COLORS["green"], linewidth=2.5,
            markersize=8, label="vs Aleatorio")
    ax.plot(budgets, wr_vs_ab, 's-', color=COLORS["red"], linewidth=2.5,
            markersize=8, label="vs Alpha-beta (d=3)")
    ax.set_xlabel("Iteraciones por movimiento", fontsize=12)
    ax.set_ylabel("Tasa de victorias MCTS", fontsize=12)
    ax.set_title("Calidad de MCTS vs presupuesto de iteraciones (Hex 5×5)",
                 fontsize=13, fontweight='bold')
    ax.legend(fontsize=11)
    ax.set_ylim(0, 1.05)
    _save(fig, "14_iteration_budget.png")


def plot_15_asymmetric_tree():
    """Visualize asymmetric MCTS tree as visit distribution."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 6))

    random.seed(42)
    state = Hex(5)
    _, root = _run_mcts(state, 1000, 1, c=1.41)

    # Get depth-1 children sorted by visits
    actions = sorted(root.children.keys(), key=lambda a: root.children[a].N, reverse=True)
    visits = [root.children[a].N for a in actions]
    labels = [f"({r},{c})" for r, c in actions]

    # Color by Q/N value
    qn_vals = [root.children[a].Q / root.children[a].N if root.children[a].N > 0 else 0
               for a in actions]
    norm = plt.Normalize(vmin=min(qn_vals) - 0.1, vmax=max(qn_vals) + 0.1)
    cmap = plt.cm.RdYlGn
    colors_mapped = [cmap(norm(v)) for v in qn_vals]

    bars = ax.bar(range(len(actions)), visits, color=colors_mapped,
                  edgecolor=COLORS["dark"], alpha=0.85)
    ax.set_xticks(range(len(actions)))
    ax.set_xticklabels(labels, rotation=60, fontsize=8)
    ax.set_ylabel("Visitas N(v)", fontsize=12)
    ax.set_xlabel("Acción desde la raíz", fontsize=12)
    ax.set_title("Árbol asimétrico: distribución de visitas (Hex 5×5, 1000 iter.)",
                 fontsize=13, fontweight='bold')
    # Add colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, shrink=0.8)
    cbar.set_label("Q/N (tasa de éxito)", fontsize=10)
    _save(fig, "15_asymmetric_tree.png")


# ---------------------------------------------------------------------------
# Plot functions: AlphaZero figures (16-17)
# ---------------------------------------------------------------------------

def plot_16_algorithm_evolution():
    """Timeline of game AI evolution."""
    fig, ax = plt.subplots(1, 1, figsize=(14, 5))

    systems = [
        (1997, "Deep Blue", "Alpha-beta\n+ eval manual", COLORS["gray"]),
        (2008, "Stockfish", "Alpha-beta\n+ NNUE", COLORS["blue"]),
        (2016, "AlphaGo", "MCTS\n+ redes (datos\nhumanos)", COLORS["green"]),
        (2018, "AlphaZero", "MCTS\n+ red (auto-\njuego)", COLORS["orange"]),
    ]

    for year, name, desc, color in systems:
        ax.plot(year, 0.5, 'o', markersize=25, color=color,
                markeredgecolor=COLORS["dark"], markeredgewidth=2, zorder=5)
        ax.text(year, 0.8, name, ha='center', va='bottom',
                fontsize=13, fontweight='bold', color=color)
        ax.text(year, 0.15, desc, ha='center', va='top',
                fontsize=9, color=COLORS["dark"])
        ax.text(year, -0.15, str(year), ha='center', va='top',
                fontsize=11, fontweight='bold', color=COLORS["gray"])

    # Timeline line
    ax.plot([1995, 2020], [0.5, 0.5], '-', color=COLORS["gray"],
            linewidth=2, alpha=0.3, zorder=1)
    # Arrows between
    for i in range(len(systems) - 1):
        ax.annotate('', xy=(systems[i+1][0] - 0.5, 0.5),
                    xytext=(systems[i][0] + 0.5, 0.5),
                    arrowprops=dict(arrowstyle='->', color=COLORS["gray"],
                                   lw=1.5, alpha=0.5))

    ax.set_xlim(1994, 2021)
    ax.set_ylim(-0.4, 1.2)
    ax.axis('off')
    ax.set_title("Evolución de la IA en juegos", fontsize=14, fontweight='bold')
    _save(fig, "16_algorithm_evolution.png")


def plot_17_rollout_convergence():
    """Rollout estimate convergence with increasing N."""
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))

    # Mid-game position on Hex 3x3
    state = Hex(3)
    state = state.result((1, 1))  # Black center

    n_values = list(range(1, 201))
    n_trials = 20
    all_estimates = []

    for trial in range(n_trials):
        random.seed(trial * 13)
        estimates = []
        cumsum = 0
        for n in n_values:
            # One rollout
            sim = Hex(state.size, state.board, state.current_player)
            while not sim.is_terminal():
                acts = sim.actions()
                sim = sim.result(acts[random.randint(0, len(acts) - 1)])
            cumsum += sim.utility(1)
            estimates.append(cumsum / n)
        all_estimates.append(estimates)

    all_estimates = np.array(all_estimates)
    mean_est = all_estimates.mean(axis=0)
    std_est = all_estimates.std(axis=0)

    # Plot individual trials faintly
    for trial in range(min(5, n_trials)):
        ax.plot(n_values, all_estimates[trial], alpha=0.2, color=COLORS["blue"],
                linewidth=0.8)

    ax.plot(n_values, mean_est, color=COLORS["blue"], linewidth=2.5,
            label="Media de 20 experimentos")
    ax.fill_between(n_values, mean_est - std_est, mean_est + std_est,
                    alpha=0.15, color=COLORS["blue"])

    ax.axhline(y=0, color=COLORS["gray"], linestyle=':', alpha=0.5)
    ax.set_xlabel("Número de rollouts N", fontsize=12)
    ax.set_ylabel("Estimación del valor", fontsize=12)
    ax.set_title("Convergencia del estimador por rollouts (Hex 3×3, Negro en centro)",
                 fontsize=13, fontweight='bold')
    ax.legend(fontsize=11)
    _save(fig, "17_rollout_convergence.png")


def plot_18_eval_vs_rollout():
    """Compare heuristic eval vs rollout estimate across positions."""
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))

    # Generate several positions on Hex 3x3 by random play
    positions = []
    for seed in range(50):
        random.seed(seed)
        state = Hex(3)
        depth = random.randint(1, 5)
        for _ in range(depth):
            if state.is_terminal():
                break
            acts = state.actions()
            state = state.result(acts[random.randint(0, len(acts) - 1)])
        if not state.is_terminal():
            positions.append(state)

    # Heuristic eval: count stones difference
    heuristic_vals = []
    rollout_vals = []

    for pos in positions:
        # Simple heuristic: (black stones - white stones) / total
        b_count = sum(1 for r in range(pos.size) for c in range(pos.size)
                      if pos.board[r][c] == 1)
        w_count = sum(1 for r in range(pos.size) for c in range(pos.size)
                      if pos.board[r][c] == 2)
        heuristic_vals.append((b_count - w_count) / pos.size**2)

        # Rollout average (100 rollouts)
        total = 0
        for _ in range(100):
            sim = Hex(pos.size, pos.board, pos.current_player)
            while not sim.is_terminal():
                acts = sim.actions()
                sim = sim.result(acts[random.randint(0, len(acts) - 1)])
            total += sim.utility(1)
        rollout_vals.append(total / 100)

    ax.scatter(heuristic_vals, rollout_vals, color=COLORS["blue"], alpha=0.6,
               s=60, edgecolor=COLORS["dark"], linewidth=0.5)
    ax.axhline(y=0, color=COLORS["gray"], linestyle=':', alpha=0.5)
    ax.axvline(x=0, color=COLORS["gray"], linestyle=':', alpha=0.5)

    # Trend line
    z = np.polyfit(heuristic_vals, rollout_vals, 1)
    p = np.poly1d(z)
    x_line = np.linspace(min(heuristic_vals), max(heuristic_vals), 100)
    ax.plot(x_line, p(x_line), '--', color=COLORS["red"], linewidth=1.5,
            alpha=0.7, label=f"Tendencia lineal")

    ax.set_xlabel("Evaluación heurística (diferencia de piedras)", fontsize=12)
    ax.set_ylabel("Evaluación por rollouts (100 por posición)", fontsize=12)
    ax.set_title("Heurística vs rollouts en distintas posiciones (Hex 3×3)",
                 fontsize=13, fontweight='bold')
    ax.legend(fontsize=11)
    _save(fig, "18_eval_vs_rollout.png")


# ---------------------------------------------------------------------------
# UCT formula breakdown (09)
# ---------------------------------------------------------------------------

def plot_09b_uct_formula():
    """Visual breakdown of the UCT formula."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 4))

    ax.text(0.5, 0.75, r"$\mathrm{UCT}(v) = $", fontsize=22, ha='right', va='center',
            transform=ax.transAxes)

    # Exploitation box
    rect1 = mpatches.FancyBboxPatch((0.51, 0.55), 0.15, 0.4,
                                     boxstyle="round,pad=0.02",
                                     facecolor=COLORS["blue"], alpha=0.15,
                                     edgecolor=COLORS["blue"], linewidth=2,
                                     transform=ax.transAxes)
    ax.add_patch(rect1)
    ax.text(0.585, 0.75, r"$\frac{Q(v)}{N(v)}$", fontsize=22, ha='center', va='center',
            transform=ax.transAxes, color=COLORS["blue"])
    ax.text(0.585, 0.35, "Explotación\n(tasa de éxito)", fontsize=10, ha='center',
            va='top', transform=ax.transAxes, color=COLORS["blue"])

    ax.text(0.69, 0.75, r"$+$", fontsize=22, ha='center', va='center',
            transform=ax.transAxes)

    # Exploration box
    rect2 = mpatches.FancyBboxPatch((0.72, 0.55), 0.25, 0.4,
                                     boxstyle="round,pad=0.02",
                                     facecolor=COLORS["green"], alpha=0.15,
                                     edgecolor=COLORS["green"], linewidth=2,
                                     transform=ax.transAxes)
    ax.add_patch(rect2)
    ax.text(0.845, 0.75, r"$c\sqrt{\frac{\ln N(\mathrm{padre})}{N(v)}}$",
            fontsize=22, ha='center', va='center',
            transform=ax.transAxes, color=COLORS["green"])
    ax.text(0.845, 0.35, "Exploración\n(bonus para poco visitados)", fontsize=10,
            ha='center', va='top', transform=ax.transAxes, color=COLORS["green"])

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    ax.set_title("Descomposición de la fórmula UCT", fontsize=14, fontweight='bold')
    _save(fig, "09_uct_formula.png")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generando imágenes para el módulo 18 (Monte Carlo Tree Search)...\n")

    # Hex board figures
    plot_01_hex_empty_board()
    plot_02_hex_neighbors()
    plot_03_hex_legal_moves()
    plot_04_hex_winning_path()
    plot_05_hex_3x3_games()
    plot_06_hex_strategy()

    # MCTS algorithm figures
    plot_07_mcts_four_phases()
    plot_08_mcts_tree_growth()
    plot_09_mcts_trace()
    plot_09b_uct_formula()

    # UCT figures
    plot_10_uct_vs_uniform()
    plot_11_uct_c_effect()

    # Experiment figures
    plot_12_mcts_vs_minimax_3x3()
    plot_13_tournament_results()
    plot_14_iteration_budget()
    plot_15_asymmetric_tree()

    # AlphaZero figures
    plot_16_algorithm_evolution()

    # Rollout figures
    plot_17_rollout_convergence()
    plot_18_eval_vs_rollout()

    print(f"\n✓  Todas las imágenes generadas en {IMAGES_DIR}/")


if __name__ == "__main__":
    main()
