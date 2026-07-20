# Ponytail Review Profile

Use for every non-documentation diff. This profile reviews only unnecessary
complexity; combine it with the normal correctness, security, test, and
architecture profiles.

## Checklist

- The change is required by the current task rather than a speculative need.
- Existing helpers, types, and patterns are reused instead of reimplemented.
- Standard-library or native-platform features replace equivalent custom code.
- No new dependency was added for behavior already covered by a few clear
  lines or an installed dependency.
- No interface, factory, layer, option, or configuration exists for a single
  hypothetical future use.
- No dead flexibility, boilerplate, duplicate path, or scaffolding remains.
- The same behavior cannot be expressed more directly without hiding intent.
- Bug fixes address the shared root cause rather than one named symptom.
- Required validation, data-loss protection, security, accessibility, and the
  smallest meaningful regression check remain intact.

## Finding Format

Prefix the title with one of:

- `delete:` nothing should replace the code.
- `stdlib:` name the standard-library replacement.
- `native:` name the platform feature.
- `yagni:` name the speculative abstraction or flexibility.
- `shrink:` state the smaller equivalent.

Every finding must use `profile: "ponytail"`. All surviving Ponytail findings
must be resolved before commit, regardless of severity.

## Severity

- Critical: Complexity actively bypasses or obscures a safety boundary.
- Major: A dependency, abstraction, or duplicate implementation materially
  increases ownership or creates divergent behavior.
- Minor: A safe deletion or direct simplification remains.

