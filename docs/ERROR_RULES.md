# ERROR_RULES — Auto-Learned Forbidden Rules

> Auto-maintained by ErrorRulesEngine (TASK-036).
> Generated: 2026-06-11

No forbidden rules yet. Rules are auto-generated when
the same error pattern occurs >= 3 times.

---

## How Rules Work

1. Each time a CLI command fails, the error pattern is extracted
2. When the same pattern occurs >= 3 times, a forbidden rule is auto-generated
3. Active rules are injected into Planner prompts to prevent recurrence
4. Rules can be exported/imported for cross-session persistence

## Valid Part Types

`box`, `cylinder`, `sphere`, `cone`, `torus`, `wedge`, `helix`, `ellipsoid`, `spiral`

## Valid Planes

`XY`, `XZ`, `YZ`
