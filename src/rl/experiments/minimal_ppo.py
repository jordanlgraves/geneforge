# src/rl/experiments/minimal_ppo.py
import os
import gymnasium as gym
from stable_baselines3 import PPO
from src.rl.envs.gene_circuit_env import GeneCircuitMacroEnv
from src.rl.reward_evaluator import RewardEvaluator
import random
import numpy as np
import torch
from stable_baselines3.common.logger import configure
from pathlib import Path
import dotenv
import datetime
run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

prompt = "Design a NOT gate circuit for E. coli using one sensor."

# ------------------------------
# Configuration / Reproducibility
# ------------------------------
dotenv.load_dotenv()

SEED = int(os.getenv("PPO_SEED", "42"))
SAVE_DIR = Path(os.getenv("PPO_SAVE_DIR", "outputs/rl_models"))
LOG_DIR = Path(os.getenv("PPO_LOG_DIR", "outputs/rl_logs"))

SAVE_DIR = SAVE_DIR / run_id
LOG_DIR = LOG_DIR / run_id

SAVE_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Set global seeds for reproducibility
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

# ------------------------------
# Environment setup
# ------------------------------
env = GeneCircuitMacroEnv(
    prompt, 
    max_steps=5,
    reward_evaluator=RewardEvaluator(
        scenario=None, 
        step_penalty=0.01,
        success_bonus=1.0
    ),
    # Reward shaping parameters
    shaping=True,
    lib_bonus=0.3,      # Increased from 0.2
    verilog_bonus=0.4,  # Increased from 0.3
    cello_bonus=0.8,    # Increased from 0.7
    repeat_penalty=0.05
)

# Seed the internal RNGs of the environment + action space
env.reset(seed=SEED)
env.action_space.seed(SEED)

# ------------------------------
# Logger configuration
# ------------------------------
output_formats = ["stdout", "tensorboard", "csv"]
new_logger = configure(LOG_DIR.as_posix(), output_formats)

def train():
    # ------------------------------
    # Model training
    # ------------------------------
    model = PPO(
        "MlpPolicy", 
        env,
        n_steps=64,           # Increased from 32
        batch_size=32,
        n_epochs=10,          # Added epochs
        learning_rate=3e-4,   # Increased learning rate
        ent_coef=0.01,       # Added entropy coefficient
        verbose=1, 
        seed=SEED, 
        tensorboard_log=LOG_DIR.as_posix()
    )
    model.set_logger(new_logger)
    model.learn(total_timesteps=2000)  # Increased from 1000

    # ------------------------------
    # Save trained model
    # ------------------------------
    model_path = SAVE_DIR / "ppo_gene_circuit"
    model.save(model_path)
    print(f"Model saved to {model_path}")

    # ------------------------------
    # Basic evaluation
    # ------------------------------
    evaluate_policy(model, env, n_episodes=10)
    
    return model

def evaluate_policy(model, env, n_episodes: int = 10, seed: int = SEED, out_dir: Path = None):
    """Run deterministic episodes and report average reward."""
    rewards = []
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

        with open(out_dir / "eval_logs.txt", "w") as f:
            f.write(f"Evaluating policy for {n_episodes} episodes\n")

    for ep in range(n_episodes):
        obs, _ = env.reset(seed=seed + ep)  # vary seed every episode
        done = False
        total_reward = 0.0
        action_log = []
        obs_log = []
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, _ = env.step(action)
            done = terminated or truncated
            total_reward += reward
            action_log.append(action)
            obs_log.append(obs)

        rewards.append(total_reward)

        if out_dir:
            with open(out_dir / "eval_logs.txt", "a") as f:
                f.write(f"Episode {ep+1} reward: {total_reward:.3f}\n")
                f.write(f"Action log: {action_log}\n")
                f.write(f"Observation log: {obs_log}\n")
                f.write(f"Done: {done}\n")
                f.write(f"Terminated: {terminated}\n")
                f.write(f"Truncated: {truncated}\n")
                f.write(f"Reward: {reward}\n")
                f.write(f"Total reward: {total_reward}\n")
                f.write(f"--------------------------------\n")
                
    avg_reward = float(np.mean(rewards))
    return avg_reward

def load_model(model_path: Path):
    model = PPO.load(model_path)
    return model

if __name__ == "__main__":
    # Run evaluation
    model_id = None
    # model_id = '20250510_053316'
    model = train()
    model = load_model(Path(f'outputs/rl_models/{model_id}/ppo_gene_circuit.zip'))
    evaluate_policy(model, env, n_episodes=10, out_dir=Path(f'outputs/rl_logs/{model_id}/'))