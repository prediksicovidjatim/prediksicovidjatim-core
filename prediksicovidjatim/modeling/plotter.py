import matplotlib.pyplot as plt
from .. import util

class ModelPlotter:
    def __init__(self, kabko, result):
        self.kabko = kabko
        self.result = result
        self.tanggal = self.get_tanggal(len(result.t))
        #config.init_plot()
        
    def plot_r0(self, ax):
        if self.result.r0_normal is not None:
            self._plot(ax, self.result.r0_normal, 'y', alpha=0.5, linewidth=2, label='R0 normal')
        if self.result.r0_over is not None:
            self._plot(ax, self.result.r0_over, 'r', alpha=0.5, linewidth=2, label='R0 over')
        if self.result.r0_overall is not None:
            self._plot(ax, self.result.r0_overall, 'orange', alpha=0.7, linewidth=2, label='R0 overall')

        ax.title.set_text('R0 over time')
        
    def get_tanggal(self, length, shift=0, previous_shift=None):
        if previous_shift is None:
            previous_shift = self.kabko.last_outbreak_shift
        length_full = length - previous_shift
        return self.kabko.get_tanggal(shift, length_full)
        
    def revert_shift(self, arr, previous_shift=None, preceeding_zero=True):
        if previous_shift is None:
            previous_shift = self.kabko.last_outbreak_shift
        return util.shift_array(arr, -previous_shift, preceeding_zero=preceeding_zero)
        
    def plot_mortality_rate(self, ax):
        if self.result.mortality_rate is not None:
            self._plot(ax, self.result.mortality_rate, label="Mortality rate", color="orange")
            ax.title.set_text('Mortality Rate over Time')
        
    def plot_over(self, ax):
        if self.result.exposed_over is not None:
            self._plot(ax, self.result.exposed_over, 'blue', alpha=0.7, linewidth=2, label='Exposed by Neglected')
        if self.result.critical_over is not None:
            self._plot(ax, self.result.critical_over(), 'orange', alpha=0.7, linewidth=2, label="Critical but Neglected")
        if self.result.dead_over is not None:
            self._plot(ax, self.result.dead_over, 'black', alpha=0.7, linewidth=2, label='Dead by Neglect')
        if self.result.over is not None:
            self._plot(ax, self.result.over(), 'grey', alpha=0.7, linewidth=2, label='Total Over')
        
        ax.title.set_text('Insufficient Healthcare')
        
    def plot_dead(self, ax):
        if self.result.dead_normal is not None:
            self._plot(ax, self.result.dead_normal, 'blue', alpha=0.7, linewidth=2, label='Dead (Normal)')
        if self.result.dead_over is not None:
            self._plot(ax, self.result.dead_over, 'red', alpha=0.7, linewidth=2, label="Dead by Neglect")
        if self.result.dead is not None:
            self._plot(ax, self.result.dead(), 'black', alpha=0.7, linewidth=2, label='Dead (Total)')
        
        ax.title.set_text('Death')
        
    def plot_healthcare(self, ax):
        if self.result.critical is not None:
            self._plot(ax, self.result.critical, 'orange', alpha=0.7, linewidth=2, label='Critical')
        if self.result.critical_cared is not None:
            self._plot(ax, self.result.critical_cared(), 'blue', alpha=0.7, linewidth=2, label='Critical cared')
        if self.result.critical_over is not None:
            self._plot(ax, self.result.critical_over(), 'red', alpha=0.7, linewidth=2, label='Critical over')
        if self.result.kapasitas_rs is not None:
            self._plot(ax, self.result.kapasitas_rs, 'grey', alpha=0.7, linewidth=2, label="Healthcare Limit")
        
        ax.title.set_text('Healthcare limit')
        
    def _plot(self, ax, y, *args, shift=0, previous_shift=None, preceeding_zero=True, **kwargs):
        #x = self.get_tanggal(x, shift=shift, previous_shift=previous_shift) if previous_shift is not None else x
        y = self.revert_shift(y, previous_shift=previous_shift, preceeding_zero=preceeding_zero)
        x = self.tanggal[:len(y)]
        return ax.plot(x, y, *args, **kwargs)
        
    def plot(self, f, *args, **kwargs):
        fig, ax = plt.subplots(1, 1)
        f(ax, *args, **kwargs)
        util.post_plot(ax)
        util.date_plot(ax)
        return fig
        
    def plot_main(self, ax):
        self._plot_main(ax, susceptible=self.result.susceptible, exposed=self.result.exposed(), infectious=self.result.infectious, critical=self.result.critical, recovered=self.result.recovered(), dead=self.result.dead(), kapasitas_rs=self.result.kapasitas_rs, population=self.result.population, title="Main (Total)")
        
    def plot_main_lite(self, ax):
        self._plot_main(ax, exposed=self.result.exposed(), infectious=self.result.infectious, critical=self.result.critical, recovered=self.result.recovered(), dead=self.result.dead(), kapasitas_rs=self.result.kapasitas_rs, title="Main (Total, Lite)")
    
    def plot_main_data(self, ax, datasets, previous_shift=None):
        self._plot_data(
            ax, 
            **self.result.get_datasets(datasets),
            kapasitas_rs=self.result.kapasitas_rs,
            is_data=False
        )
        data = self.kabko.get_datasets(datasets)
        self._plot_data(
            ax, 
            is_data=True,
            **data
        )
        ax.title.set_text("Model-Data Comparison")
        
    def _plot_data(self, ax, infectious=None, critical_cared=None, infectious_all=None, recovered=None, dead=None, infected=None, kapasitas_rs=None, is_data=False):
        line_style = "-" if is_data else "-"
        label_suffix = " (data)" if is_data else " (model)"
        alpha = 0.7 if is_data else 0.4
        line_width = 3 if is_data else 2
        previous_shift = 0 if is_data else None
        if infectious is not None:
            self._plot(ax, infectious, 'blue', alpha=alpha, label='Infectious'+label_suffix, linewidth=line_width, ls=line_style, previous_shift=previous_shift)
        if critical_cared is not None:
            self._plot(ax, critical_cared, 'red', alpha=alpha, label='Positif Rawat RS'+label_suffix, linewidth=line_width, ls=line_style, previous_shift=previous_shift)
        if infectious_all is not None:
            self._plot(ax, infectious_all, 'purple', alpha=alpha, label='Positif Aktif'+label_suffix, linewidth=line_width, ls=line_style, previous_shift=previous_shift)
        if recovered is not None:
            self._plot(ax, recovered, 'green', alpha=alpha, label='Positif Sembuh'+label_suffix, linewidth=line_width, ls=line_style, previous_shift=previous_shift)
        if dead is not None:
            self._plot(ax, dead, 'black', alpha=alpha, label='Positif Meninggal'+label_suffix, linewidth=line_width, ls=line_style, previous_shift=previous_shift)
        if infected is not None:
            self._plot(ax, infected, 'grey', alpha=alpha, label='Positif Total'+label_suffix, linewidth=line_width, ls=line_style, previous_shift=previous_shift)
        if kapasitas_rs is not None:
            self._plot(ax, kapasitas_rs, 'orange', alpha=0.3, label='Kapasitas RS', ls=':', previous_shift=previous_shift, preceeding_zero=False)
        
        
    def _plot_main(self, ax, susceptible=None, exposed=None, infectious=None, critical=None, recovered=None, dead=None, kapasitas_rs=None, population=None, title="Main", line_style="-"):
        if susceptible is not None:
            self._plot(ax, susceptible, 'b', alpha=0.7, label='Susceptible', ls=line_style, preceeding_zero=False)
        if exposed is not None:
            self._plot(ax, exposed, 'y', alpha=0.7, label='Exposed', ls=line_style)
        if infectious is not None:
            self._plot(ax, infectious, 'r', alpha=0.7, label='Infectious', ls=line_style)
        if critical is not None:
            self._plot(ax, critical, 'orange', alpha=0.7, label='Critical', ls=line_style)
        if recovered is not None:
            self._plot(ax, recovered, 'g', alpha=0.7, label='Recovered', ls=line_style)
        if dead is not None:
            self._plot(ax, dead, 'black', alpha=0.7, label='Dead', ls=line_style)
        if kapasitas_rs is not None:
            self._plot(ax, kapasitas_rs, 'red', alpha=0.3, label='Healthcare', ls='dotted')
        if population is not None:
            self._plot(ax, population, 'grey', alpha=0.3, label='Population', ls='dotted', preceeding_zero=False)
        
        ax.title.set_text(title)

    def plot_daily(self, ax):
        self._plot_main(ax, susceptible=self.result.daily_susceptible(), exposed=self.result.daily_exposed(), infectious=self.result.daily_infectious(), critical=self.result.daily_critical(), recovered=self.result.daily_recovered(), dead=self.result.daily_dead(), title="Main (Harian)")

    def plot_daily_lite(self, ax):
        self._plot_main(ax, exposed=self.result.daily_exposed(), infectious=self.result.daily_infectious(), critical=self.result.daily_critical(), recovered=self.result.daily_recovered(), dead=self.result.daily_dead(), title="Main (Harian)")
        