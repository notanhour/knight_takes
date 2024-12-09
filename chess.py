import pygame as pg
import mysql.connector
import sys


class PuzzleDataBase:
    def __init__(self):
        self.connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="koliaprivet",
            database="puzzle_db"
        )
        self.cursor = self.connection.cursor()
        self.puzzle_index = 0

    def _get_puzzle(self, index=None):
        query = f"SELECT * FROM puzzles LIMIT 1 OFFSET {index}"
        self.cursor.execute(query)
        puzzle = self.cursor.fetchone()
        if puzzle:
            return puzzle
        return None
    
    def get_total_puzzles(self):
        self.cursor.execute("SELECT COUNT(*) FROM puzzles")
        total = self.cursor.fetchone()[0]
        return total
    
    def get_next_puzzle(self):
        puzzle = self._get_puzzle(self.puzzle_index)
        if puzzle:
            self.puzzle_index += 1
        return puzzle
    
    def get_puzzle(self, index):
        return self._get_puzzle(index)

    def reset(self):
        self.puzzle_index = 0

    def close(self):
        self.cursor.close()
        self.connection.close()


board_size = 800
square_size = board_size / 8
screen = pg.display.set_mode((board_size, board_size))

LIGHT = (222, 227, 230)
DARK = (140, 162, 173)


class Board:
    def __init__(self):
        self.grid = [[None for _ in range(8)] for _ in range(8)]  # Создаем пустую 8x8 доску
        self.records = []

    def draw(self):
        # Отрисовка клеток
        for row in range(8):
            for col in range(8):
                color = LIGHT if (row + col) % 2 == 0 else DARK
                pg.draw.rect(screen, color, pg.Rect(col * square_size, row * square_size, square_size, square_size))
        # Отрисовка фигур
        for row in range(8):
            for col in range(8):
                piece = self.grid[row][col]
                if piece:
                    screen.blit(piece.image, (col * square_size, row * square_size))

    # Инициализация фигур на их начальных позициях
    def setup(self, fen=None):
        self.grid = [[None for _ in range(8)] for _ in range(8)]
        if fen:
            lines = fen.split()[0].split("/")
            board = []
            for s in lines:
                horizontal = []
                for character in s:
                    if character.isdigit():
                        horizontal.extend([" "] * int(character))
                    else:
                        horizontal.append(character)
                board.append(horizontal)
            for row in range(8):
                for col in range(8):
                    self.grid[row][col] = self.character_to_piece(board[row][col], (row, col))
                    
                
        else:
            for col in range(8):
                self.grid[1][col] = Pawn("black", (1, col))
                self.grid[6][col] = Pawn("white", (6, col))

            pieces = [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook]
            for col, piece in enumerate(pieces):
                self.grid[0][col] = piece("black", (0, col))
                self.grid[7][col] = piece("white", (7, col))

        self.save_board_state()

    def save_board_state(self):
        board_state = [[piece for piece in row] for row in self.grid]
        self.records.append(board_state)
    
    def is_blank(self, row, col):
        return self.grid[row][col] is None
    
    def is_foe(self, row, col, color):
        piece = self.grid[row][col]
        return piece is not None and piece.color != color
    
    def is_on_board(self, row, col):
        return (-1 < row < 8) and (-1 < col < 8)
    
    def is_check(self, color):
        king_position = None
        for row in range(8):
            for col in range(8):
                piece = self.grid[row][col]
                if piece and isinstance(piece, King) and piece.color == color:
                    king_position = (row, col)
                    break
            if king_position:
                break

        for row in range(8):
            for col in range(8):
                piece = self.grid[row][col]
                if piece and piece.color != color:
                    if king_position in piece.get_valid_moves(self):
                        return True
        return False
    
    def is_checkmate(self, color):
        if not self.is_check(color):
            return False

        for row in range(8):
            for col in range(8):
                piece = self.grid[row][col]
                if piece and piece.color == color:
                    legal_moves = piece.get_legal_moves(self)
                    if len(legal_moves) > 0:
                        return False
        return True
    
    def is_pat(self, color):
        if self.is_check(color):
            return False

        for row in range(8):
            for col in range(8):
                piece = self.grid[row][col]
                if piece and piece.color == color:
                    legal_moves = piece.get_legal_moves(self)
                    if len(legal_moves) > 0:
                        return False
        return True
    
    def highlight_moves(self, moves, selected_piece):
        move_highlight = pg.Surface((square_size, square_size), pg.SRCALPHA)
        pg.draw.circle(move_highlight, (50, 50, 50, 120), (square_size / 2, square_size / 2), square_size / 5)
        capture_highlight = pg.Surface((square_size, square_size), pg.SRCALPHA)
        pg.draw.circle(capture_highlight, (50, 50, 50, 120), (square_size / 2, square_size / 2), square_size / 2, 7)
        for row, col in moves:
            target_piece = self.grid[row][col]
            if target_piece and target_piece.color != selected_piece.color:
                screen.blit(capture_highlight, (col * square_size, row * square_size))
            else:
                screen.blit(move_highlight, (col * square_size, row * square_size))

    def move_piece(self, piece, row, col, record=True):
        _row, _col = piece.position
        self.grid[_row][_col] = None

        # Взятие на проходе
        if isinstance(piece, Pawn) and abs(_col - col) == 1 and self.is_blank(row, col):
            if piece.color == "white":
                self.grid[row + 1][col] = None
            else:
                self.grid[row - 1][col] = None

        # Рокировка
        if isinstance(piece, King) and abs(col - _col) == 2:
            if col > _col:
                rook = self.grid[_row][7]
                self.grid[_row][7] = None
                self.grid[_row][5] = rook
                rook.position = (_row, 5)
            else:
                rook = self.grid[_row][0]
                self.grid[_row][0] = None
                self.grid[_row][3] = rook
                rook.position = (_row, 3)

        # Превращение пешки
        if isinstance(piece, Pawn) and (row == 0 or row == 7):
            self.grid[row][col] = piece = Queen(piece.color, (row, col))
        else:
            self.grid[row][col] = piece
            piece.position = (row, col)  # Новая позиция фигуры

        if isinstance(piece, (Pawn, King, Rook)):
            piece.has_moved = True

        if record:
            self.save_board_state()

    def character_to_piece(self, character, position):
        color = "white" if character.isupper() else "black"

        match character.lower():
            case "p":
                return Pawn(color, position)
            case "r":
                return Rook(color, position)
            case "n":
                return Knight(color, position)
            case "b":
                return Bishop(color, position)
            case "q":
                return Queen(color, position)
            case "k":
                return King(color, position)
        
        return None


class Piece:
    def __init__(self, color, position):
        self.color = color
        self.position = position
        self.image = pg.image.load(f"pieces/{color}/{self.__class__.__name__.lower()}.png")
        self.image = pg.transform.smoothscale(self.image, (square_size, square_size))

    def get_valid_moves(self, board):
        return []

    def get_legal_moves(self, board):
        valid_moves = self.get_valid_moves(board)
        legal_moves = []

        for move in valid_moves:
            start_row, start_col = self.position
            target_row, target_col = move
            target_piece = board.grid[target_row][target_col]

            board.grid[start_row][start_col] = None
            board.grid[target_row][target_col] = self
            self.position = (target_row, target_col)

            if not board.is_check(self.color):
                legal_moves.append(move)

            board.grid[start_row][start_col] = self
            board.grid[target_row][target_col] = target_piece
            self.position = (start_row, start_col)

        return legal_moves


    def _get_linear_moves(self, board, directions):
        moves = []
        start_y, start_x = self.position

        for dy, dx in directions:
            y, x = start_y, start_x
            while board.is_on_board(y + dy, x + dx):
                y += dy
                x += dx
                if board.is_blank(y, x):
                    moves.append((y, x))
                elif board.is_foe(y, x, self.color):
                    moves.append((y, x))
                    break
                else:
                    break
        
        return moves



class King(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)
        self.has_moved = False

    def get_valid_moves(self, board):
        moves = []
        y, x = self.position
        king_moves = [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]

        for dy, dx in king_moves:
            if board.is_on_board(y + dy, x + dx) and (board.is_blank(y + dy, x + dx) or board.is_foe(y + dy, x + dx, self.color)):
                moves.append((y + dy, x + dx))

        if not self.has_moved:
            if isinstance(board.grid[y][0], Rook) and not board.grid[y][0].has_moved:
                if all(board.is_blank(y, col) for col in range(1, 4)):
                    moves.append((y, x - 2))
            
            if isinstance(board.grid[y][7], Rook) and not board.grid[y][7].has_moved:
                if all(board.is_blank(y, col) for col in range(5, 7)):
                    moves.append((y, x + 2))

        return moves

    def get_legal_moves(self, board):
        valid_moves = self.get_valid_moves(board)
        legal_moves = []

        for move in valid_moves:
            start_row, start_col = self.position
            target_row, target_col = move
            target_piece = board.grid[target_row][target_col]

            if abs(target_col - start_col) == 2:
                dx = 1 if target_col > start_col else -1
                clear = True
                for col in range(start_col + dx, target_col + dx, dx):
                    board.grid[start_row][start_col] = None
                    board.grid[target_row][col] = self
                    self.position = (target_row, col)
                    
                    if board.is_check(self.color):
                        clear = False

                    board.grid[start_row][start_col] = self
                    board.grid[target_row][col] = target_piece
                    self.position = (start_row, start_col)

                    if not clear:
                        break
                
                if clear and not board.is_check(self.color):
                    legal_moves.append(move)

            else:
                board.grid[start_row][start_col] = None
                board.grid[target_row][target_col] = self
                self.position = (target_row, target_col)

                if not board.is_check(self.color):
                    legal_moves.append(move)

                board.grid[start_row][start_col] = self
                board.grid[target_row][target_col] = target_piece
                self.position = (start_row, start_col)

        return legal_moves

class Queen(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)

    def get_valid_moves(self, board):
        return self._get_linear_moves(board, directions=[(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)])


class Rook(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)
        self.has_moved = False

    def get_valid_moves(self, board):
        return self._get_linear_moves(board, directions=[(0, 1), (1, 0), (0, -1), (-1, 0)])


class Bishop(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)

    def get_valid_moves(self, board):
        return self._get_linear_moves(board, directions=[(1, 1), (1, -1), (-1, -1), (-1, 1)])


class Knight(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)

    def get_valid_moves(self, board):
        moves = []
        y, x = self.position
        knight_moves = [(2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2)]
        for dy, dx in knight_moves:
            if board.is_on_board(y + dy, x + dx) and (board.is_blank(y + dy, x + dx) or board.is_foe(y + dy, x + dx, self.color)):
                moves.append((y + dy, x + dx))
        return moves



class Pawn(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)
        self.has_moved = False

    def get_valid_moves(self, board):
        moves = []
        y, x = self.position
        direction = -1 if self.color == "white" else 1

        if board.is_blank(y + direction, x):
            moves.append((y + direction, x))

        if not self.has_moved:
            if board.is_blank(y + direction, x) and board.is_blank(y + 2 * direction, x):
                moves.append((y + 2 * direction, x))
        
        for dx in [-1, 1]:
            if board.is_on_board(y + direction, x + dx) and board.is_foe(y + direction, x + dx, self.color):
                moves.append((y + direction, x + dx))

        # Взятие на проходе (en passant)
        if self.color == "white" and y == 3:
            if board.is_on_board(y, x - 1) and isinstance(board.grid[y][x - 1], Pawn) and board.grid[y][x - 1].color == "black":
                if isinstance(board.records[-2][y - 2][x - 1], Pawn) and board.records[-2][y - 1][x - 1] is None:
                    moves.append((y - 1, x - 1))

            if board.is_on_board(y, x + 1) and isinstance(board.grid[y][x + 1], Pawn) and board.grid[y][x + 1].color == "black":
                if isinstance(board.records[-2][y - 2][x + 1], Pawn) and board.records[-2][y - 1][x + 1] is None:
                    moves.append((y - 1, x + 1))
        
        elif self.color == "black" and y == 4:
            if board.is_on_board(y, x - 1) and isinstance(board.grid[y][x - 1], Pawn) and board.grid[y][x - 1].color == "white":
                if isinstance(board.records[-2][y + 2][x - 1], Pawn) and board.records[-2][y + 1][x - 1] is None:
                    moves.append((y + 1, x - 1))

            if board.is_on_board(y, x + 1) and isinstance(board.grid[y][x + 1], Pawn) and board.grid[y][x + 1].color == "white":
                if isinstance(board.records[-2][y + 2][x + 1], Pawn) and board.records[-2][y + 1][x + 1] is None:
                    moves.append((y + 1, x + 1))

        return moves
    

class Player:
    pass


class AI:
    pass


class Game:
    def __init__(self):
        self.board = Board()
        self.turn = "white"
        self.selected_piece = None
        self.legal_moves = []
        self.running = None

        self.mode = None
        self.puzzle_moves = []
        self.step_index = 0

    def set(self, mode="normal", fen=None, puzzle_moves=None):
        self.running = True
        self.mode = mode
        if mode == "puzzle" and puzzle_moves:
            self.puzzle_moves = puzzle_moves.split()
            self.step_index = 0
            self.turn = "white" if fen.split()[1] == "w" else "black"
        self.board.setup(fen)  # Если fen is None, то на начальные позиции

    def translate_to_coordinates(self, notational):
        start = (8 - int(notational[1]), ord(notational[0]) - ord("a"))
        end = (8 - int(notational[3]), ord(notational[2]) - ord("a"))
        return start, end

    def run(self):
        while self.running:
            for event in pg.event.get():
                self.handle_event(event)
            if not self.running:
                break

            screen.fill(LIGHT)
            self.board.draw()
            self.board.highlight_moves(self.legal_moves, self.selected_piece)
            pg.display.flip()

    def handle_event(self, event):
        if event.type == pg.QUIT or event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
            self.running = False
            pg.quit()
        elif event.type == pg.MOUSEBUTTONDOWN:
            row, col = int(event.pos[1] / square_size), int(event.pos[0] / square_size)
            self.handle_piece(row, col)
        
    def handle_piece(self, row, col):
        piece = self.board.grid[row][col]
        if piece and piece.color == self.turn:
                self.selected_piece = piece
                self.legal_moves = piece.get_legal_moves(self.board)
        elif self.selected_piece and (row, col) in self.legal_moves:
            if self.mode == "normal":
                self.board.move_piece(self.selected_piece, row, col)
                self.turn = "black" if self.turn == "white" else "white"
                if self.board.is_checkmate(self.turn) or self.board.is_pat(self.turn):
                    self.running = False
            elif self.mode == "puzzle":
                expected = self.puzzle_moves[self.step_index]
                start_position, end_position = self.translate_to_coordinates(expected)
                if self.selected_piece.position != start_position or (row, col) != end_position:
                    pass  # Добавить логику наказания за неправильный ход
                else:
                    self.board.move_piece(self.selected_piece, row, col)
                    self.turn = "black" if self.turn == "white" else "white"
                    self.step_index += 1
                    if self.step_index == len(self.puzzle_moves):
                        print("Puzzle solved!")
                        self.running = False
            self.selected_piece = None
            self.legal_moves = []
        else:
            self.legal_moves = []


def main():
    pg.init()

    game = Game()
    puzzle_db = PuzzleDataBase()

    args = sys.argv

    if len(args) < 2:
        print("Error: Not enough arguments provided.")
        exit(1)
    
    mode = args[1]

    if mode not in ("normal", "puzzle"):
        print(f"Error: '{mode}' is not a valid mode. Enter 'normal' or 'puzzle'.")
        sys.exit(1)

    if mode == "normal":
        game.set(mode)

    elif mode == "puzzle":
        if len(args) < 3:
            print("Error: Puzzle index is required for 'puzzle' mode.")
            exit(1)

        try:
            puzzle_index = int(args[2])
        except ValueError:
            print("Error: Puzzle index must be an integer.")
            sys.exit(1)

        try:
            puzzle = puzzle_db.get_puzzle(puzzle_index)
        except ValueError:
            print(f"Error: No puzzle found for index {puzzle_index}")
            exit(1)
        
        game.set(mode, fen=puzzle[1], puzzle_moves=puzzle[2])
    
    try:
        game.run()
    finally:
        puzzle_db.close()


if __name__ == "__main__":
    main()