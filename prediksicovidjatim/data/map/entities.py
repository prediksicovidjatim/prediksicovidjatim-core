from ... import util

class MapDataReal:
    def __init__(self, 
            kabko, tanggal, populasi, otg=0, odp_aktif=0, pdp_aktif=0, 
            pos_aktif=0, pos_rs=0, pos_meninggal=0, pos_sembuh=0, pos_total=0):
        
        self.kabko = kabko
        self.tanggal = tanggal
        self.populasi = populasi
        self.otg = otg
        self.odp_aktif = odp_aktif
        self.pdp_aktif = pdp_aktif
        self.pos_aktif = pos_aktif
        self.pos_rs = pos_rs
        self.pos_meninggal = pos_meninggal
        self.pos_sembuh = pos_sembuh
        self.pos_total = pos_total
        
    def zero(kabko, populasi, tanggal_start, count=1):
        tanggal = util.date_range(tanggal_start, count)
        return [MapDataReal(kabko, t, populasi) for t in tanggal]
        
    def shift(data, tanggal_start):
        tanggal_start_0 = data[0].tanggal
        if tanggal_start >= tanggal_start_0:
            return list(data)
        return MapDataReal.zero(
            data[0].kabko, data[0].populasi, tanggal_start, 
            util.days_between(tanggal_start, tanggal_start_0)
        ) + data
        
    def tanggal_ms(self):
        return util.date_to_ms(self.tanggal)
        
    def _apply(self, attributes):
        attributes["kabko"] = self.kabko
        attributes["tanggal"] = self.tanggal_ms()
        attributes["populasi"] = self.populasi
        attributes["otg"] = self.otg
        attributes["odp_aktif"] = self.odp_aktif
        attributes["pdp_aktif"] = self.pdp_aktif
        attributes["pos_aktif"] = self.pos_aktif
        attributes["pos_rs"] = self.pos_rs
        attributes["pos_meninggal"] = self.pos_meninggal
        attributes["pos_sembuh"] = self.pos_sembuh
        attributes["pos_total"] = self.pos_total
        
    def apply(self, feature):
        self._apply(feature.attributes)
        return feature
        
    def to_dict(self):
        ret = dict()
        self._apply(ret)
        return ret
        
class MapDataPred:
    def __init__(self, 
            kabko, tanggal, populasi, pos_aktif=0, pos_rs=0, pos_meninggal=0,
            pos_sembuh=0, pos_total=0, mortality_rate=0, rt=0,
            kapasitas_rs=0, test_coverage=0):
        
        self.kabko = kabko
        self.tanggal = tanggal
        self.populasi = populasi
        self.pos_aktif = pos_aktif
        self.pos_rs = pos_rs
        self.pos_meninggal = pos_meninggal
        self.pos_sembuh = pos_sembuh
        self.pos_total = pos_total
        self.mortality_rate = mortality_rate
        self.rt = rt
        self.kapasitas_rs = kapasitas_rs
        self.test_coverage = test_coverage
        
    def zero(kabko, populasi, tanggal_start, count=1):
        tanggal = util.date_range(tanggal_start, count)
        return [MapDataReal(kabko, t, populasi) for t in tanggal]
        
    def shift(data, tanggal_start):
        tanggal_start_0 = data[0].tanggal
        if tanggal_start >= tanggal_start_0:
            return list(data)
        return MapDataPred.zero(
            data[0].kabko, data[0].populasi, tanggal_start, 
            util.days_between(tanggal_start, tanggal_start_0)
        ) + data
        
    def tanggal_ms(self):
        return util.date_to_ms(self.tanggal)
        
    def _apply(self, attributes):
        attributes["kabko"] = self.kabko
        attributes["tanggal"] = self.tanggal_ms()
        attributes["populasi"] = self.populasi
        attributes["pos_aktif"] = self.pos_aktif
        attributes["pos_rs"] = self.pos_rs
        attributes["pos_meninggal"] = self.pos_meninggal
        attributes["pos_sembuh"] = self.pos_sembuh
        attributes["pos_total"] = self.pos_total
        attributes["mortality_rate"] = self.mortality_rate
        attributes["rt"] = self.rt
        attributes["kapasitas_rs"] = self.kapasitas_rs
        attributes["test_coverage"] = self.test_coverage
        
    def apply(self, feature):
        self._apply(feature.attributes)
        return feature
        
    def to_dict(self):
        ret = dict()
        self._apply(ret)
        return ret
        
    def from_result(kabko, result, shift=None):
        length = len(result.t)
        if shift is None:
            shift = kabko.last_outbreak_shift
        populasi = kabko.population
        length_full = length - shift
        tanggal = kabko.get_tanggal(0, length_full)
        assert (len(tanggal) == length_full)
        kabko = kabko.kabko
        pos_rs = util.shift_array(result.critical_cared_scaled(), -shift)
        assert (len(pos_rs) == length_full)
        pos_aktif = util.shift_array(result.infectious_scaled(), -shift) + pos_rs
        pos_meninggal = util.shift_array(result.dead_scaled(), -shift)
        pos_sembuh = util.shift_array(result.recovered_scaled(), -shift)
        pos_total = pos_aktif + pos_meninggal + pos_sembuh
        mortality_rate = util.shift_array(result.mortality_rate, -shift)
        rt = util.shift_array(result.r0_overall, -shift)
        kapasitas_rs = util.shift_array(result.kapasitas_rs, -shift)
        test_coverage = util.shift_array(result.test_coverage, -shift)
        
        return [MapDataPred(
            kabko, tanggal[i], populasi, pos_aktif[i], pos_rs[i], pos_meninggal[i],
            pos_sembuh[i], pos_total[i], mortality_rate[i], rt[i],
            kapasitas_rs[i], test_coverage[i]*100
        ) for i in range(0, length_full)]