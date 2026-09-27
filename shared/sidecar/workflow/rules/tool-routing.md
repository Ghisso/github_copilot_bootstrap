# Tool Routing

Choose the narrowest tool that answers the question.

- Use a direct file read when you already know the path, or the person
  named a specific file.
- Use exact text search (for example `rg`) for literals: symbols, error
  text, configuration keys, and filenames.
- Use this client's own semantic or repository-search feature, when it has
  one, for broader questions such as "where is this implemented?" or
  "what else calls this function?".

Fall back in that order: try the direct read or exact search first: only
reach for semantic search when the first two leave a real gap. If this
client has no semantic search feature, direct reads and exact search are
enough on their own — that is not a blocker.

Read a file normally before you edit it. Git and the files on disk are
always the current truth; nothing you searched earlier overrides what is
actually in the repository now.

Do not reach for a search tool for a simple edit in a file you already
have open, for running a test or lint command, or for a secret,
credential, or otherwise protected file.
