## printables-feeds

Reverse-engineered GraphQL API for Printables.com. Prusa, please bless this and provide official API documentation!

View feeds at https://dyn.tedder.me/rss/printables/

---

## API Notes

**Endpoint:** `https://api.printables.com/graphql/`

**Required headers:**
```
content-type: application/json
graphql-client-version: v1.0.96
origin: https://www.printables.com
```

The `graphql-client-version` header appears to be required — requests without it may fail or return errors.

No API key or authentication token is needed for read-only public data. The code has commented-out `authorization` and `client-uid` headers captured during reverse-engineering, but they are not required.

### Introspection

The API supports GraphQL introspection, so you can discover available queries:

```bash
curl -s -X POST 'https://api.printables.com/graphql/' \
  -H 'content-type: application/json' \
  -H 'graphql-client-version: v1.0.96' \
  -H 'origin: https://www.printables.com' \
  -d '{"query":"{ __schema { queryType { fields { name } } } }"}'
```

---

## Getting Models for a Specific User

Fetching a user's models is a two-step process: resolve the handle to a numeric user ID, then query models filtered by that ID.

### Step 1: Resolve handle to user ID

Use `searchUsers2` with the username as a query string. The result is paginated under `items`.

```bash
curl -s -X POST 'https://api.printables.com/graphql/' \
  -H 'content-type: application/json' \
  -H 'graphql-client-version: v1.0.96' \
  -H 'origin: https://www.printables.com' \
  -d '{
    "operationName": "SearchUsers",
    "query": "query SearchUsers($query: String!) { searchUsers2(query: $query, limit: 5) { items { id publicUsername handle } } }",
    "variables": {"query": "CADGuy"}
  }'
```

Response:
```json
{
  "data": {
    "searchUsers2": {
      "items": [
        {"id": "251219", "publicUsername": "CADGUY88",  "handle": "CADGUY88"},
        {"id": "218560", "publicUsername": "CAD-Guy",   "handle": "CADGuy"},
        ...
      ]
    }
  }
}
```

Match the result where `handle` equals the target (case-insensitive). For `@CADGuy`, the ID is `218560`.

Note: `publicUsername` is the display name; `handle` is the URL slug used in `printables.com/@handle`.

### Step 2: Fetch models by user ID

Pass `userId` to the `morePrints` query. Omit `publishedDateLimitDays` to get all models, not just recent ones.

```bash
curl -s -X POST 'https://api.printables.com/graphql/' \
  -H 'content-type: application/json' \
  -H 'graphql-client-version: v1.0.96' \
  -H 'origin: https://www.printables.com' \
  -d '{
    "operationName": "ModelList",
    "query": "query ModelList($limit: Int!, $cursor: String, $userId: ID, $ordering: String) { models: morePrints(limit: $limit, cursor: $cursor, userId: $userId, ordering: $ordering) { cursor items { id name slug firstPublish downloadCount likesCount } } }",
    "variables": {
      "limit": 36,
      "cursor": null,
      "userId": "218560",
      "ordering": "-first_publish"
    }
  }'
```

### Step 3: Paginate

The response includes a `cursor` string. Pass it as `cursor` in subsequent requests to get the next page. When `cursor` is `null` in the response, you've reached the end.

```json
{
  "data": {
    "models": {
      "cursor": "MjAyMy0wNy0yM...",
      "items": [ ... ]
    }
  }
}
```

### Known `ordering` values

| Value | Description |
|---|---|
| `-first_publish` | Newest first |
| `-likes_count_30_days` | Trending (30-day likes) |
| `-rating_avg` | Top rated |
| `-download_count_30_days` | Most downloaded (30 days) |

### Notable `morePrints` filter parameters

| Parameter | Type | Description |
|---|---|---|
| `userId` | ID | Filter to a specific user's models |
| `categoryId` | ID | Filter by category |
| `publishedDateLimitDays` | Int | Only return models published within N days — omit for all-time |
| `featured` | Boolean | Only featured models |
| `paid` | PaidEnum | Filter free vs. paid models |
| `cursor` | String | Pagination cursor from previous response |
