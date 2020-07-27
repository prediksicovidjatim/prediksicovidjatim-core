from arcgis.gis import GIS
from arcgis.features.feature import Feature
import os
from dotenv import load_dotenv
from .. import util
load_dotenv()

ARCGIS_USER = os.getenv("ARCGIS_USER")
ARCGIS_PASS = os.getenv("ARCGIS_PASS")
ARCGIS_PORTAL = os.getenv("ARCGIS_PORTAL")

from memory_profiler import profile

class MapUpdater:
    required_capabilities = ["Create", "Delete", "Query", "Update", "Editing"]
    def __init__(self, portal=None, user=None, pw=None, chunk_size=100):
        global ARCGIS_USER
        global ARCGIS_PASS
        global ARCGIS_PORTAL
        portal = portal or ARCGIS_PORTAL
        user = user or ARCGIS_USER
        pw = pw or ARCGIS_PASS
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
        
    def filter_kabko(self, layer, kabko):
        return layer.query(
            where='kabko=\'%s\'' % (kabko,), 
            order_by_fields="tanggal ASC"
        )
        
        
    def to_update(self, fset, updates):
        
        updates_dict = {u.tanggal_ms():u for u in updates}
        feature_dict = {f.attributes["tanggal"]:f for f in fset.features}
        to_update = {k:updates_dict[k].apply(v) for k, v in feature_dict.items() if k in updates_dict}
        not_updated = [u for u in updates if u.tanggal_ms() not in to_update]
        
        return list(to_update.values()), not_updated
        
    def to_append(self, example, appends):
        geometry = example.geometry
        attributes = dict(example.attributes)
        if "FID" in attributes:
            del attributes["FID"]
        
        to_append = [a.apply(Feature(geometry, dict(attributes))) for a in appends]
        return to_append
        
    def to_save(self, layer, kabko, to_save):
        
        fset = self.filter_kabko(layer, kabko)
        
        example = fset.features[0]
        example = Feature(example.geometry, dict(example.attributes))
        
        to_update, to_append = self.to_update(fset, to_save)
        del fset
        to_append = self.to_append(example, to_append)
        
        
        return to_update, to_append
        
    def __save(self, f, arg, val):
        f({arg:val})
        return len(val)
        
    @profile
    def _save(self, layer, to_save, update, pool=None):
        chunk_size = self.chunk_size
        done = 0
        while True:
            try:
                chunks = util.chunks(to_save[done:], chunk_size)
                arg = "updates" if update else "adds"
                args = [(layer.edit_features, "arg", c) for c in chunks]
                if not pool:
                    done += sum(self.__save(*a) for a in args)
                else:
                    pool.starmap(self.__save, args)
                return done
            except ConnectionError:
                if chunk_size > 10:
                    chunk_size -= 10
                else:
                    raise
        
        
    @profile
    def save(self, layer, kabko, to_save, update=True):
        to_update, to_append = self.to_save(layer, kabko, to_save)
        done = 0
        if update:
            done += self._save(layer, to_update, True)
        else:
            done += len(to_update)
        del to_update
        done += self._save(layer, to_append, False)
        return done