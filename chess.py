import pygame as pg

pg.init()

board_size = 800
square_size = board_size / 8
screen = pg.display.set_mode((board_size, board_size))

LIGHT = (222, 227, 230)
DARK = (140, 162, 173)

class Board:
    def __init__(self):
        self.grid = [[None for _ in range(8)] for _ in range(8)]  # Создаем пустую 8x8 доску
        self.setup()

    def get_valid_moves(self, board):
        return []

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
    def setup(self):
        for col in range(8):
            self.grid[1][col] = Pawn("black", (col, 1))
            self.grid[6][col] = Pawn("white", (col, 6))

        pieces = [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook]
        for col, piece in enumerate(pieces):
            self.grid[0][col] = piece("black", (col, 0))
            self.grid[7][col] = piece("white", (col, 7))
    
    def is_blank(self, col, row):
        return self.grid[row][col] is None
    
    def is_foe(self, col, row, color):
        piece = self.grid[row][col]
        return piece is not None and piece.color != color
    
    def is_on_board(self, col, row):
        return (-1 < col < 8) and (-1 < row < 8)
    
    def highlight_moves(self, moves, selected_piece):
        move_highlight = pg.Surface((square_size, square_size), pg.SRCALPHA)
        pg.draw.circle(move_highlight, (50, 50, 50, 120), (square_size / 2, square_size / 2), square_size / 5)
        capture_highlight = pg.Surface((square_size, square_size), pg.SRCALPHA)
        pg.draw.circle(capture_highlight, (50, 50, 50, 120), (square_size / 2, square_size / 2), square_size / 2, 7)
        for col, row in moves:
            target_piece = self.grid[row][col]
            if target_piece and target_piece.color != selected_piece.color:
                screen.blit(capture_highlight, (col * square_size, row * square_size))
            else:
                screen.blit(move_highlight, (col * square_size, row * square_size))

    def move_piece(self, piece, col, row):
        _col, _row = piece.position
        self.grid[_row][_col] = None
        piece.position = (col, row)
        self.grid[row][col] = piece

class Piece:
    def __init__(self, color, position):
        self.color = color
        self.position = position
        self.image = pg.image.load(f"pieces/{color}/{self.__class__.__name__.lower()}.png")
        self.image = pg.transform.smoothscale(self.image, (square_size, square_size))

    def _get_linear_moves(self, board, directions):
        moves = []
        x, y = self.position

        for dx, dy in directions:
            coord_x, coord_y = x + dx, y + dy
            while board.is_on_board(coord_x, coord_y):
                if board.is_blank(coord_x, coord_y):
                    moves.append((coord_x, coord_y))
                elif board.is_foe(coord_x, coord_y, self.color):
                    moves.append((coord_x, coord_y))
                    break
                else:
                    break
                coord_x += dx
                coord_y += dy
        
        return moves



class King(Piece):
    def get_valid_moves(self, board):
        moves = []
        x, y = self.position
        king_moves = [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]
        for dx, dy in king_moves:
            if board.is_on_board(x + dx, y + dy) and (board.is_blank(x + dx, y + dy) or board.is_foe(x + dx, y + dy, self.color)):
                moves.append((x + dx, y + dy))
        return moves


class Queen(Piece):
    def get_valid_moves(self, board):
        return self._get_linear_moves(board, directions=[(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)])


class Rook(Piece):
    def get_valid_moves(self, board):
        return self._get_linear_moves(board, directions=[(0, 1), (1, 0), (0, -1), (-1, 0)])


class Bishop(Piece):
    def get_valid_moves(self, board):
        return self._get_linear_moves(board, directions=[(1, 1), (1, -1), (-1, -1), (-1, 1)])


class Knight(Piece):
    def get_valid_moves(self, board):
        moves = []
        x, y = self.position
        knight_moves = [(2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2)]
        for dx, dy in knight_moves:
            if (board.is_on_board(x + dx, y + dy) and (board.is_blank(x + dx, y + dy) or board.is_foe(x + dx, y + dy, self.color))):
                moves.append((x + dx, y + dy))
        return moves



class Pawn(Piece):
    def get_valid_moves(self, board):
        moves = []
        x, y = self.position
        direction = -1 if self.color == "white" else 1

        if board.is_blank(x, y + direction):
            moves.append((x, y + direction))

        if (self.color == "white" and y == 6) or (self.color == "black" and y == 1):
            if board.is_blank(x, y + 2 * direction):
                moves.append((x, y + 2 * direction))
        
        for dx in [-1, 1]:
            if board.is_on_board(x + dx, y + direction) and board.is_foe(x + dx, y + direction, self.color):
                moves.append((x + dx, y + direction))
        
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
        self.valid_moves = []
        self.loop()

    def loop(self):
        while True:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    pg.quit()
                if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                    pg.quit()
                if event.type == pg.MOUSEBUTTONDOWN:
                    row, col = int(event.pos[1] / square_size), int(event.pos[0] / square_size)
                    self.handle_piece(row, col)
            screen.fill(LIGHT)
            self.board.draw()
            self.board.highlight_moves(self.valid_moves, self.selected_piece)
            pg.display.flip()
        
    def handle_piece(self, row, col):
        piece = self.board.grid[row][col]
        if piece and piece.color == self.turn:
            self.selected_piece = piece
            self.valid_moves = piece.get_valid_moves(self.board)
        elif self.selected_piece and (col, row) in self.valid_moves:
            self.board.move_piece(self.selected_piece, col, row)
            self.turn = "black" if self.turn == "white" else "white"
            self.selected_piece = None
            self.valid_moves = []
        else:
            self.valid_moves = []


game = Game()
