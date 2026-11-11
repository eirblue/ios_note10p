# v205 genuine storage driver object result

The v205 synthetic fixture passed 32 cases in three groups. The reviewed source was published, and the single CI run stopped during preflight because `IOKit/perfcontrol/IOPerfControl.h` was not found in the public-header and SDK `usr/include` roots it searched. Private-header roots were not checked, so this does not establish that the header is absent from the full SDK. The preflight also did not include Clang’s resource include path for `<stdatomic.h>`.

The failed preflight occurred before IIG generation or target compilation. No new driver object was produced or inspected, and no metadata join, kernel link/build, or device action occurred. The authenticated failure result was fetched and extracted once. No retry was made.

This run does not establish a compiled or linked storage driver, runtime provider registration, firmware compatibility, or device behavior. The separate v204 static kernel result and v189 physical baseline remain distinct.
