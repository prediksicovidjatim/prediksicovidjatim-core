from ... import util, database
from ..model.entities import KabkoData, DayData, ParamData, RtData
from ..raw.repo import fetch_kabko, fetch_kabko_dict, get_latest_tanggal, get_oldest_tanggal
from ...modeling import BaseModel


def fetch_kabko_need_fitting(tanggal, cur=None):
    if cur:
        return _fetch_kabko_need_fitting(tanggal, cur)
    else:
        with database.get_conn() as conn, conn.cursor() as cur:
            return _fetch_kabko_need_fitting(tanggal, cur)
            
def _fetch_kabko_need_fitting(tanggal, cur):
    cur.execute("""
        SELECT k.kabko
        FROM main.kabko k
        WHERE k.last_fit<%s
        ORDER BY k.kabko
    """, (tanggal,))
    
    return [x for x, in cur.fetchall()]

def fetch_kabko_scored(cur=None):
    if cur:
        return _fetch_kabko_scored(cur)
    else:
        with database.get_conn() as conn, conn.cursor() as cur:
            return _fetch_kabko_scored(cur)
            
def _fetch_kabko_scored(cur):
    cur.execute("""
        SELECT k.kabko, k.text 
        FROM main.kabko k
        WHERE k.kabko IN (
            SELECT DISTINCT s.kabko
            FROM main.scores s
        )
        ORDER BY k.kabko
    """)
    
    return list(cur.fetchall())
        
def fetch_day_data(kabko, cur=None):
    if cur:
        return _fetch_day_data(kabko, cur)
    else:
        with database.get_conn() as conn, conn.cursor() as cur:
            return _fetch_day_data(kabko, cur)
    
def _fetch_day_data(kabko, cur):
    cur.execute("""
        SELECT 
            tanggal,
            pos_total AS infected,
            (pos_rawat_total-pos_rawat_rs) AS infectious,
            pos_rawat_rs AS critical_cared,
            pos_rawat_total AS infectious_all,
            pos_sembuh AS recovered,
            pos_meninggal AS dead
        FROM main.raw_covid_data
        WHERE kabko=%s
        ORDER BY tanggal
    """, (kabko,))
    ret = [DayData(*args) for args in cur.fetchall()]
    while True:
        if ret[-1].is_zero():
            del ret[-1]
        else:
            break
    return ret
        
def fetch_param_data(kabko, cur=None):
    if cur:
        return _fetch_param_data(kabko, cur)
    else:
        with database.get_conn() as conn, conn.cursor() as cur:
            return _fetch_param_data(kabko, cur)
    
def _fetch_param_data(kabko, cur):
    cur.execute("""
        SELECT 
            pk.parameter,
            pk.init,
            pk.min,
            pk.max,
            p.vary,
            p.expr,
            pk.stderr
        FROM main.parameter_kabko pk, main.parameter p
        WHERE pk.parameter=p.parameter AND kabko=%s
        ORDER BY pk.parameter
    """, (kabko,))
    
    return [ParamData(*args) for args in cur.fetchall()]

def fetch_kapasitas_rs(kabko, cur=None):
    if cur:
        return _fetch_kapasitas_rs(kabko, cur)
    else:
        with database.get_conn() as conn, conn.cursor() as cur:
            return _fetch_kapasitas_rs(kabko, cur)
            
def _fetch_kapasitas_rs(kabko, cur):
    cur.execute("""
        SELECT 
            tanggal,
            kapasitas
        FROM main.kapasitas_rs
        WHERE kabko=%s
        ORDER BY tanggal
    """, (kabko,))
    
    return [(*row,) for row in cur.fetchall()]

def fetch_rt_data(kabko, cur=None):
    if cur:
        return _fetch_rt_data(kabko, cur)
    else:
        with database.get_conn() as conn, conn.cursor() as cur:
            return _fetch_rt_data(kabko, cur)
    
def _fetch_rt_data(kabko, cur):
    cur.execute("""
        SELECT 
            tanggal,
            init,
            min,
            max,
            stderr
        FROM main.rt
        WHERE kabko=%s
        ORDER BY tanggal
    """, (kabko,))
    
    return [RtData(*args) for args in cur.fetchall()]
        
def get_kabko(kabko, cur=None):
    if cur:
        return _get_kabko(kabko, cur)
    else:
        with database.get_conn() as conn, conn.cursor() as cur:
            return _get_kabko(kabko, cur)
    
def _get_kabko(kabko, cur):
    cur.execute("""
        SELECT 
            k.kabko,
            text,
            population,
            outbreak_shift,
            fpd.tanggal AS first_positive,
            rcd.pos_total AS seed,	
            CASE WHEN k.kabko IN (
                SELECT DISTINCT s.kabko
                FROM main.scores s
            ) THEN 1 ELSE 0 END AS scored
        FROM main.kabko k, main.first_pos_date fpd, main.raw_covid_data rcd
        WHERE k.kabko=fpd.kabko AND k.kabko=rcd.kabko AND rcd.tanggal=fpd.tanggal AND k.kabko=%s
    """, (kabko,))
    
    return (*cur.fetchone(),)
        
def get_kabko_full(kabko, cur=None):
    if cur:
        return _get_kabko_full(kabko, cur)
    else:
        with database.get_conn() as conn, conn.cursor() as cur:
            return _get_kabko_full(kabko, cur)

def _get_kabko_full(kabko, cur):
    return KabkoData(
        *get_kabko(kabko, cur), 
        fetch_day_data(kabko, cur), 
        fetch_kapasitas_rs(kabko, cur), 
        fetch_rt_data(kabko, cur), 
        fetch_param_data(kabko, cur)
    )
    
def update_params_init(kabko, filtered_params, cur=None):
    if cur:
        return _update_params_init(kabko, filtered_params, cur)
    else:
        with database.get_conn() as conn, conn.cursor() as cur:
            ret = _update_params_init(kabko, filtered_params, cur)
            conn.commit()
            return ret
            
def _update_params_init(kabko, filtered_params, cur):
    cur.execute('''
        PREPARE update_params_init AS 
        UPDATE main.parameter_kabko 
        SET init=$1, stderr=$2
        WHERE "parameter"=$3
            AND kabko=$4
    ''')
    database.execute_batch(
        cur, 
        "EXECUTE update_params_init (%s, %s, %s, %s)",
        [(v.value, v.stderr, k, kabko) for k, v in filtered_params.items() if v.vary]
    )
    ret = cur.rowcount
    cur.execute("DEALLOCATE update_params_init")
    return ret
    
def update_rt_init(kabko, rts, cur=None):
    if cur:
        return _update_rt_init(kabko, rts, cur)
    else:
        with database.get_conn() as conn, conn.cursor() as cur:
            return _update_rt_init(kabko, rts, cur)
            
def _update_rt_init(kabko, rts, cur):
    cur.execute('''
        PREPARE update_rt_init AS 
        UPDATE main.rt 
        SET init=$1, stderr=$2
        WHERE tanggal=$3
            AND kabko=$4
    ''')
    database.execute_batch(
        cur, 
        "EXECUTE update_rt_init (%s, %s, %s, %s)",
        [(v.value, v.stderr, k, kabko) for k, v in rts if v.vary]
    )
    cur.execute("DEALLOCATE update_rt_init")
    
def update_kabko(kabko, outbreak_shift, tanggal=None, cur=None):
    if cur:
        return _update_kabko(kabko, outbreak_shift, tanggal, cur)
    else:
        with database.get_conn() as conn, conn.cursor() as cur:
            return _update_kabko(kabko, outbreak_shift, tanggal, cur)
            
def _update_kabko(kabko, outbreak_shift, tanggal, cur):
    if tanggal:
        cur.execute("""
            UPDATE main.kabko
            SET outbreak_shift=%s, last_fit=%s
            WHERE kabko=%s
        """, (outbreak_shift, tanggal, kabko,))
    else:
        cur.execute("""
            UPDATE main.kabko
            SET outbreak_shift=%s, last_fit=current_date
            WHERE kabko=%s
        """, (outbreak_shift, kabko,))
    
score_columns = ["residual_mean", "residual_median", "max_error", "mae", "mse", "rmse", "rmsle", "explained_variance", "r2", "r2_adj", "smape", "mase", "chi2", "redchi", "aic", "aicc", "bic", "dw", "residual_normal", "residual_runs", "pearson_data", "pearson_residual", "f_mean", "f_data", "f_residual", "ks_data", "ks_residual", "prediction_interval"]
score_columns_2 = ["nvarys"] + score_columns
score_updates = ["%s=EXCLUDED.%s" % (col, col) for col in score_columns_2]
score_updates_str = ", ".join(score_updates)
score_keys = ["kabko", "test", "dataset"]
score_keys_str = ", ".join(score_keys)
score_columns_full = score_keys + score_columns_2
score_columns_full_str = ", ".join(score_columns_full)
score_args_str = util.mogrify_value_template(len(score_columns_full))

def update_scores(kabko, datasets, scorer, test, cur=None):
    if cur:
        return _update_scores(kabko, datasets, scorer, test, cur)
    else:
        with database.get_conn() as conn, conn.cursor() as cur:
            return _update_scores(kabko, datasets, scorer, test, cur)
            
def _update_scores(kabko, datasets, scorer, test, cur):
    test = 1 if test else 0
    values = [datasets] + [len(datasets) * [scorer.nvarys]] + scorer.get_values(score_columns)
    values = util.transpose_list_list(values)
    keys = [kabko, test]
    values = [keys + v for v in values]
    score_args_str_full = ','.join(cur.mogrify(score_args_str, x).decode('utf-8') for x in values)
    sql = """
        INSERT INTO main.scores(%s) VALUES %s
        ON CONFLICT (%s) DO UPDATE SET
            %s
    """ % (score_columns_full_str, score_args_str_full, score_keys_str, score_updates_str)
    
    cur.execute(sql)
    
    
def init_weights(cur=None):
    if cur:
        return _init_weights(cur)
    else:
        with database.get_conn() as conn, conn.cursor() as cur:
            return _init_weights(cur)
    
def _init_weights(cur):
    cur.execute("""
        SELECT 
            dataset,
            weight
        FROM main.dataset
    """)
    
    weights = dict(cur.fetchall())
    BaseModel.dataset_weights = weights
    
def save_fitting_result(fit_result, tanggal=None, option="seicrd_rlc", cur=None):
    if cur:
        return _save_fitting_result(fit_result, tanggal, option, cur)
    else:
        with database.get_conn() as conn, conn.cursor() as cur:
            ret = _save_fitting_result(fit_result, tanggal, option, cur)
            conn.commit()
            return ret 
        
def _save_fitting_result(fit_result, tanggal, option, cur):
    params_needed = KabkoData.get_params_needed(option)
    params = fit_result.fit_result.params
    kabko = fit_result.kabko
    filtered_params = util.filter_dict(params, params_needed)
    outbreak_shift = fit_result.outbreak_shift
    rts = kabko.transform_rt_to_dates(kabko.get_kwargs_rt(params, "_r" in option))
    
    update_params_init(kabko.kabko, filtered_params, cur)
    update_rt_init(kabko.kabko, rts, cur)
    update_kabko(kabko.kabko, outbreak_shift, tanggal, cur)
    update_scores(kabko.kabko, fit_result.datasets, fit_result.fit_scorer, False, cur)
    update_scores(kabko.kabko, ["flat"], fit_result.fit_scorer.flatten(), False, cur)
    if fit_result.test_scorer:
        update_scores(kabko.kabko, fit_result.datasets, fit_result.test_scorer, True, cur)
        update_scores(kabko.kabko, ["flat"], fit_result.test_scorer.flatten(), True, cur)
        

def fetch_scores(kabko, cur=None):
    if cur:
        return _fetch_scores(kabko, cur)
    else:
        with database.get_conn() as conn, conn.cursor() as cur:
            return _fetch_scores(kabko, cur)
    
def _split_test(ret):
    return [r[1:] for r in ret if r[0]==0], [r[1:] for r in ret if r[0]==1]
    
def _fetch_scores(kabko, cur):
    cur.execute("""
        SELECT 
            test, d.text, nvarys, max_error, mae, rmse, rmsle, r2, r2_adj, smape, mase, redchi, aic, aicc, bic
        FROM main.scores s, main.dataset d
        WHERE s.dataset=d.dataset AND s.kabko=%s
        ORDER BY s.test ASC, d.order ASC
    """, (kabko,))
    
    ret = [args for args in cur.fetchall()]
    #return ret
    return _split_test(ret)
    
def fetch_scores_flat(cur=None):
    if cur:
        return _fetch_scores_flat(cur)
    else:
        with database.get_conn() as conn, conn.cursor() as cur:
            return _fetch_scores_flat(cur)
            
def _fetch_scores_flat(cur):
    cur.execute("""
        SELECT 
            s.test, s.kabko, k.text, mae, rmse, rmsle, r2_adj, smape, mase, redchi, aicc, bic
        FROM main.scores s, main.kabko k
        WHERE s.kabko=k.kabko AND s.dataset='flat'
        ORDER BY s.test, k.kabko
    """)
    
    ret = [args for args in cur.fetchall()]
    #return ret
    return _split_test(ret)
    
def fetch_scores_avg(cur=None):
    if cur:
        return _fetch_scores_avg(cur)
    else:
        with database.get_conn() as conn, conn.cursor() as cur:
            return _fetch_scores_avg(cur)
    
def _fetch_scores_avg(cur):
    cur.execute("""
        SELECT 
            s.test, s.kabko, k.text, mae, rmse, rmsle, r2_adj, smape, mase, redchi, aicc, bic
        FROM main.scores_avg s, main.kabko k
        WHERE s.kabko=k.kabko
        ORDER BY s.test, k.kabko
    """)
    
    ret = [args for args in cur.fetchall()]
    #return ret
    return _split_test(ret)