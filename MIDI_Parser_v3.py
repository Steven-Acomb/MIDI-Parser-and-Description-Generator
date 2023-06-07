from tkinter import filedialog

__author__ = "Stephen Acomb"
__license__ = "GPL"
__version__ = "3"
__maintainer__ = "Stephen Acomb"
__email__ = "acomb.stephen@gmail.com"

class MidiFile:

    def __init__(self):
        filetypes = (("MIDI files", "*.mid"), ("All files", "*.*"))
        self.file_name = filedialog.askopenfilename(filetypes=filetypes)
        with open(self.file_name, mode='rb') as file:
            self.file_content = file.read()
        if self.file_name is None:
            return
        # print("Opened file \"" + str(self.file_name) + "\"")
        self.midi_hex = self.file_content.hex()
        self.chunks = divide_chunks(self.midi_hex)
        for chunk in self.chunks:
            chunk.parse()
    
    def to_block_format_txt(self):
        name = filedialog.asksaveasfile(mode='w',defaultextension=".txt", initialfile = str(self.file_name)[:len(str(self.file_name))-4]+".txt").name
        if name is None:
            return
        with open(name, 'w', encoding="utf-8") as f:
            f.write(self.__str__())
        f.close()
        print("Saved block format of \""+ str(self.file_name) + "\" to file \"" + str(name) + "\".")

    def to_tabular_format_csv(self):
        name = filedialog.asksaveasfile(mode='w',defaultextension=".csv", initialfile = str(self.file_name)[:len(str(self.file_name))-4]+".csv").name
        if name is None:
            return
        with open(name, 'w', encoding="utf-8") as f:
            f.write("%s,%s,%s\n"%('Byte Offset','Description','Value'))
            for chunk in self.chunks:
                for chunk_data in chunk.chunk_data:
                    f.write(chunk_data.to_tabular_string(',') + "\n")
        f.close()
        print("Saved tabular format of \""+ str(self.file_name) + "\" to file \"" + str(name) + "\".")

    def to_tabular_str(self):
        str_out = "Byte Offset" + "\t\t" + "Description" + "\t\t" + "Value" + "\n"
        for chunk in self.chunks:
            for chunk_data in chunk.chunk_data:
                    str_out = str_out + chunk_data.to_tabular_string('\t\t') + "\n"
        return str_out

    def __str__(self):
        str_out = "Midi File:" + "\n"
        for chunk in self.chunks:
            str_out += str(chunk) + "\n"
        return str_out

class Chunk:
    def __init__(self, bytes_remaining, hex_bytes):
        self.bytes_remaining = bytes_remaining
        self.hex_bytes = hex_bytes
        self.chunk_data = []

class HeaderChunk(Chunk):
    def __init__(self, bytes_remaining, hex_bytes, byte_offset):
        super().__init__(bytes_remaining, hex_bytes)
        self.byte_offset = byte_offset
        self.format = None
        self.track_count = None
        self.division = None

    def parse(self):
        self.chunk_data.append(ChunkID('4d546864', self.byte_offset+0, '\'MThd\''))
        self.chunk_data.append(ChunkBytesRemaining(self.hex_bytes[8:16], self.byte_offset+4, self.bytes_remaining))
        
        self.format = int("0x"+self.hex_bytes[16:20],16)
        self.chunk_data.append(MidiFileFormat(self.hex_bytes[16:20], self.byte_offset+4+4, str(self.format)))
        
        self.track_count = int("0x"+self.hex_bytes[20:24],16)
        self.chunk_data.append(TrackCount(self.hex_bytes[20:24], self.byte_offset+4+4+2, str(self.track_count)))
        
        self.division = 500000 if self.bytes_remaining == 0 else int("0x"+self.hex_bytes[24:],16)
        self.chunk_data.append(Division(self.hex_bytes[24:], self.byte_offset+4+4+2+2, str(self.division)))

    def __str__(self):
        str_out = "Header Chunk"
        # str_out = self.hex_bytes + "\nHeader Chunk"
        str_out += "\n\t" + "Bytes Left: " + str(self.bytes_remaining)
        str_out += "\n\t" + "Format: " + str(self.format)
        str_out += "\n\t" + "Track Count: " + str(self.track_count)
        str_out += "\n\t" + "Division: " + str(self.division)
        return str_out

class TrackChunk(Chunk):
    def __init__(self, bytes_remaining, hex_bytes, byte_offset):
        super().__init__(bytes_remaining, hex_bytes)
        self.byte_offset = byte_offset
        self.delta_times = []
        self.events = []
        self.running_status = None

    def parse(self):
        self.chunk_data.append(ChunkID('4d54726b', self.byte_offset+0, '\'MTrk\''))
        self.chunk_data.append(ChunkBytesRemaining(self.hex_bytes[8:16], self.byte_offset+4, self.bytes_remaining))
        self.process(self.hex_bytes[16:])
    

    def process(self, hex_left):
        current_offset = self.byte_offset+4+4
        while len(hex_left) > 0:
            dt_len = vlf_len(hex_left)
            
            dt_val = int(parse_vlf(hex_left[0:2*dt_len]),16)
            self.delta_times.append(dt_val)
            self.chunk_data.append(DeltaTime(self.hex_bytes[2*current_offset:2*(current_offset+dt_len)], current_offset, dt_val))
            current_offset = current_offset + dt_len
            hex_left = hex_left[2*dt_len:]

            status_offset = 1
            if int(hex_left[0],16) < 8:
                status = self.running_status
                status_offset = 0
            else:
                status = hex_left[0:2]
                self.running_status = status
            
            message_length = 0

            if status[0] == "8":
                message_length += 2
            elif status[0] == "9":
                message_length += 2
            elif status[0] == "a":
                message_length += 2
            elif status[0] == "b":
                message_length += 2
            elif status[0] == "c":
                message_length += 1
            elif status[0] == "d":
                message_length += 1
            elif status[0] == "e":
                message_length += 2
            elif status == "f1":
                message_length += 1
            elif status == "f2":
                message_length += 2
            elif status == "f3":
                message_length += 1
            elif status == "f6":
                message_length += 0
            elif status == "f8":
                message_length += 0
            elif status == "fA":
                message_length += 0
            elif status == "fB":
                message_length += 0
            elif status == "fC":
                message_length += 0
            elif status == "f0":
                message_length += system_exclusive_len(hex_left[2*status_offset:])
            elif status == "ff":
                message_length += meta_len(hex_left[2*status_offset:])
            
            # print("message_length = " +str(message_length) + " bytes.")
            # event = Event(status, hex_left[2*status_offset:2*(message_length+status_offset)], message_length)
            current_offset = current_offset + message_length + status_offset
            event = classify_event(status, hex_left[2*status_offset:2*(message_length+status_offset)], message_length, current_offset)
            self.events.append(event)
            self.chunk_data.append(event)
            hex_left = hex_left[2*(message_length+status_offset):]

    def __str__(self):
        str_out = "Track Chunk"
        # str_out = self.hex_bytes + "\nTrack Chunk"
        str_out += "\n\t" + "Bytes Left: " + str(self.bytes_remaining)
        for k in range(len(self.delta_times)):
            str_out += "\n\tDelta Time = " + str(self.delta_times[k])
            str_out += str(self.events[k])
        return str_out

class ChunkData():
    def __init__(self, hex_bytes, byte_offset, description, value):
        self.hex_bytes = hex_bytes
        self.byte_offset = byte_offset
        self.description = description
        self.value = value
    
    def to_tabular_string(self, spacer):
        if spacer == ",":
            str_out = hex(self.byte_offset) + spacer + self.description.replace(',', '(comma)') + spacer + str(self.value).replace(',', '(comma)')
        else:
            str_out = hex(self.byte_offset) + spacer + self.description + spacer + str(self.value)
        return str_out

class ChunkID(ChunkData):
    def __init__(self, hex_bytes, byte_offset, value):
        description = "Chunk ID"
        super().__init__(hex_bytes, byte_offset, description, value)

class ChunkBytesRemaining(ChunkData):
    def __init__(self, hex_bytes, byte_offset, bytes_remaining):
        description = 'Bytes Remaining'
        value = str(bytes_remaining)
        super().__init__(hex_bytes, byte_offset, description, value)

class MidiFileFormat(ChunkData):
    def __init__(self, hex_bytes, byte_offset, value):
        description = 'File format type'
        super().__init__(hex_bytes, byte_offset, description, value)

class TrackCount(ChunkData):
    def __init__(self, hex_bytes, byte_offset, value):
        description = 'Number of tracks'
        super().__init__(hex_bytes, byte_offset, description, value)

class Division(ChunkData):
    def __init__(self, hex_bytes, byte_offset, value):
        description = 'Division'
        value = str(value) + " ticks per quarter note"
        super().__init__(hex_bytes, byte_offset, description, value)

class DeltaTime(ChunkData):
    def __init__(self, hex_bytes, byte_offset, value):
        description = 'Delta Time'
        value = str(value)
        super().__init__(hex_bytes, byte_offset, description, value)

class Event(ChunkData):
    def __init__(self, status, hex_bytes, bytes_remaining, byte_offset):
        description = status
        super().__init__(hex_bytes, byte_offset, description, "-")
        self.status = status
        self.bytes_remaining = bytes_remaining
        # print("\ncreated event with:\nstatus = "+ status + "\nhex_bytes = " + hex_bytes + "\nbytes_remaining = " + str(bytes_remaining))

    def __str__(self):
        str_out = "\n\tEvent"
        str_out += "\n\t\tStatus = " + self.status
        str_out += "\n\t\thex_bytes = " + self.hex_bytes
        str_out += "\n\t\tbytes_remaining = " + str(self.bytes_remaining)
        return str_out


# Superclass for Message Events
class MessageEvent(Event):
    def __init__(self, status, hex_bytes, bytes_remaining, byte_offset):
        super().__init__(status, hex_bytes, bytes_remaining, byte_offset)

    def __str__(self):
        str_out = "\n\tMessage"
        str_out += "\n\t\tStatus = " + self.status
        str_out += "\n\t\thex_bytes = " + self.hex_bytes
        str_out += "\n\t\tbytes_remaining = " + str(self.bytes_remaining)
        return str_out

# status = 0x8n
class NoteOffEvent(MessageEvent):
    def __init__(self, channel, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Note Off", hex_bytes, bytes_remaining, byte_offset)
        self.channel = channel
        self.note = decode_note_number(hex_bytes[0:2])
        self.velocity = int(hex_bytes[2:],16)
        self.value = "Channel = " + str(self.channel) + "; Note = " + self.note + "; Velocity = " + str(self.velocity)
    def __str__(self):
        # str_out = super().__str__()
        str_out = "\n\tMessage"
        str_out += "\n\t\t" + self.status
        str_out += "\n\t\t\tChannel = " + str(self.channel)
        str_out += "\n\t\t\tNote = " + self.note
        str_out += "\n\t\t\tVelocity = " + str(self.velocity)    
        return str_out

# status = 0x9n
class NoteOnEvent(MessageEvent):
    def __init__(self, channel, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Note On", hex_bytes, bytes_remaining, byte_offset)
        self.channel = channel
        self.note = decode_note_number(hex_bytes[0:2])
        self.velocity = int(hex_bytes[2:],16)
        self.value = "Channel = " + str(self.channel) + "; Note = " + self.note + "; Velocity = " + str(self.velocity)
    def __str__(self):
        # str_out = super().__str__()
        str_out = "\n\tMessage"
        str_out += "\n\t\t" + self.status
        str_out += "\n\t\t\tChannel = " + str(self.channel)
        str_out += "\n\t\t\tNote = " + self.note
        str_out += "\n\t\t\tVelocity = " + str(self.velocity)
        return str_out

# status = 0xan
class PolyphonicAftertouchEvent(MessageEvent):
    def __init__(self, channel, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Polyphonic Aftertouch", hex_bytes, bytes_remaining, byte_offset)
        self.channel = channel
        self.note = decode_note_number(hex_bytes[0:2])
        self.pressure = int(hex_bytes[2:],16)
        self.value = "Channel = " + str(self.channel) + "; Note = " + self.note + "; Pressure = " + str(self.pressure)
    def __str__(self):
        # str_out = super().__str__()
        str_out = "\n\tMessage"
        str_out += "\n\t\t" + self.status
        str_out += "\n\t\t\tChannel = " + str(self.channel)
        str_out += "\n\t\t\tNote = " + self.note
        str_out += "\n\t\t\tPressure = " + str(self.pressure)
        return str_out

# status = 0xbn
class ControlChangeEvent(MessageEvent):
    def __init__(self, channel, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Control Change", hex_bytes, bytes_remaining, byte_offset)
        self.channel = channel
        self.controller_number = int(hex_bytes[0:2],16)
        self.controller = decode_controller_number(hex_bytes[0:2])
        self.data = hex_bytes[2:]
        self.value = "Channel = " + str(self.channel) + "; Controller Number = " + str(self.controller_number) + "; Controller = " + str(self.controller) + "; Data = " + str(self.data)
    def __str__(self):
        # str_out = super().__str__()
        str_out = "\n\tMessage"
        str_out += "\n\t\t" + self.status
        str_out += "\n\t\t\tChannel = " + str(self.channel)
        str_out += "\n\t\t\tController Number = " + str(self.controller_number)
        str_out += "\n\t\t\tController = " + self.controller
        str_out += "\n\t\t\tData = " + self.data
        return str_out

# status = 0xcn
class ProgramChangeEvent(MessageEvent):
    def __init__(self, channel, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Program Change", hex_bytes, bytes_remaining, byte_offset)
        self.channel = channel
        self.program_number = hex_bytes
        self.sound_type = decode_program_number(hex_bytes[0:])
        self.value = "Channel = " + str(self.channel) + "; Program Number = " + self.program_number + "; Sound Type = " + str(self.sound_type)
    def __str__(self):
        # str_out = super().__str__()
        str_out = "\n\tMessage"
        str_out += "\n\t\t" + self.status
        str_out += "\n\t\t\tChannel = " + str(self.channel)
        str_out += "\n\t\t\tProgram Number = " + str(self.program_number)
        str_out += "\n\t\t\tSound Type = " + self.sound_type
        return str_out

# status = 0xdn
class ChannelAftertouchEvent(MessageEvent):
    def __init__(self, channel, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Channel Aftertouch", hex_bytes, bytes_remaining, byte_offset)
        self.channel = channel
        self.pressure = int(hex_bytes,16)
        self.value = "Channel = " + str(self.channel) + "; Pressure = " + str(self.pressure)
    def __str__(self):
        # str_out = super().__str__()
        str_out = "\n\tMessage"
        str_out += "\n\t\t" + self.status
        str_out += "\n\t\t\tChannel = " + str(self.channel)
        str_out += "\n\t\t\tPressure = " + str(self.pressure)
        return str_out

# status = 0xen
class PitchWheelEvent(MessageEvent):
    def __init__(self, channel, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Pitch Wheel", hex_bytes, bytes_remaining, byte_offset)
        self.channel = channel
        self.ls_byte = hex_bytes[0:2]
        self.ms_byte = hex_bytes[2:]
        self.value = "Channel = " + str(self.channel) + "; LS Byte = " + self.ls_byte + "; MS Byte = " + str(self.ms_byte)
    def __str__(self):
        # str_out = super().__str__()
        str_out = "\n\tMessage"
        str_out += "\n\t\t" + self.status
        str_out += "\n\t\t\tChannel = " + str(self.channel)
        str_out += "\n\t\t\tLS Byte = " + self.ls_byte
        str_out += "\n\t\t\tMS Byte = " + self.ms_byte
        return str_out

# # Superclass for System Events
class SystemEvent(Event):
    def __init__(self, status, hex_bytes, bytes_remaining, byte_offset):
        super().__init__(status, hex_bytes, bytes_remaining, byte_offset)
    def __str__(self):
        str_out = "\n\tSystem Event"
        str_out += "\n\t\tStatus = " + self.status
        str_out += "\n\t\thex_bytes = " + self.hex_bytes
        str_out += "\n\t\tbytes_remaining = " + str(self.bytes_remaining)
        return str_out

# Superclass for System Exclusive Events
class SystemExclusiveEvent(SystemEvent):
    def __init__(self, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("System Exclusive", hex_bytes, bytes_remaining, byte_offset)
        self.manufacturer_id = int(hex_bytes[0:2],16)
        self.data = hex_bytes[2:2*(bytes_remaining-1)]
        try:
            self.data_as_utf8 = bytes.fromhex(self.data).decode('utf-8')
        except:
            self.data_as_utf8 = "N/A - data is not a properly formatted utf-8 string."
        self.value = "Manufacturer ID = " + str(self.manufacturer_id) + "; Data = " + self.data + "; Data as utf-8 = " + str(self.data_as_utf8)
    def __str__(self):
        str_out = "\n\tSystem Exclusive Event"
        str_out += "\n\t\tManufacturer ID = " + str(self.manufacturer_id)
        str_out += "\n\t\tData = " + self.data
        str_out += "\n\t\tData as utf-8 = " + self.data_as_utf8
        return str_out

# Superclass for System Common Events
class SystemCommonEvent(SystemEvent):
    def __init__(self, status, hex_bytes, bytes_remaining, byte_offset):
        super().__init__(status, hex_bytes, bytes_remaining, byte_offset)
    def __str__(self):
        str_out = "\n\tSystem Common Event"
        str_out += "\n\t\tStatus = " + self.status
        str_out += "\n\t\thex_bytes = " + self.hex_bytes
        str_out += "\n\t\tbytes_remaining = " + str(self.bytes_remaining)
        return str_out

# status = 0xf1
class QuarterFrameEvent(SystemCommonEvent):
    def __init__(self, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Quarter Frame", hex_bytes, bytes_remaining, byte_offset)
        self.data = hex_bytes
        self.value = "Data = " + self.data
    def __str__(self):
        str_out = "\n\tSystem Common Event"
        str_out += "\n\t\tStatus = " + self.status
        str_out += "\n\t\tData = " + self.data
        return str_out

# status = 0xf2
class SongPointerEvent(SystemCommonEvent):
    def __init__(self, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Song Pointer", hex_bytes, bytes_remaining, byte_offset)
        self.ls_byte = hex_bytes[0:2]
        self.ms_byte = hex_bytes[2:]
        self.value = "LS Byte = " + self.ls_byte + "; MS Byte = " + str(self.ms_byte)
    def __str__(self):
        str_out = "\n\tSystem Common Event"
        str_out += "\n\t\tStatus = " + self.status
        str_out += "\n\t\t\tLS Byte = " + self.ls_byte
        str_out += "\n\t\t\tMS Byte = " + self.ms_byte
        return str_out

# status = 0xf3
class SongSelectEvent(SystemCommonEvent):
    def __init__(self, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Song Select", hex_bytes, bytes_remaining, byte_offset)
        self.song_number = int(hex_bytes,16)
        self.value = "Song Number = " + self.song_number
    def __str__(self):
        str_out = "\n\tSystem Common Event"
        str_out += "\n\t\tStatus = " + self.status
        str_out += "\n\t\t\tSong Number = " + str(self.song_number)
        return str_out

# status = 0xf6
class TuneRequestEvent(SystemCommonEvent):
    def __init__(self, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Tune Request", hex_bytes, bytes_remaining, byte_offset)
    def __str__(self):
        str_out = "\n\tSystem Common Event"
        str_out += "\n\t\tStatus = " + self.status
        return str_out

# Superclass for System Real Time Events
class SystemRealTimeEvent(SystemEvent):
    def __init__(self, status, hex_bytes, bytes_remaining, byte_offset):
        super().__init__(status, hex_bytes, bytes_remaining, byte_offset)
    def __str__(self):
        str_out = "\n\tSystem Real Time Event"
        str_out += "\n\t\tStatus = " + self.status
        return str_out

# status = 0xf8
class TimingClockEvent(SystemRealTimeEvent):
    def __init__(self, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Timing Clock", hex_bytes, bytes_remaining, byte_offset)

# status = 0xfa
class StartEvent(SystemRealTimeEvent):
    def __init__(self, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Start", hex_bytes, bytes_remaining, byte_offset)

# status = 0xfb
class ContinueEvent(SystemRealTimeEvent):
    def __init__(self, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Continue", hex_bytes, bytes_remaining, byte_offset)

# status = 0xfc
class StopEvent(SystemRealTimeEvent):
    def __init__(self, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Stop", hex_bytes, bytes_remaining, byte_offset)

# status = 0xfe
class ActiveSensingEvent(SystemRealTimeEvent):
    def __init__(self, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Active Sensing", hex_bytes, bytes_remaining, byte_offset)

# Superclass for Meta Events
class MetaEvent(Event):
    def __init__(self, meta_type, hex_bytes, bytes_remaining, byte_offset):
        super().__init__(meta_type, hex_bytes, bytes_remaining, byte_offset)
        self.meta_type = meta_type
    
    def __str__(self):
        str_out = "\n\tMeta Event"
        str_out += "\n\t\tMeta Type = " + self.meta_type
        str_out += "\n\t\thex_bytes = " + self.hex_bytes
        str_out += "\n\t\tbytes_remaining = " + str(self.bytes_remaining)
        return str_out


# meta_type = 0x00
class SequenceNumberEvent(MetaEvent):
    def __init__(self, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Sequence Number", hex_bytes, bytes_remaining, byte_offset)
        self.sequence_number = int(hex_bytes,16)
        self.value = "Sequence Number = " + str(self.sequence_number)
    def __str__(self):
        str_out = "\n\tMeta Event"
        str_out += "\n\t\tMeta Type = " + self.meta_type
        str_out += "\n\t\tSequence Number = " + str(self.sequence_number)
        return str_out

# meta_type = 0x01
class TextEvent(MetaEvent):
    def __init__(self, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Text", hex_bytes, bytes_remaining, byte_offset)
        self.text_as_utf8 = bytes.fromhex(hex_bytes).decode('utf-8')
        self.value = "Text = " + str(self.text_as_utf8)
    def __str__(self):
        str_out = "\n\tMeta Event"
        str_out += "\n\t\tMeta Type = " + self.meta_type
        str_out += "\n\t\tText = " + self.text_as_utf8
        return str_out

# meta_type = 0x02
class CopyrightNoticeEvent(MetaEvent):
    def __init__(self, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Copyright Notice", hex_bytes, bytes_remaining, byte_offset)
        self.notice_as_utf8 = bytes.fromhex(hex_bytes).decode('utf-8')
        self.value = "Copytight Notice = " + str(self.notice_as_utf8)
    def __str__(self):
        str_out = "\n\tMeta Event"
        str_out += "\n\t\tMeta Type = " + self.meta_type
        str_out += "\n\t\tCopytight Notice = " + self.notice_as_utf8
        return str_out

# meta_type = 0x03
class TrackNameEvent(MetaEvent):
    def __init__(self, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Track Name", hex_bytes, bytes_remaining, byte_offset)
        self.name_as_utf8 = bytes.fromhex(hex_bytes).decode('utf-8')
        self.value = "Track Name = " + str(self.name_as_utf8)
    def __str__(self):
        str_out = "\n\tMeta Event"
        str_out += "\n\t\tMeta Type = " + self.meta_type
        str_out += "\n\t\tTrack Name = " + self.name_as_utf8
        return str_out

# meta_type = 0x04
class InstrumentNameEvent(MetaEvent):
    def __init__(self, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Instrument Name", hex_bytes, bytes_remaining, byte_offset)
        self.name_as_utf8 = bytes.fromhex(hex_bytes).decode('utf-8')
        self.value = "Instrument Name = " + str(self.name_as_utf8)
    def __str__(self):
        str_out = "\n\tMeta Event"
        str_out += "\n\t\tMeta Type = " + self.meta_type
        str_out += "\n\t\tInstrument Name = " + self.name_as_utf8
        return str_out

# meta_type = 0x05
class LyricsEvent(MetaEvent):
    def __init__(self, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Lyrics", hex_bytes, bytes_remaining, byte_offset)
        self.lyrics_as_utf8 = bytes.fromhex(hex_bytes).decode('utf-8')
        self.value = "Lyrics = " + str(self.lyrics_as_utf8)
    def __str__(self):
        str_out = "\n\tMeta Event"
        str_out += "\n\t\tMeta Type = " + self.meta_type
        str_out += "\n\t\tLyrics = " + self.lyrics_as_utf8
        return str_out

# meta_type = 0x06
class MarkerEvent(MetaEvent):
    def __init__(self, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Marker", hex_bytes, bytes_remaining, byte_offset)
        self.marker_text_as_utf8 = bytes.fromhex(hex_bytes).decode('utf-8')
        self.value = "Marker Text = " + str(self.marker_text_as_utf8)
    def __str__(self):
        str_out = "\n\tMeta Event"
        str_out += "\n\t\tMeta Type = " + self.meta_type
        str_out += "\n\t\tMarker Text = " + self.marker_text_as_utf8
        return str_out

# meta_type = 0x07
class CuePointEvent(MetaEvent):
    def __init__(self, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Cue Point", hex_bytes, bytes_remaining, byte_offset)
        self.cue_point_text_as_utf8 = bytes.fromhex(hex_bytes).decode('utf-8')
        self.value = "Cue Point Text = " + str(self.cue_point_text_as_utf8)
    def __str__(self):
        str_out = "\n\tMeta Event"
        str_out += "\n\t\tMeta Type = " + self.meta_type
        str_out += "\n\t\tCue Point Text = " + self.cue_point_text_as_utf8
        return str_out 

# meta_type = 0x20
class ChannelPrefixEvent(MetaEvent):
    def __init__(self, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Channel Prefix", hex_bytes, bytes_remaining, byte_offset)
        self.channel = int(hex_bytes,16)
        self.value = "Channel = " + str(self.channel)
    def __str__(self):
        str_out = "\n\tMeta Event"
        str_out += "\n\t\tMeta Type = " + self.meta_type
        str_out += "\n\t\tChannel = " + str(self.channel)
        return str_out

# meta_type = 0x2f
class EndOfTrackEvent(MetaEvent):
    def __init__(self, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("End Of Track", hex_bytes, bytes_remaining, byte_offset)
    def __str__(self):
        str_out = "\n\tMeta Event"
        str_out += "\n\t\tMeta Type = " + self.meta_type
        return str_out

# meta_type = 0x51
class SetTempoEvent(MetaEvent):
    def __init__(self, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Set Tempo", hex_bytes, bytes_remaining, byte_offset)
        self.tempo = int(hex_bytes,16)
        self.value = "Tempo = " + str(self.tempo) + " us/beat"
    def __str__(self):
        str_out = "\n\tMeta Event"
        str_out += "\n\t\tMeta Type = " + self.meta_type
        str_out += "\n\t\tTempo = " + str(self.tempo) + " us/beat"
        return str_out

# meta_type = 0x54
class SMPTEOffsetEvent(MetaEvent):
    def __init__(self, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("SMPTE Offset", hex_bytes, bytes_remaining, byte_offset)
        self.offset = int(hex_bytes,16)
        self.value = "SMPTE Offset = " + str(self.offset)
    def __str__(self):
        str_out = "\n\tMeta Event"
        str_out += "\n\t\tMeta Type = " + self.meta_type
        str_out += "\n\t\tSMPTE Offset = " + str(self.offset)
        return str_out

# meta_type = 0x58
class TimeSignatureEvent(MetaEvent):
    def __init__(self, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Time Signature", hex_bytes, bytes_remaining, byte_offset)
        self.numerator = int(hex_bytes[0:2],16)
        self.denominator = 2**int(hex_bytes[2:4],16)
        self.metronome = int(hex_bytes[4:6],16)
        self.beat_size = int(hex_bytes[6:8],16)
        self.value = "Time Signature = " + str(self.numerator) + "/" + str(self.denominator) + " at " + str(self.denominator) + "clicks per midi clock; " + str(self.beat_size) + " 32nd notes per beat."

# meta_type = 0x59
class KeySignatureEvent(MetaEvent):
    def __init__(self, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Key Signature", hex_bytes, bytes_remaining, byte_offset)
        self.value = hex_bytes
        # TODO: Decode Key Signature.

# meta_type = 0x7f
class SequencerSpecificEvent(MetaEvent):
    def __init__(self, hex_bytes, bytes_remaining, byte_offset):
        super().__init__("Sequencer Specific", hex_bytes, bytes_remaining, byte_offset)
        try:
            self.data_as_utf8 = bytes.fromhex(self.hex_bytes).decode('utf-8')
        except:
            self.data_as_utf8 = "N/A - data is not a properly formatted utf-8 string."
        self.value = "Data = " + str(self.hex_bytes) + "; Data as utf-8 = " + str(self.data_as_utf8)
    def __str__(self):
        str_out = "\n\tMeta Event"
        str_out += "\n\t\tMeta Type = " + self.meta_type
        str_out += "\n\t\tData = " + self.hex_bytes
        str_out += "\n\t\tData as utf-8 = " + self.data_as_utf8
        return str_out


def divide_chunks(midi_hex):
    chunks = []
    chunk_start = 0

    while chunk_start < len(midi_hex):
        is_header = midi_hex[chunk_start+4:chunk_start+8] == "6864"
        bytes_remaining = int("0x"+midi_hex[chunk_start+8:chunk_start+16],16)
        next_chunk_start = chunk_start+16+2*bytes_remaining
        if is_header:
            chunks.append(HeaderChunk(bytes_remaining, midi_hex[chunk_start:next_chunk_start], chunk_start//2))
        else:
            chunks.append(TrackChunk(bytes_remaining, midi_hex[chunk_start:next_chunk_start], chunk_start//2))
        chunk_start = next_chunk_start
    
    return chunks

def vlf_len(hex_in):
    byte_count = 1
    while int(hex_in[(byte_count-1)*2],16) >= 8:
        byte_count += 1
    return byte_count

def parse_vlf(vlf_hex):
    bin_in = bin(int(vlf_hex, 16))[2:]
    bin_in = bin_in[::-1]
    bin_out = ""
    for k in range(len(bin_in)):
        if (k+1)%8 != 0:
            bin_out = bin_out + bin_in[k]
    bin_out = bin_out[::-1]
    hex_out = hex(int(bin_out,2))[2:]
    return hex_out


# Returns number of bytes in system message, excluding status
def system_exclusive_len(hex_in):
    byte_count = 1
    while hex_in[(byte_count-1)*2:(byte_count)*2] != "f7":
        byte_count += 1
    return byte_count

# Returns number of bytes in meta event, excluding status
def meta_len(hex_in):
    vlf_bytes = vlf_len(hex_in[2:])
    bytes_left = parse_vlf(hex_in[2:2+2*(vlf_bytes)])
    length = 1 + vlf_bytes + int(bytes_left,16)
    # print("\nmeta_len = " + str(length))
    return length

# Returns the appropriate type of event for the given input
def classify_event(status, hex_bytes, bytes_remaining, byte_offset):
    # self, status, hex_bytes, byte_offset, description, value, bytes_remaining
    if int(status[0],16) < int("f",16):
        return classify_message_event(status, hex_bytes, bytes_remaining, byte_offset)
    elif int(status[1],16) < int("f",16):
        return classify_system_event(status, hex_bytes, bytes_remaining, byte_offset)
    elif int(status[1],16) == int("f",16):
        return classify_meta_event(hex_bytes, bytes_remaining, byte_offset)
    return Event(status, hex_bytes, bytes_remaining, byte_offset)


def classify_message_event(status, hex_bytes, bytes_remaining, byte_offset):
    # self, status, hex_bytes, byte_offset, description, value, bytes_remaining
    channel = 1 + int(status[1],16)
    if status[0]  == "8":
        return NoteOffEvent(channel, hex_bytes, bytes_remaining, byte_offset)
    if status[0]  == "9":
        return NoteOnEvent(channel, hex_bytes, bytes_remaining, byte_offset)
    if status[0]  == "a":
        return PolyphonicAftertouchEvent(channel, hex_bytes, bytes_remaining, byte_offset)
    if status[0]  == "b":
        return ControlChangeEvent(channel, hex_bytes, bytes_remaining, byte_offset)
    if status[0]  == "c":
        return ProgramChangeEvent(channel, hex_bytes, bytes_remaining, byte_offset)
    if status[0]  == "d":
        return ChannelAftertouchEvent(channel, hex_bytes, bytes_remaining, byte_offset)
    if status[0]  == "e":
        return PitchWheelEvent(channel, hex_bytes, bytes_remaining, byte_offset)
    return MessageEvent(status, hex_bytes, bytes_remaining, byte_offset)

def classify_system_event(status, hex_bytes, bytes_remaining, byte_offset):
    # self, status, hex_bytes, byte_offset, description, value, bytes_remaining
    if status[1] in ["1", "2", "3", "6"]:
        return classify_system_common_event(status, hex_bytes, bytes_remaining, byte_offset)
    if status[1] in ["8", "a", "b", "c", "e"]:
        return classify_system_realtime_event(status, hex_bytes, bytes_remaining, byte_offset)
    if status[1]  == "0":
        return SystemExclusiveEvent(hex_bytes, bytes_remaining, byte_offset)
    return SystemEvent(status, hex_bytes, bytes_remaining, byte_offset)

def classify_system_realtime_event(status, hex_bytes, bytes_remaining, byte_offset):
    # print("classifing system realtime event with status[1] = " + status[1])
    if status[1]  == "8":
        return TimingClockEvent(hex_bytes, bytes_remaining, byte_offset)
    if status[1]  == "a":
        return StartEvent(hex_bytes, bytes_remaining, byte_offset)
    if status[1]  == "b":
        return ContinueEvent(hex_bytes, bytes_remaining, byte_offset)
    if status[1]  == "c":
        return StopEvent(hex_bytes, bytes_remaining, byte_offset)
    if status[1]  == "e":
        return ActiveSensingEvent(hex_bytes, bytes_remaining, byte_offset)
    return SystemRealTimeEvent(status, hex_bytes, bytes_remaining, byte_offset)

def classify_system_common_event(status, hex_bytes, bytes_remaining, byte_offset):
    # print("classifing system common event with status[1] = " + status[1])
    if status[1]  == "1":
        return QuarterFrameEvent(hex_bytes, bytes_remaining, byte_offset)
    if status[1]  == "2":
        return SongPointerEvent(hex_bytes, bytes_remaining, byte_offset)
    if status[1]  == "3":
        return SongSelectEvent(hex_bytes, bytes_remaining, byte_offset)
    if status[1]  == "6":
        return TuneRequestEvent(hex_bytes, bytes_remaining, byte_offset)
    return SystemCommonEvent(status, hex_bytes, bytes_remaining, byte_offset)

def classify_meta_event(hex_bytes, bytes_remaining, byte_offset):
    # self, meta_type, hex_bytes, bytes_remaining
    meta_type = hex_bytes[0:2]
    length_offset = vlf_len(hex_bytes[2:])
    if meta_type  == "00":
        return SequenceNumberEvent(hex_bytes[2+2*length_offset:], bytes_remaining, byte_offset)
    if meta_type  == "01":
        return TextEvent(hex_bytes[2+2*length_offset:], bytes_remaining, byte_offset)
    if meta_type  == "02":
        return CopyrightNoticeEvent(hex_bytes[2+2*length_offset:], bytes_remaining, byte_offset)
    if meta_type  == "03":
        return TrackNameEvent(hex_bytes[2+2*length_offset:], bytes_remaining, byte_offset)
    if meta_type  == "04":
        return InstrumentNameEvent(hex_bytes[2+2*length_offset:], bytes_remaining, byte_offset)
    if meta_type  == "05":
        return LyricsEvent(hex_bytes[2+2*length_offset:], bytes_remaining, byte_offset)
    if meta_type  == "06":
        return MarkerEvent(hex_bytes[2+2*length_offset:], bytes_remaining, byte_offset)
    if meta_type  == "07":
        return CuePointEvent(hex_bytes[2+2*length_offset:], bytes_remaining, byte_offset)
    if meta_type  == "20":
        return ChannelPrefixEvent(hex_bytes[2+2*length_offset:], bytes_remaining, byte_offset)
    if meta_type  == "2f":
        return EndOfTrackEvent(hex_bytes[2+2*length_offset:], bytes_remaining, byte_offset)
    if meta_type  == "51":
        return SetTempoEvent(hex_bytes[2+2*length_offset:], bytes_remaining, byte_offset)
    if meta_type  == "54":
        return SMPTEOffsetEvent(hex_bytes[2+2*length_offset:], bytes_remaining, byte_offset)
    if meta_type  == "58":
        return TimeSignatureEvent(hex_bytes[2+2*length_offset:], bytes_remaining, byte_offset)
    if meta_type  == "59":
        return KeySignatureEvent(hex_bytes[2+2*length_offset:], bytes_remaining, byte_offset)
    if meta_type  == "7f":
        return SequencerSpecificEvent(hex_bytes[2+2*length_offset:], bytes_remaining, byte_offset)
    return MetaEvent(meta_type, hex_bytes[2:], bytes_remaining, byte_offset)

def decode_note_number(note_number_hex):
    notes = ["C", "C#","D", "D#","E", "E#","F", "F#","G", "G#","A", "A#","B", "B#"]
    note_number = int(note_number_hex,16)
    musical_note = notes[note_number%12]
    octave = str((note_number//12)-2)
    return musical_note+octave

def decode_controller_number(controller_number_hex):
    controller_number = int(controller_number_hex,16)
    if controller_number < int("20",16):
        return "14-bit controllers - MSbyte"
    if controller_number < int("40",16):
        return "14-bit controllers - LSbyte"
    if controller_number < int("66",16):
        return "7-bit controllers or switches"
    if controller_number < int("78",16):
        return "Originally Undefined Controller"
    if controller_number < int("78",16):
        return "Originally Undefined Controller"
    return "Channel Mode Control"

def decode_program_number(program_number_hex):
    program_number = int(program_number_hex,16)
    if program_number < 8:
        return "Piano"
    if program_number < 16:
        return "Chromatic Percussion"
    if program_number < 24:
        return "Organ"
    if program_number < 32:
        return "Guitar"
    if program_number < 40:
        return "Bass"
    if program_number < 48:
        return "Strings"
    if program_number < 56:
        return "Ensemble"
    if program_number < 64:
        return "Brass"
    if program_number < 72:
        return "Reed"
    if program_number < 80:
        return "Pipe"
    if program_number < 88:
        return "Synth Lead"
    if program_number < 96:
        return "Synth Pad"
    if program_number < 104:
        return "Synth Effects"
    if program_number < 112:
        return "Ethnic"
    if program_number < 120:
        return "Percussive"
    return "Sound Effects"

def classify_chunk_data(hex_bytes, bytes_remaining):
    print()

midi_file = MidiFile()

print(midi_file.__str__())
# midi_file.to_tabular_format_csv()
# midi_file.to_block_format_txt()

print("\nComplete.")