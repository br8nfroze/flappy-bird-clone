"""Run the real game loop with a headless display and deterministic inputs."""

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

from contextlib import ExitStack
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import flappy_bird as game


class GameTests(unittest.TestCase):
    def run_game(self, frame_count, *, ticks=None, prepare_bird=None,
                 prepare_pipe=None, space_frames=(), gravity=0):
        """Control events/time while retaining real physics, drawing and collisions."""
        game.pygame.init()
        real_font = game.pygame.font.SysFont("Arial", 32)
        bird_class, pipe_class = game.Bird, game.Pipe
        birds, pipes, frames = [], [], []
        rendered_text, drawn_pipes = [], []
        frame_number = 0

        def create_bird():
            bird = bird_class()
            if prepare_bird:
                prepare_bird(bird, len(birds))
            birds.append(bird)
            return bird

        def create_pipe(x):
            pipe = pipe_class(x)
            if prepare_pipe:
                prepare_pipe(pipe, len(pipes))
            pipes.append(pipe)
            return pipe

        def get_events():
            nonlocal frame_number
            frame_number += 1
            if frame_number > frame_count:
                return [game.pygame.event.Event(game.pygame.QUIT)]
            if frame_number in space_frames:
                return [game.pygame.event.Event(
                    game.pygame.KEYDOWN, key=game.pygame.K_SPACE)]
            return []

        def get_ticks():
            return ticks(frame_number) if ticks else frame_number * 17

        def render(text, antialias, color):
            rendered_text.append(text)
            return real_font.render(text, antialias, color)

        original_draw = pipe_class.draw

        def draw_pipe(pipe, screen):
            drawn_pipes.append((pipe.x, pipe.width))
            original_draw(pipe, screen)

        def capture_frame():
            frames.append({
                "text": list(rendered_text),
                "pipes": list(drawn_pipes),
                "bird_y": birds[-1].y,
                "bird_velocity": birds[-1].velocity,
            })
            rendered_text.clear()
            drawn_pipes.clear()

        font = Mock()
        font.render.side_effect = render
        try:
            with ExitStack() as stack:
                stack.enter_context(patch.object(game, "Bird", create_bird))
                stack.enter_context(patch.object(game, "Pipe", create_pipe))
                stack.enter_context(patch.object(game, "GRAVITY", gravity))
                stack.enter_context(patch.object(pipe_class, "draw", draw_pipe))
                stack.enter_context(patch.object(game.pygame.event, "get", get_events))
                stack.enter_context(patch.object(game.pygame.time, "get_ticks", get_ticks))
                stack.enter_context(patch.object(game.pygame.time, "Clock", return_value=Mock()))
                stack.enter_context(patch.object(game.pygame.font, "SysFont", return_value=font))
                stack.enter_context(patch.object(game.pygame.display, "flip", capture_frame))
                quit_mock = stack.enter_context(patch.object(
                    game.pygame, "quit", wraps=game.pygame.quit))
                with self.assertRaises(SystemExit) as exited:
                    game.main()
                self.assertIn(exited.exception.code, (None, 0))
                quit_mock.assert_called_once_with()
        finally:
            game.pygame.quit()
        self.assertEqual(len(frames), frame_count)
        return frames, birds, pipes

    def test_first_two_pipes_have_playable_spacing(self):
        frames, _, pipes = self.run_game(
            91, ticks=lambda frame: int(frame * 1000 / 60))
        self.assertEqual(len(pipes), 2)
        first_x, width = frames[-1]["pipes"][0]
        second_x, _ = frames[-1]["pipes"][1]
        self.assertEqual(second_x - first_x, 90 * game.PIPE_SPEED)
        self.assertGreater(second_x - first_x - width, 2 * game.Bird().radius)

    def test_restart_resets_pipe_timer_after_waiting(self):
        def prepare_bird(bird, index):
            if index == 0:
                bird.y = game.SCREEN_HEIGHT - bird.radius

        times = [0, 17, 10000, 11500, 11501]
        frames, birds, _ = self.run_game(
            4, ticks=lambda frame: times[min(frame, len(times) - 1)],
            prepare_bird=prepare_bird, space_frames=(2,))
        self.assertIn("GAME OVER", frames[0]["text"])
        self.assertEqual(len(birds), 2)
        self.assertNotIn("GAME OVER", frames[1]["text"])
        self.assertEqual(frames[1]["pipes"], [(game.SCREEN_WIDTH - game.PIPE_SPEED, 50)])
        self.assertEqual(len(frames[2]["pipes"]), 1)
        self.assertEqual(len(frames[3]["pipes"]), 2)
        self.assertIn("Score: 0", frames[1]["text"])

    def test_score_waits_until_entire_pipe_clears_bird(self):
        def prepare_pipe(pipe, _):
            pipe.x = 2
            pipe.height = 225

        frames, _, pipes = self.run_game(8, prepare_pipe=prepare_pipe)
        for frame in frames[:5]:
            self.assertIn("Score: 0", frame["text"])
        for frame in frames[5:]:
            self.assertIn("Score: 1", frame["text"])
            self.assertNotIn("GAME OVER", frame["text"])
        self.assertTrue(pipes[0].passed)

    def test_screen_collision_includes_bird_radius(self):
        for position in (15, game.SCREEN_HEIGHT - 15):
            with self.subTest(y=position):
                frames, _, _ = self.run_game(
                    2, prepare_bird=lambda bird, _: setattr(bird, "y", position))
                self.assertIn("GAME OVER", frames[0]["text"])
                self.assertIn("GAME OVER", frames[1]["text"])

    def test_bird_just_inside_screen_remains_active(self):
        for position in (16, game.SCREEN_HEIGHT - 16):
            with self.subTest(y=position):
                frames, _, _ = self.run_game(
                    1, prepare_bird=lambda bird, _: setattr(bird, "y", position))
                self.assertNotIn("GAME OVER", frames[0]["text"])

    def test_collision_with_pipe_ends_game(self):
        def prepare_pipe(pipe, _):
            pipe.x = 50
            pipe.height = 320

        frames, _, _ = self.run_game(2, prepare_pipe=prepare_pipe)
        self.assertIn("GAME OVER", frames[0]["text"])
        self.assertEqual(frames[0]["pipes"], frames[1]["pipes"])

    def test_space_flaps_before_gravity_is_applied(self):
        frames, _, _ = self.run_game(2, space_frames=(1,), gravity=game.GRAVITY)
        self.assertEqual(frames[0]["bird_velocity"], game.FLAP_STRENGTH + game.GRAVITY)
        self.assertEqual(frames[0]["bird_y"], game.SCREEN_HEIGHT // 2 - 6.25)
        self.assertEqual(frames[1]["bird_velocity"], game.FLAP_STRENGTH + 2 * game.GRAVITY)

    def test_offscreen_removal_uses_actual_pipe_width(self):
        def prepare_pipe(pipe, _):
            pipe.x = -50
            pipe.width = 100
            pipe.height = 225

        frames, _, _ = self.run_game(17, prepare_pipe=prepare_pipe)
        self.assertTrue(all(len(frame["pipes"]) == 1 for frame in frames[:16]))
        self.assertEqual(frames[-1]["pipes"], [])

    def test_quit_exits_without_rendering_another_frame(self):
        frames, _, _ = self.run_game(0)
        self.assertEqual(frames, [])


if __name__ == "__main__":
    unittest.main()
