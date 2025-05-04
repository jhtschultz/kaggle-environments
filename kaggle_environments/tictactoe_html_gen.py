import os
from kaggle_environments import make

# --- Configuration ---
environment_name = "open_spiel_gin_rummy"
agents_to_run = ["random", "random"] # You can replace "random" with paths to your agent files
output_html_file = f"{environment_name}_game_replay.html"
replay_width = 500
replay_height = 450
# Set debug=True for more verbose output during the run, False for cleaner output
debug_mode = False
# --------------------

try:
    # 1. Create the environment instance
    print(f"Setting up environment: '{environment_name}'")
    env = make(environment_name, debug=debug_mode)

    # 2. Run a full game episode with the specified agents
    print(f"Running game with agents: {agents_to_run}...")
    # The env.run() method executes the game and stores the steps internally
    env.run(agents_to_run)
    print("Game finished.")

    # 3. Render the completed episode directly to HTML
    # The env object now holds the state and steps from the run we just did
    print("Generating HTML replay...")
    html_replay = env.render(mode="html", width=replay_width, height=replay_height)

    # 4. Write the HTML content to the output file
    print(f"Saving replay to: '{output_html_file}'")
    with open(output_html_file, "w", encoding="utf-8") as f:
        f.write(html_replay)

    print("-" * 20)
    print(f"Successfully generated replay: {os.path.abspath(output_html_file)}")
    print("You can open this file in VS Code (using Live Preview) or your web browser.")
    print("-" * 20)

except Exception as e:
    print(f"An error occurred: {e}")
    import traceback
    traceback.print_exc()