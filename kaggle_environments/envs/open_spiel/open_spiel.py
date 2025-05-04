# envs/open_spiel/open_spiel.py
# Copyright 2025 Kaggle Inc
# (Your license header)

import json
from os import path
import sys
import os
import copy # For deep copying the template

# --- Path Setup and Debugging ---
print(f"--- EXECUTING: open_spiel.py ---")
# print(f"--- CWD in open_spiel.py: {os.getcwd()} ---") # Optional debug
# print(f"--- LD_LIBRARY_PATH in open_spiel.py: {os.environ.get('LD_LIBRARY_PATH')} ---") # Optional debug
# print(f"--- Initial sys.path in open_spiel.py: ---") # Optional debug
# for p in sys.path: print(f"    {p}") # Optional debug
# print(f"--- End of Initial sys.path ---") # Optional debug

# Add pyspiel build directory to Python path
pyspiel_dir = os.environ.get("PYSPIEL_BUILD_DIR", "/opt/open_spiel/build/python")
if pyspiel_dir not in sys.path:
    print(f"--- Adding to sys.path for pyspiel: {pyspiel_dir} ---")
    sys.path.insert(0, pyspiel_dir)

# Check LD_LIBRARY_PATH (informational)
open_spiel_lib_dir = os.environ.get("OPEN_SPIEL_LIB_DIR", "/opt/open_spiel/build/lib")
current_ld_path = os.environ.get('LD_LIBRARY_PATH', '')
if open_spiel_lib_dir and open_spiel_lib_dir not in current_ld_path.split(os.pathsep):
    print(f"--- INFO: Consider adding {open_spiel_lib_dir} to LD_LIBRARY_PATH if needed ---")

# --- Import pyspiel ---
try:
    print(f"--- Attempting to import pyspiel in open_spiel.py ---")
    import pyspiel
    print("--- Successfully imported pyspiel in open_spiel.py ---")
except Exception as e:
    print(f"--- ERROR importing pyspiel: {e} ---")
    raise ImportError(f"Failed to import pyspiel: {e}")


# --- Base Kaggle Environment Specification Template (as Python Dict) ---
# This template defines the structure that will be placed under the top-level
# 'specification' key, adhering strictly to the base_schema.json provided.
# It aims to define ONLY what's necessary and let core.py handle standard parts.
DEFAULT_ACT_TIMEOUT = 5.0 # Keep for interpreter fallback
MAX_LEN_THRESHOLD = 5000 # Used for description only
DEFAULT_EPISODE_STEPS = 1000 # Fallback max steps if game max_len is 0 or very large

BASE_SPEC_TEMPLATE = {
  "name": "PLACEHOLDER_NAME",
  "title": "PLACEHOLDER_TITLE",
  "description": "PLACEHOLDER_DESCRIPTION",
  "version": "0.1.0",
  "agents": ["PLACEHOLDER_AGENTS"], # Required agent count list, e.g., [2]

  # --- Add back configuration schema definition ---
  "configuration": {
    "episodeSteps": {
      "description": "Maximum number of steps (actions taken) in an episode.",
      "type": "integer",
      "default": "PLACEHOLDER_EPISODE_STEPS" # Dynamically set during generation
    },
    "actTimeout": {
      "description": "Maximum runtime (seconds) to obtain an action from an agent.",
      "type": "number",
      "default": DEFAULT_ACT_TIMEOUT
    },
    "runTimeout": { # Add runTimeout for completeness, using a reasonable default
        "description": "Maximum runtime (seconds) for the entire episode.",
        "type": "number",
        "default": 1200.0
    },
    "openSpielGameName": {
      "description": "The short_name of the OpenSpiel game to load. This is fixed for this environment.",
      "type": "string",
      "default": "PLACEHOLDER_GAME_SHORT_NAME" # Set during generation
    }
    # NOTE: openSpielGameSettings is intentionally omitted here. It's meant to be a runtime override.
  },

  # --- Schemas defined according to base_schema.json['specification']['properties'] ---
  "observation": {
      # "type": "object",
      # NOTE: Removed "type": "object" and "additionalProperties": True below
      # to work around an issue in core.py's extend_specification function.
      # This function incorrectly handles top-level non-dict values.
      "properties": {
            # Game/Wrapper specific observation fields
            "openSpielGameName": {"description": "Short name of the OpenSpiel game.", "type": "string"},
            "raw_observation_string": {"description": "String representation of state.", "type": "string"},
            "observation_tensor": {"description": "Flattened state tensor for agent.", "type": "array", "items": {"type": "number"}},
            "legal_actions": {"description": "List of legal action IDs.", "type": "array", "items": {"type": "integer"}},
            "current_player": {"description": "ID of player whose turn it is.", "type": "integer"},
            "is_terminal": {"description": "Boolean indicating game end.", "type": "boolean"},
            "player_id": {"description": "ID of the agent receiving this observation.", "type": "integer"},

            # --- WORKAROUND for core.py spec processing error ---
            # Define standard fields EXACTLY as they appear in base_schema['state']['properties']['observation']['properties']
            # to prevent core.py from erroring when it processes/merges schemas.
            "remainingOverageTime": {
                "description": "Total remaining banked time (seconds) that can be used in excess of per-step actTimeouts -- agent is disqualified with TIMEOUT status when this drops below 0.",
                "shared": False,
                "type": "number",
                "minimum": 0,
                # "default": 12 # Let core.py handle applying the default value
            },
            "step": {
                "description": "Current step within the episode.",
                "type": "integer",
                "shared": True,
                "minimum": 0,
                # "default": 0 # Let core.py handle applying the default value
            }
            # --- END WORKAROUND ---
        },
        # "additionalProperties": True, # Removed due to core.py issue
        "default": {} # Keeping 'default' as its value is a dict. Required by base schema.
  },
   "action": {
        "type": ["integer", "null"], # Allow null for errors/timeouts
        "minimum": 0, # Assuming non-negative action IDs
        "default": 0 # Required by base schema for specification.action
   },
  "reward": {
        "type": ["number", "null"], # Allow null for errors/timeouts
        "default": 0.0 # Required by base schema for specification.reward
  },
}


# --- Agent Cache and Game Loading Helper ---
_OS_GAME_CACHE = {}
def _get_open_spiel_game(env_config: dict) -> pyspiel.Game:
    game_name=env_config.get("openSpielGameName","tic_tac_toe"); game_settings_dict=env_config.get("openSpielGameSettings",{}); game_settings_tuple=tuple(sorted(game_settings_dict.items())); cache_key=(game_name,game_settings_tuple)
    if cache_key in _OS_GAME_CACHE: return _OS_GAME_CACHE[cache_key]
    try:
        game_params={str(k):str(v) for k,v in game_settings_dict.items()}
        game=pyspiel.load_game(game_name,game_params); _OS_GAME_CACHE[cache_key]=game
        return game
    except Exception as e: print(f"*** ERROR (_get_open_spiel_game): Failed loading '{game_name}': {e} ***"); raise

# --- State Reconstruction Helper ---
def _reconstruct_os_state(game: pyspiel.Game, kaggle_steps_history: list, num_expected_agents: int) -> pyspiel.State:
    # kaggle_steps_history[0] is the initial dummy state from core.py
    # kaggle_steps_history[1] is the list returned by interpreter after step 0
    # kaggle_steps_history[k] is the list returned by interpreter after step k-1
    num_interpreter_calls = len(kaggle_steps_history) - 1 # Number of actual game steps processed so far
    os_state = game.new_initial_state()
    print(f"--- DEBUG _reconstruct: History len={len(kaggle_steps_history)}, num_calls={num_interpreter_calls} ---")

    for i in range(num_interpreter_calls): # Iterate through steps 0, 1, ..., k-1
        step_output = kaggle_steps_history[i+1] # Output state list from interpreter call 'i'
        print(f"--- DEBUG _reconstruct: Processing history step index {i+1} (corresponds to end of game step {i}) ---")

        # Apply chance moves deterministically FIRST for this step transition
        # This assumes chance nodes are resolved *before* the player acts in a step.
        while os_state.is_chance_node():
             outcomes = os_state.chance_outcomes()
             if outcomes:
                 # Apply the first outcome deterministically (consistent with interpreter)
                 chance_action = outcomes[0][0]
                 print(f"--- DEBUG _reconstruct: Applying chance action {chance_action} before player action in step {i} ---")
                 os_state.apply_action(chance_action)
             else:
                 print(f"--- WARNING _reconstruct: Chance node with no outcomes at step {i} ---")
                 break # Should not happen

        # Check for terminal state *after* chance resolution
        if os_state.is_terminal():
            print(f"--- DEBUG _reconstruct: State became terminal after chance node in step {i}. Stopping. ---")
            break

        # Now apply the player's action for step 'i'
        os_player=os_state.current_player()
        print(f"--- DEBUG _reconstruct: Expecting player action for step {i}, OS Player={os_player} ---")

        if 0 <= os_player < num_expected_agents:
            # Retrieve the action that was successfully applied in step 'i' from the 'info' dict.
            action_applied_in_step = step_output[os_player].info.get("submitted_action")

            if action_applied_in_step is not None:
                legal=os_state.legal_actions()
                if action_applied_in_step in legal:
                    print(f"--- DEBUG _reconstruct: Applying action {action_applied_in_step} for P{os_player} from history step {i+1} ---")
                    os_state.apply_action(action_applied_in_step) # Corrected variable name
                else:
                    # This indicates a divergence between the game logic and the history.
                    print(f"*** CRITICAL WARNING (_reconstruct): Hist. action {action_applied_in_step} for P{os_player} from step {i+1} ILLEGAL. State likely DIVERGED. Legal: {legal} ***")
                    break # Stop reconstruction on divergence
            else:
                 # This means the agent's action in step 'i' was invalid/timeout/None.
                 # The game state should not have advanced for this player's turn in that step.
                 print(f"--- DEBUG _reconstruct: No valid action found in history info for P{os_player} at step {i+1}. State remains unchanged for this player turn. ---")
                 # Continue to the next step in history.
        elif os_player == pyspiel.PlayerId.SIMULTANEOUS:
             # TODO: Handle reconstruction for simultaneous games if needed. Requires storing list in info.
             print(f"*** WARNING (_reconstruct): Simultaneous move reconstruction not fully implemented. State may diverge. ***")
             break # Stop for now

    print(f"--- DEBUG _reconstruct: Finished reconstruction. Final state string:\n{os_state.to_string()} ---")
    return os_state

# --- Core Kaggle Environment Functions ---
def interpreter(state, env):
    """Kaggle interpreter function."""
    # Get game name/settings from RUNTIME configuration passed via make()
    print("DEBUG INTERPRETER START:")
    print(state)
    game_name = env.configuration.get("openSpielGameName", "tic_tac_toe")
    game = _get_open_spiel_game({"openSpielGameName": game_name, **env.configuration})
    num_agents = game.num_players()

    if len(state) != num_agents: raise ValueError(f"Runtime agent count {len(state)} != game players {num_agents} for '{game_name}'.")

    os_current_state = _reconstruct_os_state(game, env.steps, num_agents)
    os_state_after = os_current_state.clone()
    applied_actions = [None] * num_agents # Track successfully applied actions for storing in info

    # --- ADDED DEBUG: State *after* chance nodes, *before* action processing ---
    if env.debug:
        print(f"--- DEBUG INTERPRETER ({env.name}): State post-chance, pre-action. IsTerminal: {os_state_after.is_terminal()}, CurrentPlayer: {os_state_after.current_player()}, IsChance: {os_state_after.is_chance_node()} ---")
        print(f"--- State String:\n{os_state_after.to_string()}\n--- End State String ---")
    if not os_state_after.is_terminal():
        is_initial_reset_call = (len(env.steps) == 1) # Check if this is the first interpreter call during reset
        active_player = os_state_after.current_player()

        # --- Step 1: Process Submitted Player Action ---
        # Only apply if not initial reset and the current state is a player node (not chance/terminal)
        if not is_initial_reset_call and not os_state_after.is_chance_node():
            if active_player == pyspiel.PlayerId.SIMULTANEOUS:
                # TODO: Refine simultaneous game handling if needed.
                # Need to know how the specific OpenSpiel game expects actions (list length, handling of None/invalid).
                actions_submitted = [state[idx].action for idx in range(num_agents)]
                try:
                    # Assuming apply_actions handles None or requires a specific invalid action constant.
                    # actions_to_apply = [a if a is not None else pyspiel.INVALID_ACTION for a in actions_submitted] # Example
                    os_state_after.apply_actions(actions_submitted) # Or actions_to_apply
                    # Store submitted actions. Status might need update based on apply_actions result/exceptions.
                    applied_actions = actions_submitted
                except Exception as e:
                    print(f"*** ERROR interpreter ({env.name}): apply_actions failed: {e} ***")
                    # Mark all involved agents as ERROR? Or check individual action validity? Complex.
                    for i in range(num_agents): state[i].status = "ERROR" # Simplistic approach
            elif 0 <= active_player < num_agents:
                action = state[active_player].action # Action submitted by the agent for this step
                if action is not None:
                    legal = os_state_after.legal_actions()
                    if action in legal:
                        try:
                            os_state_after.apply_action(action)
                            applied_actions[active_player] = action # Store successfully applied action
                        except Exception as e:
                            print(f"*** ERROR interpreter ({env.name}): apply_action failed for P{active_player} action {action}: {e} ***")
                            state[active_player].status = "ERROR" # Mark agent status based on input state
                    else:
                        # Action submitted was illegal according to the state before the action
                        print(f"--- INFO interpreter ({env.name}): P{active_player} submitted INVALID action {action}. Legal: {legal} ---")
                        state[active_player].status = "INVALID" # Mark agent status based on input state
                        applied_actions[active_player] = None # Ensure no action is recorded as applied
                # else: action is None (e.g., agent timed out or returned None), state doesn't change for this player. Status handled by core.py?

    # --- Step 2: Handle Chance Nodes AFTER player action (if any) ---
    while os_state_after.is_chance_node():
        outcomes = os_state_after.chance_outcomes()
        if outcomes: os_state_after.apply_action(outcomes[0][0]) # Apply first outcome deterministically
        else: print(f"--- WARNING interpreter ({env.name}): Chance node with no outcomes ---"); break

    # --- Step 3: Generate next states for Kaggle based on the final os_state_after ---
    new_states = []; is_terminal = os_state_after.is_terminal()
    returns = os_state_after.returns() if is_terminal else [0.0] * num_agents
    next_player = os_state_after.current_player()
    # Use core.py's configuration defaults if available, else fallback
    act_timeout_default = env.configuration.get("actTimeout", DEFAULT_ACT_TIMEOUT)

    for i in range(num_agents):
        status = ""; reward = None
        input_status = state[i].status # Get status from input state

        # --- MODIFIED: Don't inherit INVALID/TIMEOUT/ERROR status during initial reset ---
        # This prevents the dummy action check from incorrectly marking the initial state invalid.
        # --- Check input status AND if the submitted action was invalid ---
        if not is_initial_reset_call and input_status in ["INVALID", "TIMEOUT", "ERROR"]:
            # If it's *not* the reset call, inherit the status if it's a terminal one.
            status = input_status; reward = None
        elif not is_initial_reset_call and i == active_player and applied_actions[i] is None and state[i].action is not None: # Check if *this* agent submitted an invalid action
            status = state[i].status; reward = None
        elif is_terminal: # Check if the game ended *after* the action was applied
             status = "DONE"
             reward = float(returns[i]) if i < len(returns) else 0.0 # Assign final rewards
        elif i == next_player: status = "ACTIVE"; reward = env.specification.reward.default
        else: status = "INACTIVE"; reward = env.specification.reward.default # Game continues, not this player's turn

        # Prepare info dict, storing the action applied by this agent (if any)
        info_dict = {}
        submitted_action = applied_actions[i]
        if submitted_action is not None:
            info_dict["submitted_action"] = submitted_action
        # Create observation dictionary, ensuring keys match the schema defined above
        obs_dict = {
            "openSpielGameName": game_name, # Fetched from runtime config
            "raw_observation_string": "Error: Could not generate string.",
            "observation_tensor": [],
            "legal_actions": [],
            "current_player": int(next_player),
            "is_terminal": is_terminal,
            "player_id": i,
            # These values come from the parent state managed by core.py
            "remainingOverageTime": state[i].observation.get("remainingOverageTime", act_timeout_default * 2), # Example fallback for overage
            "step": len(env.steps) # Current step index
        }
        obs_dict["raw_observation_string"] = os_state_after.to_string()
        # TODO
        # obs_dict["observation_tensor"] = [float(x) for x in os_state_after.observation_tensor(i)]
        if status == "ACTIVE":
             try:
                 if env.debug:
                     print(f"--- DEBUG INTERPRETER ({env.name}): P{i} ACTIVE. About to call legal_actions. State type: {type(os_state_after)}, IsTerminal: {os_state_after.is_terminal()}, CurrentPlayer: {os_state_after.current_player()}, IsChance: {os_state_after.is_chance_node()} ---")
                     print(f"--- State String:\n{os_state_after.to_string()}\n--- End State String ---")
                 if not os_state_after.is_chance_node():
                     legal_acts = os_state_after.legal_actions(i)
                     print(f"--- DEBUG INTERPRETER ({env.name}): P{i} legal_actions returned: {legal_acts} (Type: {type(legal_acts)}) ---")
                     obs_dict["legal_actions"] = legal_acts
                     # --- ADDED DEBUG: Value in obs_dict *after* assignment ---
                     if env.debug: print(f"--- DEBUG INTERPRETER ({env.name}): P{i} obs_dict['legal_actions'] set to: {obs_dict['legal_actions']} ---")
             except Exception as e_legal:
                 print(f"--- WARNING interpreter ({env.name}): Exception getting legal_actions for P{i} (Status: {status}): {type(e_legal).__name__}: {e_legal} ---")
                 if env.debug: print(f"--- DEBUG INTERPRETER ({env.name}): P{i} obs_dict['legal_actions'] remains default [] due to exception. ---")
                 pass # Leave empty if error


        new_states.append({"reward": reward, "info": info_dict, "observation": obs_dict, "status": status})

    # --- DEBUG PRINT ---
    # Check if this is the interpreter call happening *during* the initial reset sequence.
    # At this point, core.py has already created a default step 0, so len(env.steps) == 1.
    is_initial_reset_call = (len(env.steps) == 1)
    if is_initial_reset_call and env.debug:
        print(f"--- DEBUG INTERPRETER (Reset): Returning new_states ---")
        for idx, ns in enumerate(new_states): print(f"  Agent {idx}: Status={ns['status']}, Obs.player_id={ns['observation'].get('player_id')}, Obs.current_player={ns['observation'].get('current_player')}, Obs.legal_actions={ns['observation'].get('legal_actions')}")
    # --- END DEBUG PRINT ---
    return new_states

def renderer(state_history_entry, env):
    """Kaggle renderer function."""
    if (state_history_entry and len(state_history_entry)>0 and hasattr(state_history_entry[0],"observation") and
        state_history_entry[0].observation is not None and isinstance(state_history_entry[0].observation,dict) and
        "raw_observation_string" in state_history_entry[0].observation):
        board=state_history_entry[0].observation["raw_observation_string"]; return board if board is not None else "Obs string None"
    else: print(f"--- WARNING renderer ({env.name}): Obs missing/malformed. Rendering initial. ---");
    try: return _get_open_spiel_game(env.configuration).new_initial_state().to_string()
    except Exception as e: print(f"--- ERROR renderer ({env.name}): Fallback failed: {e} ---"); return f"Error rendering {env.name}"

def html_renderer():
    """Provides the HTML/JS for the interactive replay viewer."""
    # Adjust JS to get game name from runtime config if possible
    return """<script> function renderer(context){const{parent,environment,step}=context;parent.innerHTML='';const d=document.createElement("div");d.style.fontFamily="monospace";d.style.whiteSpace="pre";d.style.lineHeight="1.2";d.style.padding="10px";d.style.border="1px solid #ccc";d.style.backgroundColor="#f9f9f9";d.style.maxWidth="800px";let t='OpenSpiel Game',g='Unknown',s='N/A';if(environment&&environment.specification){t=environment.specification.title||t;const a=environment.specification.agents;s=Array.isArray(a)?a.join(', '):'N/A';if(environment.configuration&&environment.configuration.openSpielGameName){g=environment.configuration.openSpielGameName}}let n="Waiting for state...",i=`Step: ${step}`,r=[],l="Initial State";if(environment&&environment.steps&&step>0&&environment.steps[step-1]){const p=environment.steps[step-1].map((e,a)=>`P${a}: ${e.action!==undefined?e.action:'?'}`);p.length>0&&(l=`Actions leading to this state: ${p.join('; ')}`)}if(environment&&environment.steps&&environment.steps[step]){const c=environment.steps[step];c[0]&&c[0].observation&&c[0].observation.raw_observation_string!==undefined?n=String(c[0].observation.raw_observation_string||'').replace(/&/g,'&').replace(/</g,'<').replace(/>/g,'>').replace(/\\n/g,'<br>'):n="State data not available in observation.";c.forEach((e,a)=>{let o=e.status||'UNKNOWN',u=e.reward===null?'null':e.reward!==undefined?e.reward.toFixed(2):'N/A';r.push(`P${a}: ${o} (Rwd: ${u})`)});i+=` (${r.join(', ')})`}else step===0&&(n="Initial state");d.innerHTML=`<h3 style="margin-top:0; margin-bottom:5px;">${t}</h3><p style="font-size:.9em; color:#555; margin-top:0; margin-bottom:10px;">Game: ${g} | Agents in Spec: ${s}</p><p style="margin-bottom:5px;">${i}</p><p style="font-size:.8em; color:#777; margin-top:0; margin-bottom:10px;">${l}</p><div style="margin-top:10px; border-top:1px solid #eee; padding-top:10px;"><b>Game State:</b></div><div style="background-color:#fff; border:1px solid #eee; padding:5px; margin-top:5px; max-height:400px; overflow-y:auto;">${n}</div>`;parent.appendChild(d)}</script>"""


# --- Dynamic Environment Generation ---
registered_spiel_envs = {}
try:
    print(f"--- Generating OpenSpiel environment specifications dynamically ---")
    all_registered_games = pyspiel.registered_games()
    print(f"--- Found {len(all_registered_games)} registered game types. Loading defaults... ---")
    successful_loads = 0; skipped_loads = 0
    for game_info in all_registered_games:
        short_name = game_info.short_name; long_name = game_info.long_name
        if not short_name: skipped_loads += 1; continue
        try:
            loaded_game = pyspiel.load_game(short_name); num_players = loaded_game.num_players(); max_len = loaded_game.max_game_length()
            if num_players <= 0: print(f"  Skipping '{short_name}': num_players={num_players}."); skipped_loads += 1; continue

            # Use the template with detailed observation properties WORKAROUND
            game_spec = copy.deepcopy(BASE_SPEC_TEMPLATE)
            env_name = f"open_spiel_{short_name.replace('-', '_').replace('.', '_')}"

            # Populate ONLY the fields defined in the minimal template
            game_spec["name"] = env_name; game_spec["title"] = f"OpenSpiel: {long_name}"
            desc_range = f"{game_info.min_num_players}" + (f"-{game_info.max_num_players}" if game_info.min_num_players != game_info.max_num_players else "")
            game_spec["description"] = f"Kaggle env for OpenSpiel: {long_name} ({short_name}). Requires {num_players}. Supports: {desc_range}."
            game_spec["agents"] = [num_players]

            # Set configuration defaults
            if 0 < max_len < MAX_LEN_THRESHOLD: episode_steps = max_len
            else: episode_steps = DEFAULT_EPISODE_STEPS
            game_spec["configuration"]["episodeSteps"]["default"] = episode_steps
            game_spec["configuration"]["openSpielGameName"]["default"] = short_name

            # Set observation default (can still be useful for generic agents)
            game_spec["observation"]["properties"]["openSpielGameName"]["default"] = short_name
            # NO default set for observation['openSpielGameName'] here - will be set by interpreter

            registered_spiel_envs[env_name] = {
                "specification": game_spec, # Pass the spec with the obs workaround
                "interpreter": interpreter,
                "renderer": renderer,
                "html_renderer": html_renderer,
            }
            successful_loads += 1
        except pyspiel.SpielError as e: print(f"--- INFO Skipping '{short_name}': Load failed (needs config?). Error: {e} ---"); skipped_loads += 1; continue
        except Exception as e: print(f"--- WARNING Skipping '{short_name}': Unexpected error: {type(e).__name__}: {e} ---"); skipped_loads += 1; continue
except ImportError as e:
     if 'pyspiel' in str(e): print(f"--- CRITICAL ERROR: pyspiel import failed. {e} ---")
     else: print(f"--- !!! ERROR during generation (Import): {e} !!! ---")
     registered_spiel_envs = {}
except Exception as e: print(f"--- !!! UNEXPECTED TOP-LEVEL ERROR during generation: {type(e).__name__}: {e} !!! ---")
print(f"--- Finished dynamic generation. Prepared specs for {successful_loads} games. Skipped {skipped_loads} games. ---")
print(f"--- Final count of OpenSpiel environments prepared for registration: {len(registered_spiel_envs)} ---")
# --- END of open_spiel.py ---