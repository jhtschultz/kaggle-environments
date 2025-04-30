from kaggle_environments import make
import kaggle_environments
import random

print(f"kaggle_environments loaded from: {kaggle_environments.__file__}")

def random_os_agent(observation, configuration):
    agent_player_id = observation.get("player_id", "Unknown")
    current_os_turn_player_id = observation.get("current_player_id", "Unknown")
    is_agent_active_turn = (str(agent_player_id) == str(current_os_turn_player_id)) # Compare as strings for safety

    print(f"--- AGENT P{agent_player_id} (OS current turn in obs: P{current_os_turn_player_id}, Agent is Active: {is_agent_active_turn}) ---")
    print(f"    Received observation.legal_actions: {observation.legal_actions}")
    # Optionally print the full observation if short enough or needed
    # print(f"    Full observation for P{agent_player_id}: {observation}")
    print(f"    Raw_observation_string for P{agent_player_id}: {observation.get('raw_observation_string', 'N/A').strip()}")


    if is_agent_active_turn and observation.legal_actions:
        choice = random.choice(observation.legal_actions)
        print(f"    Agent P{agent_player_id} ACTIVE, chose: {choice} from {observation.legal_actions}")
        return choice
    else:
        if observation.get("is_terminal"):
            print(f"    Agent P{agent_player_id} sees TERMINAL state, returning None (no action).")
        elif not is_agent_active_turn:
            print(f"    Agent P{agent_player_id} INACTIVE (OS turn is P{current_os_turn_player_id}), returning None (no action).")
        elif not observation.legal_actions:
             print(f"    Agent P{agent_player_id} ACTIVE but has NO legal actions, returning None (no action).")
        return None # Return None if not active or no legal actions

try:
    print("Attempting to make the 'open_spiel' environment...")
    env = make("open_spiel", debug=False)
    print(f"Successfully made environment: {env.name}")
    print(f"Configuration: {env.configuration}")

    print("\nRunning a game with two random OpenSpiel agents...")
    final_steps = env.run([random_os_agent, random_os_agent])

    print("\nGame Over. Final state (from renderer):")
    env.render(mode="human")

    if final_steps:
        last_state_per_agent = final_steps[-1]
        for i, agent_state in enumerate(last_state_per_agent):
            print(f"Agent {i}: Action Taken={agent_state.action}, Reward={agent_state.reward}, Status={agent_state.status}")
            # print(f"Agent {i} Final Observation: {agent_state.observation}")


except Exception as e:
    print(f"An error occurred in runner: {e}")
    import traceback
    traceback.print_exc()
