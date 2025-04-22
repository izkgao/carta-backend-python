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


@njit(nb.int64[:](nb.float32[:], nb.float32[:]))
def numba_histogram_single(data, bin_edges):
    # Precompute constants
    n_bins = bin_edges.size - 1
    bin_min, bin_max = bin_edges[0], bin_edges[-1]
    bin_width = bin_edges[1] - bin_edges[0]
    max_idx = n_bins - 1
    hist = np.zeros(n_bins, dtype=np.int64)

    for x in data:
        if not np.isnan(x) and bin_min <= x <= bin_max:
            bin_idx = int((x - bin_min) / bin_width)
            bin_idx = min(max_idx, bin_idx)
            hist[bin_idx] += 1

    return hist


@njit((nb.int64[:](nb.float32[:], nb.float32[:])),
      parallel=True, fastmath=True)
def numba_histogram(data, bin_edges):
    # Precompute constants
    n_bins = bin_edges.size - 1
    bin_min, bin_max = bin_edges[0], bin_edges[-1]
    bin_width = bin_edges[1] - bin_edges[0]
    max_idx = n_bins - 1

    # Use thread-local histograms to avoid race conditions
    n_threads = nb.get_num_threads()
    local_hists = np.zeros((n_threads, n_bins), dtype=np.int64)

    # Process data in chunks for better cache locality
    chunk_size = 1024**2
    n_chunks = (data.size + chunk_size - 1) // chunk_size

    for chunk in nb.prange(n_chunks):
        thread_id = nb.get_thread_id()
        start = chunk * chunk_size
        end = min(start + chunk_size, data.size)

        # Process each chunk
        for i in range(start, end):
            x = data[i]
            # Combine conditions to reduce branching
            if not np.isnan(x) and x >= bin_min and x <= bin_max:
                bin_idx = min(max_idx, int((x - bin_min) / bin_width))
                local_hists[thread_id, bin_idx] += 1

    # Sum up the thread-local histograms
    hist = np.zeros(n_bins, dtype=np.int64)
    for t in range(n_threads):
        for b in range(n_bins):
            hist[b] += local_hists[t, b]

    return hist


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
        da.histogram(data, bins=nbins, range=[bin_min, bin_max]))
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


async def get_histogram_numpy(data: np.ndarray) -> CARTA.Histogram:
    # Calculate number of bins
    nbins = int(max(np.sqrt(data.shape[0] * data.shape[1]), 2.0))

    # Calculate bin range
    bin_min, bin_max = np.nanmin(data), np.nanmax(data)
    bin_width = (bin_max - bin_min) / nbins
    bin_edges = np.linspace(bin_min, bin_max, nbins + 1, dtype='float32')

    # Calculate histogram
    data = data.astype('float32').ravel()
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
