"""Build the Gemma prompt and return a field card about the walk."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Optional
import re

import config
from detect import Detection

def get_gemma_status() -> tuple[str, str, str]:
    """Check if Ollama and the Gemma model are running.
    
    Returns:
        (state, color, message): state can be 'ready', 'not running', or 'model missing'.
    """
    try:
        import ollama
        import httpx
        
        # Lightweight check with 2s timeout
        client = ollama.Client(host="http://localhost:11434", timeout=2.0)
        models = client.list()
        
        has_model = any(m.get("model", "").startswith(config.OLLAMA_MODEL) for m in models.get("models", []))
        if has_model:
            return "ready", "var(--success-green, green)", "Ready."
        else:
            return "model missing", "var(--warning-amber, amber)", f"Gemma model not found. Run: ollama pull {config.OLLAMA_MODEL}"
            
    except ImportError:
        return "not running", "var(--warning-amber, amber)", "The `ollama` package is not installed."
    except (ConnectionError, Exception) as e: # Catch all since httpx might throw various errors
        import httpx
        if isinstance(e, (httpx.ConnectError, httpx.TimeoutException, ConnectionError)):
            pass
        return "not running", "var(--warning-amber, amber)", "Gemma isn't running. Open the Ollama app (or run `ollama serve`), then press Retry. Your detections are fine; here is a template card meanwhile."

def _build_prompt(
    detections: list[Detection],
    missed_species: list[str],
    walk_date: str,
    time_of_day: str,
    duration_mmss: str,
    allowed_species: list[str],
) -> str:
    detection_data = [
        {
            "common_name": d.common_name,
            "scientific_name": d.scientific_name,
            "detection_windows": d.count, # number of 3-second moments
            "max_confidence": d.max_confidence,
            "first_heard": d.first_heard_mmss,
        }
        for d in detections
    ]

    payload = {
        "walk_date": walk_date,
        "time_of_day": time_of_day,
        "duration": duration_mmss,
        "detected_species": detection_data,
        "missed_bingo_species": missed_species,
        "ALLOWED_SPECIES_LIST": allowed_species,
    }

    prompt = f"""You are a friendly naturalist writing a short field card about an offline bird-listening walk.

Here is the walk data as JSON:
{json.dumps(payload, indent=2)}

Write a field card following these rules strictly:
1. Start directly with a one-line summary of the walk (date, time of day, duration).
2. Explicitly mention every detected species by its exact common name.
3. Write one short sentence per detected bird — mention what makes it distinctive or what its call sounds like. Keep each sentence concise (~20 words).
4. If a bird's max_confidence is below 0.7, honestly note it was a tentative or uncertain detection.
5. End with a "Listen for these next time" line naming up to 3 of the missed bingo species.
6. Total length: Keep the total field card summary concise and under 150 words.
7. Operating mode: Strictly offline local processing. Do NOT include any web references, web links, online URLs, or external internet queries.

STRICT GROUNDING RULES:
- Output ONLY the field card text itself. Do NOT include introductory text.
- Only mention species that appear in the ALLOWED_SPECIES_LIST. Do NOT invent any species or sightings.
- If a bird name is not in the ALLOWED_SPECIES_LIST, do not write it under any circumstances.
- Do NOT invent statistics, counts, or facts not present in the data.
- NEVER state a number of individual birds (e.g. do not say "4 Common Mynas"). The "detection_windows" field is the number of 3-second moments in which the bird was heard. Use phrases like "heard repeatedly" or "heard in {payload['detected_species'][0]['detection_windows'] if payload['detected_species'] else 0} moments".
- Do NOT claim certainty beyond the confidence values provided."""

    return prompt


def _template_card(
    detections: list[Detection],
    missed_species: list[str],
    walk_date: str,
    time_of_day: str,
    duration_mmss: str,
) -> str:
    lines = [
        f"🌿 Field Card — {walk_date} ({time_of_day})",
        f"Duration: {duration_mmss} | Species detected: {len(detections)}",
        "",
    ]

    if detections:
        lines.append("Birds heard:")
        for d in detections:
            conf_note = ""
            if d.max_confidence < 0.7:
                conf_note = " (tentative)"
            lines.append(
                f"- {d.common_name} ({d.scientific_name}) — "
                f"{d.count} detection windows, peak confidence {d.max_confidence:.0%}, "
                f"first heard at {d.first_heard_mmss}{conf_note}"
            )
        lines.append("")
    else:
        lines.append("No birds were detected above the threshold this walk.")
        lines.append("")

    if missed_species:
        next_time = missed_species[:3]
        lines.append(
            f"🔭 Listen for these next time: {', '.join(next_time)}"
        )

    return "\n".join(lines)


def generate_field_card(
    detections: list[Detection],
    missed_species: list[str],
    walk_date: str,
    time_of_day: str = "Day",
    duration_mmss: str = "20:00",
) -> tuple[str, Optional[str], bool]:
    template = _template_card(
        detections, missed_species, walk_date, time_of_day, duration_mmss
    )

    if not detections:
        return template, None, True

    try:
        import ollama

        allowed_species = [d.common_name for d in detections] + missed_species
        prompt = _build_prompt(
            detections, missed_species, walk_date, time_of_day, duration_mmss, allowed_species
        )
        # Use configured timeout and keep_alive
        client = ollama.Client(timeout=config.OLLAMA_TIMEOUT)
        response = client.generate(
            model=config.OLLAMA_MODEL, 
            prompt=prompt,
            options={"temperature": 0.2},
            keep_alive="30m"
        )
        card_text = response.response.strip()  # type: ignore[union-attr]

        if not card_text:
            return template, "Gemma returned an empty response. Showing template card.", True
            
        # Check forbidden birds
        card_lower = card_text.lower()
        forbidden = ["robin", "cardinal", "sparrow", "pigeon", "eagle", "hawk"]
        for f in forbidden:
            if f in card_lower and f not in " ".join(allowed_species).lower():
                return template, f"Gemma hallucinated '{f}'. Showing template card.", True
                
        # Numbers allow-list check
        allowed_numbers = set()
        # duration
        allowed_numbers.update(re.findall(r'\d+', duration_mmss))
        # year, month, day
        allowed_numbers.update(re.findall(r'\d+', walk_date))
        
        for d in detections:
            allowed_numbers.add(str(d.count))
            allowed_numbers.add(str(int(d.max_confidence * 100)))
            allowed_numbers.update(re.findall(r'\d+', d.first_heard_mmss))
            
        # extract all digits from generated card
        generated_numbers = re.findall(r'\b\d+\b', card_text)
        for num in generated_numbers:
            # We allow small numbers (e.g. 1, 2, 3) which are often used for formatting/lists
            if int(num) > 3 and num not in allowed_numbers:
                return template, f"Gemma hallucinated number '{num}'. Showing template card.", True

        return card_text, None, False

    except ImportError:
        return template, "The `ollama` Python package is not installed.", True

    except Exception as e:
        import httpx
        import ollama
        if isinstance(e, (ollama.ResponseError, ConnectionError, httpx.ConnectError, httpx.TimeoutException)):
            msg = "Gemma isn't running. Open the Ollama app (or run `ollama serve`), then press Retry. Your detections are fine; here is a template card meanwhile."
            # Find if it's model missing
            if isinstance(e, ollama.ResponseError) and "not found" in str(e).lower():
                msg = f"Gemma model not found. Run: ollama pull {config.OLLAMA_MODEL}"
            return template, msg, True
        error_msg = str(e)
        return template, f"Ollama error: {error_msg}", True


def build_walk_data(
    detections: list[Detection],
    missed_species: list[str],
    bingo_species: list[str],
    walk_date: str,
    time_of_day: str,
    duration_mmss: str,
    latitude: float,
    longitude: float,
    week: int,
    threshold: float,
    processing_time_s: float,
    model_name: str,
    card_text: str,
    card_warning: Optional[str],
) -> dict:
    return {
        "walk_date": walk_date,
        "time_of_day": time_of_day,
        "duration_mmss": duration_mmss,
        "latitude": latitude,
        "longitude": longitude,
        "week": week,
        "threshold": threshold,
        "processing_time_s": processing_time_s,
        "gemma_model_name": model_name,
        "bingo_species": bingo_species,
        "detections": [asdict(d) for d in detections],
        "missed_species": missed_species,
        "bingo_score": f"{len(detections)}/{len(bingo_species)}",
        "found_count": len(detections),
        "bingo_total": len(bingo_species),
        "field_card": card_text,
        "card_source": "template" if card_warning else "gemma",
        "card_warning": card_warning,
    }
