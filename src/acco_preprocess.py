# Author : Chenhe Gu, last edited 2021.12.10
# This script takes as input the result of chorderator located in generated,
# and massages the resulting chords so the file can be properly used by
# AccoMontage for further accompaniment generation.

# More specifically, the script does the following tasks:
# 0. Fix the key of the generated chord progression
# 1. making all notes in a chord the same length
# 2. limit the chords to 3 or 4 notes only while maintaining the chord signature
#    as much as possible
# 3. fill in chords coherently when the existing chord does not contain
#    a suitable chord sequence

import pretty_midi as pretty
import time
import datetime

from pretty_midi.containers import Note

input_mid_path = './generated/generated.mid'

song_name = 'closer'
tempo = 100                   # default output of chorderator
oritinal_key = 'D#'             # for levels

input_midi = pretty.PrettyMIDI(input_mid_path)
input_melody_track, input_chord_track = input_midi.instruments[0], input_midi.instruments[1]

input_chords = input_chord_track.notes
input_melody = input_melody_track.notes

time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

prepped = pretty.PrettyMIDI(initial_tempo=tempo)
output_mid_path = './accomontage_prepped/' + song_name + '-' + time + '.mid'
output_chords = pretty.Instrument(program=pretty.instrument_name_to_program('Acoustic Grand Piano'))

output_melody_track = input_melody_track
prepped.instruments.append(output_melody_track)

acceptable_note_differences = {'(4, 3)': 'maj/0', 
                        '(3, 5)': 'maj/1', 
                        '(5, 4)': 'maj/2', 

                        '(3, 4)': 'min/0', 
                        '(4, 5)': 'min/1', 
                        '(5, 3)': 'min/2',

                        '(4, 4)': 'aug/0',
                        
                        '(3, 3)': 'dim/0',
                        '(3, 6)': 'dim/1',
                        '(6, 3)': 'dim/2',

                        '(4, 3, 3)': '7/0',
                        '(3, 3, 2)': '7/1',
                        '(3, 2, 4)': '7/2',
                        '(2, 4, 3)': '7/3',

                        '(4, 3, 4)': 'maj7/0',
                        '(3, 4, 1)': 'maj7/1',
                        '(4, 1, 4)': 'maj7/2',
                        '(1, 4, 3)': 'maj7/3',

                        '(3, 4, 3)': 'min7/0',
                        '(4, 3, 2)': 'min7/1',
                        '(3, 2, 3)': 'min7/2',
                        '(2, 3, 4)': 'min7/3',

                        '(3, 4, 4)': 'minmaj7/0',
                        '(4, 4, 1)': 'minmaj7/1',
                        '(4, 1, 3)': 'minmaj7/2',
                        '(1, 3, 4)': 'minmaj7/3',

                        '(3, 3, 3)': 'dim7/0',

                        '(3, 3, 4)': 'hdim7/0',
                        '(3, 4, 2)': 'hdim7/1',
                        '(4, 2, 3)': 'hdim7/2',
                        '(2, 3, 3)': 'hdim7/3',
                        }

acceptable_first_and_second_diffs_four_notes = {1, 2, 3, 4}
acceptable_first_diffs_three_notes = {3, 4, 5, 6}

def is_chord_num_notes_valid(notes):
    return len(notes) == 3 or len(notes) == 4

def is_chord_length_valid(notes):
    for note in notes:
        if note.start != notes[0].start or note.end != notes[0].end:
            return False
    
    return True

def is_chord_note_diff_valid(notes):
    sorted_notes = sorted(notes, key = lambda x: x.start)

    if len(notes) == 3:
        diff = str(((sorted_notes[1].pitch - sorted_notes[0].pitch), (sorted_notes[2].pitch - sorted_notes[1].pitch)))
    else:   # notes length == 4
        diff = str((((sorted_notes[1].pitch - sorted_notes[0].pitch), (sorted_notes[2].pitch - sorted_notes[1].pitch), (sorted_notes[3].pitch - sorted_notes[2].pitch))))

    if diff not in acceptable_note_differences:
            return False
    
    return True

def is_chord_valid(notes):
    return is_chord_length_valid(notes) and is_chord_num_notes_valid(notes) and is_chord_note_diff_valid(notes)

def maximize_duration(notes, max):
    maximized = []
    for note in notes:
        maximized.append(pretty.pretty_midi.Note(note.velocity, note.pitch, note.start, max))
    
    return maximized

def minimize_duration(notes, min):
    minimized = []
    for note in notes:
        minimized.append(pretty.pretty_midi.Note(note.velocity, note.pitch, note.start, min))
    
    return minimized

def equalize_duration(notes):
    start = notes[0].start

    min = notes[0].end
    max = notes[0].end

    tot = 0.0
    for note in notes:
        end = note.end
        if end > max:
            max = end
        if end < min:
            min = end
        
        tot += end - start
    
    if min == max:
        return notes

    avg = tot / len(notes)

    if avg - min > max - avg:
        return minimize_duration(notes, min)
    else:
        return maximize_duration(notes, max)

def calc_difference_vector(notes):
    diff_vector = []
    for index, note in enumerate(notes):
        if index > 0:
            diff_vector.append(note.pitch - notes[index - 1].pitch)
    
    return diff_vector

def format_diff_tuple_key(diff_1, diff_2, diff_3 = None):
    if diff_3 == None:
        return str((diff_1, diff_2))
    else:
        return str((diff_1, diff_2, diff_3))

def partial_diff(lower_note_index, higher_note_index, diff_vector):
    tot_diff = 0
    for i in range(lower_note_index, higher_note_index):
        tot_diff += diff_vector[i]

    return tot_diff
# prioritize 4-note chords
# output in the format of a list of tuples 
# where each tuple is structured as 
# (starting note index, [list of differences in partials]) 
def get_all_possible_chords(diff_vector):

    possible_four_note_chords = []
    for index in range(len(diff_vector) + 1):
        for second_index in range(index + 1, len(diff_vector) + 1):
            first_diff = partial_diff(index, second_index, diff_vector)
            if first_diff not in acceptable_first_and_second_diffs_four_notes:
                continue

            for third_index in range(second_index + 1, len(diff_vector) + 1):
                second_diff = partial_diff(second_index, third_index, diff_vector)
                if second_diff not in acceptable_first_and_second_diffs_four_notes:
                    continue
                
                for fourth_index in range(third_index + 1, len(diff_vector) + 1):
                    third_diff = partial_diff(third_index, fourth_index, diff_vector)

                    if format_diff_tuple_key(first_diff, second_diff, third_diff) in acceptable_note_differences:
                        possible_four_note_chords.append((index, [first_diff, second_diff, third_diff]))
    
    if len(possible_four_note_chords) != 0:
        return possible_four_note_chords
    
    print('no valid four-note chords found')
    possible_three_note_chords = []
    for index in range(len(diff_vector) + 1):
        for second_index in range(index + 1, len(diff_vector) + 1):
            first_diff = partial_diff(index, second_index, diff_vector)
            if first_diff not in acceptable_first_diffs_three_notes:
                continue

            for third_index in range(second_index + 1, len(diff_vector) + 1):
                second_diff = partial_diff(second_index, third_index, diff_vector)

                if format_diff_tuple_key(first_diff, second_diff) in acceptable_note_differences:
                    possible_three_note_chords.append((index, [first_diff, second_diff]))
    
    if len(possible_three_note_chords) != 0:
        return possible_three_note_chords
    else:
        print('no valid three-note chords found')
        return None
    
def pitch_sum(possible_chord, sorted_notes):
    base_pitch = sorted_notes[possible_chord[0]].pitch
    curr_sum = base_pitch
    for diff in possible_chord[1]:
        curr_sum += base_pitch + diff

    return curr_sum

# the case where we can take a chord out of the existing chord
# we choose higher notes over lower notes as they have a more
# significant effect on the listening experience
def find_optimal_chord(possible_chords, sorted_notes):
    
    curr_optimal = possible_chords[0]
    max_pitch_sum = pitch_sum(possible_chords[0], sorted_notes)

    for chord in possible_chords:
        if pitch_sum(chord, sorted_notes) > max_pitch_sum:
            curr_optimal = chord
            max_pitch_sum = pitch_sum(chord, sorted_notes)
    
    return curr_optimal

# maps the diff list to notes and return the chord
# as a list of pretty midi notes
def diff_vector_to_chord(optimal, sorted_notes):
    note_1 = sorted_notes[optimal[0]]
    chord = [note_1]

    curr_note_pitch = note_1.pitch
    for diff in optimal[1]:
        curr_note_pitch += diff
        for note in sorted_notes:
            if note.pitch == curr_note_pitch:
                chord.append(note)
    
    if (len(chord) != len(optimal[1]) + 1):
        raise Exception('resulting chord length', len(chord))
    
    return chord

# if we have no choices of either 4-note chords or 3-note chords,
# we reference the melody track and generate a 3-note major based
# on that note at this time point
def fill_in_basic_chord(desired_start_time, end_time, velocity):

    def is_playing_at_time(note):
        return note.start <= desired_start_time and note.end >= desired_start_time

    notes_playing = list(filter(is_playing_at_time, input_melody))
    if len(notes_playing) != 0:
        closest_time = notes_playing[0].start
        curr_closest_note = notes_playing[0]
        for note in notes_playing:
            if note.start > closest_time:
                curr_closest_note = note
        
        # construct simple 3-note chord based on note
        pitch_1 = curr_closest_note.pitch - 12
        pitch_2 = pitch_1 - 4
        pitch_3 = pitch_1 + 3

        note_1 = pretty.pretty_midi.Note(velocity, pitch_1, desired_start_time, end_time)
        note_2 = pretty.pretty_midi.Note(velocity, pitch_2, desired_start_time, end_time)
        note_3 = pretty.pretty_midi.Note(velocity, pitch_3, desired_start_time, end_time)
        return [note_2, note_1, note_3]

    print('no melody at this time point')
    return None

num_partials_to_C_key = {
    'G#' : -4,
    'A' : -3,
    'A#' : -2,
    'B' : -1,
    'C' : 0,
    'C#' : 1,
    'D' : 2,
    'D#' : 3,
    'E' : 4,
    'F' : 5,
    'F#' : 6,
    'G' : 7,
}

def adjust_key(original_key, all_notes_in_track):
    adjusted_notes = []
    
    partial_offset = num_partials_to_C_key[original_key]
    for note in all_notes_in_track:
        adjusted_note = pretty.pretty_midi.Note(note.velocity, note.pitch + partial_offset, note.start, note.end)
        adjusted_notes.append(adjusted_note)

    return adjusted_notes

# pipeline of prepping one chord:
def prep_chord(chord):
    equalized = equalize_duration(chord)
    sorted_by_pitch = sorted(equalized, key = lambda x : x.pitch)
    diff_vector = calc_difference_vector(sorted_by_pitch)

    possible_chords_diff_vectors = get_all_possible_chords(diff_vector)

    if possible_chords_diff_vectors != None:
        optimal_diff = find_optimal_chord(possible_chords_diff_vectors, sorted_by_pitch)
        res = diff_vector_to_chord(optimal_diff, sorted_by_pitch)

    else:       # we couldn't interpolate a chord from what was generated

        # we extract the start, end and velocity information from
        # the first note to feed to the fill_in_basic_chord function,
        # since it's the same for all notes anyway
        desired_start = chord[0].start
        desired_end = chord[0].end
        desired_velocity = chord[0].velocity

        res = fill_in_basic_chord(desired_start, desired_end, desired_velocity)

    if res != None:
        if not is_chord_valid(res):
            print("oof bug alert")

    return res
# initialize output chord track 
output_chord_track = pretty.Instrument(program=pretty.instrument_name_to_program('Voice Oohs'))

# first we sort the notes according to start time for better processing
input_chords = sorted(input_chords, key = lambda x: x.start)

# we then adjust the key of the entire track
adjusted_input_chords = adjust_key(oritinal_key, input_chords)

# we then parse the notes into chords judging by their starting time
curr_chord = []
curr_chord_start = 0

for note in adjusted_input_chords:
    if note.start == curr_chord_start:
        curr_chord.append(note)

    else:   # we start to see notes from the next chord
        if len(curr_chord) > 2:
            if prep_chord(curr_chord) != None:
                output_chord_track.notes += prep_chord(curr_chord)  # we prep the chord that's completed
        
        curr_chord = [note]
        curr_chord_start = note.start

output_chord_track.notes += prep_chord(curr_chord)          # we prep the last chord in the sequence
prepped.instruments.append(output_chord_track) 

print('prepping complete, writing to output')
prepped.write(output_mid_path)