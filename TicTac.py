from __future__ import annotations

import json
import math
import os
import random
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

APP_NAME = "ULTIMATE TIC-TAC-TOE"
STATS_FILE = "tic_tac_toe_stats.json"
HISTORY_FILE = "tic_tac_toe_history.json"

EMPTY = ""
X = "X"
O = "O"
DRAW = "DRAW"

RESET = "\033[0m"
RED = "\033[91m"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"
GRAY = "\033[90m"
BOLD = "\033[1m"


# ─────────────────────────────────────────────────────────────────────────────
# Utility functions
# ─────────────────────────────────────────────────────────────────────────────

def supports_color() -> bool:
    """Return whether the terminal probably supports ANSI colors."""
    if os.getenv("NO_COLOR"):
        return False
    return sys.stdout.isatty() or os.name != "nt"


USE_COLOR = supports_color()


def paint(text: str, code: str) -> str:
    """Color text when terminal coloring is available."""
    if not USE_COLOR:
        return text
    return f"{code}{text}{RESET}"


def clear_screen() -> None:
    """Clear the terminal screen."""
    command = "cls" if os.name == "nt" else "clear"
    os.system(command)


def pause(message: str = "Press Enter to continue...") -> None:
    input(f"\n{message}")


def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def other_symbol(symbol: str) -> str:
    return O if symbol == X else X


def safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ─────────────────────────────────────────────────────────────────────────────
# Data models
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Player:
    name: str
    symbol: str
    is_computer: bool = False


@dataclass
class GameSettings:
    board_size: int = 3
    mode: str = "computer"
    difficulty: str = "impossible"
    starting_symbol: str = X
    show_coordinates: bool = True
    animations: bool = True


@dataclass
class MatchRecord:
    date: str
    mode: str
    board_size: int
    difficulty: str
    player_x: str
    player_o: str
    result: str
    moves: int


@dataclass
class Statistics:
    total_games: int = 0
    x_wins: int = 0
    o_wins: int = 0
    draws: int = 0
    human_wins: int = 0
    computer_wins: int = 0
    fastest_win_moves: Optional[int] = None
    longest_game_moves: int = 0

    def record(
        self,
        result: str,
        mode: str,
        winner_is_computer: bool,
        move_count: int,
    ) -> None:
        self.total_games += 1

        if result == X:
            self.x_wins += 1
        elif result == O:
            self.o_wins += 1
        elif result == DRAW:
            self.draws += 1

        if result in (X, O):
            if winner_is_computer:
                self.computer_wins += 1
            elif mode == "computer":
                self.human_wins += 1

            if self.fastest_win_moves is None:
                self.fastest_win_moves = move_count
            else:
                self.fastest_win_moves = min(
                    self.fastest_win_moves,
                    move_count,
                )

        self.longest_game_moves = max(
            self.longest_game_moves,
            move_count,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Persistence
# ─────────────────────────────────────────────────────────────────────────────

def load_statistics() -> Statistics:
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        valid_fields = Statistics.__dataclass_fields__
        cleaned = {
            key: data.get(key)
            for key in valid_fields
            if key in data
        }

        return Statistics(**cleaned)

    except (
        OSError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
    ):
        return Statistics()


def save_statistics(stats: Statistics) -> None:
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as file:
            json.dump(asdict(stats), file, indent=2)
    except OSError:
        pass


def load_history() -> List[MatchRecord]:
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return [
            MatchRecord(**record)
            for record in data
            if isinstance(record, dict)
        ]

    except (
        OSError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
    ):
        return []


def save_history(history: List[MatchRecord]) -> None:
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as file:
            json.dump(
                [asdict(record) for record in history],
                file,
                indent=2,
            )
    except OSError:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Board implementation
# ─────────────────────────────────────────────────────────────────────────────

class Board:
    """
    Generalized Tic-Tac-Toe board.

    A player wins when they occupy an entire row, column, or diagonal.
    For example, a 4x4 board requires four symbols in a line.
    """

    def __init__(self, size: int = 3) -> None:
        if size not in (3, 4, 5):
            raise ValueError("Board size must be 3, 4, or 5.")

        self.size = size
        self.cells: List[str] = [EMPTY] * (size * size)

    @property
    def area(self) -> int:
        return self.size * self.size

    def copy(self) -> "Board":
        new_board = Board(self.size)
        new_board.cells = self.cells.copy()
        return new_board

    def is_full(self) -> bool:
        return EMPTY not in self.cells

    def available_moves(self) -> List[int]:
        return [
            index
            for index, cell in enumerate(self.cells)
            if cell == EMPTY
        ]

    def is_valid_move(self, index: int) -> bool:
        return (
            0 <= index < self.area
            and self.cells[index] == EMPTY
        )

    def place(self, index: int, symbol: str) -> bool:
        if not self.is_valid_move(index):
            return False

        self.cells[index] = symbol
        return True

    def undo(self, index: int) -> None:
        if 0 <= index < self.area:
            self.cells[index] = EMPTY

    def coordinates(self, index: int) -> Tuple[int, int]:
        return divmod(index, self.size)

    def index_at(self, row: int, column: int) -> int:
        return row * self.size + column

    def winning_lines(self) -> List[List[int]]:
        lines: List[List[int]] = []

        for row in range(self.size):
            lines.append([
                self.index_at(row, column)
                for column in range(self.size)
            ])

        for column in range(self.size):
            lines.append([
                self.index_at(row, column)
                for row in range(self.size)
            ])

        lines.append([
            self.index_at(index, index)
            for index in range(self.size)
        ])

        lines.append([
            self.index_at(index, self.size - index - 1)
            for index in range(self.size)
        ])

        return lines

    def winner(self) -> Optional[str]:
        for line in self.winning_lines():
            symbols = [self.cells[index] for index in line]

            if symbols[0] != EMPTY and all(
                symbol == symbols[0]
                for symbol in symbols
            ):
                return symbols[0]

        return None

    def result(self) -> Optional[str]:
        winning_symbol = self.winner()

        if winning_symbol:
            return winning_symbol

        if self.is_full():
            return DRAW

        return None

    def winning_line(self) -> Optional[List[int]]:
        for line in self.winning_lines():
            symbols = [self.cells[index] for index in line]

            if symbols[0] != EMPTY and all(
                symbol == symbols[0]
                for symbol in symbols
            ):
                return line

        return None


# ─────────────────────────────────────────────────────────────────────────────
# Board rendering
# ─────────────────────────────────────────────────────────────────────────────

def symbol_display(symbol: str, winning: bool = False) -> str:
    if symbol == X:
        value = paint(" X ", RED)
    elif symbol == O:
        value = paint(" O ", BLUE)
    else:
        value = "   "

    if winning:
        return paint(value, GREEN)

    return value


def position_display(index: int, width: int) -> str:
    return paint(
        str(index + 1).center(width),
        GRAY,
    )


def render_board(
    board: Board,
    highlight: Optional[List[int]] = None,
    show_coordinates: bool = True,
) -> str:
    highlight_set = set(highlight or [])
    width = max(3, len(str(board.area)) + 2)
    separator = "+".join("-" * width for _ in range(board.size))

    rows = []

    for row in range(board.size):
        cells = []

        for column in range(board.size):
            index = board.index_at(row, column)
            value = board.cells[index]

            if value == EMPTY and show_coordinates:
                cell = position_display(index, width)
            else:
                cell = symbol_display(
                    value,
                    winning=index in highlight_set,
                )

            cells.append(cell.center(width))

        rows.append("|".join(cells))

    return f"\n{separator}\n".join(rows)


def print_header(title: str = APP_NAME) -> None:
    width = max(42, len(title) + 10)
    border = "═" * width

    print(paint(f"╔{border}╗", CYAN))
    print(paint(f"║{title.center(width)}║", CYAN))
    print(paint(f"╚{border}╝", CYAN))


# ─────────────────────────────────────────────────────────────────────────────
# AI implementation
# ─────────────────────────────────────────────────────────────────────────────

class AI:
    def __init__(self, difficulty: str) -> None:
        self.difficulty = difficulty

    def choose_move(self, board: Board, symbol: str) -> int:
        if self.difficulty == "easy":
            return self.easy_move(board)

        if self.difficulty == "medium":
            return self.medium_move(board, symbol)

        if board.size == 3:
            return self.perfect_move(board, symbol)

        return self.strong_move(board, symbol)

    @staticmethod
    def easy_move(board: Board) -> int:
        return random.choice(board.available_moves())

    @staticmethod
    def immediate_winning_move(
        board: Board,
        symbol: str,
    ) -> Optional[int]:
        for move in board.available_moves():
            board.place(move, symbol)

            if board.winner() == symbol:
                board.undo(move)
                return move

            board.undo(move)

        return None

    def medium_move(self, board: Board, symbol: str) -> int:
        opponent = other_symbol(symbol)

        winning_move = self.immediate_winning_move(board, symbol)
        if winning_move is not None:
            return winning_move

        blocking_move = self.immediate_winning_move(board, opponent)
        if blocking_move is not None:
            return blocking_move

        center = board.area // 2
        if board.is_valid_move(center):
            return center

        corners = [
            0,
            board.size - 1,
            board.area - board.size,
            board.area - 1,
        ]
        available_corners = [
            move
            for move in corners
            if board.is_valid_move(move)
        ]

        if available_corners:
            return random.choice(available_corners)

        return random.choice(board.available_moves())

    def perfect_move(self, board: Board, symbol: str) -> int:
        best_score = -math.inf
        best_moves: List[int] = []

        for move in board.available_moves():
            board.place(move, symbol)
            score = self.minimax(
                board=board,
                ai_symbol=symbol,
                turn=other_symbol(symbol),
                depth=0,
                alpha=-math.inf,
                beta=math.inf,
            )
            board.undo(move)

            if score > best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)

        return random.choice(best_moves)

    def minimax(
        self,
        board: Board,
        ai_symbol: str,
        turn: str,
        depth: int,
        alpha: float,
        beta: float,
    ) -> int:
        result = board.result()
        opponent = other_symbol(ai_symbol)

        if result == ai_symbol:
            return 10 - depth

        if result == opponent:
            return depth - 10

        if result == DRAW:
            return 0

        maximizing = turn == ai_symbol

        if maximizing:
            best_score = -math.inf

            for move in board.available_moves():
                board.place(move, turn)

                score = self.minimax(
                    board=board,
                    ai_symbol=ai_symbol,
                    turn=opponent,
                    depth=depth + 1,
                    alpha=alpha,
                    beta=beta,
                )

                board.undo(move)
                best_score = max(best_score, score)
                alpha = max(alpha, best_score)

                if beta <= alpha:
                    break

            return int(best_score)

        best_score = math.inf

        for move in board.available_moves():
            board.place(move, turn)

            score = self.minimax(
                board=board,
                ai_symbol=ai_symbol,
                turn=ai_symbol,
                depth=depth + 1,
                alpha=alpha,
                beta=beta,
            )

            board.undo(move)
            best_score = min(best_score, score)
            beta = min(beta, best_score)

            if beta <= alpha:
                break

        return int(best_score)

    def strong_move(self, board: Board, symbol: str) -> int:
        """
        Heuristic AI for 4x4 and 5x5 boards.

        It prioritizes:
        1. Winning immediately.
        2. Blocking the opponent.
        3. Center squares.
        4. Moves that create multiple threats.
        5. Random choice among tied moves.
        """
        opponent = other_symbol(symbol)

        winning = self.immediate_winning_move(board, symbol)
        if winning is not None:
            return winning

        blocking = self.immediate_winning_move(board, opponent)
        if blocking is not None:
            return blocking

        best_score = -math.inf
        best_moves: List[int] = []

        for move in board.available_moves():
            board.place(move, symbol)
            score = self.heuristic_score(board, symbol, opponent)
            board.undo(move)

            if score > best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)

        return random.choice(best_moves)

    @staticmethod
    def heuristic_score(
        board: Board,
        symbol: str,
        opponent: str,
    ) -> int:
        score = 0

        center = board.area // 2
        if board.cells[center] == symbol:
            score += 5
        elif board.cells[center] == opponent:
            score -= 5

        for line in board.winning_lines():
            values = [board.cells[index] for index in line]
            own = values.count(symbol)
            enemy = values.count(opponent)
            empty = values.count(EMPTY)

            if enemy == 0:
                score += own * own * 4 + empty
            if own == 0:
                score -= enemy * enemy * 4

        return score


# ─────────────────────────────────────────────────────────────────────────────
# Input helpers
# ─────────────────────────────────────────────────────────────────────────────

def ask_non_empty(prompt: str, default: str = "") -> str:
    while True:
        value = input(prompt).strip()

        if value:
            return value

        if default:
            return default

        print("Please enter a value.")


def ask_board_size() -> int:
    while True:
        value = input("Board size (3, 4, or 5) [3]: ").strip() or "3"

        if value in {"3", "4", "5"}:
            return int(value)

        print("Choose 3, 4, or 5.")


def ask_difficulty() -> str:
    print("\nDifficulty:")
    print("1. Easy       - random moves")
    print("2. Medium     - basic tactics")
    print("3. Hard       - strong heuristic AI")
    print("4. Impossible - unbeatable on 3x3")

    choices = {
        "1": "easy",
        "2": "medium",
        "3": "hard",
        "4": "impossible",
        "easy": "easy",
        "medium": "medium",
        "hard": "hard",
        "impossible": "impossible",
    }

    while True:
        value = input("\nChoose difficulty [4]: ").strip().lower() or "4"

        if value in choices:
            return choices[value]

        print("Choose 1, 2, 3, or 4.")


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"

    while True:
        value = input(f"{prompt} {suffix}: ").strip().lower()

        if not value:
            return default

        if value in {"y", "yes"}:
            return True

        if value in {"n", "no"}:
            return False

        print("Please answer yes or no.")


def ask_square(board: Board, prompt: str) -> Optional[int]:
    while True:
        value = input(prompt).strip().lower()

        if value in {"q", "quit", "exit"}:
            return None

        if value in {"u", "undo"}:
            return -1

        if value in {"h", "hint"}:
            return -2

        try:
            index = int(value) - 1
        except ValueError:
            print("Enter a square number, H for hint, U for undo, or Q to quit.")
            continue

        if board.is_valid_move(index):
            return index

        print("That square is unavailable.")


# ─────────────────────────────────────────────────────────────────────────────
# Game engine
# ─────────────────────────────────────────────────────────────────────────────

class Match:
    def __init__(
        self,
        settings: GameSettings,
        stats: Statistics,
        history: List[MatchRecord],
    ) -> None:
        self.settings = settings
        self.stats = stats
        self.history = history
        self.board = Board(settings.board_size)
        self.moves: List[Tuple[int, str]] = []

        if settings.mode == "computer":
            self.human_symbol = settings.starting_symbol
            self.computer_symbol = other_symbol(self.human_symbol)

            self.human = Player(
                name="You",
                symbol=self.human_symbol,
            )
            self.computer = Player(
                name="Computer",
                symbol=self.computer_symbol,
                is_computer=True,
            )
        else:
            self.human_symbol = None
            self.computer_symbol = None
            self.human = Player("Player 1", X)
            self.computer = Player("Player 2", O)

        self.ai = AI(settings.difficulty)

    def players(self) -> Dict[str, Player]:
        return {
            self.human.symbol: self.human,
            self.computer.symbol: self.computer,
        }

    def current_player(self) -> Player:
        symbol = self.settings.starting_symbol

        if self.moves:
            symbol = other_symbol(self.moves[-1][1])

        return self.players()[symbol]

    def undo_last_turn(self) -> bool:
        if not self.moves:
            return False

        undo_count = 1

        if (
            self.settings.mode == "computer"
            and len(self.moves) >= 2
        ):
            undo_count = 2

        for _ in range(min(undo_count, len(self.moves))):
            index, _symbol = self.moves.pop()
            self.board.undo(index)

        return True

    def add_move(self, index: int, symbol: str) -> None:
        self.board.place(index, symbol)
        self.moves.append((index, symbol))

    def display(self) -> None:
        clear_screen()
        print_header()
        print(
            f"\nBoard: {self.settings.board_size}x"
            f"{self.settings.board_size} | "
            f"Moves: {len(self.moves)}"
        )

        print(
            f"X: {self.human.name if self.human.symbol == X else self.computer.name}"
            f"   O: {self.human.name if self.human.symbol == O else self.computer.name}"
        )

        print(
            render_board(
                self.board,
                show_coordinates=self.settings.show_coordinates,
            )
        )

    def announce_hint(self) -> None:
        current = self.current_player()

        if current.is_computer:
            return

        if not self.board.available_moves():
            return

        if self.settings.board_size == 3:
            move = self.ai.perfect_move(
                self.board,
                current.symbol,
            )
        else:
            move = self.ai.strong_move(
                self.board,
                current.symbol,
            )

        print(
            paint(
                f"\nHint: square {move + 1} is a strong move.",
                YELLOW,
            )
        )
        pause()

    def play(self) -> str:
        while self.board.result() is None:
            self.display()
            player = self.current_player()

            if player.is_computer:
                if self.settings.animations:
                    print("\nComputer is thinking...")
                    time.sleep(0.6)

                move = self.ai.choose_move(
                    self.board,
                    player.symbol,
                )
                self.add_move(move, player.symbol)
                continue

            print(
                f"\n{player.name}'s turn "
                f"({symbol_display(player.symbol).strip()})"
            )

            command = ask_square(
                self.board,
                "Choose a square, H=hint, U=undo, Q=quit: ",
            )

            if command is None:
                return "QUIT"

            if command == -1:
                if self.undo_last_turn():
                    print("Last turn undone.")
                else:
                    print("There are no moves to undo.")
                pause()
                continue

            if command == -2:
                self.announce_hint()
                continue

            self.add_move(command, player.symbol)

        return self.board.result() or DRAW

    def finish(self, result: str) -> None:
        self.display()

        winning_line = self.board.winning_line()

        if winning_line:
            print(
                "\n"
                + paint(
                    f"{self.players()[result].name} wins!",
                    GREEN,
                )
            )
        else:
            print("\n" + paint("The game is a draw!", YELLOW))

        winner_is_computer = (
            result in self.players()
            and self.players()[result].is_computer
        )

        self.stats.record(
            result=result,
            mode=self.settings.mode,
            winner_is_computer=winner_is_computer,
            move_count=len(self.moves),
        )

        self.history.append(
            MatchRecord(
                date=timestamp(),
                mode=self.settings.mode,
                board_size=self.settings.board_size,
                difficulty=self.settings.difficulty,
                player_x=self.players()[X].name,
                player_o=self.players()[O].name,
                result=result,
                moves=len(self.moves),
            )
        )

        save_statistics(self.stats)
        save_history(self.history)
        pause()


# ─────────────────────────────────────────────────────────────────────────────
# Menus
# ─────────────────────────────────────────────────────────────────────────────

def configure_match() -> Optional[GameSettings]:
    clear_screen()
    print_header("NEW MATCH")

    print("\n1. Human vs Computer")
    print("2. Human vs Human")

    while True:
        mode_choice = input("\nSelect mode [1]: ").strip() or "1"

        if mode_choice == "1":
            mode = "computer"
            break

        if mode_choice == "2":
            mode = "human"
            break

        print("Choose 1 or 2.")

    board_size = ask_board_size()

    if mode == "computer":
        difficulty = ask_difficulty()

        print("\nChoose your symbol:")
        print("1. X — moves first")
        print("2. O — moves second")

        symbol_choice = input("\nChoose symbol [1]: ").strip() or "1"
        human_symbol = O if symbol_choice == "2" else X

        settings = GameSettings(
            board_size=board_size,
            mode=mode,
            difficulty=difficulty,
            starting_symbol=X,
        )

        match = Match(settings, Statistics(), [])
        match.human = Player("You", human_symbol)
        match.computer = Player(
            "Computer",
            other_symbol(human_symbol),
            True,
        )

        return settings, match.human, match.computer

    player_x = ask_non_empty("\nName for X [Player 1]: ", "Player 1")
    player_o = ask_non_empty("Name for O [Player 2]: ", "Player 2")

    settings = GameSettings(
        board_size=board_size,
        mode=mode,
        difficulty="human",
        starting_symbol=X,
    )

    return settings, Player(player_x, X), Player(player_o, O)


def start_match(stats: Statistics, history: List[MatchRecord]) -> None:
    configured = configure_match()

    if configured is None:
        return

    settings, player_x_or_human, player_o_or_computer = configured

    match = Match(settings, stats, history)

    if settings.mode == "computer":
        match.human = player_x_or_human
        match.computer = player_o_or_computer
    else:
        match.human = player_x_or_human
        match.computer = player_o_or_computer

    result = match.play()

    if result == "QUIT":
        return

    match.finish(result)


def show_statistics(stats: Statistics) -> None:
    clear_screen()
    print_header("SCOREBOARD")

    print(f"\nGames played:       {stats.total_games}")
    print(f"X wins:             {stats.x_wins}")
    print(f"O wins:             {stats.o_wins}")
    print(f"Draws:              {stats.draws}")
    print(f"Human wins:         {stats.human_wins}")
    print(f"Computer wins:      {stats.computer_wins}")
    print(
        "Fastest win:        "
        f"{stats.fastest_win_moves or 'No wins yet'} moves"
    )
    print(f"Longest game:       {stats.longest_game_moves} moves")

    if stats.total_games:
        draw_rate = stats.draws / stats.total_games * 100
        print(f"Draw rate:           {draw_rate:.1f}%")

    pause()


def show_history(history: List[MatchRecord]) -> None:
    clear_screen()
    print_header("MATCH HISTORY")

    if not history:
        print("\nNo completed matches yet.")
        pause()
        return

    for number, match in enumerate(reversed(history[-20:]), start=1):
        result_text = "Draw" if match.result == DRAW else f"{match.result} won"

        print(
            f"\n{number:>2}. {match.date} | "
            f"{match.board_size}x{match.board_size} | "
            f"{result_text} | "
            f"{match.moves} moves"
        )
        print(f"    X: {match.player_x}")
        print(f"    O: {match.player_o}")

    pause()


def reset_all_data(stats: Statistics, history: List[MatchRecord]) -> None:
    clear_screen()
    print_header("RESET DATA")

    confirmation = input(
        "\nType DELETE EVERYTHING to erase the scoreboard and history: "
    ).strip()

    if confirmation == "DELETE EVERYTHING":
        fresh_stats = Statistics()
        stats.__dict__.update(fresh_stats.__dict__)
        history.clear()
        save_statistics(stats)
        save_history(history)
        print("\nAll data has been erased.")
    else:
        print("\nReset cancelled.")

    pause()


def settings_menu() -> None:
    clear_screen()
    print_header("SETTINGS")

    print("\nThe game uses the following controls:")
    print("• Enter a square number to make a move.")
    print("• Enter H to request a hint.")
    print("• Enter U to undo the previous turn.")
    print("• Enter Q to leave the current match.")
    print("• Set NO_COLOR=1 to disable terminal colors.")
    print("• Statistics are saved automatically.")

    pause()


def main_menu() -> None:
    stats = load_statistics()
    history = load_history()

    while True:
        clear_screen()
        print_header()

        print("\n1. New match")
        print("2. Scoreboard")
        print("3. Match history")
        print("4. Controls and settings")
        print("5. Reset all data")
        print("6. Quit")

        choice = input("\nSelect an option: ").strip().lower()

        if choice in {"1", "new", "play"}:
            start_match(stats, history)

        elif choice in {"2", "score", "scoreboard"}:
            show_statistics(stats)

        elif choice in {"3", "history"}:
            show_history(history)

        elif choice in {"4", "settings", "help"}:
            settings_menu()

        elif choice in {"5", "reset"}:
            reset_all_data(stats, history)

        elif choice in {"6", "q", "quit", "exit"}:
            clear_screen()
            print_header()
            print("\nThanks for playing!")
            break

        else:
            print("\nInvalid option.")
            pause()


# ─────────────────────────────────────────────────────────────────────────────
# Program entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    except EOFError:
        print("\n\nGoodbye!")