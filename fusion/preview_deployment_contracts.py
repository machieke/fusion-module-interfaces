"""Pure identity of the opt-in synthetic single-node deployment contract."""
COMPOSITION='omega-single-node-developer-preview/1'

SUSTAINED_COMPOSITION='omega-single-node-sustained-preview/1'

# Pure selection identity is also used by the extracted Secret recipe. Importing
# the Search implementation here would make operator installation depend on E5/
# Chroma, even though that recipe only validates a profile and allocates tokens.
SEARCH_MAINTENANCE_PROFILE='bounded-derived-search-repair/1'
