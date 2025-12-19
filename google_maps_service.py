"""
Google Maps API service for journey planning and route information
"""
import googlemaps
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Initialize Google Maps client
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
gmaps = None

if GOOGLE_MAPS_API_KEY:
    try:
        gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
        logger.info("Google Maps client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Google Maps client: {e}")
else:
    logger.warning("GOOGLE_MAPS_API_KEY not found in environment variables")


def get_directions(
    origin: str,
    destination: str,
    mode: str = "driving",
    departure_time: Optional[datetime] = None,
    alternatives: bool = True
) -> Optional[List[Dict]]:
    """
    Get directions from origin to destination using Google Maps Directions API
    
    Args:
        origin: Starting location (address or place name)
        destination: End location (address or place name)
        mode: Travel mode (driving, walking, bicycling, transit)
        departure_time: Departure time for traffic estimates
        alternatives: Whether to return alternative routes
    
    Returns:
        List of route dictionaries or None if error
    """
    if not gmaps:
        logger.error("Google Maps client not initialized")
        return None
    
    try:
        # If no departure time specified, use current time for traffic data
        if departure_time is None:
            departure_time = datetime.now()
        
        directions_result = gmaps.directions(
            origin=origin,
            destination=destination,
            mode=mode,
            departure_time=departure_time,
            alternatives=alternatives,
            traffic_model="best_guess"
        )
        
        if directions_result:
            logger.info(f"Successfully retrieved directions from {origin} to {destination}")
            return directions_result
        else:
            logger.warning(f"No routes found from {origin} to {destination}")
            return None
            
    except googlemaps.exceptions.ApiError as e:
        logger.error(f"Google Maps API error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error getting directions: {e}")
        return None


def get_distance_matrix(
    origins: List[str],
    destinations: List[str],
    mode: str = "driving",
    departure_time: Optional[datetime] = None
) -> Optional[Dict]:
    """
    Get distance and duration matrix between multiple origins and destinations
    
    Args:
        origins: List of origin locations
        destinations: List of destination locations
        mode: Travel mode
        departure_time: Departure time for traffic estimates
    
    Returns:
        Distance matrix dictionary or None if error
    """
    if not gmaps:
        logger.error("Google Maps client not initialized")
        return None
    
    try:
        if departure_time is None:
            departure_time = datetime.now()
        
        matrix_result = gmaps.distance_matrix(
            origins=origins,
            destinations=destinations,
            mode=mode,
            departure_time=departure_time,
            traffic_model="best_guess"
        )
        
        if matrix_result:
            logger.info(f"Successfully retrieved distance matrix")
            return matrix_result
        else:
            logger.warning("No distance matrix data returned")
            return None
            
    except googlemaps.exceptions.ApiError as e:
        logger.error(f"Google Maps API error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error getting distance matrix: {e}")
        return None


def parse_journey_data(directions_result: List[Dict]) -> str:
    """
    Parse Google Maps directions result into a concise format for LLM
    
    Args:
        directions_result: Raw directions result from Google Maps API
    
    Returns:
        Formatted string with essential journey information only
    """
    if not directions_result or len(directions_result) == 0:
        return "No route information available."
    
    # Get the first (recommended) route
    route = directions_result[0]
    leg = route['legs'][0]
    
    # Extract key information
    distance = leg['distance']['text']
    duration = leg['duration']['text']
    start_address = leg['start_address']
    end_address = leg['end_address']
    
    # Get main highways/roads from the route summary if available
    route_summary = route.get('summary', 'Route information')
    
    # Build concise output
    output = f"""JOURNEY SUMMARY:
From: {start_address}
To: {end_address}
Distance: {distance}
Duration: {duration}
Main Route: {route_summary}
"""
    
    # Add alternative routes if available (concise)
    if len(directions_result) > 1:
        output += f"\nAlternatives: {len(directions_result) - 1} other route(s) available"
        for i, alt_route in enumerate(directions_result[1:2], 2):  # Show only 1 alternative
            alt_leg = alt_route['legs'][0]
            alt_distance = alt_leg['distance']['text']
            alt_duration = alt_leg['duration']['text']
            output += f"\n  Route {i}: {alt_distance}, {alt_duration}"
    
    return output


def extract_locations_from_text(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Simple extraction of origin and destination from user text
    This is a basic implementation - can be enhanced with NLP
    
    Args:
        text: User's message text
    
    Returns:
        Tuple of (origin, destination) or (None, None)
    """
    text_lower = text.lower()
    
    # Common patterns
    from_patterns = ["from ", "starting from ", "leaving from ", "departing from "]
    to_patterns = [" to ", " going to ", " heading to ", " traveling to "]
    
    origin = None
    destination = None
    
    # Try to find "from X to Y" pattern
    for from_word in from_patterns:
        if from_word in text_lower:
            from_idx = text_lower.index(from_word) + len(from_word)
            remaining = text[from_idx:]
            
            for to_word in to_patterns:
                if to_word in remaining.lower():
                    to_idx = remaining.lower().index(to_word)
                    origin = remaining[:to_idx].strip()
                    destination = remaining[to_idx + len(to_word):].strip()
                    # Clean up punctuation
                    destination = destination.rstrip('.,!?')
                    break
            break
    
    return origin, destination


def format_journey_summary(origin: str, destination: str) -> Optional[str]:
    """
    Get journey information and format it for the LLM
    
    Args:
        origin: Starting location
        destination: End location
    
    Returns:
        Formatted journey summary or None if error
    """
    directions = get_directions(origin, destination)
    
    if directions:
        return parse_journey_data(directions)
    else:
        return None


def generate_map_image_url(origin: str, destination: str, size: str = "600x400") -> Optional[str]:
    """
    Generate a Google Maps Static API URL showing the route from origin to destination
    
    Args:
        origin: Starting location
        destination: End location
        size: Image size in format "widthxheight" (max 640x640 for free tier)
    
    Returns:
        URL to the static map image or None if API key not available
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.error("Google Maps API key not available for map image generation")
        return None
    
    try:
        # URL encode the locations
        import urllib.parse
        origin_encoded = urllib.parse.quote(origin)
        destination_encoded = urllib.parse.quote(destination)
        
        # Build the Static Maps API URL
        # This creates a map with markers at origin (green) and destination (red)
        # and draws the route path between them
        base_url = "https://maps.googleapis.com/maps/api/staticmap"
        
        # Parameters
        params = [
            f"size={size}",
            f"markers=color:green|label:A|{origin_encoded}",
            f"markers=color:red|label:B|{destination_encoded}",
            f"path=weight:3|color:blue|enc:",  # Will add encoded polyline
            f"key={GOOGLE_MAPS_API_KEY}"
        ]
        
        # Get directions to extract the polyline
        directions = get_directions(origin, destination)
        if directions and len(directions) > 0:
            # Extract the overview polyline from the route
            polyline = directions[0].get('overview_polyline', {}).get('points', '')
            if polyline:
                # Replace the path parameter with the encoded polyline
                params[3] = f"path=weight:3|color:0x0000ff|enc:{polyline}"
        
        map_url = f"{base_url}?{'&'.join(params)}"
        
        logger.info(f"Generated map image URL for route from {origin} to {destination}")
        return map_url
        
    except Exception as e:
        logger.error(f"Error generating map image URL: {e}")
        return None
