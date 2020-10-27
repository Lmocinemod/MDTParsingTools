# MDT Parsing Tools
### Version 1.0.0
#### by Lmocinemod, using code by HertzDevil and MarkCWirt

## Contents
* [About](#about)
* [How To Use](#how-to-use)
* [.MD2 Exports](#md2-exports)
* [MIDI Instruments](#midi-instruments)
* [Known Limitations](#known-limitations)
* [Credits](#credits)

## About
MDT Parsing Tools is a set of Python scripts that can parse MDRV2 .MDT
binaries, decompile them to .MD2 files, extract OPM-format instrument data
(readable by
[VOPM virtual synth](https://www.kvraudio.com/product/vopm-by-sam)), and export
note data as MIDI files.

[MDRV2](https://www.vector.co.jp/soft/dos/art/se018677.html) is the music
driver used in [_Touhou Reiiden ~ Highly Responsive to
Prayers_](https://en.touhouwiki.net/wiki/Highly_Responsive_to_Prayers)
(hereafter, "HRtP"), and all of the music tracks that play in-game are stored
as .MDT binary files in the main game directory.

## How To Use
If you've downloaded the Windows EXE, simply run `MDTparse.exe` and follow the
instructions.

If you've downloaded the source code, first download
[`MidiFile.py`](https://github.com/MarkCWirt/MIDIUtil/blob/develop/src/midiutil/MidiFile.py)
from [MarkCWirt's MIDIUtil library](https://github.com/MarkCWirt/MIDIUtil),
and move it into the same directory as the other scripts. Then, pass `main.py`
as an argument to your Python interpreter of choice.

The scripts were written for Python v3.8.4, and compatibility with other
versions - especially earlier versions - cannot be guarenteed.

## .MD2 Exports
The exported .MD2 files can be re-compiled back into .MDT binaries using
MDRV2's compiler. Binaries re-compiled from decompilations of HRtP's music have
been found to be _functionally_ identical to the originals, though not fully
byte-perfect. (See [Known Limitations](#known-limitations) for details.)

For information regarding MDRV2's dialect of MML, please see the
[English translation of the
documentation,](https://en.touhouwiki.net/wiki/User:Mami/Music_Dev/Mdrv2/Md2mml)
hosted on Touhou Wiki.

## MIDI Instruments
Because .MDT binaries call for FM instruments and SSG envelopes, which cannot
be directly encoded into MIDI, the program will convert all instrument change
events to Grand Piano by default.

Because a MIDI consisting entirely of pianos sounds rather bland when played
back, a set of manually-selected instrument suggestions is available for the
tracks from HRtP. These instruments were selected with Microsoft GS Wavetable
Synth and [Arachno SoundFont](http://www.arachnosoft.com/main/soundfont.php) in
mind, and several artistic liberties were taken in their selection.

Additionally, if the user opts for OPM-format instrument data to be exported,
the program can use these exported instruments for the instrument change MIDI
events, allowing for very close approximations of the original track when using
VOPM.

However, the program is incapable of exporting SSG envelopes. To compensate for
this, a set of manually-defined FM approximations is included in the download.
To use them, simply import `approximations.opm` into your VOPM instance(s).

## Known Limitations
* Decompiled .MD2 MML files are SHIFT-JIS-encoded (with CRLF line endings), and
may not display correctly in some text editors.
* Unused FM instruments may not re-compile back to their original data.
* Unused macros are not decompiled, and are thus excluded from re-compiled
binaries.
* Byte 31 (index 0) of FM instrument definitions does not re-compile to its
original value. However, byte 31 appears to be unused, and does not seem to
affect playback.
* **Portamentos (glides) require large lookup tables to decompile, and may not
work correctly for SSG channels.**
* Attempting to decompile binaries that contain any of the following may cause
a crash:
    * ADPCM data
    * Octave 8 SSG notes
    * OPM/OPLL flags
* SSG envelopes cannot be exported as OPM approximations.
* MIDI cannot be exported from binaries compiled for OPM/OPLL.
* ADPCM channels are completely ignored when exporting MIDI.
* MIDI portamento rate is not calculated based on portamento length, and
instead uses a constant, user-selectable value (default: 55).
* **When exporting MIDI, infinite loops are not extended to match the lengths
of the other parts, causing some parts to seemingly end early.**
* Fade-ins/outs are not converted to MIDI.
* **No attempt is made to accurately translate LFO information to MIDI
controllers, which may result in vibrato/tremolo being barely noticable.**
* No attempt is made to compensate for FM instruments that play at higher or
lower octaves than the MML data would imply.
* It is not possible to choose file names/extensions when exporting multiple
files.
* **It is not possible to export any files to a folder that does not already
exist.**
* It may not be possible to write to protected folders, as the program does not
attempt to elevate its permissions.
* The program does not accept any command-line parameters or options.

## Credits
[HertzDevil](https://www.youtube.com/user/hertzdevil/), for the decompilation
script.

[MarkCWirt](https://github.com/MarkCWirt), for the MIDIUtil library.

For details, please see `CREDITS.txt`.
