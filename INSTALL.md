# How to install voltdemort

This is (yet) a manual procedure.

* Copy all `*.py` files into `/opt/voltdemort` (or simply clone the repo over there).
* Copy the `voltdemort.service` file into `/etc/systemd/system/`.
* Reload *systemd* daemon with: `systemctl daemon-reload`
* Edit the config data (vars) on the file `/opt/voltdemort/voltdemort.py`
* Enable and start the service with: `systemctl enable --now voltdemort`
* Check the logs/status with `journalctl -f -u voltdemort`

