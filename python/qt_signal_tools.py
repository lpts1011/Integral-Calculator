"""Signal integration workspace: sampled data, noise, convolution and reconstruction."""
from pathlib import Path

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QPushButton,
    QDoubleSpinBox,QSpinBox,QFileDialog,QPlainTextEdit,QTabWidget)

from math_editor.panel import MathEditorPanel
from math_editor.syntax import FieldRole
from qt_dialogs import show_error_dialog
from qt_jobs import JobRunner
from signal_analysis import (integrate_signal,noise_experiment,
    fourier_reconstruction,generate_and_integrate,load_and_integrate,convolve_expression)
from theme_utils import THEMES, apply_plot_theme


class SignalToolsPanel(QWidget):
    def __init__(self,parent=None,*,panel_factory=MathEditorPanel,text=None,theme_name="Light"):
        super().__init__(parent)
        self.labels=dict(text or {}); self.samples=None; self.theme_name=theme_name
        self.runner=JobRunner(self)
        layout=QVBoxLayout(self)
        intro=QLabel(self.labels.get("signal_intro","Integrate sampled signals using their timestamps. In formulas, x represents time."),self)
        intro.setWordWrap(True); layout.addWidget(intro)
        self.editor=panel_factory(self)
        self.function=self.editor.create_field("signal.expression",FieldRole.EXPRESSION,"sin(2*pi*5*x)",label="Signal x(t):")
        self.impulse=self.editor.create_field("signal.impulse",FieldRole.EXPRESSION,"exp(-x)",label="Impulse response h(t):")
        self.editor.set_theme(theme_name); self.editor.setFixedHeight(205); layout.addWidget(self.editor)
        if hasattr(self.editor,"content_height_changed"):
            self.editor.content_height_changed.connect(lambda height:self.editor.setFixedHeight(min(260,max(180,height))))
        self.controls=QTabWidget(self); self.controls.setMaximumHeight(250); layout.addWidget(self.controls)
        data=QWidget(self); form=QFormLayout(data)
        self.start=QDoubleSpinBox(data); self.start.setRange(-1e6,1e6); self.start.setDecimals(6)
        self.stop=QDoubleSpinBox(data); self.stop.setRange(-1e6,1e6); self.stop.setDecimals(6); self.stop.setValue(1.)
        self.count=QSpinBox(data); self.count.setRange(2,200000); self.count.setValue(1001)
        form.addRow("Start time",self.start); form.addRow("End time",self.stop); form.addRow("Samples",self.count)
        row=QHBoxLayout(); self.generate=QPushButton(self.labels.get("signal_generate","Sample formula"),data)
        self.import_csv=QPushButton(self.labels.get("signal_import","Import CSV"),data)
        self.analyze=QPushButton(self.labels.get("signal_analyze","Integrate data"),data)
        for button in (self.generate,self.import_csv,self.analyze):row.addWidget(button)
        form.addRow(row); self.controls.addTab(data,self.labels.get("signal_data","Sampled data"))
        noise=QWidget(self); nf=QFormLayout(noise)
        self.std=QDoubleSpinBox(noise); self.std.setRange(0,1e6); self.std.setDecimals(5); self.std.setValue(.1)
        self.bias=QDoubleSpinBox(noise); self.bias.setRange(-1e6,1e6); self.bias.setDecimals(5); self.bias.setValue(.05)
        self.seed=QSpinBox(noise); self.seed.setRange(0,2147483647)
        self.window=QSpinBox(noise); self.window.setRange(1,10001); self.window.setSingleStep(2); self.window.setValue(11)
        nf.addRow("Noise standard deviation",self.std);nf.addRow("Simulated constant bias",self.bias)
        nf.addRow("Random seed",self.seed);nf.addRow("Moving-average window",self.window)
        self.noise_button=QPushButton(self.labels.get("signal_noise_run","Compare noise and drift"),noise);nf.addRow(self.noise_button)
        note=QLabel("Processing subtracts the known simulated bias, then filters. A real signal's DC component is not automatically discarded.",noise)
        note.setWordWrap(True);nf.addRow(note);self.controls.addTab(noise,self.labels.get("signal_noise","Noise / drift"))
        conv=QWidget(self); cf=QVBoxLayout(conv)
        self.conv_button=QPushButton(self.labels.get("signal_convolve","Compute convolution integral"),conv);cf.addWidget(self.conv_button)
        conv_note=QLabel("The sampled convolution is multiplied by the sample spacing. Inputs are zero outside the supplied window. Direct and FFT timing are compared within an operation budget.",conv)
        conv_note.setWordWrap(True);cf.addWidget(conv_note);self.controls.addTab(conv,self.labels.get("signal_convolution","Convolution"))
        fourier=QWidget(self);ff=QFormLayout(fourier)
        self.terms=QSpinBox(fourier);self.terms.setRange(0,100000);self.terms.setValue(5)
        ff.addRow("Retained harmonics",self.terms)
        self.fourier_button=QPushButton(self.labels.get("signal_reconstruct","Reconstruct signal"),fourier);ff.addRow(self.fourier_button)
        fn=QLabel("Uniform samples are periodically extended. The displayed period is N × sample spacing. Coefficients approximate Fourier integrals by sampled sums.",fourier)
        fn.setWordWrap(True);ff.addRow(fn);self.controls.addTab(fourier,self.labels.get("signal_fourier","Fourier reconstruction"))
        self.figure=Figure(figsize=(7,4),dpi=100);self.axes=self.figure.subplots(2,1)
        self.canvas=FigureCanvasQTAgg(self.figure);self.canvas.setMinimumHeight(280);layout.addWidget(self.canvas,stretch=1)
        layout.addWidget(NavigationToolbar2QT(self.canvas,self))
        self.output=QPlainTextEdit(self);self.output.setReadOnly(True);self.output.setMinimumHeight(100);self.output.setMaximumHeight(140);layout.addWidget(self.output)
        self.cancel=QPushButton(self.labels.get("cancel_calculation","Cancel calculation"),self);self.cancel.setEnabled(False);layout.addWidget(self.cancel)
        self.buttons=(self.generate,self.import_csv,self.analyze,self.noise_button,self.conv_button,self.fourier_button)
        self.runner.busy_changed.connect(self._busy);self.cancel.clicked.connect(self.runner.cancel)
        self.generate.clicked.connect(self.generate_samples);self.import_csv.clicked.connect(self.load_csv)
        self.analyze.clicked.connect(self.analyze_data);self.noise_button.clicked.connect(self.run_noise)
        self.conv_button.clicked.connect(self.run_convolution);self.fourier_button.clicked.connect(self.run_fourier)
        self.destroyed.connect(self.runner.close)
        self._clear_axes()

    def _busy(self,busy):
        for button in self.buttons:button.setEnabled(not busy)
        self.cancel.setEnabled(busy)

    def _error(self,error):
        self.output.setPlainText(str(error));show_error_dialog(self,"Signal analysis",str(error))

    def _job(self,function,args,present):
        self.output.setPlainText(self.labels.get("computing","Computing…"))
        return self.runner.submit(function,args,present,self._error,timeout=12)

    def _data(self):
        if self.samples is None:
            self._error(ValueError("Sample a formula or import a CSV first."));return None
        return self.samples

    def generate_samples(self):
        self._job(generate_and_integrate,(self.function.get_text(),self.start.value(),self.stop.value(),self.count.value()),self.show_integral)

    def load_csv(self):
        path,_=QFileDialog.getOpenFileName(self,"Import time,value CSV","","CSV files (*.csv);;All files (*)")
        if not path:return
        try:
            if Path(path).stat().st_size > 32*1024*1024:raise ValueError("CSV is larger than the 32 MB import budget.")
            text=Path(path).read_text(encoding="utf-8-sig")
        except Exception as error:self._error(error);return
        self._job(load_and_integrate,(text,),self.show_integral)

    def analyze_data(self):
        data=self._data()
        if data:self._job(integrate_signal,(data["time"],data["signal"]),self.show_integral)

    def _clear_axes(self):
        for axis in self.axes:
            axis.clear()
            theme=THEMES.get(self.theme_name,THEMES["Light"])
            apply_plot_theme(self.figure,axis,theme);axis.grid(True,alpha=.2)

    def _draw(self):
        self.figure.tight_layout();self.canvas.draw_idle()

    def show_integral(self,result):
        self.samples=result;self._clear_axes()
        self.axes[0].plot(result["time"],result["signal"]);self.axes[0].set_ylabel("Signal")
        self.axes[1].plot(result["time"],result["cumulative"]);self.axes[1].set_ylabel("Cumulative integral")
        self.axes[1].set_xlabel("Time");self._draw()
        self.output.setPlainText(f"Samples: {result['samples']}   Duration: {result['duration']:.10g}\nIntegral: {result['integral']:.12g}\nMean: {result['mean']:.12g}   RMS: {result['rms']:.12g}\nSignal energy ∫|x(t)|²dt: {result['energy']:.12g}\nMethod: {result['method']}\nSampling and measurement errors are not included in a certified error bound.")

    def run_noise(self):
        data=self._data()
        if data:self._job(noise_experiment,(data["time"],data["signal"],self.std.value(),self.bias.value(),self.seed.value(),self.window.value()),self.show_noise)

    def show_noise(self,result):
        self._clear_axes()
        for name in ("clean","measured","filtered"):self.axes[0].plot(result["time"],result[name],label=name)
        for name in ("raw","processed"):
            self.axes[1].plot(result["time"],result[name]["cumulative"]-result["truth"]["cumulative"],label=name)
        self.axes[0].legend();self.axes[1].legend();self.axes[1].set_ylabel("Integral error");self.axes[1].set_xlabel("Time");self._draw()
        self.output.setPlainText(f"Expected bias drift bT: {result['expected_bias_drift']:.12g}\nMeasured integral error: {result['raw_integral_error']:.12g}\nProcessed integral error: {result['processed_integral_error']:.12g}\nSeed: {result['seed']}   Filter window: {result['window']}\nFiltering can also distort the signal; inspect the curves and errors.")

    def run_convolution(self):
        data=self._data()
        if data:self._job(convolve_expression,(data["time"],data["signal"],self.impulse.get_text()),self.show_convolution)

    def show_convolution(self,result):
        self._clear_axes();self.axes[0].plot(result["time"],result["output"]);self.axes[0].set_ylabel("Convolution output")
        self.axes[1].bar(list(result["timings"]),list(result["timings"].values()));self.axes[1].set_ylabel("Median time (s)");self._draw()
        self.output.setPlainText(f"Sample spacing: {result['dt']:.10g}\nDirect / FFT maximum difference: {result['difference']}\n{result['direct_status']}\n{result['boundary']}\nTimings: {result['timings']}")

    def run_fourier(self):
        data=self._data()
        if data:self._job(fourier_reconstruction,(data["time"],data["signal"],self.terms.value()),self.show_fourier)

    def show_fourier(self,result):
        self._clear_axes();self.axes[0].plot(result["time"],result["signal"],label="Original")
        self.axes[0].plot(result["time"],result["reconstructed"],label="Reconstructed");self.axes[0].legend()
        self.axes[1].plot(result["time"],result["error"]);self.axes[1].set_ylabel("Reconstruction error");self.axes[1].set_xlabel("Time");self._draw()
        self.output.setPlainText(f"Harmonics: {result['terms']}   Period: {result['period']:.12g}\nRMS error: {result['rms_error']:.12g}\nMaximum error: {result['max_error']:.12g}\n{result['assumption']}")
