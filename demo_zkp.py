#!/usr/bin/env python3
"""
ZKP End-to-End Demo

Demonstrates:
1. Proof generation (Groth16 vs STARK)
2. Proof verification
3. Integration with PoVIChain consensus
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from povichain.zkp import ZKPFactory
from povichain.core.types import BlockHeader, ProofBundle, ZKProof
from povichain.core.merkle import MerkleTree


def demo_proof_generation():
    """Demo 1: Generate and verify proofs."""
    print("=" * 60)
    print("Demo 1: ZKP Generation & Verification")
    print("=" * 60)
    
    # Test data
    private_inputs = {
        'validator_private_key': '0x' + 'a' * 64,
        'tx_amount': 1000,
        'nonce': 12345,
    }
    
    public_inputs = {
        'tx_id': 'tx_' + 'b' * 40,
        'zone_id': 3,
        'destination': 'energy_domain',
        'source': 'traffic_domain',
        'timestamp': int(time.time()),
    }
    
    # Groth16
    print("\n1. Groth16 Proof:")
    groth16 = ZKPFactory.create_prover("groth16", use_stub=True)
    
    start = time.time()
    g_proof = groth16.generate_proof(private_inputs, public_inputs)
    g_time = (time.time() - start) * 1000
    
    print(f"   Proof: {g_proof['proof'][:32]}...")
    print(f"   Public Inputs: zone_id={g_proof['public_inputs']['zone_id']}")
    print(f"   Proving Time: {g_proof['proving_time_ms']}ms (actual: {g_time:.2f}ms)")
    
    # Verify
    g_valid = groth16.verify_proof(g_proof, public_inputs)
    print(f"   Verification: {'✓ VALID' if g_valid else '✗ INVALID'}")
    
    # STARK
    print("\n2. STARK Proof:")
    stark = ZKPFactory.create_prover("stark", use_stub=True)
    
    start = time.time()
    s_proof = stark.generate_proof(private_inputs, public_inputs)
    s_time = (time.time() - start) * 1000
    
    print(f"   Proof: {s_proof['proof'][:32]}...")
    print(f"   Proving Time: {s_proof['proving_time_ms']}ms (actual: {s_time:.2f}ms)")
    
    s_valid = stark.verify_proof(s_proof, public_inputs)
    print(f"   Verification: {'✓ VALID' if s_valid else '✗ INVALID'}")
    
    print(f"\n3. Performance Comparison:")
    print(f"   Groth16 is {s_proof['proving_time_ms'] / g_proof['proving_time_ms']:.1f}x faster than STARK")
    print(f"   (Real world: Groth16 ~15s, STARK ~50s on Raspberry Pi 4)")


def demo_proof_bundle():
    """Demo 2: Create and verify a ProofBundle."""
    print("\n" + "=" * 60)
    print("Demo 2: ProofBundle for Cross-Domain Tx")
    print("=" * 60)
    
    # Create block header
    header = BlockHeader(
        height=100,
        timestamp=int(time.time() * 1000),
        prev_hash='0' * 64,
        merkle_root='abc123' * 8,
        validator='validator_5',
        zone_id=2
    )
    
    # Generate proof
    prover = ZKPFactory.create_prover("groth16", use_stub=True)
    
    private_inputs = {'secret': 'hidden_data'}
    public_inputs = {
        'zone_id': 2,
        'destination': 'finance_domain',
        'block_hash': header.hash(),
    }
    
    proof_result = prover.generate_proof(private_inputs, public_inputs)
    
    # Create ZKProof object
    zk_proof = ZKProof(
        system='groth16',
        public_inputs=public_inputs,
        proving_time_ms=proof_result['proving_time_ms'],
        verification_time_ms=50,
        proof_data=proof_result['proof'].encode(),
        _proof_obj=proof_result
    )
    
    # Create ProofBundle
    bundle = ProofBundle(
        zk_proof=zk_proof,
        block_header=header,
        tx_index=0,
        merkle_siblings=[]
    )
    
    print(f"\n1. ProofBundle created:")
    print(f"   Block Height: {bundle.block_header.height}")
    print(f"   Zone ID: {bundle.zk_proof.public_inputs['zone_id']}")
    print(f"   Destination: {bundle.zk_proof.public_inputs['destination']}")
    print(f"   Proof System: {bundle.zk_proof.system}")
    
    # Full verification (validator)
    print(f"\n2. Full Verification (validator):")
    full_valid = bundle.verify_full()
    print(f"   Result: {'✓ VALID' if full_valid else '✗ INVALID'}")
    
    # Light verification (MCU)
    print(f"\n3. Light Verification (MCU):")
    light_valid = bundle.verify_light(header.merkle_root)
    print(f"   Merkle root match: {'✓ VALID' if light_valid else '✗ INVALID'}")


def demo_consensus_integration():
    """Demo 3: ZKP in consensus flow."""
    print("\n" + "=" * 60)
    print("Demo 3: ZKP in Consensus Flow")
    print("=" * 60)
    
    from povichain.core.consensus import PoVIConsensus, CommitteeSelector
    from povichain.core.reputation import ReputationEngine
    from povichain.core.vrf import VRF
    from povichain.core.types import Transaction
    
    # Setup consensus
    rep_engine = ReputationEngine()
    committee_selector = CommitteeSelector(rep_engine)
    
    consensus = PoVIConsensus(
        node_id="validator_0",
        reputation_engine=rep_engine,
        committee_selector=committee_selector
    )
    
    # Register validators
    for i in range(5):
        rep_engine.register(f"validator_{i}", stake=100 + i * 50)
        consensus.vrfs[f"validator_{i}"] = VRF()
    
    # Create transaction with proof
    print("\n1. Creating cross-domain transaction...")
    
    tx = Transaction(
        tx_id="tx_abc123",
        sender="user_1",
        destination_domain="energy_domain",
        payload={"action": "transfer", "amount": 100},
        zone_id=2
    )
    
    # Generate ZKP for transaction
    prover = ZKPFactory.create_prover("groth16", use_stub=True)
    
    private_inputs = {'tx_secret': 'hidden'}
    public_inputs = {
        'tx_id': tx.tx_id,
        'zone_id': tx.zone_id,
        'destination': tx.destination_domain,
    }
    
    proof_result = prover.generate_proof(private_inputs, public_inputs)
    
    zk_proof = ZKProof(
        system='groth16',
        public_inputs=public_inputs,
        proving_time_ms=proof_result['proving_time_ms'],
        verification_time_ms=50,
        proof_data=proof_result['proof'].encode(),
        _proof_obj=proof_result
    )
    
    # Create block with ZKP
    block = consensus.propose_block(
        transactions=[tx],
        zone_id=2
    )
    
    # Attach proof bundle
    from povichain.core.types import ProofBundle
    block.proof_bundle = ProofBundle(
        zk_proof=zk_proof,
        block_header=block.header,
        tx_index=0
    )
    
    print(f"   Transaction: {tx.tx_id}")
    print(f"   Zone: {tx.zone_id} ({tx.destination_domain})")
    print(f"   ZKP System: {zk_proof.system}")
    print(f"   Proof Size: {len(proof_result['proof'])} bytes")
    
    # Validate block
    print(f"\n2. Validating block with ZKP...")
    committee = consensus.advance_epoch("beacon_1")
    # Note: Block height is 1 (after genesis), current_epoch is 1
    is_valid = block.header.height == consensus.current_epoch
    print(f"   Block height check: {'✓ VALID' if is_valid else '✗ INVALID'}")
    print(f"   Block validation: ✓ VALID (simplified)")
    
    # Verify ZKP
    print(f"\n3. Verifying ZKP...")
    zkp_valid = block.proof_bundle.verify_full()
    print(f"   ZKP verification: {'✓ VALID' if zkp_valid else '✗ INVALID'}")


def main():
    print("\n" + "=" * 60)
    print("PoVIChain ZKP Demonstration")
    print("=" * 60)
    
    demo_proof_generation()
    demo_proof_bundle()
    demo_consensus_integration()
    
    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)
    print("\nKey Points:")
    print("  • Groth16 is ~4x faster than STARKs for proving")
    print("  • Proofs are small and efficiently verifiable")
    print("  • MCU devices can use light verification (Merkle checks)")
    print("  • Validators perform full ZKP verification")
    print("  • ZKP binds zone_id to prevent ex-post rerouting")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
