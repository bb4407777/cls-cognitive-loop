# CLS Cognitive Loop System — White Paper

> Author: Cognitive Workshop | Contact: QQ 1419456542 | zyc2018@mail.ustc.edu.cn
> First commit: 2026-05-25 | Version: 1.0 | June 2026

## Abstract
The Cognitive Loop System (CLS) is a harness-level architecture that transforms stochastic LLM outputs into a verifiable, self-improving pipeline through a 6-step cognitive cycle with dual-AI verification, independent circuit breakers, and cross-session persistence.

## 1. Architecture (4 Layers)
1. **Fuse Board** — 6 independent circuit breakers (stdlib-only, runs outside cognitive system)
2. **Cognitive Core Loop** — 6 mandatory steps per task (cardiac systole/diastole rhythm)
3. **Dual-AI Gate** — Generator/Evaluator separation with statistical guarantee
4. **Symbolic Dynamics** — Real-time audit compressing 50K tokens to 3 numbers + 1 word

## 2. Key Innovations
- **Generator/Evaluator Separation**: P(err) = P(gen) x P(eval), e.g. 0.1x0.1=1%
- **Circuit Breaker Safety**: 6 fuses run outside the protected system, pure stdlib
- **Cross-Window Coordination**: Multi-session state sharing prevents agent collisions
- **Fact Anchoring**: Every claim must reference file path + field value
- **Symbolic Compression**: Full conversation state reduced to 3 numbers + 1 word

## 3. Origin Timeline
| Date | Event |
|------|-------|
| 2026-05-25 | CLS 6-step cognitive cycle committed (commit 73ee3a84) |
| 2026-06-02 | Fuse Board activated |
| 2026-06-03 | Dual-AI Gate enforced |
| 2026-06-07 | Addy Osmani publishes Loop Engineering (first public use of term) |
| 2026-06-10~20 | Boris Cherny and Peter Steinberger public talks |

CLS predates the Loop Engineering public discourse by approximately 2 weeks.

## 4. Design Philosophy
1. Interface > Implementation — fixed signatures, swappable backends
2. Triple Product: AI x CLS x Human — stable closed loop
3. Sparse Activation, Shared Baseline — safety always on, domain skills on demand

## 5. Repository
- GitHub: https://github.com/zyc1419456542/cls-cognitive-loop
- License: Apache 2.0
