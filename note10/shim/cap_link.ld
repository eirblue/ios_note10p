/* Relative addresses only; this is a research ELF, not a deployment address. */
ENTRY(_start)
PHDRS { code PT_LOAD FLAGS(5); record PT_LOAD FLAGS(6); }
SECTIONS {
    . = 0;
    .text : { KEEP(*(.text.entry)) } :code
    . = ALIGN(64);
    .data : { KEEP(*(.data.record)) } :record
    /DISCARD/ : { *(.comment) *(.note*) }
}
