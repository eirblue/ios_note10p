"""One new generic type3 readonly span candidate Image; first use PC only."""
from build_builtin_init_image import main

if __name__=='__main__':
    import sys
    # Selector is removed before the common builder parses its own closed arguments.
    kind='kernel-readonly-span-candidate'
    if '--producer' in sys.argv:
        index=sys.argv.index('--producer')
        if index+1>=len(sys.argv) or sys.argv[index+1]!='v109-readonly-stage-witness-pc':
            raise ValueError('explicit v109 witness producer selector required')
        kind='kernel-readonly-stage-witness-candidate';del sys.argv[index:index+2]
    main(kind)
