# Dummy custom error for unit test purposes.
# The amdsmi library cannot be imported unless the AMD SMI library is installed,
# making unit testing difficult. This custom exception is raised to
# simulate amdsmi.AmdSmiException without requiring the actual library. 

class DummyAmdSmiException(Exception):
    pass