import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import pyabf
from feature_extractor import SpikeFeatureExtractor, SpikeTrainFeatureExtractor
import subthresh_features as sbth
import qc_features as qc


save_directory = "./uploads"

def list_files(directory):
    file_list = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            file_list.append(file_path)
    return file_list

# Specify the directory path
directory_path = save_directory

# Call the function to list all files
files = list_files(directory_path)
st.dataframe(files)

# Create a file upload widget
uploaded_file = st.file_uploader("Upload a file", type=['abf'], accept_multiple_files=False)

# Check if a file is uploaded
if uploaded_file is not None:
   
    # Create the directory if it doesn't exist
    os.makedirs(save_directory, exist_ok=True)

    # Save the uploaded file to the specified directory
    file_path = os.path.join(save_directory, uploaded_file.name)
    with open(file_path, "wb") as ff:
        ff.write(uploaded_file.getvalue())

    # Load the ABF file using pyabf
    f = pyabf.ABF(file_path)

    st.write(f)

    if f.nOperationMode == 5 and f.sweepCount > 3:   # multi-sweeps
        # folder = out_folder + '\\' + f.abfID
        # if not os.path.exists(folder):
        #     os.mkdir(folder)

        result = dict()
        result['file'] = f.abfID
        
        f.setSweep(0)
        first_epoc = f.sweepEpochs
        f.setSweep(1)
        second_epoc = f.sweepEpochs
        dif = np.asarray(second_epoc.levels) - np.asarray(first_epoc.levels)

        step = dif != 0
        start = np.asarray(first_epoc.p1s)[step][0]
        end = np.asarray(first_epoc.p2s)[step][0]

        fig, ax = plt.subplots()

        ax.set_xlabel(f.sweepLabelX)
        ax.set_ylabel(f.sweepLabelY)

        if f.sweepUnitsC == 'pA':   # current clamp

            sampling_rate = f.sampleRate
            temp_result_list = []

            rmp = []
            tau = []
            sag = []

            t_set = []
            i_set = []
            v_set = []

            sfe = SpikeFeatureExtractor(filter=2)
            spte = SpikeTrainFeatureExtractor(start=start/sampling_rate, end=end/sampling_rate)

            for index in f.sweepList:
                f.setSweep(index)
                t = f.sweepX
                v = f.sweepY
                i = f.sweepC
                
                if f.sweepUnitsY == f.sweepUnitsC:
                    v = v/20
                
                ax.plot(t, v)
                
                current = np.asarray(f.sweepEpochs.levels)[step][0]

                rmp.append(np.median(v[np.where(i == 0)]))
                if current < 0:
                    baseline_interval = min(start/(sampling_rate*2), 0.1)
                    tau.append(sbth.time_constant(t=t, v=v, i=i, start=start/sampling_rate, end=(end-2)/sampling_rate, baseline_interval=baseline_interval))
                    sag.append(sbth.sag(t=t, v=v, i=i, start=start/sampling_rate, end=end/sampling_rate, baseline_interval=baseline_interval))
                    t_set.append(t)
                    i_set.append(i)
                    v_set.append(v)

                if current == 0:
                    t_set.append(t)
                    i_set.append(i)
                    v_set.append(v)

                ft = sfe.process(t, v, i)
                # ft.to_csv(f'{folder}/{index}.csv', index=False)
                sptft= spte.process(t=t, v=v, i=i, spikes_df=ft)
                sptft['injected current (pA)'] = current
                temp_result_list.append((ft, sptft))

            rin = sbth.input_resistance(t_set=t_set, i_set=i_set, v_set=v_set, start=start/sampling_rate, end=end/sampling_rate)
            result['Rin (MOm)'] = rin
            result['RMP (mV)'] = np.mean(rmp)
            result['tau (sec)'] = np.mean(tau)
            result['sag ratio'] = np.mean(sag)

            for i_result in temp_result_list:
                if i_result[1]['avg_rate'] > 0:
                    new_df = i_result[0].mean(numeric_only=True).to_dict()
                    result.update(new_df)
                    break
            fire_pattern_df = None
            for i_result in temp_result_list:
                if 'adapt' in i_result[1] and i_result[1]['adapt'] > 0:
                    temp_dict = {i: [i_result[1][i]] for i in i_result[1]} 
                    result.update(temp_dict)
                    break

            firing_rate_list = dict()
            firing_rate_list['sampling rate'] = [sampling_rate]
            for i_result in temp_result_list:
                current = i_result[1]['injected current (pA)']
                rate = i_result[1]['avg_rate']
                firing_rate_list[f'{current} pA'] = [rate]
            result.update(firing_rate_list)

        if f.sweepUnitsC == 'mV':
            # QC
            rin_v = []
            r_access = []

            ina = dict()

            for index in f.sweepList:
                f.setSweep(index)
                v, t, i = f.sweepC[:start-1], f.sweepX[:start-1], f.sweepY[:start-1]
                holding_current = np.median(i[np.where(v == f.sweepEpochs.levels[0])])
                rin_v.append(qc.measure_input_resistance(v, i, t))
                r_access.append(qc.measure_initial_access_resistance(v, i, t))

                v_step = np.asarray(f.sweepEpochs.levels)[step][0]
                i_peak = np.min(f.sweepY[start:end]) - holding_current

                
                ina[f'{v_step} mV'] = i_peak

                ax.plot(f.sweepX, f.sweepY)
            
            result['Rin (MOm)'] = np.mean(rin_v)
            result['Access resistance (Mom)'] = np.mean(r_access)
            result.update(ina)

    st.pyplot(fig)
    st.dataframe(result)

os.remove(file_path)