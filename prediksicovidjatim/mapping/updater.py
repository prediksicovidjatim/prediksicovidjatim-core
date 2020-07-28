from arcgis.gis import GIS
from arcgis.features.feature import Feature
import os
from .. import util
from ..util import ThreadPool, lprofile
'''
from dotenv import load_dotenv
load_dotenv()
'''
from requests.exceptions import ConnectionError
'''
ARCGIS_USER = os.getenv("ARCGIS_USER")
ARCGIS_PASS = os.getenv("ARCGIS_PASS")
ARCGIS_PORTAL = os.getenv("ARCGIS_PORTAL")
'''
from memory_profiler import profile as mprofile

import gc

GEOMETRY_CACHE = {}

class MapUpdater:
    required_capabilities = ["Create", "Delete", "Query", "Update", "Editing"]
    def __init__(self, portal, user, pw, chunk_size=100):
        self.credentials = (portal, user, pw)
        self.chunk_size = chunk_size
        self.login()
        
    def login(self):
        self.gis = GIS(*self.credentials)
        
    def get_layer(self, content_id):
        ret = self.gis.content.get(content_id).layers[0]
        self.check_layer_capabilities(ret)
        return ret
        
    def check_layer_capabilities(self, layer):
        caps = layer.properties.capabilities
        incapable = [cap for cap in MapUpdater.required_capabilities if cap not in caps]
        if len(incapable) > 0:
            raise Exception("You need to have %s capabilities" % (str(incapable),))
            #return False
        #return True
        
    def cache_kabko_geometry(self, layer, first_tanggal='2020-03-20'):
        global GEOMETRY_CACHE
        if not GEOMETRY_CACHE:
            features = layer.query(
                where='tanggal = DATE \'%s\'' % (first_tanggal,), 
                out_fields='kabko',
                return_geometry=True
            ).features
            #cache = {f.attributes["kabko"]:(f.geometry, f.attributes["SHAPE"]) for f in features}
            cache = {f.attributes["kabko"]:f.geometry for f in features}
            GEOMETRY_CACHE = cache
        return GEOMETRY_CACHE
        
    def get_kabko_geometry(self, layer, kabko):
        global GEOMETRY_CACHE
        if not GEOMETRY_CACHE:
            self.cache_kabko_geometry(layer)
        if GEOMETRY_CACHE and kabko in GEOMETRY_CACHE:
            return GEOMETRY_CACHE[kabko]
        feature = layer.query(
            where='kabko=\'%s\'' % (kabko,), 
            out_fields='',
            return_geometry=True,
            result_record_count=1
        ).features[0]
        geometry = feature.geometry#, feature.attributes["SHAPE"]
        GEOMETRY_CACHE[kabko] = geometry
        return geometry
        
    def fetch_kabko_feature_tanggal(self, layer, kabko, geometry=None):#, shape=None):
        fset = layer.query(
            where='kabko=\'%s\'' % (kabko,), 
            order_by_fields="tanggal ASC",
            out_fields='tanggal',
            return_geometry=False
        )
        if geometry:
            features = [Feature(geometry, f.attributes) for f in fset.features]
        else:
            features = list(fset.features)
        del fset
        #gc.collect()
        '''
        if geometry:# and shape:
            for f in features:
                f.geometry = geometry
                #f.attributes["SHAPE"] = shape
        '''
        return features
        
    def filter_tanggal_scalar(self, features):
        return {f.attributes["tanggal"] for f in features}
        
    def fetch_kabko_feature_tanggal_scalar(self, layer, kabko):
        features = self.fetch_kabko_feature_tanggal(layer, kabko)
        tanggal = self.filter_tanggal_scalar(features)
        del features
        #gc.collect()
        return tanggal
        
    def make_features(self, attributes, geometry):
        '''
        for a in attributes:
            a["SHAPE"] = shape
        '''
        return [Feature(geometry, a) for a in attributes]
        
    '''
    def fetch_kabko_features(self, layer, kabko, geometry, shape):
        fset = layer.query(
            where='kabko=\'%s\'' % (kabko,), 
            order_by_fields="tanggal ASC",
            return_geometry=False
        )
        features = list(fset.features)
        for f in features:
            f.geometry = geometry
            f.attributes["SHAPE"] = shape
        del fset
        #gc.collect()
        return features
    '''
        
        
    @lprofile
    def to_update(self, features, updates):
        
        updates_dict = {u.tanggal_ms():u for u in updates}
        feature_dict = {f.attributes["tanggal"]:f for f in features}
        to_update = {k:updates_dict[k].apply(v) for k, v in feature_dict.items() if k in updates_dict}
        
        return list(to_update.values()), set(to_update.keys())
        
    @lprofile
    def to_append(self, appends, geometry, update_keys=None, features=None, free_features=True):
        if update_keys is None:
            if features is None:
                raise Exception("Please provide either update_keys or features")
            update_keys = self.filter_tanggal_scalar(features)
            if free_features:
                del features
                #gc.collect()
                
        appends = [u for u in appends if u.tanggal_ms() not in update_keys]
        to_append = self.make_features([a.to_dict() for a in appends], geometry)
        return to_append
        
    @lprofile
    def to_save(self, layer, kabko, to_save, update=True):
        
        geometry = self.get_kabko_geometry(layer, kabko)
        
        if update:
            features = self.fetch_kabko_feature_tanggal(layer, kabko, geometry)
            to_update, update_keys = self.to_update(features, to_save)
            del features
        else:
            to_update = []
            update_keys = self.fetch_kabko_feature_tanggal_scalar(layer, kabko)
            
        to_append = self.to_append(to_save, geometry, update_keys=update_keys)
        return to_update, to_append
        
    def __save(self, f, arg, val):
        ret = f(**{arg:val})
        del ret
        #gc.collect()
        return len(val)
        
    @lprofile
    def _save(self, layer, to_save, update, chunk_size=100, max_process_count=None, max_tasks_per_child=100):
        chunk_size = chunk_size or self.chunk_size
        done = 0
        pool = None
        while True:
            chunks = util.chunks(to_save[done:], chunk_size)
            arg = "updates" if update else "adds"
            args = [(layer.edit_features, arg, c) for c in chunks]
            del chunks
            #gc.collect()
            pool = None
            try:
                if max_process_count==1 or len(args) == 1:
                    done += sum(self.__save(*a) for a in args)
                else:
                    #done += self.__save(*args[0])
                    #pool = Pool(processes=max_process_count, maxtasksperchild=max_tasks_per_child)
                    #pool = ThreadPool(processes=util.min_none(len(args)-1, max_process_count))
                    #output = pool.starmap(self.__save, args[1:])
                    pool = ThreadPool(processes=util.min_none(len(args), max_process_count))
                    output = pool.starmap(self.__save, args)
                    pool.close()
                    pool.join()
                    done += sum(output)
                    del pool
                return done, chunk_size
            except ConnectionError:
                if pool:
                    del pool
                if chunk_size > 10:
                    chunk_size -= 10
                else:
                    raise
            finally:
                #gc.collect()
                pass
        
        
    @lprofile
    def save(self, layer, kabko, to_save, update=True, chunk_size=100, max_process_count=None, max_tasks_per_child=100):
        
        geometry = self.get_kabko_geometry(layer, kabko)
        
        chunk_size = chunk_size or self.chunk_size
        done = 0
        
        
        
        
        if update:
            features = self.fetch_kabko_feature_tanggal(layer, kabko, *geometry)
            to_update, update_keys = self.to_update(features, to_save)
            del features
            #gc.collect()
            
            if len(to_update) > 0:
                done2, chunk_size2 = self._save(layer, to_update, True, chunk_size=chunk_size, max_process_count=max_process_count, max_tasks_per_child=max_tasks_per_child)
                done += done2
                chunk_size = min(chunk_size, chunk_size2)
                del to_update
                #gc.collect()
        else:
            update_keys = self.fetch_kabko_feature_tanggal_scalar(layer, kabko)
            
        to_append = self.to_append(to_save, *geometry, update_keys=update_keys)
        if len(to_append) > 0:
            done2, chunk_size2 = self._save(layer, to_append, False, max_process_count=max_process_count, max_tasks_per_child=max_tasks_per_child)
            done += done2
            chunk_size = min(chunk_size, chunk_size2)
            del to_append
            #gc.collect()
        return done, chunk_size