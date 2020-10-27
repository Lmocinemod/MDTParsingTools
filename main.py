from sys import exit
from os.path import isfile, isdir
from glob import glob
from typing import List, Dict, cast

from mdt_decomp_rip import (
    write_opm_header,
    write_unused_warning,
    remove_path,
    FMInstrument,
    Song,
    parse_mdt,
    process_insts_in_songs
)
from md2mml_midi import (
    SUGGESTED_INST_NUMS,
    SUGGESTED_SSG_NUMS,
    APPROXIMATION_SSG_NUMS,
    parse_song,
    write_midi_file,
    MIDIFile
)


# Constants
AFFIRMATIVES = {"yes", "y"}
NEGATIVES = {"no", "n"}

# Me trying to be funny (and failing miserably)
AFFIRMATIVES |= {"ye", "yeh", "ya", "yah", "yas", "yahs", "yeah", "aye"}
AFFIRMATIVES |= {"yeah boi", "yeah girl", "yessir", "yes sir", "yes ma'am"}
NEGATIVES |= {"nah", "meh", "nty", "no thx", "nope", "heck no", "nay"}
NEGATIVES |= {"nah boi", "nah girl", "no sir", "no ma'am"}

# While I'm at it...
AFFIRMATIVES |= {"si", "oui", "ja", "jes", "da", "hai", "un"}
NEGATIVES |= {"non", "nein", "ne", "net", "nyet", "iie", "iya", "u~un"}

# This was used as a placeholder value at one point, but not anymore.
JOKE = "Satori's self-esteem."


# Okay, back to work.
# Helper functions
def empty_line():
    print("")


def longstr(*parts: str) -> str:
    return " ".join(parts)


def prompt(*prompt_parts: str) -> str:
    prompt_str = longstr(*prompt_parts) + " "
    try:
        return input(prompt_str)
    except (KeyboardInterrupt, EOFError):
        print("\nExiting due to keyboard interrupt or EOF.")
        exit()


def yes_no(*question_parts: str) -> bool:
    question = longstr(*question_parts) + " (Y/n):"
    answer = ""
    while answer not in AFFIRMATIVES and answer not in NEGATIVES:
        answer = prompt(question).lower()
    return answer in AFFIRMATIVES


# Subroutines (so I don't hate myself when writing main())
def input_subroutine() -> (str, bool):
    path = ""
    while not isfile(path) and not isdir(path):
        path = prompt(
            "Please specify an input file/folder",
            "(paths are relative to main.py or MDTparse.exe):"
        )
    return (path, isfile(path))


def parse_subroutine(
    path_input: str,
    input_is_file: bool,
    whether_cut_time: bool
) -> list:
    print("Parsing input MDT file(s)...")
    song_list = []

    # Give credit where it's due
    print(longstr(
        "MDT->MD2 decompiler based on HertzDevil's",
        "\"MDRV2 MDT to MML unconverter\" script.",
        "Please see CREDITS.txt for more information."
    ))

    # Parse input MDT file(s)
    if input_is_file:
        # "Easier to Ask for Forgiveness than Permission" (EAFP) models are
        # present throughout a lot of this file. It might be the Pythonic
        # thing to do, but I personally really dislike all these indents.
        # (Doesn't help that autopep8 forces me to use a tab width of 4. 😑)
        # Maybe it's time I learned C... lol
        try:
            s = parse_mdt(path_input, whether_cut_time)
            song_list.append(s)
        except BaseException as err:
            print("Exiting due to error during parsing of input file:", err)
            exit()

    else:
        for f in glob(f"{path_input}/*.MDT"):
            try:
                s = parse_mdt(f, whether_cut_time)
                song_list.append(s)
            except BaseException as err:
                print("Skipping file", remove_path(f), "due to error:", err)
                continue

    print("DONE")
    return song_list


def md2_subroutine(song_list: List[Song], input_is_file: bool):
    # Possibly exit subroutine early
    whether_decompile = yes_no(
        "Would you like to decompile the MDT file(s) to MD2 (MML) file(s)?"
    )
    if not whether_decompile:
        return

    # Output MD2 file(s)
    if input_is_file:
        while True:
            # Get a filename
            path = prompt(
                "Please specify an output file for the MD2 MML",
                "(this cannot be a folder):"
            )
            if not path or isdir(path):
                continue

            # Try to write to it
            try:
                song_list[0].write_md2_file(path)
            except OSError:
                print("Failed to create file. Please enter a different path.")
                continue
            break

    else:
        while True:
            # Get a directory
            path = ""
            while not isdir(path):
                path = prompt(
                    "Please specify an output folder for the MD2 files:"
                )

            # Try to write to it
            try:
                for s in song_list:
                    filename = s.filename
                    if len(filename) >= 4 and filename[-4:].upper() == ".MDT":
                        filename = filename[:-4] + ".MD2"
                    s.write_md2_file(path + "/" + filename)
            except OSError:
                print(longstr(
                    "Failed to write to folder.",
                    "Please specify a different output folder."
                ))
                continue
            break

    print("DONE")


def opm_subroutine(song_list: List[Song]) -> Dict[str, Dict[int, int]]:
    # Possibly exit subroutine early
    whether_export_opm = yes_no(
        "Would you like to export FM instruments in OPM format,",
        "for use in VOPM/VOPMex?"
    )
    if not whether_export_opm:
        return cast(Dict[str, Dict[int, int]], {})

    # Extract, remove duplicates, split, sort, assign, generate inst_map
    # (This function does WAY too much 😂)
    used, unused, inst_map = process_insts_in_songs(song_list)

    # Figure out what to export
    whether_export_used = yes_no(
        "Export instruments that ARE used in the input files?"
    )
    whether_export_unused = yes_no(
        "Export instruments that ARE NOT used in the input files?"
    )

    # Export used instruments (maybe)
    if whether_export_used:
        while True:
            # Get a filename
            path = prompt(
                "Please specify an output file for the used instruments",
                "(this cannot be a folder):"
            )
            if not path or isdir(path):
                continue

            # Try to write to it
            try:
                with open(path, "w") as f:
                    write_opm_header(f)
                    for i, v in enumerate(used):
                        f.write(v.opm_str(i))
                    f.close()
            except OSError:
                print("Failed to create file. Please enter a different path.")
                continue
            break

    # Export unused instruments (maybe)
    if whether_export_unused:
        while True:
            # Get a filename
            path = prompt(
                "Please specify an output file for the unused instruments",
                "(this cannot be a folder):"
            )
            if not path or isdir(path):
                continue

            # Try to write to it
            try:
                with open(path, "w") as f:
                    write_unused_warning(f)
                    write_opm_header(f)
                    for i, v in enumerate(unused):
                        f.write(v.opm_str(i))
                    f.close()
            except OSError:
                print("Failed to create file. Please enter a different path.")
                continue
            break

    print("DONE")
    return inst_map


def midi_subroutine(
    song_list: List[Song],
    inst_map: Dict[str, Dict[int, int]],
    input_is_file: bool,
    cut_time: bool
):
    # Possibly exit subroutine early
    whether_export_midi = yes_no(
        "Would you like to export MIDI conversions of the input file(s)?"
    )
    if not whether_export_midi:
        return

    # Give credit where it's due
    print(longstr(
        "MIDI conversion made possible by the Python library MIDIUtil,",
        "made by MarkCWirt. Please see CREDITS.txt for more information."
    ))

    # Figure out which FM/SSG instrument map(s) to use, if any
    # Figure out which FM instrument map to use, if any
    fm_inst_map = cast(Dict[str, Dict[int, int]], {})
    ssg_inst_map = cast(Dict[str, Dict[int, int]], {})
    selection = 0
    if not not inst_map:
        # User extracted OPMs, offer to use them in MIDI
        whether_use_inst_map = yes_no(
            "Would you like to use the exported OPM-format instruments",
            "for MIDI program change numbers?"
        )
        if whether_use_inst_map:
            selection = 1
            print(longstr(
                "Note that SSG channels may use OPM-format approximations,",
                "contained in approximations.txt (included in download)."
            ))
    if selection == 0:
        # User doesn't have or doesn't want to use OPMs
        # Offer to use suggested instrument numbers
        whether_use_suggested = yes_no(
            "Would you like to use suggested MIDI program change numbers",
            "for TH01 (HRtP) tracks?"
        )
        if whether_use_suggested:
            selection = 2

    if selection == 1:
        fm_inst_map = inst_map
        ssg_inst_map = APPROXIMATION_SSG_NUMS
    elif selection == 2:
        fm_inst_map = SUGGESTED_INST_NUMS
        ssg_inst_map = SUGGESTED_SSG_NUMS

    # if not not inst_map:
    #     whether_use_inst_map = yes_no(
    #         "Would you like to use the exported OPM-format instruments",
    #         "for MIDI program change numbers on FM channels?"
    #     )
    #     if whether_use_inst_map:
    #         selection = 1
    # if not selection:
    #     whether_use_suggested = yes_no(
    #         "Would you like to use suggested MIDI program change numbers",
    #         "for FM channels in TH01 (HRtP) tracks?"
    #     )
    #     if whether_use_suggested:
    #         selection = 2
    # selection = selection or 3
    # inst_map = inst_map if (selection == 1) else (
    #     SUGGESTED_INST_NUMS if (selection == 2) else cast(
    #         Dict[str, Dict[int, int]],
    #         {}
    #     )
    # )

    # # Figure out whether or not the premade SSG instrument map should be used
    # ssg_map = cast(Dict[str, Dict[int, int]], {})
    # whether_use_ssg_map = yes_no(
    #     "Would you like to use suggested MIDI program change numbers",
    #     "for SSG channels in TH01 (HRtP) tracks?"
    # )
    # if whether_use_ssg_map:
    #     ssg_map = SUGGESTED_SSG_NUMS

    # Figure out what portamento rate to use
    # Can you say "feature creep?" 😏
    portamento_rate = 55
    while True:
        # Get a portamento rate
        answer = prompt(
            "Please specify a portamento rate to use (0-127, inclusive),",
            "or leave empty to use the default (55):"
        )

        # Try to convert it to an int (or default to 55)
        if not answer:
            break
        try:
            portamento_rate = int(answer)
            if portamento_rate < 0 or portamento_rate > 127:
                portamento_rate = 55
                continue
            break
        except ValueError:
            continue

    # Export one MIDI file
    if input_is_file:
        s = song_list[0]
        midi: MIDIFile

        # Try to convert to MIDI
        try:
            midi = parse_song(
                song=s,
                fm_inst_map=fm_inst_map,
                ssg_inst_map=ssg_inst_map,
                portamento_rate=portamento_rate,
                cut_time=cut_time
            )
        except BaseException as err:
            print("Could not convert file", s.filename, "due to error:", err)
            return

        # Output the file
        while True:
            # Get a filename
            path = prompt("Please specify an output MIDI file:")
            if not path or isdir(path):
                continue

            # Try to write to it
            try:
                write_midi_file(path, midi)
            except OSError:
                print("Failed to create file. Please enter a different path.")
                continue
            break

    # Export several MIDI files
    else:
        while True:
            # Get a directory
            path = prompt(
                "Please specify an output folder for the MIDI files:"
            )
            if not isdir(path):
                continue

            # Try... several things
            try:
                for s in song_list:
                    # Convenience variables
                    filename = s.filename
                    if len(filename) >= 4 and filename[-4:].upper() == ".MDT":
                        filename = filename[:-4] + ".MID"
                    midi: MIDIFile

                    # Try to convert to MIDI
                    try:
                        midi = parse_song(
                            song=s,
                            fm_inst_map=fm_inst_map,
                            ssg_inst_map=ssg_inst_map,
                            portamento_rate=portamento_rate,
                            cut_time=cut_time
                        )
                    except BaseException as err:
                        print(
                            "Skipping file", s.filename, "due to error:", err
                        )
                        continue

                    # Try to write to the directory from before
                    write_midi_file(
                        filename=path + "/" + filename,
                        midi_file=midi
                    )
            except OSError:
                print(longstr(
                    "Failed to write to folder.",
                    "Please specify a different output folder."
                ))
                continue
            break

    print("DONE")


# Yeah, I might have delegated a bit TOO much... main() is pretty empty now!
def main():
    # Greeting message
    print("|-------------------------------------------------------|")
    print("|            MDT Parsing Tools version 1.0.0            |")
    print("| by Lmocinemod, using code by HertzDevil and MarkCWirt |")
    print("|-------------------------------------------------------|")
    empty_line()

    # Get input file or directory
    path_input, input_is_file = input_subroutine()

    # Should I use cut time?
    whether_cut_time = yes_no(
        "Would you like to use cut (double) time for parsing/conversion?",
        "This is recommended for TH01 (HRtP)."
    )

    # Parse all the things!
    song_list: List[Song] = parse_subroutine(
        path_input,
        input_is_file,
        whether_cut_time
    )
    empty_line()

    # Decompile stuff!
    md2_subroutine(song_list, input_is_file)
    empty_line()

    # Do OPM stuff!
    fm_inst_map: Dict[str, Dict[int, int]] = opm_subroutine(song_list)
    empty_line()

    # Now export MIDI! (If the user wants)
    midi_subroutine(song_list, fm_inst_map, input_is_file, whether_cut_time)
    empty_line()

    print("All tasks complete!")
    input("Press ENTER/RETURN to exit.")


if __name__ == "__main__":
    main()
