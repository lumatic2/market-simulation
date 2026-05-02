# market-simulation

**AI-powered market research simulation for Korean consumers — no local LLM or API key required.**

Simulate how real Korean personas respond to your product, price point, or service concept using [NVIDIA Nemotron-Personas-Korea](https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea) (1M demographically grounded personas, CC BY 4.0) and Claude Code's built-in agent system.

---

## How it works

```
HuggingFace dataset          Claude Code skill
(1M Korean personas)  ──▶   filter by target segment
                      ──▶   batch into groups of 5
                      ──▶   6 parallel sub-agents (isolated context per batch)
                      ──▶   collect responses → CSV + report
```

Each sub-agent receives a batch of 5 persona profiles and responds **in character** as each person — independently, with no cross-contamination between batches. Results are saved as a CSV and a structured Markdown report.

---

## Requirements

- [Claude Code](https://claude.ai/code) (any plan — uses your existing subscription, no extra API key)
- Python 3.10+

```bash
pip install datasets pandas pyarrow
```

First run downloads and caches the Nemotron dataset (~few GB). Subsequent runs load from cache instantly.

---

## Quick start

### As a Claude Code skill

1. Clone this repo to a fixed location and install dependencies:

```bash
git clone https://github.com/lumatic2/market-simulation ~/projects/market-simulation
cd ~/projects/market-simulation
pip install datasets pandas pyarrow
```

2. Copy `SKILL.md` to your Claude Code skills directory:

```bash
cp SKILL.md ~/.claude/skills/market-simulation.md
```

3. **Start Claude Code from the repo root** — the skill runs Python code relative to the working directory:

```bash
cd ~/projects/market-simulation
claude
```

4. Trigger with natural language:

```
서울 30대 직장인들이 월 9,900원 커피 구독 서비스에 어떻게 반응할지 시뮬해줘
```

Claude will ask for your target segment and question, then run the simulation.

> **Note**: The simulation outputs (CSV + report) are saved to `output/` in the repo root.

### Programmatically

```python
from src.personas import load_pool, filter_pool, occupation_kw

# Load and filter personas
df = load_pool('korea', sample_n=50000)
pool = filter_pool(
    df,
    province='서울',
    age_range=(25, 39),
    occupation_keywords=occupation_kw('IT'),
)
sample = pool.sample(20, random_state=42)
print(f'{len(sample)} personas ready')
```

---

## Simulation limits

| | Value | Why |
|---|---|---|
| Default | 20 personas | Sufficient for theme saturation |
| Hard cap | **30 personas** | 6 agents × 5 personas. Returns diminish beyond this |
| Batch size | 5 per agent | Context isolation + response quality |

> Simulation results are LLM-generated hypotheses, not real market data. Use for directional insight and relative comparisons (segment A vs B, price X vs Y), not absolute predictions.

---

## Output

```
output/
├── 2026-05-02_coffee-subscription.csv       # raw responses
└── 2026-05-02_coffee-subscription.report.md # auto-generated stats report
```

**CSV columns:** `id, age, sex, occupation, province, district, answer`

**Report includes:** response rate, demographic breakdown, full response quotes, and a prompt to synthesize a `.summary.md` with pattern clusters and key insights.

---

## Dataset

| Field | Value |
|---|---|
| Source | [nvidia/Nemotron-Personas-Korea](https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea) |
| Size | ~1M personas |
| License | CC BY 4.0 (commercial use allowed) |
| Grounding | Korean census data, demographic distributions |
| Also available | [Japan](https://huggingface.co/datasets/nvidia/Nemotron-Personas-Japan), [USA](https://huggingface.co/datasets/nvidia/Nemotron-Personas-USA), [France](https://huggingface.co/datasets/nvidia/Nemotron-Personas-France), and more |

---

## Disclaimer

- Simulation results are **LLM-generated hypotheses**, not real survey data.
- Response rates and approval ratios are inflated by LLM positive bias — trust **relative comparisons within the same simulation**, not absolute values.
- Persona dataset is publicly available under CC BY 4.0; cite NVIDIA accordingly.

---

## Project structure

```
market-simulation/
├── SKILL.md          ← Claude Code skill entrypoint
├── src/
│   ├── personas.py   ← HuggingFace loader, filter, card builder
│   └── analyze.py    ← CSV → stats report generator
└── output/           ← simulation results (gitignored)
```

---

## License

Code: MIT  
Persona data: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (NVIDIA)
