#!/usr/bin/env python3
"""Test that all modules can be imported."""
import sys

def test_imports():
    try:
        print("Testing imports...")
        
        from povichain.core.config import Config
        print("  ✓ core.config")
        
        from povichain.core.types import Transaction, Block, ReputationState
        print("  ✓ core.types")
        
        from povichain.core.merkle import MerkleTree
        print("  ✓ core.merkle")
        
        from povichain.core.vrf import VRF
        print("  ✓ core.vrf")
        
        from povichain.core.reputation import ReputationEngine
        print("  ✓ core.reputation")
        
        from povichain.core.consensus import PoVIConsensus
        print("  ✓ core.consensus")
        
        from povichain.zones.dispatcher import SmartZoneDispatcher
        print("  ✓ zones.dispatcher")
        
        from povichain.verification.stub_prover import StubProver
        print("  ✓ verification.stub_prover")
        
        from povichain.experiments.calibrated_runner import (
            RQ1Calibrated, RQ2Calibrated, RQ3Calibrated, RQ4Calibrated
        )
        print("  ✓ experiments.calibrated_runner")
        
        print("\n✓ All imports successful!")
        return 0
        
    except Exception as e:
        print(f"\n✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(test_imports())
