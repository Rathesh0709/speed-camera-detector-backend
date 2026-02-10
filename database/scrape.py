"""
Comprehensive Tamil Nadu Speed Camera Scraper
Uses smaller grid cells to capture ALL cameras like the map interface does
"""

import requests
import json
from typing import Dict, List, Any, Optional, Set
import time
from datetime import datetime


class ComprehensiveTNCameraScraper:
    """
    Improved scraper that uses smaller viewport bounds to get all cameras
    The map shows more cameras because it requests data for smaller areas at a time
    """
    
    def __init__(self):
        self.base_url = "https://www.scdb.info"
        self.api_endpoint = f"{self.base_url}/karte/"
        self.session = requests.Session()
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://www.scdb.info',
            'Referer': 'https://www.scdb.info/en/karte/',
            'X-Requested-With': 'XMLHttpRequest',
        })
        
        self.all_cameras = {}  # Use dict to avoid duplicates by ID
    
    def get_cameras_by_bounds(
        self, 
        lat_min: float, 
        lat_max: float, 
        lng_min: float, 
        lng_max: float,
        show_progress: bool = True
    ) -> Optional[List[Dict[str, Any]]]:
        """Fetch cameras within geographical bounds"""
        
        form_data = {
            'xhr': '1',
            'action': 'all',
            'latMax': str(lat_max),
            'lngMax': str(lng_max),
            'latMin': str(lat_min),
            'lngMin': str(lng_min),
        }
        
        try:
            if show_progress:
                print(f"  Fetching: Lat[{lat_min:.3f}-{lat_max:.3f}] Lng[{lng_min:.3f}-{lng_max:.3f}]", end="")
            
            response = self.session.post(
                self.api_endpoint,
                data=form_data,
                timeout=15
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Extract result array
            cameras = data.get('result', data) if isinstance(data, dict) else data
            
            if isinstance(cameras, list):
                if show_progress:
                    print(f" → Found {len(cameras)} cameras")
                return cameras
            
            if show_progress:
                print(" → No data")
            return []
            
        except Exception as e:
            if show_progress:
                print(f" → Error: {e}")
            return []
    
    def scrape_chennai_comprehensive(self, grid_size: float = 0.02) -> Dict[int, Dict[str, Any]]:
        """
        Scrape Chennai area using a fine grid to capture all cameras
        
        Args:
            grid_size: Size of each grid cell in degrees (smaller = more comprehensive)
                      0.02 degrees ≈ 2.2 km (recommended)
                      0.01 degrees ≈ 1.1 km (very detailed, more requests)
        
        Chennai bounds: Lat 12.85-13.25, Lng 80.1-80.35
        """
        print("="*70)
        print(f"COMPREHENSIVE CHENNAI SCRAPER (Grid size: {grid_size}° ≈ {grid_size*111:.1f} km)")
        print("="*70)
        
        # Chennai bounds (extended slightly for suburbs)
        lat_start, lat_end = 12.20, 13.60
        lng_start, lng_end = 79.60, 80.35
        
        total_cells = int((lat_end - lat_start) / grid_size) * int((lng_end - lng_start) / grid_size)
        current_cell = 0
        
        print(f"\nTotal grid cells to scan: {total_cells}")
        print("-"*70)
        
        lat = lat_start
        while lat < lat_end:
            lng = lng_start
            while lng < lng_end:
                current_cell += 1
                print(f"[{current_cell}/{total_cells}] ", end="")
                
                cameras = self.get_cameras_by_bounds(
                    lat_min=lat,
                    lat_max=lat + grid_size,
                    lng_min=lng,
                    lng_max=lng + grid_size
                )
                
                if cameras:
                    for camera in cameras:
                        if isinstance(camera, dict):
                            cam_id = camera.get('id')
                            if cam_id:
                                self.all_cameras[cam_id] = camera
                
                lng += grid_size
                time.sleep(0.5)  # Be respectful to server
            
            lat += grid_size
        
        print("\n" + "="*70)
        print(f"✓ Scraping complete! Found {len(self.all_cameras)} unique cameras")
        print("="*70)
        
        return self.all_cameras
    
    def scrape_tamil_nadu_comprehensive(self, grid_size: float = 0.1) -> Dict[int, Dict[str, Any]]:
        """
        Scrape entire Tamil Nadu using a grid
        
        Args:
            grid_size: Size of grid cells (0.1 = ~11 km, good for state-wide)
        
        Tamil Nadu bounds: Lat 8.0-13.5, Lng 76.2-80.35
        """
        print("="*70)
        print(f"COMPREHENSIVE TAMIL NADU SCRAPER (Grid size: {grid_size}° ≈ {grid_size*111:.0f} km)")
        print("="*70)
        
        lat_start, lat_end = 8.0, 13.5
        lng_start, lng_end = 76.2, 80.35
        
        total_cells = int((lat_end - lat_start) / grid_size) * int((lng_end - lng_start) / grid_size)
        current_cell = 0
        
        print(f"\nTotal grid cells to scan: {total_cells}")
        print("⚠️  This will take approximately {:.0f} minutes".format(total_cells * 0.5 / 60))
        print("-"*70)
        
        lat = lat_start
        while lat < lat_end:
            lng = lng_start
            while lng < lng_end:
                current_cell += 1
                print(f"[{current_cell}/{total_cells}] ", end="")
                
                cameras = self.get_cameras_by_bounds(
                    lat_min=lat,
                    lat_max=lat + grid_size,
                    lng_min=lng,
                    lng_max=lng + grid_size
                )
                
                if cameras:
                    for camera in cameras:
                        if isinstance(camera, dict):
                            cam_id = camera.get('id')
                            if cam_id:
                                self.all_cameras[cam_id] = camera
                
                lng += grid_size
                time.sleep(0.5)
            
            lat += grid_size
        
        print("\n" + "="*70)
        print(f"✓ Scraping complete! Found {len(self.all_cameras)} unique cameras")
        print("="*70)
        
        return self.all_cameras
    
    def extract_coordinates(self, cameras: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract clean coordinate data"""
        extracted = []
        
        for cam_id, camera in cameras.items():
            camera_data = {
                'id': camera.get('id'),
                'latitude': camera.get('lat') or camera.get('breitengrad_dezimal'),
                'longitude': camera.get('lng') or camera.get('laengengrad_dezimal'),
                'city': camera.get('ort', ''),
                'state': camera.get('bundesland', '') or 'Tamil Nadu',
                'street': camera.get('strasse', ''),
                'postal_code': camera.get('plz', ''),
                'country': camera.get('land', 'IND'),
                'type': camera.get('type', ''),
                'camera_type': camera.get('art', ''),
                'speed_limit': camera.get('vmax', ''),
                'direction': camera.get('richtung', ''),
                'status': camera.get('status', ''),
                'rotatable': bool(camera.get('drehbar', 0)),
                'gps_status': camera.get('gps_status', ''),
            }
            
            if camera_data['latitude'] and camera_data['longitude']:
                extracted.append(camera_data)
        
        return extracted
    
    def save_all_formats(self, prefix: str = "tn"):
        """Save data in multiple formats"""
        
        cameras_list = list(self.all_cameras.values())
        coordinates = self.extract_coordinates(self.all_cameras)
        
        # 1. Detailed JSON with metadata
        detailed_output = {
            'metadata': {
                'total_cameras': len(coordinates),
                'region': 'Chennai, Tamil Nadu' if 'chennai' in prefix else 'Tamil Nadu',
                'country': 'India',
                'extracted_at': datetime.now().isoformat(),
                'source': 'scdb.info',
                'scraping_method': 'comprehensive_grid'
            },
            'cameras': coordinates
        }
        
        with open(f"{prefix}_cameras_detailed.json", 'w', encoding='utf-8') as f:
            json.dump(detailed_output, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved: {prefix}_cameras_detailed.json")
        
        # 2. Simple coordinates
        simple_coords = [
            {
                'id': cam['id'],
                'lat': cam['latitude'],
                'lng': cam['longitude'],
                'location': f"{cam['street']}, {cam['city']}".strip(', '),
                'type': cam['type']
            }
            for cam in coordinates
        ]
        
        with open(f"{prefix}_cameras_simple.json", 'w', encoding='utf-8') as f:
            json.dump(simple_coords, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved: {prefix}_cameras_simple.json")
        
        # 3. GeoJSON
        features = [
            {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [cam['longitude'], cam['latitude']]
                },
                'properties': {
                    'id': cam['id'],
                    'name': cam['street'] or 'Unknown',
                    'city': cam['city'],
                    'type': cam['type'],
                    'speed_limit': cam['speed_limit'],
                    'status': cam['status']
                }
            }
            for cam in coordinates
        ]
        
        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }
        
        with open(f"{prefix}_cameras.geojson", 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved: {prefix}_cameras.geojson")
        
        # 4. CSV
        import csv
        
        fields = ['id', 'latitude', 'longitude', 'street', 'city', 'postal_code', 
                  'type', 'camera_type', 'speed_limit', 'direction', 'status']
        
        with open(f"{prefix}_cameras.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for cam in coordinates:
                row = {field: cam.get(field, '') for field in fields}
                writer.writerow(row)
        print(f"✓ Saved: {prefix}_cameras.csv")
    
    def print_statistics(self):
        """Print statistics about scraped cameras"""
        
        if not self.all_cameras:
            print("No cameras to analyze")
            return
        
        coordinates = self.extract_coordinates(self.all_cameras)
        
        print("\n" + "="*70)
        print("STATISTICS")
        print("="*70)
        
        print(f"\n📊 Total Cameras: {len(coordinates)}")
        
        # By type
        types = {}
        for cam in coordinates:
            cam_type = cam['type']
            types[cam_type] = types.get(cam_type, 0) + 1
        
        print("\n🎥 Camera Types:")
        for cam_type, count in sorted(types.items(), key=lambda x: x[1], reverse=True):
            print(f"   {cam_type}: {count}")
        
        # By city
        cities = {}
        for cam in coordinates:
            city = cam['city']
            if city:
                cities[city] = cities.get(city, 0) + 1
        
        print("\n🏙️  Top Cities:")
        for city, count in sorted(cities.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"   {city}: {count}")
        
        # By status
        statuses = {}
        for cam in coordinates:
            status = cam['status']
            statuses[status] = statuses.get(status, 0) + 1
        
        print("\n✅ Camera Status:")
        status_names = {'A': 'Active', 'L': 'Empty', 'Z': 'Destroyed'}
        for status, count in statuses.items():
            status_name = status_names.get(status, status)
            print(f"   {status_name}: {count}")


def main():
    """Main scraper function"""
    
    scraper = ComprehensiveTNCameraScraper()
    
    print("\n🎯 COMPREHENSIVE CAMERA SCRAPER")
    print("Choose an option:")
    print("1. Chennai only (0.02° grid ≈ 2.2 km, ~5-10 minutes)")
    print("2. Chennai detailed (0.01° grid ≈ 1.1 km, ~20-30 minutes, most comprehensive)")
    print("3. Entire Tamil Nadu (0.1° grid ≈ 11 km, ~30-45 minutes)")
    
    # For automatic execution, run Chennai comprehensive
    print("\n🚀 Running: Chennai Comprehensive (0.02° grid)\n")
    
    cameras = scraper.scrape_chennai_comprehensive(grid_size=0.02)
    
    if cameras:
        scraper.print_statistics()
        LOCATION_PREFIX = "chennai"
        print("\n💾 Saving files...")
        scraper.save_all_formats(prefix=f"{LOCATION_PREFIX}_complete")
        
        print("\n" + "="*70)
        print("✅ SCRAPING COMPLETE!")
        print("="*70)
        print(f"\nTotal cameras found: {len(cameras)}")
        print("\nFiles created:")
        print(f"  • {LOCATION_PREFIX}_complete_cameras_detailed.json")
        print(f"  • {LOCATION_PREFIX}_complete_cameras_simple.json")
        print(f"  • {LOCATION_PREFIX}_complete_cameras.geojson")
        print(f"  • {LOCATION_PREFIX}_complete_cameras.csv")
    else:
        print("\n❌ No cameras found!")


if __name__ == "__main__":
    main()