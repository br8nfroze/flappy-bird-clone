import pygame
import random
import sys

# --- Configuration & Constants ---
SCREEN_WIDTH = 400
SCREEN_HEIGHT = 600
GRAVITY = 0.25
FLAP_STRENGTH = -6.5
PIPE_SPEED = 3
PIPE_GAP = 150
PIPE_FREQUENCY = 1500  # milliseconds

# Colors
WHITE = (255, 255, 255)
BLUE = (135, 206, 235)
YELLOW = (255, 255, 0)
GREEN = (0, 200, 0)

class Bird:
    def __init__(self):
        self.x = 50
        self.y = SCREEN_HEIGHT // 2
        self.velocity = 0
        self.radius = 15

    def flap(self):
        self.velocity = FLAP_STRENGTH

    def update(self):
        self.velocity += GRAVITY
        self.y += self.velocity

    def draw(self, screen):
        pygame.draw.circle(screen, YELLOW, (int(self.x), int(self.y)), self.radius)

    def get_rect(self):
        return pygame.Rect(self.x - self.radius, self.y - self.radius, self.radius * 2, self.radius * 2)

class Pipe:
    def __init__(self, x):
        self.x = x
        self.height = random.randint(100, 400)
        self.passed = False
        self.width = 50

    def update(self):
        self.x -= PIPE_SPEED

    def draw(self, screen):
        # Top Pipe
        pygame.draw.rect(screen, GREEN, (self.x, 0, self.width, self.height))
        # Bottom Pipe
        pygame.draw.rect(screen, GREEN, (self.x, self.height + PIPE_GAP, self.width, SCREEN_HEIGHT))

    def get_rects(self):
        top_rect = pygame.Rect(self.x, 0, self.width, self.height)
        bottom_rect = pygame.Rect(self.x, self.height + PIPE_GAP, self.width, SCREEN_HEIGHT)
        return top_rect, bottom_rect

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Flappy Bird Clone")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 32)

    bird = Bird()
    pipes = [Pipe(SCREEN_WIDTH)]
    score = 0
    last_pipe_time = pygame.time.get_ticks()
    game_active = True

    while True:
        # 1. Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if game_active:
                        bird.flap()
                    else:
                        # Restart Game
                        bird = Bird()
                        pipes = [Pipe(SCREEN_WIDTH)]
                        score = 0
                        last_pipe_time = pygame.time.get_ticks()
                        game_active = True

        if game_active:
            # 2. Update Physics
            bird.update()

            # Pipe Generation
            current_time = pygame.time.get_ticks()
            if current_time - last_pipe_time > PIPE_FREQUENCY:
                pipes.append(Pipe(SCREEN_WIDTH))
                last_pipe_time = current_time

            # Move Pipes & Scoring
            for pipe in pipes:
                pipe.update()
                if not pipe.passed and pipe.x + pipe.width < bird.x - bird.radius:
                    score += 1
                    pipe.passed = True

            # Remove off-screen pipes
            pipes = [p for p in pipes if p.x + p.width > 0]

            # 3. Collision Detection
            bird_rect = bird.get_rect()
            for pipe in pipes:
                top_p, bot_p = pipe.get_rects()
                if bird_rect.colliderect(top_p) or bird_rect.colliderect(bot_p):
                    game_active = False

            if bird.y - bird.radius <= 0 or bird.y + bird.radius >= SCREEN_HEIGHT:
                game_active = False

        # 4. Drawing
        screen.fill(BLUE)  # Background

        for pipe in pipes:
            pipe.draw(screen)

        bird.draw(screen)

        # Display Score
        score_surface = font.render(f"Score: {score}", True, WHITE)
        screen.blit(score_surface, (10, 10))

        if not game_active:
            over_surface = font.render("GAME OVER", True, WHITE)
            screen.blit(over_surface, over_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
            restart_surface = font.render("Press Space to restart", True, WHITE)
            screen.blit(restart_surface, restart_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40)))

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
