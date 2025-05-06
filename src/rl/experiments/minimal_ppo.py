# src/rl/experiments/minimal_ppo.py
import os
import gymnasium as gym
from stable_baselines3 import PPO
from src.rl.envs.gene_circuit_env import GeneCircuitEnv
from src.rl.reward_evaluator import RewardEvaluator
import random
import numpy as np
import torch
from stable_baselines3.common.logger import configure
from pathlib import Path
import dotenv

prompt = "Design a NOT gate circuit for E. coli using one sensor."

# ------------------------------
# Configuration / Reproducibility
# ------------------------------
dotenv.load_dotenv()

SEED = int(os.getenv("PPO_SEED", "42"))
SAVE_DIR = Path(os.getenv("PPO_SAVE_DIR", "outputs/rl_models"))
LOG_DIR = Path(os.getenv("PPO_LOG_DIR", "outputs/rl_logs"))
SAVE_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Set global seeds for reproducibility
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

# ------------------------------
# Environment setup
# ------------------------------
env = GeneCircuitEnv(prompt, max_steps=5,
                     reward_evaluator=RewardEvaluator(scenario=None, step_penalty=0.01))
# Seed the internal RNGs of the environment + action space
env.reset(seed=SEED)
env.action_space.seed(SEED)

# ------------------------------
# Logger configuration (SB3 -> stdout)
# ------------------------------
new_logger = configure(LOG_DIR.as_posix(), ["stdout"])

# ------------------------------
# Model training
# ------------------------------
model = PPO("MlpPolicy", env, n_steps=32, batch_size=32, verbose=1, seed=SEED, tensorboard_log=LOG_DIR.as_posix())
model.set_logger(new_logger)
model.learn(total_timesteps=128)

# ------------------------------
# Save trained model
# ------------------------------
model_path = SAVE_DIR / "ppo_gene_circuit"
model.save(model_path)
print(f"Model saved to {model_path}")

# ------------------------------
# Basic evaluation
# ------------------------------

def evaluate_policy(model, env, n_episodes: int = 10, seed: int = SEED):
    """Run deterministic episodes and report average reward."""
    rewards = []
    for ep in range(n_episodes):
        obs, _ = env.reset(seed=seed + ep)  # vary seed every episode
        done = False
        total_reward = 0.0
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, _ = env.step(action)
            done = terminated or truncated
            total_reward += reward
        rewards.append(total_reward)
    avg_reward = float(np.mean(rewards))
    print(f"Average reward over {n_episodes} episodes: {avg_reward:.3f}")
    return avg_reward

# Run evaluation
evaluate_policy(model, env, n_episodes=10)