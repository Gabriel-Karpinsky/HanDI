import mido
from mido import Message, open_output
import time

# List available MIDI output ports
print("Available MIDI Output Ports:")
print(mido.get_output_names())

# Open the correct MIDI port for VCV Rack
midi_out = open_output("Python to VCV 1")  # Adjust if needed

note = 60  # Default note (Middle C)
velocity = 100  # Default volume
playing_notes = set()  # Keep track of active notes

# Function to play a note
def play_note():
    global note, velocity, playing_notes
    midi_out.send(Message('note_on', note=note, velocity=velocity))  # Start note
    playing_notes.add(note)  # Track active note
    print(f"Playing note {note} with velocity {velocity}")

# Function to stop a specific note
def stop_note():
    global note, playing_notes
    if note in playing_notes:
        midi_out.send(Message('note_off', note=note))  # Stop note
        playing_notes.remove(note)  # Remove from active notes
        print(f"Stopped note {note}")

# Function to stop all active notes
def stop_all_notes():
    global playing_notes
    for n in playing_notes:
        midi_out.send(Message('note_off', note=n))  # Stop each note
    playing_notes.clear()
    # Send "All Notes Off" control message (MIDI CC 123)
    midi_out.send(Message('control_change', control=123, value=0))
    print("All notes stopped.")

# User input loop
print("Commands: 'vol <0-127>' (change volume), 'note <MIDI number>' (change pitch), 'play' (play note), 'stop' (stop note), 'exit' (stop all & quit).")

while True:
    user_input = input("Enter command: ")

    if user_input.lower() == "exit":
        stop_all_notes()  # Ensure all notes stop before quitting
        break

    elif user_input.lower() == "play":
        play_note()

    elif user_input.lower() == "stop":
        stop_note()

    else:
        try:
            command, value = user_input.split()
            value = int(value)

            if command == "vol" and 0 <= value <= 127:
                velocity = value
                print(f"Volume changed to {value}")

            elif command == "note" and 0 <= value <= 127:
                note = value
                print(f"Pitch changed to MIDI Note {value}")

            else:
                print("Invalid command. Use 'vol <0-127>', 'note <MIDI number>', 'play', 'stop', or 'exit'.")

        except ValueError:
            print("Invalid input. Use 'vol <0-127>', 'note <MIDI number>', 'play', 'stop', or 'exit'.")

# Ensure all notes are turned off before exiting
stop_all_notes()
print("MIDI notes stopped. Exiting...")