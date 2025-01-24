import googlemaps
from datetime import datetime


class MapsService:
    def __init__(self, api_key):
        self.client = googlemaps.Client(api_key)

    def get_directions(self, start, end, mode="driving"):
        now = datetime.now()
        directions_result = self.client.directions(start, end, mode=mode, departure_time=now)
        steps = directions_result[0]['legs'][0]['steps']
        formatted_steps = [step['html_instructions'] for step in steps]
        return formatted_steps
