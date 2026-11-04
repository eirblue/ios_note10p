"""One new generic type3 readonly span candidate Image; first use PC only."""
from build_builtin_init_image import main

if __name__=='__main__':
    import sys
    # Selector is removed before the common builder parses its own closed arguments.
    kind='kernel-readonly-span-candidate'
    if '--producer' in sys.argv:
        index=sys.argv.index('--producer')
        choices={'v121-native-prefree-output-zero-candidate-pc-first':'kernel-prefree-output-zero-observation-candidate',
                 'v109-readonly-stage-witness-pc':'kernel-readonly-stage-witness-candidate',
                 'v116-native-scoped-output-candidate-pc-first':'kernel-scoped-verified-output-candidate'}
        if index+1>=len(sys.argv) or sys.argv[index+1] not in choices:
            raise ValueError('explicit closed class3 producer selector required')
        kind=choices[sys.argv[index+1]];del sys.argv[index:index+2]
    main(kind)
