import os
import random
from kaggle_environments import make
import pyspiel

# --- Configuration ---
#open_spiel_game_name = "universal_poker"
#open_spiel_game_name = "universal_poker_proxy"
#open_spiel_game_name = "universal_poker_proxy(betting=nolimit,numPlayers=2,stack=20 20,numRounds=4,blind=1 2,firstPlayer=2 1 1 1,numSuits=4,numRanks=13,numHoleCards=2,numBoardCards=0 3 1 1,bettingAbstraction=fullgame)"
#open_spiel_game_name = "universal_poker(betting=nolimit,numPlayers=2,stack=20 20,numRounds=4,blind=1 2,firstPlayer=2 1 1 1,numSuits=4,numRanks=13,numHoleCards=2,numBoardCards=0 3 1 1,bettingAbstraction=fullgame)"

#open_spiel_game_name = "universal_poker(betting=nolimit,bettingAbstraction=fullgame,blind=1 2,firstPlayer=2 1 1 1,numBoardCards=0 3 1 1,numHoleCards=2,numPlayers=2,numRanks=13,numRounds=4,numSuits=4,stack=20 20)"
#open_spiel_game_name = "universal_poker_proxy(betting=nolimit,bettingAbstraction=fullgame,blind=1 2,firstPlayer=2 1 1 1,numBoardCards=0 3 1 1,numHoleCards=2,numPlayers=2,numRanks=13,numRounds=4,numSuits=4,stack=20 20)"

#open_spiel_game_name = "universal_poker(betting=nolimit,numPlayers=2,stack=20000 20000,numRounds=4,blind=50 100,firstPlayer=2 1 1 1,numSuits=4,numRanks=13,numHoleCards=2,numBoardCards=0 3 1 1,bettingAbstraction=fullgame)"
#open_spiel_game_name = "go"
open_spiel_game_name = "chess"

game = pyspiel.load_game(open_spiel_game_name)
game_type = game.get_type()
environment_name = f"open_spiel_{game_type.short_name}"
agents_to_run = ["random"] * game.num_players()
output_html_file = f"kaggle_environments/envs/open_spiel/{environment_name}_game_replay.html"
replay_width = 500
replay_height = 450
debug_mode = True

#game_params = game.get_parameters()
#game_params = {k: v for k, v in game_params.items() if v}
#config = {"openSpielGameParameters": game_params}
#env = make(environment_name, configuration=config, debug=debug_mode)
env = make(environment_name, debug=debug_mode)

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