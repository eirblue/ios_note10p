# v140 DSIM terminal result

The v140 new-only validation, CI build, and package completed successfully. The single physical cycle wrote BOOT once, rebooted once, performed one internal load and reboot, and returned automatically to TWRP; all five partition checks passed.

The display-freeze admission gate refused with errno -16 because admission was still active at the immediate freeze check. No current terminal witness was produced, so the new DSIM terminal proof was not reached. The cycle is spent and must not be replayed. No XNU entry or full boot was observed, and watchdog cause remains unqualified. This result makes no physical clock-off claim.
