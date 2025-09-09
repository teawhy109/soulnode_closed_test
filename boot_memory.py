from soulnode_memory import SoulNodeMemory

core_facts = [
    ("Ty", "full_name", "Tyease Myron Jerome Butler"),
    ("Ty", "birthday", "March 27, 1976"),
    ("Ty", "child", "Kobe"),
    ("Ty", "child", "TJ"),
    ("Ty", "child", "Ivy"),
    ("TJ", "father", "Ty"),
    ("Kobe", "father", "Ty"),
    ("Ivy", "father", "Ty"),
    ("Ty", "mission", "Create generational wealth for TJ Kobe and Ivy"),
    ("Kobe", "nickname", "Chef Hat King"),
    ("Ty", "health_protocol", "20-hour fasting, Dexcom G7, magnesium, ACV, berberine"),
    ("SoulNode", "creator", "Ty"),
    ("SoulNode", "purpose", "Be Ty’s AI co-pilot with memory, emotion, and loyalty")
]

# Optional: Still runnable directly if needed
if __name__ == "__main__":
    memory = SoulNodeMemory()
    for subj, rel, obj in core_facts:
        memory.save_fact(subj, rel, obj)
    print("✅ Core memory injected manually.")