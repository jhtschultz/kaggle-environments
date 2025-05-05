import os
from kaggle_environments import make

# --- Configuration ---
open_spiel_game_name = "hearts"
environment_name = f"open_spiel_{open_spiel_game_name}"
# TODO
agents_to_run = ["random"] * 4
output_html_file = f"{environment_name}_game_replay.html"
replay_width = 500
replay_height = 450
# Set debug=True for more verbose output during the run, False for cleaner output
debug_mode = False
# --------------------

print(f"Setting up environment: '{environment_name}'")
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
print("You can open this file in VS Code (using Live Preview) or your web browser.")
print("-" * 20)