import os
import random
from kaggle_environments import make
import pyspiel

def random_agent(observation):
  """A built-in random agent specifically for OpenSpiel environments. """
  legal_actions = observation.get("legal_actions")
  if not legal_actions:
    return None
  action = random.choice(legal_actions)
  return int(action)

agents = [random_agent] * 3

# --- Configuration ---
#open_spiel_game_name = "universal_poker_proxy"
open_spiel_game_name = "universal_poker_proxy(betting=nolimit,numPlayers=2,stack=20000 20000,numRounds=4,blind=50 100,firstPlayer=2 1 1 1,numSuits=4,numRanks=13,numHoleCards=2,numBoardCards=0 3 1 1,bettingAbstraction=fullgame)"
game = pyspiel.load_game(open_spiel_game_name)
game_type = game.get_type()
environment_name = f"open_spiel_{game_type.short_name}"
agents_to_run = ["random"] * game.num_players() + ["game_master"]
output_html_file = f"kaggle_environments/envs/open_spiel/{environment_name}_game_replay.html"
replay_width = 500
replay_height = 450
# Set debug=True for more verbose output during the run, False for cleaner output
debug_mode = True
# --------------------

def _pprint_state(state):
    for i, player_state in enumerate(state):
        print(f"Player {i}:")
        print(player_state)

print(f"Setting up environment: '{environment_name}'")
env = make(environment_name, debug=debug_mode)

#_pprint_state(env.state)
#for _ in range(5):
#    agent_actions = [random_agent(env.state[i].observation) for i in range(len(agents))]
#    #print("================")
#    #print(agent_actions)
#    #print("================")
#    state = env.step(agent_actions)
#
#    #_pprint_state(env.state)






print(f"Running game with agents: {agents_to_run}...")
env.run(agents_to_run)
print("Game finished.")

print("Generating HTML replay...")
html_replay = env.render(mode="html", width=replay_width, height=replay_height)

print(f"Saving replay to: '{output_html_file}'")
with open(output_html_file, "w", encoding="utf-8") as f:
    f.write(html_replay)

print("-" * 20)
print(f"Successfully generated replay: {os.path.abspath(output_html_file)}")
print("-" * 20)