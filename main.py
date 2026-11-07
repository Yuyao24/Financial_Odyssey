import pygame
import sys

# Constants
GAME_W, GAME_H = 1920, 1080  # 16:9 logical resolution
FPS = 60

class Game:
    def __init__(self):
        # Init
        pygame.init()
        # Default windowed size (e.g. 1280x720) with resizable support
        self.screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
        pygame.display.set_caption("Credit Capital")
        self.clock = pygame.time.Clock()

        # Off-screen game surface
        self.game = pygame.Surface((GAME_W, GAME_H))

        # Game state
        self.player_pos = (GAME_W // 2, GAME_H // 2)
        self.running = True

        # Game Stats
        self.net_worth = 0
        self.credit_score = 0
        self.final_score = 0

    def run(self):
        # Main loop
        while self.running:
            # 1. Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False

            # 2. Update
            keys = pygame.key.get_pressed()
            x, y = self.player_pos
            if keys[pygame.K_LEFT]:
                x -= 5
            if keys[pygame.K_RIGHT]:
                x += 5
            if keys[pygame.K_UP]:
                y -= 5
            if keys[pygame.K_DOWN]:
                y += 5
            self.player_pos = (x, y)

            # 3. Draw to game surface
            self.game.fill((30, 30, 30))
            pygame.draw.rect(self.game, (0, 200, 255), (*self.player_pos, 40, 40))
            pygame.draw.circle(self.game, (255, 255, 255), (GAME_W // 2, 100), 30)

            # 4. Blit to screen (handles letterboxing)
            self.blit_game()

            # 5. Frame rate
            self.clock.tick(FPS)


    # Helper
    def blit_game(self):
        """Scale game to fit screen, centred, with black bars."""
        sw, sh = self.screen.get_size()
        scale = min(sw / GAME_W, sh / GAME_H)
        w, h = int(GAME_W * scale), int(GAME_H * scale)
        scaled = pygame.transform.scale(self.game, (w, h))
        self.screen.fill((0, 0, 0))
        self.screen.blit(scaled, ((sw - w) // 2, (sh - h) // 2))
        pygame.display.flip()

    # Calc final score
    def calculate_final_score(self, net_worth, credit_score, age):
        if credit_score <= 640:
            score_multiplier = 0.5
        elif credit_score <= 860:
            score_multiplier = 1.0
        elif credit_score <= 1120:
            score_multiplier = 1.3
        else:
            score_multiplier = 2.0

        self.final_score = net_worth * score_multiplier

if __name__ == '__main__':
    game = Game()
    game.run()

pygame.quit()
sys.exit()