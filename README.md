# USB/IP VID·PID Emulator

Pure-Python **USB/IP device emulator** for Windows driver / PnP testing.

Spin up a virtual USB device with a custom `VID`/`PID`, attach it via [usbip-win2](https://github.com/vadimgrn/usbip-win2), and verify that Device Manager (and vendor software that keys off hardware IDs) sees the ID you expect — **without physical hardware**.

> Intended use: driver packaging, INF binding, and peripheral WebHID filter checks.
> Not for bypassing licensing, DRM, or anti-cheat.

## Why

Vendor apps and driver catalogs often match on `USB\VID_xxxx&PID_yyyy`.  
Reproducing that ID on a clean machine usually means buying the device. This repo gives you a software stand-in for that step.

## Status

| Area | State |
|------|--------|
| Generic boot mouse / keyboard HID | Ready |
| Composite mouse+keyboard with arbitrary VID/PID | Ready |
| **IQUNIX** Raw HID (`FF60/61`) examples | Validated on real Windows + usbip-win2 |
| Logitech G HUB full recognition | Roadmap |
| Motherboard ARGB / WinRing0 stacks | **Do not use** for “open vendor app and control lights” on non-matching boards |

## Repo layout

```text
examples/
  generic/          # minimal HID + arbitrary VID/PID composite
  iqunix/           # validated IQUNIX-style Raw HID demos
lab/                # experiments (incomplete / unsafe / brand-specific drafts)
scripts/            # portable attach helper
```

Local capture dumps belong in `_scratch/` and are gitignored.

## Requirements

- Windows 10/11
- Python 3.10+
- [usbip-win2](https://github.com/vadimgrn/usbip-win2/releases) (attestation-signed build recommended)
- PyPI package: `usbip`

```powershell
pip install -r requirements.txt
```

If `usbip.exe` is not on `PATH`:

```powershell
$env:USBIP_EXE = 'C:\Path\To\USBip\usbip.exe'
```

## Quick start (generic)

Terminal A — start emulator:

```powershell
cd examples\generic
python -u emulate_hid.py --vid 0x1234 --pid 0x5678 --kind keyboard
```

Or composite mouse+keyboard:

```powershell
python -u emulate_vidpid.py --vid 046D --pid C08C --product "PnP test"
```

Terminal B — admin — attach:

```powershell
# from repo root
powershell -ExecutionPolicy Bypass -File .\scripts\attach.ps1
```

Check Device Manager → the hardware ID should look like:

```text
USB\VID_1234&PID_5678
```

Detach when done:

```powershell
& $env:USBIP_EXE detach -p 1
```

## IQUNIX examples (validated path)

These emulate `VID_3869` devices with:

- Boot keyboard interface (optional)
- Vendor Raw HID: Usage Page `0xFF60`, Usage `0x61`, 32-byte In/Out (VIA/QMK-style WebHID filter)

| Script | PID | Notes |
|--------|-----|--------|
| `examples/iqunix/emulate_iqunix_7838.py` | `7838` | EC75-class Raw HID |
| `examples/iqunix/emulate_iqunix_7c18.py` | `7C18` | Same descriptor family |
| `examples/iqunix/emulate_iqunix_ev63.py` | `63E1` | EV63 WebHID filter |

```powershell
cd examples\iqunix
python -u emulate_iqunix_7838.py
# admin other terminal:
powershell -ExecutionPolicy Bypass -File ..\..\scripts\attach.ps1
```

Or use `attach_7838.bat` / `attach_7c18.bat` (expects `USBIP_EXE` or a local `usbip.exe`).

**What “works” means here:** Windows enumerates the hardware ID; WebHID filters that match `3869` + `FF60/61` can see the interface. It does **not** claim a full clone of every IQUNIX cloud feature or firmware command.

## Safety

| Device class | Risk |
|--------------|------|
| Mouse / keyboard HID | Generally low — failed protocol ⇒ app error, not host hang |
| Motherboard lighting controllers + OEM apps using **WinRing0** | High — kernel-level I/O against the wrong board can freeze the machine |

Keep motherboard / Super-I/O experiments in `lab/` and do not open OEM lighting centers against fake controllers on non-matching hardware.

## Roadmap

- [ ] Logitech: Device Manager ID demos → then document G HUB recognition limits
- [ ] Cleaner multi-interface templates (audio + HID hubs)
- [ ] Capture helper: dump real device descriptors into an emulator stub
- [ ] CI smoke: start emulator + assert USB/IP `list` output

## Disclaimer

This project is for interoperability testing and education.  
You are responsible for complying with local law and vendor terms. Do not use it to impersonate devices for fraud or to circumvent protections.

## License

MIT — see [LICENSE](LICENSE).

## Credits

- USB/IP wire protocol + Windows VHCI: [usbip-win2](https://github.com/vadimgrn/usbip-win2)
- Python USB/IP stack: [`usbip` on PyPI](https://pypi.org/project/usbip/)
