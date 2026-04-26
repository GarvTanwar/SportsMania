from dataclasses import dataclass, field
import math
from pathlib import Path
import random
import sys

import pygame

from ball import Ball
from scoreboard import Scoreboard


WIDTH = 960
HEIGHT = 640
FPS = 60
MAX_WICKETS = 10


LEVELS = [
    {"level": 1, "overs": 2, "target": 18},
    {"level": 2, "overs": 3, "target": 34},
    {"level": 3, "overs": 4, "target": 54},
    {"level": 4, "overs": 5, "target": 78},
    {"level": 5, "overs": 6, "target": 105},
]


@dataclass
class MatchState:
    level: int = 1
    overs: int = 2
    target: int = 18
    total_balls: int = 12
    runs: int = 0
    wickets: int = 0
    balls: int = 0
    commentary: list[str] = field(default_factory=lambda: ["Welcome to Sports Arcade: Cricket."])


class CricketGame:
    def __init__(self, exit_on_close=True, quit_label="Quit App"):
        self.exit_on_close = exit_on_close
        self.quit_label = quit_label
        pygame.init()
        pygame.display.set_caption("Sports Arcade: Cricket")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.scoreboard = Scoreboard(WIDTH)
        self.font = pygame.font.SysFont("arial", 28, bold=True)
        self.small_font = pygame.font.SysFont("arial", 20)
        self.large_font = pygame.font.SysFont("arial", 52, bold=True)
        self.trophy_image = self.load_trophy_image()

        self.ball = Ball((WIDTH // 2, 150), 475, WIDTH // 2)
        self.state = MatchState()
        self.level_index = 0
        self.highest_unlocked = 0
        self.won_levels = set()
        self.mode = "menu"
        self.next_delivery_at = 0
        self.message_flash_until = 0
        self.swing_until = 0
        self.swing_shot = None
        self.last_dismissal = ""
        self.dismissal_flash_until = 0

    def load_trophy_image(self):
        path = Path(__file__).resolve().parent / "images" / "olenchic-ai-generated-9489516_1920.png"
        try:
            return pygame.image.load(path).convert_alpha()
        except (FileNotFoundError, pygame.error):
            return None

    def run(self):
        """Main game loop: handle input, update active scene, then redraw at a fixed FPS."""
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

        pygame.quit()
        if self.exit_on_close:
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
                self.ball.reset()
                return True
            shot = {
                pygame.K_LEFT: "defensive",
                pygame.K_DOWN: "ground",
                pygame.K_RIGHT: "lofted",
                pygame.K_SPACE: "power",
            }.get(key)
            if shot:
                self.play_shot(shot, now)
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
        self.state = MatchState()

    def start_level(self, index=None):
        if index is not None:
            self.level_index = index
        config = LEVELS[self.level_index]
        self.state = MatchState(
            level=config["level"],
            overs=config["overs"],
            target=config["target"],
            total_balls=config["overs"] * 6,
            commentary=[f"Level {config['level']}: chase {config['target']} in {config['overs']} overs."],
        )
        self.ball.reset()
        self.mode = "playing"
        self.next_delivery_at = pygame.time.get_ticks() + 1000
        self.swing_until = 0
        self.swing_shot = None
        self.last_dismissal = ""
        self.dismissal_flash_until = 0
        self.add_commentary("Watch the ball and time your shot.")

    def next_level(self):
        if self.level_index >= len(LEVELS) - 1:
            self.mode = "trophy"
            return
        self.start_level(self.level_index + 1)

    def update_play(self, now):
        if self.has_won_level():
            self.complete_level()
            return

        if self.has_failed_level():
            self.mode = "game_over"
            return

        if not self.ball.active and now >= self.next_delivery_at:
            self.ball.bowl()
            self.add_commentary("Bowler runs in...")

        self.ball.update()
        if self.ball.resolved:
            self.resolve_missed_ball()

    def play_shot(self, shot, now):
        if not self.ball.is_in_hittable_zone():
            self.message_flash_until = now + 500
            return

        self.swing_shot = shot
        self.swing_until = now + 320
        timing = self.classify_timing(self.ball.timing_delta())
        runs, wicket = self.score_delivery(shot, timing)

        # Scoring logic: every completed delivery is one legal ball. Timing determines the
        # base outcome pool, while shot choice nudges risk and boundary potential.
        self.state.balls += 1
        if wicket:
            self.state.wickets += 1
            self.last_dismissal = "CAUGHT"
            self.dismissal_flash_until = now + 900
            self.add_commentary(f"{timing.title()} timing on the {shot} shot. OUT!")
        else:
            self.state.runs += runs
            if runs == 0:
                self.add_commentary(f"{timing.title()} timing. Dot ball.")
            elif runs in (4, 6):
                self.add_commentary(f"{timing.title()} timing! {runs} runs with a {shot} shot.")
            else:
                self.add_commentary(f"{timing.title()} timing. They run {runs}.")

        self.finish_delivery(now)

    def resolve_missed_ball(self):
        self.state.balls += 1
        if self.ball.is_hitting_stumps():
            self.state.wickets += 1
            self.last_dismissal = "BOWLED"
            self.dismissal_flash_until = pygame.time.get_ticks() + 900
            self.add_commentary("Missed it. The ball crashes into the stumps. Bowled!")
        elif random.random() < 0.08:
            self.state.wickets += 1
            self.last_dismissal = "EDGE"
            self.dismissal_flash_until = pygame.time.get_ticks() + 900
            self.add_commentary("Loose leave outside off. Thin edge, caught behind!")
        else:
            self.add_commentary("The ball misses bat and stumps. Dot ball.")
        self.finish_delivery(pygame.time.get_ticks())

    def finish_delivery(self, now):
        self.ball.reset()
        if self.has_won_level():
            self.complete_level()
        elif self.has_failed_level():
            self.mode = "game_over"
        else:
            self.next_delivery_at = now + random.randint(1200, 2200)

    def complete_level(self):
        self.won_levels.add(self.level_index)
        self.highest_unlocked = min(len(LEVELS) - 1, max(self.highest_unlocked, self.level_index + 1))
        self.mode = "trophy" if self.level_index == len(LEVELS) - 1 else "level_complete"

    def classify_timing(self, delta):
        if delta <= 22:
            return "perfect"
        if delta <= 55:
            return "good"
        return "poor"

    def score_delivery(self, shot, timing):
        if timing == "perfect":
            pools = {
                "defensive": [(0, 0.08), (1, 0.40), (2, 0.26), (4, 0.22), (6, 0.04)],
                "ground": [(1, 0.25), (2, 0.24), (3, 0.12), (4, 0.34), (6, 0.05)],
                "lofted": [(1, 0.10), (2, 0.10), (4, 0.36), (6, 0.38), ("W", 0.06)],
                "power": [(0, 0.04), (2, 0.08), (4, 0.34), (6, 0.45), ("W", 0.09)],
            }
        elif timing == "good":
            pools = {
                "defensive": [(0, 0.18), (1, 0.55), (2, 0.22), (3, 0.05)],
                "ground": [(0, 0.10), (1, 0.31), (2, 0.27), (3, 0.12), (4, 0.20)],
                "lofted": [(0, 0.16), (1, 0.18), (2, 0.20), (3, 0.08), (4, 0.24), ("W", 0.14)],
                "power": [(0, 0.22), (1, 0.12), (2, 0.14), (4, 0.26), (6, 0.10), ("W", 0.16)],
            }
        else:
            pools = {
                "defensive": [(0, 0.70), (1, 0.18), ("W", 0.12)],
                "ground": [(0, 0.54), (1, 0.22), (2, 0.08), ("W", 0.16)],
                "lofted": [(0, 0.42), (1, 0.08), (4, 0.12), ("W", 0.38)],
                "power": [(0, 0.38), (4, 0.10), (6, 0.06), ("W", 0.46)],
            }

        outcome = self.weighted_choice(pools[shot])
        return (0, True) if outcome == "W" else (outcome, False)

    def weighted_choice(self, weighted_items):
        roll = random.random()
        cumulative = 0
        for item, weight in weighted_items:
            cumulative += weight
            if roll <= cumulative:
                return item
        return weighted_items[-1][0]

    def add_commentary(self, line):
        self.state.commentary.append(line)
        self.state.commentary = self.state.commentary[-4:]

    def has_won_level(self):
        return self.state.runs >= self.state.target

    def has_failed_level(self):
        return self.state.balls >= self.state.total_balls or self.state.wickets >= MAX_WICKETS

    def draw(self):
        self.screen.fill((57, 128, 78))
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
        self.screen.fill((18, 31, 34))
        title = self.large_font.render("Sports Arcade: Cricket", True, (245, 190, 78))
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 58))

        subtitle = self.small_font.render("Select an unlocked chase. Win levels to open the next target.", True, (224, 232, 222))
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
            border = (245, 190, 78)
            status = "WON"
        elif unlocked:
            fill = (40, 73, 92)
            border = (245, 190, 78)
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
        self.screen.blit(level_text, (rect.centerx - level_text.get_width() // 2, rect.y + 24))

        target = self.small_font.render(f"Target {level['target']}", True, body_color)
        overs = self.small_font.render(f"{level['overs']} overs", True, body_color)
        state = self.small_font.render(status, True, (245, 190, 78) if unlocked else (175, 181, 179))
        self.screen.blit(target, (rect.centerx - target.get_width() // 2, rect.y + 74))
        self.screen.blit(overs, (rect.centerx - overs.get_width() // 2, rect.y + 102))
        self.screen.blit(state, (rect.centerx - state.get_width() // 2, rect.y + 134))

    def draw_game(self):
        self.draw_field()
        self.scoreboard.draw(self.screen, self.state)
        self.draw_players()
        self.draw_ball()
        self.draw_dismissal_flash()
        self.draw_commentary()

    def draw_field(self):
        pygame.draw.ellipse(self.screen, (68, 145, 86), (75, 100, 810, 510))
        pygame.draw.rect(self.screen, (201, 174, 116), (WIDTH // 2 - 52, 140, 104, 390), border_radius=4)
        pygame.draw.rect(self.screen, (226, 202, 145), (WIDTH // 2 - 36, 150, 72, 370), border_radius=3)
        pygame.draw.line(self.screen, (246, 246, 232), (WIDTH // 2 - 64, 452), (WIDTH // 2 + 64, 452), 3)
        pygame.draw.line(self.screen, (246, 246, 232), (WIDTH // 2 - 64, 180), (WIDTH // 2 + 64, 180), 3)
        pygame.draw.circle(self.screen, (44, 104, 64), (145, 515), 38, 3)
        pygame.draw.circle(self.screen, (44, 104, 64), (815, 155), 34, 3)

    def draw_players(self):
        batsman_x, batsman_y = WIDTH // 2 + 42, 470
        bowler_x, bowler_y = WIDTH // 2 - 10, 145
        now = pygame.time.get_ticks()

        pygame.draw.ellipse(self.screen, (30, 84, 52), (batsman_x - 30, batsman_y + 42, 72, 16))
        pygame.draw.rect(self.screen, (236, 238, 230), (batsman_x - 16, batsman_y - 24, 32, 50), border_radius=8)
        pygame.draw.rect(self.screen, (41, 112, 82), (batsman_x - 16, batsman_y - 20, 32, 18), border_radius=5)
        pygame.draw.circle(self.screen, (221, 176, 128), (batsman_x, batsman_y - 40), 13)
        pygame.draw.arc(self.screen, (27, 38, 48), (batsman_x - 16, batsman_y - 55, 32, 26), 3.05, 6.3, 7)
        pygame.draw.line(self.screen, (27, 38, 48), (batsman_x - 11, batsman_y - 38), (batsman_x + 14, batsman_y - 38), 3)
        pygame.draw.line(self.screen, (236, 238, 230), (batsman_x - 13, batsman_y - 5), (batsman_x - 30, batsman_y + 12), 6)
        pygame.draw.line(self.screen, (236, 238, 230), (batsman_x + 12, batsman_y - 4), (batsman_x - 12, batsman_y + 7), 6)
        pygame.draw.circle(self.screen, (255, 255, 245), (batsman_x - 31, batsman_y + 13), 6)
        pygame.draw.circle(self.screen, (255, 255, 245), (batsman_x - 14, batsman_y + 8), 6)
        pygame.draw.line(self.screen, (44, 44, 42), (batsman_x - 11, batsman_y + 25), (batsman_x - 17, batsman_y + 51), 6)
        pygame.draw.line(self.screen, (44, 44, 42), (batsman_x + 12, batsman_y + 25), (batsman_x + 21, batsman_y + 50), 6)
        pygame.draw.rect(self.screen, (245, 245, 235), (batsman_x - 24, batsman_y + 36, 12, 25), border_radius=4)
        pygame.draw.rect(self.screen, (245, 245, 235), (batsman_x + 15, batsman_y + 35, 12, 25), border_radius=4)
        bat_start, bat_end = self.bat_line(batsman_x, batsman_y, now)
        self.draw_bat(bat_start, bat_end)

        stride = int(math.sin(pygame.time.get_ticks() / 160) * 8) if self.ball.active else 0
        pygame.draw.ellipse(self.screen, (30, 84, 52), (bowler_x - 36, bowler_y + 42, 72, 14))
        pygame.draw.circle(self.screen, (221, 176, 128), (bowler_x, bowler_y - 32), 12)
        pygame.draw.arc(self.screen, (27, 38, 48), (bowler_x - 14, bowler_y - 45, 28, 21), 3.0, 6.25, 6)
        pygame.draw.rect(self.screen, (70, 108, 190), (bowler_x - 14, bowler_y - 19, 28, 45), border_radius=7)
        pygame.draw.line(self.screen, (70, 108, 190), (bowler_x - 9, bowler_y - 6), (bowler_x - 31, bowler_y + 12), 6)
        pygame.draw.line(self.screen, (70, 108, 190), (bowler_x + 11, bowler_y - 7), (bowler_x + 34, bowler_y - 33), 6)
        pygame.draw.circle(self.screen, (178, 29, 38), (bowler_x + 37, bowler_y - 36), 6)
        pygame.draw.line(self.screen, (35, 41, 52), (bowler_x - 9, bowler_y + 25), (bowler_x - 28 - stride, bowler_y + 50), 6)
        pygame.draw.line(self.screen, (35, 41, 52), (bowler_x + 10, bowler_y + 25), (bowler_x + 25 + stride, bowler_y + 49), 6)

        for stump_x in (WIDTH // 2 - 18, WIDTH // 2, WIDTH // 2 + 18):
            pygame.draw.line(self.screen, (235, 238, 224), (stump_x, 448), (stump_x, 502), 4)
            pygame.draw.line(self.screen, (235, 238, 224), (stump_x, 162), (stump_x, 203), 4)

        if pygame.time.get_ticks() < self.dismissal_flash_until and self.last_dismissal == "BOWLED":
            pygame.draw.line(self.screen, (235, 238, 224), (WIDTH // 2 - 24, 444), (WIDTH // 2 - 3, 432), 4)
            pygame.draw.line(self.screen, (235, 238, 224), (WIDTH // 2 + 7, 444), (WIDTH // 2 + 31, 436), 4)

    def bat_line(self, batsman_x, batsman_y, now):
        handle = (batsman_x - 18, batsman_y + 7)
        resting = (batsman_x - 54, batsman_y + 38)
        if now >= self.swing_until or not self.swing_shot:
            return handle, resting

        poses = {
            "defensive": (batsman_x - 58, batsman_y + 6),
            "ground": (batsman_x - 74, batsman_y + 30),
            "lofted": (batsman_x - 72, batsman_y - 36),
            "power": (batsman_x - 88, batsman_y - 18),
        }
        progress = max(0, min(1, (self.swing_until - now) / 320))
        swing = poses.get(self.swing_shot, resting)
        end_x = int(swing[0] * progress + resting[0] * (1 - progress))
        end_y = int(swing[1] * progress + resting[1] * (1 - progress))
        return handle, (end_x, end_y)

    def draw_bat(self, handle, toe):
        dx = toe[0] - handle[0]
        dy = toe[1] - handle[1]
        length = max(1, math.hypot(dx, dy))
        nx = -dy / length
        ny = dx / length
        shoulder = (int(handle[0] + dx * 0.28), int(handle[1] + dy * 0.28))
        blade_top_left = (int(shoulder[0] + nx * 7), int(shoulder[1] + ny * 7))
        blade_top_right = (int(shoulder[0] - nx * 7), int(shoulder[1] - ny * 7))
        toe_left = (int(toe[0] + nx * 11), int(toe[1] + ny * 11))
        toe_right = (int(toe[0] - nx * 11), int(toe[1] - ny * 11))
        pygame.draw.line(self.screen, (82, 48, 24), handle, shoulder, 5)
        pygame.draw.polygon(self.screen, (190, 132, 63), [blade_top_left, blade_top_right, toe_right, toe_left])
        pygame.draw.polygon(self.screen, (112, 68, 33), [blade_top_left, blade_top_right, toe_right, toe_left], 2)
        pygame.draw.line(self.screen, (224, 170, 89), blade_top_left, toe_left, 2)

    def draw_ball(self):
        if self.ball.active:
            pygame.draw.circle(self.screen, (178, 29, 38), (int(self.ball.x), int(self.ball.y)), self.ball.radius)
            pygame.draw.circle(self.screen, (255, 238, 220), (int(self.ball.x) - 2, int(self.ball.y) - 2), 2)
        elif pygame.time.get_ticks() < self.message_flash_until:
            text = self.small_font.render("Wait for the ball to reach you", True, (255, 241, 176))
            self.screen.blit(text, (WIDTH // 2 - text.get_width() // 2, 105))

    def draw_dismissal_flash(self):
        if pygame.time.get_ticks() >= self.dismissal_flash_until or not self.last_dismissal:
            return
        labels = {
            "BOWLED": "BOWLED!",
            "CAUGHT": "OUT!",
            "EDGE": "EDGE AND OUT!",
        }
        text = self.large_font.render(labels.get(self.last_dismissal, "OUT!"), True, (255, 239, 160))
        shadow = self.large_font.render(labels.get(self.last_dismissal, "OUT!"), True, (83, 30, 24))
        x = WIDTH // 2 - text.get_width() // 2
        self.screen.blit(shadow, (x + 3, 100 + 3))
        self.screen.blit(text, (x, 100))

    def draw_commentary(self):
        panel_y = HEIGHT - 106
        pygame.draw.rect(self.screen, (20, 34, 33), (0, panel_y, WIDTH, 106))
        pygame.draw.line(self.screen, (245, 190, 78), (0, panel_y), (WIDTH, panel_y), 3)
        heading = self.small_font.render("Commentary", True, (245, 190, 78))
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
        pygame.draw.rect(self.screen, (245, 190, 78), panel, 4, border_radius=8)

        title = self.large_font.render("Chase Failed", True, (22, 41, 37))
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, panel.y + 34))

        final = self.font.render(f"Final Score: {self.state.runs}/{self.state.wickets}", True, (31, 52, 48))
        self.screen.blit(final, (WIDTH // 2 - final.get_width() // 2, panel.y + 112))

        overs = self.small_font.render(
            f"Level {self.state.level} target: {self.state.target}  Overs: {self.state.balls // 6}.{self.state.balls % 6}",
            True,
            (55, 74, 69),
        )
        self.screen.blit(overs, (WIDTH // 2 - overs.get_width() // 2, panel.y + 152))

        self.draw_button("Retry Level", self.restart_button_rect(), (39, 112, 76))
        self.draw_button("Levels", self.quit_button_rect(), (77, 91, 96))

        hint = self.small_font.render("R/Enter restarts, Q/Esc quits", True, (55, 74, 69))
        self.screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, panel.y + 322))

    def draw_level_complete(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 10, 12, 165))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(WIDTH // 2 - 240, HEIGHT // 2 - 165, 480, 330)
        pygame.draw.rect(self.screen, (236, 241, 229), panel, border_radius=8)
        pygame.draw.rect(self.screen, (245, 190, 78), panel, 4, border_radius=8)

        title = self.large_font.render("Target Chased", True, (22, 41, 37))
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, panel.y + 34))

        result = self.font.render(
            f"Level {self.state.level} won: {self.state.runs}/{self.state.wickets}",
            True,
            (31, 52, 48),
        )
        self.screen.blit(result, (WIDTH // 2 - result.get_width() // 2, panel.y + 116))

        next_config = LEVELS[self.level_index + 1]
        next_text = self.small_font.render(
            f"Next: chase {next_config['target']} in {next_config['overs']} overs",
            True,
            (55, 74, 69),
        )
        self.screen.blit(next_text, (WIDTH // 2 - next_text.get_width() // 2, panel.y + 158))

        self.draw_button("Next Level", self.next_level_button_rect(), (39, 112, 76))
        self.draw_button("Levels", self.quit_button_rect(), (77, 91, 96))

    def draw_trophy(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 10, 12, 178))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(WIDTH // 2 - 280, HEIGHT // 2 - 235, 560, 470)
        pygame.draw.rect(self.screen, (236, 241, 229), panel, border_radius=8)
        pygame.draw.rect(self.screen, (245, 190, 78), panel, 4, border_radius=8)

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
        pygame.draw.rect(self.screen, (245, 190, 78), rect, 2, border_radius=7)
        text = self.font.render(label, True, (250, 252, 246))
        self.screen.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))

    def start_button_rect(self):
        return pygame.Rect(WIDTH // 2 - 115, 300, 230, 54)

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
