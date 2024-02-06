from scipy.optimize import curve_fit
from scipy.special import wofz
import numpy as np
import matplotlib.cm as cm
import matplotlib.pyplot as plt


def Lorentzian(x: np.ndarray, center: float, intensity: float, w: float) -> np.ndarray:
    y = w ** 2 / (4 * (x - center) ** 2 + w ** 2)
    return intensity * y


def Gaussian(x: np.ndarray, center: float, intensity: float, sigma: float) -> np.ndarray:
    y = np.exp(-1 / 2 * (x - center) ** 2 / sigma ** 2)
    return intensity * y


def Voigt(x: np.ndarray, center: float, intensity: float, lw: float, gw: float) -> np.ndarray:
    # lw : HWFM of Lorentzian
    # gw : sigma of Gaussian
    if gw == 0:
        gw = 1e-10
    z = (x - center + 1j*lw) / (gw * np.sqrt(2.0))
    w = wofz(z)
    model_y = w.real / (gw * np.sqrt(2.0*np.pi))
    intensity /= model_y.max()
    return intensity * model_y


def linear(x: np.ndarray, a: float, b: float) -> np.ndarray:
    return a * x + b


class Fitter:
    func_names = ['Lorentzian', 'Gaussian', 'Voigt']
    funcs = [Lorentzian, Gaussian, Voigt]

    def __init__(self):
        self.x = None
        self.y = None
        self.xlim = None
        self.params = None
        self.num_func = 0
        self.func = Lorentzian
        self.num_params_per_func = 3

        self.y_sum = None
        self.y_list = []

        self.params_fit = None
        self.pcov = None

    def set_data(self, x: np.ndarray, y: np.ndarray, xlim: np.ndarray) -> None:
        self.xlim = xlim
        fit_range = (xlim[0] <= x) & (x <= xlim[1])
        x = x[fit_range]
        y = y[fit_range]

        self.x = x
        self.y = y

    def set_function(self, name: str) -> None:
        if name == 'Lorentzian':
            self.func = Lorentzian
            self.num_params_per_func = 3
        elif name == 'Gaussian':
            self.func = Gaussian
            self.num_params_per_func = 3
        elif name == 'Voigt':
            self.func = Voigt
            self.num_params_per_func = 4
        else:
            raise ValueError(f'Unsupported function name: {name}')

    def set_params(self, params: list) -> None:
        self.params = params
        self.num_func = int(len(self.params) / self.num_params_per_func)

    def superposition(self, x: np.ndarray, *params) -> np.ndarray:
        # 全てのyを足し合わせ
        self.y_sum = np.zeros_like(x)
        for i in range(self.num_func):
            p = params[i * self.num_params_per_func:(i + 1) * self.num_params_per_func]
            self.y_sum += self.func(x, *p)

        # バックグラウンドを追加
        self.y_sum += linear(x, params[-2], params[-1])

        return self.y_sum

    def fit(self) -> bool:
        if self.params is None:
            return False
        try:
            self.params_fit, self.pcov = curve_fit(self.superposition, self.x, self.y, p0=self.params)
        except RuntimeError:
            return False

        return True

    def make_y_list(self) -> bool:
        if self.x is None or self.y is None or self.params_fit is None:
            return False

        self.y_list = []
        self.y_list.append(self.superposition(self.x, *self.params_fit))
        for i in range(self.num_func):
            p = self.params_fit[i * self.num_params_per_func:(i + 1) * self.num_params_per_func]
            y = self.func(self.x, *p)
            self.y_list.append(y)

        # バックグラウンドを追加
        self.y_list.append(linear(self.x, self.params_fit[-2], self.params_fit[-1]))

        return True

    def draw(self, ax: plt.axes) -> list:
        ok = self.make_y_list()
        if not ok:
            return []

        fitting_result = []
        for i, y in enumerate(self.y_list):
            if i == 0 or i == len(self.y_list) - 1:
                line = ax.plot(self.x, y, color='r')
                fitting_result.append(line[0])
            else:
                fill = ax.fill_between(self.x, y, self.y_list[-1], facecolor=cm.rainbow(i / len(self.y_list)), alpha=0.6)
                fitting_result.append(fill)

        return fitting_result

