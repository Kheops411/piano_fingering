from music21.articulations import Fingering
import pianoplayer.utils as utils

class Hand:
    def __init__(self, noteseq, side="right", size='M'):
        self.LR = side
        self.noteseq = noteseq
        self.fingerseq = []
        self.depth = 9
        self.autodepth = True
        self.verbose = True
        self.lyrics = False
        self.size = size
        
        self.frest = [None, -7.0, -2.8, 0.0, 2.8, 5.6]
        self.weights = [None, 1.1, 1.0, 1.1, 0.9, 0.8]
        self.bfactor = [None, 0.3, 1.0, 1.1, 0.8, 0.7]
        
        self.hf = utils.handSizeFactor(size)
        self.frest = [None if f is None else f * self.hf for f in self.frest]
        self.cfps = list(self.frest)
        self.cost = -1
        
        print('Your hand span set to size-' + size, 'which is', 21 * self.hf, 'cm')
        print('(max relaxed distance between thumb and pinkie)')

    def set_fingers_positions(self, fings, notes, i):
        if i >= len(fings) or i >= len(notes) or fings[i] < 1 or fings[i] > 5:
            return
        
        anchor = self.frest[fings[i]]
        if anchor is not None:
            self.cfps = [None if self.frest[j] is None else (self.frest[j] - anchor) + notes[i].x 
                         for j in range(6)]

    def _skip(self, fa, fb, na, nb, hf, LR, level):
        xba = nb.x - na.x
        
        if not na.isChord and not nb.isChord:
            if fa == fb and xba and na.duration < 4:
                return True
            if fa > 1:
                if fb > 1 and (fb - fa) * xba < 0:
                    return True
                if fb == 1 and nb.isBlack and xba > 0:
                    return True
            elif na.isBlack and xba < 0 and fb > 1 and na.duration < 2:
                return True
        
        elif na.isChord and nb.isChord and na.chordID == nb.chordID:
            axba = abs(xba) * hf / 0.8
            chord_rules = [
                (fa == fb),
                (fa < fb and LR == 'left'),
                (fa > fb and LR == 'right'),
                (axba > 5 and {fa, fb} == {3, 4}),
                (axba > 5 and {fa, fb} == {4, 5}),
                (axba > 6 and {fa, fb} == {2, 3}),
                (axba > 7 and {fa, fb} == {2, 4}),
                (axba > 8 and {fa, fb} == {3, 5}),
                (axba > 11 and {fa, fb} == {2, 5}),
                (axba > 12 and {fa, fb} == {1, 2}),
                (axba > 14 and {fa, fb} == {1, 3}),
                (axba > 16 and {fa, fb} == {1, 4})
            ]
            return any(chord_rules)
        
        return False

    def optimize_seq(self, nseq, istart):
        if not nseq:
            return ([0] * 9, -1)
        
        depth = self._calculate_depth(nseq)
        notes = nseq[:depth]
        
        if depth <= 1:
            return ([istart or 1] + [0] * 8, 0.0)
        
        memo = {}
        all_fingers = (1, 2, 3, 4, 5)
        valid_starts = (istart,) if istart else all_fingers
        
        def recurse(level, prev_f):
            if (level, prev_f) in memo:
                return memo[(level, prev_f)]
            
            if level == depth:
                return (0.0, [])
            
            candidates = valid_starts if level == 0 else all_fingers
            best_cost, best_seq = float('inf'), None
            
            for f in candidates:
                if level > 0 and self._skip(prev_f, f, notes[level - 1], notes[level], 
                                            self.hf, self.LR, level):
                    continue
                
                move_cost = self._compute_move_cost(level, prev_f, f, notes) if level > 0 else 0.0
                future_cost, future_seq = recurse(level + 1, f)
                total_cost = move_cost + future_cost
                
                if total_cost < best_cost:
                    best_cost, best_seq = total_cost, [f] + future_seq
            
            if best_seq is None:
                best_cost, best_seq = float('inf'), []
            
            memo[(level, prev_f)] = (best_cost, best_seq)
            return memo[(level, prev_f)]
        
        total_cost, sequence = recurse(0, 0)
        
        if not sequence:
            return ([0] * 9, -1)
        
        avg_velocity = total_cost / (depth - 1) if depth > 1 else 0.0
        return (sequence + [0] * (9 - len(sequence)), avg_velocity)

    def _calculate_depth(self, nseq):
        effective_depth = len(nseq)
        
        if self.autodepth:
            if nseq[0].isChord:
                self.depth = max(3, nseq[0].NinChord - nseq[0].chordnr + 1)
            else:
                for i in range(1, effective_depth):
                    if nseq[i].time - nseq[0].time > 3.5:
                        self.depth = i + 1
                        break
                else:
                    self.depth = effective_depth
        
        return min(self.depth, effective_depth)

    def _compute_move_cost(self, level, prev_f, curr_f, notes):
        anchor = self.frest[prev_f]
        finger_pos = (self.frest[curr_f] - anchor) + notes[level - 1].x
        distance = abs(notes[level].x - finger_pos)
        time_delta = abs(notes[level].time - notes[level - 1].time) + 0.1
        velocity = distance / time_delta
        
        weight = self.weights[curr_f]
        if notes[level].isBlack:
            weight *= self.bfactor[curr_f]
        
        return velocity / weight

    def generate(self, start_measure=0, nmeasures=1000):
        if start_measure == 1:
            start_measure = 0
        
        if self.LR == "left":
            for note in self.noteseq:
                note.x = -note.x
        
        self.depth = max(3, min(9, self.depth))
        start_finger = 0
        
        for i, note in enumerate(self.noteseq):
            if note.measure and not (start_measure <= note.measure <= start_measure + nmeasures):
                continue
            
            window = self.noteseq[i:i + 9]
            fingering, velocity = self.optimize_seq(window, start_finger)
            
            if velocity == -1:
                fingering, velocity = self.optimize_seq(window, 0)
            
            note.fingering = fingering[0]
            note.cost = velocity
            start_finger = fingering[1]
            
            self.set_fingers_positions(fingering, window, 0)
            self.fingerseq.append(list(self.cfps))
            
            self._print_progress(i, note, fingering, velocity, window)

    def _print_progress(self, i, note, fingering, velocity, window):
        if self.verbose:
            measure = f"meas.{note.measure: <3}" if note.measure else " " * 9
            pitch = f"Pitch:{note.pitch} Octave:{note.octave}"
            vel = f"v={round(velocity, 1)}" if velocity != -1 else "v=N/A"
            print(f"{measure} finger_{fingering[0]}  plays  {pitch: <22} {vel}", end='')
            
            display_depth = min(self.depth, len(window))
            seq_str = str(fingering[:display_depth])
            suffix = f" d:{display_depth}" if self.autodepth else ""
            print(f"\t{seq_str}{suffix}")
        elif i and not i % 100 and note.measure:
            print(f'scanned {i}/{len(self.noteseq)} notes, measure {note.measure + 1} for the {self.LR} hand...')