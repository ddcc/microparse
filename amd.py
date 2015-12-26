#! /usr/bin/env python3

import microparse
import struct

# http://review.coreboot.org/gitweb?p=coreboot.git;a=blob;f=src/cpu/amd/microcode/microcode.c;hb=HEAD
# http://lxr.free-electrons.com/source/arch/x86/include/asm/microcode_amd.h
# http://lxr.free-electrons.com/source/arch/x86/kernel/microcode_amd.c
# http://lxr.free-electrons.com/source/arch/x86/kernel/microcode_amd_early.c

class static():
    # multiplier for patch_data_len
    TRIAD_SIZE = 7
    F1X_MAX_SIZE = 2048
    F14_MAX_SIZE = 1824
    F15_MAX_SIZE = 4096

    fmt_string = "-- %-27s: %s\n"

    def container_header(swap_endian):
        if swap_endian:
            return struct.Struct(">4sII")
        else:
            return struct.Struct("<4sII")

    def container_equiv(swap_endian):
        if swap_endian:
            return struct.Struct(">IIIHH")
        else:
            return struct.Struct("<IIIHH")

    def container_preheader(swap_endian):
        if swap_endian:
            return struct.Struct(">II")
        else:
            return struct.Struct("<II")

    def header(swap_endian):
        if swap_endian:
            return struct.Struct(">IIHBBIIIHBBBBBBIIIIIIII")
        else:
            return struct.Struct("<IIHBBIIIHBBBBBBIIIIIIII")

class container():
    def __init__(self, data, swap_endian):
        self.is_swap_endian = swap_endian

        self.parse_header(data[0 : static.container_header(self.is_swap_endian).size])
        self.parse_equivalent_cpu(data[static.container_header(self.is_swap_endian).size : static.container_header(self.is_swap_endian).size + self.equiv_size])
        self.parse_microcodes(data[static.container_header(self.is_swap_endian).size + self.equiv_size : ])
       
        self.raw = data

    def csv(self):
        output = ""
        for entry in self.equiv_cpu:
            output += \
            microparse.static.hex8(entry[0]) + "," + \
            microparse.static.hex8(entry[1]) + "," + \
            microparse.static.hex8(entry[2]) + "," + \
            microparse.static.hex8(entry[3]) + "," + \
            microparse.static.hex8(entry[4]) + "\n"

        for microcode in self.microcodes:
            output += microcode.csv()

        return output

    def size(self):
        size = static.container_header(self.is_swap_endian).size + self.equiv_size

        for p in self.preheaders:
            size += static.container_preheader(self.is_swap_endian).size + p[1]

        return size

    def parse_header(self, data):
        if len(data) == static.container_header(self.is_swap_endian).size:
            try:
                header = static.container_header(self.is_swap_endian).unpack(data)
            except struct.error:
                raise Exception("Cannot unpack microcode container header!")

            self.magic = header[0]
            if self.magic != b"DMA\x00":
                raise Exception("Input microcode container magic string mismatch!")
            self.cpu_table_type = header[1]
            if self.cpu_table_type != 0:
                raise Exception("Unexpected CPU equivalence table type!")
            self.equiv_size = header[2]
        else:
            raise Exception("Input microcode container header size mismatch!")

    def parse_equivalent_cpu(self, data):
        self.equiv_cpu = []
        self.equiv_cpuid = dict()

        if len(data) == self.equiv_size:
            for i in range(0, self.equiv_size, static.container_equiv(self.is_swap_endian).size):
                try:
                    equiv = static.container_equiv(self.is_swap_endian).unpack(data[i : i + static.container_equiv(self.is_swap_endian).size])
                except struct.error:
                    raise Exception("Cannot unpack CPU equivalence table!")

                # skip the zero entry that marks end of the table
                if equiv[0] != 0:
                    self.equiv_cpu.append((equiv[0], equiv[1], equiv[2], equiv[3], equiv[4]))

                    # generate mapping table from processor revision id to cpuid (processor signature)
                    if equiv[3] in self.equiv_cpuid:
                        self.equiv_cpuid[equiv[3]].append(equiv[0])
                    else:
                        self.equiv_cpuid[equiv[3]] = [equiv[0]]
        else:
            raise Exception("Input CPU equivalence table size mismatch!")

    def parse_microcodes(self, data):
        offset = 0
        self.preheaders = []
        self.microcodes = []

        while offset < len(data):
            if offset + static.container_preheader(self.is_swap_endian).size < len(data):
                try:
                    # type, size
                    preheader = static.container_preheader(self.is_swap_endian).unpack(data[offset : offset + static.container_preheader(self.is_swap_endian).size])
                except struct.error:
                    raise Exception("Cannot unpack preheader!")

                if preheader[0] != 1:
                    raise Exception("Unexpected microcode preheader type!")

                self.preheaders.append(preheader)
            else:
                raise Exception("Input preheader block size mismatch!")

            m = microcode(data[offset + static.container_preheader(self.is_swap_endian).size : offset + static.container_preheader(self.is_swap_endian).size + preheader[1]], self.equiv_cpuid, preheader[1], self.is_swap_endian)
            self.microcodes.append(m)

            offset += static.container_preheader(self.is_swap_endian).size + m.size()

    def __str__(self):
        output = \
        microparse.static.fmt_string % ("Container Magic: ", self.magic) + \
        microparse.static.fmt_string % ("Container Table Type: ", microparse.static.hex8(self.cpu_table_type)) + \
        microparse.static.fmt_string % ("Container Table Size: ", microparse.static.hex8(self.equiv_size)) + \
        microparse.static.fmt_string % ("Container Processor Signature Table", "")

        for entry in self.equiv_cpu:
            output += \
            static.fmt_string % ("Processor Signature: ", microparse.static.hex8(entry[0])) + \
            static.fmt_string % ("Errata Mask: ", microparse.static.hex8(entry[1])) + \
            static.fmt_string % ("Errata Compare: ", microparse.static.hex8(entry[2])) + \
            static.fmt_string % ("Processor Revision ID: ", microparse.static.hex8(entry[3])) + \
            static.fmt_string % ("Unknown: ", microparse.static.hex8(entry[4])) + "\n"
            #str(microparse.signature(entry[0]))

        if (len(self.preheaders) != len(self.microcodes)):
            raise Exception("Input preheaders and microcodes size mismatch!")

        for i in range(0, len(self.microcodes)):
            output += \
            microparse.static.fmt_string % ("Microcode Type: ", microparse.static.hex8(self.preheaders[i][0])) + \
            microparse.static.fmt_string % ("Microcode Size: ", microparse.static.hex8(self.preheaders[i][1])) + \
            str(self.microcodes[i])

        return output

class microcode():
    def __init__(self, data, equiv_cpuid, size, swap_endian):
        self.is_swap_endian = swap_endian

        # mapping table generated earlier
        self.equiv_cpuid = equiv_cpuid
        self.total_size = size

        self.parse_header(data[0 : static.header(self.is_swap_endian).size])
        
        if (self.total_size != 0):
            self.parse_data(data[static.header(self.is_swap_endian).size : self.total_size])
            self.raw = data[0 : self.total_size]
        else:
            # don't both parsing data, since we can't calculate checksum for encrypted microcode anyway
            self.total_size = len(data)

            self.data = []
            self.raw = data[0 : ]

    def csv(self):
        return \
        microparse.static.int2date(self.date) + "," + \
        microparse.static.hex8(self.patch_id) + "," + \
        microparse.static.hex8(self.patch_data_id) + "," + \
        microparse.static.hex8(self.patch_data_len) + "," + \
        microparse.static.hex8(self.init_flag) + "," + \
        microparse.static.hex8(self.patch_data_checksum) + "," + \
        microparse.static.hex8(self.nb_dev_id) + "," + \
        microparse.static.hex8(self.sb_dev_id) + "," + \
        microparse.static.hex8(self.processor_rev_id) + "," + \
        microparse.static.hex8(self.nb_rev_id) + "," + \
        microparse.static.hex8(self.sb_rev_id) + "," + \
        microparse.static.hex8(self.bios_api_rev) + "," + \
        microparse.static.hex8(self.unknown1) + "," + \
        microparse.static.hex8(self.unknown2) + "," + \
        microparse.static.hex8(self.unknown3) + "," + \
        microparse.static.hex8(self.match_reg1) + "," + \
        microparse.static.hex8(self.match_reg2) + "," + \
        microparse.static.hex8(self.match_reg3) + "," + \
        microparse.static.hex8(self.match_reg4) + "," + \
        microparse.static.hex8(self.match_reg5) + "," + \
        microparse.static.hex8(self.match_reg6) + "," + \
        microparse.static.hex8(self.match_reg7) + "," + \
        microparse.static.hex8(self.match_reg8) + "\n"

    def filename(self):
        return microparse.static.hex8(self.processor_rev_id) + "_" + microparse.static.hex8(self.patch_id) + "_" + microparse.static.hex8(self.patch_data_checksum)

    def size(self):
        return self.total_size

    def parse_header(self, data):
        if len(data) == static.header(self.is_swap_endian).size:
            try:
                header = static.header(self.is_swap_endian).unpack(data)
            except struct.error:
                raise Exception("Cannot unpack microcode header!")

            self.date = header[0]
            self.patch_id = header[1]
            self.patch_data_id = header[2]
            self.patch_data_len = header[3]
            # attempt to compute total size, will fail for newer encrypted microcode with patch_data_len = 0
            # if self.total_size == 0 and self.patch_data_len != 0:
            #     self.total_size = static.header(self.is_swap_endian).size + self.patch_data_len * microparse.static.data(self.is_swap_endian).size * static.TRIAD_SIZE
            self.init_flag = header[4]
            self.patch_data_checksum = header[5]
            self.nb_dev_id = header[6]
            self.sb_dev_id = header[7]
            self.processor_rev_id = header[8]
            if (self.equiv_cpuid):
                for s in self.equiv_cpuid[self.processor_rev_id]:
                    signature = microparse.signature(s)
                    if (signature.family == 0xe and self.total_size > static.F14_MAX_SIZE) \
                    or (signature.family == 0xf and self.total_size > static.F15_MAX_SIZE) \
                    or ((signature.family != 0xe and signature.family != 0xf) and self.total_size > static.F1X_MAX_SIZE):
                        raise Exception("Microcode exceeds maximum valid size")

            self.nb_rev_id = header[9]
            self.sb_rev_id = header[10]
            self.bios_api_rev = header[11]
            self.unknown1 = header[12]
            self.unknown2 = header[13]
            self.unknown3 = header[14]
            self.match_reg1 = header[15]
            self.match_reg2 = header[16]
            self.match_reg3 = header[17]
            self.match_reg4 = header[18]
            self.match_reg5 = header[19]
            self.match_reg6 = header[20]
            self.match_reg7 = header[21]
            self.match_reg8 = header[22]
        else:
            raise Exception("Input microcode header size mismatch!")

    def parse_data(self, data):
        self.data = []

        if len(data) == self.total_size - static.header(self.is_swap_endian).size:
            for i in range(0, self.total_size - static.header(self.is_swap_endian).size, microparse.static.data(self.is_swap_endian).size):
                try:
                    self.data.append(microparse.static.data(self.is_swap_endian).unpack(data[i : i + microparse.static.data(self.is_swap_endian).size])[0])
                except struct.error:
                    raise Exception("Cannot unpack microcode data!")
        else:
            raise Exception("Input microcode data size mismatch!")

    def calculate_checksum(self):
        return (sum(self.data) & 0xFFFFFFFF) if self.data else 0

    def __str__(self):
        fmt_string = ".... %-25s: %s\n"
        checksum = " (!)" if self.patch_data_checksum != self.calculate_checksum() else ""

        output = \
        microparse.static.fmt_string % ("Date", microparse.static.int2date(self.date)) + \
        microparse.static.fmt_string % ("Patch ID", microparse.static.hex8(self.patch_id)) + \
        microparse.static.fmt_string % ("Patch Data ID", microparse.static.hex8(self.patch_data_id)) + \
        microparse.static.fmt_string % ("Patch Data Length", microparse.static.hex8(self.patch_data_len)) + \
        microparse.static.fmt_string % ("Initialization Flag", microparse.static.hex8(self.init_flag)) + \
        microparse.static.fmt_string % ("Patch Data Checksum", microparse.static.hex8(self.patch_data_checksum) + checksum) + \
        microparse.static.fmt_string % ("Northbridge Device ID", microparse.static.hex8(self.nb_dev_id)) + \
        microparse.static.fmt_string % ("Southbridge Device ID", microparse.static.hex8(self.sb_dev_id)) + \
        microparse.static.fmt_string % ("Processor Revision ID", microparse.static.hex8(self.processor_rev_id))

        if (self.equiv_cpuid):
            for s in self.equiv_cpuid[self.processor_rev_id]:
                output += \
                microparse.signature.fmt_string % ("Processor Signature Entry", microparse.static.hex8(s)) + \
                str(microparse.signature(s))

        output += \
        microparse.static.fmt_string % ("Northbridge Revision ID", microparse.static.hex8(self.nb_rev_id)) + \
        microparse.static.fmt_string % ("Southbridge Revision ID", microparse.static.hex8(self.sb_rev_id)) + \
        microparse.static.fmt_string % ("BIOS API Revision", microparse.static.hex8(self.bios_api_rev)) + \
        microparse.static.fmt_string % ("Unknown 1", microparse.static.hex8(self.unknown1)) + \
        microparse.static.fmt_string % ("Unknown 2", microparse.static.hex8(self.unknown2)) + \
        microparse.static.fmt_string % ("Unknown 3", microparse.static.hex8(self.unknown3)) + \
        microparse.static.fmt_string % ("Match Register 1", microparse.static.hex8(self.match_reg1)) + \
        microparse.static.fmt_string % ("Match Register 2", microparse.static.hex8(self.match_reg2)) + \
        microparse.static.fmt_string % ("Match Register 3", microparse.static.hex8(self.match_reg3)) + \
        microparse.static.fmt_string % ("Match Register 4", microparse.static.hex8(self.match_reg4)) + \
        microparse.static.fmt_string % ("Match Register 5", microparse.static.hex8(self.match_reg5)) + \
        microparse.static.fmt_string % ("Match Register 6", microparse.static.hex8(self.match_reg6)) + \
        microparse.static.fmt_string % ("Match Register 7", microparse.static.hex8(self.match_reg7)) + \
        microparse.static.fmt_string % ("Match Register 8", microparse.static.hex8(self.match_reg8)) + "\n"

        return output
