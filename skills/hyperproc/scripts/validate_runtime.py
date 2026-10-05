"""Deterministic helper and tiny synthetic QA/index/raster checks; no acquisition."""
from __future__ import annotations
import argparse
import importlib.metadata as md
import json
import subprocess
import sys
import tempfile
from pathlib import Path

BUNDLE=Path(__file__).resolve().parents[1]


def expect(condition,message):
    if not condition:raise AssertionError(message)


def run_checks(bundle):
    import numpy as np
    import xarray as xr
    import dask.array as da
    from dask import delayed
    import hyperproc as hp
    import rasterio
    from affine import Affine
    from inspect_product import inspect_dataset,parse_reader_options
    from download_plan import plan_download
    from run_context import context_for
    from api_index import installed_source,resolve_source,runtime_symbol
    from sensor_table import reader_rows
    from env_report import inspect_environment
    checks=[]
    version,modules,declarations,aliases=installed_source()
    expect(version==md.version('hyperproc'),'Installed version report differs')
    expect('hyperproc.atmos.process' in modules,'Installed module enumeration missed atmos.process')
    expect(resolve_source('hyperproc.spectral_index',declarations,aliases)['qualified_name']=='hyperproc.features.index','Source export alias resolution failed')
    from hyperproc.atmos import process
    import inspect
    expect(runtime_symbol('hyperproc.atmos.process')['signature']==str(inspect.signature(process)),'Runtime signature differs')
    expect(any(r['sensor']=='NEON' and r['level']=='L3' and not r['implemented'] for r in reader_rows(hp)),'Planned reader reported incorrectly')
    expect(inspect_environment(['core'])['versions']['hyperproc']==version,'Environment version differs')
    checks+=['live installed source enumeration/export aliases','exact runtime callable signature','reader registry including unimplemented levels','environment metadata']
    @delayed
    def prohibited_read():raise AssertionError('Metadata inspection evaluated the cube')
    lazy=da.from_delayed(prohibited_read(),shape=(4,5,2),dtype=np.float32)
    coords={'y':np.arange(4),'x':np.arange(5),'wavelength':[660.,860.],'good_wavelength':('wavelength',[True,True])}
    meta=xr.Dataset({'reflectance':(('y','x','wavelength'),lazy)},coords=coords)
    expect(inspect_dataset(meta)['sampling'] is None,'Metadata report unexpectedly sampled')
    try:parse_reader_options('{"nested":{"password":"dummy"}}')
    except ValueError:pass
    else:raise AssertionError('Credential-like reader options accepted')
    values=np.broadcast_to(np.array([.2,.6],dtype=np.float32),(4,5,2)).copy();values[0,0]=np.nan
    coords['x']=500000.+(np.arange(5)+.5)*30;coords['y']=4500000.-(np.arange(4)+.5)*30
    attrs={'sensor':'SYNTHETIC','units':'1','crs':'EPSG:32611','transform':(500000.,30.,0.,4500000.,0.,-30.),'granule':'synthetic'}
    ds=xr.Dataset({'reflectance':(('y','x','wavelength'),values)},coords=coords,attrs=attrs)
    expect(inspect_dataset(ds,sample=True,window=[1,3,1,4])['sampling']['cube_bytes']==48,'Sampling bounds differ')
    try:inspect_dataset(ds,sample=True,window=[0,5,0,1])
    except ValueError:pass
    else:raise AssertionError('Out-of-bounds window accepted')
    quality=hp.quality_flags(ds,derive=('fill',));expect(int(hp.quality_decode(quality,'fill').sum())==1,'Fill known answer differs')
    ndvi=hp.spectral_index(hp.quality_apply(ds,quality,drop=('fill',)),'NDVI')
    expect(np.allclose(ndvi.values[1:],.5) and np.isnan(ndvi.values[0,0]),'NDVI known answer differs')
    checks+=['metadata-only no cube evaluation','bounded sampling and invalid-window rejection','credential-like options rejected','QA fill and exact NDVI known answers']
    with tempfile.TemporaryDirectory(prefix='hyperproc-merged-skill-') as directory:
        work=Path(directory);input_file=work/'primary';input_file.write_text('synthetic identity')
        a=context_for([input_file],{'y':[0,2],'x':[0,2]},{'engine':'sRTMnet'},work/'runs')
        b=context_for([input_file],{'y':[1,3],'x':[0,2]},{'engine':'sRTMnet'},work/'runs')
        expect(a['suggested_work_dir']!=b['suggested_work_dir'] and not (work/'runs').exists(),'Run identities collide or wrote directories')
        try:context_for([input_file],{}, {'token':'dummy'},work)
        except ValueError:pass
        else:raise AssertionError('Secret-like context accepted')
        known=plan_download([{'name':'a','size_mb':1024,'links':['one']}],work/'data',2)
        unknown=plan_download([{'name':'a','size_mb':1024,'links':['one']},{'name':'b','size_mb':None}],work/'data',2)
        expect(known['within_budget'] and known['reported_size_subtotal_gib']==1,'Known size planning differs')
        expect(unknown['within_budget'] is None and unknown['unknown_size_granules']==['b'],'Unknown size treated as zero/within budget')
        expect(not (work/'data').exists(),'Download planning wrote destination')
        cube=hp.to_geotiff(ds,work/'cube.tif');hp.bands_to_csv(ds,work/'bands.csv')
        qpath=hp.to_geotiff_2d(ds.assign(quality=quality),work/'qa.tif',var='quality',tags=quality.attrs)
        with rasterio.open(cube) as src:
            expect(src.count==2 and src.crs.to_epsg()==32611 and src.transform==Affine.from_gdal(*attrs['transform']),'Export grid/count differs')
            expect(np.allclose(src.read().transpose(1,2,0),values,equal_nan=True),'Export spectral values differ')
        with rasterio.open(qpath) as src:
            expect(src.dtypes[0]=='uint16' and np.array_equal(src.read(1),quality.values),'QA dtype/values lost')
            expect('flag_meanings' in src.tags(),'QA bit meanings lost')
        # Fresh processes prove snippets do not depend on previously imported namespaces.
        code='import hyperproc as hp; from hyperproc.atmos import process; import hyperproc.correct as hc; assert callable(process) and callable(hc.fit_topo); assert not hasattr(hp,"Map")'
        subprocess.run([sys.executable,'-c',code],check=True,capture_output=True,text=True)
    checks+=['different windows produce distinct work identities without writes','secret-like run settings rejected','known/unknown download volume planning without downloads/writes','spectral raster geometry/value round trip and band CSV','uint16 QA raster values/bit metadata round trip','explicit processing imports in a fresh interpreter']
    return {'hyperproc_version':version,'source':hp.__file__,'checks':checks,'scope':'Synthetic Linux helper/output tests; no real scene download, authentication, asset installation or atmospheric retrieval, and no claim of cross-OS execution.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,help='New result JSON, not overwritten.')
    args=parser.parse_args()
    try:
        report=run_checks(BUNDLE)
    except AssertionError as exc:
        report={'passed':False,'failure':str(exc),'scope':'A deterministic check returned an unexpected answer; the installed release differs from the reviewed baseline.'}
    except ImportError as exc:
        report={'passed':False,'failure':f'{type(exc).__name__}: {exc}','scope':'These checks need the core runtime dependencies (numpy, xarray, dask, rasterio, hyperproc) in the interpreter running this script.'}
    else:
        report={'passed':True,**report,'checks_run':len(report['checks'])}
    payload=json.dumps(report,indent=2,allow_nan=False)+'\n'
    if args.output:
        with args.output.open('x') as stream:stream.write(payload)
    else:print(payload,end='')
    return 0 if report['passed'] else 1

if __name__=='__main__':
    raise SystemExit(main())
