import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rc
import streamlit as st
import pyabf
from feature_extractor import SpikeFeatureExtractor, SpikeTrainFeatureExtractor
import subthresh_features as sbth
import qc_features as qc


darkmode = 1
facecolor = ['w', '#555555']
line_text_color = ['k', 'w']

rc('lines', linewidth=0.5)
rc('font', family='Arial', weight='bold', size=9)
rc('axes', linewidth=1, labelsize=5, labelweight='bold', titlesize=10,
   titleweight='bold', edgecolor=line_text_color[darkmode], labelcolor=line_text_color[darkmode],
   facecolor=facecolor[darkmode])
rc('axes.spines', right=False, top=False)
rc('legend', framealpha=0.5, fontsize=5, frameon=False)
rc('xtick', top=False, labeltop=False, labelsize=5, color=line_text_color[darkmode])
rc('ytick', right=False, labelright=False, labelsize=5, color=line_text_color[darkmode])
rc('text', color=line_text_color[darkmode])
rc('figure', dpi=300, figsize=(6, 1.5), facecolor=facecolor[darkmode])
rc('figure.subplot', left=0.1, right=0.9, bottom=0.3, top=0.9, wspace=0.4, hspace=0.2)
rc('errorbar', capsize=0)
rc('savefig', transparent=True, dpi=300)


save_directory = "./uploads"

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
    st.table(result)

    os.remove(file_path)