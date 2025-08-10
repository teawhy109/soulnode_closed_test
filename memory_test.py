from soulnode_memory import SoNoMemory

memory = SoNoMemory()

# Save a test memory
memory.remember("My name is Ty.", "Okay, your name is Ty.")

# Try to recall it
print(memory.recall("My name is Ty."))
print(memory.recall("Who am I?")) # Should say: I don't remember that yet.