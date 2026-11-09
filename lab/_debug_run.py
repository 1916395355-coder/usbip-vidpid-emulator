import logging, time
from pathlib import Path
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(name)s %(levelname)s %(message)s",
                    handlers=[logging.FileHandler(r"d:\开发项目\usbip-vidpid-spoof\usbip_debug.log", encoding="utf-8"),
                              logging.StreamHandler()])
# run emulate by exec
import runpy
runpy.run_path(r"d:\开发项目\usbip-vidpid-spoof\emulate_iqunix_7c18.py", run_name="__main__")
