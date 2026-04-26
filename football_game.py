from dataclasses import dataclass, field
import asyncio
import math
from pathlib import Path
import random
import sys

import pygame


WIDTH = 960
HEIGHT = 640
FPS = 60


LEVELS = [
    {"level": 1, "shots": 5, "target": 3, "keeper": 0.34},
    {"level": 2, "shots": 5, "target": 4, "keeper": 0.40},
    {"level": 3, "shots": 6, "target": 4, "keeper": 0.46},
    {"level": 4, "shots": 6, "target": 5, "keeper": 0.52},
    {"level": 5, "shots": 7, "target": 6, "keeper": 0.58},
]


@dataclass
class ShootoutState:
    level: int = 1
    shots: int = 5
    target: int = 3
    keeper: float = 0.34
    goals: int = 0
    attempts: int = 0
    saves: int = 0
    commentary: list[str] = field(default_factory=lambda: ["Welcome to Sports Arcade: Football."])


class FootballGame:
    def __init__(self, exit_on_close=True, quit_label="Quit App"):
        self.exit_on_close = exit_on_close
        self.quit_label = quit_label
        pygame.init()
        pygame.display.set_caption("Sports Arcade: Football")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 28, bold=True)
        self.small_font = pygame.font.SysFont("arial", 20)
        self.large_font = pygame.font.SysFont("arial", 52, bold=True)
        self.trophy_image = self.load_trophy_image()
        self.level_index = 0
        self.highest_unlocked = 0
        self.won_levels = set()
        self.state = ShootoutState()
        self.mode = "menu"
        self.aim = "center"
        self.ball_start = (WIDTH // 2, 512)
        self.ball_pos = self.ball_start
        self.ball_target = (WIDTH // 2, 205)
        self.ball_active = False
        self.kick_started_at = 0
        self.kick_duration = 620
        self.pending_result = None
        self.result_flash_until = 0
        self.result_label = ""
        self.keeper_side = "center"

    def load_trophy_image(self):
        path = Path(__file__).resolve().parent / "images" / "olenchic-ai-generated-9489516_1920.png"
        try:
            return pygame.image.load(path).convert_alpha()
        except (FileNotFoundError, pygame.error):
            return None

    async def run(self):
        running = True
        while running:
            now = pygame.time.get_ticks()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    running = self.handle_key(event.key, now)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    running = self.handle_click(event.pos)

            if self.mode == "playing":
                self.update_play(now)

            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)
            await asyncio.sleep(0)

        if self.exit_on_close:
            pygame.quit()
            sys.exit()

    def handle_key(self, key, now):
        if self.mode == "menu":
            number_keys = [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5]
            if key in number_keys:
                selected = number_keys.index(key)
                if selected <= self.highest_unlocked:
                    self.start_level(selected)
            elif key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_s):
                self.start_level(self.highest_unlocked)
            elif key in (pygame.K_ESCAPE, pygame.K_q):
                return False
        elif self.mode == "playing":
            if key in (pygame.K_ESCAPE, pygame.K_q):
                self.mode = "menu"
                self.ball_active = False
            elif key == pygame.K_LEFT:
                self.aim = "left"
            elif key in (pygame.K_DOWN, pygame.K_UP):
                self.aim = "center"
            elif key == pygame.K_RIGHT:
                self.aim = "right"
            elif key == pygame.K_SPACE:
                self.take_penalty(now)
        elif self.mode == "game_over":
            if key in (pygame.K_RETURN, pygame.K_r, pygame.K_SPACE):
                self.start_level(self.level_index)
            elif key in (pygame.K_ESCAPE, pygame.K_q):
                self.mode = "menu"
        elif self.mode == "level_complete":
            if key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_n):
                self.next_level()
            elif key in (pygame.K_ESCAPE, pygame.K_q):
                self.mode = "menu"
        elif self.mode == "trophy":
            if key in (pygame.K_RETURN, pygame.K_r, pygame.K_SPACE):
                self.start_game()
            elif key in (pygame.K_ESCAPE, pygame.K_q):
                self.mode = "menu"
        return True

    def handle_click(self, pos):
        if self.mode == "menu":
            for index, rect in enumerate(self.level_card_rects()):
                if rect.collidepoint(pos) and index <= self.highest_unlocked:
                    self.start_level(index)
                    return True
            if self.reset_progress_button_rect().collidepoint(pos):
                self.reset_progress()
            elif self.quit_button_rect().collidepoint(pos):
                return False
        elif self.mode == "playing":
            for aim, rect in self.aim_button_rects().items():
                if rect.collidepoint(pos):
                    self.aim = aim
                    return True
            if self.shoot_button_rect().collidepoint(pos):
                self.take_penalty(pygame.time.get_ticks())
        elif self.mode == "game_over":
            if self.restart_button_rect().collidepoint(pos):
                self.start_level(self.level_index)
            elif self.quit_button_rect().collidepoint(pos):
                self.mode = "menu"
        elif self.mode == "level_complete":
            if self.next_level_button_rect().collidepoint(pos):
                self.next_level()
            elif self.quit_button_rect().collidepoint(pos):
                self.mode = "menu"
        elif self.mode == "trophy":
            if self.restart_button_rect().collidepoint(pos):
                self.start_game()
            elif self.quit_button_rect().collidepoint(pos):
                self.mode = "menu"
        return True

    def start_game(self):
        self.reset_progress()
        self.start_level(0)

    def reset_progress(self):
        self.level_index = 0
        self.highest_unlocked = 0
        self.won_levels = set()
        self.state = ShootoutState()

    def start_level(self, index=None):
        if index is not None:
            self.level_index = index
        config = LEVELS[self.level_index]
        self.state = ShootoutState(
            level=config["level"],
            shots=config["shots"],
            target=config["target"],
            keeper=config["keeper"],
            commentary=[f"Level {config['level']}: score {config['target']} from {config['shots']} penalties."],
        )
        self.mode = "playing"
        self.aim = "center"
        self.ball_pos = self.ball_start
        self.ball_active = False
        self.pending_result = None
        self.result_label = ""
        self.keeper_side = "center"
        self.add_commentary("Choose a side, then press Space to shoot.")

    def next_level(self):
        if self.level_index >= len(LEVELS) - 1:
            self.mode = "trophy"
            return
        self.start_level(self.level_index + 1)

    def take_penalty(self, now):
        if self.ball_active or self.state.attempts >= self.state.shots:
            return

        self.keeper_side = random.choice(["left", "center", "right"])
        shot_quality = random.random()
        on_target = shot_quality > self.miss_chance()
        saved = on_target and self.keeper_side == self.aim and random.random() < self.state.keeper
        goal = on_target and not saved

        self.pending_result = {"goal": goal, "saved": saved, "missed": not on_target, "aim": self.aim}
        self.ball_target = self.target_for_aim(self.aim, not on_target)
        self.ball_start = (WIDTH // 2, 512)
        self.ball_pos = self.ball_start
        self.ball_active = True
        self.kick_started_at = now

    def update_play(self, now):
        if not self.ball_active:
            if self.has_won_level():
                self.complete_level()
            elif self.has_failed_level():
                self.mode = "game_over"
            return

        progress = min(1, (now - self.kick_started_at) / max(1, self.kick_duration))
        eased = 1 - (1 - progress) * (1 - progress)
        sx, sy = self.ball_start
        tx, ty = self.ball_target
        arc = math.sin(progress * math.pi) * 58
        self.ball_pos = (sx + (tx - sx) * eased, sy + (ty - sy) * eased - arc)

        if progress >= 1:
            self.resolve_penalty(now)

    def resolve_penalty(self, now):
        result = self.pending_result
        self.ball_active = False
        self.pending_result = None
        self.state.attempts += 1

        if result["goal"]:
            self.state.goals += 1
            self.result_label = "GOAL!"
            self.add_commentary(f"Goal into the {result['aim']} side.")
        elif result["saved"]:
            self.state.saves += 1
            self.result_label = "SAVED!"
            self.add_commentary(f"The keeper reads the {result['aim']} shot and saves.")
        else:
            self.result_label = "MISSED!"
            self.add_commentary(f"The {result['aim']} shot misses the target.")

        self.result_flash_until = now + 950
        if self.has_won_level():
            self.complete_level()
        elif self.has_failed_level():
            self.mode = "game_over"

    def miss_chance(self):
        return {"left": 0.12, "center": 0.08, "right": 0.12}[self.aim] + self.level_index * 0.01

    def target_for_aim(self, aim, missed):
        targets = {
            "left": (WIDTH // 2 - 132, 204),
            "center": (WIDTH // 2, 212),
            "right": (WIDTH // 2 + 132, 204),
        }
        x, y = targets[aim]
        if missed:
            if aim == "left":
                x = WIDTH // 2 - random.randint(245, 285)
                y = random.randint(170, 230)
            elif aim == "right":
                x = WIDTH // 2 + random.randint(245, 285)
                y = random.randint(170, 230)
            else:
                x = WIDTH // 2 + random.randint(-55, 55)
                y = random.randint(72, 100)
        return x, y

    def add_commentary(self, line):
        self.state.commentary.append(line)
        self.state.commentary = self.state.commentary[-4:]

    def has_won_level(self):
        return self.state.goals >= self.state.target

    def has_failed_level(self):
        remaining = self.state.shots - self.state.attempts
        return self.state.attempts >= self.state.shots or self.state.goals + remaining < self.state.target

    def complete_level(self):
        self.won_levels.add(self.level_index)
        self.highest_unlocked = min(len(LEVELS) - 1, max(self.highest_unlocked, self.level_index + 1))
        self.mode = "trophy" if self.level_index == len(LEVELS) - 1 else "level_complete"

    def draw(self):
        self.screen.fill((37, 126, 76))
        if self.mode == "menu":
            self.draw_menu()
        elif self.mode == "playing":
            self.draw_game()
        elif self.mode == "game_over":
            self.draw_game()
            self.draw_game_over()
        elif self.mode == "level_complete":
            self.draw_game()
            self.draw_level_complete()
        elif self.mode == "trophy":
            self.draw_game()
            self.draw_trophy()

    def draw_menu(self):
        self.screen.fill((18, 31, 40))
        title = self.large_font.render("Sports Arcade: Football", True, (238, 243, 235))
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 58))
        subtitle = self.small_font.render("Select an unlocked shootout. Win levels to open the next penalty test.", True, (224, 232, 222))
        self.screen.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, 125))

        for index, rect in enumerate(self.level_card_rects()):
            self.draw_level_card(index, rect)

        self.draw_button("Reset Progress", self.reset_progress_button_rect(), (77, 91, 96))
        self.draw_button(self.quit_label, self.quit_button_rect(), (105, 47, 47))
        hint = self.small_font.render("Press 1-5 for unlocked levels. Enter starts the latest unlocked level.", True, (183, 197, 189))
        self.screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 560))

    def draw_level_card(self, index, rect):
        level = LEVELS[index]
        won = index in self.won_levels
        unlocked = index <= self.highest_unlocked
        if won:
            fill = (39, 112, 76)
            border = (238, 243, 235)
            status = "WON"
        elif unlocked:
            fill = (38, 97, 143)
            border = (238, 243, 235)
            status = "UNLOCKED"
        else:
            fill = (47, 53, 57)
            border = (105, 115, 118)
            status = "LOCKED"

        pygame.draw.rect(self.screen, fill, rect, border_radius=8)
        pygame.draw.rect(self.screen, border, rect, 3, border_radius=8)
        title_color = (250, 252, 246) if unlocked else (196, 204, 202)
        body_color = (230, 238, 230) if unlocked else (178, 186, 184)
        level_text = self.font.render(f"Level {level['level']}", True, title_color)
        target = self.small_font.render(f"{level['target']} goals", True, body_color)
        shots = self.small_font.render(f"{level['shots']} shots", True, body_color)
        state = self.small_font.render(status, True, (238, 243, 235) if unlocked else (175, 181, 179))
        self.screen.blit(level_text, (rect.centerx - level_text.get_width() // 2, rect.y + 24))
        self.screen.blit(target, (rect.centerx - target.get_width() // 2, rect.y + 74))
        self.screen.blit(shots, (rect.centerx - shots.get_width() // 2, rect.y + 102))
        self.screen.blit(state, (rect.centerx - state.get_width() // 2, rect.y + 134))

    def draw_game(self):
        self.draw_pitch()
        self.draw_scoreboard()
        self.draw_goal()
        self.draw_keeper()
        self.draw_player()
        self.draw_ball()
        self.draw_controls()
        self.draw_result_flash()
        self.draw_commentary()

    def draw_pitch(self):
        self.screen.fill((47, 138, 82))
        for x in range(0, WIDTH, 120):
            color = (41, 126, 76) if (x // 120) % 2 == 0 else (53, 147, 88)
            pygame.draw.rect(self.screen, color, (x, 76, 120, HEIGHT - 76))
        pygame.draw.line(self.screen, (220, 237, 220), (0, 410), (WIDTH, 410), 4)
        pygame.draw.arc(self.screen, (220, 237, 220), (WIDTH // 2 - 160, 330, 320, 180), math.pi, 0, 4)
        pygame.draw.circle(self.screen, (220, 237, 220), (WIDTH // 2, 512), 5)

    def draw_scoreboard(self):
        pygame.draw.rect(self.screen, (18, 31, 40), (0, 0, WIDTH, 76))
        pygame.draw.line(self.screen, (238, 243, 235), (0, 75), (WIDTH, 75), 3)
        level = self.font.render(f"Level {self.state.level}/5", True, (238, 243, 235))
        score = self.font.render(
            f"Goals {self.state.goals}/{self.state.target}  Shots {self.state.attempts}/{self.state.shots}",
            True,
            (250, 252, 246),
        )
        controls = self.small_font.render("Left/Down/Right: Aim   Space: Shoot   Q/Esc: Levels", True, (198, 212, 204))
        self.screen.blit(level, (22, 12))
        self.screen.blit(score, (WIDTH // 2 - score.get_width() // 2, 12))
        self.screen.blit(controls, (WIDTH // 2 - controls.get_width() // 2, 48))

    def draw_goal(self):
        post = (238, 243, 235)
        net = (184, 211, 215)
        rect = pygame.Rect(WIDTH // 2 - 210, 118, 420, 154)
        pygame.draw.rect(self.screen, (25, 58, 68), rect)
        pygame.draw.rect(self.screen, post, rect, 7)
        for x in range(rect.x + 35, rect.right, 35):
            pygame.draw.line(self.screen, net, (x, rect.y + 4), (x, rect.bottom - 4), 1)
        for y in range(rect.y + 28, rect.bottom, 28):
            pygame.draw.line(self.screen, net, (rect.x + 4, y), (rect.right - 4, y), 1)

    def draw_keeper(self):
        base_x = {"left": WIDTH // 2 - 105, "center": WIDTH // 2, "right": WIDTH // 2 + 105}[self.keeper_side]
        y = 245
        diving = self.ball_active
        lean = {"left": -34, "center": 0, "right": 34}[self.keeper_side] if diving else 0
        pygame.draw.ellipse(self.screen, (24, 64, 48), (base_x - 42, y + 34, 84, 14))
        pygame.draw.circle(self.screen, (221, 176, 128), (base_x + lean // 3, y - 38), 13)
        pygame.draw.rect(self.screen, (231, 88, 59), (base_x - 16 + lean // 3, y - 24, 32, 48), border_radius=7)
        pygame.draw.line(self.screen, (231, 88, 59), (base_x - 12, y - 8), (base_x - 42 + lean, y - 28), 7)
        pygame.draw.line(self.screen, (231, 88, 59), (base_x + 12, y - 8), (base_x + 42 + lean, y - 28), 7)
        pygame.draw.circle(self.screen, (255, 255, 245), (base_x - 45 + lean, y - 30), 7)
        pygame.draw.circle(self.screen, (255, 255, 245), (base_x + 45 + lean, y - 30), 7)
        pygame.draw.line(self.screen, (27, 38, 48), (base_x - 10, y + 23), (base_x - 30, y + 54), 7)
        pygame.draw.line(self.screen, (27, 38, 48), (base_x + 10, y + 23), (base_x + 30, y + 54), 7)

    def draw_player(self):
        x, y = WIDTH // 2 - 62, 486
        kick = self.ball_active
        swing = int(math.sin(min(1, (pygame.time.get_ticks() - self.kick_started_at) / max(1, self.kick_duration)) * math.pi) * 34) if kick else 0
        pygame.draw.ellipse(self.screen, (29, 84, 52), (x - 30, y + 38, 70, 14))
        pygame.draw.circle(self.screen, (221, 176, 128), (x, y - 58), 13)
        pygame.draw.rect(self.screen, (61, 102, 196), (x - 16, y - 43, 32, 54), border_radius=8)
        pygame.draw.line(self.screen, (61, 102, 196), (x - 12, y - 30), (x - 35, y - 8), 6)
        pygame.draw.line(self.screen, (61, 102, 196), (x + 12, y - 30), (x + 34, y - 10), 6)
        pygame.draw.line(self.screen, (27, 38, 48), (x - 9, y + 9), (x - 26, y + 45), 7)
        pygame.draw.line(self.screen, (27, 38, 48), (x + 10, y + 9), (x + 25 + swing, y + 40 - swing // 3), 7)

    def draw_ball(self):
        x, y = self.ball_pos
        pygame.draw.circle(self.screen, (20, 29, 38), (int(x), int(y)), 12)
        pygame.draw.circle(self.screen, (238, 243, 235), (int(x), int(y)), 12, 3)
        pygame.draw.line(self.screen, (238, 243, 235), (int(x) - 8, int(y)), (int(x) + 8, int(y)), 2)
        pygame.draw.line(self.screen, (238, 243, 235), (int(x), int(y) - 8), (int(x), int(y) + 8), 2)

    def draw_controls(self):
        for aim, rect in self.aim_button_rects().items():
            color = (39, 112, 76) if aim == self.aim else (77, 91, 96)
            self.draw_button(aim.title(), rect, color)
        self.draw_button("Shoot", self.shoot_button_rect(), (38, 97, 143))

    def draw_result_flash(self):
        if pygame.time.get_ticks() >= self.result_flash_until or not self.result_label:
            return
        text = self.large_font.render(self.result_label, True, (255, 239, 160))
        shadow = self.large_font.render(self.result_label, True, (36, 54, 62))
        x = WIDTH // 2 - text.get_width() // 2
        self.screen.blit(shadow, (x + 3, 300 + 3))
        self.screen.blit(text, (x, 300))

    def draw_commentary(self):
        panel_y = HEIGHT - 106
        pygame.draw.rect(self.screen, (18, 31, 40), (0, panel_y, WIDTH, 106))
        pygame.draw.line(self.screen, (238, 243, 235), (0, panel_y), (WIDTH, panel_y), 3)
        heading = self.small_font.render("Commentary", True, (238, 243, 235))
        self.screen.blit(heading, (22, panel_y + 10))
        for index, line in enumerate(self.state.commentary[-3:]):
            text = self.small_font.render(line, True, (235, 241, 232))
            self.screen.blit(text, (22, panel_y + 38 + index * 22))

    def draw_game_over(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 10, 12, 178))
        self.screen.blit(overlay, (0, 0))
        panel = pygame.Rect(WIDTH // 2 - 220, HEIGHT // 2 - 180, 440, 360)
        pygame.draw.rect(self.screen, (236, 241, 229), panel, border_radius=8)
        pygame.draw.rect(self.screen, (238, 243, 235), panel, 4, border_radius=8)
        title = self.large_font.render("Shootout Lost", True, (22, 41, 37))
        final = self.font.render(f"Goals: {self.state.goals}/{self.state.target}", True, (31, 52, 48))
        shots = self.small_font.render(f"Level {self.state.level} shots taken: {self.state.attempts}/{self.state.shots}", True, (55, 74, 69))
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, panel.y + 34))
        self.screen.blit(final, (WIDTH // 2 - final.get_width() // 2, panel.y + 112))
        self.screen.blit(shots, (WIDTH // 2 - shots.get_width() // 2, panel.y + 152))
        self.draw_button("Retry Level", self.restart_button_rect(), (39, 112, 76))
        self.draw_button("Levels", self.quit_button_rect(), (77, 91, 96))

    def draw_level_complete(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 10, 12, 165))
        self.screen.blit(overlay, (0, 0))
        panel = pygame.Rect(WIDTH // 2 - 240, HEIGHT // 2 - 165, 480, 330)
        pygame.draw.rect(self.screen, (236, 241, 229), panel, border_radius=8)
        pygame.draw.rect(self.screen, (238, 243, 235), panel, 4, border_radius=8)
        title = self.large_font.render("Level Won", True, (22, 41, 37))
        result = self.font.render(f"Level {self.state.level}: {self.state.goals} goals", True, (31, 52, 48))
        next_config = LEVELS[self.level_index + 1]
        next_text = self.small_font.render(
            f"Next: score {next_config['target']} from {next_config['shots']} penalties",
            True,
            (55, 74, 69),
        )
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, panel.y + 34))
        self.screen.blit(result, (WIDTH // 2 - result.get_width() // 2, panel.y + 116))
        self.screen.blit(next_text, (WIDTH // 2 - next_text.get_width() // 2, panel.y + 158))
        self.draw_button("Next Level", self.next_level_button_rect(), (39, 112, 76))
        self.draw_button("Levels", self.quit_button_rect(), (77, 91, 96))

    def draw_trophy(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 10, 12, 178))
        self.screen.blit(overlay, (0, 0))
        panel = pygame.Rect(WIDTH // 2 - 280, HEIGHT // 2 - 235, 560, 470)
        pygame.draw.rect(self.screen, (236, 241, 229), panel, border_radius=8)
        pygame.draw.rect(self.screen, (238, 243, 235), panel, 4, border_radius=8)
        self.draw_won_label(panel)
        self.draw_trophy_image(panel)
        self.draw_button("Play Again", self.restart_button_rect(), (39, 112, 76))
        self.draw_button("Levels", self.quit_button_rect(), (77, 91, 96))

    def draw_trophy_image(self, panel):
        if not self.trophy_image:
            self.draw_cup(WIDTH // 2, panel.y + 190)
            return
        max_w = 430
        max_h = 300
        if self.trophy_image.get_width() <= 0 or self.trophy_image.get_height() <= 0:
            self.draw_cup(WIDTH // 2, panel.y + 190)
            return
        scale = min(max_w / self.trophy_image.get_width(), max_h / self.trophy_image.get_height())
        size = (int(self.trophy_image.get_width() * scale), int(self.trophy_image.get_height() * scale))
        image = pygame.transform.smoothscale(self.trophy_image, size)
        self.screen.blit(image, (panel.centerx - size[0] // 2, panel.y + 72))

    def draw_won_label(self, panel):
        text = self.large_font.render("WON!!", True, (39, 150, 82))
        self.screen.blit(text, (panel.centerx - text.get_width() // 2, panel.y + 18))

    def draw_cup(self, x, y):
        cup = (245, 190, 78)
        cup_shadow = (157, 103, 35)
        stem = (116, 132, 139)
        stem_shadow = (72, 88, 96)
        base = (35, 101, 148)
        base_shadow = (18, 58, 90)

        pygame.draw.arc(self.screen, cup_shadow, (x - 144, y - 56, 86, 96), 1.55, 4.75, 16)
        pygame.draw.arc(self.screen, cup_shadow, (x + 58, y - 56, 86, 96), -1.6, 1.6, 16)
        pygame.draw.rect(self.screen, cup_shadow, (x - 68, y - 74, 136, 98), border_radius=13)
        pygame.draw.rect(self.screen, cup, (x - 62, y - 68, 124, 86), border_radius=11)
        pygame.draw.arc(self.screen, cup, (x - 136, y - 48, 74, 80), 1.55, 4.75, 10)
        pygame.draw.arc(self.screen, cup, (x + 62, y - 48, 74, 80), -1.6, 1.6, 10)
        pygame.draw.rect(self.screen, stem_shadow, (x - 32, y + 18, 64, 76))
        pygame.draw.rect(self.screen, stem, (x - 26, y + 18, 52, 70))
        pygame.draw.rect(self.screen, base_shadow, (x - 116, y + 86, 232, 32), border_radius=7)
        pygame.draw.rect(self.screen, base, (x - 108, y + 88, 216, 24), border_radius=6)

    def draw_button(self, label, rect, color):
        pygame.draw.rect(self.screen, color, rect, border_radius=7)
        pygame.draw.rect(self.screen, (238, 243, 235), rect, 2, border_radius=7)
        text = self.font.render(label, True, (250, 252, 246))
        self.screen.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))

    def level_card_rects(self):
        card_w = 154
        gap = 18
        total_w = card_w * len(LEVELS) + gap * (len(LEVELS) - 1)
        start_x = WIDTH // 2 - total_w // 2
        return [pygame.Rect(start_x + index * (card_w + gap), 210, card_w, 190) for index in range(len(LEVELS))]

    def reset_progress_button_rect(self):
        return pygame.Rect(WIDTH // 2 - 250, 460, 230, 54)

    def restart_button_rect(self):
        if self.mode == "trophy":
            return pygame.Rect(WIDTH // 2 - 115, HEIGHT // 2 + 112, 230, 48)
        return pygame.Rect(WIDTH // 2 - 115, HEIGHT // 2 + 62, 230, 48)

    def next_level_button_rect(self):
        return pygame.Rect(WIDTH // 2 - 115, HEIGHT // 2 + 54, 230, 48)

    def quit_button_rect(self):
        if self.mode == "trophy":
            return pygame.Rect(WIDTH // 2 - 115, HEIGHT // 2 + 170, 230, 48)
        if self.mode == "game_over":
            return pygame.Rect(WIDTH // 2 - 115, HEIGHT // 2 + 122, 230, 48)
        if self.mode == "level_complete":
            return pygame.Rect(WIDTH // 2 - 115, HEIGHT // 2 + 112, 230, 48)
        return pygame.Rect(WIDTH // 2 + 20, 460, 230, 54)

    def aim_button_rects(self):
        return {
            "left": pygame.Rect(WIDTH // 2 - 300, 424, 140, 44),
            "center": pygame.Rect(WIDTH // 2 - 70, 424, 140, 44),
            "right": pygame.Rect(WIDTH // 2 + 160, 424, 140, 44),
        }

    def shoot_button_rect(self):
        return pygame.Rect(WIDTH // 2 - 95, 476, 190, 46)
