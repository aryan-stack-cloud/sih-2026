
=============================================================
Distributed Sensing of Radio Spectrum Occupancy amid COVID-19
=============================================================

This is data described in the technical note of the same name.
Details about how the data were collected are available in that report, which
is available at (insert DOI link to the report).

subdirectory: 'histograms'
================================

This folder contains histograms computed on the power samples, split into files for each test site.
The input data for the computed histograms were from 'time series - denoised'.

File format:
* File name "<site #>.csv.gz", where "<site #>" is a 2-digit residence site number or "hospital"
* Comma-separated values in UTF-8 encoding
* Compressed with gzip

Table structure:
* First row contains column names
    Column labels 1,2: Labels for indexing in time and frequency
    Column labels 3,4,...: The power level at the lower edge of the bin (decimal, in dBm on 0.25 dB steps)

* Remaining rows contain data the tabular data:
    Column 1: Frequency (decimal, in MHz)
    Column 2: Local time (string, formatted as "2020-06-17 13:56:48.586358")
    Columns 3,4,...: Number of observations at specified power level (integer)
  Sorting was applied first in frequency, then in time.

subdirectory: 'network profiling'
================================
This folder contains network data traffic profiling information that were
output by a wireless protocol tester.

File format:
* File name "<site description>/<frequency> MHz <traffic type description>.csv.gz"
* Comma-separated values in UTF-8 encoding
* Compressed with gzip

Table structure for "cellular" traffic type:
* First row contains column names
* Remaining rows contain the tabular data as follows:
    Column 1: Time elapsed since arbitrary start time reference (decimal, in sec)
    Column 2: Number of users (integer)
    Column 3: Number of occupied resource blocks (integer)
    Column 4: Average modulation and coding value (integer)

Table structure for "wlan" traffic type:
* First row contains column names
* Remaining rows contain the tabular data on each observed packet as follows:
    Column 1: Time elapsed since arbitrary start time reference (string, format "0 days 00:00:00.056990")
    Column 2: Packet type (string)
    Column 3: Modulation and coding scheme (integer)
    Column 4: Power level (decimal, in dBm)
    Column 5: Number of bytes sent
    Column 6: Error-vector magnitude
    Column 7: Destination user unique ID # (integer) or "broadcast" (string)
    Column 8: Source user, unique ID # (integer)
    Column 9: Packet transmission duration (decimal, in sec)
    Column 10: Data rate (decimal, in kbps)


subdirectory: 'occupancy durations'
================================
This folder contains occupancy rate data computed from power samples, split into files for each test site.
The input data for the computed histograms were from 'time series - denoised'.

File format:
* File name "<site #>.csv.gz"
* Comma-separated values in UTF-8 encoding
* Compressed with gzip

Table structure:
* First row contains column names
    Column labels 1,2: Labels for indexing in time and frequency
    Column labels 3,4,...: The threshold power levels used to compute the occupancy (in dBm)

* Remaining rows contain data the tabular data:
    Column 1: Frequency (decimal, in MHz)
    Column 2: Local time (string, formatted as )"2020-06-17 13:56:48.586358")
    Columns 3-8: Fraction of samples that exceeded the power threshold, or empty if none were observed (decimal, between 0 and 1)
  Sorting was applied first in frequency, then in time.

subdirectory: 'time series'
================================
This folder contains the raw data collected by each sensor, which consists of a time series of power readings at each dwell window.
The data in this directory were corrected with an offset calibration (in dB) to give power at the input (in mW), but not corrected to remove noise.

The data files are split into directories corresponding to the test site at which the sensor collected data.
The data files in each directory have been converted from the binary output produced by the sensor and into to csv. Each data
file represents up to 1 day of data samples. New files were generated either when data collection was restarted, or when the previous file
filled after 1 day.

Container file format:
* File name "<site #>.tar.gz"
* Tar file format containing data files; compressed with gzip

File format inside .tar.gz files:
* File name "<site #> <file creation timestamp>.csv"
* Comma-separated values in UTF-8 encoding

Table structure:
* First row contains column names
    Column labels 1,2,3: Labels for indexing {time, frequency, sweep number}.
    Column labels 4...: Time elapsed since the time given by the row index, at the start of the time bin (decimal, in seconds)

* Remaining rows contain data the tabular data:
    Column 1: Local time (string, formatted as "2020-06-17 13:56:48.586358")
    Column 2: Frequency (decimal, in MHz)
    Column 3: Sweep number (integer, counting from 0)
    Columns 4...: Average power recorded during the time bin specified by the column label (decimal, in mW)
  Sorting is by time.


subdirectory: 'time series - denoised'
================================
This folder contains the raw data collected by each sensor, which consists of a time series of power readings at each dwell window.
The data in this directory were corrected with  1) an offset calibration (in dB) to give power at the input (in mW), and 2) subtraction
of calibrated noise level of the sensor.

The data files are split into directories corresponding to the test site at which the sensor collected data.
The data files in each directory have been converted from the binary output produced by the sensor and into to csv. Each data
file represents up to 1 day of data samples. New files were generated either when data collection was restarted, or when the previous file
filled after 1 day.


Container file format:
* File name "<site #>.tar.gz"
* Tar file format containing data files; compressed with gzip

File format inside .tar.gz files:
* File name "<site #> <file creation timestamp>.csv"
* Comma-separated values in UTF-8 encoding

Table structure:
* First row contains column names
    Column labels 1,2,3: Labels for indexing {time, frequency, sweep number}.
    Column labels 4...: Time elapsed since the time given by the row index, at the start of the time bin (decimal, in seconds)

* Remaining rows contain data the tabular data:
    Column 1: Local time (string, formatted as "2020-06-17 13:56:48.586358")
    Column 2: Frequency (decimal, in MHz)
    Column 3: Sweep number (integer, counting from 0)
    Columns 4...: Average power recorded during the time bin specified by the column label (decimal, in mW)
  Sorting is by time.

file: 'source-code.zip'
================================
This file contains the source code used to produce and analyze the data presented here.
More information is contained in the README.md and pdf documentation files contained within.
