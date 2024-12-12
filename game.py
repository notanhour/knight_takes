import pygame as pg
import mysql.connector
import sys
import configparser
import chess
import chess.engine

# Путь к двигателю Stockfish
ENGINE = "./stockfish-ubuntu-x86-64-avx2"

# Класс для взаимодействия с шахматным двигателем (например, Stockfish)
class ChessEngine:
    def __init__(self, path, depth=15):
        self.path = path
        self.depth = depth
        # Запуск двигателя с заданной глубиной анализа
        self.engine = chess.engine.SimpleEngine.popen_uci(path)

    def get_best_move(self, fen):
        # Преобразуем строку FEN в объект шахматной доски
        board = chess.Board(fen)
        search_depth = chess.engine.Limit(depth=self.depth)
        result = self.engine.play(board, search_depth)
        return result.move  # Возвращаем лучший ход

    def close(self):
        # Закрытие соединения с двигателем
        self.engine.close()

# Класс для работы с базой данных шахматных задачек
class PuzzleDataBase:
    def __init__(self):
        # Чтение конфигурации из файла
        config = configparser.ConfigParser()
        config.read("config.ini")
        self.connection = mysql.connector.connect(
            host=config["mysql"]["host"],
            user=config["mysql"]["user"],
            password=config["mysql"]["password"],
            database=config["mysql"]["database"]
        )
        self.cursor = self.connection.cursor()
        self.puzzle_index = 0

    def get_puzzle(self, index):
        # Получение задачки по индексу из базы данных
        query = f"SELECT * FROM puzzles ORDER BY rating ASC LIMIT 1 OFFSET {index}"
        self.cursor.execute(query)
        puzzle = self.cursor.fetchone()
        if puzzle:
            return puzzle
        return None

    def get_total_puzzles(self):
        # Получаем общее количество задачек в базе данных
        self.cursor.execute("SELECT COUNT(*) FROM puzzles")
        total = self.cursor.fetchone()[0]
        return total

    def get_next_puzzle(self):
        # Получаем следующую задачку
        puzzle = self.get_puzzle(self.puzzle_index)
        if puzzle:
            self.puzzle_index += 1
        return puzzle

    def reset(self):
        # Сбрасываем индекс задачки
        self.puzzle_index = 0

    def close(self):
        # Закрываем соединение с базой данных
        self.cursor.close()
        self.connection.close()

# Размеры доски и клеток
board_size = 800
square_size = board_size / 8
screen = pg.display.set_mode((board_size, board_size))

clock = pg.time.Clock()

# Цвета для светлых и темных клеток доски
LIGHT = (222, 227, 230)
DARK = (140, 162, 173)

# Класс шахматной доски
class Board:
    def __init__(self):
        self.grid = [[None for _ in range(8)] for _ in range(8)]  # Создаем пустую 8x8 доску
        self.records = []  # История состояния доски
        self.records_fen = {}  # Частота позиций по FEN
        self.is_flipped = False  # Флаг переворота доски
        self.en_passant_target = None  # Цель для взятия на проходе
        self.halfmove_clock = 0  # Часы половинных ходов (для подсчета 50 ходов без взятия или хода пешки)
        self.fullmove_number = 1  # Номер полного хода

    def draw(self):
        for row in range(8):
            for col in range(8):
                # Клетки
                _row, _col = self._translate_coordinates(row, col)
                color = LIGHT if (_row + _col) % 2 == 0 else DARK
                pg.draw.rect(screen, color, pg.Rect(col * square_size, row * square_size, square_size, square_size))

                # Фигуры
                piece = self.grid[_row][_col]
                if piece:
                    screen.blit(piece.image, (col * square_size, row * square_size))

    def flip(self):
        # Переворот доски
        self.is_flipped = not self.is_flipped

    def _translate_coordinates(self, row, col):
        # Преобразование координат в зависимости от переворота доски
        if self.is_flipped:
            return 7 - row, 7 - col
        return row, col

    def translate_to_coordinates(self, s):
        # Преобразование строки хода (например, 'e2e4') в координаты
        start = (8 - int(s[1]), ord(s[0]) - ord("a"))
        end = (8 - int(s[3]), ord(s[2]) - ord("a"))
        return start, end

    def _get_fen(self, turn):
        # Генерация FEN для текущего состояния доски
        fen = ""
        for row in self.grid:
            blank = 0
            for square in row:
                if square is None:
                    blank += 1
                else:
                    if blank > 0:
                        fen += str(blank)
                        blank = 0
                    fen += square.character
            if blank > 0:
                fen += str(blank)
            fen += "/"
        fen = fen[:-1]  # Затираем последний /

        fen += f" {"w" if turn == "white" else "b"}"  # Текущий ход
        fen += f" {self._get_castling_rights()}"  # Права на рокировку
        fen += f" {self.en_passant_target if self.en_passant_target else "-"}"  # Взятие на проходе
        fen += f" {self.halfmove_clock}"  # Количество половинных ходов
        fen += f" {self.fullmove_number}"  # Номер полного хода

        return fen

    def _get_castling_rights(self):
        # Получение прав на рокировку для двух сторон
        rights = ""
        if isinstance(self.grid[7][4], King) and isinstance(self.grid[7][7], Rook):
            if not self.grid[7][4].has_moved and not self.grid[7][7].has_moved:
                rights += "K"
        if isinstance(self.grid[7][4], King) and isinstance(self.grid[7][0], Rook):
            if not self.grid[7][4].has_moved and not self.grid[7][0].has_moved:
                rights += "Q"
        if isinstance(self.grid[0][4], King) and isinstance(self.grid[0][7], Rook):
            if not self.grid[0][4].has_moved and not self.grid[0][7].has_moved:
                rights += "k"
        if isinstance(self.grid[0][4], King) and isinstance(self.grid[0][0], Rook):
            if not self.grid[0][4].has_moved and not self.grid[0][0].has_moved:
                rights += "q"
        return rights if rights else "-"


    # Инициализация фигур на их начальных позициях или по FEN
    def setup(self, fen=None):
        self.grid = [[None for _ in range(8)] for _ in range(8)]
        if fen:
            parts = fen.split()  # Разбиваем FEN на компоненты
            lines, castling, en_passant = parts[0], parts[2], parts[3]
            # Расстановка фигур
            board = []
            for s in lines.split("/"):
                horizontal = []
                for character in s:
                    if character.isdigit():
                        horizontal.extend([" "] * int(character))  # Пропуск пустых клеток
                    else:
                        horizontal.append(character)
                board.append(horizontal)
            for row in range(8):
                for col in range(8):
                    self.grid[row][col] = self.character_to_piece(board[row][col], (row, col))

            # Флаги рокировки
            for row in [0, 7]:
                for col in [0, 4, 7]:
                    piece = self.grid[row][col]
                    if isinstance(piece, (King, Rook)):
                        piece.has_moved = True  # Предполагаем, что фигуры до этого двигались

            if "K" in castling:
                self.grid[7][4].has_moved = False
                self.grid[7][7].has_moved = False
            if "Q" in castling:
                self.grid[7][4].has_moved = False
                self.grid[7][0].has_moved = False
            if "k" in castling:
                self.grid[0][4].has_moved = False
                self.grid[0][7].has_moved = False
            if "q" in castling:
                self.grid[0][4].has_moved = False
                self.grid[0][0].has_moved = False

            # Взятие на проходе
            if en_passant != "-":
                col = ord(en_passant[0]) - ord("a")
                row = 8 - int(en_passant[1])
                self.en_passant_target = (row, col)

        else:
            for col in range(8):
                self.grid[1][col] = Pawn("black", (1, col))
                self.grid[6][col] = Pawn("white", (6, col))

            pieces = [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook]
            for col, piece in enumerate(pieces):
                self.grid[0][col] = piece("black", (0, col))
                self.grid[7][col] = piece("white", (7, col))

        # Сохранение состояния доски
        self.save_board_state()

    def save_board_state(self):
        # Сохраняем текущее состояние доски в историю
        board_state = [[piece for piece in row] for row in self.grid]
        self.records.append(board_state)

    def is_blank(self, row, col):
        # Проверка, пуста ли клетка
        return self.grid[row][col] is None

    def is_foe(self, row, col, color):
        # Проверка, является ли фигура на клетке противником
        piece = self.grid[row][col]
        return piece is not None and piece.color != color

    def is_on_board(self, row, col):
        # Проверка, находится ли клетка на доске
        return (-1 < row < 8) and (-1 < col < 8)

    def is_check(self, color):
        # Проверка, находится ли король данного цвета под шахом
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
        # Проверка, мат ли королю данного цвета
        if not self.is_check(color):
            return False

        for row in range(8):
            for col in range(8):
                piece = self.grid[row][col]
                if piece and piece.color == color:
                    legal_moves = piece.get_legal_moves(self)
                    if len(legal_moves) > 0:  # Если есть легальные ходы, то не пат
                        return False
        return True

    def is_pat(self, color):
        # Проверка, пат ли королю данного цвета
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
        # Подсветка доступных ходов
        move_highlight = pg.Surface((square_size, square_size), pg.SRCALPHA)
        pg.draw.circle(move_highlight, (50, 50, 50, 120), (square_size / 2, square_size / 2), square_size / 5)
        capture_highlight = pg.Surface((square_size, square_size), pg.SRCALPHA)
        pg.draw.circle(capture_highlight, (50, 50, 50, 120), (square_size / 2, square_size / 2), square_size / 2, 7)
        for row, col in moves:
            _row, _col = self._translate_coordinates(row, col)
            target_piece = self.grid[row][col]
            if target_piece and target_piece.color != selected_piece.color:
                screen.blit(capture_highlight, (_col * square_size, _row * square_size))
            else:
                screen.blit(move_highlight, (_col * square_size, _row * square_size))

    def move_piece(self, piece, row, col, record=True):
        # Выполнение хода фигуры
        _row, _col = piece.position
        self.grid[_row][_col] = None

        # Правило 50 ходов
        if isinstance(piece, Pawn) or not self.is_blank(row, col):
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

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

        # Если пешка, король или ладья двигаются, запомним это
        if isinstance(piece, (Pawn, King, Rook)):
            piece.has_moved = True

        # Изменение номера полного хода
        if piece.color == "black":
            self.fullmove_number += 1

        if record:
            self.save_board_state()

        # Проверка на 3-кратное повторение позиции
        fen = self._get_fen(piece.color).split()[0]
        if fen in self.records_fen:
            self.records_fen[fen] += 1
        else:
            self.records_fen[fen] = 1

    def character_to_piece(self, character, position):
        # Преобразование символа FEN в объект фигуры
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

    def is_threefold_repetition(self):
        # Проверка 3-кратного повторения позиции
        for fen in self.records_fen:
            if self.records_fen[fen] >= 3:
                return True
        return False

# Абстрактный класс фигуры
class Piece:
    def __init__(self, color, position):
        self.color = color  # Цвет фигуры ("white" или "black")
        self.position = position  # Позиция фигуры (координаты на доске)
        self.character = None  # Символ, представляющий фигуру (например, 'K' для короля)
        # Загрузка изображения фигуры
        self.image = pg.image.load(f"pieces/{color}/{self.__class__.__name__.lower()}.png")
        self.image = pg.transform.smoothscale(self.image, (square_size, square_size))

    def get_valid_moves(self, board):
        # Метод для получения всех допустимых ходов фигуры (без проверки шахов)
        return []

    def get_legal_moves(self, board):
        # Метод для получения всех легальных ходов (с проверкой шахов)
        valid_moves = self.get_valid_moves(board)
        legal_moves = []

        for move in valid_moves:
            # Сохраняем состояние
            start_row, start_col = self.position
            target_row, target_col = move
            target_piece = board.grid[target_row][target_col]

            # Делаем временный ход
            board.grid[start_row][start_col] = None
            board.grid[target_row][target_col] = self
            self.position = (target_row, target_col)

            # Проверяем, не находится ли король под шахом
            if not board.is_check(self.color):
                legal_moves.append(move)

            # Возвращаем ход
            board.grid[start_row][start_col] = self
            board.grid[target_row][target_col] = target_piece
            self.position = (start_row, start_col)

        return legal_moves


    def _get_linear_moves(self, board, directions):
        # Метод для получения всех ходов в линейных направлениях (для ладьи, ферзя, слона)
        moves = []
        start_y, start_x = self.position

        for dy, dx in directions:
            y, x = start_y, start_x
            while board.is_on_board(y + dy, x + dx):  # Проверяем, находится ли клетка на доске
                y += dy
                x += dx
                if board.is_blank(y, x):  # Если клетка пуста, добавляем её в список ходов
                    moves.append((y, x))
                elif board.is_foe(y, x, self.color):  # Если на клетке стоит фигура противника, добавляем её и прекращаем проверку в этом направлении
                    moves.append((y, x))
                    break
                else:  # Если на клетке стоит союзная фигура, прекращаем проверку в этом направлении
                    break

        return moves


class King(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)
        self.character = "K" if color == "white" else "k"
        self.has_moved = False  # Флаг, указывающий, делал ли король ход (для рокировки)
    def get_valid_moves(self, board):
        moves = []
        y, x = self.position
        king_moves = [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]

        # Проверяем, может ли король пойти в каждую из соседних клеток
        for dy, dx in king_moves:
            if board.is_on_board(y + dy, x + dx) and (board.is_blank(y + dy, x + dx) or board.is_foe(y + dy, x + dx, self.color)):
                moves.append((y + dy, x + dx))

        # Проверка на доступность рокировки
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

            if abs(target_col - start_col) == 2:  # Проверка рокировки
                dx = 1 if target_col > start_col else -1
                clear = True
                for col in range(start_col + dx, target_col + dx, dx):
                    # Выполняем временные ходы через клетки, по которым будет двигаться король
                    board.grid[start_row][start_col] = None
                    board.grid[target_row][col] = self
                    self.position = (target_row, col)

                    # Если король попадает под шах, рокировка недоступна
                    if board.is_check(self.color):
                        clear = False

                    # Возвращаем ходы
                    board.grid[start_row][start_col] = self
                    board.grid[target_row][col] = target_piece
                    self.position = (start_row, start_col)

                    if not clear:
                        break

                if clear and not board.is_check(self.color):
                    legal_moves.append(move)

            else:
                # Проверяем обычные ходы
                board.grid[start_row][start_col] = None
                board.grid[target_row][target_col] = self
                self.position = (target_row, target_col)

                # Если король не под шахом, ход допустим
                if not board.is_check(self.color):
                    legal_moves.append(move)

                # Возвращаем ход
                board.grid[start_row][start_col] = self
                board.grid[target_row][target_col] = target_piece
                self.position = (start_row, start_col)

        return legal_moves

class Queen(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)
        self.character = "Q" if color == "white" else "q"

    def get_valid_moves(self, board):
        return self._get_linear_moves(board, directions=[(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)])


class Rook(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)
        self.character = "R" if color == "white" else "r"
        self.has_moved = False

    def get_valid_moves(self, board):
        return self._get_linear_moves(board, directions=[(0, 1), (1, 0), (0, -1), (-1, 0)])


class Bishop(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)
        self.character = "B" if color == "white" else "b"

    def get_valid_moves(self, board):
        return self._get_linear_moves(board, directions=[(1, 1), (1, -1), (-1, -1), (-1, 1)])


class Knight(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)
        self.character = "N" if color == "white" else "n"

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
        self.character = "P" if color == "white" else "p"
        # Проверяем, сделала ли пешка свой первый ход
        if (color == "white" and position[0] != 6) or (color == "black" and position[0] != 1):
            self.has_moved = True
        else:
            self.has_moved = False

    def get_valid_moves(self, board):
        moves = []
        y, x = self.position
        # Направление движения пешки (вверх для белых, вниз для черных)
        direction = -1 if self.color == "white" else 1

        # Пешка доступен ход вперед, если клетка перед ней свободна
        if board.is_blank(y + direction, x):
            moves.append((y + direction, x))

         # Пешке доступен двойной ход вперед, если она еще не двигалась
        if not self.has_moved:
            if board.is_blank(y + direction, x) and board.is_blank(y + 2 * direction, x):
                moves.append((y + 2 * direction, x))

        # Пешке доступна атака по диагонали, если там находится фигура противника
        for dx in [-1, 1]:
            if board.is_on_board(y + direction, x + dx) and board.is_foe(y + direction, x + dx, self.color):
                moves.append((y + direction, x + dx))

        # Взятие на проходе (en passant)
        if self.color == "white" and y == 3:
            if board.is_on_board(y, x - 1) and isinstance(board.grid[y][x - 1], Pawn) and board.grid[y][x - 1].color == "black":
                if (y - 1, x - 1) == board.en_passant_target:
                    moves.append((y - 1, x - 1))
                elif len(board.records) > 1 and isinstance(board.records[-2][y - 2][x - 1], Pawn) and board.records[-2][y - 1][x - 1] is None:
                    moves.append((y - 1, x - 1))

            if board.is_on_board(y, x + 1) and isinstance(board.grid[y][x + 1], Pawn) and board.grid[y][x + 1].color == "black":
                if (y - 1, x + 1) == board.en_passant_target:
                    moves.append((y - 1, x + 1))
                elif len(board.records) > 1 and isinstance(board.records[-2][y - 2][x + 1], Pawn) and board.records[-2][y - 1][x + 1] is None:
                    moves.append((y - 1, x + 1))

        elif self.color == "black" and y == 4:
            if board.is_on_board(y, x - 1) and isinstance(board.grid[y][x - 1], Pawn) and board.grid[y][x - 1].color == "white":
                if (y + 1, x - 1) == board.en_passant_target:
                    moves.append((y + 1, x - 1))
                elif len(board.records) > 1 and isinstance(board.records[-2][y + 2][x - 1], Pawn) and board.records[-2][y + 1][x - 1] is None:
                    moves.append((y + 1, x - 1))

            if board.is_on_board(y, x + 1) and isinstance(board.grid[y][x + 1], Pawn) and board.grid[y][x + 1].color == "white":
                if (y + 1, x + 1) == board.en_passant_target:
                    moves.append((y + 1, x + 1))
                elif len(board.records) > 1 and isinstance(board.records[-2][y + 2][x + 1], Pawn) and board.records[-2][y + 1][x + 1] is None:
                    moves.append((y + 1, x + 1))

        return moves


class Man:
    def __init__(self, color):
        self.color = color

    def find_move(self, board):
        pass  # Ход обрабатывается через события


class Computer:
    def __init__(self, color, engine, depth=15):
        self.color = color
        self.engine = engine

    def find_move(self, board):
        # Преобразуем текущее состояние доски в формат FEN и используем двигатель для поиска лучшего хода
        fen = board._get_fen(self.color)
        start, end = board.translate_to_coordinates(str(self.engine.get_best_move(fen)))
        piece = board.grid[start[0]][start[1]]
        return piece, end

    def close(self):
        # Закрываем двигатель после работы
        self.engine.close()


class Game:
    def __init__(self):
        self.board = Board()
        self.turn = "white"
        self.selected_piece = None
        self.legal_moves = []  # Легальные ходы для выбранной фигуры
        self.running = None  # Флаг состояния игры
        self.last_turn = "white"  # Последний ход
        self.halfmove_clock = 0  # Половинные ходы для правила 50 ходов

        # Настройки игры и дополнительные параметры
        self.mode = None
        self.puzzle_moves = []  # Верные ходы для задачек
        self.step_index = None
        self.think_time = 0  # Время на подумать для компьютера
        self.points = 0  # Количество очков за решение задачек

        # Игроки (Man | Computer)
        self.player_w = None
        self.player_b = None

    def set_players(self, a, b):
        # Распределение игроками цветов
        if a.color == "white":
            self.player_w = a
            self.player_b = b
        else:
            self.player_w = b
            self.player_b = a

    def set(self, mode="normal", fen=None, puzzle_moves=None):
        # Настройка игры и начального состояния доски
        self.running = True
        self.mode = mode
        if mode == "puzzle" and puzzle_moves:
            turn = fen.split()[1]  # Текущий ход по FEN
            self.puzzle_moves = puzzle_moves.split()
            self.step_index = 0
            self.turn = "white" if turn == "w" else "black"
        self.board.setup(fen)  # Если fen is None, то фигуры встают на начальные позиции

    def run(self):
        # Главный игровой цикл
        while self.running:
            for event in pg.event.get():
                self.handle_event(event)  # Работа с событиями

            if not self.running:
                break

            # Проверки на конец игры
            if self.board.halfmove_clock >= 50:
                print("Draw by 50-move rule!")
                self.running = False
            if self.board.is_threefold_repetition():
                print("Draw by threefold repetition!")
                self.running = False
            if self.board.is_checkmate(self.turn):
                print(f"Checkmate! {self.turn.capitalize()} loses!")
                self.running = False
            if self.board.is_pat(self.turn):
                print(f"Stalemate! {self.turn.capitalize()} draws!")
                self.running = False
            
            if self.mode == "puzzle":
                if self.step_index == len(self.puzzle_moves):
                    print("Puzzle solved!")
                    self.running = False

            # Переворот доски, если играют два человека
            if self.running and self.last_turn != self.turn and self.mode == "normal" and isinstance(self.player_w, Man) and isinstance(self.player_b, Man):
                self.board.flip()
                self.last_turn = self.turn

            # Если играет компьютер, то добавляем delay
            running_time = pg.time.get_ticks()

            if self.turn == "white" and isinstance(self.player_w, Computer) or self.turn == "black" and isinstance(self.player_b, Computer):
                if not self.think_time:
                    self.think_time = running_time + 2000
                if running_time > self.think_time:
                    if self.turn == "white":
                        self.handle_turn(self.player_w)
                    else:
                        self.handle_turn(self.player_b)
                    self.think_time = 0

            # Delay в задачках
            if self.mode == "puzzle" and self.step_index % 2 == 0:
                start, end = self.board.translate_to_coordinates(self.puzzle_moves[self.step_index])
                if not self.think_time:
                    self.think_time = running_time + 1000
                if running_time > self.think_time:
                    self.board.move_piece(self.board.grid[start[0]][start[1]], end[0], end[1])
                    self.turn = "black" if self.turn == "white" else "white"
                    self.step_index += 1
                    self.think_time = 0

            # Перерисовываем игровое поле
            screen.fill(LIGHT)
            self.board.draw()
            self.board.highlight_moves(self.legal_moves, self.selected_piece)
            pg.display.flip()

            clock.tick(30)  # FPS

    def handle_turn(self, player):
        # Обработка хода игрока
        if isinstance(player, Man):
            return  # Ход обрабатывается через события
        elif isinstance(player, Computer):
            if self.running:
                piece, move = player.find_move(self.board)
                if piece and move:
                    row, col = move
                    self.board.move_piece(piece, row, col)
                    self.turn = "black" if self.turn == "white" else "white"

    def handle_event(self, event):
        # Обработка событий PyGame
        if event.type == pg.QUIT or event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
            self.running = False
            pg.quit()
        elif event.type == pg.MOUSEBUTTONDOWN:
            row, col = self.board._translate_coordinates(int(event.pos[1] / square_size), int(event.pos[0] / square_size))
            self.handle_click(row, col)

    def handle_click(self, row, col):
        # Обработка кликов мыши
        player = self.player_w if self.turn == "white" else self.player_b
        # Если ход компьютера или это задачка, то запрещаем взаимодействие с его фигурами
        if isinstance(player, Computer) or self.mode == "puzzle" and self.step_index % 2 == 0:
            return

        piece = self.board.grid[row][col]
        if piece and piece.color == self.turn:
                # Выделяем фигуру и показываем её легальные ходы
                self.selected_piece = piece
                self.legal_moves = piece.get_legal_moves(self.board)
        elif self.selected_piece and (row, col) in self.legal_moves:
            # Выполняем ход
            if self.mode == "normal":
                if self.running:
                    self.board.move_piece(self.selected_piece, row, col)
                    self.turn = "black" if self.turn == "white" else "white"
            elif self.mode == "puzzle":
                # Проверяем правильность хода в задаче
                if self.step_index % 2 != 0:
                    expected = self.puzzle_moves[self.step_index]
                    start_position, end_position = self.board.translate_to_coordinates(expected)
                    if self.selected_piece.position == start_position and (row, col) == end_position:
                        self.board.move_piece(self.selected_piece, row, col)
                        self.turn = "black" if self.turn == "white" else "white"
                        if self.step_index + 1 < len(self.puzzle_moves):
                            self.step_index += 1
            self.selected_piece = None
            self.legal_moves = []
        else:
            self.legal_moves = []


def main():
    pg.init()  # Инициализация Pygame

    # Создаем основной объект игры, базу данных задачек и шахматный двигатель
    game = Game()
    puzzle_db = PuzzleDataBase()
    engine = ChessEngine(ENGINE)  # Инициализация шахматного двигателя

    # Считываем аргументы командной строки
    args = sys.argv

    # Проверка на минимальное количество аргументов
    if len(args) < 2:
        print("Error: Not enough arguments provided.")
        exit(1)

    mode = args[1].lower()

    if mode not in ("normal", "puzzle"):
        print(f"Error: '{mode}' is not a valid mode. Enter 'normal' or 'puzzle'.")
        sys.exit(1)

    if mode == "normal":
        foe = "man"
        color = "white"

        # Проверка аргументов для определения соперника
        if len(args) > 2:
            foe = args[2].lower()
            if foe not in ("man", "computer"):
                print(f"Error: '{foe}' is not a valid foe. Enter 'man' or 'computer'.")
                sys.exit(1)

        # Проверка аргументов для выбора цвета
        if len(args) > 3:
            color = args[3].lower()
            if color not in ("white", "black"):
                print("Error: Invalid color. Enter 'white' or 'black'.")
                sys.exit(1)

        # Настройка игры
        game.set(mode)

        # Настройка игроков в зависимости от выбранного соперника
        if foe == "man":
            game.set_players(Man("white"), Man("black"))
        else:
            game.set_players(Man(color), Computer("black" if color == "white" else "white", engine))

        # Если пользователь играет черными против компьютера, переворачиваем доску
        if color == "black" and foe == "computer":
            game.board.flip()
            pass

    elif mode == "puzzle":
        # Проверка на минимальное количество аргументов для 'puzzle'
        if len(args) < 3:
            print("Error: Puzzle index is required for 'puzzle' mode.")
            exit(1)

        # Проверка и получение индекса задачки
        try:
            puzzle_index = int(args[2])
        except ValueError:
            print("Error: Puzzle index must be an integer.")
            sys.exit(1)

        # Загрузка задачки из базы данных
        try:
            puzzle = puzzle_db.get_puzzle(puzzle_index)
        except ValueError:
            print(f"Error: No puzzle found for index {puzzle_index}")
            exit(1)

        # Настройка игры
        game.set(mode, fen=puzzle[1], puzzle_moves=puzzle[2])

    # Запуск игры
    try:
        game.run()
    finally:
        # Закрытие ресурсов после завершения игры
        engine.close()  # Закрываем двигатель
        puzzle_db.close()  # Закрываем базу данных задачек

    while True:
        for event in pg.event.get():
            if event.type == pg.QUIT or event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                pg.quit()
                sys.exit(0)

if __name__ == "__main__":
    main()