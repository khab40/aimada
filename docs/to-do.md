# Todos left

## Evidence and correctness
DONE: Start real Nebius endpoint and jobs
Run several relatively heavy tasks from UI Control panel
DONE: Check results at Nebius cloud and grab results back to the project and repo

## Update documentation
LinkedIn, images suggested
Images and logs in Evidence.md


## Updates for Submission

## Video recording
Using transcript that already exists

## Suggestions from AI
Remaining publication work: final Nebius/UI screenshots only.

# Codex Prompt 2 — Build the Judge-Facing Production Evidence Bundle

Create a compact, public, sanitized production-evidence bundle for the Nebius Serverless AI Builders Challenge.

The application already implements:

* more than ten successful Nebius Serverless AI Job runs;
* a vLLM-backed Nebius Serverless AI Endpoint;
* successful execution of multiple Endpoint routes;
* durable evidence archival to Nebius Object Storage;
* S3-to-backend synchronization;
* evidence display and download links in the UI.

Do not reimplement these features. Package existing evidence so judges can verify it quickly without access to private Nebius credentials or the private S3 bucket.

## Create this structure

```text
docs/evidence/
├── README.md
├── production-run-summary.md
├── endpoint/
│   ├── README.md
│   ├── endpoint-health-example.json
│   ├── endpoint-route-example.json
│   └── redacted-endpoint-log.txt
├── jobs/
│   ├── README.md
│   ├── production-run-index.json
│   ├── representative-job-status.json
│   └── redacted-job-log.txt
├── artifacts/
│   ├── manifest.json
│   ├── metrics.csv
│   ├── benchmark-report.md
│   └── artifact-index.json
└── screenshots/
    └── README.md
```

Use the actual existing output paths and names where appropriate rather than duplicating data unnecessarily.

## Requirements

1. Select one successful Serverless AI Job as the canonical representative production run.

2. Document:

* sanitized Job ID or shortened display form;
* final status;
* Job image and tag;
* hardware preset;
* scenario/run configuration;
* start and completion timestamps if available;
* measured runtime;
* produced artifacts;
* how evidence moved from Job execution to S3, backend storage and UI.

3. Include a small production-run history showing that more than ten runs completed.

4. Add Endpoint evidence for representative successful routes such as:

* health;
* scenario generation;
* incident analysis;
* investigation report;
* structured market-event explanation.

5. Preserve meaningful technical metadata:

* route name;
* status;
* latency;
* model;
* platform or hardware;
* execution timestamp.

6. Remove or redact:

* access keys;
* secret keys;
* bearer tokens;
* authorization headers;
* signed URLs;
* private endpoint hostnames where sensitive;
* tenant IDs;
* project IDs;
* personal email addresses;
* private local paths.

7. Never invent evidence, runtime, costs, IDs, metrics or screenshots.

8. When raw evidence is unavailable in the repository, create a clearly marked placeholder checklist in `docs/evidence/screenshots/README.md` rather than fabricating a result.

9. Update `docs/challenge-submission.md` so its Proof of Execution section contains direct relative links to this evidence bundle.

10. Add a prominent link near the top of the README:

```markdown
[Production Nebius evidence](docs/evidence/README.md)
```

## Evidence README structure

The judge-facing evidence README should include:

* what was executed;
* why Endpoints and Jobs were used;
* representative production Job;
* representative production Endpoint routes;
* S3 archival and synchronization flow;
* public sanitized artifacts;
* limitations;
* instructions for reproducing the local deterministic path.

## Validation

Run:

* secret scanning;
* tests for evidence archival and synchronization;
* any artifact validation scripts;
* Markdown checks if available.

Report:

* evidence files created;
* source artifacts used;
* all redactions applied;
* anything that still requires a manual screenshot.


# Last mile
Score project on four dimensions:

* Technical quality
* Originality
* Use of Nebius platform
* Presentation/storytelling

1. Validate the deployment 
* endpoint health
* vLLM starts correctly
* GPU memory usage
* latency
* structured JSON responses
* prompts work

Do not change any more infrastructure after this unless something is broken.

⸻

2. Freeze versions

This is something people often forget.

Record:

* git commit hash
* Docker image tag
* endpoint image
* model version
* Nebius preset
* platform
* Python version

You’ll need this later if someone asks

“Exactly what did you run?”

⸻

3. Run 5–10 representative scenarios

Don’t just run random experiments.

Create a benchmark table.

Scenario	Expected	Result
benign MM	benign	✅
spoofing	spoofing	✅
layering	layering	✅
detector disagreement	uncertainty	✅
low liquidity	suspicious	✅

This becomes great material for the article.

⸻

4. Save EVERYTHING

Don’t only save logs.

Save

* screenshots
* JSON requests
* JSON responses
* latency
* GPU metrics
* endpoint dashboard
* Nebius dashboard
* architecture diagrams

You will reuse all of this.

⸻

Missing technical things

I’d also collect

GPU utilization

One screenshot.

Endpoint metrics

One screenshot.

Example structured output

One JSON.

Architecture

One clean diagram.

⸻

LinkedIn article

I’d actually publish before submission if the challenge rules don’t prohibit it.

Structure:

1. Problem
2. Existing approaches
3. AIMADA
4. Architecture
5. Nebius Serverless
6. Multi-agent design
7. LLM investigation
8. Results
9. Future work

This will likely be your strongest technical article this year.

⸻

Images

I’d make around 8 images.

Not screenshots.

Proper diagrams.

For example

1. Overall architecture
2. Red vs Blue agents
3. LOB simulation
4. AI investigation workflow
5. Nebius deployment
6. Detection pipeline
7. Structured JSON
8. Dashboard screenshot

⸻

Video

Absolutely yes.

I would upload to:

* ✅ YouTube (primary)
* LinkedIn (native upload)
* GitHub README (link to YouTube)

A 4–6 minute video is ideal.

Structure

30 sec
Problem

60 sec
Architecture

60 sec
Simulation

60 sec
LLM investigation

60 sec
Nebius deployment

30 sec
Future work

⸻

GitHub

This is one thing you didn’t mention.

I’d spend an hour making the repository polished.

Add

* animated GIF
* architecture
* quick start
* screenshots
* challenge badge
* nice README

People absolutely judge projects by the README.

⸻

Submission package

Besides updating the submission document, I’d include

* GitHub
* YouTube
* LinkedIn article
* architecture PDF
* demo screenshots

⸻

Future work section

Don’t forget this.

Mention things like

* PRAGMA integration
* Graph Neural Networks
* reinforcement learning agents
* multiple exchanges
* cross-market manipulation
* multi-LLM tournaments
* synthetic surveillance datasets

Judges love seeing a clear roadmap.

⸻

The only major thing I think is still missing

Something you’ve talked about but not yet demonstrated:

Quantitative evaluation

Right now you’ll have

“It works.”

I’d also show

“It works better.”

For example:

Metric	Old	New
Avg investigation length	90 tokens	820 tokens
JSON validity	72%	100%
Avg latency	2.8 s	3.4 s
GPU utilization	4%	43%
False-positive explanation quality	Medium	High

Even five simple before/after metrics make the submission much more convincing.

⸻

Overall assessment

If the deployment succeeds, I would stop adding major features.

You’re at the point where another week of engineering is likely to add less value than a day spent on:

* polishing the README,
* creating a clear architecture diagram,
* producing a strong demo video,
* and publishing a professional technical article.

Those presentation assets are what will make AIMADA stand out from a technically solid but less well-communicated submission.

# Evidence artefacts collection
I recommend treating the deployment exactly like a research experiment. Once it works, capture the complete state once and never overwrite it. This makes your results reproducible and gives you solid material for the submission, GitHub, and LinkedIn.

I would create a folder:

evidence/
    deployment-2026-07-14/

and populate it automatically.

1. Git version

mkdir -p evidence/deployment-2026-07-14
git rev-parse HEAD \
> evidence/deployment-2026-07-14/git-commit.txt
git status \
> evidence/deployment-2026-07-14/git-status.txt
git log -1 \
> evidence/deployment-2026-07-14/git-last-commit.txt

⸻

2. Docker image

docker images \
> evidence/deployment-2026-07-14/docker-images.txt

Then save the actual endpoint image metadata:

docker image inspect \
ghcr.io/khab40/ai-market-abuse-detection-arena-endpoint:vllm-qwen14b-l40s-d-v1 \
> evidence/deployment-2026-07-14/docker-image-inspect.json

⸻

3. Endpoint configuration

Save every deployment variable:

env | grep -E 'NEBIUS_|LOCAL_VLLM_|ENDPOINT_' \
> evidence/deployment-2026-07-14/environment.txt

Do not include:

* ENDPOINT_TOKEN
* Hugging Face tokens
* GitHub tokens
* Nebius API tokens

Filter them out if necessary:

env \
| grep -E 'NEBIUS_|LOCAL_VLLM_|ENDPOINT_' \
| grep -v TOKEN \
> evidence/deployment-2026-07-14/environment.txt

⸻

4. Endpoint description

After creation:

nebius ai endpoint list \
> evidence/deployment-2026-07-14/endpoints.txt

Then

nebius ai endpoint get <endpoint-id> \
> evidence/deployment-2026-07-14/endpoint.json

This is probably the most valuable deployment artifact.

⸻

5. Platform

nebius compute platform list \
> evidence/deployment-2026-07-14/platforms.txt

⸻

6. Python

python --version \
> evidence/deployment-2026-07-14/python-version.txt
pip freeze \
> evidence/deployment-2026-07-14/pip-freeze.txt

⸻

7. Docker version

docker version \
> evidence/deployment-2026-07-14/docker-version.txt
docker info \
> evidence/deployment-2026-07-14/docker-info.txt

⸻

8. vLLM version

Inside the container:

python -c "import vllm; print(vllm.__version__)"

Save:

> evidence/deployment-2026-07-14/vllm-version.txt

⸻

9. Model

Save exactly what model was used:

Qwen/Qwen2.5-14B-Instruct

Create

evidence/deployment-2026-07-14/model.txt

Example

Model:
Qwen/Qwen2.5-14B-Instruct
dtype:
auto
context:
16384
GPU utilization:
0.90
max_num_seqs:
16

⸻

10. Benchmark

Record

Prompt
↓
Response
↓
Latency
↓
GPU
↓
JSON validity

This becomes your benchmark.

⸻

11. Architecture

Save

architecture-v1.drawio
architecture-v1.png
architecture-v1.pdf

⸻

12. Screenshots

Create

screenshots/
01-endpoint-created.png
02-nebius-dashboard.png
03-health-endpoint.png
04-json-output.png
05-architecture.png
06-demo-ui.png

⸻

13. Prompt versions

Don’t forget this.

Create

prompts/
system-v1.md
investigation-v1.md
red-agent-v1.md

When you improve prompts later:

system-v2.md
system-v3.md

This makes your evolution obvious.

⸻

14. Experiment log

A simple Markdown file:

experiments.md

Example

Experiment 1
Old H100
Qwen14B
Short prompt
Latency 2.8s
Output:
Poor
Experiment 2
L40S
Structured prompt
Latency 3.4s
Output:
Excellent

⸻

15. Final release manifest

I like creating a single release.md that answers:

Repository
Git commit
Docker image
Model
Nebius platform
Preset
Prompt version
Date
Author

This becomes the canonical reference for the project version you submitted.

⸻

I would automate it

Given the maturity of your repository, I’d add a single script, for example:

./scripts/freeze-release.sh

that automatically collects:

* Git metadata
* Docker metadata
* Nebius endpoint configuration
* Environment (with secrets removed)
* Python packages
* vLLM version
* Docker version
* Endpoint metadata
* Model configuration
* Prompt files
* Architecture
* README
* Screenshots
* Benchmark outputs

and writes everything into a timestamped evidence/deployment-YYYY-MM-DD-HHMM/ directory.

That would take less than a minute to run, and if someone from Nebius later asks, “Exactly what did you submit?”, you’ll have a complete, reproducible snapshot of the entire system.
