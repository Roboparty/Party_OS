<p align="center">
  <b>English</b> · <a href="mimiclite-vs-partymimic_zh.md">简体中文</a> · <a href="../README.md">← Back to Party OS</a>
</p>

# 🎯 MimicLite vs ⚡ PartyMimic

Both are general motion trackers in the Party OS motion control layer. They solve the same problem with different learning paradigms, and are meant to be used together: **MimicLite is the deployment baseline, PartyMimic is the fast-iteration engine.**

| | 🎯 [MimicLite](https://github.com/Roboparty/MimicLite) | ⚡ [PartyMimic](https://github.com/Roboparty/PartyMimic) |
|---|---|---|
| 🧠 Learning paradigm | **Model-free RL**: PPO, plus PPO-ROA teacher–student adaptation (Train → Adapt → Finetune) | **Model-based** (SuperMimic family): an online MLP world model; the policy is trained by backpropagating through 32 imagined steps, with a critic beyond the horizon |
| 🔥 Training compute | 8 × 8,192 parallel environments; about 50 GPU-hours for the G1 v1.1 entry | A single RTX 4090 (22 GB peak), **7–30 minutes**; optional two-GPU pipeline |
| 📏 Held-out error, G1 Loc/Man ¹ | 26.7 mm | **23.6 mm** (12k iterations) |
| ⏱️ Reference lookahead | **0.08 s** | 0.20 s (10 future frames at 50 Hz) |
| 🤖 Robots | Released checkpoints for G1, H2, A3, RP1 (28 / 24 DoF) | G1, RP1 (28 DoF) |
| 🧪 Simulation | [active-adaptation](https://github.com/Agent-3154/active-adaptation) training framework | [mjlab](https://github.com/mujocolab/mjlab) + MuJoCo Warp |
| ✅ Validation | Physical G1: Pico teleoperation and highly dynamic motion tracking | Sim2sim on the [sim2real leaderboard](https://egalahad.github.io/sim2real/leaderboard/) protocol; exports ONNX + deploy YAML for the same runtime |
| 🛠️ Use it for | Real-robot deployment, low-latency teleoperation | New robots, new data, reward / interface / constraint experiments in minutes |

¹ Body position error on the held-out MotionDecode splits, scored by the sim2real leaderboard sim2sim evaluator. The MimicLite number is its official leaderboard entry, trained with different data and hardware; see the [PartyMimic README](https://github.com/Roboparty/PartyMimic#results-on-held-out-motions) for the full protocol.
