import sys
import os
import random
import importlib.util 

# --- Ensure local workspace is prioritized in Python's path FIRST ---
workspace_dir = "/workspace" # Or adjust if your structure is different
if workspace_dir not in sys.path or sys.path[0] != workspace_dir:
    if workspace_dir in sys.path: sys.path.remove(workspace_dir) # Remove if exists elsewhere
    print(f"--- Prepending '{workspace_dir}' to sys.path to prioritize local modules ---")
    sys.path.insert(0, workspace_dir)
print(f"--- Top of sys.path: {sys.path[0]} ---")

# --- Function to Clean Kaggle Env from sys.modules ---
def force_reimport_kaggle_environments():
    """
    Removes kaggle_environments and its key submodules from sys.modules
    to force a complete re-import and re-initialization on next import.
    """
    print("\n--- Attempting to force re-import by cleaning sys.modules ---")
    # List modules related to kaggle_environments structure and initialization.
    # Need to ensure all relevant parts involved in registration and core structures are removed.
    modules_to_remove = [
        # Specific envs loaded by __init__
        'kaggle_environments.envs.connectx.connectx',
        'kaggle_environments.envs.tictactoe.tictactoe',
        'kaggle_environments.envs.open_spiel.open_spiel',
        # Core components potentially holding state or involved in registration
        'kaggle_environments.agent',
        'kaggle_environments.core',
        'kaggle_environments.utils',
        'kaggle_environments.errors',
        'kaggle_environments.api',
        'kaggle_environments.main',
        # The top-level package itself
        'kaggle_environments'
    ]
    removed_count = 0
    for module_name in modules_to_remove:
        if module_name in sys.modules:
            try:
                del sys.modules[module_name]
                removed_count += 1
            except Exception as e:
                print(f"  Warning: Could not remove '{module_name}': {e}")
    print(f"--- Removed {removed_count} relevant module entries from sys.modules. ---")

# --- Main Script Logic ---

# --- Step 1: (Optional) Initial Import - Simulates cached state ---
# You might comment this out if running the script fresh each time
try:
    print("--- Performing initial import (simulating cached state) ---")
    import kaggle_environments
    from kaggle_environments import make
    print(f"Initial envs: {list(kaggle_environments.environments.keys())}")
except Exception as e:
    print(f"(Initial import failed or skipped: {e})")

# --- Step 2: Clean the cache ---
force_reimport_kaggle_environments()

# --- Step 3: Re-import after cleaning ---
# This import WILL execute __init__.py from scratch
print("\n--- Re-importing kaggle_environments after cache clean ---")
import_success = False
try:
    # Import the top-level package. This runs __init__.py.
    import kaggle_environments
    # Explicitly import the core module WHERE the 'environments' dict lives.
    import kaggle_environments.core
    # Import the 'make' function AFTER the package is initialized.
    from kaggle_environments import make
    print("--- Successfully re-imported kaggle_environments and its core components ---")
    import_success = True
except Exception as e:
     print(f"*** ERROR during re-import after cache clean: {type(e).__name__}: {e} ***")
     import traceback; traceback.print_exc()


# --- Define the Random Agent ---
# (Moved definition outside the 'if import_success' block for clarity)
def random_os_agent(observation, configuration):
    """A simple agent that chooses a random legal action."""
    agent_player_id = observation.get("player_id", "Unknown") # Get agent's own ID
    current_os_turn_player_id = observation.get("current_player", "Unknown") # Get whose turn it is in OS terms
    is_agent_active_turn = (str(agent_player_id) == str(current_os_turn_player_id)) # Compare as strings for safety

    print(f"\n--- AGENT P{agent_player_id} ---") # Add P prefix for clarity
    print(f"    Observed Step: {observation.step}, OS Turn in Obs: P{current_os_turn_player_id}, Agent Active: {is_agent_active_turn}")
    print(f"    Raw State: {observation.get('raw_observation_string', 'N/A').strip()}")
    print(f"    Legal Actions: {observation.legal_actions}")
    # print(f"    Full Obs: {observation}") # Uncomment for very detailed view

    if is_agent_active_turn and observation.legal_actions:
        choice = random.choice(observation.legal_actions)
        print(f"    ACTION CHOSEN: {choice}")
        return choice
    else:
        if observation.get("is_terminal"): print(f"    ACTION: None (Terminal State)")
        elif not is_agent_active_turn: print(f"    ACTION: None (Not Agent's Turn)")
        elif not observation.legal_actions: print(f"    ACTION: None (No Legal Actions)")
        return None # Return None if not active or no legal actions

# --- Step 4: Check Registry and Attempt Make ---
if import_success:
    print(f"\nkaggle_environments path after re-import: {kaggle_environments.__file__}")
    try:
        # *** Directly access the registry from the re-imported core module ***
        environments_registry = kaggle_environments.core.environments
        available_envs_keys = list(environments_registry.keys())
        print(f"Available environments found in registry after re-import ({len(available_envs_keys)}):")
        # Print a sample, including potentially the one we want
        sample_keys = available_envs_keys[:5] + available_envs_keys[-5:]
        if "open_spiel_kuhn_poker" in available_envs_keys: sample_keys.append("open_spiel_kuhn_poker")
        if "open_spiel_kuhn_poker" in available_envs_keys: sample_keys.append("open_spiel_gin_rummy")
        if "tictactoe" in available_envs_keys: sample_keys.append("tictactoe")
        print(f"  Sample: {sorted(list(set(sample_keys)))}")

        # Define the target environment
        # target_env = "tictactoe"
        target_env = "open_spiel_tic_tac_toe"
        # target_env = "open_spiel_gin_rummy"

        # Check if the target is actually in the registry we have access to
        if target_env in environments_registry:
            print(f"\nTarget environment '{target_env}' FOUND in the accessed registry.")
            print(f"Attempting to make environment: '{target_env}'")
            try:
                # *** Use the 'make' function imported AFTER re-import ***
                env = make(target_env, debug=True)
                print(f"Successfully built environment '{env.name}'.")

                # Try a basic render to confirm it works
                print("\nRendering initial state:")
                print(env.render(mode="ansi"))

                # --- Run a full game ---
                print("\n--- Running Full Game with Random Agents ---")
                # env.run() returns the list of steps, where each step contains the state for each agent
                final_steps = env.run([random_os_agent, random_os_agent])
                print("\n--- Game Finished ---")

                # Render final state
                print("\nFinal Board State:")
                print(env.render(mode="ansi"))

                # Print final rewards and statuses
                if final_steps:
                    last_state_per_agent = final_steps[-1]
                    for i, agent_state in enumerate(last_state_per_agent):
                        print(f"Agent {i} Final: Reward={agent_state.reward}, Status={agent_state.status}")
            except Exception as e:
                 # Catch errors specifically during make() or render()
                 print(f"\n*** ERROR calling make() or render() for '{target_env}': {type(e).__name__}: {e} ***")
                 print("*** This implies the registry was correct, but Environment init or rendering failed. Check previous error (InvalidArgument?). ***")
                 import traceback; traceback.print_exc()
        else:
             # This is the key failure point if the registration didn't "stick"
             print(f"\n*** CRITICAL ERROR: Target environment '{target_env}' NOT FOUND in registry after re-import. ***")
             print("*** The __init__.py logs showed registration, but it's not visible here. Module reference issue suspected. ***")
             print(f"Full list of found envs ({len(available_envs_keys)}): {available_envs_keys}")

    except Exception as e:
        # Catch errors accessing the registry or other issues
        print(f"*** ERROR accessing environments registry or during checks: {e} ***")
        import traceback; traceback.print_exc()
else:
    print("\n--- Skipping checks due to import failure after cache clean ---")