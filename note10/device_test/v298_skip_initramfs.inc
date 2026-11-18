/* Only the existing built-in diagnostic route consumes the bootloader skip. */
static int __init skip_initramfs_param(char *str)
{
	if (*str)
		return 0;
	if (IS_ENABLED(CONFIG_NOTE10_BUILTIN_INIT_ROUTE) &&
	    IS_ENABLED(CONFIG_NOTE10_V154_LINUX_DIAGNOSTIC))
		return 1;
	do_skip_initramfs = 1;
	return 1;
}
