"""Supported SDK exports; all validation executes the repository contracts.

This facade contains no owner, adapter, runtime, or duplicated validator.
Raw fusion modules additionally contain application convenience builders whose
runtime dependencies are deliberately outside this lightweight distribution.
See public-api.json for the supported surface and explicit limitations.
"""
from fusion.contracts import AtomRef, ContractError
from fusion.ports import AtomEnvelope, Mutation
from fusion.registry import Descriptor, Requirement, resolve, selection_token
from fusion.preview_client import AtomFeedClient, Endpoint, retry_classification
from fusion.preview_handles import (
    PROFILE as HANDLE_PROFILE, Kind, Target, MemoryTarget, TaskTarget,
    ResultTarget, HandleEnvelope, ParsedHandle, parse, target, derive, make,
    envelope,
)
from fusion.preview_tools import (
    PROFILE as TOOL_PROFILE, VOCABULARY, Argument, ToolDescriptor, Catalogue,
    SessionAuthority, context_tools,
)

__all__ = (
    'AtomRef', 'ContractError', 'AtomEnvelope', 'Mutation', 'Descriptor',
    'Requirement', 'resolve', 'selection_token', 'AtomFeedClient', 'Endpoint',
    'retry_classification', 'HANDLE_PROFILE', 'Kind', 'Target', 'MemoryTarget',
    'TaskTarget', 'ResultTarget', 'HandleEnvelope', 'ParsedHandle', 'parse',
    'target', 'derive', 'make', 'envelope', 'TOOL_PROFILE', 'VOCABULARY',
    'Argument', 'ToolDescriptor', 'Catalogue', 'SessionAuthority',
    'context_tools',
)
