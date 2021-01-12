# Mantid Repository : https://github.com/mantidproject/mantid
#
# Copyright &copy; 2018 ISIS Rutherford Appleton Laboratory UKRI,
#   NScD Oak Ridge National Laboratory, European Spallation Source,
#   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
# SPDX - License - Identifier: GPL - 3.0 +
# pylint: disable=no-init,invalid-name,too-few-public-methods
#
# These system test perform some of the fits provided by NIST for non-linear
# least square systems that can be found here:
# http://www.itl.nist.gov/div898/strd/nls/nls_main.shtml
import systemtesting
from mantid.simpleapi import *


def runFit(x, y, fn):
    ws = CreateWorkspace(x, y)

    Fit(fn, ws, Output='ws',
        Minimizer='Levenberg-Marquardt',
        CostFunction="Unweighted least squares")

    param_table = mtd['ws_Parameters']

    params = param_table.column(1)[:-1]
    errors = param_table.column(2)[:-1]

    return params, errors


class LeastSquaresNISTRat43Test(systemtesting.MantidSystemTest):
    def runTest(self):
        x = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
        y = [16.08, 33.83, 65.8, 97.2, 191.55, 326.2, 386.87, 520.53, 590.03, 651.92, 724.93, 699.56, 689.96, 637.56,
             717.41]

        function = 'name=UserFunction,Formula=b1/((1+exp(b2-b3*x))^(1/b4)),b1=700,b2=5,b3=0.75,b4=1.3'

        params, errors = runFit(x, y, function)

        expected_params = [6.9964151270E+02, 5.2771253025E+00, 7.5962938329E-01, 1.2792483859E+00]
        expected_errors = [1.6302297817E+01, 2.0828735829E+00, 1.9566123451E-01, 6.8761936385E-01]

        for err, expected in zip(errors, expected_errors):
            self.assertDelta(err / expected - 1.0, 0.0, 3e-2)

        for val, expected in zip(params, expected_params):
            self.assertDelta(val / expected - 1.0, 0.0, 3e-3)


class LeastSquaresNISTGauss3Test(systemtesting.MantidSystemTest):
    def runTest(self):
        x = [1.000000, 2.000000, 3.000000, 4.000000, 5.000000, 6.000000, 7.000000, 8.000000, 9.000000, 10.000000,
             11.00000, 12.00000, 13.00000, 14.00000, 15.00000, 16.00000, 17.00000, 18.00000, 19.00000, 20.00000,
             21.00000, 22.00000, 23.00000, 24.00000, 25.00000, 26.00000, 27.00000, 28.00000, 29.00000, 30.00000,
             31.00000, 32.00000, 33.00000, 34.00000, 35.00000, 36.00000, 37.00000, 38.00000, 39.00000, 40.00000,
             41.00000, 42.00000, 43.00000, 44.00000, 45.00000, 46.00000, 47.00000, 48.00000, 49.00000, 50.00000,
             51.00000, 52.00000, 53.00000, 54.00000, 55.00000, 56.00000, 57.00000, 58.00000, 59.00000, 60.00000,
             61.00000, 62.00000, 63.00000, 64.00000, 65.00000, 66.00000, 67.00000, 68.00000, 69.00000, 70.00000,
             71.00000, 72.00000, 73.00000, 74.00000, 75.00000, 76.00000, 77.00000, 78.00000, 79.00000, 80.00000,
             81.00000, 82.00000, 83.00000, 84.00000, 85.00000, 86.00000, 87.00000, 88.00000, 89.00000, 90.00000,
             91.00000, 92.00000, 93.00000, 94.00000, 95.00000, 96.00000, 97.00000, 98.00000, 99.00000, 100.00000,
             101.00000, 102.00000, 103.00000, 104.00000, 105.00000, 106.0000, 107.0000, 108.0000, 109.0000, 110.0000,
             111.0000, 112.0000, 113.0000, 114.0000, 115.0000, 116.0000, 117.0000, 118.0000, 119.0000, 120.0000,
             121.0000, 122.0000, 123.0000, 124.0000, 125.0000, 126.0000, 127.0000, 128.0000, 129.0000, 130.0000,
             131.0000, 132.0000, 133.0000, 134.0000, 135.0000, 136.0000, 137.0000, 138.0000, 139.0000, 140.0000,
             141.0000, 142.0000, 143.0000, 144.0000, 145.0000, 146.0000, 147.0000, 148.0000, 149.0000, 150.0000,
             151.0000, 152.0000, 153.0000, 154.0000, 155.0000, 156.0000, 157.0000, 158.0000, 159.0000, 160.0000,
             161.0000, 162.0000, 163.0000, 164.0000, 165.0000, 166.0000, 167.0000, 168.0000, 169.0000, 170.0000,
             171.0000, 172.0000, 173.0000, 174.0000, 175.0000, 176.0000, 177.0000, 178.0000, 179.0000, 180.0000,
             181.0000, 182.0000, 183.0000, 184.0000, 185.0000, 186.0000, 187.0000, 188.0000, 189.0000, 190.0000,
             191.0000, 192.0000, 193.0000, 194.0000, 195.0000, 196.0000, 197.0000, 198.0000, 199.0000, 200.0000,
             201.0000, 202.0000, 203.0000, 204.0000, 205.0000, 206.0000, 207.0000, 208.0000, 209.0000, 210.0000,
             211.0000, 212.0000, 213.0000, 214.0000, 215.0000, 216.0000, 217.0000, 218.0000, 219.0000, 220.0000,
             221.0000, 222.0000, 223.0000, 224.0000, 225.0000, 226.0000, 227.0000, 228.0000, 229.0000, 230.0000,
             231.0000, 232.0000, 233.0000, 234.0000, 235.0000, 236.0000, 237.0000, 238.0000, 239.0000, 240.0000,
             241.0000, 242.0000, 243.0000, 244.0000, 245.0000, 246.0000, 247.0000, 248.0000, 249.0000, 250.0000]
        y = [97.58776, 97.76344, 96.56705, 92.52037, 91.15097, 95.21728, 90.21355, 89.29235, 91.51479, 89.60965,
             86.56187, 85.55315, 87.13053, 85.67938, 80.04849, 82.18922, 87.24078, 80.79401, 81.28564, 81.56932,
             79.22703, 79.43259, 77.90174, 76.75438, 77.17338, 74.27296, 73.11830, 73.84732, 72.47746, 71.92128,
             66.91962, 67.93554, 69.55841, 69.06592, 66.53371, 63.87094, 69.70526, 63.59295, 63.35509, 59.99747,
             62.64843, 65.77345, 59.10141, 56.57750, 61.15313, 54.30767, 62.83535, 56.52957, 56.98427, 58.11459,
             58.69576, 58.23322, 54.90490, 57.91442, 56.96629, 51.13831, 49.27123, 52.92668, 54.47693, 51.81710,
             51.05401, 52.51731, 51.83710, 54.48196, 49.05859, 50.52315, 50.32755, 46.44419, 50.89281, 52.13203,
             49.78741, 49.01637, 54.18198, 53.17456, 53.20827, 57.43459, 51.95282, 54.20282, 57.46687, 53.60268,
             58.86728, 57.66652, 63.71034, 65.24244, 65.10878, 69.96313, 68.85475, 73.32574, 76.21241, 78.06311,
             75.37701, 87.54449, 89.50588, 95.82098, 97.48390, 100.86070, 102.48510, 105.7311, 111.3489, 111.0305,
             110.1920, 118.3581, 118.8086, 122.4249, 124.0953, 125.9337, 127.8533, 131.0361, 133.3343, 135.1278,
             131.7113, 131.9151, 132.1107, 127.6898, 133.2148, 128.2296, 133.5902, 127.2539, 128.3482, 124.8694,
             124.6031, 117.0648, 118.1966, 119.5408, 114.7946, 114.2780, 120.3484, 114.8647, 111.6514, 110.1826,
             108.4461, 109.0571, 106.5308, 109.4691, 106.8709, 107.3192, 106.9000, 109.6526, 107.1602, 108.2509,
             104.96310, 109.3601, 107.6696, 99.77286, 104.96440, 106.1376, 106.5816, 100.12860, 101.66910, 96.44254,
             97.34169, 96.97412, 90.73460, 93.37949, 82.12331, 83.01657, 78.87360, 74.86971, 72.79341, 65.14744,
             67.02127, 60.16136, 57.13996, 54.05769, 50.42265, 47.82430, 42.85748, 42.45495, 38.30808, 36.95794,
             33.94543, 34.19017, 31.66097, 23.56172, 29.61143, 23.88765, 22.49812, 24.86901, 17.29481, 18.09291,
             15.34813, 14.77997, 13.87832, 12.88891, 16.20763, 16.29024, 15.29712, 14.97839, 12.11330, 14.24168,
             12.53824, 15.19818, 11.70478, 15.83745, 10.035850, 9.307574, 12.86800, 8.571671, 11.60415, 12.42772,
             11.23627, 11.13198, 7.761117, 6.758250, 14.23375, 10.63876, 8.893581, 11.55398, 11.57221, 11.58347,
             9.724857, 11.43854, 11.22636, 10.170150, 12.50765, 6.200494, 9.018902, 10.80557, 13.09591, 3.914033,
             9.567723, 8.038338, 10.230960, 9.367358, 7.695937, 6.118552, 8.793192, 7.796682, 12.45064, 10.61601,
             6.001000, 6.765096, 8.764652, 4.586417, 8.390782, 7.209201, 10.012090, 7.327461, 6.525136, 2.840065,
             10.323710, 4.790035, 8.376431, 6.263980, 2.705892, 8.362109, 8.983507, 3.362469, 1.182678, 4.875312]

        function = ("name=UserFunction,Formula=b1*exp(-b2*x) + b3*exp( -(x-b4)^2 / b5^2 ) + b6*exp( -(x-b7)^2 / b8^2 ),"
                    "b1=94.9,b2=0.009,b3=90.1,b4=113.0,b5=20.0,b6=73.8,b7=140.0,b8=20.0")

        expected_params = [9.8940368970E+01, 1.0945879335E-02, 1.0069553078E+02, 1.1163619459E+02, 2.3300500029E+01,
                           7.3705031418E+01, 1.4776164251E+02, 1.9668221230E+01]

        expected_errors = [5.3005192833E-01, 1.2554058911E-04, 8.1256587317E-01, 3.5317859757E-01, 3.6584783023E-01,
                           1.2091239082E+00, 4.0488183351E-01, 3.7806634336E-01]

        params, errors = runFit(x, y, function)

        for err, expected in zip(errors, expected_errors):
            self.assertDelta(err / expected - 1.0, 0.0, 1e-2)

        for val, expected in zip(params, expected_params):
            self.assertDelta(val / expected - 1.0, 0.0, 2e-5)


class LeastSquaresNISTMGH09Test(systemtesting.MantidSystemTest):
    def runTest(self):
        x = [4.000000E+00, 2.000000E+00, 1.000000E+00, 5.000000E-01, 2.500000E-01, 1.670000E-01, 1.250000E-01,
             1.000000E-01, 8.330000E-02, 7.140000E-02, 6.250000E-02]

        y = [1.957000E-01, 1.947000E-01, 1.735000E-01, 1.600000E-01, 8.440000E-02, 6.270000E-02, 4.560000E-02,
             3.420000E-02, 3.230000E-02, 2.350000E-02, 2.460000E-02]

        # Second set of starting parameters.
        function = 'name=UserFunction,Formula=b1*(x^2+x*b2) / (x^2+x*b3+b4),b1=0.25,b2=0.39,b3=0.415,b4=0.39'

        params, errors = runFit(x, y, function)

        expected_params = [1.9280693458E-01,1.9128232873E-01,1.2305650693E-01,1.3606233068E-01]
        expected_errors = [1.1435312227E-02,1.9633220911E-01,8.0842031232E-02,9.0025542308E-02]

        for err, expected in zip(errors, expected_errors):
            self.assertDelta(err / expected - 1.0, 0.0, 1e-3)

        for val, expected in zip(params, expected_params):
            self.assertDelta(val / expected - 1.0, 0.0, 3e-4)