from ... import util, database
from .entities import MapDataReal
from ..model.repo import get_kabko_full
from ..raw.repo import fetch_kabko, fetch_kabko_dict, get_latest_tanggal, get_oldest_tanggal

def fetch_kabko_need_mapping(tanggal, cur=None):
    if cur:
        return _fetch_kabko_need_mapping(tanggal, cur)
    else:
        with database.get_conn() as conn, conn.cursor() as cur:
            return _fetch_kabko_need_mapping(tanggal, cur)
            
def _fetch_kabko_need_mapping(tanggal, cur):
    if tanggal:
        cur.execute("""
            SELECT k.kabko, k.map_chunk_size
            FROM main.kabko k
            WHERE k.last_map<%s
            ORDER BY k.kabko
        """, (tanggal,))
    else:
        cur.execute("""
            SELECT k.kabko, k.map_chunk_size
            FROM main.kabko k
            WHERE k.last_map<k.last_fit
            ORDER BY k.kabko
        """)
        
    
    return list(cur.fetchall())
    
def fetch_real_data(kabko, cur=None):
    if cur:
        return _fetch_real_data(kabko, cur)
    else:
        with database.get_conn() as conn, conn.cursor() as cur:
            return _fetch_real_data(kabko, cur)
    
def _fetch_real_data(kabko, cur):
    cur.execute("""
        SELECT 
            k.kabko,
            d.tanggal,
            k.population as populasi,
            d.otg,
            d.odp_rawat_total as odp_aktif,
            d.pdp_rawat_total as pdp_aktif,
            d.pos_rawat_total as pos_aktif,
            d.pos_rawat_rs as pos_rs,
            d.pos_meninggal,
            d.pos_sembuh,
            d.pos_total
        FROM main.kabko k, main.raw_covid_data d
        WHERE k.kabko=%s AND d.kabko=k.kabko
        ORDER BY tanggal
    """, (kabko,))
    
    return [MapDataReal(*args) for args in cur.fetchall()]
    
def set_updated(kabko, tanggal, chunk_size=None, cur=None):
    if cur:
        return _set_updated(kabko, tanggal, chunk_size, cur)
    else:
        with database.get_conn() as conn, conn.cursor() as cur:
            return _set_updated(kabko, tanggal, chunk_size, cur)
            
def _set_updated(kabko, tanggal, chunk_size, cur):
    #template = util.mogrify_value_template(len(kabko))
    #tup = tuple("'%s'" % k for k in kabko)
    if tanggal:
        if chunk_size:
            print("SET UPDATED 1")
            cur.execute("""
                UPDATE main.kabko
                SET last_map=%s, map_chunk_size=%s
                WHERE kabko = %s
            """, (tanggal, chunk_size, kabko))
        else:
            print("SET UPDATED 2")
            cur.execute("""
                UPDATE main.kabko
                SET last_map=%s
                WHERE kabko = %s
            """, (tanggal, kabko))
    else:
        if chunk_size:
            print("SET UPDATED 3. %s, %s, %s" % (kabko, str(tanggal), str(chunk_size)))
            cur.execute("""
                UPDATE main.kabko
                SET last_map=last_fit, map_chunk_size=%s
                WHERE kabko = %s
            """, (chunk_size, kabko))
        else:
            print("SET UPDATED 4")
            cur.execute("""
                UPDATE main.kabko
                SET last_map=last_fit
                WHERE kabko = %s
            """, kabko)