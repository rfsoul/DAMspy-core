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

    #test_results.test_param_log(params, "6_rx_Maximum_Usable_Sensitivity")
    #print(f"[MUS] Logging output in {out_dir!r}")

    # 1) Pull test-specific parameters from `params`
    temperature     = params.get("temperature")
    freqs           = params.get("frequency", [])
    sinad_min       = float(params.get("sinad_min", 9))
    ccitt_flag      = bool(params.get("ccitt", False))
    bandwidths = params.get("Bandwidth", [])
    this_script_abr = params.get("this_test_abr")
    print('this_script_abr ='+this_script_abr)
    log_script_prefix = params.get("log_script_prefix")


    radio_sn = radio_ctrl.get_serial_no()
    print("serial number is = "+str(radio_sn))
    print("length of serial number is " +str(len(radio_sn)))




    ## force write sn
    # new_serialnumber ="3D2.1.#4_250560035"
    # radio_ctrl.set_serial_no(new_serialnumber)
    # time.sleep(.1)
    # radio_sn = radio_ctrl.get_serial_no()
    # print('final sn')
    # print(radio_sn)
    # print("_______done___________")
    # import kdfhgkahfdsk

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

    # 4) Read combined cal_factor from TGR driver

    if hasattr(sg, "cal_factor"):
        try:
            cal_factor = float(sg.cal_factor)
            print_green(f"[INFO] Using TGR2051.cal_factor = {cal_factor:.1f} dB")
        except Exception:
            pass

    # 5) Build list of power levels from YAML
    cal_factor = float(sg.cal_factor)
    test_radio_levels = params.get("power", {}).get("levels", [])

    # 6) Prepare to collect results
    results = []

    # 7) Main loop over bandwidths then frequencies
    for bandwidth in bandwidths:
        for test_freq_MHz in freqs:
            # Set Bandwidth
            if bandwidth == 'WB':
                print(f"[{this_script_abr} Bandwidth] Setting Bandwidth to " + bandwidth)
                radio_ctrl.set_bandwidth(True)
            elif bandwidth == 'NB':
                print(f"[{this_script_abr} Bandwidth] Setting Bandwidth to " + bandwidth)
                radio_ctrl.set_bandwidth(False)
            else:
                radio_ctrl.set_bandwidth(False)
                print(f"[{this_script_abr} Bandwidth] Bandwidth not recognised in YAML")
                print(f"[{this_script_abr} Bandwidth] Setting Bandwidth to Narrowband")

            print_yellow("\n" + "-"*80)
            print_green(f"[MUS Sig] Starting {test_freq_MHz:.3f} MHz test loop")

            # 7.a) Set radio receive frequency
            freq_Hz = test_freq_MHz * 1e6
            print(f"[MUS Radio] Setting radio RX frequency to {test_freq_MHz:.3f} MHz")
            radio_ctrl.set_frequency(freq_Hz)
            time.sleep(params.get('freq_delay', 0.1))
            actual_rx = radio_ctrl.get_frequency()
            print(f"[MUS Radio] Radio now reports: {actual_rx} Hz")

            # 7.b) Set sig-gen frequency
            print(f"[MUS Sig Freq] Setting SG frequency to {test_freq_MHz:.3f} MHz")
            sg.set_frequency(test_freq_MHz)
            time.sleep(0.2)
            actual_sig_gen_freq_Hz = float(sg.get_frequency())
            actual_sig_gen_freq_MHz = actual_sig_gen_freq_Hz / 1e6
            print(f"[MUS Sig Freq] SG reports: {actual_sig_gen_freq_MHz:.3f} MHz")

            # 7.c) Sweep power levels
            for test_radio_level in test_radio_levels:
                print_yellow("  " + "-"*60)

                wanted_sig_gen_amplitude = test_radio_level-cal_factor   #both radio level and cal factor are negative   radio level should be lower
                amp=wanted_sig_gen_amplitude

                print("[MUS Sig Lev] setting TGR2051 level to " + str(amp) + "dBm")
                print( "[MUS Sig Lev] cal_factor = "+str(cal_factor)+"dBm")
                print('[MUS Sig Lev] Corresponds to Rx level @ radio =' + str(test_radio_level) + 'dBm')

                sg.set_amplitude(amp)
                time.sleep(0.2)

                actual_sig_gen_level = sg.get_amplitude()

                if actual_sig_gen_level == amp :
                    print_green("[MUS Sig Lev] Amplitude correctly set")
                else:
                    print_red("[MUS Sig Lev] Amplitude no correctly set")
                    print(amp)
                    print(actual_sig_gen_level)

                sg.enable_output()
                time.sleep(1) # give it a moment to settle

                # measure SINAD




                # 7.d) # measure SINAD
                time.sleep(.5)  # give it a moment to settle

                print("")
                print_yellow("_ _ _ _ _ _ _ _ measuring sinad _ _ _ _ _ _ _ _ _ _ ")
                measure_sinad = sinad_drv.measure_sinad
                cc = ccitt_flag
                print('CCITT is set')

                if cc:
                    print('CCITT is ON')
                else:
                    print('CCITT is OFF')

                measurements = 20
                _sum = 0.0
                min_sinad = float('inf')
                max_sinad = float('-inf')

                k = 1
                for _ in range(measurements):
                    v = measure_sinad(ccitt=cc)
                    _sum += v
                    if v < min_sinad: min_sinad = v
                    if v > max_sinad: max_sinad = v
                    if k == 5:
                        if min_sinad > (sinad_min + 10):
                            print_green('five sinads above min+10, exiting loop')
                            measurements = 5
                            break
                    k = k + 1
                    time.sleep(0.05)

                average_sinad = round(_sum / measurements, 1)

                print("")
                print_yellow(
                    f"SINAD → min_sinad={min_sinad:.1f} dB, max_sinad={max_sinad:.1f} dB, avg={average_sinad:.1f} dB")
                print("")

                print_blue(
                    f"[MUS Sin] actual_radio_rx_frequency = {actual_sig_gen_freq_MHz: 3f} MHz {bandwidth}"
                )
                print_blue(
                    f"radio_level = {test_radio_level:.1f} dBm, "
                )


                time.sleep(1)
                sg.disable_output()


                # collect the result
                results.append({
                    'temperature': temperature,
                    'CCIT': ccitt_flag,
                    'serial_no': radio_sn,
                    'freq_MHz': test_freq_MHz,
                    'actual_radio_rx_frequency_MHz': str(actual_rx / 1e6),
                    'bandwidth': bandwidth,
                    'rx_level_dBm': test_radio_level,
                    'average_sinad_dB': average_sinad,
                    'min_sinad': min_sinad,
                    'max_sinad': max_sinad
                })

                # quick exit if we already passed the min SINAD at this level
                if average_sinad <= sinad_min and amp < -81 :
                    print_green("[MUS Sin] Signal level less that -81dBm")
                    print_green(f"[MUS Sin] SINAD <= {sinad_min:.1f} dB, moving to next freq")
                    break

    # 8) After all measurements, save and plot results
    # 8.a) Create output directory
    #out_dir = test_results.test_results_path
    #os.makedirs(out_dir, exist_ok=True)

    # 8.b) Save CSV
    #csv_path = os.path.join(out_dir, 'mus_results '+str(radio_sn)+'.csv'
    csv_path = os.path.join(out_dir, log_script_prefix + '_' + '_' + str(radio_sn) + '.csv')
    df = pd.DataFrame(results)
    df.to_csv(csv_path, index=False)
    print_green(f"[MUS] Results saved to {csv_path}")

    # 8.c) Plot SINAD vs Frequency for each RX level, separately for NB and WB
    for bw in df['bandwidth'].unique():
        plt.figure()
        for level in sorted(df.loc[df['bandwidth'] == bw, 'rx_level_dBm'].unique()):
            subset = df[(df['bandwidth'] == bw) & (df['rx_level_dBm'] == level)]
            plt.plot(subset['freq_MHz'], subset['average_sinad_dB'], marker='o', label=f"{level:.1f} dBm")

        plt.xlabel('Frequency (MHz)')
        plt.ylabel('SINAD (dB)')
        plt.title(f'MUS {bw}: SINAD vs Frequency')
        plt.legend(title='RX Level')
        plt.grid(True)

        png_path = os.path.join(out_dir, f'mus_plot_{bw}.png')
        plt.savefig(png_path, dpi=200)
        plt.close()
        print_green(f"[MUS] {bw} plot saved to {png_path}")


    # 9) Cleanup
    return True
