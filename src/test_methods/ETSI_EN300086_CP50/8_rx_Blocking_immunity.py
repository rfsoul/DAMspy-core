# test_methods/ETSI_EN300086_CP50/7_rx_Adjacent_Channel_Selectivity.py
# This code measures adjacent channel selectivity at the sinad levels and powers in the YAML file 7_rx_Adjacent_Channel_Selectivity.yaml
# THe yaml specifies
# wanted_frequency
# Channel_spacing
# wanted_signal_power
# unwanted_signal_power

#
#
#

# # test_methods/ETSI_EN300086_CP50/6_rx_Maximum_Usable_Sensitivity.py
# # This code measures sinad across receive levels and frequencies set in the yaml 6_rx_Maximum_Usable_Sensitivity.yaml
# This code measures sinad levels and powers in the YAML file 7_rx_Adjacent_Channel_Selectivity.yaml



import os
import time
import pandas as pd
import matplotlib.pyplot as plt
from SETI_logging.text_formatter import print_green, print_red, print_blue, print_yellow
from SETI_logging.log_generator import Logging
#logging = Logging(loc_cfg["log_path"])

import os


def get_youngest_directory_absolute_path(parent_folder_path):
    """
    Returns the absolute path to the youngest (most recently modified) directory
    within the specified parent folder.

    Args:
        parent_folder_path (str): The path to the parent folder to search within.

    Returns:
        str or None: The absolute path to the youngest directory, or None if no
                     directories are found or the parent_folder_path is invalid.
    """
    if not os.path.isdir(parent_folder_path):
        return None

    youngest_dir = None
    youngest_timestamp = -1

    for item_name in os.listdir(parent_folder_path):
        item_path = os.path.join(parent_folder_path, item_name)
        if os.path.isdir(item_path):
            try:
                modified_time = os.path.getmtime(item_path)
                if modified_time > youngest_timestamp:
                    youngest_timestamp = modified_time
                    youngest_dir = item_path
            except OSError:
                # Handle cases where getmtime might fail (e.g., permissions)
                continue

    if youngest_dir:
        return os.path.abspath(youngest_dir)
    else:
        return None

def run(params, radio_ctrl, equip_mgr, test_results):
    """
    RX Maximum Usable Sensitivity (MUS) test.
    """

    out_dir = test_results.top_level_dir_path
    print('test dir path')
    print(out_dir)

    ETS_log_path = 'C:\GME\Tools\Radios\GIT\SETI_Al\ets_logs'
    Current_test_dir_path=get_youngest_directory_absolute_path(ETS_log_path)
    out_dir = Current_test_dir_path
    print(Current_test_dir_path)



    #test_results.test_param_log(params, "6_rx_Maximum_Usable_Sensitivity")
    #print(f"[MUS] Logging output in {out_dir!r}")

    # 1) Pull test-specific parameters from `params`
    temperature     = params.get("temperature")
    wanted_freqs    = params.get("frequency", [])
    sinad_min       = float(params.get("sinad_min", 9))
    ccitt_flag      = bool(params.get("ccitt", False))
    Channel_spacing = params.get("Channel_spacing", [])
    unwanted_freq_offsets = [- Channel_spacing, Channel_spacing]
    bandwidths = params.get("Bandwidth", [])
    this_script_abr = params.get("this_test_abr")
    print('this_script_abr ='+this_script_abr)
    log_script_prefix = params.get("log_script_prefix")


    # print_blue('bandwidths')
    # for b in bandwidths:
    #     print(b)
    ## force write sn
    # new_serialnumber ="3D2.2.5"
    # radio_ctrl.set_serial_no(new_serialnumber)
    # time.sleep(.1)
    # radio_sn = radio_ctrl.get_serial_no()
    # print('final sn')
    # print(radio_sn)
    # print("_______done___________")
    # import kdfhgkahfdsk


    radio_sn = radio_ctrl.get_serial_no()
    print("serial number is = "+str(radio_sn))
    print("length of serial number is " +str(len(radio_sn)))

    if radio_sn== '':
        print('lets burn in a new Sn!')

    if "3D2" or "3d2" or "#" in radio_sn:
        print("3d2 present in SN, proceeding without change")
    elif radio_sn=='250160003':
        print('known reference radio,SN not altered')
    else:
        print("SN is empty or numeric-only (or missing 3d2). You can append a suffix, or press Enter to skip:")
        extra = input("  Enter new SN prefix (blank to skip): ").strip()


        if extra:
            # build new_sn = extra + "_" + old, but omit "_" if old is blank
            if radio_sn:
                new_sn = f"{extra}_{radio_sn}"
            else:
                new_sn = extra

            print(f"Writing new SN = {new_sn!r} into EEPROM …")
            radio_ctrl.set_serial_no(new_sn)

            # verify
            verify = radio_ctrl.get_serial_no().strip()
            if verify == new_sn:
                print_green("[OK] Successfully burned-in new SN")
            else:
                print_red(f"[ERROR] Failed to set SN; radio reports {verify!r}")

        else:
            print("Sn update canceled, proceeding without change")

    radio_sn = radio_ctrl.get_serial_no()
    print('final sn')
    print(radio_sn)

    # 3) Grab drivers from EquipmentLoader
    try:
        sinad_drv = equip_mgr.sinad_meter
    except AttributeError:
        print_red("❗ Error: 'sinad_meter' driver not found in EquipmentLoader")
        return False

    try:
        sg = equip_mgr.TGR2051
    except AttributeError:
        print_red("❗ Error: 'TGR2051' driver not found in EquipmentLoader")
        return False

    try:
        smc = equip_mgr.SMC100A   # or whatever key your SMC100 driver uses
    except AttributeError:
        print_red("❗ Error: 'SMC100A' driver not found in EquipmentLoader")
        return False

    # 4) Read combined cal_factor from TGR driver

    if hasattr(sg, "cal_factor"):
        try:
            cal_factor = float(sg.cal_factor)
            print_green(f"[INFO] Using TGR2051.cal_factor = {cal_factor:.1f} dB")
        except Exception:
            pass

    # 5) Build list of power levels from YAML
    cal_factor = float(sg.cal_factor)
    wanted_test_radio_levels = params.get("wanted_signal_power", {}).get("levels", [])
    unwanted_relative_radio_levels= params.get("unwanted_signal_power", {}).get("relative_level", [])

    # 6) Prepare to collect results
    results = []


    # 7) Main loop over frequencies
    for wanted_test_freq_MHz in wanted_freqs:
        for unwanted_freq_offset in unwanted_freq_offsets:
            for bandwidth in bandwidths:
                print_yellow("\n" + "-"*80)
                print_green(f"[{this_script_abr} Sig] Starting {wanted_test_freq_MHz:.3f} MHz test loop")
                print_green(f"[{this_script_abr} Sig] Starting {unwanted_freq_offset} unwanted_freq_offset test loop")
                print_green(f"[{this_script_abr} Sig] Starting {bandwidth} bandwidth test loop")



                # 7.a) Set radio receive frequency
                wanted_freq_Hz = wanted_test_freq_MHz * 1e6
                print(f"[{this_script_abr} Radio] Setting radio RX frequency to {wanted_test_freq_MHz:.3f} MHz")
                radio_ctrl.set_frequency(wanted_freq_Hz)
                time.sleep(params.get('freq_delay', 0.1))
                actual_rx_frequency = radio_ctrl.get_frequency()
                print(f"[{this_script_abr} Radio] Radio now reports: {actual_rx_frequency} Hz")

                # 7.b) Set wanted sig-gen frequency  TGR
                print(f"[{this_script_abr} Wanted Sig Freq] Setting SG frequency to {wanted_test_freq_MHz:.3f} MHz")
                sg.set_frequency(wanted_test_freq_MHz)
                time.sleep(0.2)
                actual_wanted_sig_gen_freq_Hz = float(sg.get_frequency())
                actual_wanted_sig_gen_freq_MHz = actual_wanted_sig_gen_freq_Hz  / 1e6
                print(f"[{this_script_abr} Wanted Sig Freq] SG reports: {actual_wanted_sig_gen_freq_MHz:.3f} MHz")

                # 7.c) Set unwanted sig-gen frequency  SMC100A
                unwanted_test_freq_MHz = wanted_test_freq_MHz+unwanted_freq_offset/1000
                print(f"[{this_script_abr} UnWanted Sig Freq] Setting SMC frequency to {unwanted_test_freq_MHz:.3f} MHz")
                smc.set_frequency(unwanted_test_freq_MHz*1e6)
                time.sleep(0.2)
                actual_unwanted_sig_gen_freq_Hz = float(smc.get_frequency())
                actual_unwanted_sig_gen_freq_MHz = actual_unwanted_sig_gen_freq_Hz / 1e6
                print(f"[{this_script_abr} UnWanted Sig Freq] SMC reports: {actual_unwanted_sig_gen_freq_MHz:.3f} MHz")

                # 7.c2) Set Bandwidth
                if bandwidth == 'WB':
                    print(f"[{this_script_abr} Bandwidth] Setting Bandwidth to "+ bandwidth)
                    radio_ctrl.set_bandwidth(True)
                elif bandwidth == 'NB':
                    print(f"[{this_script_abr} Bandwidth] Setting Bandwidth to " + bandwidth)
                    radio_ctrl.set_bandwidth(False)
                else:
                    radio_ctrl.set_bandwidth(False)
                    print(f"[{this_script_abr} Bandwidth] SBandwidth not recognised in YAML")
                    print(f"[{this_script_abr} Bandwidth] Setting Bandwidth to Narrowband")

                # 7.d) Sweep power levels
                print('['+str(this_script_abr)+' Sweep Power levels]  starting power level sweep')

                for wanted_test_radio_level in wanted_test_radio_levels:
                    previous_sinad_meas = "untested"
                    for unwanted_relative_radio_level in unwanted_relative_radio_levels:
                        if previous_sinad_meas != "low":
                            print_yellow("  " + "-"*60)

                            wanted_sig_gen_amplitude = wanted_test_radio_level - cal_factor  # both radio level and cal factor are negative   radio level should be lower

                            # 7.e) Sweep wanted power levels
                            print('['+this_script_abr+' Wanted Sig Lev] setting TGR2051 level to ' + str(wanted_sig_gen_amplitude) + 'dBm')
                            print('['+this_script_abr+' Wanted Sig Lev] cal_factor = '+str(cal_factor)+'dBm')
                            print('['+this_script_abr+' Wanted Sig Lev] Corresponds to Rx level @ radio =' + str(wanted_test_radio_level) + 'dBm')

                            sg.set_amplitude(wanted_sig_gen_amplitude)
                            time.sleep(0.2)

                            actual_wanted_sig_gen_level = sg.get_amplitude()

                            if actual_wanted_sig_gen_level == wanted_sig_gen_amplitude :
                                print_green('['+this_script_abr+' Wanted Sig Lev] Amplitude correctly set')
                            else:
                                print_red('['+this_script_abr+'Wanted Sig Lev] Amplitude not correctly set')
                                print(wanted_sig_gen_amplitude)
                                print(actual_sig_gen_level)

                            sg.enable_output()
                            time.sleep(1)

                            # 7.f) Sweep unwanted power levels
                            unwanted_sig_gen_amplitude = round(wanted_sig_gen_amplitude + unwanted_relative_radio_level,1)
                            unwanted_test_radio_level = round(unwanted_sig_gen_amplitude+cal_factor,1)
                            print('['+this_script_abr+' Unwanted Sig Lev] setting SMC100A level to ' + str(unwanted_sig_gen_amplitude) + 'dBm')
                            print('['+this_script_abr+'Unwanted Sig Lev] Corresponds to Unwanted Rx level @ radio =' + str(unwanted_test_radio_level) + 'dBm')
                            print('['+this_script_abr+'Unwanted Radio Level is '+str(unwanted_relative_radio_level )+ "dB above wanted level")

                            smc.set_amplitude(unwanted_sig_gen_amplitude)
                            time.sleep(0.2)

                            actual_unwanted_sig_gen_amplitude = smc.get_amplitude()

                            if actual_unwanted_sig_gen_amplitude == unwanted_sig_gen_amplitude:
                                print_green('['+this_script_abr+' Amplitude correctly set')
                            else:
                                print_red('['+this_script_abr+' Amplitude no correctly set')
                                print(unwanted_sig_gen_level)
                                print(actual_unwanted_sig_gen_level)

                            smc.enable_output()


                            # 7.d) # measure SINAD
                            time.sleep(.5)  # give it a moment to settle

                            print("")
                            print_yellow("_ _ _ _ _ _ _ _ measuring sinad _ _ _ _ _ _ _ _ _ _ ")
                            measure_sinad = sinad_drv.measure_sinad
                            cc = ccitt_flag

                            measurements = 20
                            _sum = 0.0
                            min_sinad = float('inf')
                            max_sinad = float('-inf')


                            for _ in range(measurements):
                                v = measure_sinad(ccitt=cc)
                                _sum += v
                                if v < min_sinad: min_sinad = v
                                if v > max_sinad: max_sinad = v
                                time.sleep(0.05)

                            average_sinad = round(_sum / measurements,1)

                            print("")
                            print_yellow(f"SINAD → min_sinad={min_sinad:.1f} dB, max_sinad={max_sinad:.1f} dB, avg={average_sinad:.1f} dB")
                            print("")

                            print_blue(
                                f"[{this_script_abr} Sin] actual_radio_rx_frequency = {actual_rx_frequency/1e6:3f} MHz {bandwidth}"
                            )
                            print_blue(
                                f"[{this_script_abr} Sin] actual_wanted_sg_freq_MHz = {actual_wanted_sig_gen_freq_MHz:.3f} MHz, "
                                f"wanted_radio_level = {wanted_test_radio_level:.1f} dBm, "
                            )
                            print_blue(
                                f"[{this_script_abr} Sin] actual_unwanted_smc_freq_MHz = {actual_unwanted_sig_gen_freq_MHz:.3f} MHz, "
                                f"unwanted_radio_level = {unwanted_test_radio_level:.1f} dBm, "
                            )
                            print_blue(
                                f"[{this_script_abr} Sin] unwanted_relative_radio_level = {unwanted_relative_radio_level:.1f} dBm, Sinad = {average_sinad:.1f}dB"
                            )

                            time.sleep(1)
                            sg.disable_output()
                            smc.disable_output()

                            # collect the result
                            results.append({
                                'temperature': temperature,
                                'CCIT' : ccitt_flag,
                                'serial_no':  radio_sn,
                                'wanted_freq_MHz': wanted_test_freq_MHz,
                                'actual_radio_rx_frequency_MHz' : str(actual_rx_frequency/1e6),
                                'bandwidth': bandwidth,
                                'wanted_rx_level_dBm': wanted_test_radio_level,
                                'unwanted_freq_MHz': unwanted_test_freq_MHz,
                                'offset' : unwanted_freq_offset,
                                'unwanted_rx_level_dBm': unwanted_test_radio_level,
                                'unwanted_relative_radio_level': unwanted_relative_radio_level,
                                'average_sinad_dB': average_sinad,
                                'min_sinad' : min_sinad,
                                'max_sinad' : max_sinad
                            })

                            # quick exit if we already passed the min SINAD at this level

                            if average_sinad <= sinad_min:
                                print_green(str(unwanted_freq_offset))
                                print_green(f"[{this_script_abr} Sin] SINAD <= {sinad_min:.1f} dB, moving to next freq")
                                #break
                                previous_sinad_meas = "low"

                        else:
                            print('skipping test for unwanted_relative_radio_level ' +str(unwanted_relative_radio_level) +' as previous sinad below min')


    # 8) After all measurements, save and plot results
    # 8.a) Create output directorystr(
    # out_dir = test_results.test_results_path
    # os.makedirs(out_dir, exist_ok=True)

    # 8.b) Save CSV
    print('saving results')
    csv_path = os.path.join(out_dir, log_script_prefix+'_'+'_'+str(radio_sn)+'.csv')
    #csv_path = os.path.join(out_dir, '8_rx_blocking_immunity_results_' + str(radio_sn) + '.csv')
    #csv_path = os.path.join(out_dir, '9_rx_Spurious_Response_Immunity_' + str(radio_sn) + '.csv')

    df = pd.DataFrame(results)
    df.to_csv(csv_path, index=False)
    print_green(f"[ACS] Results saved to {csv_path}")

    # # 8.c) Plot SINAD vs Frequency for each RX level
    # plt.figure()
    # for level in sorted(df['rx_level_dBm'].unique()):
    #     subset = df[df['rx_level_dBm'] == level]
    #     plt.plot(subset['freq_MHz'], subset['sinad_dB'], marker='o', label=f"{level:.1f} dBm")
    #
    # plt.xlabel('Frequency (MHz)')
    # plt.ylabel('SINAD (dB)')
    # plt.title('ACS: SINAD vs Frequency')
    # plt.legend(title='RX Level')
    # plt.grid(True)
    #
    # png_path = os.path.join(out_dir, 'ACS.png')
    # plt.savefig(png_path, dpi=200)
    # plt.close()
    # print_green(f"[ACS] Plot saved to {png_path}")

    #9) Cleanup
    sg.set_frequency(600)
    return True

