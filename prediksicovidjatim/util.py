from datetime import datetime, date, timezone
import numpy as np
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import math
from datetime import timedelta
from operator import add
from sklearn.model_selection import TimeSeriesSplit
from . import config
import calendar
from threading import RLock
import line_profiler
lprofile = line_profiler.LineProfiler()
#import atexit
#atexit.register(lprofile.print_stats)

odeint_lock = RLock()
lmfit_lock = RLock()


def use_multiprocess():
    try:
        ipy_str = str(type(get_ipython()))
        if 'zmqshell' in ipy_str:
            #return 'jupyter'
            return True
        if 'terminal' in ipy_str:
            #return 'ipython'
            return True
        return True
    except:
        #return 'terminal'
        return False

if use_multiprocess():
    from multiprocess import Pool
else:
    from multiprocessing import Pool
    
from multiprocessing.pool import ThreadPool
'''
def max_none(a, b):
    return a if b is None else max(a, b)
'''
def min_none(a, b):
    return a if b is None else min(a, b)
    
    
def chunks(lst, n):
    #https://stackoverflow.com/a/312464
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
        
SANITY_CHECK_IGNORE = 0
SANITY_CHECK_CORRECT = 1
SANITY_CHECK_ERROR = 2

def sanity_clamp(arr, mode=SANITY_CHECK_CORRECT):
    if mode == SANITY_CHECK_IGNORE:
        return arr
    elif mode == SANITY_CHECK_CORRECT:
        return np.clip(arr, 0, None)
    elif mode == SANITY_CHECK_ERROR:
        if (arr < 0).any():
            raise Exception("%s can't be negative. (%f, %f)" % (name, y, config.FLOAT_TOLERANCE))
        else:
            return arr
    raise ValueError("Invalid mode")

def sanity_check_init(name, y, mode=SANITY_CHECK_CORRECT):
    if mode==SANITY_CHECK_IGNORE or y >= 0:
        return y
    elif math.isclose(y, 0, abs_tol=config.FLOAT_TOLERANCE):
        return y
    elif mode==SANITY_CHECK_CORRECT:
        return 0
    elif mode==SANITY_CHECK_ERROR:
        raise Exception("%s can't be negative. (%f, %f)" % (name, y, config.FLOAT_TOLERANCE))
    raise ValueError("Invalid mode")
    
def sanity_check_flow(name, flow, mode=SANITY_CHECK_CORRECT):
    return sanity_check_init(name, flow, mode)
    
def sanity_check_y(name, y, dy, mode=SANITY_CHECK_CORRECT):
    y1 = y+dy
    try:
        return sanity_check_init(name, y1, mode)
    except ValueError:
        raise
    except Exception:
        raise Exception("%s can't flow more than source. (%f+%f=%f, %f)" % (name, y, dy, y1, config.FLOAT_TOLERANCE))
    
def parse_int(text):
    if not text:
        return 0
    text = text.replace(".", "").replace(",", "").replace(" ", "")
    try:
        val = int(text)
    except ValueError as ex:
        try:
            val = int(float(text))
        except ValueError as ex2:
            raise
    return val
    
def get_obj_attr(obj, attr):
    ret = getattr(obj, attr)
    if callable(ret):
        ret = ret()
    return ret

def mogrify_value_template(n):
    return "("+ ",".join(n*("%s",))+")"

def parse_date(d):
    if isinstance(d, date):
        return d
    return datetime.strptime(d, "%Y-%m-%d").date()
    
def format_date(d):
    if isinstance(d, str):
        return d
    return datetime.strftime(d, "%Y-%m-%d")
    
def ms_to_date(d):
    return datetime.utcfromtimestamp(d / 1e3).date()
    
def date_to_ms(d):
    d = parse_date(d) if isinstance(d, str) else d
    return int(calendar.timegm(d.timetuple()) * 1e3)
    
def shift_date(init, shift):
    return init + timedelta(days=shift)
    
def date_range(init, length, start=0):
    init = parse_date(init) if isinstance(init, str) else init
    return [shift_date(init, x) for x in range(start, length+start)]
    
def filter_dates_after(dates, after):
    if after is None:
        return list(dates)
    if isinstance(after, str):
        after = parse_date(after)
    new_dates = [d for d in dates if d and parse_date(d) > after]
    return new_dates
    
def filter_dict(data, keys):
    return {k:data[k] for k in keys}
    
def filter_dict_new(data, keys):
    return {v:data[k] for k, v in keys.items()}
    
def extract_dict(data, keys):
    return [data[k] for k in keys]
    
def delta(arr):
    return np.array([arr[0]] + [arr[i]-arr[i-1] for i in range(1, len(arr))])
    
def post_plot(ax):
    ax.yaxis.set_tick_params(length=0)
    ax.xaxis.set_tick_params(length=0)

    ax.grid(b=True, which='major', c='w', lw=0.5, ls='-', alpha=0.25)

    ax.legend(loc='best', shadow=True)
    
    for spine in ('top', 'right', 'bottom', 'left'):
        ax.spines[spine].set_visible(False)
        

date_formatter = mdates.DateFormatter('%Y-%m-%d')

def date_plot(ax):
    ax.xaxis.set_major_formatter(date_formatter)
    ax.format_xdata = date_formatter
    ax.fmt_xdata = date_formatter
    ax.xaxis_date()
    
def sum_respectively(lists):
    return [sum(x) for x in zip(*lists)]

def sum_element(a, b):
    return np.array(list(map(add, a, b)))

def lerp(start, end, t):
    return start + (end-start)*t
    
def lerp_many(start, end, n):
    return [lerp(start, end, i/(n+1.0)) for i in range(1, n+1)]
    
def get_missing_data(data, start, count=1):
    end = start+count-1
    return [data[i].to_db_row() for i in range(start, end+1)]
    
def days_between(start, end, non_negative=False):
    dt = parse_date(end) - parse_date(start)
    dt = dt.days
    if non_negative:
        dt = max(0, dt)
    return dt
    
def get_date_index(data, date):
    return int(days_between(data[0].tanggal, date, True))
    
def lerp_missing_data(data, start, count=1):
    end = start+count-1
    yesterday = data[start-1].to_db_row()
    tomorrow = data[end+1].to_db_row()
    return [{
        k:(
            int(lerp(v, tomorrow[k], i/(count+1.0))) if isinstance(v, int) 
            else format_date(parse_date(v) + timedelta(days=i)) if isinstance(v, str) and "2020-" in v
            else v
        )
        for k, v in yesterday.items()
    } for i in range(1, 1+count)]
    
def check_finite_many(retT):
    not_finite = []
    for i in range(0, len(retT)):
        if not np.isfinite(retT[i]).all():
            not_finite.append(i)
    
    if len(not_finite) > 0:
        raise Exception("Not finite: " + str(not_finite))
        
def check_finite(retT):
    not_finite = []
    for i in range(0, len(retT)):
        if not math.isfinite(retT[i]):
            not_finite.append(i)
    
    if len(not_finite) > 0:
        raise Exception("Not finite: " + str(not_finite))
        
def map_function(t, f, unpack=False):
    if unpack:
        return np.array([f(*ti) for ti in t])
    return np.array([f(ti) for ti in t])
    
def get_kwargs_rt(kwargs, count):
    return [kwargs["r_%d" % (i,)] for i in range(0, count)]
    
def shift_array(data, shift, preceeding_zero=True, trailing_zero=False, keep_length=False):
    shift = int(shift)
    if shift == 0:
        return np.array(data)
    elif shift > 0:
        preceeding = np.zeros(shift) if preceeding_zero else np.repeat(data[0], shift)
        
        ret = np.concatenate((preceeding, data))
        if keep_length:
            return ret[:len(data)]
        else:
            return ret
    else:
        ret = data[-shift:]
        if keep_length:
            trailing = np.zeros(-shift) if trailing_zero else np.repeat(data[-1], -shift)
            return np.concatenate((ret, trailing))
        else:
            return ret
        
def get_if_exists(d, index):
    if index in d:
        return d[index]
    return None
    
def transpose_dict_list(ld):
    example = ld[0]
    return {k:[ldi[k] for ldi in ld] for k in example.keys()}
    
def transpose_list_list(ll):
    row_count = len(ll)
    col_count = len(ll[0])
    return [[ll[i][j] for i in range(0, row_count)] for j in range(0, col_count)]
    
def plot_single(t, data, title=None, label=None, color='blue'):
    fig, ax = plt.subplots(1, 1)
    _plot_single(ax, t, data, title, label, color)
    post_plot(ax)
    return fig
    
def _plot_single(ax, t, data, title=None, label=None, color='blue'):
    ax.plot(t, data, color, alpha=0.7, linewidth=2, label=label)
    
    if title:
        ax.title.set_text(title)
        
def plot_single_pred(t, pred, data=None, min=None, max=None, title=None, label=None, color='blue'):
    fig, ax = plt.subplots(1, 1)
    _plot_single(ax, t, data, pred, min, max, title, label, color)
    util.post_plot(ax)
    return fig
    
def _plot_single_pred(ax, t, pred, data=None, min=None, max=None, title=None, label=None, color='blue'):
    ax.plot(t, pred, color=color, alpha=0.7, linewidth=2, label=label + " (model)")
    if data:
        ax.plot(t, data, marker='o', linestyle='', color=color, label=label + " (data)")
    if min and max:
        ax.fill_between(t, min, max, color=color, alpha=0.1, label=label + " (interval keyakinan)")
    
    if title:
        ax.title.set_text(title)

def stdev(cov):
    return np.sqrt(np.diag(cov))
    
def np_split(arr, split):
    return np.array(np.split(arr, split))
    
def np_mean_2d(data):
    return np.array([np.mean(d) for d in data])
    
def np_multiply_2d(data, weights):
    return np.array([weights[i] * data[i] for i in range(0, len(weights))])
    
def np_concat_2d(arrs):
    row = len(arrs[0])
    return np.array([np.concatenate([a[i] for a in arrs]) for i in range(0, row)])
    
def np_f_2d(arrs, f):
    row = len(arrs[0])
    return np.array([f([a[i] for a in arrs]) for i in range(0, row)])
    
def np_make_2d(data):
    if not isinstance(data, np.ndarray):
        data = np.array(data)
    if data.ndim == 1:
        data = np.array([data])
    return data
    
def time_series_split(data, split):
    if split > 1:
        return TimeSeriesSplit(split).split(data)
    else:
        data_len = len(data)
        full_index = np.linspace(0, data_len - 1, data_len, dtype=int)
        empty_index = np.array([], dtype=int)
        return [(full_index, empty_index)]
        
def simple_linear(y_0, a, x):
    return a*x + y_0