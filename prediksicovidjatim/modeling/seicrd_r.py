import numpy as np
from scipy.integrate import odeint
import lmfit
from .. import util
from .base_model import BaseModel

class SeicrdRModel(BaseModel):
    params = ["incubation_period",
                    "critical_chance", "critical_time", 
                    "recovery_time_normal", "recovery_time_critical",
                    "death_chance_normal", "death_time_normal",
                    "exposed_rate_critical", "k"]
                    
    def __init__(self, kabko):
        super().__init__(kabko) 
    
    def deriv(self, y, t, exposed_rate, infectious_rate, 
                critical_rate, critical_chance, 
                recovery_rate_normal, recovery_rate_critical, 
                death_rate, death_chance):
        
        population, susceptible, exposed, infectious, critical, recovered, dead = y
        exposed_flow = exposed_rate(t) * susceptible * infectious / population
        infectious_flow = infectious_rate * exposed * 1
        critical_flow = critical_rate * infectious * critical_chance
        recovery_flow_normal = recovery_rate_normal * infectious * (1-critical_chance)
        recovery_flow_critical = recovery_rate_critical * critical * (1-death_chance)
        death_flow = death_rate * critical * death_chance
        dSdt = -exposed_flow
        dEdt = exposed_flow - infectious_flow
        dIdt = infectious_flow - recovery_flow_normal - critical_flow
        dCdt = critical_flow - recovery_flow_critical - death_flow
        dRdt = recovery_flow_normal + recovery_flow_critical
        dDdt = death_flow
        dPdt = dSdt + dEdt + dIdt + dCdt + dRdt + dDdt
        return dPdt, dSdt, dEdt, dIdt, dCdt, dRdt, dDdt
        
    def model(self, days, incubation_period,
                    critical_chance, critical_time, 
                    recovery_time_normal, recovery_time_critical,
                    death_chance_normal, death_time_normal,
                    k, **kwargs):
        
        #unpack rt values
        rt_values = util.get_kwargs_rt(kwargs, self.kabko.rt_count)
        rt_data = list(zip(self.kabko.rt_days, rt_values))
        rt_delta = util.rt_delta(rt_data, self.kabko.oldest_tanggal)
        r_0 = rt_values[0]
        
        #load values
        population = self.kabko.population
        
        # this is derived parameter
        infectious_period_opt = recovery_time_normal * (1-critical_chance) + critical_time * critical_chance #this is derived parameter
        infectious_rate = 1.0 / incubation_period # this is derived parameter
        recovery_rate_normal = 1.0 / recovery_time_normal # this is derived parameter
        death_rate_normal = 1.0 / death_time_normal # this is derived parameter
        critical_rate = 1.0 / critical_time # this is derived parameter
        recovery_rate_critical = 1.0 / recovery_time_critical #this is derived parameter
        
        def logistic_rt(t):
            return self.kabko.logistic_rt(r_0, rt_delta, t, k)

        def exposed_rate_normal(t):
            ret = logistic_rt(t) / infectious_period_opt
            return ret

        population_init, susceptible_init, exposed_init, infectious_init, critical_init, recovered_init, dead_init = population, population-1, 1, 0, 0, 0, 0,  # initial conditions: one exposed, rest susceptible
        
        t = np.linspace(0, days-1, days) # days
        y0 = population_init, susceptible_init, exposed_init, infectious_init, critical_init, recovered_init, dead_init # Initial conditions tuple

        
        # Integrate the SIR equations over the time grid, t.
        ret = odeint(self.deriv, y0, t, args=(
            exposed_rate_normal, infectious_rate, 
            critical_rate, critical_chance, 
            recovery_rate_normal, recovery_rate_critical, 
            death_rate_normal, death_chance_normal
        ))
        
        retT = ret.T
        population_2, susceptible, exposed, infectious, critical, recovered, dead = retT
        
        
        death_chance_val = [0] + [100 * dead[i] / sum(infectious_rate*exposed[:i]) if sum(infectious_rate*exposed[:i])>0 else 0 for i in range(1, len(t))]
        #death_chance_val = np.zeros(days)
        
        r0_normal_val = util.map_function(t, logistic_rt)
        
        infected = np.array(util.sum_respectively([infectious, critical, dead, recovered]))
        
        return t, population_2, susceptible, exposed, infectious, critical, recovered, dead, infected, death_chance_val, r0_normal_val
    
    def fitter(self, x, days, incubation_period,
                    critical_chance, critical_time, 
                    recovery_time_normal, recovery_time_critical,
                    death_chance_normal, death_time_normal,
                    k, **kwargs):
        #days = self.kabko.data_days(self.kabko.outbreak_shift(incubation_period))
        ret = self.model(days, incubation_period,
                    critical_chance, critical_time, 
                    recovery_time_normal, recovery_time_critical,
                    death_chance_normal, death_time_normal,
                    k, **kwargs)
        dead = ret[7]
        return dead[x]
    
    def fit(self):
        mod = lmfit.Model(self.fitter)
        
        self.kabko.apply_params(mod)
        
        outbreak_shift = self.kabko.outbreak_shift(
            self.kabko.params["incubation_period"].init
        )
        
        days = self.kabko.data_days(outbreak_shift)
        
        mod.set_param_hint("days", value=days, vary=False)

        params = mod.make_params()
        
        x_data = np.linspace(0, days - 1, days, dtype=int)
        
        y_data = util.shift_array(
            self.kabko.dead, 
            outbreak_shift
        )

        result = mod.fit(y_data, params, method="least_squares", x=x_data)
        

        #result.plot_fit(datafmt="-");
        
        return result

Model = SeicrdRModel