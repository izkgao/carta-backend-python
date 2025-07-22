import asyncio

import dask.array as da
import numba as nb
import numpy as np
from dask.distributed import Client
from numba import njit

from carta_backend import proto as CARTA
from carta_backend.log import logger

clog = logger.bind(name="CARTA")
pflog = logger.bind(name="Performance")
ptlog = logger.bind(name="Protocol")


@njit(nb.int64[:](nb.float32[:], nb.float32[:]), fastmath=True, cache=True)
def numba_histogram_single(data, bin_edges):
    # Precompute constants
    n_bins = bin_edges.size - 1
    bin_min, bin_max = bin_edges[0], bin_edges[-1]
    bin_width = bin_edges[1] - bin_edges[0]
    max_idx = np.uint64(n_bins - 1)
    hist = np.zeros(n_bins, dtype=np.int64)

    for x in data:
        if bin_min <= x <= bin_max:
            bin_idx = np.uint64((x - bin_min) / bin_width)
            bin_idx = min(max_idx, bin_idx)
            hist[bin_idx] += 1

    return hist


@njit(
    (nb.int64[:](nb.float32[:], nb.float32[:])),
    parallel=True,
    fastmath=True,
)
def numba_histogram(data, bin_edges):
    # Precompute constants
    n_bins = np.uint64(bin_edges.size - 1)
    bin_min, bin_max = bin_edges[0], bin_edges[-1]
    bin_width = bin_edges[1] - bin_edges[0]
    max_idx = np.uint64(n_bins - 1)

    # Use thread-local histograms to avoid race conditions
    n_threads = np.uint64(nb.get_num_threads())
    local_hists = np.zeros((n_threads, n_bins), dtype=np.int64)

    # Process data in chunks for better cache locality
    chunk_size = 2**18
    n_chunks = (data.size + chunk_size - 1) // chunk_size

    for chunk in nb.prange(n_chunks):
        thread_id = np.uint64(nb.get_thread_id())
        start = np.uint64(chunk * chunk_size)
        end = np.uint64(min(start + chunk_size, data.size))

        # Process each chunk
        for i in range(start, end):
            x = data[i]
            # Combine conditions to reduce branching
            if x >= bin_min and x <= bin_max:
                bin_idx = min(max_idx, np.uint64((x - bin_min) / bin_width))
                local_hists[thread_id, bin_idx] += 1

    # Sum up the thread-local histograms
    hist = np.zeros(n_bins, dtype=np.int64)
    for t in range(n_threads):
        for b in range(n_bins):
            hist[b] += local_hists[t, b]

    return hist


@nb.njit(
    (nb.float32[:](nb.float32[:])),
    parallel=True,
    fastmath=True,
    cache=True,
)
def numba_minmax_finite(data):
    n = data.size
    if n == 0:
        return np.array([np.float32(np.nan), np.float32(np.nan)])

    # Thread-local min/max - use 1D array for better cache behavior
    n_threads = np.uint32(nb.get_num_threads())
    thread_mins = np.full(n_threads, np.float32(np.inf))
    thread_maxs = np.full(n_threads, np.float32(-np.inf))

    # Use power-of-2 chunk size aligned with cache lines
    chunk_size = max(1024, n // (n_threads * 4))

    # Calculate number of chunks and process them in parallel
    n_chunks = (n + chunk_size - 1) // chunk_size

    for chunk_idx in nb.prange(n_chunks):
        thread_id = np.uint64(nb.get_thread_id())
        i = np.uint64(chunk_idx * chunk_size)
        end_idx = np.uint64(min(i + chunk_size, n))

        # Process chunk with manual loop unrolling
        local_min = thread_mins[thread_id]
        local_max = thread_maxs[thread_id]

        # Process chunk
        for j in range(i, end_idx):
            j = np.uint64(j)
            v = data[j]
            if not (np.isinf(v) or np.isnan(v)):
                if v < local_min:
                    local_min = v
                if v > local_max:
                    local_max = v

        thread_mins[thread_id] = local_min
        thread_maxs[thread_id] = local_max

    # Final reduction
    final_min = np.float32(np.inf)
    final_max = np.float32(-np.inf)

    for i in range(n_threads):
        if thread_mins[i] < final_min:
            final_min = thread_mins[i]
        if thread_maxs[i] > final_max:
            final_max = thread_maxs[i]

    # Handle case where all values were inf/-inf
    if np.isinf(final_min) and np.isinf(final_max):
        return np.array([np.float32(np.nan), np.float32(np.nan)])

    return np.array([final_min, final_max])


@nb.njit(
    (nb.float32[:](nb.float32[:])), parallel=True, fastmath=True, cache=True
)
def numba_minmax_fast(data):
    n = data.size
    if n == 0:
        return np.array([np.float32(np.nan), np.float32(np.nan)])

    # Thread-local min/max - use 1D array for better cache behavior
    n_threads = np.uint32(nb.get_num_threads())
    thread_mins = np.full(n_threads, np.float32(np.inf))
    thread_maxs = np.full(n_threads, np.float32(-np.inf))

    # Use power-of-2 chunk size aligned with cache lines
    chunk_size = max(1024, n // (n_threads * 4))

    # Calculate number of chunks and process them in parallel
    n_chunks = (n + chunk_size - 1) // chunk_size

    # For uint64 indices
    one, two, three, four = (
        np.uint64(1),
        np.uint64(2),
        np.uint64(3),
        np.uint64(4),
    )

    for chunk_idx in nb.prange(n_chunks):
        thread_id = np.uint64(nb.get_thread_id())
        i = np.uint64(chunk_idx * chunk_size)
        end_idx = np.uint64(min(i + chunk_size, n))

        # Process chunk with manual loop unrolling
        local_min = thread_mins[thread_id]
        local_max = thread_maxs[thread_id]

        # Unroll loop by 4 for better instruction-level parallelism
        while i + three < end_idx:
            local_min = min(
                local_min,
                min(
                    min(data[i], data[i + one]),
                    min(data[i + two], data[i + three]),
                ),
            )
            local_max = max(
                local_max,
                max(
                    max(data[i], data[i + one]),
                    max(data[i + two], data[i + three]),
                ),
            )
            i += four

        # Handle remaining elements
        while i < end_idx:
            v = data[i]
            if v < local_min:
                local_min = v
            if v > local_max:
                local_max = v
            i += one

        thread_mins[thread_id] = local_min
        thread_maxs[thread_id] = local_max

    # Final reduction
    final_min = np.float32(np.inf)
    final_max = np.float32(-np.inf)

    for i in range(n_threads):
        if thread_mins[i] < final_min:
            final_min = thread_mins[i]
        if thread_maxs[i] > final_max:
            final_max = thread_maxs[i]

    return np.array([final_min, final_max])


def numba_minmax(data: np.ndarray[np.float32]) -> np.ndarray[np.float32]:
    minmax = numba_minmax_fast(data)
    if np.isinf(minmax).any():
        return numba_minmax_finite(data)
    return minmax


async def dask_histogram(data, bins):
    bin_min = da.nanmin(data)
    bin_max = da.nanmax(data)
    hist, bin_edges = da.histogram(data, bins=bins, range=[bin_min, bin_max])
    return hist, bin_edges, bin_min


async def get_histogram_dask(data, client: Client):
    # Calculate number of bins
    nbins = int(max(np.sqrt(data.shape[0] * data.shape[1]), 2.0))

    # Calculate bin range
    res = client.compute([da.nanmin(data), da.nanmax(data)])
    bin_min, bin_max = await client.gather(res)

    # Calculate histogram
    res = client.compute(
        da.histogram(data, bins=nbins, range=[bin_min, bin_max])
    )
    hist, bin_edges = await client.gather(res)
    bin_width = bin_edges[1] - bin_edges[0]
    bin_centers = bin_edges[:-1] + bin_width / 2
    mean = np.sum(hist * bin_centers) / np.sum(hist)
    std_dev = np.sqrt(np.sum(hist * (bin_centers - mean) ** 2) / np.sum(hist))

    histogram = CARTA.Histogram()
    histogram.num_bins = nbins
    histogram.bin_width = bin_width
    histogram.first_bin_center = bin_centers[0]
    histogram.bins.extend(hist)
    histogram.mean = mean
    histogram.std_dev = std_dev
    return histogram


async def get_histogram_numpy(data: np.ndarray[np.float32]) -> CARTA.Histogram:
    # Calculate number of bins
    nbins = int(max(np.sqrt(data.shape[0] * data.shape[1]), 2.0))

    # Calculate bin range
    data = data.ravel()
    bin_min, bin_max = numba_minmax(data)
    bin_width = (bin_max - bin_min) / nbins
    bin_edges = np.linspace(bin_min, bin_max, nbins + 1, dtype=np.float32)

    # Calculate histogram
    if data.size <= 1024**2:
        hist = numba_histogram_single(data, bin_edges)
    else:
        hist = await asyncio.to_thread(numba_histogram, data, bin_edges)
    bin_centers = bin_edges[:-1] + bin_width / 2
    mean = np.sum(hist * bin_centers) / np.sum(hist)
    std_dev = np.sqrt(np.sum(hist * (bin_centers - mean) ** 2) / np.sum(hist))

    histogram = CARTA.Histogram()
    histogram.num_bins = nbins
    histogram.bin_width = bin_width
    histogram.first_bin_center = bin_min + bin_width / 2
    histogram.bins.extend(hist)
    histogram.mean = mean
    histogram.std_dev = std_dev
    return histogram


async def get_histogram(
    data: da.Array | np.ndarray, client: Client
) -> CARTA.Histogram:
    if isinstance(data, da.Array):
        clog.debug("Using dask histogram")
        return await get_histogram_dask(data, client)
    elif isinstance(data, np.ndarray):
        clog.debug("Using numba histogram")
        return await get_histogram_numpy(data)
