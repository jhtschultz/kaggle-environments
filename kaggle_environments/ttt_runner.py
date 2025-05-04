from kaggle_environments import make
import kaggle_environments
import random

print(f"kaggle_environments loaded from: {kaggle_environments.__file__}")

# Basic agent which marks the first available cell.
def my_agent(obs):
  # Add a check for empty list to avoid errors on full boards
  available_cells = [c for c in range(len(obs.board)) if obs.board[c] == 0]
  # Simple strategy: take the first available cell
  action = available_cells[0] if available_cells else 0 
  # You could print the agent's decision here if needed:
  # print(f"    my_agent (Player 0) sees board {obs.board}, chooses action {action}")
  return action

# Setup a tictactoe environment.
# We keep debug=True for potential internal env logs, though it doesn't affect rendering directly
env = make("tictactoe", debug=True) 
print("Successfully built tictactoe environment.")

# --- Use env.train() ---
# Set up training for player 0 (my_agent) against the default "random" agent for player 1.
# 'None' indicates the agent we will provide actions for manually.
trainer = env.train([None, "random"]) 

# Get the initial observation for the agent being trained (player 0)
obs = trainer.reset() 

print("\nInitial Board State:")
print(env.render(mode="ansi")) # Print initial state using the main env object

# --- Manual Game Loop ---
done = False
step_count = 0
while not done:
    step_count += 1
    
    # Get action from our agent (player 0) based on its observation
    agent_action = my_agent(obs) 
    
    print(f"\n--- Step {step_count} ---")
    print(f"Player 0 ({my_agent.__name__}) takes action: {agent_action}")
    
    # trainer.step() takes player 0's action, runs it, 
    # then runs player 1's ("random") action, 
    # and returns the next observation for player 0.
    # It also updates the main 'env' state internally.
    obs, reward, done, info = trainer.step(agent_action) 
    
    # Render the board state AFTER the step (including opponent's move)
    print(env.render(mode="ansi")) 

    # Optional: Print reward and status for player 0
    if done:
        print(f"\nGame Over!")
        if reward == 1:
            print("Player 0 (my_agent) won!")
        elif reward == 0:
            print("Draw!")
        elif reward == -1: # Or possibly 0 for loser in TicTacToe depending on setup
             print("Player 0 (my_agent) lost!")
        else:
             print(f"Final reward for Player 0: {reward}")
        # You can access the final full state if needed
        # print("Final state detail:", env.state)

#from kaggle_environments import make
#import kaggle_environments
#import random
#
#print(f"kaggle_environments loaded from: {kaggle_environments.__file__}")
#
## Setup a tictactoe environment.
#env = make("tictactoe", debug=True)
#print("Successfully built tictactoe environment.")
#
## ---> RENDER 1 (Print the returned ANSI string) <---
#print("Initial Board State:")
#print(env.render(mode="ansi")) # Add print() here
#
## Basic agent which marks the first available cell.
#def my_agent(obs):
#  # Add a check for empty list to avoid errors on full boards
#  available_cells = [c for c in range(len(obs.board)) if obs.board[c] == 0]
#  return available_cells[0] if available_cells else 0 # Return 0 if no cells available (shouldn't happen if game logic is right)
#
#
## Run the basic agent against a default agent which chooses a "random" move.
#print("\nRunning game...")
#env.run([my_agent, "random"])
#print("Game finished.")
#
## ---> RENDER 2 (Print the returned ANSI string) <---
#print("\nFinal Board State:")
#print(env.render(mode="ansi")) # Add print() here