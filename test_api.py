"""
Test script for Dublin City Facilities API
Tests all endpoints and verifies responses.
"""

import requests
import json
from typing import Dict, Any

# API Configuration
API_BASE_URL = "http://localhost:5000"

# ANSI color codes for pretty output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_test(name: str):
    """Print test name."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Testing: {name}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")


def print_success(message: str):
    """Print success message."""
    print(f"{GREEN}✓ {message}{RESET}")


def print_error(message: str):
    """Print error message."""
    print(f"{RED}✗ {message}{RESET}")


def print_info(message: str):
    """Print info message."""
    print(f"{YELLOW}ℹ {message}{RESET}")


def print_response(data: Any, limit: int = 3):
    """Print response data (limited)."""
    if isinstance(data, list):
        print(f"  Response: {len(data)} items")
        for i, item in enumerate(data[:limit]):
            print(f"    [{i+1}] {json.dumps(item, indent=6)}")
        if len(data) > limit:
            print(f"    ... and {len(data) - limit} more")
    elif isinstance(data, dict):
        print(f"  Response: {json.dumps(data, indent=2)}")
    else:
        print(f"  Response: {data}")


def test_health():
    """Test health check endpoint."""
    print_test("Health Check")
    
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"API is healthy: {data}")
            
            if data.get('graphdb') == 'connected':
                print_success("GraphDB connection successful")
            else:
                print_error("GraphDB connection failed")
            
            return True
        else:
            print_error(f"Health check failed: {response.status_code}")
            print_info(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to API. Is it running on http://localhost:5000?")
        print_info("Start the API with: python api/app.py")
        return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def test_areas():
    """Test areas endpoint."""
    print_test("Get All Areas")
    
    try:
        response = requests.get(f"{API_BASE_URL}/areas")
        
        if response.status_code == 200:
            areas = response.json()
            print_success(f"Retrieved {len(areas)} areas")
            print_response(areas)
            
            # Validate structure
            if areas and isinstance(areas, list):
                area = areas[0]
                required_fields = ['id', 'name', 'uri', 'facilityCount']
                if all(field in area for field in required_fields):
                    print_success("Area structure is valid")
                else:
                    print_error(f"Missing fields. Expected: {required_fields}")
            
            return True
        else:
            print_error(f"Failed: {response.status_code}")
            print_info(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def test_facility_types():
    """Test facility types endpoint."""
    print_test("Get All Facility Types")
    
    try:
        response = requests.get(f"{API_BASE_URL}/facility-types")
        
        if response.status_code == 200:
            types = response.json()
            print_success(f"Retrieved {len(types)} facility types")
            print_response(types)
            
            # Validate structure
            if types and isinstance(types, list):
                ftype = types[0]
                required_fields = ['id', 'name', 'uri', 'facilityCount']
                if all(field in ftype for field in required_fields):
                    print_success("Facility type structure is valid")
                else:
                    print_error(f"Missing fields. Expected: {required_fields}")
            
            return True
        else:
            print_error(f"Failed: {response.status_code}")
            print_info(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def test_facilities_no_filter():
    """Test facilities endpoint without filters."""
    print_test("Get All Facilities (No Filter)")
    
    try:
        response = requests.get(f"{API_BASE_URL}/facilities")
        
        if response.status_code == 200:
            geojson = response.json()
            print_success(f"Retrieved GeoJSON with {geojson['metadata']['count']} features")
            
            # Validate GeoJSON structure
            if geojson.get('type') == 'FeatureCollection':
                print_success("Valid GeoJSON FeatureCollection")
                
                if geojson['features']:
                    feature = geojson['features'][0]
                    print_info("Sample feature:")
                    print_response(feature, limit=1)
                    
                    # Check geometry
                    if feature['geometry']['type'] == 'Point':
                        coords = feature['geometry']['coordinates']
                        print_success(f"Valid Point geometry: [{coords[0]}, {coords[1]}]")
                    
                    # Check properties
                    props = feature['properties']
                    required_props = ['name', 'area', 'type']
                    if all(prop in props for prop in required_props):
                        print_success("Feature properties are valid")
            
            return True
        else:
            print_error(f"Failed: {response.status_code}")
            print_info(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def test_facilities_with_filters():
    """Test facilities endpoint with filters."""
    print_test("Get Facilities with Filters (area=central, type=park)")
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/facilities",
            params={'area': 'central', 'type': 'park'}
        )
        
        if response.status_code == 200:
            geojson = response.json()
            count = geojson['metadata']['count']
            print_success(f"Retrieved {count} parks in Central area")
            
            if count > 0:
                print_info("Sample facilities:")
                for i, feature in enumerate(geojson['features'][:3]):
                    props = feature['properties']
                    print(f"    {i+1}. {props['name']} ({props['type']}, {props['area']})")
            else:
                print_info("No parks found in Central area")
            
            return True
        else:
            print_error(f"Failed: {response.status_code}")
            print_info(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def test_stats():
    """Test stats endpoint."""
    print_test("Get Statistics (area=south-east)")
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/stats",
            params={'area': 'south-east'}
        )
        
        if response.status_code == 200:
            stats = response.json()
            print_success(f"Total facilities in South East: {stats['total']}")
            
            print_info("Breakdown by type:")
            for item in stats['byType'][:5]:
                print(f"    {item['type']}: {item['count']}")
            
            if len(stats['byType']) > 5:
                print(f"    ... and {len(stats['byType']) - 5} more types")
            
            return True
        else:
            print_error(f"Failed: {response.status_code}")
            print_info(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def test_search():
    """Test search endpoint."""
    print_test("Search Facilities (q=library)")
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/search",
            params={'q': 'library', 'limit': 5}
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Found {data['count']} results for '{data['query']}'")
            
            if data['results']:
                print_info("Results:")
                for i, result in enumerate(data['results'][:5]):
                    print(f"    {i+1}. {result['name']} ({result['type']}, {result['area']})")
            
            return True
        else:
            print_error(f"Failed: {response.status_code}")
            print_info(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def run_all_tests():
    """Run all API tests."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Dublin City Facilities API - Test Suite{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"API URL: {API_BASE_URL}")
    
    tests = [
        ("Health Check", test_health),
        ("Areas Endpoint", test_areas),
        ("Facility Types Endpoint", test_facility_types),
        ("Facilities Endpoint (No Filter)", test_facilities_no_filter),
        ("Facilities Endpoint (With Filters)", test_facilities_with_filters),
        ("Statistics Endpoint", test_stats),
        ("Search Endpoint", test_search),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print_error(f"Test crashed: {e}")
            results.append((name, False))
    
    # Summary
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Test Summary{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"  {status} - {name}")
    
    print(f"\n{BLUE}{'='*60}{RESET}")
    if passed == total:
        print(f"{GREEN}All tests passed! ({passed}/{total}){RESET}")
    else:
        print(f"{YELLOW}Some tests failed: {passed}/{total} passed{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
