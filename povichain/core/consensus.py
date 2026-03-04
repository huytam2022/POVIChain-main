"""PoVI Consensus."""
import random
import time
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
from .types import Block, BlockHeader, Transaction, ProofBundle, ReputationState
from .reputation import ReputationEngine
from .vrf import VRF, derive_seed
from .merkle import MerkleTree


@dataclass
class CommitteeSelector:
    reputation_engine: ReputationEngine
    vrf_threshold: float = 0.10
    min_reputation: float = 0.10
    
    def select_committee(self, seed: str, validators: List[str],
                        vrfs: Dict[str, VRF]) -> List[Tuple[str, str]]:
        committee = []
        total_weight = self.reputation_engine.get_total_effective_reputation()
        
        if total_weight == 0:
            return []
        
        for validator_id in validators:
            effective_rep = self.reputation_engine.get_effective_reputation(validator_id)
            
            if effective_rep < self.min_reputation:
                continue
            
            vrf = vrfs.get(validator_id)
            if not vrf:
                continue
            
            output, proof = vrf.prove(seed)
            priority = VRF.output_to_float(output, 2**64)
            threshold = self.vrf_threshold * (effective_rep / total_weight)
            
            if priority < threshold:
                committee.append((validator_id, proof))
        
        return committee


@dataclass
class PoVIConsensus:
    node_id: str
    reputation_engine: ReputationEngine
    committee_selector: CommitteeSelector
    epoch_duration_ms: int = 1000
    
    current_epoch: int = 0
    chain: List[Block] = field(default_factory=list)
    pending_transactions: List[Transaction] = field(default_factory=list)
    current_committee: List[str] = field(default_factory=list)
    vrfs: Dict[str, VRF] = field(default_factory=dict)
    
    votes_received: Dict[str, Set[str]] = field(default_factory=dict)
    invalid_accepted: int = 0
    lost_blocks: int = 0
    
    def __post_init__(self):
        if not self.chain:
            genesis = Block(
                header=BlockHeader(
                    height=0,
                    timestamp=int(time.time()),
                    prev_hash="0" * 64,
                    merkle_root="0" * 64,
                    validator="genesis",
                    zone_id=0
                ),
                transactions=[]
            )
            self.chain.append(genesis)
    
    def get_chain_head(self) -> str:
        return self.chain[-1].hash() if self.chain else "0" * 64
    
    def advance_epoch(self, random_beacon: str) -> List[str]:
        self.current_epoch += 1
        seed = derive_seed(self.get_chain_head(), random_beacon)
        
        all_validators = list(self.reputation_engine.reputations.keys())
        committee_with_proofs = self.committee_selector.select_committee(
            seed, all_validators, self.vrfs
        )
        
        self.current_committee = [c[0] for c in committee_with_proofs]
        self.votes_received = {}
        
        return self.current_committee
    
    def propose_block(self, transactions: List[Transaction],
                     proof_bundle: Optional[ProofBundle] = None,
                     zone_id: int = 0) -> Block:
        tx_hashes = [tx.hash().encode() for tx in transactions]
        merkle_tree = MerkleTree(tx_hashes)
        
        header = BlockHeader(
            height=self.current_epoch,
            timestamp=int(time.time() * 1000),
            prev_hash=self.get_chain_head(),
            merkle_root=merkle_tree.root.hex() if merkle_tree.root else "0" * 64,
            validator=self.node_id,
            zone_id=zone_id
        )
        
        return Block(header=header, transactions=transactions, proof_bundle=proof_bundle)
    
    def validate_block(self, block: Block, is_committee_member: bool = False) -> bool:
        if block.header.height != self.current_epoch:
            return False
        if block.header.prev_hash != self.get_chain_head():
            return False
        return True
    
    def receive_vote(self, validator_id: str, block_hash: str) -> bool:
        if block_hash not in self.votes_received:
            self.votes_received[block_hash] = set()
        self.votes_received[block_hash].add(validator_id)
        
        committee_size = len(self.current_committee)
        votes = len(self.votes_received[block_hash])
        return votes > (2 * committee_size // 3)
    
    def finalize_block(self, block: Block):
        self.chain.append(block)
        block_hash = block.hash()
        voters = self.votes_received.get(block_hash, set())
        
        for validator_id in self.current_committee:
            self.reputation_engine.update(
                validator_id,
                participated=(validator_id in voters),
                verified_correctly=True
            )
