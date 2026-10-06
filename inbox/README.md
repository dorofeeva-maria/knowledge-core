# inbox/

Raw drop zone. Anything can land here — links, documents, pasted text, media, or files
dropped by external programs and browser extensions. Contents are **committed** (the core is
private), so every device sees them.

`close` (and the `inbox` skill) process what's here into the right modules, then clear it.
Anything still here at the next session start gets a stub in `ecosystem/todo/` from `kc todo`
and is offered in the todo walk-through.
