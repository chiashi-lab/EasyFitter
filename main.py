import os
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinterdnd2 import Tk, DND_FILES, TkinterDnD
import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from dataloader import DataLoader
from Fitter import Fitter


font_lg = ('Arial', 24)
font_md = ('Arial', 16)
font_sm = ('Arial', 12)


def is_num(s):
    if s == '':
        return True
    try:
        float(s)
    except ValueError:
        return False
    else:
        return True


class PGraph(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master

        self.dl = DataLoader()
        self.spec = None
        self.fitter = Fitter()
        self.fitter.set_function('Lorentzian')

        self.num_peaks = 0
        self.idx_deleted = []
        self.selected_peak_objs = []
        self.result_objs = []

        # ピーク矩形選択用
        self.rect_drawing = None
        self.x0 = 0
        self.y0 = 0
        self.x1 = 0
        self.y1 = 0
        self.drawing = False

        self.create_widgets()

    def create_widgets(self):
        # スタイル設定
        style = ttk.Style()
        style.theme_use('winnative')
        style.configure('TButton', font=font_md, width=14, padding=[0, 4, 0, 4], foreground='black')
        style.configure('R.TButton', font=font_md, width=14, padding=[0, 4, 0, 4], foreground='red')
        style.configure('TLabel', font=font_sm, padding=[0, 4, 0, 4], foreground='black')
        style.configure('Color.TLabel', font=font_lg, padding=[0, 0, 0, 0], width=4, background='black')
        style.configure('TEntry', font=font_md, width=14, padding=[0, 4, 0, 4], foreground='black')
        style.configure('TCheckbutton', font=font_md, padding=[0, 4, 0, 4], foreground='black')
        style.configure('TMenubutton', font=font_md, padding=[20, 4, 0, 4], foreground='black')
        style.configure('TTreeview', font=font_md, foreground='black')

        self.frame_graph = ttk.LabelFrame(self, text='Graph')
        self.frame_param = ttk.LabelFrame(self, text='Parameters')
        frame_info = ttk.LabelFrame(self, text='Info')
        self.frame_graph.grid(row=0, column=0, rowspan=100, sticky=tk.NSEW)
        self.frame_param.grid(row=0, column=1, sticky=tk.NSEW)
        frame_info.grid(row=1, column=1, sticky=tk.NSEW)

        # Graph
        self.width = 900
        self.height = 600
        dpi = 100
        if os.name == 'posix':
            self.width /= 2
            self.height /= 2
            dpi /= 2
        fig = plt.figure(figsize=(self.width / dpi, self.height / dpi), dpi=dpi)
        fig.canvas.mpl_connect('button_press_event', self.on_press)
        fig.canvas.mpl_connect('motion_notify_event', self.draw_preview)
        fig.canvas.mpl_connect('button_release_event', self.on_release)
        self.ax = fig.add_subplot()
        self.canvas = FigureCanvasTkAgg(fig, master=self.frame_graph)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.frame_graph, pack_toolbar=False)
        self.canvas.get_tk_widget().grid(row=0, column=0)
        self.toolbar.grid(row=1, column=0)

        # Parameters
        self.peak_widgets = []
        label_peak_name = ttk.Label(self.frame_param, text='Name')
        label_peak_center = ttk.Label(self.frame_param, text='Center')
        label_peak_intensity = ttk.Label(self.frame_param, text='Intensity')
        label_peak_width = ttk.Label(self.frame_param, text='Width')
        button_add_peak = ttk.Button(self.frame_param, text='Add Peak', command=self.add_peak)
        label_baseline_name = ttk.Label(self.frame_param, text='Baseline = ')
        self.entry_baseline_a = ttk.Entry(self.frame_param, validate='key', validatecommand=(self.register(is_num), '%P'))
        self.entry_baseline_a.insert(tk.END, '0')
        label_x = ttk.Label(self.frame_param, text='* x +')
        self.entry_baseline_b = ttk.Entry(self.frame_param, validate='key', validatecommand=(self.register(is_num), '%P'))
        self.entry_baseline_b.insert(tk.END, '0')
        button_fit = ttk.Button(self.frame_param, text='Fit', command=self.execute_fitting)
        label_peak_name.grid(row=0, column=0)
        label_peak_center.grid(row=0, column=1)
        label_peak_intensity.grid(row=0, column=2)
        label_peak_width.grid(row=0, column=3)
        button_add_peak.grid(row=1000, column=0, columnspan=4, sticky=tk.EW)
        label_baseline_name.grid(row=1001, column=0)
        self.entry_baseline_a.grid(row=1001, column=1)
        label_x.grid(row=1001, column=2)
        self.entry_baseline_b.grid(row=1001, column=3)
        button_fit.grid(row=1002, column=0, columnspan=5, sticky=tk.EW)

        # Info
        label_info = ttk.Label(frame_info, text=
        'ドラッグ&ドロップでファイルを読み込みます．\n'
        'グラフ上で矩形を描くことでもピークを追加できます（ズーム・パン非選択状態）．\n'
        '結果は小数第三位で丸めています．\n'
        'ローレンツ関数でフィッティングしています．')
        label_info.grid(row=0, column=0)

    def add_peak(self, center: float = 100, intensity: float = 100, width: float = 1) -> None:
        vcm = (self.register(is_num), '%P')
        self.num_peaks += 1
        label_peak = ttk.Label(self.frame_param, text=f'Peak {self.num_peaks}')
        entry_center = ttk.Entry(self.frame_param, validate='key', validatecommand=vcm)
        entry_center.insert(tk.END, str(round(center, 3)))
        entry_intensity = ttk.Entry(self.frame_param, validate='key', validatecommand=vcm)
        entry_intensity.insert(tk.END, str(round(intensity, 3)))
        entry_width = ttk.Entry(self.frame_param, validate='key', validatecommand=vcm)
        entry_width.insert(tk.END, str(round(width, 3)))
        button_delete = ttk.Button(self.frame_param, text='Delete', command=self.generate_delete_command(self.num_peaks-1))
        label_peak.grid(row=self.num_peaks, column=0)
        entry_center.grid(row=self.num_peaks, column=1)
        entry_intensity.grid(row=self.num_peaks, column=2)
        entry_width.grid(row=self.num_peaks, column=3)
        button_delete.grid(row=self.num_peaks, column=4)
        self.peak_widgets.append([label_peak, entry_center, entry_intensity, entry_width, button_delete])

        x0, x1 = center - width / 2, center + width / 2
        y0, y1 = 0, intensity
        r = patches.Rectangle((x0, y0), width, intensity, linewidth=0.5, edgecolor='r', facecolor=(1, 0, 0, 0.1))
        self.ax.add_patch(r)
        self.selected_peak_objs.append(r)
        self.canvas.draw()

    def delete_peak(self, idx) -> None:
        for w in self.peak_widgets[idx]:
            w.destroy()
        self.idx_deleted.append(idx)

    def generate_delete_command(self, idx) -> callable:
        return lambda: self.delete_peak(idx)

    def execute_fitting(self) -> None:
        self.fitter.set_data(self.spec.xdata, self.spec.ydata, self.ax.get_xlim())
        self.set_params()
        ok = self.fitter.fit()
        if not ok:
            messagebox.showwarning('Warning', 'Fitting failed.')
            return
        self.remove_selected_peak_objs_all()
        self.remove_result_objs()
        self.result_objs = self.fitter.draw(self.ax)
        self.canvas.draw()
        self.show_params_fit()

    def set_params(self) -> None:
        params = []
        for i, w in enumerate(self.peak_widgets):
            if i in self.idx_deleted:
                continue
            center = float(w[1].get())
            intensity = float(w[2].get())
            width = float(w[3].get())
            params.extend([center, intensity, width])
        a = float(self.entry_baseline_a.get())
        b = float(self.entry_baseline_b.get())
        params.extend([a, b])
        self.fitter.set_params(params)

    def show_params_fit(self) -> None:
        for i, p in enumerate(self.fitter.params_fit):
            idx_widget = i // 3
            if idx_widget in self.idx_deleted:
                continue
            if idx_widget >= self.fitter.num_func:
                break
            self.peak_widgets[idx_widget][i % 3 + 1].delete(0, tk.END)
            self.peak_widgets[idx_widget][i % 3 + 1].insert(tk.END, str(round(p, 3)))
        self.entry_baseline_a.delete(0, tk.END)
        self.entry_baseline_a.insert(tk.END, str(round(self.fitter.params_fit[-2], 3)))
        self.entry_baseline_b.delete(0, tk.END)
        self.entry_baseline_b.insert(tk.END, str(round(self.fitter.params_fit[-1], 3)))

    def load_file(self, event: TkinterDnD.DnDEvent) -> None:
        if event.data[0] == '{':
            filenames = list(map(lambda x: x.strip('{').strip('}'), event.data.split('} {')))
        else:
            filenames = event.data.split()
        if len(filenames) > 1:
            messagebox.showwarning('Warning', 'Multiple files detected. Only the first file will be loaded.')
            return
        self.dl.load_file(filename=filenames[0])
        self.spec = self.dl.spec_dict[filenames[0]]
        self.refresh()

    def refresh(self) -> None:
        self.ax.cla()
        self.ax.plot(self.spec.xdata, self.spec.ydata, color=self.spec.color)
        self.canvas.draw()

    def show_result_objs(self) -> None:
        for obj in self.result_objs:
            obj.set_visible(True)
        self.canvas.draw()

    def hide_result_objs(self) -> None:
        for obj in self.result_objs:
            obj.set_visible(True)
        self.canvas.draw()

    def remove_selected_peak_objs(self, idx: int) -> None:
        self.selected_peak_objs[idx].remove()
        self.canvas.draw()

    def remove_selected_peak_objs_all(self) -> None:
        for obj in self.selected_peak_objs:
            obj.remove()
        self.selected_peak_objs = []

    def remove_result_objs(self) -> None:
        for obj in self.result_objs:
            obj.remove()
        self.result_objs = []

    def quit(self) -> None:
        self.master.quit()
        self.master.destroy()

    # 以下ピーク矩形選択用の関数
    def on_press(self, event):
        if event.button != 1:
            return
        # Toolbarのズーム・パン機能を使っている状態では動作しないようにする
        if self.toolbar._buttons['Zoom'].var.get() or self.toolbar._buttons['Pan'].var.get():
            return
        self.x0 = event.xdata
        self.y0 = event.ydata
        self.x1 = event.xdata
        self.y1 = event.ydata
        self.drawing = True

    def on_release(self, event):
        if event.xdata is None or event.ydata is None:
            return
        if event.inaxes != self.ax:
            return
        # Toolbarのズーム機能を使っている状態では動作しないようにする
        if self.toolbar._buttons['Zoom'].var.get() or self.toolbar._buttons['Pan'].var.get():
            return

        # プレビュー用の矩形を消す
        if self.rect_drawing is not None:
            self.rect_drawing.remove()
            self.rect_drawing = None

        self.drawing = False

        self.x1 = event.xdata
        self.y1 = event.ydata
        if self.x0 == self.x1 or self.y0 == self.y1:
            return
        x0, x1 = sorted([self.x0, self.x1])
        y0, y1 = sorted([self.y0, self.y1])
        center = (x0 + x1) / 2
        intensity = y1 - y0
        width = x1 - x0
        self.add_peak(center, intensity, width)
        self.canvas.draw()

    def draw_preview(self, event):
        if event.xdata is None or event.ydata is None:
            return
        if not self.drawing:
            return
        # Toolbarのズーム機能を使っている状態では動作しないようにする
        if self.toolbar._buttons['Zoom'].var.get() or self.toolbar._buttons['Pan'].var.get():
            return
        if self.rect_drawing is not None:
            self.rect_drawing.remove()
        x1 = event.xdata
        y1 = event.ydata
        self.rect_drawing = patches.Rectangle((self.x0, self.y0), x1 - self.x0, y1 - self.y0, linewidth=0.5,
                                              edgecolor='r', linestyle='dashed', facecolor='none')
        self.ax.add_patch(self.rect_drawing)
        self.canvas.draw()


def main():
    root = Tk()
    root.title('PGraph')

    app = PGraph(master=root)
    root.drop_target_register(DND_FILES)
    root.protocol('WM_DELETE_WINDOW', app.quit)
    root.dnd_bind('<<Drop>>', app.load_file)
    app.grid(sticky=tk.NSEW)
    app.mainloop()


if __name__ == '__main__':
    main()
