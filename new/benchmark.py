import argparse
import iolib
from engine import Hand
import sys
import os
sys.path.append(os.path.dirname(__file__))

def evaluate(noteseq):
    correct_notes = 0
    total_notes_with_reference = 0
    for note in noteseq:
        if note.reference_fingerings:
            total_notes_with_reference += 1
            if note.fingering in note.reference_fingerings:
                correct_notes += 1

    accuracy = (correct_notes / total_notes_with_reference) * 100 if total_notes_with_reference > 0 else 0
    return correct_notes, total_notes_with_reference, accuracy

def main():
    parser = argparse.ArgumentParser(description="Benchmark fingering algorithm against PIG data.")
    parser.add_argument("pig_file", type=str, help="Path to the PIG file for benchmarking.")
    args = parser.parse_args()

    print(f"Running benchmark on {args.pig_file}...")

    # Load right hand data and generate fingerings
    rh_noteseq = iolib.read_pig(args.pig_file, beam=0)
    if rh_noteseq:
        rh_hand = Hand(rh_noteseq, side="right")
        rh_hand.generate()
        rh_correct, rh_total, rh_accuracy = evaluate(rh_noteseq)
        print(f"Right Hand (greedy algorithm): {rh_correct}/{rh_total} notes correct. Accuracy: {rh_accuracy:.2f}%")

    # Load left hand data and generate fingerings
    lh_noteseq = iolib.read_pig(args.pig_file, beam=1)
    if lh_noteseq:
        lh_hand = Hand(lh_noteseq, side="left")
        lh_hand.generate()
        lh_correct, lh_total, lh_accuracy = evaluate(lh_noteseq)
        print(f"Left Hand (greedy algorithm): {lh_correct}/{lh_total} notes correct. Accuracy: {lh_accuracy:.2f}%")

if __name__ == '__main__':
    main()
