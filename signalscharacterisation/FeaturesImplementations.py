from timeit import default_timer as timer

from scipy import stats
from spectrum import *
from statsmodels.tsa.ar_model import AR
from statsmodels.tsa.stattools import acf

from signalscharacterisation import FeaturesCalcHelper


class FeaturesImplementations:
    """
    This class implements a set of methods, each provide some characteristics of their input signal, x, according to
    the provided settings. It is assumed that the signal x is m by n, where m is the number of channels and n is the
    number of time points (samples).
    """
    features_list = ["accumulated_energy", "moments_channels", "freq_bands_measures", "dyadic_spectrum_measures",
                     "spectral_edge_freq", "correlation_channels_time", "correlation_channels_freq", "h_jorth",
                     "hjorth_fractal_dimension", "petrosian_fractal_dimension", "katz_fractal_dimension",
                     "hurst_fractal_dimension", "detrended_fluctuation", "autocorrelation", "autoregression"]

    @staticmethod
    def get_features_list():
        return FeaturesImplementations.features_list

    @staticmethod
    def accumulated_energy(x, settings):
        """
        Calculates the accumulated energy of the signal. See ??? for more information.

        :param x: the input signal. Its size is (number of channels, samples).
        :param settings: it provides a dictionary that includes an attribute "window_size" in which the energy is
            calculated.
        :return: is a dictionary that includes:
            "final_values":     is an array with the size "number of channels", each indicates the accumulated energy
            in that channel.
             "function_name":   that is the name of this function ("accumulated_energy").
             "time":            the amount of time in seconds that the calculations required.
        """
        window_size = settings["energy_window_size"]

        total_time = timer()
        x_size = x.shape

        k = 0
        variances = np.zeros((x_size[0], int(np.floor(x_size[1] / window_size))), dtype=np.float32)
        for i in range(0, x_size[1] - window_size, window_size):
            variances[:, k] = np.var(x[:, i:i + window_size], axis=1)
            k = k + 1

        total_time = timer() - total_time
        results = FeaturesCalcHelper.fill_results(["energy"],
                                                  [np.sum(variances, axis=1)], "accumulated_energy", [total_time])
        return results

    @staticmethod
    def moments_channels(x, settings):
        """
        Calculates mean, variance, skewness, and kurtosis of the given signal.
        :param x: the input signal. Its size is (number of channels, samples).
        :param settings:
        :return:
        """

        t = timer()
        mean_values = np.nanmean(x, axis=1)
        mean_time = timer() - t
        t = timer()
        variance_values = np.nanvar(x, axis=1)
        variance_time = timer() - t
        t = timer()
        skewness_values = stats.skew(x, axis=1)
        skewness_time = timer() - t
        t = timer()
        kurtosis_values = stats.kurtosis(x, axis=1)
        kurtosis_time = timer() - t

        results = FeaturesCalcHelper.fill_results(["mean", "variance", "skewness", "kurtosis"],
                                                  [mean_values, variance_values, skewness_values, kurtosis_values],
                                                  "moments_channels",
                                                  [mean_time, variance_time, skewness_time, kurtosis_time])

        return results

    @staticmethod
    def freq_bands_measures(x, settings):
        """
        :param x: the input signal. Its size is (number of channels, samples).
        :param settings:
        :return:
        """
        sampling_freq = settings["sampling_freq"]
        time = [0, 0]
        x = np.transpose(x)

        t = timer()
        freq_levels = FeaturesCalcHelper.eeg_standard_freq_bands()
        power_spectrum = FeaturesCalcHelper.calc_spectrum(x, freq_levels, sampling_freq)
        time[0] = timer() - t
        t = timer()
        shannon_entropy = -1 * np.sum(np.multiply(power_spectrum, np.log(power_spectrum)), axis=0)
        time[1] = timer() - t
        results = FeaturesCalcHelper.fill_results(["power spectrum", "shannon entropy"],
                                                  [power_spectrum, shannon_entropy],
                                                  "freq_bands_measures", time)

        return results

    @staticmethod
    def dyadic_spectrum_measures(x, settings):
        """

        :param x: the input signal. Its size is (number of channels, samples).
        :param settings:
        :return:
        """

        sampling_freq = settings["sampling_freq"]
        type_corr = settings["corr_type"]
        time = [0, 0, 0]
        x = np.transpose(x)
        n_samples = x.shape[0]
        lvl_d = np.floor(n_samples / 2)
        n_lvls = int(np.floor(np.log2(lvl_d)))
        dyadic_freq_levels = np.zeros(n_lvls + 1)
        coef = sampling_freq / n_samples

        for i in range(n_lvls + 1):
            dyadic_freq_levels[i] = lvl_d * coef
            lvl_d = np.floor(lvl_d / 2)

        dyadic_freq_levels = np.flipud(dyadic_freq_levels)
        t = timer()
        power_spectrum = FeaturesCalcHelper.calc_spectrum(x, dyadic_freq_levels, sampling_freq)
        time[0] = timer() - t
        t = timer()
        shannon_entropy = -1 * np.sum(np.multiply(power_spectrum, np.log(power_spectrum)), axis=0)
        time[1] = timer() - t
        t = timer()
        power_spec_corr = FeaturesCalcHelper.calc_corr(np.transpose(power_spectrum))
        iu = np.triu_indices(power_spec_corr.shape[0], 1)
        power_spec_corr = power_spec_corr[iu]
        time[2] = timer() - t
        results = FeaturesCalcHelper.fill_results(["power spectrum", "shannon entropy", "dyadic powers corr"],
                                                  [power_spectrum, shannon_entropy, power_spec_corr],
                                                  "dyadic_spectrum_measures", time)

        return results

    @staticmethod
    def spectral_edge_freq(x, settings):
        """

        :param x: the input signal. Its size is (number of channels, samples).
        :param settings:
        :return:
        """
        sfreq = settings["sampling_freq"]
        tfreq = settings["spectral_edge_tfreq"]
        ppow = settings["spectral_edge_power_coef"]
        x = np.transpose(x)
        n_samples = x.shape[0]

        t = timer()
        topfreq = int(round(n_samples / sfreq * tfreq)) + 1

        D = FeaturesCalcHelper.calc_normalized_fft(x)
        A = np.cumsum(D[:topfreq, :], axis=0)
        B = A - (A.max() * ppow)
        spedge = np.min(np.abs(B), axis=0)
        spedge = (spedge - 1) / (topfreq - 1) * tfreq

        t = timer() - t

        results = FeaturesCalcHelper.fill_results(["spectral edge freq"], [spedge],
                                                  "spectral_edge_freq", [t])
        return results

    @staticmethod
    def correlation_channels_time(x, settings):
        """

        :param x: the input signal. Its size is (number of channels, samples).
        :param settings:
        :return:
        """

        time = [0, 0]

        t = timer()
        channels_correlations = FeaturesCalcHelper.calc_corr(x)
        time[0] = timer() - t

        t = timer()
        eigs = FeaturesCalcHelper.cal_eigens(channels_correlations)
        channels_correlations_eigs = eigs["lambda"]
        time[1] = timer() - t

        iu = np.triu_indices(channels_correlations.shape[0], 1)
        channels_correlations = channels_correlations[iu]

        results = FeaturesCalcHelper.fill_results(["correlation_channels", "lambda"],
                                                  [channels_correlations, channels_correlations_eigs],
                                                  "correlation_channels_time", [time])
        return results

    @staticmethod
    def correlation_channels_freq(x, settings):
        """

        :param x: the input signal. Its size is (number of channels, samples).
        :param settings:
        :return:
        """
        # Calculate correlation matrix and its eigenvalues (b/w channels)
        time = [0, 0]

        t = timer()
        d = np.transpose(FeaturesCalcHelper.calc_normalized_fft(np.transpose(x)))
        channels_correlations = FeaturesCalcHelper.calc_corr(d)
        time[0] = timer() - t
        t = timer()
        eigs = FeaturesCalcHelper.cal_eigens(channels_correlations)
        channels_correlations_eigs = eigs["lambda"]
        time[1] = timer() - t

        iu = np.triu_indices(channels_correlations.shape[0], 1)
        channels_correlations = channels_correlations[iu]

        results = FeaturesCalcHelper.fill_results(["correlation_channels_freq", "lambda"],
                                                  [channels_correlations, channels_correlations_eigs],
                                                  "correlation_channels_freq", [time])
        return results

    @staticmethod
    def h_jorth(x, settings):
        """
        This function calculates h-jorth parameters, activity, mobility, and complexity.
        See ???? for information
        :param x: the input signal. Its size is (number of channels, samples).
        :param settings: settings (dummy for this function)
        :return: h-jorth parameters in a dictionary, including time, values, and function name.
        """
        time = [0, 0, 0]

        t = timer()
        activity = np.nanvar(x, axis=1)
        time[0] = t - timer()

        def calc_mobility(x_in): return np.divide(np.nanstd(np.diff(x_in, axis=1)), np.nanstd(x_in, axis=1))

        t = timer()
        mobility = calc_mobility(x)
        time[1] = t - timer()

        t = timer()
        complexity = np.divide(
            calc_mobility(np.diff(x, axis=1)),
            calc_mobility(x))
        time[2] = t - timer()

        results = FeaturesCalcHelper.fill_results(["activity", "mobility", "complexity"],
                                                  [activity, mobility, complexity], "h_jorth", [t])
        return results

    @staticmethod
    def hjorth_fractal_dimension(x, settings):
        """
        Compute Hjorth Fractal Dimension of a time series X, kmax
        is an HFD parameter. Kmax is basically the scale size or time offset.
        So you are going to create Kmax versions of your time series.
        The K-th series is every K-th time of the original series.
        This code was taken from pyEEG, 0.02 r1: http://pyeeg.sourceforge.net/

        :param x:  the input signal. Its size is (number of channels, samples).
        :param settings: dummy for kartz.
        :return: petrosian fractal dimension for each channel.
        """

        t = timer()
        dimensions_channels = np.apply_along_axis(FeaturesCalcHelper.calc_hjorth_fractal_dimension, 1,
                                         x, settings["hjorth_fd_k_max"])
        t = timer() - t
        results = FeaturesCalcHelper.fill_results(["h-jorth-FD"],
                                                  dimensions_channels, "hjorth_fractal_dimension", [t])
        return results

    @staticmethod
    def petrosian_fractal_dimension(x, settings):
        """
        Petrosian fractal dimension, see https://www.seas.upenn.edu/~littlab/Site/Publications_files/Esteller_2001.pdf

        :param x:  the input signal. Its size is (number of channels, samples).
        :param settings: dummy for kartz.
        :return: petrosian fractal dimension for each channel.
        """
        t = timer()
        dimensions_channels = np.apply_along_axis(FeaturesCalcHelper.calc_petrosian_fractal_dimension, 1, x)
        t = timer() - t
        results = FeaturesCalcHelper.fill_results(["petrosian-FD"],
                                                  dimensions_channels, "petrosian_fractal_dimension", [t])
        return results

    @staticmethod
    def katz_fractal_dimension(x, settings):
        """
        Kartz fractal dimension, see https://www.seas.upenn.edu/~littlab/Site/Publications_files/Esteller_2001.pdf

        :param x: the input signal. Its size is (number of channels, samples).
        :param settings: dummy for kartz
        :return: kartz exponent for each channel
        """
        def get_kartz(x): return np.log(np.abs(x - x[0]).max())/np.log(len(x))

        t = timer()
        dimensions_channels = np.apply_along_axis(get_kartz, 1, x)
        t = timer() - t

        results = FeaturesCalcHelper.fill_results(["kartz-FD"],
                                                  dimensions_channels, "katz_fractal_dimension", [t])
        return results

    @staticmethod
    def hurst_fractal_dimension(x, settigns):
        """
        Hurst fractal dimension, see https://en.wikipedia.org/wiki/Hurst_exponent

        :param x:  the input signal. Its size is (number of channels, samples).
        :param settings: dummy for hurst.
        :return: petrosian fractal dimension for each channel.
        """
        t = timer()
        dimensions_channels = np.apply_along_axis(FeaturesCalcHelper.calc_hurst, 1, x)
        t = timer() - t
        results = FeaturesCalcHelper.fill_results(["hurst-FD"],
                                                  dimensions_channels, "hurst_fractal_dimension", [t])
        return results

    @staticmethod
    def detrended_fluctuation(x, settings):
        """

        :param x:
        :param settings:
        :return:
        """
        n_samples = x.shape[1]
        nvals = FeaturesCalcHelper.calc_logarithmic_n(4, 0.1 * n_samples, 1.2)
        overlap = settings["dfa_overlap"]
        order = settings["dfa_order"]

        t = timer()
        dfa_channels = 0
        # np.apply_along_axis(FeaturesCalcHelper.calc_dfa, 1, x, nvals=nvals, overlap=overlap, order=order)
        t = timer() - t
        results = FeaturesCalcHelper.fill_results(["detrended_fluctuation"],
                                                  dfa_channels, "detrended_fluctuation", [t])
        return results

    @staticmethod
    def autocorrelation(x, settings):
        """

        :param x:
        :param settings:
        :return:
        """
        t = timer()
        autocorrs = np.apply_along_axis(acf, 1, x, unbiased=False, nlags=settings["autocorr_n_lags"])
        autocorrs = autocorrs[:, 1:]
        t = timer() - t
        results = FeaturesCalcHelper.fill_results(["autocorrelation"],
                                                  autocorrs, "autocorrelation", [t])
        return results

    @staticmethod
    def autoregression(x, settings):
        """

        :param x:
        :param settings:
        :return:
        """
        autoreg_lag = settings["autoreg_lag"]
        n_channels = x.shape[0]
        t = timer()
        channels_regg = np.zeros((n_channels, autoreg_lag + 1))
        for i in range(0, n_channels):
            fitted_model = AR(x[i, :]).fit(autoreg_lag) # This is not the same as Matlab's for some reasons!
            # kk = ARMAResults(fitted_model)
            # autore_vals, dummy1, dummy2 = arburg(x[i, :], autoreg_lag) # This looks like Matlab's but slow
            channels_regg[i, 0: len(fitted_model.params)] = np.real(fitted_model.params)

        t = timer() - t
        results = FeaturesCalcHelper.fill_results(["autoregression"],
                                                  channels_regg, "autoregression", [t])
        return results