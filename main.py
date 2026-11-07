import pygame
import sys

# --- Constants ---
GAME_W, GAME_H = 1920, 1080  # 16:9 logical resolution
FPS = 60

# --- Init ---
pygame.init()
info = pygame.display.Info()
screen = pygame.display.set_mode(
    (info.current_w, info.current_h),
    pygame.NOFRAME
)
pygame.display.set_caption("Credit Capital")
clock = pygame.time.Clock()

# Off-screen game surface
game = pygame.Surface((GAME_W, GAME_H))

# --- Game state ---
player_pos = (GAME_W // 2, GAME_H // 2)
running = True

# --- Helper ---
def blit_game():
    """Scale game to fit screen, centred, with black bars."""
    sw, sh = screen.get_size()
    scale = min(sw / GAME_W, sh / GAME_H)
    w, h = int(GAME_W * scale), int(GAME_H * scale)
    scaled = pygame.transform.scale(game, (w, h))
    screen.fill((0, 0, 0))
    screen.blit(scaled, ((sw - w) // 2, (sh - h) // 2))
    pygame.display.flip()

# --- Main loop ---
while running:
    # 1. Events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_F11:
                screen = pygame.display.set_mode(
                    (info.current_w, info.current_h),
                    0 if pygame.NOFRAME & screen.get_flags() else pygame.NOFRAME
                )

    # 2. Update
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:
        player_pos = (player_pos[0] - 5, player_pos[1])
    if keys[pygame.K_RIGHT]:
        player_pos = (player_pos[0] + 5, player_pos[1])
    if keys[pygame.K_UP]:
        player_pos = (player_pos[0], player_pos[1] - 5)
    if keys[pygame.K_DOWN]:
        player_pos = (player_pos[0], player_pos[1] + 5)

    # 3. Draw to game surface
    game.fill((30, 30, 30))
    pygame.draw.rect(game, (0, 200, 255), (*player_pos, 40, 40))
    pygame.draw.circle(game, (255, 255, 255), (GAME_W // 2, 100), 30)

    # 4. Blit to screen (handles letterboxing)
    blit_game()

    # 5. Frame rate
    clock.tick(FPS)


def final_score(net_worth, credit_score):
    if credit_score <= 640:
        score_muiltiplier = 0.5
    elif credit_score <= 860:
        score_muiltiplier = 1.0
    elif credit_score <= 1120:
        score_muiltiplier = 1.3
    elif credit_score > 1400:
        score_muiltiplier = 2.0

    score = net_worth * score_muiltiplier
    return score

pygame.quit()
sys.exit()