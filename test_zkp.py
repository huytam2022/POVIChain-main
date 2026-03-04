#!/usr/bin/env python3
"""Test ZKP functionality."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from povichain.zkp import ZKPFactory, Groth16Prover, STARKProver


def test_groth16():
    """Test Groth16 prover."""
    print("Testing Groth16 Prover...")
    
    prover = ZKPFactory.create_prover("groth16", use_stub=True)
    
    private_inputs = {'secret': 12345, 'amount': 100}
    public_inputs = {'tx_id': 'abc123', 'zone_id': 1, 'destination': 'domain_b'}
    
    # Generate proof
    proof = prover.generate_proof(private_inputs, public_inputs)
    print(f"  Proof generated: {proof['proof'][:16]}...")
    print(f"  Proving time: {proof['proving_time_ms']}ms")
    
    # Verify proof
    is_valid = prover.verify_proof(proof, public_inputs)
    print(f"  Verification: {'PASS' if is_valid else 'FAIL'}")
    
    # Test with wrong public inputs
    wrong_inputs = {'tx_id': 'wrong', 'zone_id': 2}
    is_invalid = not prover.verify_proof(proof, wrong_inputs)
    print(f"  Wrong inputs rejected: {'PASS' if is_invalid else 'FAIL'}")
    
    return is_valid and is_invalid


def test_stark():
    """Test STARK prover."""
    print("\nTesting STARK Prover...")
    
    prover = ZKPFactory.create_prover("stark", use_stub=True)
    
    private_inputs = {'secret': 67890, 'amount': 200}
    public_inputs = {'tx_id': 'def456', 'zone_id': 2}
    
    proof = prover.generate_proof(private_inputs, public_inputs)
    print(f"  Proof generated: {proof['proof'][:16]}...")
    print(f"  Proving time: {proof['proving_time_ms']}ms")
    
    is_valid = prover.verify_proof(proof, public_inputs)
    print(f"  Verification: {'PASS' if is_valid else 'FAIL'}")
    
    return is_valid


def test_comparison():
    """Compare Groth16 vs STARK timing."""
    print("\nComparing Groth16 vs STARK...")
    
    groth16 = ZKPFactory.create_prover("groth16", use_stub=True)
    stark = ZKPFactory.create_prover("stark", use_stub=True)
    
    inputs = {'tx': 'test', 'amount': 100}
    
    g_proof = groth16.generate_proof({}, inputs)
    s_proof = stark.generate_proof({}, inputs)
    
    print(f"  Groth16: {g_proof['proving_time_ms']}ms")
    print(f"  STARK:   {s_proof['proving_time_ms']}ms")
    print(f"  Ratio:   {s_proof['proving_time_ms'] / g_proof['proving_time_ms']:.1f}x slower")
    
    return True


def main():
    print("=" * 60)
    print("ZKP Module Tests")
    print("=" * 60)
    
    results = []
    results.append(("Groth16", test_groth16()))
    results.append(("STARK", test_stark()))
    results.append(("Comparison", test_comparison()))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name}: {status}")
    
    all_passed = all(r[1] for r in results)
    print(f"\nOverall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
