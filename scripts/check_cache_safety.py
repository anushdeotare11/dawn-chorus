import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from card import generate_field_card
from detect import Detection

print("=== PART 1: TEST GEMMA CARD GENERATOR ===")

# (a) Empty detection list
print("\n(a) Empty detection list:")
card, warn, badge = generate_field_card(
    detections=[],
    missed_species=["Asian Koel", "House Crow", "Common Myna"],
    walk_date="2026-10-08",
    time_of_day="Dawn",
    duration_mmss="30:00"
)
print(f"Badge: {badge}")
print(f"Warning: {warn}")
print(f"Card:\n{card}")

# (b) List of 3 real species
print("\n(b) List of 3 real species:")
d1 = Detection("Indian Peafowl", "Pavo cristatus", 2, 0.95, 10)
d2 = Detection("Rose-ringed Parakeet", "Psittacula krameri", 5, 0.88, 45)
d3 = Detection("Coppersmith Barbet", "Psilopogon haemacephalus", 1, 0.55, 120)
card, warn, badge = generate_field_card(
    detections=[d1, d2, d3],
    missed_species=["Asian Koel", "House Crow"],
    walk_date="2026-10-08",
    time_of_day="Day",
    duration_mmss="25:10"
)
print(f"Badge: {badge}")
print(f"Warning: {warn}")
print(f"Card:\n{card}")

# (c) Deliberately tempting case (asking for a bird not in the list indirectly, or providing 0 confidence)
print("\n(c) Deliberately tempting case (Only 1 rare bird, checking if it invents common ones):")
d_rare = Detection("Crab-plover", "Dromas ardeola", 1, 0.8, 60)
card, warn, badge = generate_field_card(
    detections=[d_rare],
    missed_species=["Brahminy Starling", "Indian Cuckoo"],
    walk_date="2026-10-08",
    time_of_day="Dusk",
    duration_mmss="20:00"
)
print(f"Badge: {badge}")
print(f"Warning: {warn}")
print(f"Card:\n{card}")
