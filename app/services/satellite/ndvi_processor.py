import rasterio
import numpy as np
from rasterio.mask import mask
from shapely.geometry import mapping


def compute_ndvi(red_url, nir_url, geometry):
    with rasterio.open(red_url) as red_src:
        red, _ = mask(red_src, [mapping(geometry)], crop=True)

    with rasterio.open(nir_url) as nir_src:
        nir, _ = mask(nir_src, [mapping(geometry)], crop=True)

    red = red.astype("float32")
    nir = nir.astype("float32")

    np.seterr(divide="ignore", invalid="ignore")

    ndvi = (nir - red) / (nir + red)

    ndvi_mean = float(np.nanmean(ndvi))

    return round(ndvi_mean, 4)