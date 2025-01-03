import pytest

@pytest.fixture(scope="session")  
def mock_msg_data():
    """Create a sample msg dictionary data."""
    return {
        "cpu": {
            "utilization": 10,
            "frequency": 11,
            "temperature": 12,
            "load_average_1min": 0.7651,
            "num_high_load_cores": 2,
            "cores": {
                "utilization": [7,0,0,1],
                "frequency": [],
                "temperature": []
            }
        },
        "gpu": {
            "mem_used": 4.5*10**3,
            "mem_total": 8*10**3,
            "utilization": 62,
            "temperature": 70
        },
        "ram": {
            "total": 2*10**3,
            "used": 1.2*10**3,
            "available": 8*10**3
        }
    }
