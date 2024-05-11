import sys
import random
import time
import copy
import pygame

pygame.init()

#! Constants
FPS = 60
MENU_WIDTH = 100
ROWS, COLS = 8, 8
OFFSET = 50
CELL_SIZE = 50
WIDTH, HEIGHT = 500, 500

BACKGROUND_COLOR = (70, 70, 70)
MOVE_HIGHLIGHT_COLOR = 'cyan'
ATTACKER_HIGHLIGHT_COLOR = 'yellow'
CAPTURE_HIGHLIGHT_COLOR = 'red'

w_directions = [(-1, 0), (0, -1), (0, 1)]
b_directions = [(0, -1), (1, 0), (0, 1)]
king_directions = [(0, -1), (-1, 0), (0, 1), (1, 0)]

LAST_PIECE_AMOUNT = 3

board_image = pygame.image.load('images/plastic_board.png')
board_image = pygame.transform.scale2x(board_image)

white_piece = pygame.transform.scale_by(pygame.image.load('images/white_piece.png'), 1.5)
black_piece = pygame.transform.scale_by(pygame.image.load('images/black_piece.png'), 1.5)
white_king = pygame.transform.scale_by(pygame.image.load('images/white_king.png'), 1.5)
black_king = pygame.transform.scale_by(pygame.image.load('images/black_king.png'), 1.5)

taking_sound = pygame.mixer.Sound('audio/taking.wav')
taking_sound.set_volume(0.6)

move_sound = pygame.mixer.Sound('audio/move.wav')

promote_sound = pygame.mixer.Sound('audio/promote.wav')
promote_sound.set_volume(0.3)

board = [
    [0, 0, 0, 0, 0, 0, 0, 0],
    ['b_p', 'b_p', 'b_p', 'b_p', 'b_p', 'b_p', 'b_p', 'b_p'],
    ['b_p', 'b_p', 'b_p', 'b_p', 'b_p', 'b_p', 'b_p', 'b_p'],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    ['w_p', 'w_p', 'w_p', 'w_p', 'w_p', 'w_p', 'w_p', 'w_p'],
    ['w_p', 'w_p', 'w_p', 'w_p', 'w_p', 'w_p', 'w_p', 'w_p'],
    [0, 0, 0, 0, 0, 0, 0, 0]
]

animation_fps = 120
animation_time = 0.6
min_animation_time = 0.3

highlight_cells_to_move = []
highlight_cells_that_can_capture = []
highlight_capture = []
last_positions= []
ignored_cells = []
move_dict = {}
animated_piece = ()
destination = ()

font = pygame.font.Font(None, 64)
end_text = ''
text_color = 'red'
game_state = 1 # 1 == playing, 0 == win, 2 == tie
rect_width, rect_height = 400, 80
rect_color = 'black'

current_side = random.choice(['w','b'])
w_can_take_pieces = False
b_can_take_pieces = False
draw_moves = True

selected_cell = None

#! Screen setup
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Turkish Chekers')
pygame.display.set_icon(white_piece)
clock = pygame.time.Clock()

def is_in_borders(row, col):
    """Check if given row and column indices are within the borders of the game board."""
    return 0 <= row < ROWS and 0 <= col < COLS

def is_empty(row, col, board = board):
    """Check if the specified cell on the board is empty."""
    if not board[row][col]:
        return True
    return False

moves = []
def find_all_possible_capture_moves(row, col, current_move=[], board=board):
    """Find all possible capture moves from the specified cell recursively."""
    cells = is_capture_possible(row, col, board)

    if cells:
        for taken_cell, pos in cells:
            if (taken_cell, pos) not in current_move:
                board2 = copy.deepcopy(board)
                board2[taken_cell[0]][taken_cell[1]] = 0
                board2[row][col] = 0
                board2[pos[0]][pos[1]] = board[row][col]

                new_move = copy.deepcopy(current_move)
                new_move.extend([(taken_cell, pos)])
                find_all_possible_capture_moves(pos[0], pos[1], new_move, board2)

    else:
        if tuple(current_move) not in moves:
            moves.append(tuple(current_move))

def is_capture_possible(row, col, board=board):
    """Checks if capturing moves are possible from the specified cell. If possible, returns them."""
    enemy_side = 'b' if current_side == 'w' else 'w'
    directions = w_directions if current_side == 'w' else b_directions

    cells = []
    if board[row][col][2] == 'p':
        for x, y in directions:
            cell_x, cell_y = row + x, col + y
            if is_in_borders(cell_x, cell_y) and not is_empty(cell_x, cell_y, board) and board[cell_x][cell_y][0] == enemy_side:
                cell2_x, cell2_y = cell_x + x, cell_y + y
                if is_in_borders(cell2_x, cell2_y) and is_empty(cell2_x, cell2_y, board):
                    cells.append([(cell_x, cell_y), (cell2_x, cell2_y)])

    elif board[row][col][2] == 'k':
        directions = king_directions
        for x, y in directions:
            for i in range(1, ROWS):
                cell_x, cell_y = row + x * i , col + y * i
                if is_in_borders(cell_x, cell_y):
                    if not is_empty(cell_x, cell_y, board):
                        if board[cell_x][cell_y][0] == enemy_side:
                            for j in range(1, ROWS):
                                cell2_x, cell2_y = cell_x + x * j, cell_y + y * j
                                if is_in_borders(cell2_x, cell2_y) and is_empty(cell2_x, cell2_y, board):
                                    cells.append([(cell_x, cell_y), (cell2_x, cell2_y)])
                                else: break
                            break
                        else: break
                else: break
    return cells

def get_longest_captures(moves):
    '''Returns the longest captures.'''
    return_list = []
    longest_move = 1
    for move in moves:
        if len(move) > longest_move:
            longest_move = len(move)

    for move in moves:
        if len(move) == longest_move:
            return_list.append(move)

    return return_list

def check_win():
    global game_state, end_text, text_color, rect_color

    b_piece_count = 0
    w_piece_count = 0
    for row in range(ROWS):
        for col in range(COLS):
            cell = board[row][col]
            if not is_empty(row, col):
                side = cell[0]
                if side == 'b':
                    b_piece_count += 1 
                else:
                    w_piece_count += 1

    # Win
    if b_piece_count == 0 or w_piece_count == 0:
        if game_state == 1:
            pygame.mixer.Sound('audio/win.wav').play()
            game_state = 0

    # Draw
    if b_piece_count == 1 and w_piece_count == 1:
        if (current_side == 'w' and not w_can_take_pieces) or (current_side == 'b' and not b_can_take_pieces):
            if game_state == 1:
                pygame.mixer.Sound('audio/tie.wav').play()
                game_state = 2

    if game_state == 0:
        if current_side == 'b':
            end_text = 'White Wins'
            text_color = 'white'
            rect_color = 'black'

        else:
            end_text = 'Black Wins'
            text_color = 'black'
            rect_color = 'white'

    elif game_state == 2:
        end_text = 'Tie'
        text_color = 'grey'

def check_promotion():
    """Promotes pieces if they reach the opposite end or they are the last pieces."""
    for col in range(COLS):
        if board[0][col] == 'w_p':
            board[0][col] = 'w_k'
            promote_sound.play()

        if board[ROWS-1][col] == 'b_p':
            board[ROWS-1][col] = 'b_k'
            promote_sound.play()

    promote_last_pieces()

def promote_last_pieces():
    '''Promotes the last pieces of either side.'''
    b_piece_count = 0
    w_piece_count = 0
    for row in range(ROWS):
        for col in range(COLS):
            cell = board[row][col]
            if not is_empty(row, col):
                side = cell[0]
                if side == 'b':
                    b_piece_count += 1 
                else:
                    w_piece_count += 1

    if b_piece_count <= LAST_PIECE_AMOUNT:
        for row in range(ROWS):
            for col in range(COLS):
                cell = board[row][col]
                if cell:
                    if cell[0] == 'b': board[row][col] = 'b_k'

    if w_piece_count <= LAST_PIECE_AMOUNT:
        for row in range(ROWS):
            for col in range(COLS):
                cell = board[row][col]
                if cell:
                    if cell[0] == 'w': board[row][col] = 'w_k'

def highlight_movement(row, col):
    '''Returns avaible movement for given cell.'''
    directions = w_directions if current_side == 'w' else b_directions
    highlight_cells = []
    if board[row][col][2] == 'p':
        for x, y in directions:
            cell_x, cell_y = row + x, col + y
            if is_in_borders(cell_x, cell_y) and is_empty(cell_x, cell_y):
                highlight_cells.append((cell_x, cell_y))
    else:
        for direction in king_directions:
            for i in range(1, 8):
                cell_x, cell_y = row + direction[0] * i, col + direction[1] * i
                if is_in_borders(cell_x, cell_y) and is_empty(cell_x, cell_y):
                    highlight_cells.append((cell_x, cell_y))
                else:
                    break

    return highlight_cells

def flatten_tuple(tuple_to_unpack):
    """Flattens a nested tuple structure."""
    unpacked = []
    for item in tuple_to_unpack:
        if isinstance(item, tuple):
            unpacked.extend(flatten_tuple(item))
        else:
            unpacked.append(item)
    return unpacked

def group_items_in_pairs(lst):
    """Groups items in a list into pairs."""
    paired_items = []
    for i in range(0, len(lst), 2):
        if i + 1 < len(lst):
            paired_items.append([lst[i], lst[i + 1]])
    return paired_items

def highlight_cells_between(screen, start, end):
    points = []

    if start[0] == end[0]:  # Horizontal movement
        min_col, max_col = min(start[1], end[1]), max(start[1], end[1])
        points = [(start[0], col) for col in range(min_col, max_col + 1)]
    elif start[1] == end[1]:  # Vertical movement
        min_row, max_row = min(start[0], end[0]), max(start[0], end[0])
        points = [(row, start[1]) for row in range(min_row, max_row + 1)]

    # Highlight cells
    for point in points:
        pygame.draw.rect(screen, CAPTURE_HIGHLIGHT_COLOR, (point[1] * CELL_SIZE + OFFSET, point[0] * CELL_SIZE + OFFSET, 50, 50))

def draw():
    # Draw the board
    screen.blit(board_image,(0,0))

    if moves and draw_moves:
        for move in moves:
            flat_list = group_items_in_pairs(flatten_tuple(move))

            start = selected_cell
            end = flat_list[0]
            highlight_cells_between(screen, start, end)

            for i in range(len(flat_list) -1):
                start = flat_list[i]
                end = flat_list[i + 1]
                highlight_cells_between(screen, start, end)

                pygame.draw.rect(screen, CAPTURE_HIGHLIGHT_COLOR, (flat_list[i][1] * CELL_SIZE + OFFSET, flat_list[i][0] * CELL_SIZE + OFFSET, 50, 50))

    if highlight_cells_that_can_capture:
        for row, col in highlight_cells_that_can_capture:
            pygame.draw.rect(screen, ATTACKER_HIGHLIGHT_COLOR, (col * CELL_SIZE + OFFSET, row * CELL_SIZE + OFFSET, 50, 50))

    # Draw pieces
    for row in range(ROWS):
        for col in range(COLS):
            if board[row][col] and (row, col) not in ignored_cells:
                match board[row][col]:
                    case 'w_p': image = white_piece
                    case 'w_k': image = white_king
                    case 'b_p': image = black_piece
                    case 'b_k': image = black_king
                
                screen.blit(image, (col * CELL_SIZE + OFFSET, row * CELL_SIZE + OFFSET))

    # Highlight avaible spaces to move
    if highlight_cells_to_move:
        for row, col in highlight_cells_to_move:
            pygame.draw.rect(screen, MOVE_HIGHLIGHT_COLOR, (col * CELL_SIZE + OFFSET, row * CELL_SIZE + OFFSET, 50, 50))

    # Draw end text
    if end_text:
        rect_x, rect_y = (WIDTH - rect_width) // 2, (HEIGHT - rect_height) // 2
        pygame.draw.rect(screen, rect_color, (rect_x, rect_y, rect_width, rect_height))

        text = font.render(end_text, True, text_color)
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(text, text_rect)

    # Draw the turn indicator
    if game_state == 1:
        if current_side == 'w':
            screen.blit(white_piece, (WIDTH - 50, 0))
        else:
            screen.blit(black_piece, (WIDTH - 50, 0))

def easing_func(t):
    return 1 if t == 1 else 1 - 2 ** (-8 * t)

def animate_movement(start_cell, end_cell, taken_cell=None, total_time=animation_time):
    start_time = time.perf_counter()
    frames = int(total_time * animation_fps)
    frame_duration = 1 / animation_fps

    # Get the coordinates of the pieces and turn them into vectors
    start_pos = pygame.math.Vector2(start_cell[1] * CELL_SIZE + OFFSET, start_cell[0] * CELL_SIZE + OFFSET)
    end_pos = pygame.math.Vector2(end_cell[1] * CELL_SIZE + OFFSET, end_cell[0] * CELL_SIZE + OFFSET)

    if taken_cell:
        match board[start_cell[0]][start_cell[1]]:
            case 'w_p': image = white_piece
            case 'w_k': image = white_king
            case 'b_p': image = black_piece
            case 'b_k': image = black_king
    else:
        match board[end_cell[0]][end_cell[1]]:
            case 'w_p': image = white_piece
            case 'w_k': image = white_king
            case 'b_p': image = black_piece
            case 'b_k': image = black_king

    flag1 = True
    for _ in range(frames):
        elapsed_time = time.perf_counter() - start_time
        if elapsed_time >= total_time:
            break

        eased_point = pygame.math.Vector2.lerp(start_pos, end_pos, easing_func(elapsed_time / total_time))
        if taken_cell:
            taken_cell_pos = pygame.math.Vector2((taken_cell[1] * CELL_SIZE + OFFSET, taken_cell[0] * CELL_SIZE + OFFSET))
            if eased_point[0] >= taken_cell_pos[0] and eased_point[1] >= taken_cell_pos[1] and flag1:
                taking_sound.play()
                ignored_cells.append(taken_cell)
                flag1 = False
        draw()

        screen.blit(image, eased_point)
        pygame.display.flip()

        # Ensure constant frame rate
        time_to_sleep = frame_duration - (time.perf_counter() - start_time) % frame_duration
        time.sleep(time_to_sleep)

    if not taken_cell: 
        move_sound.play()

run = True
while run:
    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False

        # Keyboard Input
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                run = False

        # Mouse Input
        if event.type == pygame.MOUSEBUTTONDOWN:
            x,y = pygame.mouse.get_pos()

            # Check if the coordinates are in the game window.
            if OFFSET < x < WIDTH - OFFSET and OFFSET < y < HEIGHT - OFFSET and game_state == 1:
                x -= OFFSET
                y -= OFFSET

                # Get the cell from coordinates.
                row, col = y // CELL_SIZE, x // CELL_SIZE

                # If player clicks on an avaible spot for capturing, make the move.
                if move_dict and (row,col) in move_dict:
                    move = move_dict[(row,col)]
                    animated_piece = selected_cell
                    highlight_cells_that_can_capture = []
                    draw_moves = False

                    for i in range(len(move)):
                        taken_cell, destination = move[i][0], move[i][1]
                        ignored_cells.append(animated_piece)

                        step_time = max(animation_time - 0.1 * i, min_animation_time)
                        animate_movement(animated_piece, destination, taken_cell=taken_cell, total_time=step_time)

                        # Remove the taken piece
                        board[destination[0]][destination[1]] = board[animated_piece[0]][animated_piece[1]]
                        board[animated_piece[0]][animated_piece[1]] = 0
                        board[taken_cell[0]][taken_cell[1]] = 0
                        animated_piece = destination

                    moves = []
                    move_dict = {}
                    ignored_cells = []
                    draw_moves = True
                    selected_cell = None

                    current_side = 'w' if current_side == 'b' else 'b'

                if board[row][col]:
                    if board[row][col][0] == current_side:
                        # If there is no avaible capture for current side, get higlight positions for the selected cell.
                        if (current_side == 'w' and not w_can_take_pieces) or (current_side == 'b' and not b_can_take_pieces):
                            highlight_cells_to_move = highlight_movement(row, col)
                            selected_cell = (row, col)

                        # If there is avaible captures for current side, get the avaible captures.
                        if (current_side == 'w' and w_can_take_pieces) or (current_side == 'b' and b_can_take_pieces) \
                            and highlight_cells_that_can_capture and (row, col) in highlight_cells_that_can_capture:

                            selected_cell = (row, col)
                            moves = []
                            move_dict = {}
                            find_all_possible_capture_moves(row, col)
                            moves = get_longest_captures(moves)

                            for move in moves:
                                move_dict[move[-1][1]] = move

                # If clicked cell is in the higlighted cells, move the piece.
                if highlight_cells_to_move:
                    if (row,col) in highlight_cells_to_move:
                        animated_piece = selected_cell
                        destination = (row, col)
                        ignored_cells = [destination]
                        board[row][col] = board[selected_cell[0]][selected_cell[1]]

                        board[selected_cell[0]][selected_cell[1]] = 0
                        selected_cell = None
                        highlight_cells_to_move = []
                        current_side = 'w' if current_side == 'b' else 'b'

                        animate_movement(animated_piece, destination)
                        animated_piece = None
                        destination = None
                        ignored_cells = []

    w_can_take_pieces = False
    b_can_take_pieces = False

    check_promotion()
    # Iterate over the board and check for possible captures for current side.
    for row in range(ROWS):
        for col in range(COLS):
            if current_side == 'w':
                if not is_empty(row, col) and board[row][col][0] == 'w' and is_capture_possible(row, col):
                    w_can_take_pieces = True
                    if (row, col) not in highlight_cells_that_can_capture:
                        highlight_cells_that_can_capture.append((row,col))

            elif current_side == 'b':
                if not is_empty(row, col) and board[row][col][0] == 'b' and is_capture_possible(row, col):
                    b_can_take_pieces = True
                    if (row, col) not in highlight_cells_that_can_capture:
                        highlight_cells_that_can_capture.append((row,col))

    check_win()

    screen.fill(BACKGROUND_COLOR)
    draw()
    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()
