from typing import List, Optional
from collections import defaultdict
import music21.note
import music21.pitch

# --- Structures de données recréées pour être fidèles à l'application ---

class INote:
    """
    Réplique autonome de la classe INote de pianoplayer.
    Cette structure de données est conçue pour être compatible avec les 
    algorithmes qui attendent le format interne de l'application.
    """
    def __init__(self):
        self.name: Optional[str] = None
        self.isChord: bool = False
        self.isBlack: bool = False
        self.pitch: int = 0
        self.octave: int = 0
        self.x: float = 0.0
        self.time: float = 0.0
        self.duration: float = 0.0
        self.fingering: int = 0
        self.measure: int = 0
        # Attributs liés aux accords, peuplés par la détection d'accords
        self.chordnr: int = 0
        self.NinChord: int = 0
        self.chordID: int = 0
        self.noteID: int = 0

def keypos(n: music21.note.Note) -> float:
    """
    Réplique autonome de la fonction keypos de pianoplayer.utils.
    Calcule une position sur le clavier basée sur le numéro de note MIDI.
    """
    return float(n.pitch.midi)

# --- Fonction de lecture améliorée et autonome ---

def reader_PIG_benchmark(fname: str, beam: Optional[int] = None, sep: Optional[str] = None,
                         comment_prefixes=("#", "//", ";")) -> List[INote]:
    """
    Lit un fichier au format PIG et le convertit en une liste d'objets INote.
    Cette version est conçue pour être autonome (sans import de pianoplayer)
    et robuste pour des fichiers de benchmark au format variable.

    Args:
        fname: Chemin vers le fichier .txt.
        beam: Filtre par canal (0=droite, 1=gauche). Si None, lit tous les canaux.
        sep: Séparateur de colonnes (défaut: espaces/tabs multiples).
        comment_prefixes: Préfixes de ligne de commentaire à ignorer.

    Returns:
        Une liste d'objets INote triés par temps, puis par hauteur.
    """
    noteseq = []
    noteID_counter = 0

    # --- Fonctions d'aide internes pour un parsing robuste ---
    def is_comment_line(s: str) -> bool:
        return s.lstrip().startswith(comment_prefixes)

    def parse_pitch(s: str) -> music21.pitch.Pitch:
        try:
            # Tente de parser la hauteur comme un numéro MIDI
            p = music21.pitch.Pitch()
            p.midi = int(float(s.strip()))
            return p
        except ValueError:
            # Sinon, le parse comme une notation scientifique (ex: "C#4")
            return music21.note.Note(s.strip()).pitch

    def find_onset_index(parts: List[str]) -> int:
        for i in range(len(parts) - 1):
            try:
                float(parts[i].strip())
                float(parts[i + 1].strip())
                return i
            except ValueError:
                continue
        raise ValueError("Paire onset/offset non trouvée")

    def find_column_by_value(parts: List[str], values: List[str]) -> Optional[str]:
        for token in reversed(parts):
            if token.strip() in values:
                return token.strip()
        return None

    # --- Lecture et parsing du fichier ---
    try:
        with open(fname, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"[ERROR] Fichier non trouvé : {fname}")
        return []

    print(f"Lecture du fichier PIG de benchmark : {fname}...")

    for line_num, raw in enumerate(lines, 1):
        raw_str = raw.strip()
        if not raw_str or is_comment_line(raw_str):
            continue

        parts = [p for p in (raw_str.split(sep) if sep else raw_str.split()) if p]
        if len(parts) < 3:
            continue

        try:
            onset_idx = find_onset_index(parts)
            onset = float(parts[onset_idx].strip())
            offset = float(parts[onset_idx + 1].strip())
            pitch_field = parts[onset_idx + 2]

            channel_str = find_column_by_value(parts, ["0", "1"])
            if channel_str is not None:
                channel = int(channel_str)
                if beam is not None and channel != beam:
                    continue

            # **Lecture du doigté (crucial pour le benchmark)**
            # Le doigté est souvent la dernière colonne entière
            finger = 0
            if len(parts) > 7:
                 try:
                     finger = int(parts[7].strip())
                 except (ValueError, IndexError):
                     pass # Le doigté n'est pas présent ou invalide
            
            duration = offset - onset
            if duration <= 1e-9:
                continue

            pitch_obj = parse_pitch(pitch_field)
            note_obj = music21.note.Note()
            note_obj.pitch = pitch_obj
            
            an = INote()
            an.time = onset
            an.duration = duration
            an.pitch = int(round(pitch_obj.midi))
            an.name = pitch_obj.name
            an.octave = pitch_obj.octave
            an.x = keypos(note_obj)
            an.isBlack = pitch_obj.isBlack
            an.fingering = abs(finger) # On stocke le doigté de référence
            an.noteID = noteID_counter
            
            noteseq.append(an)
            noteID_counter += 1
            
        except (ValueError, IndexError) as e:
            print(f"[AVERTISSEMENT] Ligne malformée ignorée #{line_num}: {raw_str} -> {e}")
        except Exception as e:
            print(f"[ERREUR] Erreur inattendue sur la ligne #{line_num}: {raw_str} -> {e}")

    # --- Post-traitement pour la détection des accords ---
    time_groups = defaultdict(list)
    for n in noteseq:
        # Grouper les notes par temps de début (avec une tolérance)
        time_groups[round(n.time, 9)].append(n)
    
    chordID_counter = 0
    for group in time_groups.values():
        if len(group) > 1:
            # Trier les notes de l'accord par hauteur
            group.sort(key=lambda n: n.pitch)
            for i, n in enumerate(group):
                n.isChord = True
                n.NinChord = len(group)
                n.chordnr = i # Index de la note dans l'accord (0=plus basse)
                n.chordID = chordID_counter
            chordID_counter += 1

    # Tri final pour garantir un ordre canonique
    noteseq.sort(key=lambda n: (n.time, n.pitch))
    
    status = "Fichier vide ou aucune note valide trouvée" if not noteseq else f"{len(noteseq)} notes lues"
    print(f"Lecture terminée. {status}.")
    
    return noteseq