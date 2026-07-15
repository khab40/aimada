# LOB Arena production E2E evidence — 2026-07-15

This sanitized bundle records six corrected Nebius Serverless Job executions. Each experiment forwards a distinct base seed, derives 200 per-run seeds with SHA-256, persists seed provenance, uploads Job outputs to Object Storage, and synchronizes them back through the backend.

## Execution summary

| Experiment | Base seed | Nebius Job | Workloads | Events | Lifecycle (s) |
|---|---:|---|---:|---:|---:|
| `EXP-BAE4F069` | 2026071511 | `aijob-e00knfv5cc4295q2gz` | 200 | 24,822 | 225.655 |
| `EXP-677397C8` | 2026071512 | `aijob-e00n4vrbmwjpt29c0g` | 200 | 24,816 | 216.562 |
| `EXP-018AB760` | 2026071513 | `aijob-e00n75a37hecaw5jh3` | 200 | 24,831 | 216.551 |
| `EXP-37FD1B07` | 2026071514 | `aijob-e00s6rbq3h6ckythqx` | 200 | 24,831 | 216.550 |
| `EXP-040AE585` | 2026071515 | `aijob-e00ee01m5dr0csp3e8` | 200 | 24,815 | 216.557 |
| `EXP-0BFB10FE` | 2026071516 | `aijob-e00ppfypw76tjpwgdg` | 200 | 24,843 | 216.561 |
| **Total** | **6 base seeds** | **6 jobs** | **1,200** | **148,958** | **1,308.436** |

All six Jobs completed. Their 42 Job-output artifacts were uploaded to the experiment S3 prefixes, synchronized, normalized, and indexed by the backend. Lifecycle time is measured from each accepted Job record's creation and final update; it includes queue, status, and collection overhead and is not provider-billed compute time.

## Seed and artifact verification

- 1,200 unique derived run seeds; zero overlap between every pair of experiments.
- Six distinct full event-stream SHA-256 digests.
- Six distinct `detector_metrics.csv` SHA-256 digests.
- Every manifest records its base seed and `seed_strategy=sha256(base_seed, run_index)`.

| Experiment | Event SHA-256 | Metrics SHA-256 |
|---|---|---|
| `EXP-BAE4F069` | `b6aef6c7c21b50edc5dd048b1e6a9941b92386ba678e781db678e5425db06221` | `035b37814806e170781bc1fe0dfe9401f00d97c2f04d92698398fa16cb0404ec` |
| `EXP-677397C8` | `0c3991c2e90a98285ce6fcd895a92627528990d7eef61060cf2215261878367a` | `ecdcef08670d8c595dd014f78eea516d4f38f6083c63b9e778054d8cac440aea` |
| `EXP-018AB760` | `020c58eabfc6f8541cbb983ab0921d4d51400cc2e3486a9b6e2b02fa854e1ab8` | `e92d8d1f8530980342b026d68db0417ea35f2c0d639fbc71c958899609e26124` |
| `EXP-37FD1B07` | `1349a049453b1a2806080112c456664416d22d3f8a14dc829ff3134d2f76202a` | `78c667167c6625a6d6f7fba8cae2f9185740067e9093d4e6120f3354553fedad` |
| `EXP-040AE585` | `335559a4752dd2442f61e7b0296469c262aa33dfc0a1ddfcdcf306e92d0c6d97` | `6ca35f43626a2d1947e5553a233700bb6c20fda93c1907d0ba17693fcbdc6b95` |
| `EXP-0BFB10FE` | `8e118ac4acdf4dbf2ecd9ec59adbc964c07d6e2d54d531b9c5e4ba7d671ab306` | `c7e51f01a053e37f69156a3109414e34c8fc6ab8416c607070af73af4edad94b` |

## Detector results

Across 960 positive attack workloads and 240 normal controls, the matched detector metrics were:

| Measure | Count / value |
|---|---:|
| True positives | 710 |
| False negatives | 250 |
| False positives | 0 |
| True negatives | 240 |
| Precision | 1.000 |
| Recall | 0.740 |
| F1 | 0.850 |
| Normal-control specificity | 1.000 |
| Normal-control false-positive rate | 0.000 |

Spoofing-like Wall and Quote Stuffing Burst each achieved recall 1.0. Layering-like Pattern achieved 230/240 detections and recall 0.958. Liquidity Evaporation produced 240 false negatives and recall 0.0. That blind spot is the principal benchmark finding; these synthetic results are execution and evaluation evidence, not a production-surveillance accuracy claim. A representative corrected cloud result is committed in [detector_metrics.csv](detector_metrics.csv).

## Audit history

The earlier six-Job set produced exactly 24,846 events per execution and identical normalized event and metrics digests because experiment seeds were stored but not forwarded; every Job used base seed `42`. It remains valid infrastructure audit history but is withdrawn as multi-seed benchmark evidence. The corrected command path now forwards the base seed, derives disjoint per-run seeds, and seed-varies reference price, tick size, depth, normal-agent count, scenario allocation, and difficulty allocation.

Cloud pricing rates were not configured. The UI therefore reports measured usage and “pricing rates are not configured”; this bundle does not invent a zero or estimated dollar cost.

No credential, authorization header, signed URL, Object Storage key, private hostname, or Endpoint token is included.
