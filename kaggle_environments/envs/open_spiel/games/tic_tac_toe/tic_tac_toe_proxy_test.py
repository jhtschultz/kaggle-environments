"""Test for proxied Tic Tac Toe game."""

import json


from absl.testing import absltest
from absl.testing import parameterized
import pyspiel
from . import tic_tac_toe_proxy as tic_tac_toe


class TicTacToeTest(parameterized.TestCase):

  def test_game_is_registered(self):
    game = pyspiel.load_game('tic_tac_toe_proxy')
    self.assertIsInstance(game, tic_tac_toe.TicTacToeGame)

  def test_random_sim(self):
    game = tic_tac_toe.TicTacToeGame()
    pyspiel.random_sim_test(game, num_sims=10, serialize=False, verbose=False)

  def test_random_sim_2(self):
    game = tic_tac_toe.TicTacToeGame()
    state = game.new_initial_state()
    print(json.loads(state.to_json()))
    for i in range(9):
        action = json.loads(state.action_to_json(state.current_player(), i))
        print(action)
        state.apply_action(i)
        print(json.loads(state.to_json()))


  def test_state_to_json(self):
    game = tic_tac_toe.TicTacToeGame()
    state = game.new_initial_state()
    json_state = json.loads(state.to_json())
    self.assertEqual(json_state['board'], [None] * 9)
    self.assertEqual(json_state['current_player'], 'x')
    state.apply_action(4)
    json_state = json.loads(state.to_json())
    expected_board = [None] * 9
    expected_board[4] = 'x'
    self.assertEqual(json_state['board'], expected_board)
    self.assertEqual(json_state['current_player'], 'o')

  def test_action_to_json(self):
    game = tic_tac_toe.TicTacToeGame()
    state = game.new_initial_state()
    action = json.loads(state.action_to_json(0, 4))
    self.assertEqual(json.loads(state.action_to_json(4)), action)
    self.assertEqual(action['row'], 1)
    self.assertEqual(action['col'], 1)
    self.assertEqual(action['player'], 'x')

  def test_action_to_string(self):
    game = tic_tac_toe.TicTacToeGame()
    state = game.new_initial_state()
    self.assertEqual(state.action_to_string(0, 4), '<1,1>')
    self.assertEqual(state.action_to_string(4), '<1,1>')

  def test_observation_string(self):
    game = tic_tac_toe.TicTacToeGame()
    state = game.new_initial_state()
    state.apply_action(4)
    self.assertEqual(state.observation_string(0), str(state))
    self.assertEqual(state.observation_string(1), str(state))


if __name__ == '__main__':
  absltest.main()
