# Introduction

Script to print entries from the Oxford English Dictionary Second Edition on CD-ROM (v.4.0) to terminal. This eliminates the need to use the Flash-based executable included in the CD-ROM to view the contents. Note that this repository does NOT include any content from the dictionary's entries: it is only a helper script for viewing entries from a legally purchased copy of the Oxford English Dictionary CD-ROM.

# Usage

Put `oed.py` and `oeda.py` into the root directory of the dictionary and run the command:

```
./oed.py [entry]
```

Where [entry] is the search query. Use `-h` for a list of all options.

#  More info

Dictionary entries are contained in Zlib-compressed blocks (1066 total) in the 196MB file `oed.t`. Blocks are located at fixed offsets defined as integer constants in the Neko bytecode file `app.n`. The Zlib magic (78 DA) at the start of each block was originally overwritten with a random 16-bit value. This and the offsets were discovered in a bytecode dump of `app.n` using the [Neko Compiler](https://nekovm.org/doc/tools/) `nekoc`.

## Entities

Entites, HTML-based representations of non-ASCII symbols, are defined in the script file `EntityMapper.as` compiled into the Flash executable `OED.swf`. The script file was extracted from the Flash executable using the [JPEXS Free Flash Decompiler](https://github.com/jindrapetrik/jpexs-decompiler) and the entities were copied to `oeda.py`.
