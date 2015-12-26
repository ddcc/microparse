#! /usr/bin/env python3

import argparse
import datetime
import os
import re
import binascii
import struct

import amd
import intel
import via

# Used to parse processor signature
class signature():
    fmt_string = "-- %-27s: %s\n"

    def __init__(self, signature):
        if signature != 0:
            self.stepping = signature & 0xF
            signature = signature >> 4

            self.model = signature & 0xF
            signature = signature >> 4

            self.family = signature & 0xF
            signature = signature >> 4

            self.type = signature & 0x3
            signature = signature >> 2

            self.unknown1 = signature & 0x3
            signature = signature >> 2

            self.extended_model = signature & 0xF
            signature = signature >> 4

            self.extended_family = signature & 0xFF
            signature = signature >> 8

            self.unknown2 = signature & 0xF
        else:
            raise Exception("Invalid processor signature!")

    def __str__(self):
        return \
        signature.fmt_string % ("Stepping", static.hex8(self.stepping)) + \
        signature.fmt_string % ("Model", static.hex8(self.model)) + \
        signature.fmt_string % ("Family", static.hex8(self.family)) + \
        signature.fmt_string % ("Type", static.hex8(self.type)) + \
        signature.fmt_string % ("Unknown 1", static.hex8(self.unknown1)) + \
        signature.fmt_string % ("Extended Model", static.hex8(self.extended_model)) + \
        signature.fmt_string % ("Extended Family", static.hex8(self.extended_family)) + \
        signature.fmt_string % ("Unknown 2", static.hex8(self.unknown2))

class static():
    fmt_string = "%-30s: %s\n"

    def data(swap_endian):
        if not swap_endian:
            return struct.Struct("<I")
        else:
            return struct.Struct(">I")

    def int2date(date):
        hex_date = static.hex8(date)[2 : ]
        return hex_date[4 : 8] + "/" + hex_date[0 : 2] + "/" + hex_date[2 : 4]

    def ymd2date(y, m, d):
        return str(y).zfill(4) + "/" + str(m).zfill(2) + "/" + str(d).zfill(2)

    def hex8(num):
        return "0x%08x" % num

    def tprint(string):
        print(str(datetime.datetime.now()) + ": " + string)

def ascii2bin(data):
    code = b""
    values = re.sub(b"[ \t\r]", b"", data) # remove spaces, tabs, and newlines (windows)
    values = re.split(b"[,\n]", values) # split on newlines (linux) and commas

    for v in values:
        if v.startswith(b"0x"):
            code += binascii.unhexlify(bytes(v[2 : ]))

    return code

def detect_ascii(path):
    with open(path, "rb") as f:
        for block in f:
            if b'\0' in block: # check for null
                return False
    return True

def open_path(path):
    if os.path.isdir(path):
            if result.recursive == True:
                listing = os.listdir(path)

                for obj in listing:
                    open_path(path + "/" + obj)

            else:
                raise Exception("Cannot open directory without recursion")
    else:
        data = b""
        static.tprint("Parsing " + path)

        if path.endswith((".dat", ".bin", ".txt", ".pdb", ".PDB", ".cfg", ".h", ".c")):
            with open(path, "rb") as f:
                data = f.read()

            if detect_ascii(path):
                data = ascii2bin(data)

            parse(data)
        else:
            static.tprint("Error: File extension not recognized")

def parse(data):
    offset = 0

    while offset < len(data):
        if result.type == "amd":
            if (result.amd_individual):
                m = amd.microcode(data[offset : ], dict(), 0, result.swap_endian)
            else:
                m = amd.container(data[offset : ], result.swap_endian)
        elif result.type == "intel":
            m = intel.microcode(data[offset: ], result.swap_endian)
        elif result.type == "via":
            m = via.microcode(data[offset: ], result.swap_endian)
        else:
            raise Exception("Microcode format not specified")

        if result.verbose:
            print(m)

        if result.report:
            report(m)

        if result.output:
            output(m)

        offset += m.size()

def output(m):
    if result.type != "amd" or result.amd_individual:
        filename = result.output + "/" + m.filename() + ".bin"

        if not os.path.exists(result.output):
            os.makedirs(result.output)

        if not os.path.exists(filename):
            with open(filename, "wb") as f:
                static.tprint("Writing " + f.name)
                f.write(m.raw)
        else:
            static.tprint("File " + filename + " already exists!")
    else:
        for microcode in m.microcodes:
            filename = result.output + "/" + microcode.filename() + ".bin"

            if not os.path.exists(result.output):
                os.makedirs(result.output)

            if not os.path.exists(filename):
                with open(filename, "wb") as f:
                    static.tprint("Writing " + f.name)
                    f.write(microcode.raw)
            else:
                static.tprint("File " + filename + " already exists!")

def report(m):
    with open("report.csv", "a") as f:
        f.write(m.csv())
    static.tprint("Updating report file")

def main():
    global result

    parser = argparse.ArgumentParser(description = "Microparse: AMD/Intel/VIA CPU microcode update parser")
    parser.add_argument("-c", action = "store_true", dest = "amd_individual", default = False, help = "amd microcode is not in container (rare)")
    parser.add_argument("-e", action = "store_true", dest = "swap_endian", default = False, help = "swap parsing endianess")
    parser.add_argument("-o", action = "store", dest = "output", help = "output directory for segmented microcode")
    parser.add_argument("-p", action = "store_true", dest = "report", default = False, help = "generate CSV report of all parsed microcode")
    parser.add_argument("-r", action = "store_true", dest = "recursive", default = False, help = "recurse into directory")
    parser.add_argument("-t", action = "store", dest = "type", choices = ["amd", "intel", "via"], help = "specify input format as amd, intel, or via microcode")
    parser.add_argument("-v", action = "store_true", dest = "verbose", default = False, help = "verbose output")
    parser.add_argument("target", action = "store", help = "input file or folder")

    result = parser.parse_args()

    open_path(result.target)

if __name__ == "__main__":
    main()
