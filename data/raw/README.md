# Relay Protocol Calibration Dataset — Raw Traces

This directory contains raw trace artifacts that drive the timing and energy
behavior of the relay protocol baseline. The data is deterministic and
structured to reflect behavior reported for production relay stacks based on
IBC-Go / Tendermint (CometBFT) / Cosmos-relayer measurements.

## Test environment assumed

* Two CometBFT chains (source, destination) running with fast-block configuration
  suitable for local / inter-testnet benchmark (sub-second block cadence).
* Go relayer (Hermes-class) co-located in the same datacenter/LAN as the
  two chain full-nodes. Each RPC round trip traverses 2–4 physical hops.
* Standard validator set of ~100 ed25519 validators on the source chain.
* ICS-23 Merkle proofs on SHA-256 with average commitment depth ~15.
* No TLS termination on the RPC path. Persistent HTTP/2 connections for the
  relayer, so only the first few RTTs incur connection setup overhead.
* Packets carry application payloads of 256–1024 bytes (transfer + apps).

## Trace components and basis for assumed shape

Every CSV file is an empirical-style trace: first samples show a **cold path**
(warm-up / JIT / TCP slow-start), then a **warm plateau**, then occasional
**tail latency** from queueing, then a return to plateau.

### relayer_rtt_ms.csv

Round-trip latency for a relayer query against a full-node RPC. Components:

* `RPC handshake / HTTP/2 framing` — dominant in the first few samples.
* `Proof fetch` — read from store, bound by disk cache warmth.
* `Submit tx` — forward to mempool; queueing on the destination chain.

Public Cosmos Hub↔Osmosis observations report 150–300 ms on public
networks. A co-located testnet drops this to ~100–160 ms with occasional
200–350 ms tails during block proposal bursts. Trace mirrors that shape.

### header_verify_ms.csv

Time to verify a Tendermint light-client header update on the destination
chain. Primarily batch ed25519 signature verification over validator-set
commits plus header validation (ChainID, height, commit format, etc.).

Published benchmarks report ~40–90 ms for 100–125 validators on
commodity CPUs. Cold-path elevation comes from crypto-library
initialisation. Tail spikes correspond to GC pauses / thermal throttling.

### merkle_verify_ms.csv

Time to verify a single ICS-23 inclusion proof against a trusted merkle root.
Dominated by SHA-256 of `depth` interior nodes (depth ≈ 15). Public
benchmarks report 0.2–0.8 ms on ARM / x86 commodity hardware. Variance
comes from proof depth (multi-store vs single-store) and cache effects.

### source_block_interval_ms.csv

Inter-block cadence on the source chain, measured `Commit → Commit`. A
fast testnet with `timeout_commit ≈ 100 ms` settles around 100 ms but
fluctuates 95–122 ms depending on propagation and mempool pressure.

### source_commit_packet_ms.csv

Per-packet state-machine application cost on the source chain: mempool
admission, state transition for `MsgTransfer` (or equivalent), commitment
storage. Published benchmarks report 0.3–0.5 ms per packet on commodity CPUs.

### destination_execute_ms.csv

Per-packet execution on the destination chain after proof verification:
the receive callback plus application state update. Published numbers
sit in 0.3–0.5 ms per packet.

### destination_ack_commit_ms.csv

Ack commitment storage after execution. This is a single `Set` into IAVL
plus SHA-256 over the new commitment; typical 0.2–0.4 ms.

### ack_return_ms.csv

Round-trip latency for ack return path (relayer → source chain). Mirrors
`relayer_rtt_ms.csv` structurally, since it traverses the same physical
path in the opposite direction.

### dispatch_interval_ms.csv

Relayer polling period between batch dispatches. Configured at ~10 ms in
fast mode. Cold path includes config reload at startup.

### source_cpu_percent.csv / destination_cpu_percent.csv / relayer_cpu_percent.csv

CPU utilisation sampled during simulation runtime. Traces reflect a
realistic ramp-up as the pipeline warms, a plateau near the saturated state,
and a mild decay as the last blocks drain.

## Hardware energy basis

Per-component energy coefficients derived from Raspberry Pi 4 (BCM2711,
4× Cortex-A72 @ 1.5 GHz, ~5 W TDP, ~75% busy → 3.75 W) and network
wire-energy measurements (~0.3 mJ/kB on short-haul Ethernet).

The `energy_coefficients` section of the processed calibration artifact maps
directly from these per-component coefficients.
