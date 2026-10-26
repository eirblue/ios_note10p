# v8 diagnostic screen console

The opt-in `screen_log=true` build adds a small terminal to the top-left quarter
of the display. It requires the existing `auto_return=true` diagnostic build.
This is experimental kernel display code; physical output is not yet verified.

## Display path

- Uses a fixed-size text ring, the pinned Linux 8x16 ASCII font at 2x scale,
  bounded wrapping and scrolling, and two DMA buffers owned by the diagnostic.
- Window width and height are at most half the active panel dimensions, aligned
  down to the panel's update granularity. Other pixels are not drawn by the
  renderer. The target is preservation of the logo in the panel's remaining RAM.
- The vendor kernel disables partial updates and forces full-width updates.
  Those defaults remain for ordinary frames. Only a marked diagnostic update
  enables the experimental partial path. The normalized hardware update region
  must exactly match the requested top-left window and remain within the quarter;
  otherwise the frame is rejected before device submission. There is no
  full-screen fallback.
- Supports the pinned nonlegacy ION/fence path and a single command-mode DSI
  panel. Unsupported layouts stop the console. No fixed physical address or
  bootloader framebuffer mapping is used.
- The normal DPU submission, DMA synchronization and retire-fence path are used.
  A timeout stops further submissions. Two existing DPU panic paths are suppressed
  only for this diagnostic's frames; normal frames keep vendor behavior.

## Logs and power management

The console callback only copies bounded text. Display calls run on a separate
freezable workqueue, at most twice per second. Redundant sequence copies and long
build/cycle identifiers are omitted from the window; error and status fields
are prioritized. Raw printk records remain unchanged for host capture.

The PM diagnostic pauses and drains painting before entering the PM framework,
then resumes it after the call returns, including errors. The reboot notifier
stops new painting without waiting on the display. No wakeup-source abort is
bypassed, and no new persistent wake lock is introduced by this console.

v8 also adds `N10PMS1` checksummed phase records for each PM attempt:

| Stage | Last checkpoint reached |
|---|---|
| 0 | PM ownership unavailable |
| 1 | PM wrapper entered |
| 10 | Prepare notifier entered |
| 11 | Interruptible filesystem sync entered |
| 12 | Filesystem sync completed |
| 13 | Freezer entered |
| 14 | Freezer returned |
| 20 | Device suspend entered |
| 21 | Device suspend returned |

The existing PM pass criteria, three-attempt bound, low-level suspend guard and
90-second recovery request remain. Stage records locate failure; they do not
convert an EBUSY abort into a pass.

## Evidence requirements

The native renderer model checks geometry, clipping, guard bytes, wrapping,
scrolling, compact status formatting and invalid inputs. Source contracts pin
the upstream display files and verify the quarter-region guards. The actual PM
C model also checks pause/resume ordering across its 32 cases. These models do
not establish physical panel behavior.

A successful kernel compile and a single device roundtrip are still required.
`N10DSP1 submit=ok` means the software submission/fence completed, not that a
person saw readable text or that the surrounding logo was preserved. Visual
placement and logo preservation require a device observation. The console starts
after Linux initializes the display; it cannot show logs from the earlier
bootloader-only logo stage. Display/driver lockups can still require manual
recovery, as with the existing diagnostic kernel.
