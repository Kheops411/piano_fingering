import argparse
import iolib
import engine

def main():
    pr = argparse.ArgumentParser(description="PianoPlayer")
    pr.add_argument("filename", type=str, help="Input music xml/mscz/mscx file name")
    pr.add_argument("-o", "--outputfile", metavar='output.xml', type=str, help="Annotated output xml file name",
                    default='new/output.xml')
    pr.add_argument("-n", "--n-measures", metavar='', type=int, help="[100] Number of score measures to scan",
                    default=100)
    pr.add_argument("-s", "--start-measure", metavar='', type=int, help="Start from measure number [1]", default=1)
    pr.add_argument("-d", "--depth", metavar='', type=int, help="[auto] Depth of combinatorial search, [4-9]",
                    default=0)
    pr.add_argument("-rbeam", metavar='', type=int, help="[0] Specify Right Hand beam number", default=0)
    pr.add_argument("-lbeam", metavar='', type=int, help="[1] Specify Left Hand beam number", default=1)
    pr.add_argument("-b", "--below-beam", help="Show fingering numbers below beam line", action="store_true")
    pr.add_argument("-l", "--left-only", help="Fingering for left hand only", action="store_true")
    pr.add_argument("-r", "--right-only", help="Fingering for right hand only", action="store_true")
    pr.add_argument("-XXS", "--hand-size-XXS", help="Set hand size to XXS", action="store_true")
    pr.add_argument("-XS", "--hand-size-XS", help="Set hand size to XS", action="store_true")
    pr.add_argument("-S", "--hand-size-S", help="Set hand size to S", action="store_true")
    pr.add_argument("-M", "--hand-size-M", help="Set hand size to M", action="store_true")
    pr.add_argument("-L", "--hand-size-L", help="Set hand size to L", action="store_true")
    pr.add_argument("-XL", "--hand-size-XL", help="Set hand size to XL", action="store_true")
    pr.add_argument("-XXL", "--hand-size-XXL", help="Set hand size to XXL", action="store_true")
    args = pr.parse_args()

    hand_size = 'M'
    if args.hand_size_XXS: hand_size = 'XXS'
    if args.hand_size_XS: hand_size = 'XS'
    if args.hand_size_S: hand_size = 'S'
    if args.hand_size_M: hand_size = 'M'
    if args.hand_size_L: hand_size = 'L'
    if args.hand_size_XL: hand_size = 'XL'
    if args.hand_size_XXL: hand_size = 'XXL'

    sf, rh_noteseq, lh_noteseq = iolib.read_score(args.filename, args.rbeam, args.lbeam)

    autodepth = args.depth == 0

    if not args.left_only and rh_noteseq:
        rh_noteseq = engine.find_fingerings(rh_noteseq, "right", hand_size, args.depth, autodepth,
                                            args.below_beam, args.start_measure, args.n_measures)

    if not args.right_only and lh_noteseq:
        lh_noteseq = engine.find_fingerings(lh_noteseq, "left", hand_size, args.depth, autodepth,
                                            args.below_beam, args.start_measure, args.n_measures)

    iolib.write_score(sf, rh_noteseq, lh_noteseq, args.outputfile, args.rbeam, args.lbeam, args.below_beam)

if __name__ == '__main__':
    main()