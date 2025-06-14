"""Test for proxied Universal Poker game."""

import json
import random

from absl.testing import absltest
from absl.testing import parameterized
import pyspiel
from . import universal_poker_proxy as universal_poker


def _render(state):
  for player in range(state.num_players()):
    print(f"OBSERVATION PLAYER {player}:")
    print(state.observation_string(player))

class UniversalPokerTest(parameterized.TestCase):

  def test_game_is_registered(self):
    game = pyspiel.load_game('universal_poker_proxy')
    self.assertIsInstance(game, universal_poker.UniversalPokerGame)

  def test_game_parameters(self):
    game = pyspiel.load_game("universal_poker_proxy(betting=nolimit,numPlayers=2,stack=20000 20000,numRounds=4,blind=50 100,firstPlayer=2 1 1 1,numSuits=4,numRanks=13,numHoleCards=2,numBoardCards=0 3 1 1,bettingAbstraction=fullgame)")
    state = game.new_initial_state()
    while not state.is_terminal():
      _render(state)
      action = random.choice(state.legal_actions())
      state.apply_action(action)
    _render(state)
    #self.assertIsInstance(game, universal_poker.UniversalPokerGame)

  def test_random_sim(self):
    game = universal_poker.UniversalPokerGame()
    pyspiel.random_sim_test(game, num_sims=10, serialize=False, verbose=False)

  #def test_state_to_json(self):
  #  game = connect_four.ConnectFourGame()
  #  state = game.new_initial_state()
  #  json_state = json.loads(state.to_json())
  #  expected_board = [['.'] * NUM_COLS for _ in range(NUM_ROWS)]
  #  self.assertEqual(json_state['board'], expected_board)
  #  self.assertEqual(json_state['current_player'], 'x')
  #  state.apply_action(3)
  #  json_state = json.loads(state.to_json())
  #  expected_board[0][3] = 'x'
  #  self.assertEqual(json_state['board'], expected_board)
  #  self.assertEqual(json_state['current_player'], 'o')
  #  state.apply_action(2)
  #  json_state = json.loads(state.to_json())
  #  expected_board[0][2] = 'o'
  #  self.assertEqual(json_state['board'], expected_board)
  #  self.assertEqual(json_state['current_player'], 'x')
  #  state.apply_action(2)
  #  json_state = json.loads(state.to_json())
  #  expected_board[1][2] = 'x'
  #  self.assertEqual(json_state['board'], expected_board)
  #  self.assertEqual(json_state['current_player'], 'o')

  #def test_action_to_json(self):
  #  game = connect_four.ConnectFourGame()
  #  state = game.new_initial_state()
  #  action = json.loads(state.action_to_json(3))
  #  self.assertEqual(json.loads(state.action_to_json(3)), action)
  #  self.assertEqual(action['col'], 3)


if __name__ == '__main__':
  absltest.main()
