from music21 import converter, note
from music21.articulations import Fingering
import os
import subprocess
import utils

class INote:
    def __init__(self):
        self.name = None
        self.isChord = False
        self.isBlack = False
        self.pitch = 0
        self.octave = 0
        self.x = 0.0
        self.time = 0.0
        self.duration = 0.0
        self.fingering = 0
        self.measure = 0
        self.chordnr = 0
        self.NinChord = 0
        self.chordID = 0
        self.noteID = 0
        self.reference_fingerings: list[int] = []

def get_finger_music21(n, j=0):
    fingers = []
    for art in n.articulations:
        if type(art) == Fingering:
            fingers.append(art.fingerNumber)
    finger = 0
    if len(fingers) > j:
        finger = fingers[j]
    return finger

def _reader(sf, beam=0):
    noteseq = []
    if hasattr(sf, 'parts'):
        if len(sf.parts) <= beam:
            return []
        strm = sf.parts[beam].flatten()
    elif hasattr(sf, 'elements'):
        if len(sf.elements) == 1 and beam == 1:
            strm = sf[0]
        else:
            if len(sf) <= beam:
                return []
            strm = sf[beam]
    else:
        strm = sf.flatten()

    chordID = 0
    noteID = 0
    for n in strm.getElementsByClass("GeneralNote"):
        if n.duration.quarterLength == 0:
            continue
        if hasattr(n, 'tie'):
            if n.tie and (n.tie.type == 'continue' or n.tie.type == 'stop'):
                continue

        if n.isNote:
            an = INote()
            an.noteID = noteID
            an.note21 = n
            an.isChord = False
            an.name = n.name
            an.octave = n.octave
            an.measure = n.measureNumber
            an.x = utils.keypos(n)
            an.pitch = n.pitch.midi
            an.time = n.offset
            an.duration = n.duration.quarterLength
            an.isBlack = False
            pc = n.pitch.pitchClass
            an.isBlack = False
            if pc in [1, 3, 6, 8, 10]:
                an.isBlack = True
            if n.lyrics:
                an.fingering = n.lyric
            an.fingering = get_finger_music21(n)
            noteseq.append(an)
            noteID += 1
        elif n.isChord:
            if n.tie and (n.tie.type == 'continue' or n.tie.type == 'stop'):
                continue
            sfasam = 0.05
            for j, cn in enumerate(n.pitches):
                an = INote()
                an.chordID = chordID
                an.noteID = noteID
                an.isChord = True
                an.pitch = cn.midi
                an.note21 = cn
                an.name = cn.name
                an.chordnr = j
                an.NinChord = len(n.pitches)
                an.octave = cn.octave
                an.measure = n.measureNumber
                an.x = utils.keypos(cn)
                an.time = n.offset - sfasam * (len(n.pitches) - j - 1)
                an.duration = n.duration.quarterLength + sfasam * (an.NinChord - 1)
                if hasattr(cn, 'pitch'):
                    pc = cn.pitch.pitchClass
                else:
                    pc = cn.pitchClass
                if pc in [1, 3, 6, 8, 10]:
                    an.isBlack = True
                else:
                    an.isBlack = False
                an.fingering = get_finger_music21(n, j)
                noteID += 1
                noteseq.append(an)
            chordID += 1
    if len(noteseq) < 2:
        return []
    return noteseq

def read_score(filename, rbeam, lbeam):
    xmlfn = filename
    if '.msc' in filename:
        xmlfn = str(filename).replace('.mscz', '.xml').replace('.mscx', '.xml')
        subprocess.run(['musescore', '-f', filename, '-o', xmlfn])

    sf = converter.parse(xmlfn)

    rh_noteseq = _reader(sf, beam=rbeam)
    lh_noteseq = _reader(sf, beam=lbeam)

    return sf, rh_noteseq, lh_noteseq

def _annotate_fingers_xml(sf, noteseq, beam, lyrics):
    p0 = sf.parts[beam]
    idx = 0
    for el in p0.flatten().getElementsByClass("GeneralNote"):
        if el.isRest:
            continue
        if el.duration.quarterLength == 0:
            continue
        if el.tie is not None and el.tie.type in ['stop', 'continue']:
            continue
        if idx >= len(noteseq):
            break
        if el.isNote:
            n = noteseq[idx]
            if lyrics:
                el.addLyric(n.fingering)
            else:
                el.articulations.append(Fingering(n.fingering))
            idx += 1
        elif el.isChord:
            for j, cn in enumerate(el.pitches):
                if idx >= len(noteseq):
                    break
                n = noteseq[idx]
                if lyrics:
                    nl = len(cn.chord21.pitches) - cn.chordnr
                    el.addLyric(cn.fingering, nl)
                else:
                    el.articulations.append(Fingering(n.fingering))
                idx += 1
            if idx >= len(noteseq) and el.isChord:
                break
    return sf

def write_score(sf, rh_noteseq, lh_noteseq, outputfile, rbeam, lbeam, below_beam):
    if rh_noteseq:
        sf = _annotate_fingers_xml(sf, rh_noteseq, rbeam, below_beam)
    if lh_noteseq:
        sf = _annotate_fingers_xml(sf, lh_noteseq, lbeam, below_beam)
    sf.write('musicxml', fp=outputfile)


def read_pig(fname: str, beam: int) -> list[INote]:
    noteseq = []
    noteID = 0
    with open(fname, 'r') as f:
        for line in f:
            if line.startswith('//'):
                continue

            parts = line.strip().split('\t')
            if len(parts) < 7:
                continue

            channel = int(parts[6])
            if channel != beam:
                continue

            an = INote()
            an.noteID = noteID

            # Time and duration
            an.time = float(parts[1])
            an.duration = float(parts[2]) - an.time

            # Pitch and spatial coordinates
            try:
                n = note.Note(parts[3])
                an.name = n.name
                an.octave = n.octave
                an.pitch = n.pitch.midi
                an.x = utils.keypos(n)
                an.isBlack = n.pitch.pitchClass in [1, 3, 6, 8, 10]
            except Exception:
                continue


            # Reference fingerings
            if len(parts) > 7:
                try:
                    fingering_str = parts[7]
                    raw_fingerings = [int(f) for f in fingering_str.split('_')]

                    filtered_fingerings = []
                    if channel == 0: # Right hand
                        filtered_fingerings = [f for f in raw_fingerings if f > 0]
                    else: # Left hand
                        filtered_fingerings = [f for f in raw_fingerings if f < 0]

                    an.reference_fingerings = [abs(f) for f in filtered_fingerings]
                except (ValueError, IndexError):
                    an.reference_fingerings = []
            else:
                an.reference_fingerings = []

            noteseq.append(an)
            noteID += 1

    return noteseq