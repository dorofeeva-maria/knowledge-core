# drafts/

One draft per open session: `<date>-<session8>.md`, the raw transcript (the human's messages
and the assistant's replies), appended by `kc` hooks in the background and **committed +
pushed** each time (the core is private), so nothing is lost on exit or a device switch.

`close` finalizes drafts into modules and clears them. Drafts still here at the next session
start get a stub in `ecosystem/todo/` from `kc todo` and are offered in the todo walk-through.
