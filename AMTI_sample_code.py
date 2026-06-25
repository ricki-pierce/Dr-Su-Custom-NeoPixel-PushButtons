# Example of how to use the AMTI USB Device SDK from Python + ctypes

# 29OCT2020 - JDT
# Python 3.8.3 (64-bit)
# Tested on Windows 10.0.18363, with AMTIUSBDevice.dll v1.3.08 (64-bit)

from ctypes import cdll, c_float, sizeof
import time

try:
    amti = cdll.AMTIUSBDevice
    countdown = 20
    amti.fmDLLInit()
    while (amti.fmDLLIsDeviceInitComplete() == 0):
        time.sleep(0.250)
        countdown -= 1
        if (countdown < 0):
            print("Connection timed out. Exit.")
            raise AssertionError()
    res = amti.fmDLLSetupCheck(); assert res == 1
    n_devices = amti.fmDLLGetDeviceCount(); assert n_devices > 0
    if n_devices > 1:
        device = int(input('which device (%d-%d): ' % (0, n_devices - 1)))
    else:
        device = 0
    amti.fmDLLSelectDeviceIndex(device)
    acq_rates = [2000, 1800, 1500, 1200, 1000, 900, 800, 600, 500, 450,
                 400, 360, 300, 250, 240, 225, 200, 180, 150, 125,
                 120, 100, 90, 80, 75, 60, 50, 45, 40, 30,
                 25, 20, 15, 10]
    while True:
        sampling_rate = int(input('sampling rate : '))
        if sampling_rate in acq_rates:
            break
        else:
            print('not available (see manual)')
    amti.fmBroadcastAcquisitionRate(sampling_rate)
    amti.fmBroadcastRunMode(1)  # metric, fully conditioned
    amti.fmDLLSetDataFormat(1)  # 8 values (incl. counter)
    dur = float(input('duration of data acquisition (sec): '))
    n_samples = int(round(dur*sampling_rate))

    sample_size = 8
    block_size = 16
    buf_size = sample_size*block_size
    buf = (c_float*buf_size)()
    data = []

    input('--- hit return to start recording ---')
    amti.fmBroadcastStart()
    samples_read = 0
    while samples_read < n_samples:
        res = amti.fmDLLGetTheFloatDataLBVStyle(buf, sizeof(buf))
        if res != 0:
            for a in range(0, buf_size, sample_size):
                data.append(buf[a:(a + sample_size)])
            samples_read += block_size
        else:
            time.sleep(0.008)
            
    # Since the DLL reads back in chunks of 16 data sets, we might have a
    # little more data than requested
    if len(data) > n_samples:
        data = data[0:n_samples]
      
    fn = input('output file name: ')
    fp = open(fn, 'wt')
    for sample in data:
        for i, x in zip(range(len(sample)), sample):
            fp.write(('%g' % x) + ('\t' if i < len(sample) - 1 else '\n'))
    fp.close()

finally:
    amti.fmBroadcastStop()
    amti.fmDLLShutDown()
