# test_methods/Hardware_Smoketests/3_PositionerJogTest.yaml
import time

POS_KEY = "d6050"

def _log(logger, msg, colour="w"):
    try:
        logger.add_line(msg, colour=colour)
    except Exception:
        print(msg)

def _fail(logger, msg):
    try:
        logger.fail_line(msg)
    except Exception:
        print(msg)

def _pick_positioner(equip_mgr):
    pos_group = getattr(equip_mgr, "positioner", None)
    if pos_group is None:
        return None
    if isinstance(pos_group, dict):
        return pos_group.get(POS_KEY)
    return pos_group  # single-object fallback

def run(equip_mgr, _unused, logger, test_config):
    """
    Simple jog test for the Diamond D6050:
      - open port
      - move relative in Az/El
      - wait settle_time
      - close
    """
    _log(logger, f"[3_PositionerJogTest] Selecting positioner: {POS_KEY}")

    pos = _pick_positioner(equip_mgr)
    if not pos:
        _fail(logger, f"No 'positioner.{POS_KEY}' loaded — check location_config.")
        return False

    az_deg      = float(test_config.get("az_jog_deg", 5.0))
    el_deg      = float(test_config.get("el_jog_deg", 0.0))
    obey_limits = bool(test_config.get("obey_limits", True))
    settle_s    = float(test_config.get("settle_time_s", 2.0))

    try:
        if hasattr(pos, "open"):
            pos.open()

        _log(logger, f"[3_PositionerJogTest] Jogging AZ={az_deg:+.2f}°, EL={el_deg:+.2f}°")
        pos.move_relative(az_deg=az_deg, el_deg=el_deg, obey_limits=obey_limits)

        time.sleep(settle_s)

        _log(logger, "PASS", colour="g")
        return True

    except Exception as e:
        _fail(logger, f"[Positioner] Jog test failed: {e}")
        return False

    finally:
        try:
            if hasattr(pos, "close"):
                pos.close()
        except Exception:
            pass
