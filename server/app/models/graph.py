from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

class GraphNodeType(str, Enum):
    CASE = "CASE"
    EVIDENCE = "EVIDENCE"
    EVENT = "EVENT"
    DEVICE = "DEVICE"
    INVESTIGATOR = "INVESTIGATOR"
    LOCATION = "LOCATION"
    CUSTODY = "CUSTODY"
    ACTOR = "ACTOR"
    IP_ADDRESS = "IP_ADDRESS"
    SECURITY_ALERT = "SECURITY_ALERT"
    BACKUP = "BACKUP"  # Preserved original backup node

class GraphEdgeType(str, Enum):
    CONTAINS = "CONTAINS"
    GENERATED_EVENT = "GENERATED_EVENT"
    COLLECTED_FROM = "COLLECTED_FROM"
    OCCURRED_ON = "OCCURRED_ON"
    LOCATED_AT = "LOCATED_AT"
    HANDLED_BY = "HANDLED_BY"
    HAS_CUSTODY_EVENT = "HAS_CUSTODY_EVENT"
    CORRELATED_WITH = "CORRELATED_WITH"
    ATTEMPTED_ACCESS = "ATTEMPTED_ACCESS"
    HAS_BACKUP = "HAS_BACKUP"               # EVIDENCE → ORIGINAL_BACKUP
    TAMPER_DETECTED = "TAMPER_DETECTED"     # ACTOR/EVENT → EVIDENCE

class GraphNode(BaseModel):
    id: str
    node_type: GraphNodeType
    label: str
    case_id: str
    source_id: str
    severity: Optional[str] = "INFO"
    metadata: Dict[str, Any] = Field(default_factory=dict)

class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    edge_type: GraphEdgeType
    label: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class EvidenceGraphResponse(BaseModel):
    case_id: str
    total_nodes: int
    total_edges: int
    nodes: List[GraphNode]
    edges: List[GraphEdge]
