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
    {"level": 1, "target": 5, "opponent": 0.34},
    {"level": 2, "target": 7, "opponent": 0.40},
    {"level": 3, "target": 9, "opponent": 0.46},
    {"level": 4, "target": 11, "opponent": 0.52},
    {"level": 5, "target": 15, "opponent": 0.58},
]


@dataclass
class BadmintonState:
    level: int = 1
    target: int = 5
    opponent: float = 0.34
    player_points: int = 0
    opponent_points: int = 0
    rallies: int = 0
    commentary: list[str] = field(default_factory=lambda: ["Welcome to Sports Arcade: Badminton."])


class BadmintonGame:
    def __init__(self, exit_on_close=True, quit_label="Quit App"):
        self.exit_on_close = exit_on_close
        self.quit_label = quit_label
        pygame.init()
        pygame.display.set_caption("Sports Arcade: Badminton")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 28, bold=True)
        self.small_font = pygame.font.SysFont("arial", 20)
        self.large_font = pygame.font.SysFont("arial", 52, bold=True)
        self.trophy_image = self.load_trophy_image()
        self.level_index = 0
        self.highest_unlocked = 0
        self.won_levels = set()
        self.state = BadmintonState()
        self.mode = "menu"
        self.shuttle_start = (WIDTH // 2, 190)
        self.shuttle_target = (WIDTH // 2, 485)
        self.shuttle_pos = self.shuttle_start
        self.shuttle_active = False
        self.next_rally_at = 0
        self.swing_until = 0
        self.swing_shot = None
        self.result_flash_until = 0
        self.result_label = ""
        self.last_target_lane = "center"
        self.queued_shot = None

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
                self.shuttle_active = False
            else:
                shot = {
                    pygame.K_LEFT: "left",
                    pygame.K_DOWN: "center",
                    pygame.K_UP: "center",
                    pygame.K_RIGHT: "right",
                    pygame.K_SPACE: "smash",
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
        elif self.mode == "playing":
            for shot, rect in self.shot_button_rects().items():
                if rect.collidepoint(pos):
                    self.play_shot(shot, pygame.time.get_ticks())
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
        self.state = BadmintonState()

    def start_level(self, index=None):
        if index is not None:
            self.level_index = index
        config = LEVELS[self.level_index]
        self.state = BadmintonState(
            level=config["level"],
            target=config["target"],
            opponent=config["opponent"],
            commentary=[f"Level {config['level']}: first to {config['target']} points wins."],
        )
        self.mode = "playing"
        self.shuttle_active = False
        self.shuttle_pos = self.shuttle_start
        self.next_rally_at = pygame.time.get_ticks() + 800
        self.swing_until = 0
        self.swing_shot = None
        self.result_label = ""
        self.queued_shot = None
        self.add_commentary("Pick a return early. It will swing when the shuttle reaches you.")

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
        if not self.shuttle_active and now >= self.next_rally_at:
            self.serve_shuttle()
        if self.shuttle_active:
            sx, sy = self.shuttle_start
            tx, ty = self.shuttle_target
            progress = min(1, (now - self.rally_started_at) / self.rally_duration)
            eased = progress * progress
            arc = math.sin(progress * math.pi) * 40
            self.shuttle_pos = (sx + (tx - sx) * eased, sy + (ty - sy) * eased - arc)
            if progress >= 1:
                self.award_point("opponent", "You missed the shuttle.")
            elif self.queued_shot and self.is_hittable():
                self.play_shot(self.queued_shot, now)

    def serve_shuttle(self):
        self.last_target_lane = random.choice(["left", "center", "right"])
        lane_x = {"left": WIDTH // 2 - 155, "center": WIDTH // 2, "right": WIDTH // 2 + 155}[self.last_target_lane]
        self.shuttle_start = (WIDTH // 2 + random.randint(-90, 90), 186)
        self.shuttle_target = (lane_x, 485)
        self.shuttle_pos = self.shuttle_start
        self.shuttle_active = True
        self.rally_started_at = pygame.time.get_ticks()
        self.rally_duration = random.randint(1150, 1550)
        self.add_commentary("Opponent sends the shuttle across.")

    def play_shot(self, shot, now):
        if not self.shuttle_active:
            self.queued_shot = shot
            self.result_label = "READY"
            self.result_flash_until = now + 520
            return
        if not self.is_hittable():
            self.queued_shot = shot
            self.result_label = "READY"
            self.result_flash_until = now + 520
            return

        self.queued_shot = None
        self.swing_shot = shot
        self.swing_until = now + 320
        timing = self.classify_timing()
        player_wins = self.resolve_rally(shot, timing)
        if player_wins:
            self.award_point("player", f"{timing.title()} {shot} wins the rally.")
        else:
            self.award_point("opponent", f"{timing.title()} {shot}, but the opponent takes the point.")

    def is_hittable(self):
        return self.shuttle_active and abs(self.shuttle_pos[1] - self.shuttle_target[1]) <= 150

    def classify_timing(self):
        delta = abs(self.shuttle_pos[1] - self.shuttle_target[1])
        if delta <= 55:
            return "perfect"
        if delta <= 115:
            return "good"
        return "poor"

    def resolve_rally(self, shot, timing):
        base = {"perfect": 0.78, "good": 0.58, "poor": 0.30}[timing]
        shot_bonus = {"left": 0.02, "center": 0.00, "right": 0.02, "smash": 0.08}[shot]
        if shot == "smash" and timing == "poor":
            shot_bonus = -0.12
        chance = max(0.12, min(0.88, base + shot_bonus - self.state.opponent * 0.35))
        return random.random() < chance

    def award_point(self, winner, line):
        self.shuttle_active = False
        self.state.rallies += 1
        if winner == "player":
            self.state.player_points += 1
            self.result_label = "POINT!"
        else:
            self.state.opponent_points += 1
            self.result_label = "OPPONENT POINT"
        self.result_flash_until = pygame.time.get_ticks() + 900
        self.add_commentary(line)
        if self.has_won_level():
            self.complete_level()
        elif self.has_failed_level():
            self.mode = "game_over"
        else:
            self.next_rally_at = pygame.time.get_ticks() + 950

    def add_commentary(self, line):
        self.state.commentary.append(line)
        self.state.commentary = self.state.commentary[-4:]

    def has_won_level(self):
        return self.state.player_points >= self.state.target

    def has_failed_level(self):
        return self.state.opponent_points >= self.state.target

    def complete_level(self):
        self.won_levels.add(self.level_index)
        self.highest_unlocked = min(len(LEVELS) - 1, max(self.highest_unlocked, self.level_index + 1))
        self.mode = "trophy" if self.level_index == len(LEVELS) - 1 else "level_complete"

    def draw(self):
        self.screen.fill((52, 122, 116))
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
        self.screen.fill((22, 28, 40))
        title = self.large_font.render("Sports Arcade: Badminton", True, (255, 218, 120))
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 58))
        subtitle = self.small_font.render("Select an unlocked point race. First player to the target wins.", True, (224, 232, 222))
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
            border = (255, 218, 120)
            status = "WON"
        elif unlocked:
            fill = (125, 78, 145)
            border = (255, 218, 120)
            status = "UNLOCKED"
        else:
            fill = (47, 53, 57)
            border = (105, 115, 118)
            status = "LOCKED"
        pygame.draw.rect(self.screen, fill, rect, border_radius=8)
        pygame.draw.rect(self.screen, border, rect, 3, border_radius=8)
        title_color = (250, 252, 246) if unlocked else (196, 204, 202)
        body_color = (230, 238, 230) if unlocked else (178, 186, 184)
        texts = [
            self.font.render(f"Level {level['level']}", True, title_color),
            self.small_font.render(f"First to {level['target']}", True, body_color),
            self.small_font.render(status, True, border if unlocked else (175, 181, 179)),
        ]
        ys = [rect.y + 28, rect.y + 86, rect.y + 132]
        for text, y in zip(texts, ys):
            self.screen.blit(text, (rect.centerx - text.get_width() // 2, y))

    def draw_game(self):
        self.draw_court()
        self.draw_scoreboard()
        self.draw_players()
        self.draw_shuttle()
        self.draw_controls()
        self.draw_result_flash()
        self.draw_commentary()

    def draw_court(self):
        self.screen.fill((45, 132, 122))
        court = pygame.Rect(WIDTH // 2 - 310, 105, 620, 420)
        line = (238, 246, 232)
        pygame.draw.rect(self.screen, (54, 150, 136), court)
        pygame.draw.rect(self.screen, line, court, 4)
        pygame.draw.line(self.screen, line, (court.x, court.centery), (court.right, court.centery), 4)
        pygame.draw.line(self.screen, line, (court.centerx, court.y), (court.centerx, court.bottom), 2)
        pygame.draw.line(self.screen, line, (court.x + 90, court.y), (court.x + 90, court.bottom), 2)
        pygame.draw.line(self.screen, line, (court.right - 90, court.y), (court.right - 90, court.bottom), 2)
        pygame.draw.line(self.screen, (55, 48, 58), (court.x - 12, court.centery), (court.right + 12, court.centery), 6)
        for x in range(court.x, court.right + 1, 24):
            pygame.draw.line(self.screen, (210, 220, 210), (x, court.centery - 26), (x, court.centery + 26), 1)

    def draw_scoreboard(self):
        pygame.draw.rect(self.screen, (22, 28, 40), (0, 0, WIDTH, 76))
        pygame.draw.line(self.screen, (255, 218, 120), (0, 75), (WIDTH, 75), 3)
        level = self.font.render(f"Level {self.state.level}/5", True, (255, 218, 120))
        score = self.font.render(
            f"You {self.state.player_points} - {self.state.opponent_points} Opponent   Target {self.state.target}",
            True,
            (250, 252, 246),
        )
        controls = self.small_font.render("Press a return before the shuttle arrives. Left/Down/Right: Return   Space: Smash", True, (216, 224, 220))
        self.screen.blit(level, (22, 12))
        self.screen.blit(score, (WIDTH // 2 - score.get_width() // 2, 12))
        self.screen.blit(controls, (WIDTH // 2 - controls.get_width() // 2, 48))

    def draw_players(self):
        self.draw_player(WIDTH // 2, 470, (61, 102, 196), False)
        self.draw_player(WIDTH // 2, 190, (225, 86, 72), True)

    def draw_player(self, x, y, shirt, opponent):
        shadow_y = y + 42 if not opponent else y + 38
        pygame.draw.ellipse(self.screen, (28, 82, 75), (x - 34, shadow_y, 68, 13))
        pygame.draw.circle(self.screen, (221, 176, 128), (x, y - 38), 12)
        pygame.draw.rect(self.screen, shirt, (x - 15, y - 24, 30, 46), border_radius=7)
        pygame.draw.line(self.screen, shirt, (x - 11, y - 8), (x - 34, y + 10), 6)
        pygame.draw.line(self.screen, shirt, (x + 11, y - 8), (x + 33, y - 18), 6)
        pygame.draw.line(self.screen, (34, 38, 48), (x - 9, y + 22), (x - 24, y + 50), 6)
        pygame.draw.line(self.screen, (34, 38, 48), (x + 9, y + 22), (x + 24, y + 50), 6)
        racket_x = x + 46
        racket_y = y - 28
        pygame.draw.line(self.screen, (102, 65, 35), (x + 31, y - 16), (racket_x, racket_y), 4)
        pygame.draw.ellipse(self.screen, (245, 245, 238), (racket_x - 12, racket_y - 18, 24, 34), 3)

    def draw_shuttle(self):
        x, y = self.shuttle_pos
        pygame.draw.circle(self.screen, (245, 245, 235), (int(x), int(y)), 6)
        pygame.draw.polygon(
            self.screen,
            (238, 238, 230),
            [(x - 9, y + 5), (x + 9, y + 5), (x + 15, y + 26), (x - 15, y + 26)],
        )
        pygame.draw.line(self.screen, (180, 190, 190), (x - 8, y + 10), (x + 8, y + 10), 1)

    def draw_controls(self):
        for shot, rect in self.shot_button_rects().items():
            self.draw_button(shot.title(), rect, (77, 91, 96) if shot != "smash" else (125, 78, 145))

    def draw_result_flash(self):
        if pygame.time.get_ticks() >= self.result_flash_until or not self.result_label:
            return
        text = self.large_font.render(self.result_label, True, (255, 239, 160))
        shadow = self.large_font.render(self.result_label, True, (50, 36, 60))
        x = WIDTH // 2 - text.get_width() // 2
        self.screen.blit(shadow, (x + 3, 280 + 3))
        self.screen.blit(text, (x, 280))

    def draw_commentary(self):
        panel_y = HEIGHT - 106
        pygame.draw.rect(self.screen, (22, 28, 40), (0, panel_y, WIDTH, 106))
        pygame.draw.line(self.screen, (255, 218, 120), (0, panel_y), (WIDTH, panel_y), 3)
        heading = self.small_font.render("Commentary", True, (255, 218, 120))
        self.screen.blit(heading, (22, panel_y + 10))
        for index, line in enumerate(self.state.commentary[-3:]):
            text = self.small_font.render(line, True, (235, 241, 232))
            self.screen.blit(text, (22, panel_y + 38 + index * 22))

    def draw_game_over(self):
        self.draw_modal("Match Lost", f"Final Score: {self.state.player_points}-{self.state.opponent_points}", "Retry Level")

    def draw_level_complete(self):
        next_text = ""
        if self.level_index < len(LEVELS) - 1:
            next_text = f"Next: first to {LEVELS[self.level_index + 1]['target']} points"
        self.draw_modal("Match Won", f"Level {self.state.level}: {self.state.player_points}-{self.state.opponent_points}", "Next Level", next_text)

    def draw_trophy(self):
        self.draw_modal("", "", "Play Again", show_cup=True)

    def draw_modal(self, title_text, result_text, action_text, extra_text="", show_cup=False):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 10, 12, 178))
        self.screen.blit(overlay, (0, 0))
        if show_cup:
            panel = pygame.Rect(WIDTH // 2 - 280, HEIGHT // 2 - 235, 560, 470)
        else:
            panel = pygame.Rect(WIDTH // 2 - 260, HEIGHT // 2 - 185, 520, 370)
        pygame.draw.rect(self.screen, (236, 241, 229), panel, border_radius=8)
        pygame.draw.rect(self.screen, (255, 218, 120), panel, 4, border_radius=8)
        title = self.large_font.render(title_text, True, (22, 41, 37))
        result = self.font.render(result_text, True, (31, 52, 48))
        if show_cup:
            self.draw_won_label(panel)
            self.draw_trophy_image(panel)
            result_y = panel.y + 244
        else:
            self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, panel.y + 36))
            result_y = panel.y + 122
            self.screen.blit(result, (WIDTH // 2 - result.get_width() // 2, result_y))
        if extra_text:
            extra = self.small_font.render(extra_text, True, (55, 74, 69))
            self.screen.blit(extra, (WIDTH // 2 - extra.get_width() // 2, panel.y + 164))
        if self.mode == "level_complete":
            self.draw_button(action_text, self.next_level_button_rect(), (39, 112, 76))
        else:
            self.draw_button(action_text, self.restart_button_rect(), (39, 112, 76))
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
        pygame.draw.rect(self.screen, (255, 218, 120), rect, 2, border_radius=7)
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
        if self.mode == "game_over":
            return pygame.Rect(WIDTH // 2 - 115, HEIGHT // 2 + 122, 230, 48)
        if self.mode == "level_complete":
            return pygame.Rect(WIDTH // 2 - 115, HEIGHT // 2 + 112, 230, 48)
        if self.mode == "trophy":
            return pygame.Rect(WIDTH // 2 - 115, HEIGHT // 2 + 170, 230, 48)
        return pygame.Rect(WIDTH // 2 + 20, 460, 230, 54)

    def shot_button_rects(self):
        return {
            "left": pygame.Rect(WIDTH // 2 - 330, 486, 135, 44),
            "center": pygame.Rect(WIDTH // 2 - 160, 486, 135, 44),
            "right": pygame.Rect(WIDTH // 2 + 10, 486, 135, 44),
            "smash": pygame.Rect(WIDTH // 2 + 180, 486, 135, 44),
        }
