
"""
 This script produces an MSAVI seasonal anomaly timeseries for an area equal to the total
 bounds of a specified shapefile.  The anomaly is based on the seasonal mean of all input time 
 steps.  The job is parallized with Dask. Go to the user inputs section and enter the relevant
 info.

"""


#import libraries
import numpy as np
import xarray as xr
import datacube 
import dask
from dask.distributed import Client, LocalCluster
import logging
import sys
sys.path.append('src')
# import lazily_load_clearlandsat as llcLS
import DEADataHandling
import query_from_shp

### Info for parallel processing with Dask #####
#     1. If reading netcdf files make sure each worker has one thread
#     2. memory_limit is per worker not per cluster of workers
#     3. When launching multiple workers (needed when reading netcdfs) 
#        on the same node you have to supply memory limit,
#        otherwise every worker will assume they have all the memory

#!!!!!!!!!!!!!!
# USER INPUTS
#!!!!!!!!!!!!!
start = '1987-12-01'
end = '2019-05-31'
shp_fpath = "/g/data/r78/cb3058/dea-notebooks/dcStats/data/spatial/griffith_MSAVI_test.shp"
chunk_size = 250
cpus = 14
memory_per_cpu = '40GB'
results = 'results/'

lat, lon = -34.294, 146.037
latLon_adjust = 1.0

#-------------------------------------------------------------------------
#Functions for script

def msavi_func(nir, red):
    return (2*nir+1-np.sqrt((2*nir+1)**2 - 8*(nir-red)))/2

def msavi_ufunc(ds):
    return xr.apply_ufunc(
        msavi_func, ds.nir, ds.red,
        dask='parallelized',
        output_dtypes=[float])

def compute_seasonal(data):		
    msavi = msavi_ufunc(data)
    #calculate the MSAVI    
    msavi = msavi.resample(time='M').mean('time')
    #calculate seasonal climatology
    msavi_seasonalClimatology = msavi.groupby('time.season').mean('time')
    #resample monthly msavi to seasonal means
    msavi_seasonalMeans = msavi.resample(time='QS-DEC').mean('time')
    #calculate anomalies
    masvi_anomalies = msavi_seasonalMeans.groupby('time.season') - msavi_seasonalClimatology
    return masvi_anomalies

#-------------------------------------------------------------------------------------
print('starting')

#trying to suppress 'garbage collector' warnings from distributed
# and 'divide' warnings from numpy
logger = logging.getLogger("distributed.utils_perf")
logger.setLevel(logging.ERROR)
np.seterr(divide='ignore', invalid='ignore')

if __name__ == '__main__':
    with LocalCluster(n_workers=cpus, threads_per_worker=1) as cluster:
        with Client(cluster, memory_limit=memory_per_cpu) as client:
            print('querying datacube')
            # create query and load data
#             query = query_from_shp.query_from_shp(shp_fpath, start, end)
            query = {'lon': (lon - latLon_adjust, lon + latLon_adjust),
                     'lat': (lat - latLon_adjust, lat + latLon_adjust),
                     'time': (start, end)}
            dc = datacube.Datacube(app='load_clearlandsat')
            ds = DEADataHandling.load_clearlandsat(dc=dc, query=query, sensors=['ls5','ls7','ls8'], bands_of_interest=['nir', 'red'],
                                                   lazy_load=True, dask_chunks = {'x': chunk_size, 'y': chunk_size},
                                                    masked_prop=0.25, mask_pixel_quality=True)
            #lazily compute anomalies
            a = compute_seasonal(ds)
            #write out data (will compute now)
            print('exporting netcdf')
            a.to_netcdf(results + 'griffith_MSAVI_anomalies_1deg.nc')  
            
