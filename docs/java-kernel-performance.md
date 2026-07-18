# Java Kernel Performance

The `kernel-benchmarks` module separates diagnostic measurement from portable regression gates. It uses [OpenJDK JMH](https://openjdk.org/projects/code-tools/jmh/) 1.37 for forked JVM benchmarks and Java thread-allocation accounting for broad CI smoke ceilings.

## JMH Benchmarks

`KernelBenchmarks` measures:

- complete deterministic simulation runs for the normal-market, quote-stuffing, and liquidity-evaporation golden requests;
- one crossing market order against a freshly prepared 12-level integer order book.

Run the configured warmup and measurement suite on macOS or Linux:

```bash
cd java
./gradlew :kernel-benchmarks:run --args='KernelBenchmarks -prof gc'
```

Use filters and shorter iterations for a development sanity check:

```bash
./gradlew :kernel-benchmarks:run \
  --args='KernelBenchmarks.runSimulation -p caseId=normal-market-seed-42 -wi 1 -i 1 -w 500ms -r 500ms -f 1 -bm avgt -tu us -prof gc'
```

JMH execution is not part of ordinary `check`: benchmark timings depend on CPU, power state, background load, JVM warmup, and profiler choice.

## Portable Regression Gates

`KernelPerformanceGateTest` runs during the normal Gradle `check` lifecycle. It checks the largest golden simulation and a complete crossing-match setup against deliberately broad ceilings:

| Path | p99 ceiling | Throughput floor | Allocation ceiling |
| --- | ---: | ---: | ---: |
| 10-tick liquidity-evaporation simulation | 1 second/run | 5 runs/second | 32 MiB/run |
| Fresh 12-level book plus crossing match | 50 ms/match | 100 matches/second | 1 MiB/match |

These are portability gates, not performance objectives. They catch order-of-magnitude regressions, runaway allocation, or accidentally blocking code without making CI depend on workstation-class timing. Tightening a gate requires repeated measurements on the CI runner and an ARD update.

The gate also verifies the largest scenario's event count and canonical stream hash on every measured run, so a faster but behaviorally different implementation cannot pass.

## Step 14 Local Sanity Baseline

A short single-fork, single-measurement run on the current macOS/aarch64 Java 25 environment reported:

| Benchmark | Average time | Normalized allocation |
| --- | ---: | ---: |
| Normal-market golden simulation | 327.707 µs/run | 763,830.948 B/run |
| Crossing market order | 0.226 µs/op | 22,536.067 B/op |

These readings only prove that benchmark generation, forking, execution, and GC allocation profiling work end to end. They are not a publishable baseline and are not used as CI thresholds. Full measurements require the default multi-iteration configuration, controlled hardware, saved raw output, and comparison against the same environment.

No Agrona or alternative data structure is introduced by this step. The allocation profile establishes evidence for later targeted optimization.
