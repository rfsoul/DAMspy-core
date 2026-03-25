import yaml
from equipment.utils.equipment_loader import EquipmentLoader

loc_cfg   = yaml.safe_load(open("../../../config/location_config.yaml"))
equip_cfg = loc_cfg["Al_desk_GME"]

mgr = EquipmentLoader(equip_cfg)
drv = mgr.get("sinad_meter")

print("→ SINAD =", drv.get_sinad(), "dB")
#print("→ RMS =", drv.get_rms(), "v?")
mgr.close_all()
