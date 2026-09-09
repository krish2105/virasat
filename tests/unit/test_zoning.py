import pytest
from pyproj import Transformer

from virasat.geo.zoning import zone_of

to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)

# Ten landmarks with well-known positions (OpenStreetMap). Expected zones follow the
# inscribed-property map: the walled city is the property, the hills and the
# C-Scheme/Ramniwas fringe are buffer, Amber and the railway station are outside.
LANDMARKS = [
    ("Hawa Mahal", 75.8267, 26.9239, "core"),
    ("City Palace", 75.8237, 26.9258, "core"),
    ("Jantar Mantar", 75.8246, 26.9247, "core"),
    ("Tripolia Gate", 75.82269, 26.92401, "core"),
    ("Badi Chaupar", 75.82671, 26.92258, "core"),
    ("Albert Hall Museum", 75.8197, 26.9117, "buffer"),
    ("Nahargarh Fort", 75.8154, 26.9373, "buffer"),
    ("Galta Ji temple approach", 75.8560, 26.9190, "buffer"),
    ("Amber Fort", 75.8513, 26.9855, "outside"),
    ("Jaipur Junction railway station", 75.7878, 26.9196, "outside"),
]


@pytest.mark.parametrize(("name", "lon", "lat", "expected"), LANDMARKS)
def test_landmark_zone(name: str, lon: float, lat: float, expected: str) -> None:
    x, y = to_utm.transform(lon, lat)
    assert zone_of(x, y) == expected, name
