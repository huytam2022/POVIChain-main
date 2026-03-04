"""Smart Zone dispatcher."""
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from ..core.types import Transaction, ProofBundle, VerificationReceipt, ZoneType


@dataclass
class SmartZone:
    zone_id: int
    zone_type: ZoneType
    name: str
    max_queue_size: int = 10000
    
    pending_queue: List[Transaction] = field(default_factory=list)
    settled_count: int = 0
    total_fees_collected: int = 0
    rejected_count: int = 0
    
    def enqueue(self, tx: Transaction) -> bool:
        if len(self.pending_queue) >= self.max_queue_size:
            return False
        self.pending_queue.append(tx)
        return True
    
    def process_batch(self, batch_size: int) -> List[Transaction]:
        batch = self.pending_queue[:batch_size]
        self.pending_queue = self.pending_queue[batch_size:]
        self.settled_count += len(batch)
        return batch
    
    def get_load(self) -> float:
        return len(self.pending_queue) / self.max_queue_size
    
    def get_stats(self) -> Dict:
        return {
            'zone_id': self.zone_id,
            'zone_type': self.zone_type.value,
            'queue_size': len(self.pending_queue),
            'load': self.get_load(),
            'settled': self.settled_count,
            'rejected': self.rejected_count,
            'fees_collected': self.total_fees_collected,
        }


@dataclass
class SmartZoneDispatcher:
    zones: Dict[int, SmartZone] = field(default_factory=dict)
    fee_schedules: Dict[int, Dict] = field(default_factory=dict)
    
    committee_share: float = 0.4
    validator_share: float = 0.3
    domain_share: float = 0.3
    
    total_dispatched: int = 0
    total_rejected: int = 0
    
    def register_zone(self, zone: SmartZone, base_fee: int = 100, 
                     per_byte_fee: int = 1):
        self.zones[zone.zone_id] = zone
        self.fee_schedules[zone.zone_id] = {
            'base_fee': base_fee,
            'per_byte_fee': per_byte_fee,
        }
    
    def dispatch(self, proof_bundle: ProofBundle, 
                fee_payer: str) -> Optional[VerificationReceipt]:
        zone_id = proof_bundle.zk_proof.public_inputs.get('zone_id', 0)
        tx_id = proof_bundle.block_header.hash()
        
        if zone_id not in self.zones:
            self.total_rejected += 1
            return None
        
        zone = self.zones[zone_id]
        fee = self._calculate_fee(zone_id, proof_bundle)
        self._distribute_fees(zone, fee)
        
        tx = Transaction(
            tx_id=tx_id,
            sender=fee_payer,
            destination_domain=proof_bundle.zk_proof.public_inputs.get('destination', ''),
            payload={'proof_bundle': proof_bundle, 'fee': fee},
            zone_id=zone_id,
            fee=fee
        )
        
        if not zone.enqueue(tx):
            zone.rejected_count += 1
            self.total_rejected += 1
            return None
        
        self.total_dispatched += 1
        
        import hashlib
        import time
        ack_data = f"{tx_id}:{zone_id}:{fee}:{int(time.time())}"
        ack = hashlib.sha256(ack_data.encode()).hexdigest()
        
        return VerificationReceipt(
            tx_id=tx_id,
            zone_id=zone_id,
            status='success',
            acknowledgement=ack
        )
    
    def _calculate_fee(self, zone_id: int, proof_bundle: ProofBundle) -> int:
        schedule = self.fee_schedules.get(zone_id, {'base_fee': 100, 'per_byte_fee': 1})
        fee = schedule['base_fee']
        proof_size = len(proof_bundle.zk_proof.proof_data)
        fee += proof_size * schedule['per_byte_fee']
        
        zone = self.zones.get(zone_id)
        if zone and zone.get_load() > 0.8:
            fee = int(fee * 1.5)
        
        return fee
    
    def _distribute_fees(self, zone: SmartZone, fee: int):
        zone.total_fees_collected += fee
    
    def get_dispatcher_efficiency(self) -> float:
        total = self.total_dispatched + self.total_rejected
        if total == 0:
            return 1.0
        return self.total_dispatched / total
