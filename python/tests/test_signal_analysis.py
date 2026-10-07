import math
import unittest
import calengine as np
from signal_analysis import *


class SignalAnalysisTests(unittest.TestCase):
    def test_csv_header_and_irregular_timestamps(self):
        t,y=read_signal_csv("time,value\n0,0\n0.1,0.2\n0.7,1.4\n1,2\n")
        result=integrate_signal(t,y)
        self.assertAlmostEqual(result["integral"],1.,places=12)
        self.assertEqual(result["cumulative"][0],0.)

    def test_invalid_csv_and_nonincreasing_times_are_rejected(self):
        for text in ("time,value\n0,1\n0,2","0,1\n1,nan","0,1,2\n1,2,3","time,value\n0,1"):
            with self.subTest(text=text),self.assertRaises(ValueError):read_signal_csv(text)

    def test_constant_signal_rms_mean_energy_and_cumulative_integral(self):
        t=np.linspace(0,2,1001);result=integrate_signal(t,np.full(len(t),3.))
        self.assertAlmostEqual(result["rms"],3.,places=12)
        self.assertAlmostEqual(result["energy"],18.,places=10)
        self.assertAlmostEqual(result["mean"],3.,places=12)
        self.assertAlmostEqual(result["integral"],6.,places=10)

    def test_sine_has_expected_rms(self):
        result=integrate_signal(*sample_expression("sin(2*pi*x)",0,1,1001))
        self.assertAlmostEqual(result["rms"],1/math.sqrt(2),places=10)
        self.assertAlmostEqual(result["integral"],0.,places=10)

    def test_pure_bias_drift_and_correction(self):
        t=np.linspace(0,10,1001);result=noise_experiment(t,np.zeros(len(t)),noise_std=0,bias=.2,window=1)
        self.assertAlmostEqual(result["raw_integral_error"],2.,places=10)
        self.assertAlmostEqual(result["processed_integral_error"],0.,places=12)
        self.assertEqual(result["expected_bias_drift"],2.)

    def test_noise_seed_and_filter_preserve_real_dc(self):
        t=np.linspace(0,1,1001);clean=np.full(len(t),5.)
        one=noise_experiment(t,clean,.1,.2,17,11);two=noise_experiment(t,clean,.1,.2,17,11)
        self.assertTrue(np.array_equal(one["measured"],two["measured"]))
        self.assertAlmostEqual(one["processed"]["mean"],5.,places=2)

    def test_direct_and_fft_convolution_agree_and_include_dt(self):
        t=np.linspace(0,1,101);ones=np.ones(len(t));result=convolution_analysis(t,ones,ones)
        self.assertLess(result["difference"],1e-12)
        self.assertAlmostEqual(result["output"][100],1.01,places=12)
        self.assertEqual(len(result["output"]),201)
        self.assertAlmostEqual(result["time"][-1],2.)

    def test_nonuniform_grid_is_rejected_by_convolution_and_fourier(self):
        t=[0,.1,.4,1.];y=[1,2,3,4]
        with self.assertRaises(ValueError):convolution_analysis(t,y,y)
        with self.assertRaises(ValueError):fourier_reconstruction(t,y)

    def test_fourier_reconstructs_retained_harmonics(self):
        t=np.arange(1024)/1024;signal=np.sin(2*np.pi*5*t)+.5*np.cos(2*np.pi*2*t)
        result=fourier_reconstruction(t,signal,5)
        self.assertLess(result["max_error"],1e-13)
        self.assertAlmostEqual(result["period"],1.)
        low=fourier_reconstruction(t,signal,2)
        self.assertAlmostEqual(low["rms_error"],1/math.sqrt(2),places=12)

    def test_fourier_dc_and_nyquist_limits(self):
        t=np.arange(32)/32
        result=fourier_reconstruction(t,np.full(32,3.),0)
        self.assertLess(result["max_error"],1e-12)
        with self.assertRaises(ValueError):fourier_reconstruction(t,np.ones(32),17)


if __name__=="__main__":unittest.main()
