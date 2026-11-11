<p align="center">
  <a href="mimiclite-vs-partymimic.md">English</a> · <b>简体中文</b> · <a href="../README_zh.md">← 返回 Party OS</a>
</p>

# 🎯 MimicLite 与 ⚡ PartyMimic

两者都是 Party OS 运控层的通用运动跟踪器，解决同一个问题，但学习范式不同，定位互补：**MimicLite 是部署基线，PartyMimic 是快速迭代的引擎。**

| | 🎯 [MimicLite](https://github.com/Roboparty/MimicLite) | ⚡ [PartyMimic](https://github.com/Roboparty/PartyMimic) |
|---|---|---|
| 🧠 学习范式 | **无模型强化学习**：PPO，加上 PPO-ROA 师生适应（Train → Adapt → Finetune） | **基于模型**（SuperMimic 系列）：在线学习一个 MLP 世界模型，策略通过 32 步想象展开反向传播训练，horizon 之外由 critic 接管 |
| 🔥 训练算力 | 8 × 8,192 个并行环境；G1 v1.1 约 50 GPU 小时 | 单张 RTX 4090（峰值 22 GB），**7–30 分钟**；可选双卡流水线 |
| 📏 Held-out 误差，G1 Loc/Man ¹ | 26.7 mm | **23.6 mm**（12k 迭代） |
| ⏱️ 参考前瞻 | **0.08 s** | 0.20 s（50 Hz 下未来 10 帧） |
| 🤖 支持机器人 | 已发布 G1、H2、A3、RP1（28 / 24 自由度）的 checkpoint | G1、RP1（28 自由度） |
| 🧪 仿真 | [active-adaptation](https://github.com/Agent-3154/active-adaptation) 训练框架 | [mjlab](https://github.com/mujocolab/mjlab) + MuJoCo Warp |
| ✅ 验证 | G1 真机：Pico 遥操作、高动态动作跟踪 | 按 [sim2real leaderboard](https://egalahad.github.io/sim2real/leaderboard/) 协议做 sim2sim；导出 ONNX 和部署 YAML，接入同一套部署运行时 |
| 🛠️ 适合做什么 | 真机部署、低延迟遥操作 | 新机器人、新数据，以及奖励、接口、约束等实验，几十分钟出结果 |

¹ 在 held-out 的 MotionDecode 划分上，用 sim2real leaderboard 的 sim2sim 评测器计算的身体位置误差。MimicLite 的数字是其官方 leaderboard 结果，训练数据和硬件与 PartyMimic 不同；完整协议见 [PartyMimic README](https://github.com/Roboparty/PartyMimic#results-on-held-out-motions)。
