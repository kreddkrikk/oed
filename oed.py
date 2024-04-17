#!/usr/bin/python3 -u

import argparse
import logging
import oeda
import os
import re
import textwrap
import zlib
from html.parser import HTMLParser

class color:
   MAGENTA = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

class MyHTMLParser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        if tag == 'br': print()
        elif tag == 'hw': print(color.BOLD, end='')
        elif tag == 'xr': print(color.BLUE, end='')
        elif tag == 'upd': print(color.RED, end='')
        elif tag == 'd': print(color.MAGENTA + color.BOLD, end='')
        #else: print('<' + tag + '>')
        
    def handle_endtag(self, tag):
        if tag == 'hw': print(color.END, end='')
        elif tag == 'xr': print(color.END, end='')
        elif tag == 'upd': print(color.END, end='')
        elif tag == 'e': print(end='\n\n')
        elif tag == 'sube': print(end='\n\n')
        elif tag == 'd': print(color.END, end='')
        #else: print('</' + tag + '>')
        
    def handle_data(self, data):
        #data = textwrap.fill(data, 80)
        print(data, end='')

def decompress_block(infile, offsets, index, fix_zlib=False):
    infile.seek(offsets[index])
    chunksize = offsets[index + 1] - offsets[index]
    comp_data = infile.read(chunksize)
    comp_data = bytearray(comp_data)
    if fix_zlib:
        # Fix zlib magic
        comp_data[0] = 0x78
        comp_data[1] = 0xda
    return bytearray(zlib.decompress(comp_data))

# Get query from arguments
def init_query():
    parser = argparse.ArgumentParser(
            description='Search for a word in the Oxford English Dictionary')
    parser.add_argument('query', metavar='query', help='word to search for')
    parser.add_argument('--log', dest='loglevel', help='set the logging level') 
    args = parser.parse_args()
    query = args.query
    loglevel = args.loglevel
    if loglevel:
        numlevel = getattr(logging, loglevel.upper())
        logging.basicConfig(level=numlevel)
    return query

# Initialize entry list
def get_entries(filename, separator):
    with open(filename, 'r+b') as f:
        b = f.read()
    d = zlib.decompress(b)
    s = d.decode('utf-8')
    if separator == '#':
        entries = s.split(separator)[1:]
    else:
        entries = s.split(separator)
    return entries

def get_selected_entry(entries):
    selected = input('\nPlease select an entry: ')
    if not selected:
        exit(1)
    if not selected.isnumeric():
        print(f'\'{selected}\' is not a number')
        return None
    index = int(selected)
    if index > len(entries) or index < 1:
        print(f'\'{short_index}\' is out of range')
        return None
    return entries[index - 1][0]

# Find index of entry
def find_entry_index(entries, query):
    entry_index = None
    results = []
    for i in range(0, len(entries)):
        result = entries[i]
        if re.match(rf'^{query}\b', result):
            # Replace entities and find matches again
            for entity in oeda.entities:
                result = result.replace(entity[0], entity[1])
            if re.match(rf'^{query}\b', result):
                results.append((i, result))
        elif entry_index:
            break
    parser = MyHTMLParser()
    if len(results) > 1:
        print(f'Found multiple entries matching \'{query}\':\n')
        for i in range(0, len(results)):
            result = results[i]
            print(f'{i+1:d}. ', end='')
            parser.feed(result[1])
            print()
        while not entry_index:
            entry_index = get_selected_entry(results)
        print()
    elif len(results) > 0:
        entry_index = results[0][0]
    if entry_index:
        logging.info('%s is entry number %d' % (query, entry_index))
    return entry_index

# Find index of block containing entry contents
def find_block_index(entry_index, query):
    blk_index = None
    for i in range(0, len(oeda.oednum)):
        if entry_index < oeda.oednum[i]:
            blk_index = i - 1
            break
    if blk_index is None:
        logging.error('Container block not found')
        exit(1)
    logging.info('%s is in block %d at offset %d' % (query, blk_index, 
        oeda.oedlen[blk_index]))
    return blk_index

def get_block_bytes(filename, blk_array, blk_index):
    with open(filename, 'r+b') as f:
        return decompress_block(f, blk_array, blk_index, True) 

def get_block_string(filename, blk_array, blk_index):
    blk = get_block_bytes(filename, blk_array, blk_index)
    return str(blk).split('#')[1:]

# Format definition contents
def get_definition(blk_str, entry_blk_index):
    definition = blk_str[entry_blk_index]
    for entity in oeda.entities:
        definition = definition.replace(entity[0], entity[1])
    definition = definition.replace('\\\'', '\'')
    return definition

def main():
    query = init_query()
    entries = get_entries('hw.t', '^')
    entry_index = find_entry_index(entries, query)
    # Look in ky.t
    if not entry_index:
        entries = get_entries('ky.t', '#')
        entry_index = find_entry_index(entries, query)
    if not entry_index:
        print(f'Search for {query} returned no results')
        exit(0)
    blk_index = find_block_index(entry_index, query)
    entry_blk_index = entry_index - oeda.oednum[blk_index]
    logging.info('%s is at index %d in block %d' % (query, entry_blk_index, 
        blk_index))
    blk_str = get_block_string('oed.t', oeda.oedlen, blk_index)
    definition = get_definition(blk_str, entry_blk_index)
    parser = MyHTMLParser()
    parser.feed(definition)

if __name__ == '__main__':
    main()
