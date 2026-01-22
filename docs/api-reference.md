# VenomFlow API Reference

## GraphQL API

VenomFlow provides a GraphQL API for querying venom peptide data with flexible field selection and real-time capabilities.

**Base URL**: `http://localhost:8000/graphql`

## Authentication

*Authentication is currently not implemented. Future versions will use JWT tokens.*

```graphql
# Future authentication header
Authorization: Bearer <token>
```

## Queries

### Get Peptide by ID

Retrieve a single peptide with all related information.

```graphql
query GetPeptide {
  peptide(id: "550e8400-e29b-41d4-a716-446655440000") {
    id
    uniprot_id
    sequence
    length
    name
    description
    organism {
      id
      name
      commonName
      taxonomyId
      lineage
    }
    properties {
      molecularWeight
      isoelectricPoint
      hydrophobicity
      netCharge
      instabilityIndex
      aliphaticIndex
    }
    bioactivities {
      id
      type
      target
      potency
      unit
      assayType
      reference
    }
  }
}
```

### List All Peptides

Retrieve multiple peptides with pagination.

```graphql
query ListPeptides {
  peptides(limit: 10, offset: 0) {
    id
    uniprot_id
    sequence
    length
    name
    organism {
      name
    }
  }
}
```

**Parameters**:
- `limit` (Int): Number of results to return (default: 10)
- `offset` (Int): Number of results to skip (default: 0)

### Search Peptides

Search peptides by various criteria.

```graphql
query SearchPeptides {
  searchPeptides(query: "neurotoxin") {
    id
    name
    sequence
    organism {
      name
    }
  }
}
```

**Parameters**:
- `query` (String): Search term for sequence or name

## Mutations

### Trigger Pipeline

Manually trigger a Dagster pipeline run.

```graphql
mutation TriggerPipeline {
  triggerPipeline(pipelineName: "venom_ingestion_pipeline") {
    success
    message
    id
  }
}
```

**Parameters**:
- `pipelineName` (String): Name of the pipeline to trigger

**Response**:
```json
{
  "data": {
    "triggerPipeline": {
      "success": true,
      "message": "Pipeline triggered successfully",
      "id": "run_123456"
    }
  }
}
```

### Update Peptide Annotation

Update annotation for a specific peptide.

```graphql
mutation UpdateAnnotation {
  updatePeptideAnnotation(
    peptideId: "550e8400-e29b-41d4-a716-446655440000",
    annotation: "This peptide shows strong antimicrobial activity"
  ) {
    success
    message
    id
  }
}
```

## Subscriptions

### Pipeline Updates

Subscribe to real-time pipeline execution updates.

```graphql
subscription PipelineUpdates {
  pipelineUpdates(pipelineName: "venom_ingestion_pipeline") {
    pipelineName
    status
    progress
  }
}
```

**Response Stream**:
```json
{
  "data": {
    "pipelineUpdates": {
      "pipelineName": "venom_ingestion_pipeline",
      "status": "running",
      "progress": 0.5
    }
  }
}
```

## Types

### Organism

```graphql
type Organism {
  id: String!
  name: String!
  commonName: String
  taxonomyId: Int!
  lineage: String
}
```

### Peptide

```graphql
type Peptide {
  id: String!
  uniprotId: String!
  sequence: String!
  length: Int!
  name: String
  description: String
  organism: Organism
  properties: Properties
  bioactivities: [Bioactivity!]!
}
```

### Properties

```graphql
type Properties {
  molecularWeight: Float
  isoelectricPoint: Float
  hydrophobicity: Float
  netCharge: Float
  instabilityIndex: Float
  aliphaticIndex: Float
  helixFraction: Float
  turnFraction: Float
  sheetFraction: Float
}
```

### Bioactivity

```graphql
type Bioactivity {
  id: String!
  type: String!
  target: String
  potency: Float
  unit: String
  assayType: String
  reference: String
}
```

## Error Handling

GraphQL errors follow the standard format:

```json
{
  "errors": [
    {
      "message": "Peptide not found",
      "locations": [{"line": 2, "column": 3}],
      "path": ["peptide"]
    }
  ],
  "data": {
    "peptide": null
  }
}
```

## Rate Limiting

*Rate limiting is not currently implemented. Future versions will include:*

- 1000 requests per hour per IP
- 100 requests per minute per IP
- Custom limits for authenticated users

## GraphQL Playground

Interactive GraphQL playground is available at:

`http://localhost:8000/graphql`

The playground provides:
- Schema documentation
- Query autocomplete
- Query history
- Variable support

## REST Endpoints

### Health Check

```
GET /health
```

**Response**:
```json
{
  "status": "healthy"
}
```

### Root

```
GET /
```

**Response**:
```json
{
  "message": "VenomFlow API",
  "version": "1.0.0",
  "graphql": "/graphql"
}
```

## Client Examples

### Python with `gql`

```python
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

transport = RequestsHTTPTransport(url="http://localhost:8000/graphql")
client = Client(transport=transport, fetch_schema_from_transport=True)

query = gql("""
    query {
        peptides(limit: 5) {
            id
            name
            sequence
        }
    }
""")

result = client.execute(query)
print(result)
```

### JavaScript with `graphql-request`

```javascript
import { request, gql } from 'graphql-request'

const query = gql`
  query {
    peptides(limit: 5) {
      id
      name
      sequence
    }
  }
`

request('http://localhost:8000/graphql', query)
  .then(data => console.log(data))
  .catch(error => console.error(error))
```

### cURL

```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ peptides(limit: 5) { id name sequence } }"
  }'
```

## Best Practices

1. **Use Field Selection**: Only request fields you need
2. **Implement Pagination**: Use limit/offset for large datasets
3. **Cache Responses**: Cache frequently accessed data
4. **Handle Errors**: Always check for errors in responses
5. **Use Variables**: Pass dynamic values as variables, not in query string
6. **Batch Queries**: Combine multiple queries in one request when possible
