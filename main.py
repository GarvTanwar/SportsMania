import sys
from pathlib import Path

import pygame


WIDTH = 960
HEIGHT = 640
FPS = 60


class SportMenu:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Sports Arcade")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.large_font = pygame.font.SysFont("arial", 58, bold=True)
        self.font = pygame.font.SysFont("arial", 30, bold=True)
        self.small_font = pygame.font.SysFont("arial", 20)
        self.images = self.load_images()

    def load_images(self):
        image_dir = Path(__file__).resolve().parent / "images"
        paths = {
            "Cricket": image_dir / "cricket_2397931.png",
            "Football": image_dir / "football-game_5778529.png",
            "Badminton": image_dir / "badminton_12635733.png",
        }
        loaded = {}
        for sport, path in paths.items():
            try:
                loaded[sport] = pygame.image.load(path).convert_alpha()
            except (FileNotFoundError, pygame.error):
                loaded[sport] = None
        return loaded

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False
                    elif event.key in (pygame.K_1, pygame.K_c):
                        self.open_cricket()
                    elif event.key in (pygame.K_2, pygame.K_f):
                        self.open_football()
                    elif event.key in (pygame.K_3, pygame.K_b):
                        self.open_badminton()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.cricket_rect().collidepoint(event.pos):
                        self.open_cricket()
                    elif self.football_rect().collidepoint(event.pos):
                        self.open_football()
                    elif self.badminton_rect().collidepoint(event.pos):
                        self.open_badminton()
                    elif self.quit_rect().collidepoint(event.pos):
                        running = False

            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()

    def open_cricket(self):
        from cricket_game import CricketGame

        pygame.quit()
        CricketGame(exit_on_close=False, quit_label="Sports Menu").run()
        self.__init__()

    def open_football(self):
        from football_game import FootballGame

        pygame.quit()
        FootballGame(exit_on_close=False, quit_label="Sports Menu").run()
        self.__init__()

    def open_badminton(self):
        from badminton_game import BadmintonGame

        pygame.quit()
        BadmintonGame(exit_on_close=False, quit_label="Sports Menu").run()
        self.__init__()

    def draw(self):
        self.screen.fill((20, 29, 38))
        pygame.draw.rect(self.screen, (29, 76, 66), (0, 0, WIDTH, 230))

        title = self.large_font.render("Sports Arcade", True, (250, 252, 246))
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 58))
        subtitle = self.small_font.render("Choose your game", True, (222, 232, 224))
        self.screen.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, 130))

        self.draw_sport_card(
            self.cricket_rect(),
            "Cricket",
            "5 chase levels",
            (57, 128, 78),
            (245, 190, 78),
            "1 / C",
        )
        self.draw_sport_card(
            self.football_rect(),
            "Football",
            "5 penalty levels",
            (38, 97, 143),
            (238, 243, 235),
            "2 / F",
        )
        self.draw_sport_card(
            self.badminton_rect(),
            "Badminton",
            "5 point races",
            (125, 78, 145),
            (255, 218, 120),
            "3 / B",
        )
        self.draw_button("Quit App", self.quit_rect(), (105, 47, 47))

    def draw_sport_card(self, rect, title, subtitle, fill, accent, key_hint):
        pygame.draw.rect(self.screen, fill, rect, border_radius=8)
        pygame.draw.rect(self.screen, accent, rect, 4, border_radius=8)
        name = self.font.render(title, True, (250, 252, 246))
        detail = self.small_font.render(subtitle, True, (232, 240, 236))
        hint = self.small_font.render(key_hint, True, accent)
        self.screen.blit(name, (rect.centerx - name.get_width() // 2, rect.y + 44))
        self.screen.blit(detail, (rect.centerx - detail.get_width() // 2, rect.y + 92))
        self.screen.blit(hint, (rect.centerx - hint.get_width() // 2, rect.y + 138))

        image = self.images.get(title)
        if image:
            self.draw_card_image(image, rect)
        elif title == "Cricket":
            self.draw_cricket_icon(rect)
        elif title == "Badminton":
            self.draw_badminton_icon(rect)
        else:
            self.draw_football_pitch_icon(rect)

    def draw_card_image(self, image, rect):
        max_w = 170
        max_h = 108
        scale = min(max_w / image.get_width(), max_h / image.get_height())
        size = (int(image.get_width() * scale), int(image.get_height() * scale))
        scaled = pygame.transform.smoothscale(image, size)
        self.screen.blit(scaled, (rect.centerx - size[0] // 2, rect.y + 164))

    def draw_cricket_icon(self, rect):
        cx = rect.centerx
        cy = rect.y + 218
        bat_color = (224, 184, 111)
        edge_color = (121, 75, 39)
        ball_color = (186, 29, 38)
        handle_top = (cx - 30, cy - 58)
        handle_bottom = (cx - 18, cy - 16)
        blade = pygame.Rect(cx - 38, cy - 16, 34, 86)
        pygame.draw.line(self.screen, edge_color, handle_top, handle_bottom, 8)
        pygame.draw.rect(self.screen, bat_color, blade, border_radius=7)
        pygame.draw.rect(self.screen, edge_color, blade, 2, border_radius=7)
        pygame.draw.line(self.screen, (242, 210, 145), (blade.x + 8, blade.y + 8), (blade.x + 8, blade.bottom - 8), 2)
        pygame.draw.circle(self.screen, ball_color, (cx + 55, cy + 14), 13)
        pygame.draw.arc(self.screen, (255, 229, 214), (cx + 47, cy + 6, 16, 16), 4.5, 1.7, 2)
        pygame.draw.arc(self.screen, (255, 229, 214), (cx + 51, cy + 6, 16, 16), 1.4, 4.9, 2)

    def draw_football_pitch_icon(self, rect):
        pitch = pygame.Rect(rect.centerx - 108, rect.y + 172, 216, 98)
        line = (238, 243, 235)
        pygame.draw.rect(self.screen, (38, 117, 80), pitch)
        pygame.draw.rect(self.screen, line, pitch, 4)
        pygame.draw.line(self.screen, line, (pitch.centerx, pitch.y), (pitch.centerx, pitch.bottom), 3)
        pygame.draw.circle(self.screen, line, pitch.center, 22, 3)
        pygame.draw.circle(self.screen, line, pitch.center, 4)
        pygame.draw.rect(self.screen, line, (pitch.x, pitch.centery - 25, 34, 50), 3)
        pygame.draw.rect(self.screen, line, (pitch.right - 34, pitch.centery - 25, 34, 50), 3)
        pygame.draw.circle(self.screen, line, pitch.topleft, 10, 3)
        pygame.draw.circle(self.screen, line, pitch.topright, 10, 3)
        pygame.draw.circle(self.screen, line, pitch.bottomleft, 10, 3)
        pygame.draw.circle(self.screen, line, pitch.bottomright, 10, 3)

    def draw_badminton_icon(self, rect):
        cx = rect.centerx
        cy = rect.y + 220
        line = (250, 252, 246)
        accent = (255, 218, 120)
        pygame.draw.ellipse(self.screen, line, (cx - 62, cy - 58, 74, 92), 5)
        for offset in (-18, 0, 18):
            pygame.draw.line(self.screen, line, (cx - 25 + offset, cy - 50), (cx - 25 + offset, cy + 24), 1)
        for offset in (-30, -10, 10):
            pygame.draw.line(self.screen, line, (cx - 54, cy + offset), (cx + 4, cy + offset), 1)
        pygame.draw.line(self.screen, accent, (cx + 2, cy + 26), (cx + 54, cy + 72), 8)
        pygame.draw.line(self.screen, (88, 54, 34), (cx + 40, cy + 60), (cx + 72, cy + 88), 8)
        pygame.draw.circle(self.screen, (245, 245, 235), (cx + 70, cy - 25), 8)
        pygame.draw.polygon(
            self.screen,
            (245, 245, 235),
            [(cx + 62, cy - 17), (cx + 78, cy - 17), (cx + 88, cy + 18), (cx + 52, cy + 18)],
        )
        pygame.draw.line(self.screen, (174, 186, 190), (cx + 58, cy + 5), (cx + 82, cy + 5), 2)

    def draw_button(self, label, rect, color):
        pygame.draw.rect(self.screen, color, rect, border_radius=7)
        pygame.draw.rect(self.screen, (245, 190, 78), rect, 2, border_radius=7)
        text = self.font.render(label, True, (250, 252, 246))
        self.screen.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))

    def cricket_rect(self):
        return pygame.Rect(55, 255, 260, 290)

    def football_rect(self):
        return pygame.Rect(350, 255, 260, 290)

    def badminton_rect(self):
        return pygame.Rect(645, 255, 260, 290)

    def quit_rect(self):
        return pygame.Rect(WIDTH // 2 - 115, 565, 230, 48)


def main():
    SportMenu().run()


if __name__ == "__main__":
    main()
