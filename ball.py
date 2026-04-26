import random


class Ball:
    """A single delivery travelling from bowler to batsman."""

    def __init__(self, start_pos, target_y, wicket_x):
        self.start_x, self.start_y = start_pos
        self.target_y = target_y
        self.wicket_x = wicket_x
        self.radius = 7
        self.reset()

    def reset(self):
        self.x = float(self.start_x)
        self.y = float(self.start_y)
        self.end_x = float(self.wicket_x + random.randint(-42, 42))
        self.speed = random.uniform(6.2, 10.8)
        self.active = False
        self.resolved = False

    def bowl(self):
        self.reset()
        self.active = True

    def update(self):
        if not self.active:
            return

        self.y += self.speed
        travel_distance = (self.target_y + 90) - self.start_y
        if travel_distance <= 0:
            travel = 1
        else:
            travel = min(1, (self.y - self.start_y) / travel_distance)
        self.x = self.start_x + (self.end_x - self.start_x) * travel
        if self.y >= self.target_y + 90:
            self.active = False
            self.resolved = True

    def timing_delta(self):
        return abs(self.y - self.target_y)

    def is_in_hittable_zone(self):
        return self.active and self.timing_delta() <= 92

    def is_hitting_stumps(self):
        return abs(self.x - self.wicket_x) <= 18
