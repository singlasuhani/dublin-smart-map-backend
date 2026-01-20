"""
Flask API for Dublin City Facilities Knowledge Graph
Connects to GraphDB and provides REST endpoints for querying facilities data.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from typing import Optional, Dict, List, Any
import shapely.wkt
from shapely.geometry import mapping
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# GraphDB Configuration
GRAPHDB_URL = os.environ.get("GRAPHDB_URL", "http://DESKTOP-FV6EDVG:7200/repositories/city_facilities")
NAMESPACE = "http://example.org/dcc/facilities#"

# Mapping of user-friendly IDs to URIs
AREA_MAPPING = {
    "north-central": "ex:NorthCentral",
    "north-west": "ex:NorthWest",
    "central": "ex:Central",
    "south-central": "ex:SouthCentral",
    "south-east": "ex:SouthEast",
}

TYPE_MAPPING = {
    "park": "ex:Park",
    "library": "ex:Library",
    "toilet": "ex:Toilet",
    "bike-parking": "ex:BikeParking",
    "community-centre": "ex:CommunityCentre",
    "water-fountain": "ex:WaterFountain",
    "public-bin": "ex:PublicBin",
    "recycling-centre": "ex:RecyclingCentre",
    "garda-station": "ex:GardaStation",
    "disabled-parking": "ex:DisabledParking",
    "swimming-pool": "ex:SwimmingPool",
    "place-of-worship": "ex:PlaceOfWorship",
}

def to_kebab_case(s: str) -> str:
    """Convert CamelCase or PascalCase to kebab-case."""
    return ''.join(['-' + c.lower() if c.isupper() else c for c in s]).lstrip('-')


def execute_sparql(query: str) -> Dict[str, Any]:
    """
    Execute a SPARQL query against GraphDB.
    
    Args:
        query: SPARQL query string
        
    Returns:
        JSON response from GraphDB
    """
    try:
        response = requests.post(
            GRAPHDB_URL,
            data=query,
            headers={
                "Content-Type": "application/sparql-query",
                "Accept": "application/sparql-results+json"
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"GraphDB query error: {e}")
        raise


def parse_bindings(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse SPARQL JSON results into clean Python dictionaries.
    
    Args:
        results: Raw SPARQL JSON results
        
    Returns:
        List of dictionaries with clean values
    """
    bindings = results.get("results", {}).get("bindings", [])
    parsed = []
    
    for binding in bindings:
        row = {}
        for key, value in binding.items():
            row[key] = value.get("value")
        parsed.append(row)
    
    return parsed


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        # Test GraphDB connection
        query = "SELECT * WHERE { ?s ?p ?o } LIMIT 1"
        execute_sparql(query)
        return jsonify({"status": "healthy", "graphdb": "connected"})
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 503


@app.route('/areas', methods=['GET'])
def get_areas():
    """
    Get list of all committee areas.
    
    Returns:
        JSON array of areas with id and name
    """
    query = """
    PREFIX ex: <http://example.org/dcc/facilities#>
    PREFIX schema: <http://schema.org/>
    
    SELECT ?uri ?name (COUNT(?facility) AS ?count)
    WHERE {
      ?uri a ex:CommitteeArea ;
           schema:name ?name .
      
      OPTIONAL {
        ?facility ex:inCommitteeArea ?uri .
      }
    }
    GROUP BY ?uri ?name
    ORDER BY ?name
    """
    
    try:
        results = execute_sparql(query)
        bindings = parse_bindings(results)
        
        areas = []
        for row in bindings:
            # Extract URI local name for ID
            uri = row['uri']
            area_id_raw = uri.split('#')[-1]
            
            areas.append({
                "id": to_kebab_case(area_id_raw),
                "name": row['name'],
                "uri": uri,
                "facilityCount": int(row.get('count', 0))
            })
        
        return jsonify(areas)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/facility-types', methods=['GET'])
def get_facility_types():
    """
    Get list of all facility types.
    
    Returns:
        JSON array of facility types with id, name, and count
    """
    query = """
    PREFIX ex: <http://example.org/dcc/facilities#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?uri ?name (COUNT(?facility) AS ?count)
    WHERE {
      ?uri a ex:FacilityType ;
           rdfs:label ?name .
      
      OPTIONAL {
        ?facility ex:hasFacilityType ?uri .
      }
    }
    GROUP BY ?uri ?name
    ORDER BY ?name
    """
    
    try:
        results = execute_sparql(query)
        bindings = parse_bindings(results)
        
        types = []
        for row in bindings:
            uri = row['uri']
            type_id_raw = uri.split('#')[-1]
            
            types.append({
                "id": to_kebab_case(type_id_raw),
                "name": row['name'],
                "uri": uri,
                "facilityCount": int(row.get('count', 0))
            })
        
        return jsonify(types)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/facilities', methods=['GET'])
def get_facilities():
    """
    Get facilities filtered by area and/or type.
    
    Query Parameters:
        area: Committee area ID (e.g., 'central', 'north-central')
        type: Facility type ID (e.g., 'park', 'library')
        
    Returns:
        GeoJSON FeatureCollection of facilities
    """
    area_id = request.args.get('area')
    type_ids = request.args.getlist('type')
    
    # Build SPARQL query with optional filters
    area_filter = ""
    type_filter = ""
    
    if area_id:
        area_uri = AREA_MAPPING.get(area_id)
        if area_uri:
            area_filter = f"VALUES ?area {{ {area_uri} }}"
    
    if type_ids:
        # Filter out invalid type IDs and get their URIs
        type_uris = [TYPE_MAPPING.get(tid) for tid in type_ids if TYPE_MAPPING.get(tid)]
        if type_uris:
            # Create a space-separated string of URIs for the VALUES clause
            uris_str = " ".join(type_uris)
            type_filter = f"VALUES ?type {{ {uris_str} }}"
    
    query = f"""
    PREFIX ex: <http://example.org/dcc/facilities#>
    PREFIX schema: <http://schema.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX geo: <http://www.opengis.net/ont/geosparql#>
    
    SELECT ?uri ?name ?lat ?lon ?address ?areaName ?typeName ?wkt
    WHERE {{
      {area_filter}
      {type_filter}
      
      ?uri a ex:Facility ;
           schema:name ?name ;
           ex:latitude ?lat ;
           ex:longitude ?lon ;
           ex:inCommitteeArea ?area ;
           ex:hasFacilityType ?type .
      
      ?area schema:name ?areaName .
      ?type rdfs:label ?typeName .
      
      OPTIONAL {{ ?uri schema:address ?address }}
      OPTIONAL {{
        ?uri geo:hasGeometry ?geo .
        ?geo geo:asWKT ?wkt .
      }}
    }}
    ORDER BY ?name
    """
    
    try:
        results = execute_sparql(query)
        bindings = parse_bindings(results)
        
        # Helper to parse WKT
        def parse_wkt_poly(wkt_str):
            try:
                # Use shapely for robust parsing
                geom = shapely.wkt.loads(wkt_str)
                return mapping(geom)
            except Exception as e:
                # print(f"WKT Parse Error: {e}")
                return None
            return None

        # Convert to GeoJSON FeatureCollection
        features = []
        for row in bindings:
            geometry = None
            if row.get('wkt'):
                # Try parsing WKT
                geometry = parse_wkt_poly(row['wkt'])
            
            # Fallback to Point if no Polygon/WKT or parse failed
            if not geometry:
                geometry = {
                    "type": "Point",
                    "coordinates": [
                        float(row['lon']),
                        float(row['lat'])
                    ]
                }

            feature = {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "uri": row['uri'],
                    "name": row['name'],
                    "address": row.get('address', ''),
                    "area": row['areaName'],
                    "type": row['typeName']
                }
            }
            features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "count": len(features),
                "filters": {
                    "area": area_id,
                    "type": type_ids
                }
            }
        }
        
        return jsonify(geojson)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/stats', methods=['GET'])
def get_stats():
    """
    Get facility statistics for an area.
    
    Query Parameters:
        area: Committee area ID (optional)
        
    Returns:
        JSON object with facility counts by type
    """
    area_id = request.args.get('area')
    
    # Build query with optional area filter
    area_filter = ""
    if area_id:
        area_uri = AREA_MAPPING.get(area_id)
        if area_uri:
            area_filter = f"FILTER(?area = {area_uri})"
    
    query = f"""
    PREFIX ex: <http://example.org/dcc/facilities#>
    PREFIX schema: <http://schema.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?typeName (COUNT(?facility) AS ?count)
    WHERE {{
      ?facility a ex:Facility ;
                ex:inCommitteeArea ?area ;
                ex:hasFacilityType ?type .
      
      ?type rdfs:label ?typeName .
      
      {area_filter}
    }}
    GROUP BY ?typeName
    ORDER BY DESC(?count)
    """
    
    try:
        results = execute_sparql(query)
        bindings = parse_bindings(results)
        
        stats = {
            "area": area_id,
            "total": 0,
            "byType": []
        }
        
        for row in bindings:
            count = int(row['count'])
            stats['total'] += count
            stats['byType'].append({
                "type": row['typeName'],
                "count": count
            })
        
        return jsonify(stats)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/search', methods=['GET'])
def search_facilities():
    """
    Search facilities by name.
    
    Query Parameters:
        q: Search query (partial name match)
        limit: Maximum results (default: 50)
        
    Returns:
        JSON array of matching facilities
    """
    search_term = request.args.get('q', '').lower()
    limit = request.args.get('limit', 50)
    
    if not search_term:
        return jsonify({"error": "Search query 'q' is required"}), 400
    
    query = f"""
    PREFIX ex: <http://example.org/dcc/facilities#>
    PREFIX schema: <http://schema.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?uri ?name ?typeName ?areaName ?lat ?lon
    WHERE {{
      ?uri a ex:Facility ;
           schema:name ?name ;
           ex:latitude ?lat ;
           ex:longitude ?lon ;
           ex:hasFacilityType ?type ;
           ex:inCommitteeArea ?area .
      
      ?type rdfs:label ?typeName .
      ?area schema:name ?areaName .
      
      FILTER(CONTAINS(LCASE(?name), "{search_term}"))
    }}
    ORDER BY ?name
    LIMIT {limit}
    """
    
    try:
        results = execute_sparql(query)
        bindings = parse_bindings(results)
        
        facilities = []
        for row in bindings:
            facilities.append({
                "uri": row['uri'],
                "name": row['name'],
                "type": row['typeName'],
                "area": row['areaName'],
                "coordinates": {
                    "lat": float(row['lat']),
                    "lon": float(row['lon'])
                }
            })
        
        return jsonify({
            "query": search_term,
            "count": len(facilities),
            "results": facilities
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/facility/<path:facility_id>', methods=['GET'])
def get_facility_details(facility_id):
    """
    Get detailed information for a specific facility.
    
    Args:
        facility_id: Facility URI or ID
        
    Returns:
        JSON object with facility details
    """
    # Construct full URI if only ID provided
    if not facility_id.startswith('http'):
        facility_uri = f"<{NAMESPACE}facility/{facility_id}>"
    else:
        facility_uri = f"<{facility_id}>"
    
    query = f"""
    PREFIX ex: <http://example.org/dcc/facilities#>
    PREFIX schema: <http://schema.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX geo: <http://www.opengis.net/ont/geosparql#>
    
    SELECT ?name ?address ?url ?lat ?lon ?areaName ?typeName ?sourceDataset
    WHERE {{
      {facility_uri} schema:name ?name ;
                     ex:latitude ?lat ;
                     ex:longitude ?lon ;
                     ex:inCommitteeArea ?area ;
                     ex:hasFacilityType ?type .
      
      ?area schema:name ?areaName .
      ?type rdfs:label ?typeName .
      
      OPTIONAL {{ {facility_uri} schema:address ?address }}
      OPTIONAL {{ {facility_uri} schema:url ?url }}
      OPTIONAL {{ {facility_uri} ex:sourceDataset ?sourceDataset }}
    }}
    """
    
    try:
        results = execute_sparql(query)
        bindings = parse_bindings(results)
        
        if not bindings:
            return jsonify({"error": "Facility not found"}), 404
        
        row = bindings[0]
        facility = {
            "uri": facility_id if facility_id.startswith('http') else f"{NAMESPACE}facility/{facility_id}",
            "name": row['name'],
            "type": row['typeName'],
            "area": row['areaName'],
            "coordinates": {
                "lat": float(row['lat']),
                "lon": float(row['lon'])
            },
            "address": row.get('address', ''),
            "url": row.get('url', ''),
            "sourceDataset": row.get('sourceDataset', '')
        }
        
        return jsonify(facility)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/insights/missing', methods=['GET'])
def get_missing_facilities():
    """
    Find areas that lack a specific facility type.
    """
    type_id = request.args.get('type')
    if not type_id or type_id not in TYPE_MAPPING:
        return jsonify({"error": "Valid type_id is required"}), 400
    
    type_uri = TYPE_MAPPING[type_id]
    
    query = f"""
    PREFIX ex: <http://example.org/dcc/facilities#>
    PREFIX schema: <http://schema.org/>
    
    SELECT ?areaUri ?areaName
    WHERE {{
      ?areaUri a ex:CommitteeArea ;
               schema:name ?areaName .
      
      MINUS {{
        ?facility ex:inCommitteeArea ?areaUri ;
                  ex:hasFacilityType {type_uri} .
      }}
    }}
    ORDER BY ?areaName
    """
    
    try:
        results = execute_sparql(query)
        bindings = parse_bindings(results)
        
        areas = []
        for row in bindings:
            areas.append({
                "id": to_kebab_case(row['areaUri'].split('#')[-1]),
                "name": row['areaName']
            })
            
        return jsonify({
            "type": type_id,
            "missingIn": areas
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/insights/distribution', methods=['GET'])
def get_facility_distribution():
    """
    Get facility counts across all areas for a specific type to find lowest access.
    """
    type_id = request.args.get('type')
    if not type_id or type_id not in TYPE_MAPPING:
        return jsonify({"error": "Valid type_id is required"}), 400
    
    type_uri = TYPE_MAPPING[type_id]
    
    query = f"""
    PREFIX ex: <http://example.org/dcc/facilities#>
    PREFIX schema: <http://schema.org/>
    
    SELECT ?areaName (COUNT(?facility) AS ?count)
    WHERE {{
      ?areaUri a ex:CommitteeArea ;
               schema:name ?areaName .
      
      OPTIONAL {{
        ?facility ex:inCommitteeArea ?areaUri .
        ?facility ex:hasFacilityType {type_uri} .
      }}
    }}
    GROUP BY ?areaName
    ORDER BY ?count ASC
    """
    
    try:
        results = execute_sparql(query)
        bindings = parse_bindings(results)
        
        distribution = []
        for row in bindings:
            distribution.append({
                "area": row['areaName'],
                "count": int(row.get('count', 0))
            })
            
        return jsonify({
            "type": type_id,
            "distribution": distribution,
            "lowestAccess": distribution[:3]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("Starting Dublin City Facilities API...")
    print(f"GraphDB endpoint: {GRAPHDB_URL}")
    print("Available endpoints:")
    print("  GET /health - Health check")
    print("  GET /areas - List all committee areas")
    print("  GET /facility-types - List all facility types")
    print("  GET /facilities?area=...&type=... - Get facilities (GeoJSON)")
    print("  GET /stats?area=... - Get statistics")
    print("  GET /search?q=... - Search facilities by name")
    print("  GET /facility/<id> - Get facility details")
    print("\nStarting server on http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
