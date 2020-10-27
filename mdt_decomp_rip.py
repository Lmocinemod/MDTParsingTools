# Contains functions, etc. for parsing and decompiling MDT files, as well as
# ripping and exporting the instruments stored in them. Only MDT files made for
# the YM2608 (OPNA) that do not contain ADPCM data are known to be supported.

# The decompilation parts of the script are HEAVILY based off of HertzDevil's
# "MDRV2 MDT to MML unconverter" script, which was written in Lua. As of
# September 2nd 2020, the script can be viewed/downloaded from here:
# https://gist.github.com/HertzDevil/036304c692b0f26b7a9d7cfe1126a0ac

# Some modifications to the decompilation procedure have been made to allow
# interfacing and correct inaccuracies (e.g. SSG noise mix, portamento).

# Be advised that many of the comments in this script are unprofessional in
# nature.


from io import TextIOWrapper as FILE
from math import trunc, fabs as abs, log
from functools import partial
from itertools import chain
from sys import argv as CMD_ARGS, exit
from typing import List, Dict, Union

# NOTE: This is terrible. If anyone's looking to contribute code, this would be
# a fantastic place to start. Fair warning, though: Portamento is complicated.
from portamento_map_fm import PORTAMENTO_MAP_FM
from portamento_map_ssg import PORTAMENTO_MAP_SSG


# Constants
CHANNEL_FLAGS = {
    0x10: "L",
    0x40: "I",
    0x41: "J",
    0x42: "K",
    0x80: "A",
    0x81: "B",
    0x82: "C",
    0x83: "D",
    0x84: "E",
    0x85: "F"
}

NOTE_NAMES = ["c", "c+", "d", "d+", "e", "f", "f+", "g", "g+", "a", "a+", "b"]

# Surprise! MDRV2 supports dotted notes, even though the docs don't mention it!
NOTE_LENGTHS = {
    1: "192",
    2: "96",
    3: "64",
    4: "48",
    6: "32",
    8: "24",
    9: "32.",
    12: "16",
    16: "12",
    18: "16.",
    24: "8",
    32: "6",
    36: "8.",
    48: "4",
    64: "3",
    72: "4.",
    96: "2",
    144: "2.",
    192: "1"
}

#                   AR DR SR RR SL TL KS MUL DT1 DT2 AMS-EN
OPM_PARAM_COLUMNS = [2, 2, 2, 2, 2, 3, 1,  2,  1,  1,     1]

OPM_OPERATOR_FLAGS = ["M1: ", "C1: ", "M2: ", "C2: "]

TRACK_NUMBER_MAP = {
    "INIT.MDT": "INIT",
    "REIMU.MDT": "01",
    "ST0.MDT": "02",
    "ST6.MDT": "02",
    "POSITIVE.MDT": "03",
    "ST1.MDT": "04",
    "ST2.MDT": "05",
    "LEGEND.MDT": "06",
    "ST3.MDT": "07",
    "ST4.MDT": "08",
    "KAMI.MDT": "09",
    "KAMI2.MDT": "09",
    "ST5.MDT": "10",
    "TENSI.MDT": "11",
    "SHUGEN.MDT": "12",
    "SYUGEN.MDT": "12",
    "ALICE.MDT": "13",
    "IRIS.MDT": "14",
    "ZIPANGU.MDT": "15",
    "ST7.MDT": "15"
}


# Helper functions
def mml_length(length: int, cut_time: bool) -> str:
    if cut_time:
        length *= 2
    return NOTE_LENGTHS.get(length, "%" + str(length))


def uint8(f: FILE) -> int:
    return int.from_bytes(f.read(1), "big")


def int8(f: FILE) -> int:
    u8 = uint8(f)
    return u8 - 0x100 if (u8 >= 0x80) else u8


def uint16(f: FILE) -> int:
    return uint8(f) + (uint8(f) * 0x100)


def int16(f: FILE) -> int:
    u16 = uint16(f)
    return u16 - 0x10000 if (u16 >= 0x8000) else u16


def read_params(f: FILE, n: int) -> list:
    result = [0] * n
    for i in range(0, n):
        result[i] = uint8(f)
    return result


def skip_bytes(f: FILE, n: int):
    f.seek(n, 1)


def str_join_list(seperator: str, the_list: list) -> str:
    return seperator.join(str(v) for v in the_list)


def opm_pad(param: int, index: int):
    param = str(param)
    padding = " " * (OPM_PARAM_COLUMNS[index] - len(param))
    return padding + param


def opm_join_params(params: list) -> str:
    return " ".join(opm_pad(p, i) for i, p in enumerate(params))


def write_opm_header(f: FILE):
    '''
    Writes an OPM file header to `f`.
    `f` must be opened in `"w"` mode.
    '''
    f.write("//@:[Number] [Name...]\n")
    f.write("//LFO: LFRQ AMD PMD WF NFRQ\n")
    f.write("//CH: PAN FL ALG AMS PMS SLOT N-EN\n")
    f.write("//_#: AR DR SR RR SL TL KS MUL DT1 DT2 AMS-EN\n\n")


def write_unused_warning(f: FILE):
    '''
    Writes a warning about unused instruments to `f`.
    `f` must be opened in `"w"` mode.
    '''
    f.write("// NOTE: The instruments in this file were not used in the files they were ripped from.\n")
    f.write(
        "// They may sound very strange, or contain garbage and/or out-of-range values.\n")
    f.write("// It is very possible that importing this file might fail.\n")
    f.write("// Please use these instruments at your own discretion.\n\n")


def remove_path(file_path: str) -> str:
    '''
    Removes directory names and slashes (foward and back) from a path,
    leaving just the file's name and extension.

    :param file_path: The path to the file, including its name and extension.
    '''
    file_path = file_path.replace("\\", "/")
    if file_path[:2] == "./":
        file_path = file_path[2:]
    file_path_split = file_path.split("/")
    return file_path_split[-1]


# Classes
class Channel:
    def __init__(self, location: int, id: int):
        self.location = location
        self.id = id
        self.loop_pos = -1
        self.events: List[List[Union[str, int]]] = []

    def add_event(self, event: List[Union[str, int]]):
        self.events.append(event)


class Macro(Channel):
    def __init__(self, location: int, id: int, macro_id: int):
        super().__init__(location, id)
        self.macro_id = macro_id


class FMInstrument:
    OPERATOR_OFFSETS = [0, 2, 1, 3]

    def __init__(self, params: list):
        self.plays = False
        self.is_duplicate = False
        self.mml_names: Dict[str, List[int]] = {}
        self.number = -1
        self.params: List[List[int]] = [
            [0] * 11,
            [0] * 11,
            [0] * 11,
            [0] * 11,
            [0] * 11
        ]
        self.files_str = ""

        # Assign channel parameters
        first = self.params[0]
        first[3], first[10] = params[0] % 0x40, params[0] >> 6  # SY, NOI
        first[4] = params[1]  # SP
        first[6] = params[2]  # AMD
        first[2], first[1] = params[3] % 0x08, params[3] >> 3  # WF, OM
        first[0], first[9] = params[4] % 0x40, params[4] >> 6  # AF, PAN
        first[8], first[7] = params[5] % 0x10, params[5] >> 4  # AMS, PMS
        # For reasons I can neither explain nor comprehend, MDRV2's compiler
        # SOMETIMES compiles PMD (the parameter, not the driver) to a value 128
        # higher than actually specified. BUT NOT ALWAYS. 😖
        # In particular, it seems to happen on FM instruments where all
        # parameters are zeros (that is, "emtpy" instruments). So, I can just
        # not write those instruments to the file, right? WRONG!!! Why? Because
        # the compiler fills the parameters with garbage values if you do! 😈
        # I don't know why. I don't want to know why. I shouldn't have had to
        # spend 4 days trying to figure out why. But none of these "empty"
        # instruments are actually USED in the MML anyway, so I can't be
        # brought to care anymore. 💀
        first[5] = params[30] % 0x80  # PMD

        # Assign operator parameters, in OPNA register order (1, 3, 2, 4)
        for i, j in enumerate(FMInstrument.OPERATOR_OFFSETS):
            op = self.params[i + 1]
            op[7] = params[j + 6] % 0x10  # ML
            op[8] = (
                0x140 - params[j + 6] if (
                    params[j + 6] >= 0x80
                ) else params[j + 6]
            ) >> 4  # D1
            op[5] = params[j + 10]  # OL
            op[0], op[6] = params[j + 14] % 0x40, params[j + 14] >> 6  # AR, KS
            op[1], op[10] = params[j + 18] % 0x80, params[j + 18] >> 7  # DR, AME
            op[2], op[9] = params[j + 22] % 0x40, params[j + 22] >> 6  # SR, D2
            op[3], op[4], = params[j + 26] % 0x10, params[j + 26] >> 4  # RR, SL

        # Also, I'm not sure what data is stored in byte 31, but it re-compiles
        # to a COMPLETELY different value from the original. Grrr! 💢
        # Testing with the Hoot emulator seems to indicate that none of the
        # OPNA registers are actually affected by that change, though.
        # ...Which implies that byte 31 is just straight-up useless?? 😂
        # I suspect it might be filled with the same garbage as the "empty"
        # instruments, but I can't be 100% sure about that.

    def add_file(self, filename: str, numbers: List[int]):
        self.mml_names.setdefault(filename, [])
        for num in numbers:
            if num not in self.mml_names[filename]:
                self.mml_names[filename].append(num)

    def gen_files_str(self) -> str:
        self.files_str = ",".join(sorted(
            TRACK_NUMBER_MAP.get(k, k) for k in self.mml_names
        ))
        return self.files_str

    def md2_str(self, number: int) -> str:
        n = str(number)
        spaces = " "
        spaces *= 4 + len(n)  # Mugenri ~ Evanescent Existence
        return f"@{n} = " + f",\r\n{spaces}".join(
            str_join_list(",", v) for v in self.params
        ) + ",\r\n"

    def opm_str(self, number: int) -> str:
        first = self.params[0]
        LFO = [0] * 5
        CH = [7] * 7

        CH[2], CH[1] = first[0] % 0x08, first[0] >> 3  # ALG, FL
        CH[5] = first[1] << 3  # SLOT
        LFO[3] = first[2]  # WF
        # Skip SY, since it doesn't have a direct equivalent in OPM
        LFO[0] = first[4]  # LFRQ
        LFO[2] = first[5]  # PMD
        LFO[1] = first[6]  # AMD
        CH[4] = first[7]  # PMS
        CH[3] = first[8]  # AMS
        CH[0] = 64 if (first[9] == 3) else (192 if (first[9] == 2) else (
            128 if (first[9] == 1) else 0
        ))  # PAN
        LFO[4] = first[10]  # NFRQ
        # CH[6] = 0  # NE

        if not self.files_str:
            self.gen_files_str()

        return "@:{} @{} {}\nLFO: {}\nCH: {}\n{}\n\n".format(
            str(number),
            str(number),
            self.files_str,
            str_join_list(" ", LFO),
            str_join_list(" ", CH),
            "\n".join(
                v + opm_join_params(self.params[i + 1]) for i, v in enumerate(
                    OPM_OPERATOR_FLAGS
                )
            )
        )


class SSGEnvelope:
    def __init__(self, params: List[int]):
        self.params = params

    def md2_str(self, number: int) -> str:
        return f"P{str(number)} = {str_join_list(', ', self.params)}\r\n"


class Song:
    def __init__(self, f: FILE, filename: str):
        self.title = ""
        self.macros: Dict[int, Macro] = {}
        self.fm: List[FMInstrument] = []
        self.ssg: List[SSGEnvelope] = []
        self.filename = filename

        # Perform initial setup
        channel_count = uint16(f)
        self.chip = uint16(f)
        self.channels: List[Channel] = []
        for i in range(channel_count):
            i  # To get Python to shut up about unused variables
            c = Channel(location=uint16(f), id=uint16(f))
            if c.id != 0:
                self.channels.append(c)

    def register_macro(self, f: FILE, channel_id: int) -> int:
        macro_loc = uint16(f)
        return self.macros.setdefault(
            macro_loc,
            Macro(location=macro_loc, id=channel_id, macro_id=len(self.macros))
        ).macro_id

    def write_md2_file(self, filename: str):
        with open(
            filename,
            "w",
            encoding="SHIFT-JIS",
            errors="ignore",
            newline=""
        ) as f:
            # Write the title
            f.write(f"T={self.title}$\r\n\r\n")

            # Write global flags
            f.write("A\t{} X1 OC0\r\n".format(
                "OPM" if self.chip == 0 else (
                    "OPN" if self.chip == 1 else "OPLL"
                )
            ))

            # Write all channels, then all macros
            for i, v in chain(
                enumerate(self.channels),
                enumerate(list(v for _, v in sorted(
                    self.macros.items(), key=lambda m: m[1].macro_id
                )))
            ):
                # Write channel/macro header
                if isinstance(v, Macro):
                    f.write("#{}\t${} ".format(
                        str(v.macro_id),
                        "F" if (v.id & 0x80) else (
                            "S" if (v.id & 0x40) else "R"
                        )
                    ))
                else:
                    f.write(CHANNEL_FLAGS[v.id] + "\t")

                # Write all events
                for event in v.events:
                    f.write("{}{} ".format(
                        event[0],
                        str_join_list(",", event[1:])
                    ))

                # Add a newline at the end of the channel/macro
                f.write("\r\n")

                # Seperate channels from macros with an empty line
                if i == len(self.channels) - 1 and len(self.macros) > 0:
                    f.write("\r\n")

            f.write("\r\n\r\n")

            # Write all FM instrument definitions
            for i, v in enumerate(self.fm):
                f.write(v.md2_str(i))
            f.write("\r\n")

            # Write all SSG envelope definitions
            for i, v in enumerate(self.ssg):
                f.write(v.md2_str(i))

            # Write one extra newline, then a substitute character (0x1A)
            # Apparently a substitute character indicates end-of-file?
            f.write("\r\n\x1A")
            # Strangely, the Lua script outputs "x1A" instead of the substitute
            # character. I'm using a portable version of Lua, though, so IDK?


# API functions
def parse_mdt(filename: str, cut_time=False) -> Song:
    '''
    Opens and reads an MDT file, and returns it as a Song instance.
    NOTE: This function can raise BaseExceptions.

    :param filename: A path to the MDT file.
    '''
    f = open(filename, "rb")  # Not using "with" to keep indentation down
    filename = remove_path(filename)

    # First 2 bytes are always(?) 02,03
    # I wondered at first if they were X and OC, but changing X and OC doesn't
    # change these bytes. 🤔
    skip_bytes(f, 2)

    song = Song(f, filename)
    if song.chip > 2:
        f.close()
        raise BaseException("Only OPM, OPN, and OPLL chips are supported.")

    # File locations
    fm_def_loc = uint16(f)
    ssg_def_loc = uint16(f)
    title_loc = uint16(f)

    # Control variables
    octave = 0
    oct_stack: List[int] = []
    fm_usage: Dict[int, bool] = {}
    ssg_usage: Dict[int, bool] = {}
    noise_mix = 1

    # One helper function, because I'm too lazy to make it global
    def note_str(char: int) -> str:
        nonlocal octave
        result = NOTE_NAMES[char % 0x10]
        shift = (char >> 4) - octave
        octave += shift
        if abs(shift) >= 2:
            # Separated into its own event for easier parsing in MDTtoMIDI.py
            ch.add_event(["O", octave])
        else:
            oct_mark = ">" if (shift > 0) else "<" if (shift < 0) else ""
            result = oct_mark + result
        return result

    # Parse the title
    f.seek(title_loc)
    DOLLAR_SIGN = int.from_bytes(b"$", "big")
    title_bytes = bytes(b for b in iter(partial(uint8, f), DOLLAR_SIGN))
    song.title = title_bytes.decode("SHIFT-JIS", errors="replace")

    # Parse each channel, then each macro
    macro_keys: List[int]
    macro_keys_generated = False
    i = 0
    while i < (len(song.channels) + len(song.macros)):
        # Yes, this is terrible and un-Pythonic. But the alternatives are to
        # either maintain a 3rd list consisting of channels AND macros, or to
        # define a really stupidly long local function. (I can't use an
        # iterator, because the macros list is being mutated.)
        ch = None
        if i >= len(song.channels):
            if not macro_keys_generated:
                macro_keys: List[int] = list(sorted(song.macros.keys()))
                macro_keys_generated = True
            ch = song.macros[macro_keys[i - len(song.channels)]]
        else:
            ch = song.channels[i]

        octave = 0xFF  # Guarantees that first note sets octave
        loop_pos_file = -1
        current_inst = 255

        # Find the channel's infinite loop point, if there is one
        f.seek(ch.location)
        char = 0x00
        while char != 0xFF:
            char = uint8(f)

            # Exit if we find it
            if char == 0xF3:
                loop_pos_file = int16(f) + f.tell()  # Order matters
                break
            # Otherwise, keep advancing based on command. If we don't, the
            # loop might exit early. -__- (Yes, this caused me some headaches.)
            elif (
                char <= 0x7F
                or char == 0x90
                or char == 0xE0
                or char == 0xE4
                or char == 0xE6
                or char == 0xE7
                or char == 0xE9
                or char == 0xEA
                or char == 0xEB
                or char == 0xEC and not ch.id & 0x10
                or char == 0xEF
                or char == 0xF0
                or char == 0xF1 and not ch.id & 0x10
                or char == 0xF4
                or char == 0xF5
                or char == 0xF8
            ):
                skip_bytes(f, 1)
            elif (
                char == 0xEE
                or char == 0xF1 and ch.id & 0x10
                or char == 0xF3
                or char == 0xF9
                or char == 0xFA
            ):
                skip_bytes(f, 2)
            elif (
                char == 0xF6
                or char == 0xF7
            ):
                skip_bytes(f, 3)
            elif (
                char == 0xE8
                or char == 0xED
                or char == 0xF2
                or char == 0xFB
                or char == 0xFC
                or char == 0xFD
            ):
                skip_bytes(f, 4)
            elif char == 0xEC and ch.id & 0x10:
                first = uint8(f)
                skip_bytes(f, 1 if (first & 0x80) else 6)

        # Parse all the events in the channel
        f.seek(ch.location)
        char = 0x00
        while char != 0xFF:
            char = uint8(f)

            # Add infinite loop event if need be
            if f.tell() == loop_pos_file:
                ch.add_event(["\\"])

            # Parse the current event
            if char < 0x80:
                # Note
                # NOTE (ha): Cut time CANNOT apply to macros, since the
                # compiler isn't smart enough to figure out whether or not cut
                # time applies to a macro during playback (which may require
                # compiling two of the same macro). Instead, the compiler just
                # assumes that cut time is NEVER used when it compiles macros.
                ch.add_event([note_str(char) + mml_length(
                    uint8(f), cut_time and not isinstance(ch, Macro)
                )])
                if not ch.id & 0x10:
                    (ssg_usage if (ch.id & 0x40) else fm_usage)[
                        current_inst
                    ] = True
            # 0x80...0x8F are unused
            # TODO: Unless they're octave 8 notes for SSG with OC set to 1?
            elif char == 0x90:
                # Rest
                ch.add_event(["r" + mml_length(
                    uint8(f), cut_time and not isinstance(ch, Macro)
                )])
            elif char == 0x91:
                # Tie
                ch.add_event(["&"])
            # 0x92...0xDF are unused
            elif char == 0xE0:
                # Loop start (pipe-colon)
                oct_stack.append(-1)
                ch.add_event(["|:", uint8(f)])
            elif char == 0xE1:
                # Skip to end of loop on last iteration (pipe-colon)
                if oct_stack[-1] == -1:
                    oct_stack[-1] = octave
                ch.add_event([":"])
            elif char == 0xE2:
                # Loop end (pipe-colon)
                octave = oct_stack[-1] if (oct_stack[-1] >= 0) else octave
                oct_stack.pop()
                ch.add_event([":|"])
            elif char == 0xE3:
                # Force note-off
                ch.add_event(["/"])
            elif char == 0xE4:
                # Loop start (bracket)
                # These loops can't be exited early, so the octave stack isn't
                # necessary.
                ch.add_event(["[", uint8(f)])
            elif char == 0xE5:
                # Loop end (bracket)
                ch.add_event(["]"])
            elif char == 0xE6:
                # Detune
                ch.add_event(["^", int8(f)])
            elif char == 0xE7:
                # Transpose
                ch.add_event(["@^", int8(f)])
            elif char == 0xE8:
                # Amplitude LFO settings (triangle)
                a, b, c, d = read_params(f, 4)
                ch.add_event(["SA", a, 0, b, c, d])
            elif char == 0xE9:
                # Tempo
                tempo = uint8(f)
                # The @T (tempo + cut time) command seems to be a compiler
                # flag, prompting it to double tempo and note lengths.
                if cut_time:
                    ch.add_event(["@T", tempo * 2])
                else:
                    ch.add_event(["t", tempo])
            elif char == 0xEA:
                # Articulation (...is what I'm calling it)
                ch.add_event(["Q", uint8(f)])
            elif char == 0xEB:
                # FM instrument change,
                # SSG noise mix and envelope change,
                # or RHYTHM sample selection
                inst_num = uint8(f)
                if ch.id & 0x40:
                    # SSG noise mix and envelope
                    # MDRV2 appears to combine the tone/noise mix (2 bits) with
                    # the envelope number (6 bits). The Lua script assumes that
                    # N is always set to 1, thus producing negative envelope
                    # numbers for anything else. Whoops! 😜
                    # This actually took me a REALLY long time to fix, and I
                    # only figured it out thanks to the documentation, which
                    # states that the N command "[takes] effect at the point
                    # where the envelope settings are changed."
                    tone = not inst_num & 0x40
                    noise = not inst_num & 0x80
                    inst_num %= 0x40
                    # Booleans in Python are also integers:
                    new_noise_mix = noise * 2 + tone
                    if new_noise_mix != noise_mix:
                        noise_mix = new_noise_mix
                        ch.add_event(["N", noise_mix])
                ch.add_event(["@", inst_num])
                if not ch.id & 0x10:
                    current_inst = inst_num
                    (ssg_usage if (ch.id & 0x40) else fm_usage).setdefault(
                        inst_num,
                        False
                    )
            elif char == 0xEC:
                # Volume
                if ch.id & 0x10:
                    # RHYTHM
                    first = uint8(f)
                    if first & 0x80:
                        # One RHYTHM sample
                        ch.add_event(["@V", first % 0x80, uint8(f)])
                    else:
                        # All RHYTHM samples
                        ch.add_event(["V", first, *read_params(f, 6)])
                elif ch.id & 0x40:
                    # SSG
                    # The Lua script (incorrectly) uses @V in SSG channels,
                    # so I added this elif to fix that.
                    # Hooray for translated docs! ✊
                    ch.add_event(["V", uint8(f)])
                else:
                    # FM (or ADPCM, I guess, but 🤷‍♀️)
                    ch.add_event(["@V", uint8(f)])
            elif char == 0xED:
                # Pitch LFO settings (triangle)
                ch.add_event(["S", *read_params(f, 4)])
            elif char == 0xEE:
                # Register move/copy
                # ...O...kay? Is this actually a useful feature?
                ch.add_event(["Y", *read_params(f, 2)])
            elif char == 0xEF:
                # FM LFO delay, or SSG noise frequency
                ch.add_event(["W", uint8(f)])
            elif char == 0xF0:
                # Fade in/out
                time = uint8(f)
                ch.add_event(["_", 0x80 - time if (time & 0x80) else time])
            elif char == 0xF1:
                # Pan
                # Read 2 params for RHYTHM, 1 for others
                params = read_params(f, 2 if (ch.id & 0x10) else 1)
                ch.add_event(["P", *params])
            elif char == 0xF2:
                # Portamento
                # Neither my nor HertzDevil's attempts at correctly calculating
                # portamento from the MDT parameters succeeded, so I created
                # a set of MD2 files containing every possible %1 portamento,
                # compiled them, and extracted their parameters into a dict.
                # There's DEFINITELY a better way to do this, but I've sunk WAY
                # too much time into this already. 😭
                # Portamentos in MDRV2 have 4 bytes of parameters:
                start_note = uint8(f)  # Starting note (and octave)
                duration = uint8(f)  # Duration, in clock cycles
                change = int16(f)  # I have NO IDEA.
                # Each octave up/down adds/subtracts 617 to change, and change
                # is divided by duration during compilation. Semitones vary in
                # size depending on the starting AND ENDING positions in their
                # respective octaves, but the starting octave doesn't seem to
                # matter??? IDK, dude. 😕
                portamento_map = PORTAMENTO_MAP_SSG if (
                    ch.id & 0x40
                ) else PORTAMENTO_MAP_FM
                end_note = -1
                for k, v in portamento_map[start_note].items():
                    # Find the note corresponding to the value of change
                    if trunc(k / duration) == change:  # Signed int division
                        end_note = v
                        break
                # NOTE for people who don't write Python: code in a for...else
                # block runs only if the for loop doesn't break.
                else:
                    # If there's no direct correspondance, find whatever key
                    # is closest (and greater in magnitude) to change
                    # TODO: This might not work for SSG...
                    last = 0
                    change_abs = abs(change)
                    itemiter = sorted(portamento_map[start_note].items())
                    for k, v in reversed(itemiter) if change < 0 else itemiter:
                        if (change < 0 and k > 0) or (change >= 0 and k < 0):
                            continue
                        last = k
                        if abs(k) > change_abs:
                            end_note = v
                            break
                    else:
                        end_note = portamento_map[start_note][last]
                ch.add_event(["({}{},{}{}){}".format(
                    str(start_note >> 4),
                    NOTE_NAMES[start_note % 0x10],
                    str(end_note >> 4),
                    NOTE_NAMES[end_note % 0x10],
                    mml_length(duration, cut_time and not isinstance(
                        ch, Macro
                    ))
                )])
            elif char == 0xF3:
                # Infinite loop - already handled
                skip_bytes(f, 2)
            elif char == 0xF4:
                # Volume increase
                ch.add_event(["@V+", uint8(f)])
            elif char == 0xF5:
                # Volume decrease
                ch.add_event(["@V-", uint8(f)])
            elif char == 0xF6:
                # Loop start (bracket-colon)
                ch.add_event(["[:", uint8(f)])
                # The documentation says that [::] loops can be nested, but
                # others "output smaller objects" (uncertain translation).
                # I assume, then, that these 2 bytes are a pointer.
                # The question is, what exactly are they pointing to?
                # Any why isn't the octave stack necessary here?
                skip_bytes(f, 2)
                # Fun fact: In Lua, wrapping a function call in parentheses
                # forces it to return only one value (since functions in Lua
                # can return multiple values). When I was first translating
                # dump.lua to Python, I assumed the parentheses were a no-op.
                # Gotcha! 😑
            elif char == 0xF7:
                # Loop end (bracket-colon)
                ch.add_event([":]"])
                # 2 of these bytes are probably a pointer back to the start of
                # the loop. What confuses me is the 3rd. What's it for?
                skip_bytes(f, 3)
            elif char == 0xF8:
                # Sync-work value entry
                # ...Whatever that means.
                ch.add_event(["Z", uint8(f)])
            elif char == 0xF9:
                # Skip to end of loop on last iteration (bracket-colon)
                ch.add_event(["|"])
                # I can only assume that these 2 bytes are a pointer to the end
                # of the loop.
                skip_bytes(f, 2)
            elif char == 0xFA:
                # Macro ("user-defined track") playback
                macro_num = song.register_macro(f, ch.id)
                ch.add_event(["U", macro_num])
            elif char == 0xFB:
                # Pitch LFO settings (sawtooth up/down)
                a, b, c, d = read_params(f, 4)
                ch.add_event(["SP", a, b, 0, c, d])
            elif char == 0xFC:
                # Amplitude LFO settings (sawtooth up/down)
                a, b, c, d = read_params(f, 4)
                ch.add_event(["SA", a, b, 0, c, d])
            elif char == 0xFD:
                # FM Hardware LFO settings (triangle only)
                ch.add_event(["SH", *read_params(f, 4)])
            # 0xFE is unused
            # 0xFF: End of channel/macro. Part of loop condition

        # "Whenever you're manipulating indicies directly, you're probably
        # doing it wrong." -Raymond Hettinger, Python core developer, 2013
        # (I may or may not have forgotten to increment i at one point. 😝)
        i += 1

    # Parse FM instrument definitions
    f.seek(fm_def_loc)
    while f.tell() < ssg_def_loc:
        song.fm.append(FMInstrument(read_params(f, 32)))
        n = len(song.fm) - 1
        song.fm[n].add_file(filename, [n])
        song.fm[n].plays = fm_usage.get(n, False)

    # Parse SSG envelope definitions
    end_of_file = f.seek(0, 2)
    f.seek(ssg_def_loc)
    while f.tell() < end_of_file:
        song.ssg.append(SSGEnvelope(read_params(f, 6)))

    # Close file and return
    f.close()
    return song


def process_insts_in_songs(
    song_list: List[Song]
) -> (List[FMInstrument], List[FMInstrument], Dict[str, Dict[int, int]]):
    '''
    Extracts instruments, removes duplicates, splits into used and unused,
    sorts by file occurrances, assigns new numbers, and generates an instrument
    number map, all returned as a tuple.

    :param song_list: A list of Song instances.
    '''
    # Make a master list of all instruments
    insts: List[FMInstrument] = []
    for song in song_list:
        insts.extend(song.fm)

    # Mark duplicates and merge MML names
    # If there's a way to do this that isn't O(n^2), I don't know of it.
    for i, v in enumerate(insts):
        for w in reversed(insts[:i]):
            if w.is_duplicate:
                # Don't mark duplicates of duplicates - that breaks everything!
                # (Yes, this was a bug that took me forever to fix.)
                continue
            if v.params == w.params:
                v.is_duplicate = True
                w.plays = w.plays or v.plays
                for k, x in v.mml_names.items():
                    w.add_file(k, x)
                break

    # Seperate into used and unused, skipping duplicates
    used: List[FMInstrument] = []
    unused: List[FMInstrument] = []
    for inst in insts:
        if inst.is_duplicate:
            continue
        (used if inst.plays else unused).append(inst)

    # Sort by file occurrances
    def BY_FILE_STR(v: FMInstrument): return v.gen_files_str()
    used.sort(key=BY_FILE_STR)
    unused.sort(key=BY_FILE_STR)

    # Assign new numbers
    for i, v in enumerate(used):
        v.number = i
    for i, v in enumerate(unused):
        v.number = i

    # Generate instrument number map
    inst_map: Dict[str, Dict[int, int]] = {}
    for inst in used:
        for k, v in inst.mml_names.items():
            inst_map.setdefault(k, {})
            for num in v:
                inst_map[k][num] = inst.number

    # Return everything
    return (used, unused, inst_map)


if __name__ == "__main__":
    if len(CMD_ARGS) < 3:
        print("Please specify an input MDT file and an output location.")
        exit()

    cut_time = len(CMD_ARGS) >= 4 and CMD_ARGS[3].lower() == "true"
    song = parse_mdt(CMD_ARGS[1], cut_time)
    song.write_md2_file(CMD_ARGS[2])
