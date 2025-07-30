# Protocol
ICD_VERSION = 30

# Tile
TILE_SHAPE = (256, 256)
MAX_COMPRESSION_QUALITY = 32

# Spectral profile calculation
INIT_DELTA_Z = 10
TARGET_DELTA_TIME = 50  # milliseconds
TARGET_PARTIAL_CURSOR_TIME = 500  # milliseconds
TARGET_PARTIAL_REGION_TIME = 1000  # milliseconds

# I/O
N_JOBS = 4
N_SEMAPHORE = 4

# Dask
CHUNK_SIZE = 1024
