import pygame


class Scoreboard:
    def __init__(self, width):
        self.width = width
        self.font = pygame.font.SysFont("arial", 24, bold=True)
        self.small_font = pygame.font.SysFont("arial", 18)
        self.bg = (22, 41, 37)
        self.text = (244, 248, 241)
        self.accent = (245, 190, 78)

    def overs_text(self, balls):
        return f"{balls // 6}.{balls % 6}"

    def run_rate(self, runs, balls):
        if balls == 0:
            return "0.00"
        return f"{runs / (balls / 6):.2f}"

    def required_rate(self, state):
        remaining_runs = max(0, state.target - state.runs)
        remaining_balls = max(0, state.total_balls - state.balls)
        if remaining_runs == 0:
            return "0.00"
        if remaining_balls == 0:
            return "--"
        return f"{remaining_runs / (remaining_balls / 6):.2f}"

    def draw(self, surface, state):
        pygame.draw.rect(surface, self.bg, (0, 0, self.width, 76))
        pygame.draw.line(surface, self.accent, (0, 75), (self.width, 75), 3)

        title = self.font.render(f"Level {state.level}/5", True, self.accent)
        surface.blit(title, (22, 12))

        score = self.font.render(
            f"{state.runs}/{state.wickets}  Target {state.target}  Overs {self.overs_text(state.balls)}/{state.overs}.0",
            True,
            self.text,
        )
        surface.blit(score, (self.width // 2 - score.get_width() // 2, 12))

        rate = self.small_font.render(
            f"CRR {self.run_rate(state.runs, state.balls)}   RRR {self.required_rate(state)}   Balls {state.balls}/{state.total_balls}",
            True,
            self.text,
        )
        surface.blit(rate, (self.width - rate.get_width() - 22, 18))

        controls = self.small_font.render(
            "Left: Defend   Down: Ground   Right: Lofted   Space: Power",
            True,
            (198, 212, 204),
        )
        surface.blit(controls, (self.width // 2 - controls.get_width() // 2, 48))
