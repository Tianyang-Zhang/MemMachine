# Phase 14 Context

## Goal
Upgrade split execution from planner-only to planner + branch execution + one
live verification pass with optional reruns.

## User-locked Decisions
- Split verification pass can request branch reruns.
- Upper-level skill should have lower-level call context for verification.

## Requirement IDs
- SPLT-01
- SPLT-02
- CONT-01

