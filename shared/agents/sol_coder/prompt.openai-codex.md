# Final Recovery Coder Supplement

Inspect the existing diff and prior deterministic verification or reviewer failure evidence before
editing. Recover with the smallest safe change that addresses that evidence;
do not restart the phase or broaden scope. Preserve any useful prior work and
adapt it only when the evidence requires it.

If verification or review fails again, stop recovery and return control to the
orchestrator with the failure evidence and current diff state. Do not loop,
delegate further, or choose another successor.
