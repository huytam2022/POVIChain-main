"""Deterministic 6-phase end-to-end transaction simulator for the demo page.

Walks a single cross-domain transaction through the six-phase protocol lifecycle:

    Phase 1 — Submit Tx       (User → Application Layer → Source Chain B1)
    Phase 2 — B1 Finalizes
    Phase 3 — Proof Bundle Extracted   (ZKP + Merkle inclusion)
    Phase 4 — Forwarded                (permissionless relay)
    Phase 5 — Verification & Receipt   (VRF-sampled validator + MCU light path)
    Phase 6 — Returned                 (signed receipt back to user)

Per-phase timings are derived from network delay profiles, gateway prover
costs, and MCU verification benchmarks. Output is bit-identical for the
same TxSpec.
"""
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List

_PREFIX = "POVI|E2E|"


def _digest(prefix: str, *parts: Any) -> str:
    h = hashlib.sha256()
    h.update(prefix.encode("utf-8"))
    for p in parts:
        h.update(b"|")
        h.update(str(p).encode("utf-8"))
    return h.hexdigest()[:16]


def _det_jitter(key: str, amplitude: float) -> float:
    if amplitude <= 0.0:
        return 0.0
    h = hashlib.sha256((_PREFIX + key).encode("utf-8")).digest()
    val = int.from_bytes(h[:8], "big") / (2 ** 64)
    return (val - 0.5) * 2.0 * amplitude


@dataclass(frozen=True)
class TxSpec:
    source_domain: str
    destination_domain: str
    smart_zone: str
    payload_bytes: int
    proof_backend: str
    edge_verifier: str


@dataclass
class PhaseResult:
    name: str
    short_name: str
    layer: str
    duration_ms: float
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""


@dataclass
class EndToEndResult:
    tx_id: str
    tx_spec: TxSpec
    phases: List[PhaseResult]
    total_duration_ms: float
    verification_path: str
    smart_zone_routed_to: str
    proof_size_kb: float
    success: bool


def run_end_to_end(spec: TxSpec) -> EndToEndResult:
    tx_id = _digest("TX", spec.source_domain, spec.destination_domain,
                    spec.payload_bytes, spec.proof_backend)
    block_id_b1 = _digest("BLK_B1", tx_id)
    state_root = _digest("STATE", block_id_b1)

    phases: List[PhaseResult] = []

    p1_dur = 5.0 + _det_jitter("P1|" + tx_id, 1.5)
    phases.append(PhaseResult(
        name="Phase 1 — Submit Tx",
        short_name="Submit",
        layer="Layer 1",
        duration_ms=p1_dur,
        inputs={
            "user": "User (Source)",
            "destination_hint": spec.destination_domain,
            "payload_bytes": spec.payload_bytes,
        },
        outputs={
            "tx_id": tx_id,
            "application_layer": "received",
            "submitted_to": spec.source_domain,
        },
        notes=(
            "User submits the cross-domain transaction with an explicit "
            "destination hint. The application layer relays it to source "
            f"chain {spec.source_domain.upper()} for native processing. "
            "No assumption of trust beyond the source chain itself."
        ),
    ))

    p2_dur = 120.0 + _det_jitter("P2|" + tx_id, 30.0)
    phases.append(PhaseResult(
        name="Phase 2 — B1 Finalizes",
        short_name="Finalize",
        layer="Layer 1",
        duration_ms=p2_dur,
        inputs={"tx_id": tx_id, "source_chain": spec.source_domain},
        outputs={
            "block_id": block_id_b1,
            "state_root": state_root,
            "finality": "immutable",
        },
        notes=(
            f"Source chain {spec.source_domain.upper()} processes the tx under "
            "its native consensus and commits the result. Once finalized, the "
            "execution outcome is immutable and eligible for external "
            "verification."
        ),
    ))

    if spec.proof_backend == "Groth16":
        zkp_dur = 15000.0 + _det_jitter("ZKP_G16|" + tx_id, 4000.0)
        proof_size_kb = 0.5
    else:
        zkp_dur = 50000.0 + _det_jitter("ZKP_STK|" + tx_id, 8000.0)
        proof_size_kb = 32.0
    merkle_dur = 50.0 + _det_jitter("MERKLE|" + tx_id, 10.0)
    p3_dur = zkp_dur + merkle_dur
    proof_digest = _digest("ZKP_PROOF", tx_id, spec.proof_backend)
    merkle_root = _digest("MERKLE_ROOT", block_id_b1)
    phases.append(PhaseResult(
        name="Phase 3 — Proof Bundle Extracted",
        short_name="Extract proof",
        layer="Layer 2",
        duration_ms=p3_dur,
        inputs={
            "block_id": block_id_b1,
            "state_root": state_root,
            "proof_backend": spec.proof_backend,
        },
        outputs={
            "zkp_proof_digest": proof_digest,
            "merkle_inclusion_root": merkle_root,
            "zone_id_committed_to_public_input": spec.smart_zone,
            "proof_size_kb": proof_size_kb,
            "zkp_generation_ms": round(zkp_dur, 1),
            "merkle_build_ms": round(merkle_dur, 1),
        },
        notes=(
            f"A proof bundle is built: a {spec.proof_backend} ZKP attesting "
            f"correct execution under {spec.source_domain.upper()}'s rules, "
            "plus a Merkle inclusion proof binding the tx to the final state "
            f"root. The destination smart zone '{spec.smart_zone}' is "
            "committed to the ZKP public inputs — preventing ex-post "
            "re-routing of value flows."
        ),
    ))

    p4_dur = 250.0 + _det_jitter("P4|" + tx_id, 100.0)
    phases.append(PhaseResult(
        name="Phase 4 — Forwarded",
        short_name="Relay",
        layer="Layer 2",
        duration_ms=p4_dur,
        inputs={
            "proof_bundle_digest": proof_digest,
            "merkle_root": merkle_root,
            "destination": spec.destination_domain,
        },
        outputs={
            "relay_path": "permissionless gossip",
            "delivered_to": spec.destination_domain,
            "relay_authority_required": False,
        },
        notes=(
            "Any relay participant can forward the bundle without "
            "registration, staking or trusted relayer status. Forwarding "
            "carries no authority — correctness is determined solely by "
            "the cryptographic validity of the bundle."
        ),
    ))

    if spec.edge_verifier == "MCU":
        mcu_verify_dur = 125.0 + _det_jitter("MCU|" + tx_id, 30.0)
        gw_verify_dur = 80.0 + _det_jitter("GW|" + tx_id, 20.0)
        p5_dur = max(mcu_verify_dur, gw_verify_dur)
        verification_path = "Hybrid: Gateway ZKP-verify + MCU O(1) Merkle"
        verify_outputs = {
            "gateway_zkp_verify_ms": round(gw_verify_dur, 1),
            "mcu_merkle_verify_ms": round(mcu_verify_dur, 1),
            "mcu_verdict": "valid (O(1) Merkle inclusion)",
            "vrf_committee_verdict": "valid (ZKP soundness)",
        }
        verify_notes = (
            f"VRF-sampled gateway validators verify the {spec.proof_backend} "
            f"ZKP ({gw_verify_dur:.0f} ms) while the MCU device performs a "
            f"constant-time Merkle inclusion check ({mcu_verify_dur:.0f} ms) "
            "independently against the authenticated header set. The MCU "
            "does not trust the gateway — its verdict comes from the "
            "Hybrid Light Client state."
        )
    else:
        gw_verify_dur = 80.0 + _det_jitter("GW_FULL|" + tx_id, 20.0)
        p5_dur = gw_verify_dur
        verification_path = "Gateway: ZKP + Merkle"
        verify_outputs = {
            "gateway_verify_ms": round(gw_verify_dur, 1),
            "vrf_committee_verdict": "valid",
        }
        verify_notes = (
            "VRF-sampled gateway verifies both the ZKP and the Merkle "
            "inclusion proof against the authenticated header set."
        )
    receipt_id = _digest("RECEIPT", tx_id, spec.destination_domain)
    phases.append(PhaseResult(
        name="Phase 5 — Verification & Receipt",
        short_name="Verify",
        layer="Layer 2",
        duration_ms=p5_dur,
        inputs={
            "verifier_role": spec.edge_verifier,
            "proof_digest": proof_digest,
            "merkle_root": merkle_root,
        },
        outputs={
            **verify_outputs,
            "verification_result": "valid",
            "receipt_id": receipt_id,
            "smart_zone": spec.smart_zone,
            "settled_at": spec.destination_domain,
        },
        notes=verify_notes,
    ))

    p6_dur = 100.0 + _det_jitter("P6|" + tx_id, 30.0)
    phases.append(PhaseResult(
        name="Phase 6 — Returned",
        short_name="Settle",
        layer="Layer 3",
        duration_ms=p6_dur,
        inputs={"receipt_id": receipt_id},
        outputs={
            "user_notification": "delivered",
            "auditable_record": True,
            "smart_zone_settled": spec.smart_zone,
        },
        notes=(
            "The cryptographically signed receipt is returned to the "
            "originating domain (or consumed by higher-level applications), "
            "providing auditable confirmation of cross-domain execution. "
            f"The transaction is settled inside Smart Zone '{spec.smart_zone}'; "
            "failures or overloads in this zone do not propagate to others."
        ),
    ))

    total = sum(p.duration_ms for p in phases)
    return EndToEndResult(
        tx_id=tx_id,
        tx_spec=spec,
        phases=phases,
        total_duration_ms=total,
        verification_path=verification_path,
        smart_zone_routed_to=spec.smart_zone,
        proof_size_kb=proof_size_kb,
        success=True,
    )
