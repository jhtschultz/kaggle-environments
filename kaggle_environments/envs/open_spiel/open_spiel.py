# envs/open_spiel/open_spiel.py
# Copyright 2025 Kaggle Inc
# (Your license header)

import json
import os
import copy
import random
import sys
from typing import Any
import numpy as np
import pyspiel

DEFAULT_ACT_TIMEOUT = 5.0  # Keep for interpreter fallback
MAX_LEN_THRESHOLD = 5000  # Used for description only
DEFAULT_EPISODE_STEPS = 1000  # Fallback max steps if game max_len is 0 or very large

BASE_SPEC_TEMPLATE = {
    "name": "PLACEHOLDER_NAME",
    "title": "PLACEHOLDER_TITLE",
    "description": "PLACEHOLDER_DESCRIPTION",
    "version": "0.1.0",
    "agents": ["PLACEHOLDER_AGENTS"],  # Required agent count list, e.g., [2]

    # --- Add back configuration schema definition ---
    "configuration": {
        "episodeSteps": {
            "description":
                "Maximum number of steps (actions taken) in an episode.",
            "type":
                "integer",
            "default":
                "PLACEHOLDER_EPISODE_STEPS"  # Dynamically set during generation
        },
        "actTimeout": {
            "description":
                "Maximum runtime (seconds) to obtain an action from an agent.",
            "type":
                "number",
            "default":
                DEFAULT_ACT_TIMEOUT
        },
        "runTimeout":
            {  # Add runTimeout for completeness, using a reasonable default
                "description":
                    "Maximum runtime (seconds) for the entire episode.",
                "type":
                    "number",
                "default":
                    1200.0
            },
        "openSpielGameName": {
            "description":
                "The short_name of the OpenSpiel game to load. This is fixed for this environment.",
            "type":
                "string",
            "default":
                "PLACEHOLDER_GAME_SHORT_NAME"  # Set during generation
        },
        # NOTE: openSpielGameSettings is intentionally omitted here. It's meant to be a runtime override.
    },
    "observation": {
        "properties": {
            # Game/Wrapper specific observation fields
            "openSpielGameName": {
                "description": "Short name of the OpenSpiel game.",
                "type": "string"
            },
            "raw_observation_string": {
                "description": "String representation of state.",
                "type": "string"
            },
            "observation_tensor": {
                "description": "Flattened state tensor for agent.",
                "type": "array",
                "items": {
                    "type": "number"
                }
            },
            "legal_actions": {
                "description": "List of legal action IDs.",
                "type": "array",
                "items": {
                    "type": "integer"
                }
            },
            "chance_outcome_probs": {
                "description": "List of probabilities for chance outcomes.",
                "type": "array",
                "items": {
                    "type": "float"
                }
            },
            "current_player": {
                "description": "ID of player whose turn it is.",
                "type": "integer"
            },
            "is_terminal": {
                "description": "Boolean indicating game end.",
                "type": "boolean"
            },
            "player_id": {
                "description": "ID of the agent receiving this observation.",
                "type": "integer"
            },
            "remainingOverageTime": {
                "description":
                    "Total remaining banked time (seconds) that can be used in excess of per-step actTimeouts -- agent is disqualified with TIMEOUT status when this drops below 0.",
                "shared":
                    False,
                "type":
                    "number",
                "minimum":
                    0,
                # "default": 12 # Let core.py handle applying the default value
            },
            "step": {
                "description": "Current step within the episode.",
                "type": "integer",
                "shared": True,
                "minimum": 0,
                # "default": 0 # Let core.py handle applying the default value
            }
        },
        "default": {}
    },
    "action": {
        "type": ["integer", "null"],  # Allow null for errors/timeouts
        "minimum": -1,
        "default": -1
    },
    "reward": {
        "type": ["number", "null"],  # Allow null for errors/timeouts
        "default": 0.0
    },
}

_OS_GLOBAL_STATE = None
_OS_GLOBAL_RNG = None
_OS_GAME_CACHE = {}


def _get_open_spiel_game(env_config: dict) -> pyspiel.Game:
  game_name = env_config.get("openSpielGameName")
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
    print(
        f"*** ERROR (_get_open_spiel_game): Failed loading '{game_name}': {e} ***"
    )
    raise


def _reconstruct_os_state(
    game: pyspiel.Game,
    kaggle_history: list,
    num_expected_agents: int,
) -> pyspiel.State:
  os_state = game.new_initial_state()
  for i, kaggle_state in enumerate(kaggle_history):
    if i == 0:
      continue  # kaggle_history[0] is the initial dummy state from core.py
    os_current_player = os_state.current_player()
    kaggle_current_player = (
      os_current_player
      if os_current_player != pyspiel.PlayerId.CHANCE
      else game.num_players()
    )
    if 0 <= kaggle_current_player < num_expected_agents:
      action = kaggle_state[kaggle_current_player].info.get("submitted_action")
      if action is not None:
        legal_actions = list(os_state.legal_actions())
        if action in legal_actions:
          os_state.apply_action(action)
        else:
          raise ValueError(
              f"_reconstruct_os_state failed to find action {action} "
              f"in legal actions: {legal_actions}"
          )
      else:
        raise ValueError(
            "_reconstruct_os_state found None action for "
            f"current player {os_current_player} in state: {os_state}"
        )
    elif os_current_player == pyspiel.PlayerId.SIMULTANEOUS:
      raise NotImplementedError
    elif os_current_player == pyspiel.PlayerId.TERMINAL:
      continue
    else:
      raise ValueError(f"Invalid player: {os_current_player}")
  return os_state


def interpreter(state, env):
  """Kaggle interpreter function using global state and a chance agent."""
  global _OS_GLOBAL_STATE, _OS_GLOBAL_RNG
  kaggle_state = state

  # TODO
  if env.done:
    return state

  # --- Get Game Info ---
  game_name = env.configuration.get("openSpielGameName")
  game = _get_open_spiel_game(env.configuration)
  num_players = game.num_players()  # Actual number of players
  num_agents = len(kaggle_state)
  if num_agents != num_players + 1:
    raise ValueError(
        f"Invalid num_agents: {num_agents}. Open Spiel must always include a game runner."
    )

  statuses = [
      kaggle_state[os_current_player].status
      for os_current_player in range(num_agents)
  ]
  if not any(status == "ACTIVE" for status in statuses):
    raise ValueError("No active agents.")

  # --- Initialization / Reset ---
  is_initial_step = len(env.steps) == 1
  # Reset if global state is missing OR it's not step 1 and core.py indicates env is done
  if _OS_GLOBAL_STATE is None or (not is_initial_step and env.done):
    print(
        f"--- INTERPRETER: Initializing/Resetting Global State (Steps len: {len(env.steps)}, env.done: {env.done}) ---"
    )
    _OS_GLOBAL_STATE = game.new_initial_state()

  # --- Main Step Processing ---
  os_state = _OS_GLOBAL_STATE
  # os_state = _reconstruct_os_state(game, env.steps, num_agents)
  os_current_player = os_state.current_player()
  kaggle_current_player = os_current_player if os_current_player != -1 else num_players

  submitted_player_action = None
  if 0 <= kaggle_current_player < num_agents:
    # --- Player Node Resolution ---
    print(
        f"--- DEBUG INTERPRETER (Step {len(env.steps)}): Player {os_current_player} Node ---"
    )
    action_submitted = kaggle_state[kaggle_current_player].action
    agent_status = kaggle_state[kaggle_current_player].status
    # Only process action if agent is ACTIVE (core.py handles TIMEOUT/ERROR status)
    if agent_status == "ACTIVE" and not is_initial_step:
      if action_submitted is not None:
        legal = os_state.legal_actions()
        if action_submitted in legal:
          try:
            os_state.apply_action(action_submitted)
            submitted_player_action = int(action_submitted)
            print(
                f"--- DEBUG INTERPRETER: Applied P{os_current_player} action {submitted_player_action} ---"
            )
          except Exception as e:
            print(
                f"*** ERROR INTERPRETER: apply_action failed for P{os_current_player} action {action_submitted}: {e} ***"
            )
            kaggle_state[os_current_player].status = "ERROR"
        else:
          print(
              f"--- INFO INTERPRETER: P{os_current_player} submitted INVALID action {action_submitted}. Legal: {legal} ---"
          )
          kaggle_state[os_current_player].status = "INVALID"
      else:
        # Agent returned None but status was ACTIVE
        # Check if None is allowed by spec ["integer", "null"]?
        action_spec_type = env.specification.action.get("type", ["integer"])
        is_null_allowed = "null" in action_spec_type or "None" in action_spec_type
        if not is_null_allowed:
          print(
              f"--- INFO INTERPRETER: P{os_current_player} returned None action (treated as INVALID) ---"
          )
          kaggle_state[os_current_player].status = "INVALID"
        # else: None is allowed, state remains unchanged.

    # If agent had TIMEOUT/ERROR/INVALID status, we don't apply action, state remains unchanged.
    # core.py will preserve the status.

  elif os_current_player == pyspiel.PlayerId.SIMULTANEOUS:
    raise NotImplementedError
  elif os_current_player == pyspiel.PlayerId.TERMINAL:
    print(f"--- DEBUG INTERPRETER (Step {len(env.steps)}): Terminal Node ---")
    pass
  else:
    raise ValueError(
        f"INTERPRETER: Unknown OpenSpiel player ID: {os_current_player}")

  # Update Global State
  _OS_GLOBAL_STATE = os_state

  # --- Determine Next State Info for Kaggle ---
  is_terminal = _OS_GLOBAL_STATE.is_terminal()
  # TODO this needs to match # players + 1
  # TODO rewards vs returns?
  returns = _OS_GLOBAL_STATE.returns() if is_terminal else [0.0] * num_players
  # TODO str(state)?
  os_state_str = _OS_GLOBAL_STATE.to_string()

  if is_terminal:
    os_next_player = pyspiel.PlayerId.TERMINAL
  elif _OS_GLOBAL_STATE.is_chance_node():
    os_next_player = pyspiel.PlayerId.CHANCE
  else:
    os_next_player = _OS_GLOBAL_STATE.current_player()

  # TODO
  kaggle_next_player = os_next_player if os_next_player != -1 else num_players

  # --- Generate Kaggle States (N Players + 1 Chance Agent) ---
  new_states = []
  act_timeout_default = env.configuration.get("actTimeout", DEFAULT_ACT_TIMEOUT)

  for i in range(0, num_agents):
    input_status = kaggle_state[i].status
    status = ""
    reward = None

    if input_status in ["TIMEOUT", "ERROR", "INVALID"]:
      status = input_status
      reward = None  # Handled by core.py mostly, but ensure no reward
    elif is_terminal:
      status = "DONE"
      reward = float(returns[i]) if i < len(returns) else 0.0
    elif kaggle_next_player == i:
      status = "ACTIVE"
      reward = env.specification.reward.default  # TODO
    else:
      status = "INACTIVE"
      reward = env.specification.reward.default  # TODO

    info_dict = {}
    # Store the successfully applied action in info for potential debugging/analysis
    # Check if the current player WAS player 'i' and their action was applied
    if kaggle_current_player == i and submitted_player_action is not None:
      info_dict["submitted_action"] = submitted_player_action

    legal_actions = []
    chance_outcome_probs = []
    if i == num_agents - 1:  # Game master agent
      obs_str = str(_OS_GLOBAL_STATE)
      if _OS_GLOBAL_STATE.is_chance_node():
        outcomes = _OS_GLOBAL_STATE.chance_outcomes()
        legal_actions, chance_outcome_probs = zip(*outcomes)
    else:
      obs_str = _OS_GLOBAL_STATE.observation_string(i)
      legal_actions = _OS_GLOBAL_STATE.legal_actions(i)

    if status == "ACTIVE" and not legal_actions:
      raise ValueError(
        f"Active agent {i} has no legal actions in state {_OS_GLOBAL_STATE}."
      )

    obs_dict = {
        "openSpielGameName": game_name,
        "raw_observation_string": obs_str,
        "observation_tensor": [],  # TODO
        "legal_actions": legal_actions,
        "chance_outcome_probs": chance_outcome_probs,
        "current_player": int(os_next_player),
        "is_terminal": is_terminal,
        "player_id": i,
        "remainingOverageTime":
            (kaggle_state[i].observation.get("remainingOverageTime",
                                             act_timeout_default * 2)),
        "step": len(env.steps)
    }


    new_states.append({
        "reward": reward,
        "info": info_dict,
        "observation": obs_dict,
        "status": status,
        "action": None
    })

  if env.debug:
    print(
        f"--- DEBUG INTERPRETER END STEP {len(env.steps)}: Returning new_states ---"
    )
    for idx, ns in enumerate(new_states):
      print(
          f"  Agent {idx}: Status={ns['status']}, Reward={ns['reward']}, Action={ns['action']}, Info={ns['info']}"
      )

  return new_states


# TODO pull obs from chance player
def renderer(state_history_entry, env):
  """Kaggle renderer function."""
  if (
    state_history_entry and
    len(state_history_entry) > 0 and
    hasattr(state_history_entry[0], "observation") and
    state_history_entry[0].observation is not None and
    isinstance(state_history_entry[0].observation, dict) and
    "raw_observation_string" in state_history_entry[0].observation
  ):
    board = state_history_entry[0].observation["raw_observation_string"]
    return board if board is not None else "Obs string None"
  #else:
  #    print(f"--- WARNING renderer ({env.name}): Obs missing/malformed. Rendering initial. ---")
  try:
    os_game =  _get_open_spiel_game(env.configuration)
    return os_game.new_initial_state().to_string()
  except Exception as e:  # pylint: disable=broad-exception-caught
    print(f"--- ERROR renderer ({env.name}): Fallback failed: {e} ---")
    return f"Error rendering {env.name}"


def html_renderer():
  """Provides the simplest possible HTML/JS renderer for OpenSpiel text observations."""
  return """
function renderer(context) {
    const { parent, environment, step } = context;
    parent.innerHTML = ''; // Clear previous rendering

    // Get the current step's data
    const currentStepData = environment.steps[step];
    const numAgents = currentStepData.length
    const gameMasterIndex = numAgents - 1
    let obsString = "Observation not available for this step.";

    // Try to get the raw observation string from the game master agent.
    if (currentStepData && currentStepData[gameMasterIndex] && currentStepData[gameMasterIndex].observation && currentStepData[gameMasterIndex].observation.raw_observation_string !== undefined) {
        obsString = currentStepData[gameMasterIndex].observation.raw_observation_string;
    } else if (step === 0 && environment.steps[0] && environment.steps[0][gameMasterIndex] && environment.steps[0][gameMasterIndex].observation && environment.steps[0][gameMasterIndex].observation.raw_observation_string !== undefined) {
        // Fallback for initial state if current step data is missing
        obsString = environment.steps[0][gameMasterIndex].observation.raw_observation_string;
    }

    // Create a <pre> element to preserve formatting
    const pre = document.createElement("pre");
    pre.style.fontFamily = "monospace"; // Ensure monospace font
    pre.style.margin = "10px";        // Add some padding
    pre.style.border = "1px solid #ccc";
    pre.style.padding = "5px";
    pre.style.backgroundColor = "#f0f0f0";

    // Set the text content (safer than innerHTML for plain text)
    pre.textContent = `Step: ${step}\\n\\n${obsString}`; // Add step number for context

    parent.appendChild(pre);
}
"""


# --- Agents ---
def random_agent(
  observation: dict[str, Any],
  configuration: dict[str, Any],
) -> int:
  """A built-in random agent specifically for OpenSpiel environments."""
  del configuration
  legal_actions = observation.get("legal_actions")
  if not legal_actions:
    return None
  action = random.choice(legal_actions)
  return int(action)


def game_master_agent(
  observation: dict[str, Any],
  configuration: dict[str, Any],
) -> int:
  """Agent for handling chance nodes and recording full game state."""
  del configuration
  legal_actions = observation.get("legal_actions")
  chance_outcome_probs = observation.get("chance_outcome_probs")
  if not legal_actions:
    return None
  if not chance_outcome_probs:
    raise ValueError("Game master received legal actions without probs.")
  action = np.random.choice(legal_actions, p=chance_outcome_probs)
  return int(action)


agents = {
  "game_master": game_master_agent,
  "random": random_agent,
}

def _register_open_spiel_envs() -> dict[str, Any]:
  successfully_loaded_games = []
  skipped_games = []
  registered_envs = {}
  for game_info in pyspiel.registered_games():
    short_name = game_info.short_name
    long_name = game_info.long_name
    try:
      loaded_game = pyspiel.load_game(short_name)
      num_players = loaded_game.num_players()
      max_len = loaded_game.max_game_length() + 1000  # TODO
      game_spec = copy.deepcopy(BASE_SPEC_TEMPLATE)
      env_name = f"open_spiel_{short_name.replace('-', '_').replace('.', '_')}"

      # Populate ONLY the fields defined in the minimal template
      game_spec["name"] = env_name
      game_spec["title"] = f"OpenSpiel: {long_name}"
      desc_range = f"{game_info.min_num_players}" + (
          f"-{game_info.max_num_players}"
          if game_info.min_num_players != game_info.max_num_players else "")
      # TODO make template?
      game_spec["description"] = f"""
Kaggle env for OpenSpiel: {long_name} ({short_name}).
Requires {num_players}.
Supports: {desc_range}.
""".strip()

      # Handle chance nodes by adding agent.
      num_players_actual = loaded_game.num_players()
      num_agents_total = num_players_actual + 1
      game_spec["agents"] = [num_agents_total]
      game_spec["description"] = f"""
Kaggle env for OpenSpiel: {long_name} ({short_name}).
{num_players_actual} players + 1 chance agent.
Supports range: {desc_range} players.
""".strip()

      # Set configuration defaults
      # TODO
      if 0 < max_len < MAX_LEN_THRESHOLD:
        episode_steps = max_len
      else:
        episode_steps = DEFAULT_EPISODE_STEPS
      game_spec["configuration"]["episodeSteps"]["default"] = episode_steps
      game_spec["configuration"]["openSpielGameName"]["default"] = short_name
      # Set observation default (can still be useful for generic agents)
      game_spec["observation"]["properties"]["openSpielGameName"][
          "default"] = short_name

      registered_envs[env_name] = {
          "specification": game_spec,
          "interpreter": interpreter,
          "renderer": renderer,
          "html_renderer": html_renderer,
          "agents": agents,
      }
      successfully_loaded_games.append(short_name)

    except Exception:  # pylint: disable=broad-exception-caught
      skipped_games.append(short_name)
      continue

  print(f"""
Successfully loaded OpenSpiel environments: {len(successfully_loaded_games)}.
Skipped {len(skipped_games)} games.
""".strip())

  return registered_envs


registered_spiel_envs = _register_open_spiel_envs()
