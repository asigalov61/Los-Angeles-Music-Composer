#! /usr/bin/python3


r'''###############################################################################
###################################################################################
#
#
#	Tegridy MIDI X Module (TMIDI X / tee-midi eks)
#	Version 1.0
#
#   NOTE: TMIDI X Module starts after the partial MIDI.py module @ line 1342
#
#	Based upon MIDI.py module v.6.7. by Peter Billam / pjb.com.au
#
#	Project Los Angeles
#
#	Tegridy Code 2021
#
#   https://github.com/Tegridy-Code/Project-Los-Angeles
#
#
###################################################################################
###################################################################################
#       Copyright 2021 Project Los Angeles / Tegridy Code
#
#       Licensed under the Apache License, Version 2.0 (the "License");
#       you may not use this file except in compliance with the License.
#       You may obtain a copy of the License at
#
#           http://www.apache.org/licenses/LICENSE-2.0
#
#       Unless required by applicable law or agreed to in writing, software
#       distributed under the License is distributed on an "AS IS" BASIS,
#       WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#       See the License for the specific language governing permissions and
#       limitations under the License.
###################################################################################
###################################################################################
#
#	PARTIAL MIDI.py Module v.6.7. by Peter Billam
#   Please see TMIDI 2.3/tegridy-tools repo for full MIDI.py module code
# 
#   Or you can always download the latest full version from:
#	https://pjb.com.au/
#	
#	Copyright 2020 Peter Billam
#
###################################################################################
###################################################################################'''

import sys, struct, copy
Version = '6.7'
VersionDate = '20201120'

_previous_warning = ''  # 5.4
_previous_times = 0     # 5.4
#------------------------------- Encoding stuff --------------------------

def opus2midi(opus=[], text_encoding='ISO-8859-1'):
    r'''The argument is a list: the first item in the list is the "ticks"
parameter, the others are the tracks. Each track is a list
of midi-events, and each event is itself a list; see above.
opus2midi() returns a bytestring of the MIDI, which can then be
written either to a file opened in binary mode (mode='wb'),
or to stdout by means of:   sys.stdout.buffer.write()

my_opus = [
    96, 
    [   # track 0:
        ['patch_change', 0, 1, 8],   # and these are the events...
        ['note_on',   5, 1, 25, 96],
        ['note_off', 96, 1, 25, 0],
        ['note_on',   0, 1, 29, 96],
        ['note_off', 96, 1, 29, 0],
    ],   # end of track 0
]
my_midi = opus2midi(my_opus)
sys.stdout.buffer.write(my_midi)
'''
    if len(opus) < 2:
        opus=[1000, [],]
    tracks = copy.deepcopy(opus)
    ticks = int(tracks.pop(0))
    ntracks = len(tracks)
    if ntracks == 1:
        format = 0
    else:
        format = 1

    my_midi = b"MThd\x00\x00\x00\x06"+struct.pack('>HHH',format,ntracks,ticks)
    for track in tracks:
        events = _encode(track, text_encoding=text_encoding)
        my_midi += b'MTrk' + struct.pack('>I',len(events)) + events
    _clean_up_warnings()
    return my_midi


def score2opus(score=None, text_encoding='ISO-8859-1'):
    r'''
The argument is a list: the first item in the list is the "ticks"
parameter, the others are the tracks. Each track is a list
of score-events, and each event is itself a list.  A score-event
is similar to an opus-event (see above), except that in a score:
 1) the times are expressed as an absolute number of ticks
    from the track's start time
 2) the pairs of 'note_on' and 'note_off' events in an "opus"
    are abstracted into a single 'note' event in a "score":
    ['note', start_time, duration, channel, pitch, velocity]
score2opus() returns a list specifying the equivalent "opus".

my_score = [
    96,
    [   # track 0:
        ['patch_change', 0, 1, 8],
        ['note', 5, 96, 1, 25, 96],
        ['note', 101, 96, 1, 29, 96]
    ],   # end of track 0
]
my_opus = score2opus(my_score)
'''
    if len(score) < 2:
        score=[1000, [],]
    tracks = copy.deepcopy(score)
    ticks = int(tracks.pop(0))
    opus_tracks = []
    for scoretrack in tracks:
        time2events = dict([])
        for scoreevent in scoretrack:
            if scoreevent[0] == 'note':
                note_on_event = ['note_on',scoreevent[1],
                 scoreevent[3],scoreevent[4],scoreevent[5]]
                note_off_event = ['note_off',scoreevent[1]+scoreevent[2],
                 scoreevent[3],scoreevent[4],scoreevent[5]]
                if time2events.get(note_on_event[1]):
                   time2events[note_on_event[1]].append(note_on_event)
                else:
                   time2events[note_on_event[1]] = [note_on_event,]
                if time2events.get(note_off_event[1]):
                   time2events[note_off_event[1]].append(note_off_event)
                else:
                   time2events[note_off_event[1]] = [note_off_event,]
                continue
            if time2events.get(scoreevent[1]):
               time2events[scoreevent[1]].append(scoreevent)
            else:
               time2events[scoreevent[1]] = [scoreevent,]

        sorted_times = []  # list of keys
        for k in time2events.keys():
            sorted_times.append(k)
        sorted_times.sort()

        sorted_events = []  # once-flattened list of values sorted by key
        for time in sorted_times:
            sorted_events.extend(time2events[time])

        abs_time = 0
        for event in sorted_events:  # convert abs times => delta times
            delta_time = event[1] - abs_time
            abs_time = event[1]
            event[1] = delta_time
        opus_tracks.append(sorted_events)
    opus_tracks.insert(0,ticks)
    _clean_up_warnings()
    return opus_tracks

def score2midi(score=None, text_encoding='ISO-8859-1'):
    r'''
Translates a "score" into MIDI, using score2opus() then opus2midi()
'''
    return opus2midi(score2opus(score, text_encoding), text_encoding)

#--------------------------- Decoding stuff ------------------------

def midi2opus(midi=b''):
    r'''Translates MIDI into a "opus".  For a description of the
"opus" format, see opus2midi()
'''
    my_midi=bytearray(midi)
    if len(my_midi) < 4:
        _clean_up_warnings()
        return [1000,[],]
    id = bytes(my_midi[0:4])
    if id != b'MThd':
        _warn("midi2opus: midi starts with "+str(id)+" instead of 'MThd'")
        _clean_up_warnings()
        return [1000,[],]
    [length, format, tracks_expected, ticks] = struct.unpack(
     '>IHHH', bytes(my_midi[4:14]))
    if length != 6:
        _warn("midi2opus: midi header length was "+str(length)+" instead of 6")
        _clean_up_warnings()
        return [1000,[],]
    my_opus = [ticks,]
    my_midi = my_midi[14:]
    track_num = 1   # 5.1
    while len(my_midi) >= 8:
        track_type   = bytes(my_midi[0:4])
        if track_type != b'MTrk':
            #_warn('midi2opus: Warning: track #'+str(track_num)+' type is '+str(track_type)+" instead of b'MTrk'")
            pass
        [track_length] = struct.unpack('>I', my_midi[4:8])
        my_midi = my_midi[8:]
        if track_length > len(my_midi):
            _warn('midi2opus: track #'+str(track_num)+' length '+str(track_length)+' is too large')
            _clean_up_warnings()
            return my_opus   # 5.0
        my_midi_track = my_midi[0:track_length]
        my_track = _decode(my_midi_track)
        my_opus.append(my_track)
        my_midi = my_midi[track_length:]
        track_num += 1   # 5.1
    _clean_up_warnings()
    return my_opus

def opus2score(opus=[]):
    r'''For a description of the "opus" and "score" formats,
see opus2midi() and score2opus().
'''
    if len(opus) < 2:
        _clean_up_warnings()
        return [1000,[],]
    tracks = copy.deepcopy(opus)  # couple of slices probably quicker...
    ticks = int(tracks.pop(0))
    score = [ticks,]
    for opus_track in tracks:
        ticks_so_far = 0
        score_track = []
        chapitch2note_on_events = dict([])   # 4.0
        for opus_event in opus_track:
            ticks_so_far += opus_event[1]
            if opus_event[0] == 'note_off' or (opus_event[0] == 'note_on' and opus_event[4] == 0):  # 4.8
                cha = opus_event[2]
                pitch = opus_event[3]
                key = cha*128 + pitch
                if chapitch2note_on_events.get(key):
                    new_event = chapitch2note_on_events[key].pop(0)
                    new_event[2] = ticks_so_far - new_event[1]
                    score_track.append(new_event)
                elif pitch > 127:
                    pass #_warn('opus2score: note_off with no note_on, bad pitch='+str(pitch))
                else:
                    pass #_warn('opus2score: note_off with no note_on cha='+str(cha)+' pitch='+str(pitch))
            elif opus_event[0] == 'note_on':
                cha = opus_event[2]
                pitch = opus_event[3]
                key = cha*128 + pitch
                new_event = ['note',ticks_so_far,0,cha,pitch, opus_event[4]]
                if chapitch2note_on_events.get(key):
                    chapitch2note_on_events[key].append(new_event)
                else:
                    chapitch2note_on_events[key] = [new_event,]
            else:
                opus_event[1] = ticks_so_far
                score_track.append(opus_event)
        # check for unterminated notes (Oisín) -- 5.2
        for chapitch in chapitch2note_on_events:
            note_on_events = chapitch2note_on_events[chapitch]
            for new_e in note_on_events:
                new_e[2] = ticks_so_far - new_e[1]
                score_track.append(new_e)
                pass #_warn("opus2score: note_on with no note_off cha="+str(new_e[3])+' pitch='+str(new_e[4])+'; adding note_off at end')
        score.append(score_track)
    _clean_up_warnings()
    return score

def midi2score(midi=b''):
    r'''
Translates MIDI into a "score", using midi2opus() then opus2score()
'''
    return opus2score(midi2opus(midi))

def midi2ms_score(midi=b''):
    r'''
Translates MIDI into a "score" with one beat per second and one
tick per millisecond, using midi2opus() then to_millisecs()
then opus2score()
'''
    return opus2score(to_millisecs(midi2opus(midi)))

#------------------------ Other Transformations ---------------------

def to_millisecs(old_opus=None, desired_time_in_ms=1):
    r'''Recallibrates all the times in an "opus" to use one beat
per second and one tick per millisecond.  This makes it
hard to retrieve any information about beats or barlines,
but it does make it easy to mix different scores together.
'''
    if old_opus == None:
        return [1000 * desired_time_in_ms,[],]
    try:
        old_tpq  = int(old_opus[0])
    except IndexError:   # 5.0
        _warn('to_millisecs: the opus '+str(type(old_opus))+' has no elements')
        return [1000 * desired_time_in_ms,[],]
    new_opus = [1000 * desired_time_in_ms,]
    # 6.7 first go through building a table of set_tempos by absolute-tick
    ticks2tempo = {}
    itrack = 1
    while itrack < len(old_opus):
        ticks_so_far = 0
        for old_event in old_opus[itrack]:
            if old_event[0] == 'note':
                raise TypeError('to_millisecs needs an opus, not a score')
            ticks_so_far += old_event[1]
            if old_event[0] == 'set_tempo':
                ticks2tempo[ticks_so_far] = old_event[2]
        itrack += 1
    # then get the sorted-array of their keys
    tempo_ticks = []  # list of keys
    for k in ticks2tempo.keys():
        tempo_ticks.append(k)
    tempo_ticks.sort()
    # then go through converting to millisec, testing if the next
    # set_tempo lies before the next track-event, and using it if so.
    itrack = 1
    while itrack < len(old_opus):
        ms_per_old_tick = 400 / old_tpq  # float: will round later 6.3
        i_tempo_ticks = 0
        ticks_so_far = 0
        ms_so_far = 0.0
        previous_ms_so_far = 0.0
        new_track = [['set_tempo',0,1000000 * desired_time_in_ms],]  # new "crochet" is 1 sec
        for old_event in old_opus[itrack]:
            # detect if ticks2tempo has something before this event
            # 20160702 if ticks2tempo is at the same time, leave it
            event_delta_ticks = old_event[1] * desired_time_in_ms
            if (i_tempo_ticks < len(tempo_ticks) and
              tempo_ticks[i_tempo_ticks] < (ticks_so_far + old_event[1]) * desired_time_in_ms):
                delta_ticks = tempo_ticks[i_tempo_ticks] - ticks_so_far
                ms_so_far += (ms_per_old_tick * delta_ticks * desired_time_in_ms)
                ticks_so_far = tempo_ticks[i_tempo_ticks]
                ms_per_old_tick = ticks2tempo[ticks_so_far] / (1000.0*old_tpq * desired_time_in_ms)
                i_tempo_ticks += 1
                event_delta_ticks -= delta_ticks
            new_event = copy.deepcopy(old_event)  # now handle the new event
            ms_so_far += (ms_per_old_tick * old_event[1] * desired_time_in_ms)
            new_event[1] = round(ms_so_far - previous_ms_so_far)
            if old_event[0] != 'set_tempo':
                previous_ms_so_far = ms_so_far
                new_track.append(new_event)
            ticks_so_far += event_delta_ticks
        new_opus.append(new_track)
        itrack += 1
    _clean_up_warnings()
    return new_opus

def event2alsaseq(event=None):   # 5.5
    r'''Converts an event into the format needed by the alsaseq module,
http://pp.com.mx/python/alsaseq
The type of track (opus or score) is autodetected.
'''
    pass

def grep(score=None, channels=None):
    r'''Returns a "score" containing only the channels specified
'''
    if score == None:
        return [1000,[],]
    ticks = score[0]
    new_score = [ticks,]
    if channels == None:
        return new_score
    channels = set(channels)
    global Event2channelindex
    itrack = 1
    while itrack < len(score):
        new_score.append([])
        for event in score[itrack]:
            channel_index = Event2channelindex.get(event[0], False)
            if channel_index:
                if event[channel_index] in channels:
                    new_score[itrack].append(event)
            else:
                new_score[itrack].append(event)
        itrack += 1
    return new_score

def play_score(score=None):
    r'''Converts the "score" to midi, and feeds it into 'aplaymidi -'
'''
    if score == None:
        return
    import subprocess
    pipe = subprocess.Popen(['aplaymidi','-'], stdin=subprocess.PIPE)
    if score_type(score) == 'opus':
        pipe.stdin.write(opus2midi(score))
    else:
        pipe.stdin.write(score2midi(score))
    pipe.stdin.close()

def score2stats(opus_or_score=None):
    r'''Returns a dict of some basic stats about the score, like
bank_select (list of tuples (msb,lsb)),
channels_by_track (list of lists), channels_total (set),
general_midi_mode (list),
ntracks, nticks, patch_changes_by_track (list of dicts),
num_notes_by_channel (list of numbers),
patch_changes_total (set),
percussion (dict histogram of channel 9 events),
pitches (dict histogram of pitches on channels other than 9),
pitch_range_by_track (list, by track, of two-member-tuples),
pitch_range_sum (sum over tracks of the pitch_ranges),
'''
    bank_select_msb = -1
    bank_select_lsb = -1
    bank_select = []
    channels_by_track = []
    channels_total    = set([])
    general_midi_mode = []
    num_notes_by_channel = dict([])
    patches_used_by_track  = []
    patches_used_total     = set([])
    patch_changes_by_track = []
    patch_changes_total    = set([])
    percussion = dict([]) # histogram of channel 9 "pitches"
    pitches    = dict([]) # histogram of pitch-occurrences channels 0-8,10-15
    pitch_range_sum = 0   # u pitch-ranges of each track
    pitch_range_by_track = []
    is_a_score = True
    if opus_or_score == None:
        return {'bank_select':[], 'channels_by_track':[], 'channels_total':[],
         'general_midi_mode':[], 'ntracks':0, 'nticks':0,
         'num_notes_by_channel':dict([]),
         'patch_changes_by_track':[], 'patch_changes_total':[],
         'percussion':{}, 'pitches':{}, 'pitch_range_by_track':[],
         'ticks_per_quarter':0, 'pitch_range_sum':0}
    ticks_per_quarter = opus_or_score[0]
    i = 1   # ignore first element, which is ticks
    nticks = 0
    while i < len(opus_or_score):
        highest_pitch = 0
        lowest_pitch = 128
        channels_this_track = set([])
        patch_changes_this_track = dict({})
        for event in opus_or_score[i]:
            if event[0] == 'note':
                num_notes_by_channel[event[3]] = num_notes_by_channel.get(event[3],0) + 1
                if event[3] == 9:
                    percussion[event[4]] = percussion.get(event[4],0) + 1
                else:
                    pitches[event[4]]    = pitches.get(event[4],0) + 1
                    if event[4] > highest_pitch:
                        highest_pitch = event[4]
                    if event[4] < lowest_pitch:
                        lowest_pitch = event[4]
                channels_this_track.add(event[3])
                channels_total.add(event[3])
                finish_time = event[1] + event[2]
                if finish_time > nticks:
                    nticks = finish_time
            elif event[0] == 'note_off' or (event[0] == 'note_on' and event[4] == 0):  # 4.8
                finish_time = event[1]
                if finish_time > nticks:
                    nticks = finish_time
            elif event[0] == 'note_on':
                is_a_score = False
                num_notes_by_channel[event[2]] = num_notes_by_channel.get(event[2],0) + 1
                if event[2] == 9:
                    percussion[event[3]] = percussion.get(event[3],0) + 1
                else:
                    pitches[event[3]]    = pitches.get(event[3],0) + 1
                    if event[3] > highest_pitch:
                        highest_pitch = event[3]
                    if event[3] < lowest_pitch:
                        lowest_pitch = event[3]
                channels_this_track.add(event[2])
                channels_total.add(event[2])
            elif event[0] == 'patch_change':
                patch_changes_this_track[event[2]] = event[3]
                patch_changes_total.add(event[3])
            elif event[0] == 'control_change':
                if event[3] == 0:  # bank select MSB
                    bank_select_msb = event[4]
                elif event[3] == 32:  # bank select LSB
                    bank_select_lsb = event[4]
                if bank_select_msb >= 0 and bank_select_lsb >= 0:
                    bank_select.append((bank_select_msb,bank_select_lsb))
                    bank_select_msb = -1
                    bank_select_lsb = -1
            elif event[0] == 'sysex_f0':
                if _sysex2midimode.get(event[2], -1) >= 0:
                    general_midi_mode.append(_sysex2midimode.get(event[2]))
            if is_a_score:
                if event[1] > nticks:
                    nticks = event[1]
            else:
                nticks += event[1]
        if lowest_pitch == 128:
            lowest_pitch = 0
        channels_by_track.append(channels_this_track)
        patch_changes_by_track.append(patch_changes_this_track)
        pitch_range_by_track.append((lowest_pitch,highest_pitch))
        pitch_range_sum += (highest_pitch-lowest_pitch)
        i += 1

    return {'bank_select':bank_select,
            'channels_by_track':channels_by_track,
            'channels_total':channels_total,
            'general_midi_mode':general_midi_mode,
            'ntracks':len(opus_or_score)-1,
            'nticks':nticks,
            'num_notes_by_channel':num_notes_by_channel,
            'patch_changes_by_track':patch_changes_by_track,
            'patch_changes_total':patch_changes_total,
            'percussion':percussion,
            'pitches':pitches,
            'pitch_range_by_track':pitch_range_by_track,
            'pitch_range_sum':pitch_range_sum,
            'ticks_per_quarter':ticks_per_quarter}

#----------------------------- Event stuff --------------------------

_sysex2midimode = {
    "\x7E\x7F\x09\x01\xF7": 1,
    "\x7E\x7F\x09\x02\xF7": 0,
    "\x7E\x7F\x09\x03\xF7": 2,
}

# Some public-access tuples:
MIDI_events = tuple('''note_off note_on key_after_touch
control_change patch_change channel_after_touch
pitch_wheel_change'''.split())

Text_events = tuple('''text_event copyright_text_event
track_name instrument_name lyric marker cue_point text_event_08
text_event_09 text_event_0a text_event_0b text_event_0c
text_event_0d text_event_0e text_event_0f'''.split())

Nontext_meta_events = tuple('''end_track set_tempo
smpte_offset time_signature key_signature sequencer_specific
raw_meta_event sysex_f0 sysex_f7 song_position song_select
tune_request'''.split())
# unsupported: raw_data

# Actually, 'tune_request' is is F-series event, not strictly a meta-event...
Meta_events = Text_events + Nontext_meta_events
All_events  = MIDI_events + Meta_events

# And three dictionaries:
Number2patch = {   # General MIDI patch numbers:
0:'Acoustic Grand',
1:'Bright Acoustic',
2:'Electric Grand',
3:'Honky-Tonk',
4:'Electric Piano 1',
5:'Electric Piano 2',
6:'Harpsichord',
7:'Clav',
8:'Celesta',
9:'Glockenspiel',
10:'Music Box',
11:'Vibraphone',
12:'Marimba',
13:'Xylophone',
14:'Tubular Bells',
15:'Dulcimer',
16:'Drawbar Organ',
17:'Percussive Organ',
18:'Rock Organ',
19:'Church Organ',
20:'Reed Organ',
21:'Accordion',
22:'Harmonica',
23:'Tango Accordion',
24:'Acoustic Guitar(nylon)',
25:'Acoustic Guitar(steel)',
26:'Electric Guitar(jazz)',
27:'Electric Guitar(clean)',
28:'Electric Guitar(muted)',
29:'Overdriven Guitar',
30:'Distortion Guitar',
31:'Guitar Harmonics',
32:'Acoustic Bass',
33:'Electric Bass(finger)',
34:'Electric Bass(pick)',
35:'Fretless Bass',
36:'Slap Bass 1',
37:'Slap Bass 2',
38:'Synth Bass 1',
39:'Synth Bass 2',
40:'Violin',
41:'Viola',
42:'Cello',
43:'Contrabass',
44:'Tremolo Strings',
45:'Pizzicato Strings',
46:'Orchestral Harp',
47:'Timpani',
48:'String Ensemble 1',
49:'String Ensemble 2',
50:'SynthStrings 1',
51:'SynthStrings 2',
52:'Choir Aahs',
53:'Voice Oohs',
54:'Synth Voice',
55:'Orchestra Hit',
56:'Trumpet',
57:'Trombone',
58:'Tuba',
59:'Muted Trumpet',
60:'French Horn',
61:'Brass Section',
62:'SynthBrass 1',
63:'SynthBrass 2',
64:'Soprano Sax',
65:'Alto Sax',
66:'Tenor Sax',
67:'Baritone Sax',
68:'Oboe',
69:'English Horn',
70:'Bassoon',
71:'Clarinet',
72:'Piccolo',
73:'Flute',
74:'Recorder',
75:'Pan Flute',
76:'Blown Bottle',
77:'Skakuhachi',
78:'Whistle',
79:'Ocarina',
80:'Lead 1 (square)',
81:'Lead 2 (sawtooth)',
82:'Lead 3 (calliope)',
83:'Lead 4 (chiff)',
84:'Lead 5 (charang)',
85:'Lead 6 (voice)',
86:'Lead 7 (fifths)',
87:'Lead 8 (bass+lead)',
88:'Pad 1 (new age)',
89:'Pad 2 (warm)',
90:'Pad 3 (polysynth)',
91:'Pad 4 (choir)',
92:'Pad 5 (bowed)',
93:'Pad 6 (metallic)',
94:'Pad 7 (halo)',
95:'Pad 8 (sweep)',
96:'FX 1 (rain)',
97:'FX 2 (soundtrack)',
98:'FX 3 (crystal)',
99:'FX 4 (atmosphere)',
100:'FX 5 (brightness)',
101:'FX 6 (goblins)',
102:'FX 7 (echoes)',
103:'FX 8 (sci-fi)',
104:'Sitar',
105:'Banjo',
106:'Shamisen',
107:'Koto',
108:'Kalimba',
109:'Bagpipe',
110:'Fiddle',
111:'Shanai',
112:'Tinkle Bell',
113:'Agogo',
114:'Steel Drums',
115:'Woodblock',
116:'Taiko Drum',
117:'Melodic Tom',
118:'Synth Drum',
119:'Reverse Cymbal',
120:'Guitar Fret Noise',
121:'Breath Noise',
122:'Seashore',
123:'Bird Tweet',
124:'Telephone Ring',
125:'Helicopter',
126:'Applause',
127:'Gunshot',
}
Notenum2percussion = {   # General MIDI Percussion (on Channel 9):
35:'Acoustic Bass Drum',
36:'Bass Drum 1',
37:'Side Stick',
38:'Acoustic Snare',
39:'Hand Clap',
40:'Electric Snare',
41:'Low Floor Tom',
42:'Closed Hi-Hat',
43:'High Floor Tom',
44:'Pedal Hi-Hat',
45:'Low Tom',
46:'Open Hi-Hat',
47:'Low-Mid Tom',
48:'Hi-Mid Tom',
49:'Crash Cymbal 1',
50:'High Tom',
51:'Ride Cymbal 1',
52:'Chinese Cymbal',
53:'Ride Bell',
54:'Tambourine',
55:'Splash Cymbal',
56:'Cowbell',
57:'Crash Cymbal 2',
58:'Vibraslap',
59:'Ride Cymbal 2',
60:'Hi Bongo',
61:'Low Bongo',
62:'Mute Hi Conga',
63:'Open Hi Conga',
64:'Low Conga',
65:'High Timbale',
66:'Low Timbale',
67:'High Agogo',
68:'Low Agogo',
69:'Cabasa',
70:'Maracas',
71:'Short Whistle',
72:'Long Whistle',
73:'Short Guiro',
74:'Long Guiro',
75:'Claves',
76:'Hi Wood Block',
77:'Low Wood Block',
78:'Mute Cuica',
79:'Open Cuica',
80:'Mute Triangle',
81:'Open Triangle',
}

Event2channelindex = { 'note':3, 'note_off':2, 'note_on':2,
 'key_after_touch':2, 'control_change':2, 'patch_change':2,
 'channel_after_touch':2, 'pitch_wheel_change':2
}

################################################################
# The code below this line is full of frightening things, all to
# do with the actual encoding and decoding of binary MIDI data.

def _twobytes2int(byte_a):
    r'''decode a 16 bit quantity from two bytes,'''
    return (byte_a[1] | (byte_a[0] << 8))

def _int2twobytes(int_16bit):
    r'''encode a 16 bit quantity into two bytes,'''
    return bytes([(int_16bit>>8) & 0xFF, int_16bit & 0xFF])

def _read_14_bit(byte_a):
    r'''decode a 14 bit quantity from two bytes,'''
    return (byte_a[0] | (byte_a[1] << 7))

def _write_14_bit(int_14bit):
    r'''encode a 14 bit quantity into two bytes,'''
    return bytes([int_14bit & 0x7F, (int_14bit>>7) & 0x7F])

def _ber_compressed_int(integer):
    r'''BER compressed integer (not an ASN.1 BER, see perlpacktut for
details).  Its bytes represent an unsigned integer in base 128,
most significant digit first, with as few digits as possible.
Bit eight (the high bit) is set on each byte except the last.
'''
    ber = bytearray(b'')
    seven_bits = 0x7F & integer
    ber.insert(0, seven_bits)  # XXX surely should convert to a char ?
    integer >>= 7
    while integer > 0:
        seven_bits = 0x7F & integer
        ber.insert(0, 0x80|seven_bits)  # XXX surely should convert to a char ?
        integer >>= 7
    return ber

def _unshift_ber_int(ba):
    r'''Given a bytearray, returns a tuple of (the ber-integer at the
start, and the remainder of the bytearray).
'''
    if not len(ba):   # 6.7
        _warn('_unshift_ber_int: no integer found')
        return ((0, b""))
    byte = ba.pop(0)
    integer = 0
    while True:
        integer += (byte & 0x7F)
        if not (byte & 0x80):
            return ((integer, ba))
        if not len(ba):
            _warn('_unshift_ber_int: no end-of-integer found')
            return ((0, ba))
        byte = ba.pop(0)
        integer <<= 7

def _clean_up_warnings():  # 5.4
    # Call this before returning from any publicly callable function
    # whenever there's a possibility that a warning might have been printed
    # by the function, or by any private functions it might have called.
    global _previous_times
    global _previous_warning
    if _previous_times > 1:
        # E:1176, 0: invalid syntax (<string>, line 1176) (syntax-error) ???
        # print('  previous message repeated '+str(_previous_times)+' times', file=sys.stderr)
        # 6.7
        sys.stderr.write('  previous message repeated {0} times\n'.format(_previous_times))
    elif _previous_times > 0:
        sys.stderr.write('  previous message repeated\n')
    _previous_times = 0
    _previous_warning = ''

def _warn(s=''):
    global _previous_times
    global _previous_warning
    if s == _previous_warning:  # 5.4
        _previous_times = _previous_times + 1
    else:
        _clean_up_warnings()
        sys.stderr.write(str(s)+"\n")
        _previous_warning = s

def _some_text_event(which_kind=0x01, text=b'some_text', text_encoding='ISO-8859-1'):
    if str(type(text)).find("'str'") >= 0:   # 6.4 test for back-compatibility
        data = bytes(text, encoding=text_encoding)
    else:
        data = bytes(text)
    return b'\xFF'+bytes((which_kind,))+_ber_compressed_int(len(data))+data

def _consistentise_ticks(scores):  # 3.6
    # used by mix_scores, merge_scores, concatenate_scores
    if len(scores) == 1:
         return copy.deepcopy(scores)
    are_consistent = True
    ticks = scores[0][0]
    iscore = 1
    while iscore < len(scores):
        if scores[iscore][0] != ticks:
            are_consistent = False
            break
        iscore += 1
    if are_consistent:
        return copy.deepcopy(scores)
    new_scores = []
    iscore = 0
    while iscore < len(scores):
        score = scores[iscore]
        new_scores.append(opus2score(to_millisecs(score2opus(score))))
        iscore += 1
    return new_scores


###########################################################################

def _decode(trackdata=b'', exclude=None, include=None,
 event_callback=None, exclusive_event_callback=None, no_eot_magic=False):
    r'''Decodes MIDI track data into an opus-style list of events.
The options:
  'exclude' is a list of event types which will be ignored SHOULD BE A SET
  'include' (and no exclude), makes exclude a list
       of all possible events, /minus/ what include specifies
  'event_callback' is a coderef
  'exclusive_event_callback' is a coderef
'''
    trackdata = bytearray(trackdata)
    if exclude == None:
        exclude = []
    if include == None:
        include = []
    if include and not exclude:
        exclude = All_events
    include = set(include)
    exclude = set(exclude)

    # Pointer = 0;  not used here; we eat through the bytearray instead.
    event_code = -1; # used for running status
    event_count = 0;
    events = []

    while(len(trackdata)):
        # loop while there's anything to analyze ...
        eot = False   # When True, the event registrar aborts this loop
        event_count += 1

        E = []
        # E for events - we'll feed it to the event registrar at the end.

        # Slice off the delta time code, and analyze it
        [time, remainder] = _unshift_ber_int(trackdata)

        # Now let's see what we can make of the command
        first_byte = trackdata.pop(0) & 0xFF

        if (first_byte < 0xF0):  # It's a MIDI event
            if (first_byte & 0x80):
                event_code = first_byte
            else:
                # It wants running status; use last event_code value
                trackdata.insert(0, first_byte)
                if (event_code == -1):
                    _warn("Running status not set; Aborting track.")
                    return []

            command = event_code & 0xF0
            channel = event_code & 0x0F

            if (command == 0xF6):  #  0-byte argument
                pass
            elif (command == 0xC0 or command == 0xD0):  #  1-byte argument
                parameter = trackdata.pop(0)  # could be B
            else: # 2-byte argument could be BB or 14-bit
                parameter = (trackdata.pop(0), trackdata.pop(0))

            #################################################################
            # MIDI events

            if (command      == 0x80):
                if 'note_off' in exclude:
                    continue
                E = ['note_off', time, channel, parameter[0], parameter[1]]
            elif (command == 0x90):
                if 'note_on' in exclude:
                    continue
                E = ['note_on', time, channel, parameter[0], parameter[1]]
            elif (command == 0xA0):
                if 'key_after_touch' in exclude:
                    continue
                E = ['key_after_touch',time,channel,parameter[0],parameter[1]]
            elif (command == 0xB0):
                if 'control_change' in exclude:
                    continue
                E = ['control_change',time,channel,parameter[0],parameter[1]]
            elif (command == 0xC0):
                if 'patch_change' in exclude:
                    continue
                E = ['patch_change', time, channel, parameter]
            elif (command == 0xD0):
                if 'channel_after_touch' in exclude:
                    continue
                E = ['channel_after_touch', time, channel, parameter]
            elif (command == 0xE0):
                if 'pitch_wheel_change' in exclude:
                    continue
                E = ['pitch_wheel_change', time, channel,
                 _read_14_bit(parameter)-0x2000]
            else:
                _warn("Shouldn't get here; command="+hex(command))

        elif (first_byte == 0xFF):  # It's a Meta-Event! ##################
            #[command, length, remainder] =
            #    unpack("xCwa*", substr(trackdata, $Pointer, 6));
            #Pointer += 6 - len(remainder);
            #    # Move past JUST the length-encoded.
            command = trackdata.pop(0) & 0xFF
            [length, trackdata] = _unshift_ber_int(trackdata)
            if (command      == 0x00):
                 if (length == 2):
                     E = ['set_sequence_number',time,_twobytes2int(trackdata)]
                 else:
                     _warn('set_sequence_number: length must be 2, not '+str(length))
                     E = ['set_sequence_number', time, 0]

            elif command >= 0x01 and command <= 0x0f:   # Text events
                # 6.2 take it in bytes; let the user get the right encoding.
                # text_str = trackdata[0:length].decode('ascii','ignore')
                # text_str = trackdata[0:length].decode('ISO-8859-1')
                # 6.4 take it in bytes; let the user get the right encoding.
                text_data = bytes(trackdata[0:length])   # 6.4
                # Defined text events
                if (command == 0x01):
                     E = ['text_event', time, text_data]
                elif (command == 0x02):
                     E = ['copyright_text_event', time, text_data]
                elif (command == 0x03):
                     E = ['track_name', time, text_data]
                elif (command == 0x04):
                     E = ['instrument_name', time, text_data]
                elif (command == 0x05):
                     E = ['lyric', time, text_data]
                elif (command == 0x06):
                     E = ['marker', time, text_data]
                elif (command == 0x07):
                     E = ['cue_point', time, text_data]
                # Reserved but apparently unassigned text events
                elif (command == 0x08):
                     E = ['text_event_08', time, text_data]
                elif (command == 0x09):
                     E = ['text_event_09', time, text_data]
                elif (command == 0x0a):
                     E = ['text_event_0a', time, text_data]
                elif (command == 0x0b):
                     E = ['text_event_0b', time, text_data]
                elif (command == 0x0c):
                     E = ['text_event_0c', time, text_data]
                elif (command == 0x0d):
                     E = ['text_event_0d', time, text_data]
                elif (command == 0x0e):
                     E = ['text_event_0e', time, text_data]
                elif (command == 0x0f):
                     E = ['text_event_0f', time, text_data]

            # Now the sticky events -------------------------------------
            elif (command == 0x2F):
                 E = ['end_track', time]
                     # The code for handling this, oddly, comes LATER,
                     # in the event registrar.
            elif (command == 0x51): # DTime, Microseconds/Crochet
                 if length != 3:
                     _warn('set_tempo event, but length='+str(length))
                 E = ['set_tempo', time,
                      struct.unpack(">I", b'\x00'+trackdata[0:3])[0]]
            elif (command == 0x54):
                 if length != 5:   # DTime, HR, MN, SE, FR, FF
                     _warn('smpte_offset event, but length='+str(length))
                 E = ['smpte_offset',time] + list(struct.unpack(">BBBBB",trackdata[0:5]))
            elif (command == 0x58):
                 if length != 4:   # DTime, NN, DD, CC, BB
                     _warn('time_signature event, but length='+str(length))
                 E = ['time_signature', time]+list(trackdata[0:4])
            elif (command == 0x59):
                 if length != 2:   # DTime, SF(signed), MI
                     _warn('key_signature event, but length='+str(length))
                 E = ['key_signature',time] + list(struct.unpack(">bB",trackdata[0:2]))
            elif (command == 0x7F):   # 6.4
                 E = ['sequencer_specific',time, bytes(trackdata[0:length])]
            else:
                 E = ['raw_meta_event', time, command,
                   bytes(trackdata[0:length])]   # 6.0
                 #"[uninterpretable meta-event command of length length]"
                 # DTime, Command, Binary Data
                 # It's uninterpretable; record it as raw_data.

            # Pointer += length; #  Now move Pointer
            trackdata = trackdata[length:]

        ######################################################################
        elif (first_byte == 0xF0 or first_byte == 0xF7):
            # Note that sysexes in MIDI /files/ are different than sysexes
            # in MIDI transmissions!! The vast majority of system exclusive
            # messages will just use the F0 format. For instance, the
            # transmitted message F0 43 12 00 07 F7 would be stored in a
            # MIDI file as F0 05 43 12 00 07 F7. As mentioned above, it is
            # required to include the F7 at the end so that the reader of the
            # MIDI file knows that it has read the entire message. (But the F7
            # is omitted if this is a non-final block in a multiblock sysex;
            # but the F7 (if there) is counted in the message's declared
            # length, so we don't have to think about it anyway.)
            #command = trackdata.pop(0)
            [length, trackdata] = _unshift_ber_int(trackdata)
            if first_byte == 0xF0:
                # 20091008 added ISO-8859-1 to get an 8-bit str
                # 6.4 return bytes instead
                E = ['sysex_f0', time, bytes(trackdata[0:length])]
            else:
                E = ['sysex_f7', time, bytes(trackdata[0:length])]
            trackdata = trackdata[length:]

        ######################################################################
        # Now, the MIDI file spec says:
        #  <track data> = <MTrk event>+
        #  <MTrk event> = <delta-time> <event>
        #  <event> = <MIDI event> | <sysex event> | <meta-event>
        # I know that, on the wire, <MIDI event> can include note_on,
        # note_off, and all the other 8x to Ex events, AND Fx events
        # other than F0, F7, and FF -- namely, <song position msg>,
        # <song select msg>, and <tune request>.
        #
        # Whether these can occur in MIDI files is not clear specified
        # from the MIDI file spec.  So, I'm going to assume that
        # they CAN, in practice, occur.  I don't know whether it's
        # proper for you to actually emit these into a MIDI file.
        
        elif (first_byte == 0xF2):   # DTime, Beats
            #  <song position msg> ::=     F2 <data pair>
            E = ['song_position', time, _read_14_bit(trackdata[:2])]
            trackdata = trackdata[2:]

        elif (first_byte == 0xF3):   # <song select msg> ::= F3 <data singlet>
            # E = ['song_select', time, struct.unpack('>B',trackdata.pop(0))[0]]
            E = ['song_select', time, trackdata[0]]
            trackdata = trackdata[1:]
            # DTime, Thing (what?! song number?  whatever ...)

        elif (first_byte == 0xF6):   # DTime
            E = ['tune_request', time]
            # What would a tune request be doing in a MIDI /file/?

        #########################################################
        # ADD MORE META-EVENTS HERE.  TODO:
        # f1 -- MTC Quarter Frame Message. One data byte follows
        #     the Status; it's the time code value, from 0 to 127.
        # f8 -- MIDI clock.    no data.
        # fa -- MIDI start.    no data.
        # fb -- MIDI continue. no data.
        # fc -- MIDI stop.     no data.
        # fe -- Active sense.  no data.
        # f4 f5 f9 fd -- unallocated

            r'''
        elif (first_byte > 0xF0) { # Some unknown kinda F-series event ####
            # Here we only produce a one-byte piece of raw data.
            # But the encoder for 'raw_data' accepts any length of it.
            E = [ 'raw_data',
                         time, substr(trackdata,Pointer,1) ]
            # DTime and the Data (in this case, the one Event-byte)
            ++Pointer;  # itself

'''
        elif first_byte > 0xF0:  # Some unknown F-series event
            # Here we only produce a one-byte piece of raw data.
            # E = ['raw_data', time, bytest(trackdata[0])]   # 6.4
            E = ['raw_data', time, trackdata[0]]   # 6.4 6.7
            trackdata = trackdata[1:]
        else:  # Fallthru.
            _warn("Aborting track.  Command-byte first_byte="+hex(first_byte))
            break
        # End of the big if-group


        ######################################################################
        #  THE EVENT REGISTRAR...
        if E and  (E[0] == 'end_track'):
            # This is the code for exceptional handling of the EOT event.
            eot = True
            if not no_eot_magic:
                if E[1] > 0:  # a null text-event to carry the delta-time
                    E = ['text_event', E[1], '']
                else:
                    E = []   # EOT with a delta-time of 0; ignore it.
        
        if E and not (E[0] in exclude):
            #if ( $exclusive_event_callback ):
            #    &{ $exclusive_event_callback }( @E );
            #else:
            #    &{ $event_callback }( @E ) if $event_callback;
                events.append(E)
        if eot:
            break

    # End of the big "Event" while-block

    return events


###########################################################################
def _encode(events_lol, unknown_callback=None, never_add_eot=False,
  no_eot_magic=False, no_running_status=False, text_encoding='ISO-8859-1'):
    # encode an event structure, presumably for writing to a file
    # Calling format:
    #   $data_r = MIDI::Event::encode( \@event_lol, { options } );
    # Takes a REFERENCE to an event structure (a LoL)
    # Returns an (unblessed) REFERENCE to track data.

    # If you want to use this to encode a /single/ event,
    # you still have to do it as a reference to an event structure (a LoL)
    # that just happens to have just one event.  I.e.,
    #   encode( [ $event ] ) or encode( [ [ 'note_on', 100, 5, 42, 64] ] )
    # If you're doing this, consider the never_add_eot track option, as in
    #   print MIDI ${ encode( [ $event], { 'never_add_eot' => 1} ) };

    data = [] # what I'll store the chunks of byte-data in

    # This is so my end_track magic won't corrupt the original
    events = copy.deepcopy(events_lol)

    if not never_add_eot:
        # One way or another, tack on an 'end_track'
        if events:
            last = events[-1]
            if not (last[0] == 'end_track'):  # no end_track already
                if (last[0] == 'text_event' and len(last[2]) == 0):
                    # 0-length text event at track-end.
                    if no_eot_magic:
                        # Exceptional case: don't mess with track-final
                        # 0-length text_events; just peg on an end_track
                        events.append(['end_track', 0])
                    else:
                        # NORMAL CASE: replace with an end_track, leaving DTime
                        last[0] = 'end_track'
                else:
                    # last event was neither 0-length text_event nor end_track
                    events.append(['end_track', 0])
        else:  # an eventless track!
            events = [['end_track', 0],]

    # maybe_running_status = not no_running_status # unused? 4.7
    last_status = -1

    for event_r in (events):
        E = copy.deepcopy(event_r)
        # otherwise the shifting'd corrupt the original
        if not E:
            continue

        event = E.pop(0)
        if not len(event):
            continue

        dtime = int(E.pop(0))
        # print('event='+str(event)+' dtime='+str(dtime))

        event_data = ''

        if (   # MIDI events -- eligible for running status
             event    == 'note_on'
             or event == 'note_off'
             or event == 'control_change'
             or event == 'key_after_touch'
             or event == 'patch_change'
             or event == 'channel_after_touch'
             or event == 'pitch_wheel_change'  ):

            # This block is where we spend most of the time.  Gotta be tight.
            if (event == 'note_off'):
                status = 0x80 | (int(E[0]) & 0x0F)
                parameters = struct.pack('>BB', int(E[1])&0x7F, int(E[2])&0x7F)
            elif (event == 'note_on'):
                status = 0x90 | (int(E[0]) & 0x0F)
                parameters = struct.pack('>BB', int(E[1])&0x7F, int(E[2])&0x7F)
            elif (event == 'key_after_touch'):
                status = 0xA0 | (int(E[0]) & 0x0F)
                parameters = struct.pack('>BB', int(E[1])&0x7F, int(E[2])&0x7F)
            elif (event == 'control_change'):
                status = 0xB0 | (int(E[0]) & 0x0F)
                parameters = struct.pack('>BB', int(E[1])&0xFF, int(E[2])&0xFF)
            elif (event == 'patch_change'):
                status = 0xC0 | (int(E[0]) & 0x0F)
                parameters = struct.pack('>B', int(E[1]) & 0xFF)
            elif (event == 'channel_after_touch'):
                status = 0xD0 | (int(E[0]) & 0x0F)
                parameters = struct.pack('>B', int(E[1]) & 0xFF)
            elif (event == 'pitch_wheel_change'):
                status = 0xE0 | (int(E[0]) & 0x0F)
                parameters =  _write_14_bit(int(E[1]) + 0x2000)
            else:
                _warn("BADASS FREAKOUT ERROR 31415!")

            # And now the encoding
            # w = BER compressed integer (not ASN.1 BER, see perlpacktut for
            # details).  Its bytes represent an unsigned integer in base 128,
            # most significant digit first, with as few digits as possible.
            # Bit eight (the high bit) is set on each byte except the last.

            data.append(_ber_compressed_int(dtime))
            if (status != last_status) or no_running_status:
                data.append(struct.pack('>B', status))
            data.append(parameters)
 
            last_status = status
            continue
        else:
            # Not a MIDI event.
            # All the code in this block could be more efficient,
            # but this is not where the code needs to be tight.
            # print "zaz $event\n";
            last_status = -1

            if event == 'raw_meta_event':
                event_data = _some_text_event(int(E[0]), E[1], text_encoding)
            elif (event == 'set_sequence_number'):  # 3.9
                event_data = b'\xFF\x00\x02'+_int2twobytes(E[0])

            # Text meta-events...
            # a case for a dict, I think (pjb) ...
            elif (event == 'text_event'):
                event_data = _some_text_event(0x01, E[0], text_encoding)
            elif (event == 'copyright_text_event'):
                event_data = _some_text_event(0x02, E[0], text_encoding)
            elif (event == 'track_name'):
                event_data = _some_text_event(0x03, E[0], text_encoding)
            elif (event == 'instrument_name'):
                event_data = _some_text_event(0x04, E[0], text_encoding)
            elif (event == 'lyric'):
                event_data = _some_text_event(0x05, E[0], text_encoding)
            elif (event == 'marker'):
                event_data = _some_text_event(0x06, E[0], text_encoding)
            elif (event == 'cue_point'):
                event_data = _some_text_event(0x07, E[0], text_encoding)
            elif (event == 'text_event_08'):
                event_data = _some_text_event(0x08, E[0], text_encoding)
            elif (event == 'text_event_09'):
                event_data = _some_text_event(0x09, E[0], text_encoding)
            elif (event == 'text_event_0a'):
                event_data = _some_text_event(0x0A, E[0], text_encoding)
            elif (event == 'text_event_0b'):
                event_data = _some_text_event(0x0B, E[0], text_encoding)
            elif (event == 'text_event_0c'):
                event_data = _some_text_event(0x0C, E[0], text_encoding)
            elif (event == 'text_event_0d'):
                event_data = _some_text_event(0x0D, E[0], text_encoding)
            elif (event == 'text_event_0e'):
                event_data = _some_text_event(0x0E, E[0], text_encoding)
            elif (event == 'text_event_0f'):
                event_data = _some_text_event(0x0F, E[0], text_encoding)
            # End of text meta-events

            elif (event == 'end_track'):
                event_data = b"\xFF\x2F\x00"

            elif (event == 'set_tempo'):
                #event_data = struct.pack(">BBwa*", 0xFF, 0x51, 3,
                #              substr( struct.pack('>I', E[0]), 1, 3))
                event_data = b'\xFF\x51\x03'+struct.pack('>I',E[0])[1:]
            elif (event == 'smpte_offset'):
                # event_data = struct.pack(">BBwBBBBB", 0xFF, 0x54, 5, E[0:5] )
                event_data = struct.pack(">BBBbBBBB", 0xFF,0x54,0x05,E[0],E[1],E[2],E[3],E[4])
            elif (event == 'time_signature'):
                # event_data = struct.pack(">BBwBBBB",  0xFF, 0x58, 4, E[0:4] )
                event_data = struct.pack(">BBBbBBB", 0xFF, 0x58, 0x04, E[0],E[1],E[2],E[3])
            elif (event == 'key_signature'):
                event_data = struct.pack(">BBBbB", 0xFF, 0x59, 0x02, E[0],E[1])
            elif (event == 'sequencer_specific'):
                # event_data = struct.pack(">BBwa*", 0xFF,0x7F, len(E[0]), E[0])
                event_data = _some_text_event(0x7F, E[0], text_encoding)
            # End of Meta-events

            # Other Things...
            elif (event == 'sysex_f0'):
                 #event_data = struct.pack(">Bwa*", 0xF0, len(E[0]), E[0])
                 #B=bitstring w=BER-compressed-integer a=null-padded-ascii-str
                 event_data = bytearray(b'\xF0')+_ber_compressed_int(len(E[0]))+bytearray(E[0])
            elif (event == 'sysex_f7'):
                 #event_data = struct.pack(">Bwa*", 0xF7, len(E[0]), E[0])
                 event_data = bytearray(b'\xF7')+_ber_compressed_int(len(E[0]))+bytearray(E[0])

            elif (event == 'song_position'):
                 event_data = b"\xF2" + _write_14_bit( E[0] )
            elif (event == 'song_select'):
                 event_data = struct.pack('>BB', 0xF3, E[0] )
            elif (event == 'tune_request'):
                 event_data = b"\xF6"
            elif (event == 'raw_data'):
                _warn("_encode: raw_data event not supported")
                # event_data = E[0]
                continue
            # End of Other Stuff

            else:
                # The Big Fallthru
                if unknown_callback:
                    # push(@data, &{ $unknown_callback }( @$event_r ))
                    pass
                else:
                    _warn("Unknown event: "+str(event))
                    # To surpress complaint here, just set
                    #  'unknown_callback' => sub { return () }
                continue

            #print "Event $event encoded part 2\n"
            if str(type(event_data)).find("'str'") >= 0:
                event_data = bytearray(event_data.encode('Latin1', 'ignore'))
            if len(event_data): # how could $event_data be empty
                # data.append(struct.pack('>wa*', dtime, event_data))
                # print(' event_data='+str(event_data))
                data.append(_ber_compressed_int(dtime)+event_data)

    return b''.join(data)

###################################################################################
###################################################################################
###################################################################################
#
#	Tegridy MIDI X Module (TMIDI X / tee-midi eks)
#	Version 1.0
#
#	Based upon and includes the amazing MIDI.py module v.6.7. by Peter Billam
#	pjb.com.au
#
#	Project Los Angeles
#	Tegridy Code 2021
# https://github.com/Tegridy-Code/Project-Los-Angeles
#
###################################################################################
###################################################################################
###################################################################################

import os

import datetime

import copy

from datetime import datetime

import secrets

import random

import pickle

import csv

import tqdm

from itertools import zip_longest
from itertools import groupby

from operator import itemgetter

import sys

from abc import ABC, abstractmethod

from difflib import SequenceMatcher as SM

import statistics

###################################################################################
#
# Original TMIDI Tegridy helper functions
#
###################################################################################

def Tegridy_TXT_to_INT_Converter(input_TXT_string, line_by_line_INT_string=True, max_INT = 0):

    '''Tegridy TXT to Intergers Converter
     
    Input: Input TXT string in the TMIDI-TXT format

           Type of output TXT INT string: line-by-line or one long string

           Maximum absolute integer to process. Maximum is inclusive 
           Default = process all integers. This helps to remove outliers/unwanted ints

    Output: List of pure intergers
            String of intergers in the specified format: line-by-line or one long string
            Number of processed integers
            Number of skipped integers
    
    Project Los Angeles
    Tegridy Code 2021'''

    print('Tegridy TXT to Intergers Converter')

    output_INT_list = []

    npi = 0
    nsi = 0

    TXT_List = list(input_TXT_string)
    for char in TXT_List:
      if max_INT != 0:
        if abs(ord(char)) <= max_INT:
          output_INT_list.append(ord(char))
          npi += 1
        else:
          nsi += 1  
      else:
        output_INT_list.append(ord(char))
        npi += 1    
    
    if line_by_line_INT_string:
      output_INT_string = '\n'.join([str(elem) for elem in output_INT_list])
    else:
      output_INT_string = ' '.join([str(elem) for elem in output_INT_list])  

    print('Converted TXT to INTs:', npi, ' / ', nsi)

    return output_INT_list, output_INT_string, npi, nsi

###################################################################################

def Tegridy_INT_to_TXT_Converter(input_INT_list):

    '''Tegridy Intergers to TXT Converter
     
    Input: List of intergers in TMIDI-TXT-INT format
    Output: Decoded TXT string in TMIDI-TXT format
    Project Los Angeles
    Tegridy Code 2020'''

    output_TXT_string = ''

    for i in input_INT_list:
      output_TXT_string += chr(int(i))
    
    return output_TXT_string

###################################################################################

def Tegridy_INT_String_to_TXT_Converter(input_INT_String, line_by_line_input=True):

    '''Tegridy Intergers String to TXT Converter
     
    Input: List of intergers in TMIDI-TXT-INT-String format
    Output: Decoded TXT string in TMIDI-TXT format
    Project Los Angeles
    Tegridy Code 2020'''
    
    print('Tegridy Intergers String to TXT Converter')

    if line_by_line_input:
      input_string = input_INT_String.split('\n')
    else:
      input_string = input_INT_String.split(' ')  

    output_TXT_string = ''

    for i in input_string:
      try:
        output_TXT_string += chr(abs(int(i)))
      except:
        print('Bad note:', i)
        continue  
    
    print('Done!')

    return output_TXT_string

###################################################################################

def Tegridy_SONG_to_MIDI_Converter(SONG,
                                  output_signature = 'Tegridy TMIDI Module', 
                                  track_name = 'Composition Track',
                                  number_of_ticks_per_quarter = 425,
                                  list_of_MIDI_patches = [0, 24, 32, 40, 42, 46, 56, 71, 73, 0, 0, 0, 0, 0, 0, 0],
                                  output_file_name = 'TMIDI-Composition',
                                  text_encoding='ISO-8859-1'):

    '''Tegridy SONG to MIDI Converter
     
    Input: Input SONG in TMIDI SONG/MIDI.py Score format
           Output MIDI Track 0 name / MIDI Signature
           Output MIDI Track 1 name / Composition track name
           Number of ticks per quarter for the output MIDI
           List of 16 MIDI patch numbers for output MIDI. Def. is MuseNet compatible patches.
           Output file name w/o .mid extension.
           Optional text encoding if you are working with text_events/lyrics. This is especially useful for Karaoke. Please note that anything but ISO-8859-1 is a non-standard way of encoding text_events according to MIDI specs.

    Output: MIDI File
            Detailed MIDI stats

    Project Los Angeles
    Tegridy Code 2020'''                                  

    print('Converting to MIDI. Please stand-by...')
    
    output_header = [number_of_ticks_per_quarter, 
                    [['track_name', 0, bytes(output_signature, text_encoding)]]]                                                    

    patch_list = [['patch_change', 0, 0, list_of_MIDI_patches[0]], 
                    ['patch_change', 0, 1, list_of_MIDI_patches[1]],
                    ['patch_change', 0, 2, list_of_MIDI_patches[2]],
                    ['patch_change', 0, 3, list_of_MIDI_patches[3]],
                    ['patch_change', 0, 4, list_of_MIDI_patches[4]],
                    ['patch_change', 0, 5, list_of_MIDI_patches[5]],
                    ['patch_change', 0, 6, list_of_MIDI_patches[6]],
                    ['patch_change', 0, 7, list_of_MIDI_patches[7]],
                    ['patch_change', 0, 8, list_of_MIDI_patches[8]],
                    ['patch_change', 0, 9, list_of_MIDI_patches[9]],
                    ['patch_change', 0, 10, list_of_MIDI_patches[10]],
                    ['patch_change', 0, 11, list_of_MIDI_patches[11]],
                    ['patch_change', 0, 12, list_of_MIDI_patches[12]],
                    ['patch_change', 0, 13, list_of_MIDI_patches[13]],
                    ['patch_change', 0, 14, list_of_MIDI_patches[14]],
                    ['patch_change', 0, 15, list_of_MIDI_patches[15]],
                    ['track_name', 0, bytes(track_name, text_encoding)]]

    output = output_header + [patch_list + SONG]

    midi_data = score2midi(output, text_encoding)
    detailed_MIDI_stats = score2stats(output)

    with open(output_file_name + '.mid', 'wb') as midi_file:
        midi_file.write(midi_data)
        midi_file.close()
    
    print('Done! Enjoy! :)')
    
    return detailed_MIDI_stats

###################################################################################

def Tegridy_File_Time_Stamp(input_file_name='File_Created_on_', ext = ''):

  '''Tegridy File Time Stamp
     
  Input: Full path and file name without extention
         File extension
          
  Output: File name string with time-stamp and extension (time-stamped file name)

  Project Los Angeles
  Tegridy Code 2021'''       

  print('Time-stamping output file...')

  now = ''
  now_n = str(datetime.now())
  now_n = now_n.replace(' ', '_')
  now_n = now_n.replace(':', '_')
  now = now_n.replace('.', '_')
      
  fname = input_file_name + str(now) + ext

  return(fname)

###################################################################################

def Tegridy_Any_Pickle_File_Writer(Data, input_file_name='TMIDI_Pickle_File'):

  '''Tegridy Pickle File Writer
     
  Input: Data to write (I.e. a list)
         Full path and file name without extention
         
  Output: Named Pickle file

  Project Los Angeles
  Tegridy Code 2021'''

  print('Tegridy Pickle File Writer')

  full_path_to_output_dataset_to = input_file_name + '.pickle'

  if os.path.exists(full_path_to_output_dataset_to):
    os.remove(full_path_to_output_dataset_to)
    print('Removing old Dataset...')
  else:
    print("Creating new Dataset file...")

  with open(full_path_to_output_dataset_to, 'wb') as filehandle:
    # store the data as binary data stream
    pickle.dump(Data, filehandle, protocol=pickle.HIGHEST_PROTOCOL)

  print('Dataset was saved as:', full_path_to_output_dataset_to)
  print('Task complete. Enjoy! :)')

###################################################################################

def Tegridy_Any_Pickle_File_Reader(input_file_name='TMIDI_Pickle_File', ext='.pickle'):

  '''Tegridy Pickle File Loader
     
  Input: Full path and file name without extention
         File extension if different from default .pickle
       
  Output: Standard Python 3 unpickled data object

  Project Los Angeles
  Tegridy Code 2021'''

  print('Tegridy Pickle File Loader')
  print('Loading the pickle file. Please wait...')

  with open(input_file_name + ext, 'rb') as pickle_file:
    content = pickle.load(pickle_file)

  return content

###################################################################################

# TMIDI X Code is below

###################################################################################

def Optimus_MIDI_TXT_Processor(MIDI_file, 
                              line_by_line_output=True, 
                              chordify_TXT=False,
                              dataset_MIDI_events_time_denominator=1,
                              output_velocity=True,
                              output_MIDI_channels = False, 
                              MIDI_channel=0, 
                              MIDI_patch=[0, 1], 
                              char_offset = 30000,
                              transpose_by = 0,
                              flip=False, 
                              melody_conditioned_encoding=False,
                              melody_pitch_baseline = 0,
                              number_of_notes_to_sample = -1,
                              sampling_offset_from_start = 0,
                              karaoke=False,
                              karaoke_language_encoding='utf-8',
                              song_name='Song',
                              perfect_timings=False,
                              musenet_encoding=False,
                              transform=0,
                              zero_token=False,
                              reset_timings=False):

    '''Project Los Angeles
       Tegridy Code 2021'''
  
###########

    debug = False

    ev = 0

    chords_list_final = []
    chords_list = []
    events_matrix = []
    melody = []
    melody1 = []

    itrack = 1

    min_note = 0
    max_note = 0
    ev = 0
    patch = 0

    score = []
    rec_event = []

    txt = ''
    txtc = ''
    chords = []
    melody_chords = []

    karaoke_events_matrix = []
    karaokez = []

    sample = 0
    start_sample = 0

    bass_melody = []

    INTS = []
    bints = 0

###########    

    def list_average(num):
      sum_num = 0
      for t in num:
          sum_num = sum_num + t           

      avg = sum_num / len(num)
      return avg

###########

    #print('Loading MIDI file...')
    midi_file = open(MIDI_file, 'rb')
    if debug: print('Processing File:', file_address)
    
    try:
      opus = midi2opus(midi_file.read())
    
    except:
      print('Problematic MIDI. Skipping...')
      print('File name:', MIDI_file)
      midi_file.close()
      return txt, melody, chords
         
    midi_file.close()

    score1 = to_millisecs(opus)
    score2 = opus2score(score1)

    # score2 = opus2score(opus) # TODO Improve score timings when it will be possible.
    
    if MIDI_channel == 16: # Process all MIDI channels
      score = score2
    
    if MIDI_channel >= 0 and MIDI_channel <= 15: # Process only a selected single MIDI channel
      score = grep(score2, [MIDI_channel])
    
    if MIDI_channel == -1: # Process all channels except drums (except channel 9)
      score = grep(score2, [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15])   
    
    #print('Reading all MIDI events from the MIDI file...')
    while itrack < len(score):
      for event in score[itrack]:
        
        if perfect_timings:
          if event[0] == 'note':
            event[1] = round(event[1], -1)
            event[2] = round(event[2], -1)

        if event[0] == 'text_event' or event[0] == 'lyric' or event[0] == 'note':
          if perfect_timings:
            event[1] = round(event[1], -1)
          karaokez.append(event)
        
        if event[0] == 'text_event' or event[0] == 'lyric':
          if perfect_timings:
            event[1] = round(event[1], -1)
          try:
            event[2] = str(event[2].decode(karaoke_language_encoding, 'replace')).replace('/', '').replace(' ', '').replace('\\', '')
          except:
            event[2] = str(event[2]).replace('/', '').replace(' ', '').replace('\\', '')
            continue
          karaoke_events_matrix.append(event)

        if event[0] == 'patch_change':
          patch = event[3]

        if event[0] == 'note' and patch in MIDI_patch:
          if len(event) == 6: # Checking for bad notes...
              eve = copy.deepcopy(event)
              
              eve[1] = int(event[1] / dataset_MIDI_events_time_denominator)
              eve[2] = int(event[2] / dataset_MIDI_events_time_denominator)
              
              eve[4] = int(event[4] + transpose_by)
              
              if flip == True:
                eve[4] = int(127 - (event[4] + transpose_by)) 
              
              if number_of_notes_to_sample > -1:
                if sample <= number_of_notes_to_sample:
                  if start_sample >= sampling_offset_from_start:
                    events_matrix.append(eve)
                    sample += 1
                    ev += 1
                  else:
                    start_sample += 1

              else:
                events_matrix.append(eve)
                ev += 1
                start_sample += 1
                
      itrack +=1 # Going to next track...

    #print('Doing some heavy pythonic sorting...Please stand by...')

    fn = os.path.basename(MIDI_file)
    song_name = song_name.replace(' ', '_').replace('=', '_').replace('\'', '-')
    if song_name == 'Song':
      sng_name = fn.split('.')[0].replace(' ', '_').replace('=', '_').replace('\'', '-')
      song_name = sng_name

    # Zero token
    if zero_token:
      txt += chr(char_offset) + chr(char_offset)
      if output_MIDI_channels:
        txt += chr(char_offset)
      if output_velocity:
        txt += chr(char_offset) + chr(char_offset)     
      else:
        txt += chr(char_offset)

      txtc += chr(char_offset) + chr(char_offset)
      if output_MIDI_channels:
        txtc += chr(char_offset)
      if output_velocity:
        txtc += chr(char_offset) + chr(char_offset)      
      else:
        txtc += chr(char_offset)
      
      txt += '=' + song_name + '_with_' + str(len(events_matrix)-1) + '_notes'
      txtc += '=' + song_name + '_with_' + str(len(events_matrix)-1) + '_notes'
    
    else:
      # Song stamp
      txt += 'SONG=' + song_name + '_with_' + str(len(events_matrix)-1) + '_notes'
      txtc += 'SONG=' + song_name + '_with_' + str(len(events_matrix)-1) + '_notes'

    if line_by_line_output:
      txt += chr(10)
      txtc += chr(10)
    else:
      txt += chr(32)
      txtc += chr(32)

    #print('Sorting input by start time...')
    events_matrix.sort(key=lambda x: x[1]) # Sorting input by start time    
    
    #print('Timings converter')
    if reset_timings:
      ev_matrix = Tegridy_Timings_Converter(events_matrix)[0]
    else:
      ev_matrix = events_matrix
    
    chords.extend(ev_matrix)
    #print(chords)

    #print('Extracting melody...')
    melody_list = []

    #print('Grouping by start time. This will take a while...')
    values = set(map(lambda x:x[1], ev_matrix)) # Non-multithreaded function version just in case

    groups = [[y for y in ev_matrix if y[1]==x and len(y) == 6] for x in values] # Grouping notes into chords while discarting bad notes...
  
    #print('Sorting events...')
    for items in groups:
        
        items.sort(reverse=True, key=lambda x: x[4]) # Sorting events by pitch
        
        if melody_conditioned_encoding: items[0][3] = 0 # Melody should always bear MIDI Channel 0 for code to work
        
        melody_list.append(items[0]) # Creating final melody list
        melody_chords.append(items) # Creating final chords list
        bass_melody.append(items[-1]) # Creating final bass melody list
    
    # [WIP] Melody-conditioned chords list
    if melody_conditioned_encoding == True:
      if not karaoke:
   
        previous_event = copy.deepcopy(melody_chords[0][0])

        for ev in melody_chords:
          hp = True
          ev.sort(reverse=False, key=lambda x: x[4]) # Sorting chord events by pitch
          for event in ev:
          
            # Computing events details
            start_time = int(abs(event[1] - previous_event[1]))
            
            duration = int(previous_event[2])

            if hp == True:
              if int(previous_event[4]) >= melody_pitch_baseline:
                channel = int(0)
                hp = False
              else:
                channel = int(previous_event[3]+1)
                hp = False  
            else:
              channel = int(previous_event[3]+1)
              hp = False

            pitch = int(previous_event[4])

            velocity = int(previous_event[5])

            # Writing INTergerS...
            try:
              INTS.append([(start_time)+char_offset, (duration)+char_offset, channel+char_offset, pitch+char_offset, velocity+char_offset])
            except:
              bints += 1

            # Converting to TXT if possible...
            try:
              txtc += str(chr(start_time + char_offset))
              txtc += str(chr(duration + char_offset))
              txtc += str(chr(pitch + char_offset))
              if output_velocity:
                txtc += str(chr(velocity + char_offset))
              if output_MIDI_channels:
                txtc += str(chr(channel + char_offset))

              if line_by_line_output:
              

                txtc += chr(10)
              else:

                txtc += chr(32)

              previous_event = copy.deepcopy(event)
            
            except:
              # print('Problematic MIDI event! Skipping...')
              continue

        if not line_by_line_output:
          txtc += chr(10)

        txt = txtc
        chords = melody_chords
    
    # Default stuff (not melody-conditioned/not-karaoke)
    else:      
      if not karaoke:
        melody_chords.sort(reverse=False, key=lambda x: x[0][1])
        mel_chords = []
        for mc in melody_chords:
          mel_chords.extend(mc)

        if transform != 0: 
          chords = Tegridy_Transform(mel_chords, transform)
        else:
          chords = mel_chords

        # TXT Stuff
        previous_event = copy.deepcopy(chords[0])
        for event in chords:

          # Computing events details
          start_time = int(abs(event[1] - previous_event[1]))
          
          duration = int(previous_event[2])

          channel = int(previous_event[3])

          pitch = int(previous_event[4] + transpose_by)
          if flip == True:
            pitch = 127 - int(previous_event[4] + transpose_by)

          velocity = int(previous_event[5])

          # Writing INTergerS...
          try:
            INTS.append([(start_time)+char_offset, (duration)+char_offset, channel+char_offset, pitch+char_offset, velocity+char_offset])
          except:
            bints += 1

          # Converting to TXT if possible...
          try:
            txt += str(chr(start_time + char_offset))
            txt += str(chr(duration + char_offset))
            txt += str(chr(pitch + char_offset))
            if output_velocity:
              txt += str(chr(velocity + char_offset))
            if output_MIDI_channels:
              txt += str(chr(channel + char_offset))


            if chordify_TXT == True and int(event[1] - previous_event[1]) == 0:
              txt += ''      
            else:     
              if line_by_line_output:
                txt += chr(10)
              else:
                txt += chr(32) 
            
            previous_event = copy.deepcopy(event)
          
          except:
            # print('Problematic MIDI event. Skipping...')
            continue

        if not line_by_line_output:
          txt += chr(10)      

    # Karaoke stuff
    if karaoke:

      melody_chords.sort(reverse=False, key=lambda x: x[0][1])
      mel_chords = []
      for mc in melody_chords:
        mel_chords.extend(mc)

      if transform != 0: 
        chords = Tegridy_Transform(mel_chords, transform)
      else:
        chords = mel_chords

      previous_event = copy.deepcopy(chords[0])
      for event in chords:

        # Computing events details
        start_time = int(abs(event[1] - previous_event[1]))
        
        duration = int(previous_event[2])

        channel = int(previous_event[3])

        pitch = int(previous_event[4] + transpose_by)

        velocity = int(previous_event[5])

        # Converting to TXT
        txt += str(chr(start_time + char_offset))
        txt += str(chr(duration + char_offset))
        txt += str(chr(pitch + char_offset))

        txt += str(chr(velocity + char_offset))
        txt += str(chr(channel + char_offset))     

        if start_time > 0:
          for k in karaoke_events_matrix:
            if event[1] == k[1]:
              txt += str('=')
              txt += str(k[2])          
              break

        if line_by_line_output:
          txt += chr(10)
        else:
          txt += chr(32) 
        
        previous_event = copy.deepcopy(event)
      
      if not line_by_line_output:
        txt += chr(10)

    # Final processing code...
    # =======================================================================

    # Helper aux/backup function for Karaoke
    karaokez.sort(reverse=False, key=lambda x: x[1])  

    # MuseNet sorting
    if musenet_encoding and not melody_conditioned_encoding and not karaoke:
      chords.sort(key=lambda x: (x[1], x[3]))
    
    # Final melody sort
    melody_list.sort()

    # auxs for future use
    aux1 = [None]
    aux2 = [None]

    return txt, melody_list, chords, bass_melody, karaokez, INTS, aux1, aux2 # aux1 and aux2 are not used atm

###################################################################################

def Optimus_TXT_to_Notes_Converter(Optimus_TXT_String,
                                    line_by_line_dataset = True,
                                    has_velocities = True,
                                    has_MIDI_channels = True,
                                    dataset_MIDI_events_time_denominator = 1,
                                    char_encoding_offset = 30000,
                                    save_only_first_composition = True,
                                    simulate_velocity=True,
                                    karaoke=False,
                                    zero_token=False):

    '''Project Los Angeles
       Tegridy Code 2020'''

    print('Tegridy Optimus TXT to Notes Converter')
    print('Converting TXT to Notes list...Please wait...')

    song_name = ''

    if line_by_line_dataset:
      input_string = Optimus_TXT_String.split('\n')
    else:
      input_string = Optimus_TXT_String.split(' ')

    if line_by_line_dataset:
      name_string = Optimus_TXT_String.split('\n')[0].split('=')
    else:
      name_string = Optimus_TXT_String.split(' ')[0].split('=')

    # Zero token
    zt = ''

    zt += chr(char_encoding_offset) + chr(char_encoding_offset)
    
    if has_MIDI_channels:
      zt += chr(char_encoding_offset)
    
    if has_velocities:
      zt += chr(char_encoding_offset) + chr(char_encoding_offset)     
    
    else:
      zt += chr(char_encoding_offset)

    if zero_token:
      if name_string[0] == zt:
        song_name = name_string[1]
    
    else:
      if name_string[0] == 'SONG':
        song_name = name_string[1]

    output_list = []
    st = 0

    for i in range(2, len(input_string)-1):

      if save_only_first_composition:
        if zero_token:
          if input_string[i].split('=')[0] == zt:

            song_name = name_string[1]
            break
        
        else:
          if input_string[i].split('=')[0] == 'SONG':

            song_name = name_string[1]
            break
      try:
        istring = input_string[i]

        if has_MIDI_channels == False:
          step = 4          

        if has_MIDI_channels == True:
          step = 5

        if has_velocities == False:
          step -= 1

        st += int(ord(istring[0]) - char_encoding_offset) * dataset_MIDI_events_time_denominator

        if not karaoke:
          for s in range(0, len(istring), step):
              if has_MIDI_channels==True:
                if step > 3 and len(istring) > 2:
                      out = []       
                      out.append('note')

                      out.append(st) # Start time

                      out.append(int(ord(istring[s+1]) - char_encoding_offset) * dataset_MIDI_events_time_denominator) # Duration

                      if has_velocities:
                        out.append(int(ord(istring[s+4]) - char_encoding_offset)) # Channel
                      else:
                        out.append(int(ord(istring[s+3]) - char_encoding_offset)) # Channel  

                      out.append(int(ord(istring[s+2]) - char_encoding_offset)) # Pitch

                      if simulate_velocity:
                        if s == 0:
                          sim_vel = int(ord(istring[s+2]) - char_encoding_offset)
                        out.append(sim_vel) # Simulated Velocity (= highest note's pitch)
                      else:                      
                        out.append(int(ord(istring[s+3]) - char_encoding_offset)) # Velocity

              if has_MIDI_channels==False:
                if step > 3 and len(istring) > 2:
                      out = []       
                      out.append('note')

                      out.append(st) # Start time
                      out.append(int(ord(istring[s+1]) - char_encoding_offset) * dataset_MIDI_events_time_denominator) # Duration
                      out.append(0) # Channel
                      out.append(int(ord(istring[s+2]) - char_encoding_offset)) # Pitch

                      if simulate_velocity:
                        if s == 0:
                          sim_vel = int(ord(istring[s+2]) - char_encoding_offset)
                        out.append(sim_vel) # Simulated Velocity (= highest note's pitch)
                      else:                      
                        out.append(int(ord(istring[s+3]) - char_encoding_offset)) # Velocity

              if step == 3 and len(istring) > 2:
                      out = []       
                      out.append('note')

                      out.append(st) # Start time
                      out.append(int(ord(istring[s+1]) - char_encoding_offset) * dataset_MIDI_events_time_denominator) # Duration
                      out.append(0) # Channel
                      out.append(int(ord(istring[s+2]) - char_encoding_offset)) # Pitch

                      out.append(int(ord(istring[s+2]) - char_encoding_offset)) # Velocity = Pitch

              output_list.append(out)

        if karaoke:
          try:
              out = []       
              out.append('note')

              out.append(st) # Start time
              out.append(int(ord(istring[1]) - char_encoding_offset) * dataset_MIDI_events_time_denominator) # Duration
              out.append(int(ord(istring[4]) - char_encoding_offset)) # Channel
              out.append(int(ord(istring[2]) - char_encoding_offset)) # Pitch

              if simulate_velocity:
                if s == 0:
                  sim_vel = int(ord(istring[2]) - char_encoding_offset)
                out.append(sim_vel) # Simulated Velocity (= highest note's pitch)
              else:                      
                out.append(int(ord(istring[3]) - char_encoding_offset)) # Velocity
              output_list.append(out)
              out = []
              if istring.split('=')[1] != '':
                out.append('lyric')
                out.append(st)
                out.append(istring.split('=')[1])
                output_list.append(out)
          except:
            continue


      except:
        print('Bad note string:', istring)
        continue

    # Simple error control just in case
    S = []
    for x in output_list:
      if len(x) == 6 or len(x) == 3:
        S.append(x)

    output_list.clear()    
    output_list = copy.deepcopy(S)


    print('Task complete! Enjoy! :)')

    return output_list, song_name

###################################################################################

def Optimus_Data2TXT_Converter(data,
                              dataset_time_denominator=1,
                              transpose_by = 0,
                              char_offset = 33,
                              line_by_line_output = True,
                              output_velocity = False,
                              output_MIDI_channels = False):


  '''Input: data as a flat chords list of flat chords lists

  Output: TXT string
          INTs

  Project Los Angeles
  Tegridy Code 2021'''

  txt = ''
  TXT = ''

  quit = False
  counter = 0

  INTs = []
  INTs_f = []

  for d in tqdm.tqdm(sorted(data)):

    if quit == True:
      break

    txt = 'SONG=' + str(counter)
    counter += 1

    if line_by_line_output:
      txt += chr(10)
    else:
      txt += chr(32)
      
    INTs = []

    # TXT Stuff
    previous_event = copy.deepcopy(d[0])
    for event in sorted(d):

      # Computing events details
      start_time = int(abs(event[1] - previous_event[1]) / dataset_time_denominator)
      
      duration = int(previous_event[2] / dataset_time_denominator)

      channel = int(previous_event[3])

      pitch = int(previous_event[4] + transpose_by)

      velocity = int(previous_event[5])

      INTs.append([start_time, duration, pitch])

      # Converting to TXT if possible...
      try:
        txt += str(chr(start_time + char_offset))
        txt += str(chr(duration + char_offset))
        txt += str(chr(pitch + char_offset))
        if output_velocity:
          txt += str(chr(velocity + char_offset))
        if output_MIDI_channels:
          txt += str(chr(channel + char_offset))
    
        if line_by_line_output:
          txt += chr(10)
        else:
          txt += chr(32) 
        
        previous_event = copy.deepcopy(event)
      except KeyboardInterrupt:
        quit = True
        break
      except:
        print('Problematic MIDI data. Skipping...')
        continue

    if not line_by_line_output:
      txt += chr(10)
    
    TXT += txt
    INTs_f.extend(INTs)

  return TXT, INTs_f

###################################################################################

def Optimus_Squash(chords_list, simulate_velocity=True, mono_compression=False):

  '''Input: Flat chords list
            Simulate velocity or not
            Mono-compression enabled or disabled
            
            Default is almost lossless 25% compression, otherwise, lossy 50% compression (mono-compression)

     Output: Squashed chords list
             Resulting compression level

             Please note that if drums are passed through as is

     Project Los Angeles
     Tegridy Code 2021'''

  output = []
  ptime = 0
  vel = 0
  boost = 15
  stptc = []
  ocount = 0
  rcount = 0

  for c in chords_list:
    
    cc = copy.deepcopy(c)
    ocount += 1
    
    if [cc[1], cc[3], (cc[4] % 12) + 60] not in stptc:
      stptc.append([cc[1], cc[3], (cc[4] % 12) + 60])

      if cc[3] != 9:
        cc[4] = (c[4] % 12) + 60

      if simulate_velocity and c[1] != ptime:
        vel = c[4] + boost
      
      if cc[3] != 9:
        cc[5] = vel

      if mono_compression:
        if c[1] != ptime:
          output.append(cc)
          rcount += 1  
      else:
        output.append(cc)
        rcount += 1
      
      ptime = c[1]

  output.sort(key=lambda x: (x[1], x[4]))

  comp_level = 100 - int((rcount * 100) / ocount)

  return output, comp_level

###################################################################################

def Optimus_Signature(chords_list, calculate_full_signature=False):

    '''Optimus Signature

    ---In the name of the search for a perfect score slice signature---
     
    Input: Flat chords list to evaluate

    Output: Full Optimus Signature as a list
            Best/recommended Optimus Signature as a list

    Project Los Angeles
    Tegridy Code 2021'''
    
    # Pitches

    ## StDev
    if calculate_full_signature:
      psd = statistics.stdev([int(y[4]) for y in chords_list])
    else:
      psd = 0

    ## Median
    pmh = statistics.median_high([int(y[4]) for y in chords_list])
    pm = statistics.median([int(y[4]) for y in chords_list])
    pml = statistics.median_low([int(y[4]) for y in chords_list])
    
    ## Mean
    if calculate_full_signature:
      phm = statistics.harmonic_mean([int(y[4]) for y in chords_list])
    else:
      phm = 0

    # Durations
    dur = statistics.median([int(y[2]) for y in chords_list])

    # Velocities

    vel = statistics.median([int(y[5]) for y in chords_list])

    # Beats
    mtds = statistics.median([int(abs(chords_list[i-1][1]-chords_list[i][1])) for i in range(1, len(chords_list))])
    if calculate_full_signature:
      hmtds = statistics.harmonic_mean([int(abs(chords_list[i-1][1]-chords_list[i][1])) for i in range(1, len(chords_list))])
    else:
      hmtds = 0

    # Final Optimus signatures
    full_Optimus_signature = [round(psd), round(pmh), round(pm), round(pml), round(phm), round(dur), round(vel), round(mtds), round(hmtds)]
    ########################    PStDev     PMedianH    PMedian    PMedianL    PHarmoMe    Duration    Velocity      Beat       HarmoBeat

    best_Optimus_signature = [round(pmh), round(pm), round(pml), round(dur, -1), round(vel, -1), round(mtds, -1)]
    ########################   PMedianH    PMedian    PMedianL      Duration        Velocity          Beat
    
    # Return...
    return full_Optimus_signature, best_Optimus_signature
    

###################################################################################
#
# TMIDI 2.0 Helper functions
#
###################################################################################

def Tegridy_FastSearch(needle, haystack, randomize = False):

  '''

  Input: Needle iterable
         Haystack iterable
         Randomize search range (this prevents determinism)

  Output: Start index of the needle iterable in a haystack iterable
          If nothing found, -1 is returned

  Project Los Angeles
  Tegridy Code 2021'''

  need = copy.deepcopy(needle)

  try:
    if randomize:
      idx = haystack.index(need, secrets.randbelow(len(haystack)-len(need)))
    else:
      idx = haystack.index(need)

  except KeyboardInterrupt:
    return -1

  except:
    return -1
    
  return idx

###################################################################################

def Tegridy_Chord_Match(chord1, chord2, match_type=2):

    '''Tegridy Chord Match
     
    Input: Two chords to evaluate
           Match type: 2 = duration, channel, pitch, velocity
                       3 = channel, pitch, velocity
                       4 = pitch, velocity
                       5 = velocity

    Output: Match rating (0-100)
            NOTE: Match rating == -1 means identical source chords
            NOTE: Match rating == 100 means mutual shortest chord

    Project Los Angeles
    Tegridy Code 2021'''

    match_rating = 0

    if chord1 == []:
      return 0
    if chord2 == []:
      return 0

    if chord1 == chord2:
      return -1

    else:
      zipped_pairs = list(zip(chord1, chord2))
      zipped_diff = abs(len(chord1) - len(chord2))

      short_match = [False]
      for pair in zipped_pairs:
        cho1 = ' '.join([str(y) for y in pair[0][match_type:]])
        cho2 = ' '.join([str(y) for y in pair[1][match_type:]])
        if cho1 == cho2:
          short_match.append(True)
        else:
          short_match.append(False)
      
      if True in short_match:
        return 100

      pairs_ratings = []

      for pair in zipped_pairs:
        cho1 = ' '.join([str(y) for y in pair[0][match_type:]])
        cho2 = ' '.join([str(y) for y in pair[1][match_type:]])
        pairs_ratings.append(SM(None, cho1, cho2).ratio())

      match_rating = sum(pairs_ratings) / len(pairs_ratings) * 100

      return match_rating

###################################################################################

def Tegridy_Last_Chord_Finder(chords_list):

    '''Tegridy Last Chord Finder
     
    Input: Flat chords list

    Output: Last detected chord of the chords list
            Last chord start index in the original chords list
            First chord end index in the original chords list

    Project Los Angeles
    Tegridy Code 2021'''

    chords = []
    cho = []

    ptime = 0

    i = 0

    pc_idx = 0
    fc_idx = 0

    chords_list.sort(reverse=False, key=lambda x: x[1])
    
    for cc in chords_list:

      if cc[1] == ptime:
        
        cho.append(cc)

        ptime = cc[1]

      else:
        if pc_idx == 0: 
          fc_idx = chords_list.index(cc)
        pc_idx = chords_list.index(cc)
        
        chords.append(cho)
        
        cho = []
      
        cho.append(cc)
        
        ptime = cc[1]
        
        i += 1
      
    if cho != []: 
      chords.append(cho)
      i += 1
     
    return chords_list[pc_idx:], pc_idx, fc_idx

###################################################################################

def Tegridy_Chords_Generator(chords_list, shuffle_pairs = True, remove_single_notes=False):

    '''Tegridy Score Chords Pairs Generator
     
    Input: Flat chords list
           Shuffle pairs (recommended)

    Output: List of chords
            
            Average time(ms) per chord
            Average time(ms) per pitch
            Average chords delta time

            Average duration
            Average channel
            Average pitch
            Average velocity

    Project Los Angeles
    Tegridy Code 2021'''

    chords = []
    cho = []

    i = 0

    # Sort by start time
    chords_list.sort(reverse=False, key=lambda x: x[1])

    # Main loop
    pcho = chords_list[0]
    for cc in chords_list:
      if cc[1] == pcho[1]:
        
        cho.append(cc)
        pcho = copy.deepcopy(cc)

      else:
        if not remove_single_notes:
          chords.append(cho)
          cho = []
          cho.append(cc)
          pcho = copy.deepcopy(cc)
          
          i += 1
        else:
          if len(cho) > 1:
            chords.append(cho)
          cho = []
          cho.append(cc)
          pcho = copy.deepcopy(cc)
            
          i += 1  
    
    # Averages
    t0 = chords[0][0][1]
    t1 = chords[-1][-1][1]
    tdel = abs(t1 - t0)
    avg_ms_per_chord = int(tdel / i)
    avg_ms_per_pitch = int(tdel / len(chords_list))

    # Delta time
    tds = [int(abs(chords_list[i-1][1]-chords_list[i][1]) / 1) for i in range(1, len(chords_list))]
    if len(tds) != 0: avg_delta_time = int(sum(tds) / len(tds))

    # Chords list attributes
    p = int(sum([int(y[4]) for y in chords_list]) / len(chords_list))
    d = int(sum([int(y[2]) for y in chords_list]) / len(chords_list))
    c = int(sum([int(y[3]) for y in chords_list]) / len(chords_list))
    v = int(sum([int(y[5]) for y in chords_list]) / len(chords_list))

    # Final shuffle
    if shuffle_pairs:
      random.shuffle(chords)

    return chords, [avg_ms_per_chord, avg_ms_per_pitch, avg_delta_time], [d, c, p, v]

###################################################################################

def Tegridy_Chords_List_Music_Features(chords_list, st_dur_div = 1, pitch_div = 1, vel_div = 1):

    '''Tegridy Chords List Music Features
     
    Input: Flat chords list

    Output: A list of the extracted chords list's music features

    Project Los Angeles
    Tegridy Code 2021'''

    chords_list1 = [x for x in chords_list if x]
    chords_list1.sort(reverse=False, key=lambda x: x[1])
    
    # Features extraction code

    melody_list = []
    bass_melody = []
    melody_chords = []
    mel_avg_tds = []
    mel_chrd_avg_tds = []
    bass_melody_avg_tds = []

    #print('Grouping by start time. This will take a while...')
    values = set(map(lambda x:x[1], chords_list1)) # Non-multithreaded function version just in case

    groups = [[y for y in chords_list1 if y[1]==x and len(y) == 6] for x in values] # Grouping notes into chords while discarting bad notes...

    #print('Sorting events...')
    for items in groups:
        items.sort(reverse=True, key=lambda x: x[4]) # Sorting events by pitch
        melody_list.append(items[0]) # Creating final melody list
        melody_chords.append(items) # Creating final chords list
        bass_melody.append(items[-1]) # Creating final bass melody list

    #print('Final sorting by start time...')      
    melody_list.sort(reverse=False, key=lambda x: x[1]) # Sorting events by start time
    melody_chords.sort(reverse=False, key=lambda x: x[0][1]) # Sorting events by start time
    bass_melody.sort(reverse=False, key=lambda x: x[1]) # Sorting events by start time

    # Extracting music features from the chords list
    
    # Melody features
    mel_avg_pitch = int(sum([y[4] for y in melody_list]) / len(melody_list) / pitch_div)
    mel_avg_dur = int(sum([int(y[2] / st_dur_div) for y in melody_list]) / len(melody_list))
    mel_avg_vel = int(sum([int(y[5] / vel_div) for y in melody_list]) / len(melody_list))
    mel_avg_chan = int(sum([int(y[3]) for y in melody_list]) / len(melody_list))
    
    mel_tds = [int(abs(melody_list[i-1][1]-melody_list[i][1])) for i in range(1, len(melody_list))]
    if len(mel_tds) != 0: mel_avg_tds = int(sum(mel_tds) / len(mel_tds) / st_dur_div)
    
    melody_features = [mel_avg_tds, mel_avg_dur, mel_avg_chan, mel_avg_pitch, mel_avg_vel]

    # Chords list features
    mel_chrd_avg_pitch = int(sum([y[4] for y in chords_list1]) / len(chords_list1) / pitch_div)
    mel_chrd_avg_dur = int(sum([int(y[2] / st_dur_div) for y in chords_list1]) / len(chords_list1))
    mel_chrd_avg_vel = int(sum([int(y[5] / vel_div) for y in chords_list1]) / len(chords_list1))
    mel_chrd_avg_chan = int(sum([int(y[3]) for y in chords_list1]) / len(chords_list1))
    
    mel_chrd_tds = [int(abs(chords_list1[i-1][1]-chords_list1[i][1])) for i in range(1, len(chords_list1))]
    if len(mel_tds) != 0: mel_chrd_avg_tds = int(sum(mel_chrd_tds) / len(mel_chrd_tds) / st_dur_div)
    
    chords_list_features = [mel_chrd_avg_tds, mel_chrd_avg_dur, mel_chrd_avg_chan, mel_chrd_avg_pitch, mel_chrd_avg_vel]

    # Bass melody features
    bass_melody_avg_pitch = int(sum([y[4] for y in bass_melody]) / len(bass_melody) / pitch_div)
    bass_melody_avg_dur = int(sum([int(y[2] / st_dur_div) for y in bass_melody]) / len(bass_melody))
    bass_melody_avg_vel = int(sum([int(y[5] / vel_div) for y in bass_melody]) / len(bass_melody))
    bass_melody_avg_chan = int(sum([int(y[3]) for y in bass_melody]) / len(bass_melody))
    
    bass_melody_tds = [int(abs(bass_melody[i-1][1]-bass_melody[i][1])) for i in range(1, len(bass_melody))]
    if len(bass_melody_tds) != 0: bass_melody_avg_tds = int(sum(bass_melody_tds) / len(bass_melody_tds) / st_dur_div)
    
    bass_melody_features = [bass_melody_avg_tds, bass_melody_avg_dur, bass_melody_avg_chan, bass_melody_avg_pitch, bass_melody_avg_vel]
    
    # A list to return all features
    music_features = []

    music_features.extend([len(chords_list1)]) # Count of the original chords list notes
    
    music_features.extend(melody_features) # Extracted melody features
    music_features.extend(chords_list_features) # Extracted chords list features
    music_features.extend(bass_melody_features) # Extracted bass melody features
    music_features.extend([sum([y[4] for y in chords_list1])]) # Sum of all pitches in the original chords list

    return music_features

###################################################################################

def Tegridy_Transform(chords_list, to_pitch=60, to_velocity=-1):

    '''Tegridy Transform
     
    Input: Flat chords list
           Desired average pitch (-1 == no change)
           Desired average velocity (-1 == no change)

    Output: Transformed flat chords list

    Project Los Angeles
    Tegridy Code 2021'''

    transformed_chords_list = []

    chords_list.sort(reverse=False, key=lambda x: x[1])

    chords_list_features = Optimus_Signature(chords_list)[1]

    pitch_diff = int((chords_list_features[0] + chords_list_features[1] + chords_list_features[2]) / 3) - to_pitch
    velocity_diff = chords_list_features[4] - to_velocity

    for c in chords_list:
      cc = copy.deepcopy(c)
      if c[3] != 9: # Except the drums
        if to_pitch != -1: 
          cc[4] = c[4] - pitch_diff
        
        if to_velocity != -1: 
          cc[5] = c[5] - velocity_diff
      
      transformed_chords_list.append(cc)

    return transformed_chords_list

###################################################################################

def Tegridy_MIDI_Zip_Notes_Summarizer(chords_list, match_type = 4):

    '''Tegridy MIDI Zip Notes Summarizer
     
    Input: Flat chords list / SONG
           Match type according to 'note' event of MIDI.py

    Output: Summarized chords list
            Number of summarized notes
            Number of dicarted notes

    Project Los Angeles
    Tegridy Code 2021'''

    i = 0
    j = 0
    out1 = []
    pout = []
 

    for o in chords_list:

      # MIDI Zip

      if o[match_type:] not in pout:
        pout.append(o[match_type:])
        
        out1.append(o)
        j += 1
      
      else:
        i += 1

    return out1, i

###################################################################################

def Tegridy_Score_Chords_Pairs_Generator(chords_list, shuffle_pairs = True, remove_single_notes=False):

    '''Tegridy Score Chords Pairs Generator
     
    Input: Flat chords list
           Shuffle pairs (recommended)

    Output: Score chords pairs list
            Number of created pairs
            Number of detected chords

    Project Los Angeles
    Tegridy Code 2021'''

    chords = []
    cho = []

    i = 0
    j = 0

    chords_list.sort(reverse=False, key=lambda x: x[1])
    pcho = chords_list[0]
    for cc in chords_list:
      if cc[1] == pcho[1]:
        
        cho.append(cc)
        pcho = copy.deepcopy(cc)

      else:
        if not remove_single_notes:
          chords.append(cho)
          cho = []
          cho.append(cc)
          pcho = copy.deepcopy(cc)
          
          i += 1
        else:
          if len(cho) > 1:
            chords.append(cho)
          cho = []
          cho.append(cc)
          pcho = copy.deepcopy(cc)
            
          i += 1  
    
    chords_pairs = []
    for i in range(len(chords)-1):
      chords_pairs.append([chords[i], chords[i+1]])
      j += 1
    if shuffle_pairs: random.shuffle(chords_pairs)

    return chords_pairs, j, i

###################################################################################

def Tegridy_Sliced_Score_Pairs_Generator(chords_list, number_of_miliseconds_per_slice=2000, shuffle_pairs = False):

    '''Tegridy Sliced Score Pairs Generator
     
    Input: Flat chords list
           Number of miliseconds per slice

    Output: Sliced score pairs list
            Number of created slices

    Project Los Angeles
    Tegridy Code 2021'''

    chords = []
    cho = []

    time = number_of_miliseconds_per_slice 

    i = 0

    chords_list1 = [x for x in chords_list if x]
    chords_list1.sort(reverse=False, key=lambda x: x[1])
    pcho = chords_list1[0]
    for cc in chords_list1[1:]:

      if cc[1] <= time:
        
        cho.append(cc)

      else:
        if cho != [] and pcho != []: chords.append([pcho, cho])
        pcho = copy.deepcopy(cho)
        cho = []
        cho.append(cc)
        time += number_of_miliseconds_per_slice
        i += 1
      
    if cho != [] and pcho != []: 
      chords.append([pcho, cho])
      pcho = copy.deepcopy(cho)
      i += 1
    
    if shuffle_pairs: random.shuffle(chords)

    return chords, i

###################################################################################

def Tegridy_Timings_Converter(chords_list, 
                              max_delta_time = 1000, 
                              fixed_start_time = 250, 
                              start_time = 0,
                              start_time_multiplier = 1,
                              durations_multiplier = 1):

    '''Tegridy Timings Converter
     
    Input: Flat chords list
           Max delta time allowed between notes
           Fixed start note time for excessive gaps

    Output: Converted flat chords list

    Project Los Angeles
    Tegridy Code 2021'''

    song = chords_list

    song1 = []

    p = song[0]

    p[1] = start_time

    time = start_time

    delta = [0]

    for i in range(len(song)):
      if song[i][0] == 'note':
        ss = copy.deepcopy(song[i])
        if song[i][1] != p[1]:
          
          if abs(song[i][1] - p[1]) > max_delta_time:
            time += fixed_start_time
          else:
            time += abs(song[i][1] - p[1])
            delta.append(abs(song[i][1] - p[1]))

          ss[1] = int(round(time * start_time_multiplier, -1))
          ss[2] = int(round(song[i][2] * durations_multiplier, -1))
          song1.append(ss)
          
          p = copy.deepcopy(song[i])
        else:
          
          ss[1] = int(round(time * start_time_multiplier, -1))
          ss[2] = int(round(song[i][2] * durations_multiplier, -1))
          song1.append(ss)
          
          p = copy.deepcopy(song[i])
      
      else:
        ss = copy.deepcopy(song[i])
        ss[1] = time
        song1.append(ss)
        
    average_delta_st = int(sum(delta) / len(delta))
    average_duration = int(sum([y[2] for y in song1 if y[0] == 'note']) / len([y[2] for y in song1 if y[0] == 'note']))

    song1.sort(reverse=False, key=lambda x: x[1])

    return song1, time, average_delta_st, average_duration

###################################################################################

def Tegridy_Score_Slicer(chords_list, number_of_miliseconds_per_slice=2000, overlap_notes = 0, overlap_chords=False):

    '''Tegridy Score Slicer
     
    Input: Flat chords list
           Number of miliseconds per slice

    Output: Sliced chords list
            Number of created slices

    Project Los Angeles
    Tegridy Code 2021'''

    chords = []
    cho = []

    time = number_of_miliseconds_per_slice
    ptime = 0

    i = 0

    pc_idx = 0

    chords_list.sort(reverse=False, key=lambda x: x[1])
    
    for cc in chords_list:

      if cc[1] <= time:
        
        cho.append(cc)

        if ptime != cc[1]:
          pc_idx = cho.index(cc)

        ptime = cc[1]


      else:

        if overlap_chords:
          chords.append(cho)
          cho.extend(chords[-1][pc_idx:])
        
        else:
          chords.append(cho[:pc_idx])
        
        cho = []
      
        cho.append(cc)
        
        time += number_of_miliseconds_per_slice
        ptime = cc[1]
        
        i += 1
      
    if cho != []: 
      chords.append(cho)
      i += 1
    
    return [x for x in chords if x], i

###################################################################################

def Tegridy_TXT_Tokenizer(input_TXT_string, line_by_line_TXT_string=True):

    '''Tegridy TXT Tokenizer
     
    Input: TXT String

    Output: Tokenized TXT string + forward and reverse dics
    
    Project Los Angeles
    Tegridy Code 2021'''

    print('Tegridy TXT Tokenizer')

    if line_by_line_TXT_string:
      T = input_TXT_string.split()
    else:
      T = input_TXT_string.split(' ')

    DIC = dict(zip(T, range(len(T))))
    RDIC = dict(zip(range(len(T)), T))

    TXTT = ''

    for t in T:
      try:
        TXTT += chr(DIC[t])
      except:
        print('Error. Could not finish.')
        return TXTT, DIC, RDIC
    
    print('Done!')
    
    return TXTT, DIC, RDIC

###################################################################################

def Tegridy_TXT_DeTokenizer(input_Tokenized_TXT_string, RDIC):

    '''Tegridy TXT Tokenizer
     
    Input: Tokenized TXT String
           

    Output: DeTokenized TXT string
    
    Project Los Angeles
    Tegridy Code 2021'''

    print('Tegridy TXT DeTokenizer')

    Q = list(input_Tokenized_TXT_string)
    c = 0
    RTXT = ''
    for q in Q:
      try:
        RTXT += RDIC[ord(q)] + chr(10)
      except:
        c+=1

    print('Number of errors:', c)

    print('Done!')

    return RTXT

###################################################################################

def Tegridy_List_Slicer(input_list, slices_length_in_notes=20):

  '''Input: List to slice
            Desired slices length in notes
     
     Output: Sliced list of lists
     
     Project Los Angeles
     Tegridy Code 2021'''

  for i in range(0, len(input_list), slices_length_in_notes):
     yield input_list[i:i + slices_length_in_notes]
    
###################################################################################    
    
def Tegridy_Split_List(list_to_split, split_value=0):
    
    # src courtesy of www.geeksforgeeks.org
  
    # using list comprehension + zip() + slicing + enumerate()
    # Split list into lists by particular value
    size = len(list_to_split)
    idx_list = [idx + 1 for idx, val in
                enumerate(list_to_split) if val == split_value]


    res = [list_to_split[i: j] for i, j in
            zip([0] + idx_list, idx_list + 
            ([size] if idx_list[-1] != size else []))]
  
    # print result
    # print("The list after splitting by a value : " + str(res))
    
    return res

###################################################################################

# This is the end of the TMIDI X Python module

###################################################################################
