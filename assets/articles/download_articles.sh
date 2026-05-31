#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

download() {
  local file="$1"
  local url="$2"
  echo "Downloading $file"
  curl -L --fail --retry 3 -o "$file" "$url"
}

download "abides-high-fidelity-market-simulation.pdf" "https://arxiv.org/pdf/1904.12066"
download "spoofing-limit-order-book-agent-based-model.pdf" "https://www.ifaamas.org/Proceedings/aamas2017/pdfs/p651.pdf"
download "realism-metrics-lob-market-simulation.pdf" "https://arxiv.org/pdf/1912.04941"
download "world-agent-lob-simulation.pdf" "https://arxiv.org/pdf/2210.09897"
download "trades-realistic-market-simulations.pdf" "https://arxiv.org/pdf/2502.07071"
download "neural-stochastic-agent-based-lob-simulation.pdf" "https://arxiv.org/pdf/2303.00080"
download "multi-agent-rl-realistic-lob-market-simulation.pdf" "https://arxiv.org/pdf/2006.05574"
download "llm-based-financial-market-agents.pdf" "https://arxiv.org/pdf/2406.19966"
