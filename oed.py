#!/usr/bin/python3 -u

import argparse
import logging
import oeda
import os
import re
import subprocess
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
    def __init__(self):
        HTMLParser.__init__(self)
        self.text = ''

    def handle_starttag(self, tag, attrs):
        if tag == 'br': self.text += '\n'
        elif tag == 'hw': self.text += color.BOLD
        elif tag == 'xr': self.text += color.BLUE
        elif tag == 'upd': self.text += color.RED
        elif tag == 'd': self.text += color.MAGENTA + color.BOLD
        #else: self.text += '<' + tag + '>')
        
    def handle_endtag(self, tag):
        if tag == 'hw': self.text += color.END
        elif tag == 'xr': self.text += color.END
        elif tag == 'upd': self.text += color.END
        elif tag == 'e': self.text += '\n\n'
        elif tag == 'sube': self.text += '\n\n'
        elif tag == 'd': self.text += color.END
        #else: self.text += '</' + tag + '>')
        
    def handle_data(self, data):
        self.text += data

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
def get_query():
    try:
        query = input('Enter search term: ')
    except:
        print()
        exit(1)
    print()
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
    try:
        selected = input('Please select an entry: ')
    except:
        print('\n')
        return -1
    if not selected:
        print('No entry selected\n')
        return None
    if not selected.isnumeric():
        print(f'\'{selected}\' is not a number\n')
        return None
    index = int(selected)
    if index > len(entries) or index < 1:
        print(f'\'{index}\' is out of range\n')
        return None
    print()
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
    text = ''
    parser = MyHTMLParser()
    if len(results) > 1:
        print(f'Found multiple entries matching \'{query}\':\n')
        for i in range(0, len(results)):
            result = results[i]
            text += f'{i+1:d}. {result[1]}\n'
        parser.feed(text)
        parser.close()
        print(parser.text)
        while not entry_index:
            entry_index = get_selected_entry(results)
    elif len(results) > 0:
        entry_index = results[0][0]
    if entry_index and entry_index > 0:
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

# Ignore color tags when calculating line length
def fold(text, width):
    output = ''
    text = text.replace('\u00A0', ' ')
    text = re.sub(r' {3,}', r'  ', text)
    for line in text.split('\n'):
        column = 0
        for word in line.split(' '):
            vlen = len(word) # Visible length (excluding color tags)
            blen = vlen # Byte length (including color tags)
            i = 0
            while i < blen:
                # Exclude color tag from length
                if word[i] == '\x1b':
                    while i < blen and word[i] != 'm':
                        vlen -= 1
                        i += 1
                    vlen -= 1
                i += 1
            column += vlen + 1 # Include space
            if column > width:
                column = vlen + 1 # Include space
                output += '\n' # Wrap the text!
            output += word + ' '
        output += '\n'
    return output

def main():
    parser = argparse.ArgumentParser(
        description='Search for a word in the Oxford English Dictionary')
    parser.add_argument('-i',  '--interactive', action='store_true', help='interactive mode')
    parser.add_argument('-w', '--width', type=int, help='wrap to column width (default: 80)')
    parser.add_argument('query', metavar='query', nargs='?', default=None, help='word to search for')
    parser.add_argument('--log', dest='loglevel', help='set the logging level')
    args = parser.parse_args()
    interactive = args.interactive
    loglevel = args.loglevel
    query = args.query
    width = args.width
    print('Oxford English Dictionary 2nd ed. on CD-ROM (v4.0)')
    print('Copyright © 2009 Oxford University Press\n')
    if interactive:
        print('Running in interactive mode. Use Ctrl-C to quit.\n')
    else:
        print('Running in default mode. Use Ctrl-C to quit.\n')
    while True:
        if not query:
            query = get_query()
        entries = get_entries('hw.t', '^')
        entry_index = find_entry_index(entries, query)
        if entry_index == -1:
            query = None
            continue
        # Look in ky.t
        if not entry_index:
            entries = get_entries('ky.t', '#')
            entry_index = find_entry_index(entries, query)
        if not entry_index:
            print(f'Search for {query} returned no results\n')
            query = None
            continue
        blk_index = find_block_index(entry_index, query)
        entry_blk_index = entry_index - oeda.oednum[blk_index]
        logging.info('%s is at index %d in block %d' % (query, entry_blk_index, 
            blk_index))
        blk_str = get_block_string('oed.t', oeda.oedlen, blk_index)
        definition = get_definition(blk_str, entry_blk_index)
        parser = MyHTMLParser()
        parser.feed(definition)
        parser.close()
        if width:
            text = fold(parser.text, width) if width else parser.text
        else:
            text = parser.text
        if interactive:
            process = subprocess.Popen(['less', '-r'], stdin=subprocess.PIPE)
            try:
                process.stdin.write(bytes(text, 'utf-8'))
                process.communicate()
            except IOError as e:
                pass
        else:
            print(text)
            break
        query = None


if __name__ == '__main__':
    main()
