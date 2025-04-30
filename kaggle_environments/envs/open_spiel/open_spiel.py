# Copyright 2025 Kaggle Inc
# (Your license header)

import json
from os import path
import sys 
import os 

# --- Debugging sys.path ---
print(f"--- EXECUTING: open_spiel.py ---")
print(f"--- CWD in open_spiel.py: {os.getcwd()} ---")
print(f"--- LD_LIBRARY_PATH in open_spiel.py: {os.environ.get('LD_LIBRARY_PATH')} ---")
print(f"--- Initial sys.path in open_spiel.py: ---")
for p in sys.path:
    print(f"    {p}")
print(f"--- End of Initial sys.path ---")

pyspiel_dir = "/opt/open_spiel/build/python"
if pyspiel_dir not in sys.path:
    print(f"--- Adding to sys.path for pyspiel: {pyspiel_dir} ---")
    sys.path.insert(0, pyspiel_dir) 

open_spiel_lib_dir = "/opt/open_spiel/build/lib" 
current_ld_path = os.environ.get('LD_LIBRARY_PATH', '')
if open_spiel_lib_dir not in current_ld_path.split(os.pathsep):
    print(f"--- INFO: Consider adding {open_spiel_lib_dir} to LD_LIBRARY_PATH if pyspiel C++ dependencies are there ---")

try:
    print(f"--- Attempting to import pyspiel in open_spiel.py ---")
    import pyspiel
    print("--- Successfully imported pyspiel in open_spiel.py ---")
except Exception as e:
    print(f"--- ERROR in open_spiel.py trying to import pyspiel: {e} ---")
    print(f"--- sys.path AT ERROR in open_spiel.py: ---")
    for p_err in sys.path:
        print(f"    {p_err}")
    print(f"--- End of sys.path AT ERROR ---")
    raise

json_spec_path = path.abspath(path.join(path.dirname(__file__), "open_spiel.json"))
with open(json_spec_path) as f:
    specification = json.load(f)


#
#
# END IMPORTS
#
#

agents = {}
_OS_GAME_CACHE = {}

def _get_open_spiel_game(env_config: dict) -> pyspiel.Game:
    game_name = env_config.get("openSpielGameName", "tic_tac_toe")
    game_settings_dict = env_config.get("openSpielGameSettings", {})
    game_settings_tuple = tuple(sorted(game_settings_dict.items()))
    cache_key = (game_name, game_settings_tuple)
    if cache_key in _OS_GAME_CACHE:
        return _OS_GAME_CACHE[cache_key]
    try:
        game_params = {str(k): str(v) for k, v in game_settings_dict.items()}
        game = pyspiel.load_game(game_name, game_params)
        _OS_GAME_CACHE[cache_key] = game
        return game
    except Exception as e:
        print(f"Error loading OpenSpiel game '{game_name}' with settings {game_params}: {e}")
        if game_name != "tic_tac_toe":
             print("Falling back to 'tic_tac_toe' without parameters.")
             try:
                 game = pyspiel.load_game("tic_tac_toe")
                 _OS_GAME_CACHE[("tic_tac_toe", tuple())] = game
                 return game
             except Exception as e_fallback:
                 raise RuntimeError(f"Failed to load fallback 'tic_tac_toe': {e_fallback}")
        raise RuntimeError(f"Failed to load OpenSpiel game '{game_name}': {e}")

def _reconstruct_os_state(game, kaggle_steps_history, num_expected_agents):
    # kaggle_steps_history is env.steps
    # env.steps[0] is the initial state (no actions led to it from game play)
    # env.steps[1] is the state AFTER the first action was processed. The action is in env.steps[1][player].action
    # env.steps[k] is the state AFTER the k-th action. The action is in env.steps[k][player].action
    # To reconstruct the state *before* the N-th agent is about to act (i.e., after N-1 game actions),
    # we need to apply actions from env.steps[1] through env.steps[N-1].
    
    num_actions_to_replay = len(kaggle_steps_history) - 1
    print(f"--- _reconstruct_os_state: Replaying {num_actions_to_replay} historical game actions. ---")
    os_state = game.new_initial_state()
    print(f"--- _reconstruct_os_state: Initial OS state for reconstruction:\n{os_state.to_string()}---")

    # Loop from the first actual game move record up to the one before the current state record
    for i in range(num_actions_to_replay):
        # The (i+1)-th entry in kaggle_steps_history contains the i-th action played in the game
        step_entry_containing_action = kaggle_steps_history[i + 1]
        
        print(f"--- _reconstruct_os_state: Processing historical game action from env.steps[{i+1}] ---")
        if os_state.is_terminal():
            print(f"--- _reconstruct_os_state: OS state is terminal. Stopping replay early at game action {i}. ---")
            break
        
        current_os_player_for_step = os_state.current_player()
        print(f"--- _reconstruct_os_state: OS player to act (before this historical action): P{current_os_player_for_step} ---")
        print(f"--- _reconstruct_os_state: OS state BEFORE applying historical action from env.steps[{i+1}]:\n{os_state.to_string()}---")
        
        if os_state.is_chance_node():
            print(f"--- _reconstruct_os_state: OS state is a CHANCE NODE. ---")
            chance_outcomes = os_state.chance_outcomes()
            if chance_outcomes:
                action_to_apply = chance_outcomes[0][0] 
                print(f"--- _reconstruct_os_state: Applying chance action {action_to_apply}. ---")
                os_state.apply_action(action_to_apply)
            else:
                print(f"--- _reconstruct_os_state: CHANCE NODE had no outcomes. ---")
            continue # This chance action was one of the "game actions"

        # Ensure the player ID is valid for indexing into step_entry_containing_action
        if not (0 <= current_os_player_for_step < num_expected_agents):
            print(f"Warning (_reconstruct_os_state): OpenSpiel active player P{current_os_player_for_step} is not a mapped Kaggle agent. Cannot get action from history. State:\n{os_state.to_string()}---")
            continue

        action_taken_in_step = step_entry_containing_action[current_os_player_for_step].action
        print(f"--- _reconstruct_os_state: Historical action for P{current_os_player_for_step} from env.steps[{i+1}] was: {action_taken_in_step} ---")

        if action_taken_in_step is not None:
            current_legal_actions = os_state.legal_actions() 
            print(f"--- _reconstruct_os_state: Legal actions for P{current_os_player_for_step} are: {current_legal_actions} ---")
            if action_taken_in_step in current_legal_actions:
                os_state.apply_action(action_taken_in_step)
                print(f"--- _reconstruct_os_state: Successfully applied historical action {action_taken_in_step}. ---")
            else:
                print(f"*** CRITICAL WARNING (_reconstruct_os_state): Historical action {action_taken_in_step} for P{current_os_player_for_step} from env.steps[{i+1}] was ILLEGAL. State has likely DIVERGED. ***")
                print(f"*** OS State at divergence:\n{os_state.to_string()}---")
                print(f"*** Legal actions were: {current_legal_actions} ***")
        else:
            print(f"--- _reconstruct_os_state: Historical action from env.steps[{i+1}] for P{current_os_player_for_step} was None. No action applied. ---")
        
        print(f"--- _reconstruct_os_state: OS state AFTER processing historical game action {i} (from env.steps[{i+1}]):\n{os_state.to_string()}---")
    
    print(f"--- _reconstruct_os_state: Finished replaying history. Final reconstructed OS state:\n{os_state.to_string()}---")
    return os_state

def interpreter(state, env):
    game = _get_open_spiel_game(env.configuration)
    num_agents = game.num_players()
    if game.num_players() != len(state):
         raise ValueError(f"OpenSpiel game '{game.get_type().short_name}' requires {game.num_players()} players, "
                          f"but Kaggle environment is configured for {len(state)} agents (from JSON 'agents' field). "
                          "These must match.")
    
    print(f"--- interpreter: Called with len(env.steps) = {len(env.steps)} ---")
    # os_current_state is the OpenSpiel state *before* the current agent's submitted action is applied.
    os_current_state = _reconstruct_os_state(game, env.steps, num_agents) 
    
    print(f"--- interpreter: OS state after reconstruction (this is state_for_agent_action_validation):\n{os_current_state.to_string()}---")

    os_state_after_current_turn_action = os_current_state.clone() if os_current_state else None

    if not os_state_after_current_turn_action.is_terminal():
        active_os_player_id_on_reconstructed = os_current_state.current_player() # Player from reconstructed state
        print(f"--- interpreter: OS player_id to act (from reconstructed state os_current_state): {active_os_player_id_on_reconstructed} ---")

        if os_current_state.is_chance_node(): 
            print(f"--- interpreter: OS state (os_current_state) is a CHANCE NODE. ---")
            chance_outcomes = os_current_state.chance_outcomes()
            if chance_outcomes:
                action_to_apply_chance = chance_outcomes[0][0]
                print(f"--- interpreter: Applying chance action {action_to_apply_chance} to os_state_after_current_turn_action. ---")
                os_state_after_current_turn_action.apply_action(action_to_apply_chance)
            else:
                print(f"--- interpreter: CHANCE NODE had no outcomes. ---")
        
        active_os_player_id_for_agent_action = os_state_after_current_turn_action.current_player()
        if active_os_player_id_for_agent_action == pyspiel.PlayerId.SIMULTANEOUS:
            print("Warning: Simultaneous move games are not fully supported by this basic interpreter.")

        if 0 <= active_os_player_id_for_agent_action < num_agents: 
            agent_to_act_idx = active_os_player_id_for_agent_action
            kaggle_active_agent_state = state[agent_to_act_idx] 
            action_to_apply_agent = kaggle_active_agent_state.action 
            
            print(f"--- interpreter: Player {agent_to_act_idx} submitted action: {action_to_apply_agent} ---")
            # Legal actions for the submitted action must be checked against the state the agent acted upon.
            # This is os_current_state if no chance node occurred, or os_state_after_current_turn_action if a chance node resolved.
            state_for_agent_action_validation = os_state_after_current_turn_action if os_current_state.is_chance_node() else os_current_state
            
            current_agent_legal_actions = state_for_agent_action_validation.legal_actions()
            print(f"--- interpreter: Legal actions for P{agent_to_act_idx} (from state_for_agent_action_validation '{state_for_agent_action_validation.to_string().strip()}') are: {current_agent_legal_actions} ---")

            if action_to_apply_agent is not None:
                if action_to_apply_agent in current_agent_legal_actions:
                    # Apply agent's action to os_state_after_current_turn_action (which might have already had a chance action applied)
                    os_state_after_current_turn_action.apply_action(action_to_apply_agent) 
                    print(f"--- interpreter: Successfully applied submitted action {action_to_apply_agent}. ---")
                else:
                    state[agent_to_act_idx].status = "INVALID" 
                    print(f"*** interpreter: Submitted action {action_to_apply_agent} by P{agent_to_act_idx} is INVALID. ***")
            else:
                print(f"--- interpreter: Player {agent_to_act_idx} submitted None action. ---")
        elif not os_state_after_current_turn_action.is_terminal() and not os_state_after_current_turn_action.is_chance_node():
             print(f"Warning (_interpreter_): OpenSpiel current player is {active_os_player_id_for_agent_action}. No Kaggle agent action to apply.")
    
    print(f"--- interpreter: Final OS state for this turn (os_state_after_current_turn_action):\n{os_state_after_current_turn_action.to_string()}---")

    new_kaggle_states = []
    os_is_terminal = os_state_after_current_turn_action.is_terminal()
    os_rewards_list = os_state_after_current_turn_action.rewards() if os_is_terminal else [] 
    
    for i in range(num_agents):
        agent_observation = {}
        final_os_player_for_obs = os_state_after_current_turn_action.current_player()

        print(f"--- interpreter (Obs Gen): For agent P{i}, OS player for next turn is P{final_os_player_for_obs} ---")
        print(f"--- interpreter (Obs Gen): OS state used for P{i}'s obs (os_state_after_current_turn_action):\n{os_state_after_current_turn_action.to_string()}---")

        if os_is_terminal:
            status = "DONE"
            agent_observation["legal_actions"] = []
        elif i == final_os_player_for_obs: 
            status = "ACTIVE"
            current_turn_legal_actions = []
            if not os_state_after_current_turn_action.is_chance_node(): 
                current_turn_legal_actions = os_state_after_current_turn_action.legal_actions(i)
            agent_observation["legal_actions"] = current_turn_legal_actions
            print(f"--- interpreter (Obs Gen): Agent P{i} is ACTIVE. Legal actions for next turn: {current_turn_legal_actions} ---")
        else:
            status = "INACTIVE"
            agent_observation["legal_actions"] = []
            print(f"--- interpreter (Obs Gen): Agent P{i} is INACTIVE. ---")

        agent_observation["openSpielGameName"] = env.configuration.get("openSpielGameName", "tic_tac_toe")
        agent_observation["raw_observation_string"] = os_state_after_current_turn_action.to_string()
        tensor = os_state_after_current_turn_action.observation_tensor(i)
        agent_observation["observation_tensor"] = [float(x) for x in tensor]
        agent_observation["current_player_id"] = int(final_os_player_for_obs) if final_os_player_for_obs >= 0 else -1
        agent_observation["is_terminal"] = os_is_terminal
        agent_observation["player_id"] = i
        agent_observation["remainingOverageTime"] = state[i].observation.remainingOverageTime

        agent_reward = 0.0
        if os_is_terminal and i < len(os_rewards_list):
            agent_reward = float(os_rewards_list[i])
        elif not os_is_terminal:
            reward_spec = env.specification.get("reward", {})
            agent_reward = reward_spec.get("default", 0.0)

        current_agent_final_status = status
        if state[i].status == "INVALID" and status != "DONE": 
            current_agent_final_status = "INVALID"
            agent_reward = None 

        new_kaggle_states.append({
            "action": state[i].action, 
            "reward": agent_reward,
            "info": {},
            "observation": agent_observation,
            "status": current_agent_final_status
        })
    return new_kaggle_states

def renderer(state_history_entry, env):
    if (state_history_entry and 
        len(state_history_entry) > 0 and # Check if list is not empty
        hasattr(state_history_entry[0], "observation") and 
        state_history_entry[0].observation is not None and # Check if observation object exists
        hasattr(state_history_entry[0].observation, "raw_observation_string")):
        
        final_board_string = state_history_entry[0].observation.raw_observation_string
        # print(f"--- renderer: Rendering board directly from last step's observation ---\n{final_board_string}")
        return final_board_string
    else:
        # print(f"--- renderer: Fallback - Observation structure not as expected or missing. Reconstructing. ---")
        game = _get_open_spiel_game(env.configuration)
        if env.steps: 
            # This full reconstruction can be problematic if history is inconsistent
            # temp_state = _reconstruct_os_state(game, env.steps, game.num_players())
            # return temp_state.to_string()
            # Safer to return the last known good string if possible, or initial if nothing else
            if len(env.steps) > 0 and len(env.steps[-1]) > 0 and hasattr(env.steps[-1][0], "observation") and env.steps[-1][0].observation is not None and hasattr(env.steps[-1][0].observation, "raw_observation_string"):
                 return env.steps[-1][0].observation.raw_observation_string
            else: # Cannot find a raw string, render initial state
                print("--- renderer: Could not find raw_observation_string in last step, rendering initial state. ---")
                return game.new_initial_state().to_string()

        else: 
            print("--- renderer: No steps in history, rendering initial state. ---")
            return game.new_initial_state().to_string()

def html_renderer():
    return """
        <script>
          function renderer(context) {
            const { parent, environment, step, frame } = context;
            parent.innerHTML = ''; 
            const container = document.createElement("div");
            container.style.fontFamily = "monospace";
            container.style.whiteSpace = "pre";
            let title = 'OpenSpiel Game';
            if (environment && environment.configuration && environment.configuration.openSpielGameName) {
                title = environment.configuration.openSpielGameName;
            }
            let stateString = "Loading state...";
            if (environment && environment.steps && environment.steps[step] && environment.steps[step][0] &&
                environment.steps[step][0].observation && environment.steps[step][0].observation.raw_observation_string) {
                stateString = environment.steps[step][0].observation.raw_observation_string;
            }
            container.innerHTML = `
              <h3>${title} (Kaggle Wrapper)</h3>
              <p>Step: ${step}</p>
              <div>Game State:</div>
              <div>${stateString.replace(/\\n/g, '<br>')}</div>
            `;
            parent.appendChild(container);
          }
        </script>
    """
