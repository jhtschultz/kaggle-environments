# kaggle_environments/__init__.py
# Copyright 2020 Kaggle Inc (and modifications for OpenSpiel integration)

from importlib import import_module
from os import path
from .agent import Agent
from .api import get_episode_replay, list_episodes, list_episodes_for_team, list_episodes_for_submission
from .core import environments, evaluate, make, register
from .main import http_request
from . import errors
from . import utils

__version__ = "1.16.11" # Update if needed

__all__ = ["Agent", "environments", "errors", "evaluate", "http_request",
           "make", "register", "utils", "__version__",
           "get_episode_replay", "list_episodes", "list_episodes_for_team", "list_episodes_for_submission"]

# --- Environment Registration Logic ---

CORE_IMPORT_ENVS = [
    "connectx",
    "open_spiel",
    "tictactoe",
]

def _register_env_details(env_name, details_dict):
     """Registers an environment using a dictionary of its details. Returns True on success."""
     if not all(k in details_dict for k in ["specification", "interpreter", "renderer"]) or \
        not all(details_dict.get(k) for k in ["specification", "interpreter", "renderer"]):
         print(f"--- WARNING Skipping registration for '{env_name}': Missing or empty required values (specification, interpreter, renderer). ---")
         return False
     try:
         # The dictionary passed to register NO LONGER includes the top-level 'agents' key.
         # The agent count info is inside details_dict["specification"]["agents"]
         register(env_name, {
             "html_renderer": details_dict.get("html_renderer"), # Optional
             "interpreter": details_dict.get("interpreter"),
             "renderer": details_dict.get("renderer"),
             "specification": details_dict.get("specification"),
         })
         return True
     except Exception as e:
         print(f"--- ERROR calling kaggle_environments.register() for '{env_name}': {type(e).__name__}: {e} ---")
         return False

# --- Main Initialization ---
print(f"--- Initializing Kaggle Environments (Version: {__version__}) ---")

_already_registered = set()
print(f"--- Attempting to load and register specified environments: {CORE_IMPORT_ENVS} ---")

for name in CORE_IMPORT_ENVS:
    if name in _already_registered and name != "open_spiel":
        continue

    env_module_path = f".envs.{name}.{name}"
    print(f"--- Processing: {name} (from module {env_module_path}) ---")

    # *** Special Handling for OpenSpiel ***
    if name == "open_spiel":
        try:
            os_module = import_module(env_module_path, __name__)

            if hasattr(os_module, "registered_spiel_envs") and isinstance(os_module.registered_spiel_envs, dict):
                num_found = len(os_module.registered_spiel_envs)
                print(f"--- Found 'registered_spiel_envs' dict with {num_found} entries in {env_module_path}.py ---")
                if num_found == 0:
                     print(f"--- WARNING: os_module.registered_spiel_envs is empty. No OpenSpiel games were successfully processed. ---")

                registered_count = 0
                for env_name, env_details in os_module.registered_spiel_envs.items():
                    if env_name in _already_registered:
                        print(f"--- Skipping already registered env: {env_name} ---")
                        continue
                    if _register_env_details(env_name, env_details):
                         _already_registered.add(env_name)
                         registered_count += 1

                print(f"--- Successfully registered {registered_count} / {num_found} prepared OpenSpiel environments. ---")
            else:
                 print(f"--- ERROR: Imported '{env_module_path}' does not have 'registered_spiel_envs' dictionary. Cannot register OpenSpiel games. ---")

        except ModuleNotFoundError:
             print(f"--- ERROR: Could not find module for '{name}': {env_module_path}. ---")
        except ImportError as e:
             print(f"--- ERROR: Failed to import '{env_module_path}' (check dependencies like pyspiel): {e} ---")
        except Exception as e:
            print(f"--- ERROR loading or processing the '{name}' module '{env_module_path}': {type(e).__name__}: {e} ---")

    # *** Standard Handling for other environments in the list ***
    else:
        try:
            env = import_module(env_module_path, __name__)
            # Pass the details extracted from the standard env module
            if _register_env_details(name, {
                "specification": getattr(env, "specification", None),
                "interpreter": getattr(env, "interpreter", None),
                "renderer": getattr(env, "renderer", None),
                "html_renderer": getattr(env, "html_renderer", None),
            }):
                _already_registered.add(name)
            # else: Error message already printed by helper

        except ModuleNotFoundError:
             print(f"--- WARNING: Environment listed in CORE_IMPORT_ENVS not found or module missing: {name} ({env_module_path}) ---")
        except Exception as e:
            print(f"--- ERROR loading/registering environment '{name}': {type(e).__name__}: {e} ---")

# --- Final Summary ---
print(f"--- Kaggle Environments initialization complete. ---")
print(f"--- Total registered environments: {len(_already_registered)} ---")
# print(f"--- Registered: {sorted(list(_already_registered))} ---") # Optional: Uncomment for full list

# --- END __init__.py ---