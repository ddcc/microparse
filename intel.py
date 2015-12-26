#! /usr/bin/env python3

import microparse
import struct

# http://review.coreboot.org/gitweb?p=coreboot.git;a=blob;f=src/cpu/intel/microcode/microcode.c;hb=HEAD
# http://lxr.free-electrons.com/source/arch/x86/include/asm/microcode_intel.h
# http://lxr.free-electrons.com/source/arch/x86/kernel/microcode_intel.c
# http://lxr.free-electrons.com/source/arch/x86/kernel/microcode_intel_early.c
# http://lxr.free-electrons.com/source/arch/x86/kernel/microcode_intel_lib.c
# http://inertiawar.com/microcode/

class static():
    # default data block size for old microcode revisions
    DEFAULT_DATA_SIZE = 2000

    def header(swap_endian):
        if swap_endian:
            return struct.Struct("<IIIIIIIIIiii")
        else:
            return struct.Struct(">IIIIIIIIIiii")

    def data_header(swap_endian):
        if swap_endian:
            return struct.Struct("<IIIIIIIIIIIIIIIIIIIIIIII")
        else:
            return struct.Struct(">IIIIIIIIIIIIIIIIIIIIIIII")

    def extended_count(swap_endian):
        if swap_endian:
            return struct.Struct("<IIiii")
        else:
            return struct.Struct(">IIiii")

class microcode():
    def __init__(self, data, swap_endian):
        self.is_swap_endian = swap_endian

        self.parse_header(data[0 : static.header(self.is_swap_endian).size])
        self.parse_data(data[static.header(self.is_swap_endian).size : static.header(self.is_swap_endian).size + self.data_size])

        self.is_data_extended = False
        if self.data.count(0) > 8: # weak heuristic for additional metadata in data block
            self.is_data_extended = True
            self.parse_data_header()

        self.is_extended = False
        if self.total_size - (static.header(self.is_swap_endian).size + self.data_size) > 0: # metadata has extended section
            self.is_extended = True
            raise Exception("Warning: Extended Intel microcode not fully supported!")
            self.parse_extended_count(data[static.header(self.is_swap_endian).size + self.data_size : static.header(self.is_swap_endian).size + self.data_size + intel.static.extended_count(self.is_swap_endian).size], result.endian)
            self.parse_extended(data[static.header(self.is_swap_endian).size + self.data_size + intel.static.extended_count(self.is_swap_endian).size : self.total_size], result.endian)

        self.raw = data[0 : self.total_size]

    def csv(self):
        data_extended = "Y" if self.is_data_extended else "N"
        extended = "Y" if self.is_extended else "N"

        return \
        microparse.static.hex8(self.processor_signature) + "," + \
        microparse.static.int2date(self.date) + "," + \
        microparse.static.hex8(self.header_version) + "," + \
        microparse.static.hex8(self.update_revision) + "," + \
        microparse.static.hex8(self.processor_flags) + "," + \
        microparse.static.hex8(self.checksum) + "," + \
        str(int(self.data_size) * microparse.static.data(self.is_swap_endian).size) + "," + \
        data_extended + "," + \
        extended + "\n"

    def filename(self):
        return microparse.static.hex8(self.processor_signature) + "_" + microparse.static.hex8(self.update_revision) + "_" + microparse.static.hex8(self.checksum)

    def size(self):
        return self.total_size

    def parse_header(self, data):
        if len(data) == static.header(self.is_swap_endian).size:
            try:
                header = static.header(self.is_swap_endian).unpack(data)
            except struct.error:
                raise Exception("Cannot unpack microcode header!")

            self.header_version = header[0]
            if self.header_version == 0x01000000:
                raise Exception("Unexpected microcode endianness!")
            elif self.header_version != 1:
                raise Exception("Unexpected microcode header version!")
            self.update_revision = header[1]
            self.date = header[2]
            self.processor_signature = header[3]
            self.checksum = header[4]
            self.loader_revision = header[5]
            self.processor_flags = header[6]
            self.data_size = header[7]
            if self.data_size == 0:
                self.data_size = static.DEFAULT_DATA_SIZE
            if self.data_size % 4 != 0: # sanity check
                raise Exception("Unexpected microcode data size")
            self.total_size = header[8]
            if self.total_size == 0: # recompute total size for old microcode revisions
                self.total_size = static.header(self.is_swap_endian).size + self.data_size
            #if (self.total_size % 1024 != 0): # seems to no longer be applicable for new microcode revisions
            #   raise Exception("Unexpected microcode total size")
            self.unknown1 = header[9]
            self.unknown2 = header[10]
            self.unknown3 = header[11]
        else:
            raise Exception("Input microcode header size mismatch!")

    def parse_data(self, data):
        self.data = []

        if len(data) == self.data_size:
            for i in range(0, self.data_size, microparse.static.data(self.is_swap_endian).size):
                try:
                    self.data.append(microparse.static.data(self.is_swap_endian).unpack(data[i : i + microparse.static.data(self.is_swap_endian).size])[0])
                except struct.error:
                    raise Exception("Cannot unpack microcode data!")
        else:
            raise Exception("Input microcode data size mismatch!")

    def parse_data_header(self):
        if self.is_data_extended and len(self.data) > static.data_header(self.is_swap_endian).size:
            try:
                # bit of a hack, need to repack the data back into a list
                header = bytearray()
                for i in range(static.data_header(self.is_swap_endian).size // 4):
                    header += microparse.static.data(self.is_swap_endian).pack(self.data[i])
                # now unpack
                data_header = static.data_header(self.is_swap_endian).unpack(header[0 : static.data_header(self.is_swap_endian).size])

            except struct.error:
                raise Exception("Cannot unpack microcode data header!")

            self.data_unknown1 = data_header[0]
            self.data_unknown2 = data_header[1]
            self.data_unknown3 = data_header[2]
            self.data_revision = data_header[3]
            self.data_unknown4 = data_header[4]
            self.data_unknown5 = data_header[5]
            self.data_date = data_header[6]
            self.data_length = data_header[7]
            self.data_unknown6 = data_header[8]
            self.data_processor_signature = data_header[9]
            self.data_unknown7 = data_header[10]
            self.data_unknown8 = data_header[11]
            self.data_unknown9 = data_header[12]
            self.data_unknown10 = data_header[13]
            self.data_unknown11 = data_header[14]
            self.data_unknown12 = data_header[15]
            self.data_unknown13 = data_header[16]
            self.data_unknown14 = data_header[17]
            self.data_unknown15 = data_header[18]
            self.data_unknown16 = data_header[19]
            self.data_unknown17 = data_header[20]
            self.data_unknown18 = data_header[21]
            self.data_unknown19 = data_header[22]
            self.data_unknown20 = data_header[23]
        else:
            raise Exception("Input microcode data header size mismatch!")

    def parse_extended_count(self, data): 
        if len(data) == static.extended_count(self.is_swap_endian).size:
            try:
                extended_data = static.extended_count(self.is_swap_endian).unpack(data)
            except struct.error:
                raise Exception("Cannot unpack microcode extended header!")

            self.extended_signature_count = extended_data[0]
            self.extended_table_checksum = extended_data[1]
            self.unknown4 = extended_data[2]
            self.unknown5 = extended_data[3]
            self.unknown6 = extended_data[4]
        else:
            raise Exception("Input microcode extended header size mismatch!")

    def parse_extended(self, data):
        self.extended_processor_signature = []
        self.extended_processor_flags = []
        self.extended_checksums = []

        if self.is_extended and len(data) == self.extended_signature_count * 3 * microparse.static.data(self.is_swap_endian).size:
            for i in range(0, self.extended_signature_count * 3 * microparse.static.data(self.is_swap_endian).size, 3 * microparse.static.data(self.is_swap_endian).size):
                try:
                    signature = microparse.static.data(self.is_swap_endian).unpack(data[i : i + microparse.static.data(self.is_swap_endian).size])
                    flags = microparse.static.data(self.is_swap_endian).unpack(data[i + microparse.static.data(self.is_swap_endian).size: i + 2 * microparse.static.data(self.is_swap_endian).size])
                    checksums = microparse.static.data(self.is_swap_endian).unpack(data[i + 2 * microparse.static.data(self.is_swap_endian).size : i + 3 * microparse.static.data(self.is_swap_endian).size])

                    self.extended_processor_signature.append(signature[0])
                    self.extended_processor_flags.append(flags[0])
                    self.extended_checksums.append(checksums[0])
                except struct.error:
                    raise Exception("Cannot unpack microcode extended data!")
        else:
            raise Exception("Input microcode extended data size mismatch!")

    def calculate_checksum(self):
        checksum = self.header_version + self.update_revision + self.date + self.processor_signature + self.loader_revision + self.processor_flags + self.data_size + self.total_size + self.unknown1 + self.unknown2 + self.unknown3
        for v in self.data:
            checksum += v

        return -checksum & 0xFFFFFFFF

    def calculate_extended_table_checksum(self):
        if self.is_extended:
            checksum = self.extended_signature_count + self.unknown4 + self.unknown5 + self.unknown6
            for s in self.extended_processor_signature:
                checksum += s
            for s in self.extended_processor_flags:
                checksum += s
            for s in self.extended_checksums:
                checksum += s

        return -checksum & 0xFFFFFFFF

    def calculate_extended_signature_checksum(self, offset):
        if self.is_extended:
            checksum = calculate_checksum() - self.processor_flags - self.processor_signature + self.extended_processor_signature[offset] + self.extended_processor_flags[offset]

        return -checksum & 0xFFFFFFFF

    def __str__(self):
        checksum1 = " (!)" if self.checksum != self.calculate_checksum() else ""

        output = \
        microparse.static.fmt_string % ("Header Version", microparse.static.hex8(self.header_version)) + \
        microparse.static.fmt_string % ("Update Revision", microparse.static.hex8(self.update_revision)) + \
        microparse.static.fmt_string % ("Date", microparse.static.int2date(self.date)) + \
        microparse.static.fmt_string % ("Processor Signature", microparse.static.hex8(self.processor_signature)) + \
        str(microparse.signature(self.processor_signature)) + \
        microparse.static.fmt_string % ("Checksum", microparse.static.hex8(self.checksum) + checksum1) + \
        microparse.static.fmt_string % ("Loader Revision", microparse.static.hex8(self.loader_revision)) + \
        microparse.static.fmt_string % ("Processor Flags", microparse.static.hex8(self.processor_flags)) + \
        microparse.static.fmt_string % ("Data Size", microparse.static.hex8(self.data_size)) + \
        microparse.static.fmt_string % ("Total Size", microparse.static.hex8(self.total_size)) + \
        microparse.static.fmt_string % ("Unknown 1", microparse.static.hex8(self.unknown1)) + \
        microparse.static.fmt_string % ("Unknown 2", microparse.static.hex8(self.unknown2)) + \
        microparse.static.fmt_string % ("Unknown 3", microparse.static.hex8(self.unknown3))

        if self.is_data_extended:
            output += \
            microparse.static.fmt_string % ("Data Unknown 1", microparse.static.hex8(self.data_unknown1)) + \
            microparse.static.fmt_string % ("Data Unknown 2", microparse.static.hex8(self.data_unknown2)) + \
            microparse.static.fmt_string % ("Data Unknown 3", microparse.static.hex8(self.data_unknown3)) + \
            microparse.static.fmt_string % ("Data Revision", microparse.static.hex8(self.data_revision)) + \
            microparse.static.fmt_string % ("Data Unknown 4", microparse.static.hex8(self.data_unknown4)) + \
            microparse.static.fmt_string % ("Data Unknown 5", microparse.static.hex8(self.data_unknown5)) + \
            microparse.static.fmt_string % ("Data Date", microparse.static.int2date(self.data_date)) + \
            microparse.static.fmt_string % ("Data Length", microparse.static.hex8(self.data_length)) + \
            microparse.static.fmt_string % ("Data Unknown 6", microparse.static.hex8(self.data_unknown6)) + \
            microparse.static.fmt_string % ("Data Processor Signature", microparse.static.hex8(self.data_processor_signature)) + \
            str(microparse.signature(self.data_processor_signature)) + \
            microparse.static.fmt_string % ("Data Unknown 7", microparse.static.hex8(self.data_unknown7)) + \
            microparse.static.fmt_string % ("Data Unknown 8", microparse.static.hex8(self.data_unknown8)) + \
            microparse.static.fmt_string % ("Data Unknown 9", microparse.static.hex8(self.data_unknown9)) + \
            microparse.static.fmt_string % ("Data Unknown 10", microparse.static.hex8(self.data_unknown10)) + \
            microparse.static.fmt_string % ("Data Unknown 11", microparse.static.hex8(self.data_unknown11)) + \
            microparse.static.fmt_string % ("Data Unknown 12", microparse.static.hex8(self.data_unknown12)) + \
            microparse.static.fmt_string % ("Data Unknown 13", microparse.static.hex8(self.data_unknown13)) + \
            microparse.static.fmt_string % ("Data Unknown 14", microparse.static.hex8(self.data_unknown14)) + \
            microparse.static.fmt_string % ("Data Unknown 15", microparse.static.hex8(self.data_unknown15)) + \
            microparse.static.fmt_string % ("Data Unknown 16", microparse.static.hex8(self.data_unknown16)) + \
            microparse.static.fmt_string % ("Data Unknown 17", microparse.static.hex8(self.data_unknown17)) + \
            microparse.static.fmt_string % ("Data Unknown 18", microparse.static.hex8(self.data_unknown18)) + \
            microparse.static.fmt_string % ("Data Unknown 19", microparse.static.hex8(self.data_unknown19)) + \
            microparse.static.fmt_string % ("Data Unknown 20", microparse.static.hex8(self.data_unknown20))

        if self.is_extended:
            checksum2 = " (!)" if self.extended_checksum != self.calculate_extended_table_checksum() else ""

            output += \
            microparse.static.fmt_string % ("Extended Signature Count", microparse.static.hex8(self.extended_signature_count)) + \
            microparse.static.fmt_string % ("Extended Checksum", microparse.static.hex8(self.extended_checksum) + checksum2) + \
            microparse.static.fmt_string % ("Unknown 4", microparse.static.hex8(self.unknown4)) + \
            microparse.static.fmt_string % ("Unknown 5", microparse.static.hex8(self.unknown5)) + \
            microparse.static.fmt_string % ("Unknown 6", microparse.static.hex8(self.unknown6))

        return output
