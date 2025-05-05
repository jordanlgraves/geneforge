# src/rl/experiments/minimal_ppo.py
import os
import gymnasium as gym
from stable_baselines3 import PPO
from src.rl.envs.gene_circuit_env import GeneCircuitEnv
from src.rl.reward_evaluator import RewardEvaluator

prompt = "Design a NOT gate circuit for E. coli using one sensor."

env = GeneCircuitEnv(prompt, max_steps=5,
                     reward_evaluator=RewardEvaluator(scenario=None, step_penalty=0.01))

model = PPO("MlpPolicy", env, n_steps=32, batch_size=32, verbose=1)
model.learn(total_timesteps=128)