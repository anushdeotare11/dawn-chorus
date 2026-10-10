import json
import glob
def summarize_walks():
    walk_files = glob.glob("walks/*.json")
    if not walk_files:
        print("No walks found.")
        return

    headers = ["Date", "Time of Day", "Duration", "Species Detected", "Bingo Score", "Other Heard", "Screen Time", "Grass Ratio", "Processing Time"]
    rows = []

    for f in sorted(walk_files):
        with open(f, "r", encoding="utf-8") as file:
            data = json.load(file)
            
            if data.get("is_sample"):
                continue
                
            date = data.get("walk_date", "")
            tod = data.get("time_of_day", "")
            duration = data.get("duration_mmss", "")
            detected_count = data.get("found_count", 0)
            bingo_score = data.get("bingo_score", "0/0")
            
            bingo_species = set(data.get("bingo_species", []))
            found_species = {d.get("common_name") for d in data.get("detections", [])}
            other_heard = len(found_species - bingo_species)
            
            # Estimate screen time based on simple duration ratio for summary purposes if not stored explicitly
            proc_time = data.get("processing_time_s", 0.0)
            
            rows.append([
                date, tod, duration, str(detected_count), bingo_score, str(other_heard),
                "Unknown", "Unknown", f"{proc_time:.1f}s"
            ])

    if not rows:
        print("No real walks found (only sample walks or empty directory). Go outside!")
        return

    # Print table
    col_widths = [max(len(str(item)) for item in col) for col in zip(*rows, headers)]
    format_str = " | ".join(f"{{:<{w}}}" for w in col_widths)
    
    print(format_str.format(*headers))
    print("-|-".join("-" * w for w in col_widths))
    
    with open("walks_summary.md", "w", encoding="utf-8") as out:
        out.write("| " + format_str.format(*headers) + " |\n")
        out.write("|" + "|".join("-" * (w+2) for w in col_widths) + "|\n")
        for row in rows:
            print(format_str.format(*row))
            out.write("| " + format_str.format(*row) + " |\n")

if __name__ == "__main__":
    summarize_walks()
