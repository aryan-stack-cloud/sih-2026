"""Scheduling primitives that sit between the belief state and the policy.

These modules hold the parts of the SCT scheduler that are *derived* rather than learned: revisit
deadlines from intercept-time theory, and the synchronisation guard. They contain no free
parameters that a reviewer cannot trace back to a mission requirement.
"""
