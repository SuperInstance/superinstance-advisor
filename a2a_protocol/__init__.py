"""A2A Protocol — Agent-to-Agent communication library.

Local working copy of SuperInstance/a2a-protocol, downloaded from
GitHub via Contents API. Provides message formatting, handshake
negotiation, capability exchange, and agent discovery.

Source: https://github.com/SuperInstance/a2a-protocol
"""

from .message import A2AMessage, MessageType
from .protocol import ProtocolVersion, ProtocolInfo
from .handshake import HandshakeState, HandshakeResult, HandshakeManager
from .capability import Capability, CapabilitySet, CompatibilityReport, check_compatibility
from .registry import AgentRegistry, AgentRecord

__version__ = "1.0.0"

__all__ = [
    "A2AMessage",
    "MessageType",
    "ProtocolVersion",
    "ProtocolInfo",
    "HandshakeState",
    "HandshakeResult",
    "HandshakeManager",
    "Capability",
    "CapabilitySet",
    "CompatibilityReport",
    "AgentRegistry",
    "AgentRecord",
]
