from MidiFile import MIDIFile
from io import TextIOWrapper as FILE
from math import floor
from sys import argv as CMD_ARGS, exit
from typing import List, Dict, Union

from mdt_decomp_rip import (
    NOTE_NAMES,
    remove_path,
    Song,
    Channel,
    Macro
)


# Constants
MIDI_EPSILON = 3 / 960

# MIDI instrument suggestions for each track from HRtP
# Made with Microsoft GS Wavetable Synth and Arachno Soundfont in mind.
# These may sound terrible with other synths/soundfonts.
A_SACRED_LOT = {
    1: 25,  # Acoustic Guitar (steel)
    2: 26,  # Jazz Guitar
    3: 16,  # Drawbar Organ
    4: 6  # Harpsichord
}
ETERNAL_SHRINE_MAIDEN = {
    1: 5,  # Electric Piano 2
    2: 11,  # Vibraphone
    5: 4,  # Electric Piano 1
    10: 77,  # Shakuhashi
    11: 16  # Drawbar Organ
}
POSITIVE_AND_NEGATIVE = {
    1: 6,  # Harpsichord
    2: 87,  # Bass + Lead
    3: 26,  # Jazz Guitar
    5: 62,  # Synth Brass 1
    11: 30  # Distortion Guitar
}
HIGHLY_RESPONSIVE_PRAYERS = {
    1: 11,  # Vibraphone
    4: 7,  # Clavichord/Clavinet
    5: 39,  # Synth Bass 2
    7: 39,  # Synth Bass 2
    11: 35,  # Fretless Bass
    13: 26  # Jazz Guitar
}
STRANGE_EASTERN_DISCOURSE = {
    1: 7,  # Clavichord/Clavinet
    3: 35,  # Fretless Bass
    4: 108,  # Kalimba
    6: 73,  # Flute
    # 6 actually sounds GREAT as 67 (Baritone Sax) in Arachno Soundfont,
    # but it sounds really terrible in Microsoft GS Wavetable. 😭
    7: 26  # Jazz Guitar
}
ANGELS_LEGEND = {
    1: 30,  # Distortion Guitar
    2: 20,  # Reed Organ
    4: 7,  # Clavichord/Clavinet
    5: 2,  # Electric Grand Piano
    7: 17,  # Percussive Organ
    13: 39  # Synth Bass 2
}
ORIENTAL_MAGICIAN = {
    1: 5,  # Electric Piano 2
    4: 42,  # Cello
    5: 6,  # Harpsichord
    6: 6,  # Harpsichord
    7: 34,  # Picked Bass
    11: 67,  # Baritone Sax
    12: 65  # Alto Sax
}
BLADE_OF_BANISHMENT = {
    3: 36,  # Slap Bass 1
    4: 65,  # Alto Sax
    5: 25,  # Acoustic Guitar (steel)
    6: 26  # Jazz Guitar
}
MAGIC_MIRROR = {
    2: 38,  # Synth Bass 1
    3: 108,  # Kalimba
    6: 87  # Bass + Lead
}
LEGEND_OF_KAGE = {
    1: 6,  # Harpsichord
    2: 33,  # Fingered Bass
    5: 11,  # Vibraphone
    6: 39,  # Synth Bass 2
    7: 119,  # Reverse Cymbal
    9: 118,  # Synth Drum
    10: 117,  # Melodic Tom
    11: 117,  # Melodic Tom
    12: 26,  # Jazz Guitar
    13: 87  # Bass + Lead
}
NOW_YOU_DIE = {
    1: 0,  # Grand Piano
    3: 57,  # Trombone
    5: 11,  # Vibraphone
    6: 65,  # Alto Sax
    7: 14,  # Tubular Bells
    9: 127,  # Gunshot
    10: 118  # Synth Drum
}
CIVILIZATION_OF_MAGIC = {
    1: 84,  # Charang Lead
    2: 33,  # Fingered Bass
    3: 26,  # Jazz Guitar
    7: 119,  # Reverse Cymbal
    9: 116,  # Taiko Drum
    12: 34  # Picked Bass
}
SWORDSMAN_DISTANT_STAR = {
    1: 3,  # Honky Tonk Piano
    3: 56,  # Trumpet (I guess? It's barely audible in the original. 😆)
    5: 108,  # Kalimba
    13: 37,  # Slap Bass 2
    14: 66  # Tenor Sax
}
IRIS = {
    2: 73,  # Flute
    12: 24  # Acoustic Guitar (nylon)
}
SHRINE_OF_WIND = {
    # Despite my best efforts, this still sounds as terrible as always. 😐
    1: 15,  # Dulcimer
    2: 73,  # Flute
    6: 72,  # Piccolo
    11: 35  # Fretless Bass
}
SUGGESTED_INST_NUMS: Dict[str, Dict[int, int]] = {
    "REIMU.MDT": A_SACRED_LOT,
    "ST0.MDT": ETERNAL_SHRINE_MAIDEN,
    "ST6.MDT": ETERNAL_SHRINE_MAIDEN,
    "POSITIVE.MDT": POSITIVE_AND_NEGATIVE,
    "ST1.MDT": HIGHLY_RESPONSIVE_PRAYERS,
    "ST2.MDT": STRANGE_EASTERN_DISCOURSE,
    "LEGEND.MDT": ANGELS_LEGEND,
    "ST3.MDT": ORIENTAL_MAGICIAN,
    "ST4.MDT": BLADE_OF_BANISHMENT,
    "KAMI2.MDT": MAGIC_MIRROR,
    "KAMI.MDT": MAGIC_MIRROR,
    "ST5.MDT": LEGEND_OF_KAGE,
    "TENSI.MDT": NOW_YOU_DIE,
    "SHUGEN.MDT": CIVILIZATION_OF_MAGIC,
    "SYUGEN.MDT": CIVILIZATION_OF_MAGIC,
    "ALICE.MDT": SWORDSMAN_DISTANT_STAR,
    "IRIS.MDT": IRIS,
    "ZIPANGU.MDT": SHRINE_OF_WIND,
    "ST7.MDT": SHRINE_OF_WIND,
}

SUGGESTED_SSG_NUMS: Dict[str, Dict[int, int]] = {
    "ST0.MDT": {
        2: 35  # Fretless Bass
    },
    "POSITIVE.MDT": {
        2: 80  # Square Lead
    },
    "ST1.MDT": {
        2: 4  # Electric Piano 1
    },
    "ST2.MDT": {
        0: 2,  # Electric Grand Piano
        1: 4,  # Electric Piano 1
        129: 127,  # N2@1, Gunshot
        130: 119,  # N2@2, Reverse Cymbal
    },
    "ST3.MDT": {
        1: 4,  # Electric Piano 1
        2: 4  # Electric Piano 1
    },
    "ST4.MDT": {
        1: 4,  # Electric Piano 1
        128: 126  # Applause
    },
    "KAMI.MDT": {
        1: 4,  # Electric Piano 1
        2: 67,  # Baritone Sax
        257: 126  # Applause
    },
    "KAMI2.MDT": {
        1: 4,  # Electric Piano 1
        2: 67,  # Baritone Sax
        128: 115,  # N2@0, Wood Block
        257: 126  # N3@1, Applause
    },
    "ST5.MDT": {
        1: 4,  # Electric Piano 1
        2: 40  # Violin
    },
    "TENSI.MDT": {
        2: 48  # String Ensemble 1s
    },
    "SHUGEN.MDT": {
        2: 19  # Church Organ
    },
    "ALICE.MDT": {
        2: 80  # Square Lead
    },
    "IRIS.MDT": {
        2: 72  # Piccolo
    },
    "ZIPANGU.MDT": {
        2: 43  # Contrabass
    }
}
SUGGESTED_SSG_NUMS["ST6.MDT"] = SUGGESTED_SSG_NUMS["ST0.MDT"]
SUGGESTED_SSG_NUMS["ST7.MDT"] = SUGGESTED_SSG_NUMS["ZIPANGU.MDT"]
SUGGESTED_SSG_NUMS["SYUGEN.MDT"] = SUGGESTED_SSG_NUMS["SHUGEN.MDT"]

# Included with the download (and source code) is a file named
# "approximations.opm" - containing approximations of the SSG envelopes used
# in HRtP in a format readable by the VOPM synth. These were made manually.
APPROXIMATIONS_MOST_FILES = {
    0: 0,
    1: 1,
    2: 2,
    3: 3,
    128: 7,
    257: 10
}
APPROXIMATION_SSG_NUMS: Dict[str, Dict[int, int]] = {
    "REIMU.MDT": APPROXIMATIONS_MOST_FILES,
    "ST0.MDT": APPROXIMATIONS_MOST_FILES,
    "ST6.MDT": APPROXIMATIONS_MOST_FILES,
    "POSITIVE.MDT": APPROXIMATIONS_MOST_FILES,
    "ST1.MDT": APPROXIMATIONS_MOST_FILES,
    "ST2.MDT": {
        0: 4,
        1: 5,
        2: 6,
        128: 8,
        129: 9
    },
    "LEGEND.MDT": APPROXIMATIONS_MOST_FILES,
    "ST3.MDT": APPROXIMATIONS_MOST_FILES,
    "ST4.MDT": APPROXIMATIONS_MOST_FILES,
    "KAMI2.MDT": {
        **APPROXIMATIONS_MOST_FILES,
        128: 11
    },
    "KAMI.MDT": APPROXIMATIONS_MOST_FILES,
    "ST5.MDT": APPROXIMATIONS_MOST_FILES,
    "TENSI.MDT": APPROXIMATIONS_MOST_FILES,
    "SHUGEN.MDT": APPROXIMATIONS_MOST_FILES,
    "SYUGEN.MDT": APPROXIMATIONS_MOST_FILES,
    "ALICE.MDT": APPROXIMATIONS_MOST_FILES,
    "IRIS.MDT": APPROXIMATIONS_MOST_FILES,
    "ZIPANGU.MDT": APPROXIMATIONS_MOST_FILES,
    "ST7.MDT": APPROXIMATIONS_MOST_FILES
}

# For use with the "in" keyword later
NOTE_STARTS = "<>abcdefg"
NOTE_NAME_CHARS = "abcdefg+"
LOOP_STARTS = {"|:", "[:", "["}
LOOP_SKIPS = {":", "|"}
LOOP_ENDS = {":|", ":]", "]"}
LFO_COMMANDS = {"S", "SA", "SP", "SH"}


# Helper classes
class NoteEvent:
    def __init__(
        self,
        channel: int,
        pitch: int,
        time: float,
        duration: float,
        velocity: int
    ):
        self.channel = channel
        self.pitch = pitch
        self.time = time
        self.duration = duration
        self.velocity = velocity

    def extend(self, duration: float):
        '''
        Increases the length of this NoteEvent by `duration`.
        '''
        self.duration += duration

    def write(self, midi_file: MIDIFile):
        '''
        Writes this NoteEvent to the specified MIDIFile.

        :param midi_file: The MIDIFile in question.
        '''
        midi_file.addNote(
            0,
            self.channel,
            self.pitch,
            self.time,
            self.duration,
            self.velocity
        )


class PercussionEvent:
    def __init__(
        self,
        time: float,
        duration: float,
        samples: int,
        velocities: List[int],
    ):
        self.time = time
        self.duration = duration
        self.samples = samples
        self.bass_v = velocities[0]
        self.snare_v = velocities[1]
        self.cymbal_v = velocities[2]
        self.hat_v = velocities[3]
        self.tom_v = velocities[4]
        self.rim_v = velocities[5]

    def extend(self, duration: float):
        '''
        Increases the length of this PercussionEvent by `duration`.
        '''
        self.duration += duration

    def write(self, midi_file: MIDIFile):
        '''
        Writes this PercussionEvent to the specified MIDIFile.

        :param midi_file: The MIDIFile in question.
        '''
        a: List[int] = [0, 9]  # Track and channel - deconstructed later
        b: List[float] = [self.time, self.duration]  # Time and duration - same
        if self.samples & 1:
            # Bass drum
            midi_file.addNote(*a, 36, *b, self.bass_v)  # C2
        if self.samples & 2:
            # Snare drum
            midi_file.addNote(*a, 38, *b, self.snare_v)  # D2
        if self.samples & 4:
            # Top cymbal
            midi_file.addNote(*a, 46, *b, self.cymbal_v)  # A#2 (Bb2)
        if self.samples & 8:
            # Hi-hat
            midi_file.addNote(*a, 42, *b, self.hat_v)  # F#2 (Gb2)
        if self.samples & 16:
            # Tom
            midi_file.addNote(*a, 48, *b, self.tom_v)  # C3
        if self.samples & 32:
            # Rim shot
            midi_file.addNote(*a, 37, *b, self.rim_v)  # C#2 (Db2)


# Helper functions
def parse_name(note_name: str, octave: int, transpose: int) -> int:
    return NOTE_NAMES.index(note_name) + ((octave + 1) * 12) + transpose


def parse_length(note_length: str, double=False) -> float:
    result = 0
    if note_length[0] == "%":
        # Clock cycles
        result = (int(note_length[1:]) / 192) * 4
    else:
        # Fraction of whole note (4 quarter notes)
        dot_mult = 1.0
        if note_length[-1] == ".":
            dot_mult = 1.5
            note_length = note_length[:-1]
        result = (4 / int(note_length)) * dot_mult
    return result * 2 if double else result


def v_map(value: int, high1: int, high2: int) -> int:
    return floor(value * (high2 / high1))


# Magic
# (jk)
def parse_channel_or_macro(
    ch: Channel,
    midi_ch: int,
    midi: MIDIFile,
    macro_list: List[Macro],
    inst_map: Dict[str, Dict[int, int]],
    portamento_rate: int,
    cut_time: bool,
    controls={}
) -> (float, int):
    RHYTHM = not not ch.id & 0x10
    SSG = not not ch.id & 0x40
    FM = not not ch.id & 0x80
    USING_SUGGESTION = (
        inst_map in SUGGESTED_INST_NUMS.values()
        or inst_map in SUGGESTED_SSG_NUMS.values()
        or inst_map in APPROXIMATION_SSG_NUMS.values()
    )
    if not FM and not SSG and not RHYTHM:
        # Don't process ADPCM channels
        return controls.get("time", 0)

    # Control variables
    time: float = controls.get("time", 0)
    articulation: float = controls.get("articulation", 1.0)  # "Q" in MML
    octave = 0
    transpose: int = controls.get("transpose", 0)
    velocity: int = controls.get("velocity", 127)
    rhythm_velocities: List[int] = controls.get("rhythm_velocities", [127] * 6)
    rhythm_samples: int = controls.get("rhythm_samples", 63)
    # 0: No output, 1: Tone, 2: Noise, 3: Tone + Noise
    ssg_noise_mix: int = controls.get("ssg_noise_mix", 1)
    pan_nonzero: bool = controls.get("pan_nonzero", True)
    tie: bool = controls.get("tie", False)
    note_list: List[Union[NoteEvent, PercussionEvent]] = []
    loop_stack = []  # Number of times to repeat
    return_stack = []  # Index to return to when repeating
    skip_stack = []  # Index to skip to on last repeat
    octave_stack = []  # Keeps track of octave numbers when looping

    # Helper function (defined locally because I'm lazy)
    def parse_note(note: str) -> (int, float):
        nonlocal octave, transpose
        split_index = 0
        while note[split_index] in NOTE_NAME_CHARS:
            split_index += 1
        pitch = parse_name(note[:split_index], octave, transpose)
        length = parse_length(
            note[split_index:],
            cut_time and isinstance(ch, Macro)
        )
        return (pitch, length)

    # Looping requires manipulation of indicies, so for once, this is okay
    i = 0
    while i < len(ch.events):
        event: list = ch.events[i]
        command = event[0]

        # For the sake of consistency, the conditions are in byte order, with
        # added grouping for clarity. This isn't the most efficient way of
        # parsing events, but the effect on runtime performance should be
        # fairly minimal. Readability is probably more important in this case.
        if command[0] in NOTE_STARTS:
            # Note or RHYTHM hit, and possibly octave up/down
            if command[0] == "<":
                octave -= 1
                command = command[1:]
            elif command[0] == ">":
                octave += 1
                command = command[1:]

            pitch, length = parse_note(command)
            if not (ssg_noise_mix and pan_nonzero):
                time += length
                tie = False
                i += 1
                continue

            duration = length * articulation
            if tie:
                note_list[-1].extend(duration)
                tie = False
            elif RHYTHM:
                note_list.append(PercussionEvent(
                    time=time,
                    duration=duration,
                    samples=rhythm_samples,
                    velocities=rhythm_velocities
                ))
            else:
                note_list.append(NoteEvent(
                    channel=midi_ch,
                    pitch=pitch,
                    time=time,
                    duration=duration,
                    velocity=velocity
                ))
            time += length
        elif command == "O":
            # Octave setting
            octave = event[1]
            # For reasons I don't fully understand, SSG plays one octave higher
            # than specified in MML. Possibly related to the OC compiler flag?
            if SSG:
                octave += 1
        # "L" (default note length) command is not output by the decompiler
        elif command[0] == "r":
            # Rest
            length = parse_length(
                command[1:],
                cut_time and isinstance(ch, Macro)
            )
            time += length
            tie = False
        elif command == "&":
            # Tie
            tie = True
        elif command in LOOP_STARTS:
            # Loop start
            loop_stack.append(event[1] - 1)
            return_stack.append(i + 1)
            skip_stack.append(-1)
            octave_stack.append(octave)
        elif command in LOOP_SKIPS:
            # Skip to end of loop on last iteration
            if loop_stack[-1] == 0 and skip_stack[-1] >= 0:
                i = skip_stack[-1]
                continue
        elif command in LOOP_ENDS:
            # Loop end
            if loop_stack[-1] == 0:
                # Break out of loop
                loop_stack.pop()
                return_stack.pop()
                skip_stack.pop()
                octave_stack.pop()
            else:
                # Loop again
                loop_stack[-1] -= 1
                skip_stack[-1] = i  # Put current index in skip
                i = return_stack[-1]  # Go back to first event of loop
                octave = octave_stack[-1]
                continue
        elif command == "/":
            # Force note-off
            # Using CC 120 instead of 123 because VOPM doesn't respond to 123
            midi.addControllerEvent(
                track=0,
                channel=midi_ch,
                time=time,
                controller_number=120,  # All Sound Off
                parameter=0
            )
        elif command == "^":
            # Detune
            # Detune in MDRV2 is signed, whereas MIDI just has "detune amount."
            # So I use the absolute value of the detune as the "amount."
            # This MIGHT sound okay? It won't work in VOPM, though.
            midi.addControllerEvent(
                track=0,
                channel=midi_ch,
                time=time,
                controller_number=94,
                parameter=max(abs(event[1]), 127)
            )
        elif command == "@^":
            # Transpose
            transpose = event[1]
        elif command in LFO_COMMANDS:
            # LFO settings
            LFO_speed = 0
            LFO_pitch_depth = 0
            LFO_amplitude_depth = 0
            LFO_delay = 0

            if command == "SH":
                # FM hardware LFO settings
                # Params: Speed 0-7, Sync ON/OFF, PMS 0-7, AMS 0-3
                LFO_speed = v_map(event[1], 7, 127)
                # Skip Sync - I don't think it can be done in MIDI
                LFO_pitch_depth = v_map(event[3], 7, 127)
                LFO_amplitude_depth = v_map(event[4], 3, 127)
                LFO_delay = 0  # I can only assume
            elif command == "S":
                # Pitch LFO settings, triangle
                # Params: Speed, Depth, Proportion, Delay
                LFO_speed = floor(event[1] / 2)
                LFO_pitch_depth = floor(event[2] / 2)
                LFO_amplitude_depth = 0
                # Skip proportion, because I have no idea what it is
                LFO_delay = floor(event[4] / 2)
            else:
                # Pitch/Amplitude LFO settings, any waveform
                # Params: Speed, Waveform, Depth, Proportion, Delay
                LFO_speed = floor(event[1] / 2)
                # Skip waveform - I don't think it can be done in MIDI
                if command == "SA":
                    LFO_pitch_depth = 0
                    LFO_amplitude_depth = floor(event[3] / 2)
                else:
                    LFO_pitch_depth = floor(event[3] / 2)
                    LFO_amplitude_depth = 0
                # Skip proportion
                LFO_delay = floor(event[5] / 2)

            # Set control changes
            midi.addControllerEvent(
                track=0,
                channel=midi_ch,
                time=time,
                controller_number=3,  # LFO rate (MSB)
                parameter=LFO_speed
            )
            midi.addControllerEvent(
                track=0,
                channel=midi_ch,
                time=time,
                controller_number=13,  # Frequency LFO depth (MSB)
                parameter=LFO_pitch_depth
            )
            midi.addControllerEvent(
                track=0,
                channel=midi_ch,
                time=time,
                controller_number=12,  # Amplitude LFO depth (MSB)
                parameter=LFO_amplitude_depth
            )
            # I'm not actually sure how best to calculate delay, so I've just
            # kind of... not? This should be pretty easy to fix in any decent
            # MIDI editor, though.
            midi.addControllerEvent(
                track=0,
                channel=midi_ch,
                time=time,
                controller_number=78,  # LFO delay
                parameter=LFO_delay
            )
        elif command == "t" or command == "@T":
            # Tempo
            # Cut time (@T) is handled (mostly) by the decompiler
            midi.addTempo(
                track=0,
                time=time,
                tempo=event[1]
            )
        elif command == "Q":
            # Articulation
            articulation = 0.125 * event[1]
            if articulation == 0:
                # Technically, this should disable note-offs entirely, but I
                # dare not try to implement that.
                articulation = 1
        elif command == "N":
            # SSG noise mix
            ssg_noise_mix = event[1]
        elif command == "@":
            # FM instrument change,
            # SSG envelope change,
            # or RHYTHM sample selection
            if FM:
                midi.addProgramChange(
                    tracknum=0,
                    channel=midi_ch,
                    time=time,
                    program=inst_map.get(event[1], 0)
                )
            elif SSG:
                offset = 0
                if USING_SUGGESTION:
                    offset = (ssg_noise_mix - 1) * 128
                midi.addProgramChange(
                    tracknum=0,
                    channel=midi_ch,
                    time=time,
                    program=inst_map.get(offset + event[1], 0)
                )
            elif RHYTHM:
                rhythm_samples = event[1]
        elif command == "V" or command == "@V":
            # Volume change (absolute)
            if FM:
                if command == "@V":
                    velocity = event[1]
                else:
                    velocity = v_map(event[1], 15, 127)
            elif SSG:
                velocity = v_map(event[1], 15, 127)
            elif RHYTHM:
                if command == "@V":
                    # When I first wrote this script, I put a == here instead
                    # of =. Gotcha! 😑
                    rhythm_velocities[event[1]] = v_map(event[2], 31, 127)
                else:
                    master = event[1] / 63
                    # When I first wrote this script, I used i here instead of
                    # j. Which proceeded to break everything, because variables
                    # in Python aren't block-scoped. Gotcha twice! 😑😑
                    for j in range(6):
                        rhythm_velocities[j] = v_map(
                            event[j + 2] * master,
                            31,
                            127
                        )
        elif command == "@V+" or command == "@V-":
            # Volume change (relative)
            volume = v_map(event[1], 15, 127) if SSG else event[1]
            velocity += -volume if (command == "@V-") else volume
        # "Y" (register move/copy) command is specific to sound chips
        elif command == "W":
            # FM LFO delay, or SSG noise frequency
            if FM:
                midi.addControllerEvent(
                    track=0,
                    channel=midi_ch,
                    time=time,
                    controller_number=78,  # LFO delay
                    parameter=floor(event[1] / 2)
                )
            elif SSG:
                # I have no idea how to implement noise frequency
                pass
        # "_" (fade in/out) command is probably better done in a DAW
        elif command == "P":
            # Pan
            if RHYTHM:
                # I'm pretty sure you can't pan individual drum sounds
                # using MIDI CCs. I might be wrong, though.
                if event[2] == 0:
                    # Pan 0 is no output, so disable the corresponding sample
                    if rhythm_samples & (1 << event[1]):
                        rhythm_samples -= (1 << event[1])
            else:
                value = 0 if (event[1] == 1) else (
                    127 if (event[1] == 2) else 64
                )
                midi.addControllerEvent(
                    track=0,
                    channel=midi_ch,
                    time=time,
                    controller_number=10,  # Pan
                    parameter=value
                )
                pan_nonzero = event[1] != 0
        elif command[0] == "(":
            # Portamento
            # Entire event is a string. Example:
            # "(ab,cd)e"
            # a = starting octave, b = starting note within octave
            # c = ending octave, d = ending note within octave
            # e = duration

            # Get parameters
            comma_index = command.index(",")
            close_index = command.index(")")
            # Note: Portamentos in MDRV2 are NOT affected by articulation.
            length = parse_length(
                command[close_index + 1:],
                cut_time and isinstance(ch, Macro)
            )

            if not (ssg_noise_mix and pan_nonzero):
                time += length
                tie = False
                i += 1
                continue

            start_note = parse_name(
                note_name=command[2: comma_index],
                octave=int(command[1]),
                transpose=transpose
            )
            end_note = parse_name(
                note_name=command[comma_index + 2: close_index],
                octave=int(command[comma_index + 1]),
                transpose=transpose
            )

            # Turn portamento on
            midi.addControllerEvent(
                track=0,
                channel=midi_ch,
                time=time,
                controller_number=65,  # Portamento ON/OFF
                parameter=127  # ON
            )
            # The problem with portamentos is that there isn't a consistent way
            # to translate their duration to the MIDI CC for portamento rate,
            # which may vary between synths. In my own testing (with CoolSoft
            # VirtualMIDISynth), a rate of 55 sounded pretty good, so I'm using
            # that as the default value.
            midi.addControllerEvent(
                track=0,
                channel=midi_ch,
                time=time,
                controller_number=5,
                parameter=portamento_rate
            )

            # Send notes
            if tie:
                # NOTE: Portamentos in MDRV2 ARE affected by ties.
                note_list[-1].extend(length - MIDI_EPSILON)
                tie = False
            else:
                note_list.append(NoteEvent(
                    channel=midi_ch,
                    pitch=start_note,
                    time=time,
                    duration=length - MIDI_EPSILON,
                    velocity=velocity
                ))
            note_list.append(NoteEvent(
                channel=midi_ch,
                pitch=end_note,
                time=time + MIDI_EPSILON,
                duration=length - MIDI_EPSILON,
                velocity=velocity
            ))

            # Increment time, then turn portamento off
            time += length
            midi.addControllerEvent(
                track=0,
                channel=midi_ch,
                time=time,
                controller_number=65,  # Portamento ON/OFF
                parameter=0  # OFF
            )
        # "\" (infinite loop) command is probably better done in a DAW
        # "Z" (sync-work value entry) is probably not relevant to MIDI
        elif command == "U":
            # Macro playback
            # This is why I put the code for parsing tracks inside a function:
            time, velocity = parse_channel_or_macro(
                ch=macro_list[event[1]],
                midi_ch=midi_ch,
                midi=midi,
                macro_list=macro_list,
                inst_map=inst_map,
                portamento_rate=portamento_rate,
                cut_time=cut_time,
                controls={
                    "time": time,
                    "articulation": articulation,
                    "transpose": transpose,
                    "velocity": velocity,
                    "rhythm_velocities": rhythm_velocities,
                    "ssg_noise_mix": ssg_noise_mix,
                    "pan_nonzero": pan_nonzero,
                    "tie": tie
                }
            )
            # Ain't it beautiful? 😁
            # Of course, if there are any macros that reference themselves
            # (directly or indirectly), I'm kind of screwed. But I'm banking on
            # the hope that MDRV2's compiler catches those. 🤞
        i += 1

    # Write events and return
    for n in note_list:
        n.write(midi)
    return (time, velocity)


# API begins here
def parse_song(
    song: Song,
    fm_inst_map={},
    ssg_inst_map={},
    portamento_rate=55,
    cut_time=False
) -> MIDIFile:
    '''
    Converts the MML events in the specified MDT `Song` to MIDI events,
    writes them to a MIDIFile instance, and returns it.
    NOTE: This function can raise BaseExceptions.

    :param song: A Song instance returned from `MDTTools.parse_mdt()`.
    :param inst_map: An optional dict with filenames as keys and more dicts as
    values. The sub-dicts have MML instrument numbers as keys and MIDI
    instrument numbers as values.
    :param cut_time: If True, all note lengths in macros will be doubled.
    '''
    if len(song.channels) == 0:
        raise BaseException("Provided Song has no channels.")
    if song.chip != 1:
        raise BaseException("Provided Song is not for OPN/OPNA.")
    if portamento_rate < 0 or portamento_rate > 127:
        raise BaseException("Portamento rate must be an int 0-127, inclusive.")

    macro_list = list(v for _, v in sorted(
        song.macros.items(), key=lambda m: m[1].macro_id
    ))

    midi = MIDIFile(
        numTracks=1,
        removeDuplicates=False,
        deinterleave=False,
        adjust_origin=False,
        file_format=1
    )

    track_end_time = 0
    melodic_channels_written = []

    channel_number = 0
    for ch in song.channels:
        if ch.id & 0x10:
            # RHYTHM channel
            parse_channel_or_macro(
                ch=ch,
                midi_ch=9,
                midi=midi,
                macro_list=macro_list,
                inst_map={},
                portamento_rate=portamento_rate,
                cut_time=cut_time
            )
        else:
            # FM/SSG/ADPCM channel
            midi.addControllerEvent(
                track=0,
                channel=channel_number,
                time=0,
                controller_number=126,  # Mono mode ON
                parameter=10  # I think 10 is correct?
                # Based on: https://www.midi.org/specifications-old/item/table-3-control-change-messages-data-bytes-2
            )
            time, _ = parse_channel_or_macro(
                ch=ch,
                midi_ch=channel_number,
                midi=midi,
                macro_list=macro_list,
                inst_map=(fm_inst_map if (ch.id & 0x80) else ssg_inst_map).get(
                    song.filename, {}
                ),
                portamento_rate=portamento_rate,
                cut_time=cut_time
            )
            track_end_time = max(time, track_end_time)
            melodic_channels_written.append(channel_number)
            channel_number += 1
            if channel_number == 9:
                channel_number += 1

    for ch in melodic_channels_written:
        midi.addControllerEvent(
            track=0,
            channel=ch,
            time=track_end_time,
            controller_number=127,  # Mono mode OFF
            parameter=0
        )

    return midi


def write_midi_file(filename: str, midi_file: MIDIFile):
    '''
    Writes the provided MIDIFile to the provided output filename.

    :param filename: A path to where the MIDI file will be written.
    :param midi_file: A MIDIFile instance returned from `parse_song()`.
    '''
    with open(filename, "wb") as f:
        midi_file.writeFile(f)
        f.close()


if __name__ == "__main__":
    if len(CMD_ARGS) < 3:
        print("Please specify an input MDT file and an output location.")
        exit()

    from mdt_decomp_rip import parse_mdt
    cut_time = len(CMD_ARGS) >= 4 and CMD_ARGS[3].lower() == "true"

    song = parse_mdt(CMD_ARGS[1], cut_time=cut_time)
    midi = parse_song(
        song=song,
        fm_inst_map=SUGGESTED_INST_NUMS,
        ssg_inst_map=SUGGESTED_SSG_NUMS,
        cut_time=cut_time
    )
    write_midi_file(CMD_ARGS[2], midi)
