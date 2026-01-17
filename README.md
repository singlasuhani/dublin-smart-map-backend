# Dublin City Facilities API

Flask REST API for querying the Dublin City facilities knowledge graph stored in GraphDB.

## Features

- ✅ RESTful endpoints for facilities data
- ✅ SPARQL query generation and execution
- ✅ GeoJSON output for map integration
- ✅ Safe parameter handling
- ✅ CORS enabled for frontend access
- ✅ Comprehensive error handling

## Prerequisites

- Python 3.8+
- GraphDB running on `http://localhost:7200`
- Repository named `facilities` with data loaded

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Configuration

Edit `app.py` to configure GraphDB connection:

```python
GRAPHDB_URL = "http://localhost:7200/repositories/facilities"
```

## Running the API

```bash
# Development mode
python app.py

# Production mode (using gunicorn)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

The API will be available at `http://localhost:5000`

## API Endpoints

### Health Check
```
GET /health
```
Returns API and GraphDB connection status.

**Response:**
```json
{
  "status": "healthy",
  "graphdb": "connected"
}
```

---

### Get All Committee Areas
```
GET /areas
```
Returns list of all committee areas with facility counts.

**Response:**
```json
[
  {
    "id": "central",
    "name": "CENTRAL",
    "uri": "http://example.org/dcc/facilities#Central",
    "facilityCount": 1249
  },
  ...
]
```

---

### Get All Facility Types
```
GET /facility-types
```
Returns list of all facility types with counts.

**Response:**
```json
[
  {
    "id": "park",
    "name": "Park",
    "uri": "http://example.org/dcc/facilities#Park",
    "facilityCount": 90
  },
  ...
]
```

---

### Get Facilities (with filters)
```
GET /facilities?area={area_id}&type={type_id}
```

**Parameters:**
- `area` (optional): Committee area ID (`central`, `north-central`, etc.)
- `type` (optional): Facility type ID (`park`, `library`, `toilet`, etc.)

**Response:** GeoJSON FeatureCollection
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-6.263325, 53.383262]
      },
      "properties": {
        "uri": "http://...",
        "name": "Albert College Park",
        "address": "",
        "area": "NORTH CENTRAL",
        "type": "Park"
      }
    }
  ],
  "metadata": {
    "count": 90,
    "filters": {
      "area": "north-central",
      "type": "park"
    }
  }
}
```

---

### Get Statistics
```
GET /stats?area={area_id}
```

**Parameters:**
- `area` (optional): Committee area ID

**Response:**
```json
{
  "area": "central",
  "total": 1249,
  "byType": [
    {
      "type": "Public Bin",
      "count": 957
    },
    {
      "type": "Bike Parking",
      "count": 238
    },
    ...
  ]
}
```

---

### Search Facilities
```
GET /search?q={query}&limit={limit}
```

**Parameters:**
- `q` (required): Search query (partial name match)
- `limit` (optional): Maximum results (default: 50)

**Response:**
```json
{
  "query": "library",
  "count": 24,
  "results": [
    {
      "uri": "http://...",
      "name": "Central Library",
      "type": "Library",
      "area": "CENTRAL",
      "coordinates": {
        "lat": 53.35007,
        "lon": -6.26540
      }
    }
  ]
}
```

---

### Get Facility Details
```
GET /facility/{facility_id}
```

**Parameters:**
- `facility_id`: Full URI or facility ID

**Response:**
```json
{
  "uri": "http://...",
  "name": "Central Library",
  "type": "Library",
  "area": "CENTRAL",
  "coordinates": {
    "lat": 53.35007,
    "lon": -6.26540
  },
  "address": "",
  "url": "https://...",
  "sourceDataset": "libraries_clean.csv"
}
```

---

## Parameter Reference

### Area IDs
- `north-central` - North Central
- `north-west` - North West
- `central` - Central
- `south-central` - South Central
- `south-east` - South East

### Facility Type IDs
- `park` - Parks
- `library` - Libraries
- `toilet` - Public Toilets
- `bike-parking` - Bike Parking
- `community-centre` - Community Centres
- `water-fountain` - Water Fountains
- `public-bin` - Public Bins
- `recycling-centre` - Recycling Centres

---

## Example Usage

### JavaScript/Fetch
```javascript
// Get all parks in Central area
fetch('http://localhost:5000/facilities?area=central&type=park')
  .then(res => res.json())
  .then(data => {
    console.log(`Found ${data.metadata.count} parks`);
    // data.features is GeoJSON ready for Leaflet/Mapbox
  });

// Search for facilities
fetch('http://localhost:5000/search?q=library')
  .then(res => res.json())
  .then(data => {
    console.log(`Found ${data.count} results`);
  });
```

### Python/Requests
```python
import requests

# Get statistics for South East area
response = requests.get('http://localhost:5000/stats?area=south-east')
stats = response.json()
print(f"Total facilities: {stats['total']}")

# Get all areas
areas = requests.get('http://localhost:5000/areas').json()
for area in areas:
    print(f"{area['name']}: {area['facilityCount']} facilities")
```

### cURL
```bash
# Health check
curl http://localhost:5000/health

# Get all parks
curl "http://localhost:5000/facilities?type=park"

# Get facilities in Central area
curl "http://localhost:5000/facilities?area=central"

# Search
curl "http://localhost:5000/search?q=street"
```

---

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200` - Success
- `400` - Bad Request (invalid parameters)
- `404` - Not Found (facility doesn't exist)
- `500` - Internal Server Error (GraphDB connection issue)
- `503` - Service Unavailable (GraphDB not reachable)

**Error Response Format:**
```json
{
  "error": "Error message description"
}
```

---

## Security Considerations

For production deployment:

1. **Add authentication**: Use Flask-JWT or similar
2. **Rate limiting**: Use Flask-Limiter
3. **Input validation**: Add stricter parameter validation
4. **HTTPS**: Deploy behind reverse proxy (nginx)
5. **Environment variables**: Move configuration to `.env` file

---

## Testing

```bash
# Test health endpoint
curl http://localhost:5000/health

# Test areas endpoint
curl http://localhost:5000/areas

# Test facilities with filters
curl "http://localhost:5000/facilities?area=central&type=park"
```

---

## Troubleshooting

### "GraphDB not connected" error
- Ensure GraphDB is running on `http://localhost:7200`
- Verify repository name is `facilities`
- Check data is loaded in GraphDB

### Empty results
- Verify data is loaded: Check GraphDB Workbench
- Test SPARQL queries directly in GraphDB
- Check parameter values match expected IDs

### CORS errors
- CORS is enabled by default
- For custom origins, modify `CORS(app)` in `app.py`

---

## Development

### Adding New Endpoints

1. Define route in `app.py`
2. Build SPARQL query with safe parameters
3. Use `execute_sparql()` to query GraphDB
4. Parse results with `parse_bindings()`
5. Return clean JSON response

### Example:
```python
@app.route('/my-endpoint', methods=['GET'])
def my_endpoint():
    query = """
    PREFIX ex: <http://example.org/dcc/facilities#>
    SELECT ?s ?p ?o
    WHERE { ?s ?p ?o }
    LIMIT 10
    """
    
    results = execute_sparql(query)
    bindings = parse_bindings(results)
    
    return jsonify(bindings)
```

---

## License

MIT License - See LICENSE file for details
