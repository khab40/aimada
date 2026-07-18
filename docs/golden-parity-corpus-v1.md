# Golden Parity Corpus V1

The version 1 golden corpus is the immutable, byte-exact acceptance input for Python and Java kernel parity. It lives in `contracts/golden/parity-v1` and contains deterministic Protobuf request/result pairs plus a checksum manifest.

## Coverage

The corpus includes:

- a normal market run;
- an empty-book run that exercises absent optional best-price, midpoint, and spread fields;
- spoofing-like wall, layering-like, quote-stuffing, and liquidity-evaporation runs;
- every canonical exchange payload: add, modify, cancel, execute, and L2 snapshot;
- multiple seeds, event-stream hashes, final-book hashes, and quantized metrics.

Each manifest entry records the raw request/result SHA-256 checksums, canonical stream and book hashes, event-type counts, and metric count. Consumers must parse the `.pb` files with `lob.exchange.v1`, but must use the canonical hashing contract instead of raw Protobuf bytes for event and book identity.

## Maintenance Policy

Version 1 files are immutable parity evidence. A behavioral or schema change that intentionally changes these bytes must create a new `parity-vN` directory and document the compatibility decision in an ARD. Correcting a proven fixture-generation defect requires an explicit ARD amendment.

Generate the checked-in corpus with:

```bash
uv run --project backend python scripts/generate_golden_parity_corpus.py
```

Verify freshness without changing repository files with:

```bash
uv run --project backend python scripts/generate_golden_parity_corpus.py --check
```

The Java build will consume the same request and expected-result files directly. It must not translate or normalize them through an intermediate JSON format.
