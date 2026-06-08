# Nebius Market Abuse Arena

Nebius Market Abuse Arena is a live synthetic market simulation for demonstrating how suspicious order-book behavior can be generated, detected, explained, and benchmarked without using real trading data.

The system combines a React visual arena, a FastAPI exchange simulator, synthetic normal and red-team agents, deterministic market microstructure detectors, and Nebius serverless infrastructure.

## What It Demonstrates

- A live synthetic order book with changing bids, asks, spread, mid-price, depth, and imbalance.
- Abuse-like scenarios such as spoofing-like walls, layering-like patterns, quote-stuffing bursts, and liquidity evaporation.
- Deterministic detectors that produce confidence scores and structured evidence.
- Incident review with replay context and plain-English AI explanations.
- Batch benchmark runs that compare detector precision, recall, F1, and detection latency.

## How Nebius Is Used

- **Nebius Serverless AI Endpoint** explains synthetic incidents, generates investigation summaries, and drafts bounded red-team scenario ideas.
- **Nebius Serverless AI Jobs** run offline detector tournaments, synthetic dataset generation, feature extraction, evaluation runs, and benchmark reports.

The browser never calls Nebius directly. The FastAPI backend owns endpoint URLs, tokens, request shaping, and fallback behavior.

## Why It Matters

Market surveillance concepts are difficult to evaluate because real order-book data is sensitive, detector output is technical, and suspicious behavior is hard to replay. This arena creates a controlled environment where product, compliance, and engineering teams can see the same evidence, test detector behavior, and discuss explainability before any real-market integration.

## Important Limitation

This project is an educational simulation. It does not detect real market manipulation, does not provide trading signals, and should not be used for compliance decisions. The scenarios are synthetic abuse-like patterns designed to demonstrate order-book anomaly detection and AI-generated explanations.

## Next Step

A practical pilot would connect the arena to sanitized historical replay data, validate detector definitions with domain experts, run Nebius benchmark jobs across controlled scenarios, and define governance rules for AI-generated explanations.
